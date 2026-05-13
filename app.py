import os
import requests
from flask import Flask, redirect, request, session, send_from_directory
from dotenv import load_dotenv
from db_connect import get_db_connection
from psycopg2.extras import RealDictCursor

# =====================================================================
# CONFIGURACIÓN INICIAL
# =====================================================================
# Carga las variables del archivo .env a nuestro entorno
load_dotenv()

# Inicialización de la aplicación Flask
# Indicamos que todos los archivos front-end están en la carpeta 'public'
app = Flask(__name__, static_folder='public', static_url_path='')
app.secret_key = os.urandom(24) # Llave secreta para manejar sesiones seguras

# =====================================================================
# VARIABLES DE DISCORD Y ROLES
# =====================================================================
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

# URL de redirección (Asegúrate de que coincida con el portal de desarrolladores de Discord)
REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'https://bot-baja-rp.onrender.com/auth/discord/callback')

# Construcción de la URL de Autorización (OAuth2)
OAUTH2_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"

# Roles específicos del servidor de Discord de BajaRP
ROLE_CIUDADANO = "1481747742018769108"
ROLE_NO_CIUDADANO = "1481747742018769107"

# =====================================================================
# RUTAS DE LA APLICACIÓN WEB
# =====================================================================

@app.route('/')
def index():
    """
    Ruta principal: Muestra la página de inicio.
    Sirve el archivo index.html que se encuentra dentro de la carpeta 'public'.
    """
    return send_from_directory('public', 'index.html')

@app.route('/auth/discord')
def auth_discord():
    """
    Ruta de inicio de sesión: Redirige al usuario al login de Discord.
    """
    return redirect(OAUTH2_URL)

@app.route('/auth/discord/callback')
def callback():
    """
    Ruta de retorno (Callback) de Discord tras autorizar la aplicación.
    Aquí manejamos el código recibido, obtenemos la información del usuario
    y verificamos qué roles tiene dentro del servidor de Discord.
    """
    code = request.args.get('code')
    if not code:
        return "Error: Código de autorización no encontrado.", 400

    # 1. Intercambiar el código por un Access Token
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    if r.status_code != 200:
        return f"Error al intercambiar el token. Discord dice: {r.text}", 400
        
    token_response = r.json()
    access_token = token_response['access_token']
    
    # 2. Obtener datos básicos del usuario desde la API de Discord
    user_req = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    if user_req.status_code != 200:
        return "Error obteniendo datos del usuario de Discord", 400
        
    user_data = user_req.json()
    user_id = user_data['id']
    username = user_data['username']
    avatar_hash = user_data.get('avatar')
    
    if avatar_hash:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
    else:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
    
    # 3. Consultar si el usuario está en nuestro Servidor de Discord (Guild) y obtener sus roles
    member_req = requests.get(f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}", headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"})
    
    if member_req.status_code == 404:
        return "No te encuentras dentro del servidor de Discord de BajaRP. Entra al servidor primero.", 403
    elif member_req.status_code != 200:
        return f"Error checando los roles (Asegúrate de que GUILD_ID es correcto en .env): {member_req.text}", 400
        
    member_data = member_req.json()
    roles = member_data.get('roles', [])
    
    # Guardamos los datos del usuario en su sesión actual
    session['user_id'] = user_id
    session['username'] = username
    session['avatar_url'] = avatar_url
    session['roles'] = roles
    
    # Verificamos si es administrador
    ADMIN_ROLES = ["1481747742047994023", "1481747742047994026", "1481747742047994028"]
    is_admin = any(role in roles for role in ADMIN_ROLES)
    session['is_admin'] = is_admin
    
    # 4. Comprobación de roles y redirección
    if ROLE_CIUDADANO in roles or is_admin:
        session['verified'] = True
        return redirect('/dashboard.html')
    elif ROLE_NO_CIUDADANO in roles:
        session['verified'] = False
        return redirect('/whitelist.html')
    else:
        return "No tienes el rol de Ciudadano ni el de No Ciudadano asignado en Discord. Contacta a un administrador.", 403

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario y redirige al inicio."""
    session.clear()
    return redirect('/')
@app.route('/api/user_info')
def user_info():
    """Devuelve la información de la sesión actual para usarla en el Frontend."""
    if 'user_id' not in session:
        return {"error": "No has iniciado sesión"}, 401
    
    user_id = session['user_id']
    
    # Extraer información adicional desde Supabase (PostgreSQL)
    saldo = 0
    sanciones_count = 0
    has_ine = False
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener saldo bancario
        cursor.execute('SELECT saldo FROM cuentas_bancarias WHERE id = %s', (user_id,))
        row = cursor.fetchone()
        if row:
            saldo = row[0]
            
        # Obtener cantidad de sanciones
        cursor.execute('SELECT COUNT(*) FROM sanciones WHERE usuario_id = %s', (user_id,))
        row = cursor.fetchone()
        if row:
            sanciones_count = row[0]
            
        # Comprobar INE
        cursor.execute('SELECT 1 FROM cedulas WHERE discord_id = %s', (user_id,))
        if cursor.fetchone():
            has_ine = True
            
        conn.close()
    except Exception as e:
        print(f"Error al obtener datos adicionales de {user_id}: {e}")
    
    return {
        "discord_id": user_id,
        "discord_name": session['username'],
        "avatar_url": session.get('avatar_url', 'https://cdn.discordapp.com/embed/avatars/0.png'),
        "is_admin": session.get('is_admin', False),
        "is_verified": session.get('verified', False),
        "saldo": saldo,
        "sanciones": sanciones_count,
        "tiene_ine": has_ine
    }

@app.route('/submit_whitelist', methods=['POST'])
def submit_whitelist():
    """Recibe y guarda en la base de datos el formulario de Whitelist."""
    if 'user_id' not in session:
        return {"error": "No has iniciado sesión. Vuelve al inicio."}, 401

    data = request.json
    roblox_name = data.get('roblox_name')
    q1 = data.get('q1')
    q2 = data.get('q2')
    q3 = data.get('q3')
    q4 = data.get('q4')
    q5 = data.get('q5')

    if not all([roblox_name, q1, q2, q3, q4, q5]):
        return {"error": "Faltan campos por completar."}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si ya envió una solicitud previamente
        cursor.execute("SELECT status FROM whitelists WHERE discord_id = %s ORDER BY created_at DESC LIMIT 1", (session['user_id'],))
        existing = cursor.fetchone()
        
        if existing and existing[0] == 'Pendiente':
            cursor.close()
            conn.close()
            return {"error": "Ya tienes una solicitud de Whitelist pendiente de revisión."}, 400
            
        cursor.execute('''
            INSERT INTO whitelists (discord_id, discord_name, roblox_name, q1, q2, q3, q4, q5, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente')
        ''', (session['user_id'], session['username'], roblox_name, q1, q2, q3, q4, q5))
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "✅ Solicitud enviada exitosamente. Espere de 1 a 3 días hábiles a que la administración la revise para que pueda rolear."}
    except Exception as e:
        print(f"Error en submit_whitelist: {e}")
        return {"error": "Hubo un error interno al guardar tu solicitud. Intenta más tarde."}, 500

@app.route('/api/pending_whitelists')
def pending_whitelists():
    """Devuelve todas las Whitelists pendientes si el usuario es administrador."""
    if not session.get('is_admin'):
        return {"error": "Acceso denegado"}, 403
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, discord_name, roblox_name, q1, q2, q3, q4, q5, created_at FROM whitelists WHERE status = 'Pendiente' ORDER BY created_at ASC")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"whitelists": data}
    except Exception as e:
        print(f"Error en pending_whitelists: {e}")
        return {"error": "Error interno del servidor"}, 500

@app.route('/api/resolve_whitelist', methods=['POST'])
def resolve_whitelist():
    """Permite a un administrador aceptar o denegar una Whitelist."""
    if not session.get('is_admin'):
        return {"error": "Acceso denegado"}, 403
        
    data = request.json
    whitelist_id = data.get('id')
    action = data.get('action') # 'accept' or 'deny'
    reason = data.get('reason', '') # Razón de rechazo
    
    if not whitelist_id or action not in ['accept', 'deny']:
        return {"error": "Datos inválidos"}, 400
        
    if action == 'deny' and not reason:
        return {"error": "Debes proporcionar una razón para denegar la solicitud."}, 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener datos antes de borrar
        cursor.execute("SELECT discord_id, roblox_name FROM whitelists WHERE id = %s", (whitelist_id,))
        record = cursor.fetchone()
        
        if not record:
            cursor.close()
            conn.close()
            return {"error": "Whitelist no encontrada o ya fue procesada."}, 404
            
        target_discord_id = record['discord_id']
        roblox_name = record['roblox_name']
        
        headers = {
            "Authorization": f"Bot {DISCORD_BOT_TOKEN}", 
            "Content-Type": "application/json"
        }
        
        if action == 'accept':
            # 1. Quitar rol de No Ciudadano
            requests.delete(f"https://discord.com/api/guilds/{GUILD_ID}/members/{target_discord_id}/roles/{ROLE_NO_CIUDADANO}", headers=headers)
            # 2. Poner rol de Ciudadano
            requests.put(f"https://discord.com/api/guilds/{GUILD_ID}/members/{target_discord_id}/roles/{ROLE_CIUDADANO}", headers=headers)
            # 3. Cambiar apodo (Requiere permisos en el Bot)
            requests.patch(f"https://discord.com/api/guilds/{GUILD_ID}/members/{target_discord_id}", headers=headers, json={"nick": roblox_name})
            
            # 4. Enviar MD de aceptación
            dm_req = requests.post("https://discord.com/api/users/@me/channels", headers=headers, json={"recipient_id": target_discord_id})
            if dm_req.status_code == 200:
                channel_id = dm_req.json().get('id')
                embed_accept = {
                    "title": "🎉 ¡WHITELIST APROBADA!",
                    "description": "¡Felicidades! Tu formulario de verificación en **BajaRP** ha sido revisado y **ACEPTADO** por la administración.\n\nYa estás oficialmente **verificado** en nuestro servidor de Discord y tienes acceso completo a todos los canales.\n\n💻 **DASHBOARD WEB:** Ya puedes entrar a nuestra página web oficial y tener acceso completo a tu panel personal y a tus beneficios.",
                    "color": 3066993,
                    "thumbnail": {
                        "url": "https://media.discordapp.net/attachments/1481747743230656571/1500738582866821270/bajaRP_logo-Photoroom.png"
                    },
                    "fields": [
                        {
                            "name": "📌 Siguientes Pasos",
                            "value": "Ingresa al servidor y recuerda tramitar tu **INE** (Identificación) lo antes posible.\n📖 Es tu responsabilidad conocer y respetar las normativas en todo momento."
                        }
                    ],
                    "footer": {
                        "text": "¡Disfruta tu estancia en BajaRP!"
                    }
                }
                requests.post(f"https://discord.com/api/channels/{channel_id}/messages", headers=headers, json={"embeds": [embed_accept]})
                
            estado = "Aceptada"
            
        elif action == 'deny':
            # 1. Crear canal de MD
            dm_req = requests.post("https://discord.com/api/users/@me/channels", headers=headers, json={"recipient_id": target_discord_id})
            if dm_req.status_code == 200:
                channel_id = dm_req.json().get('id')
                embed_deny = {
                    "title": "❌ WHITELIST RECHAZADA",
                    "description": "Hola. Lamentamos informarte que tras revisar tu formulario, tu verificación para entrar a **BajaRP** ha sido **DENEGADA**.",
                    "color": 15158332,
                    "thumbnail": {
                        "url": "https://media.discordapp.net/attachments/1481747743230656571/1500738582866821270/bajaRP_logo-Photoroom.png"
                    },
                    "fields": [
                        {
                            "name": "📄 Motivo del Rechazo",
                            "value": f"```{reason}```"
                        },
                        {
                            "name": "🔄 ¿Qué hago ahora?",
                            "value": "Te invitamos cordialmente a que **vuelvas a leer detenidamente las normativas y reglas** del servidor. Una vez que las repases, puedes volver a iniciar sesión y enviar una **nueva solicitud de verificación** tal y como lo hiciste antes."
                        }
                    ],
                    "footer": {
                        "text": "Sistema de Verificación | BajaRP"
                    }
                }
                requests.post(f"https://discord.com/api/channels/{channel_id}/messages", headers=headers, json={"embeds": [embed_deny]})
            estado = "Denegada"

        # Eliminar de la base de datos ya que ha sido procesada
        cursor.execute("DELETE FROM whitelists WHERE id = %s", (whitelist_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {"message": f"Whitelist {estado}. Se han actualizado los roles y enviado MDs si aplica."}
    except Exception as e:
        print(f"Error en resolve_whitelist: {e}")
        return {"error": "Error interno del servidor al procesar la solicitud"}, 500

# =====================================================================
# INICIALIZACIÓN DEL SERVIDOR WEB
# =====================================================================
if __name__ == '__main__':
    # Creación automática de tablas requeridas en la Base de Datos si no existen
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whitelists (
                id SERIAL PRIMARY KEY,
                discord_id VARCHAR(255) NOT NULL,
                discord_name VARCHAR(255) NOT NULL,
                roblox_name VARCHAR(255) NOT NULL,
                q1 TEXT NOT NULL,
                q2 TEXT NOT NULL,
                q3 TEXT NOT NULL,
                q4 TEXT NOT NULL,
                q5 TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'Pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Base de datos conectada correctamente y tabla 'whitelists' verificada/creada.")
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")

    # Arrancamos el servidor
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 Servidor web iniciado en: http://0.0.0.0:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
