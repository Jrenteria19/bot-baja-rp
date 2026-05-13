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

@app.route('/api/economy', methods=['POST'])
def handle_economy():
    """Maneja las acciones económicas del dashboard: transferir, cobrar, agregar, quitar."""
    if 'user_id' not in session:
        return {"error": "No has iniciado sesión."}, 401
        
    data = request.json
    action = data.get('action')
    user_id = int(session['user_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    def get_saldo(uid):
        cursor.execute('SELECT saldo FROM cuentas_bancarias WHERE id = %s', (uid,))
        res = cursor.fetchone()
        if not res:
            cursor.execute('INSERT INTO cuentas_bancarias (id, saldo) VALUES (%s, 0)', (uid,))
            conn.commit()
            return 0
        return res[0]
        
    try:
        if action == 'transferir':
            target_id = int(data.get('target_id', 0))
            amount = int(data.get('amount', 0))
            concept = data.get('concept', 'Sin concepto')
            
            if amount < 10 or amount > 2000000:
                return {"error": "La transferencia debe ser entre $10 y $2,000,000 MXN."}, 400
                
            if target_id == user_id:
                return {"error": "No puedes transferirte a ti mismo."}, 400
                
            saldo_actual = get_saldo(user_id)
            if saldo_actual < amount:
                return {"error": "Fondos insuficientes."}, 400
                
            saldo_target = get_saldo(target_id)
            if saldo_target + amount > 50000000:
                return {"error": "El destinatario ha alcanzado el límite patrimonial máximo (50 Millones)."}, 400
                
            cursor.execute('UPDATE cuentas_bancarias SET saldo = saldo - %s WHERE id = %s', (amount, user_id))
            cursor.execute('UPDATE cuentas_bancarias SET saldo = saldo + %s WHERE id = %s', (amount, target_id))
            conn.commit()
            
            # Notificación a Discord Log
            headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
            log_embed = {
                "title": "📝 Registro Financiero | Transferencia Web",
                "description": f"**Remitente:** <@{user_id}>\n**Destinatario:** <@{target_id}>\n**Monto transferido:** `${amount:,.0f} MXN`\n**Concepto:** {concept}",
                "color": 3447003
            }
            requests.post("https://discord.com/api/channels/1501013259271274543/messages", headers=headers, json={"embeds": [log_embed]})
            
            # DM al destinatario
            dm_req = requests.post("https://discord.com/api/users/@me/channels", headers=headers, json={"recipient_id": target_id})
            if dm_req.status_code == 200:
                ch_id = dm_req.json().get('id')
                dm_embed = {
                    "title": "💰 TRANSFERENCIA RECIBIDA",
                    "description": f"Has recibido una transferencia bancaria (Vía Web).\n\n**Remitente:** <@{user_id}>\n**Monto:** `${amount:,.0f} MXN`\n**Concepto:** {concept}",
                    "color": 3066993
                }
                requests.post(f"https://discord.com/api/channels/{ch_id}/messages", headers=headers, json={"embeds": [dm_embed]})
                
            return {"message": "Transferencia realizada con éxito."}

        elif action in ['agregar', 'quitar']:
            if not session.get('is_admin'):
                return {"error": "Acceso denegado. Se requiere Alta Administración Financiera."}, 403
                
            target_id = int(data.get('target_id', 0))
            amount = int(data.get('amount', 0))
            concept = data.get('concept', 'Sin concepto')
            
            if amount <= 0:
                return {"error": "La cantidad debe ser mayor a 0."}, 400
                
            saldo_target = get_saldo(target_id)
            
            if action == 'agregar':
                if saldo_target + amount > 50000000:
                    return {"error": "Límite patrimonial excedido. (Tope 50 Millones)"}, 400
                cursor.execute('UPDATE cuentas_bancarias SET saldo = saldo + %s WHERE id = %s', (amount, target_id))
            else:
                if saldo_target < amount:
                    amount = saldo_target # Solo quitamos lo que tiene
                    cursor.execute('UPDATE cuentas_bancarias SET saldo = 0 WHERE id = %s', (target_id,))
                else:
                    cursor.execute('UPDATE cuentas_bancarias SET saldo = saldo - %s WHERE id = %s', (amount, target_id))
            
            conn.commit()
            
            headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
            color = 3066993 if action == 'agregar' else 15158332
            title = "Depósito Administrativo Web" if action == 'agregar' else "Embargo Web"
            
            log_embed = {
                "title": f"📝 Registro Financiero | {title}",
                "description": f"**Oficial a cargo:** <@{user_id}>\n**Cuenta afectada:** <@{target_id}>\n**Monto:** `${amount:,.0f} MXN`\n**Comprobante:** {concept}",
                "color": color
            }
            requests.post("https://discord.com/api/channels/1501013259271274543/messages", headers=headers, json={"embeds": [log_embed]})
            
            dm_req = requests.post("https://discord.com/api/users/@me/channels", headers=headers, json={"recipient_id": target_id})
            if dm_req.status_code == 200:
                ch_id = dm_req.json().get('id')
                dm_title = "💰 DEPÓSITO BANCARIO APROBADO" if action == 'agregar' else "📉 EMBARGO BANCARIO EJECUTADO"
                dm_embed = {
                    "title": dm_title,
                    "description": f"La Secretaría de Hacienda ha realizado un movimiento en tu cuenta (Vía Web).\n\n**Monto:** `${amount:,.0f} MXN`\n**Concepto:** {concept}",
                    "color": color
                }
                requests.post(f"https://discord.com/api/channels/{ch_id}/messages", headers=headers, json={"embeds": [dm_embed]})
                
            return {"message": f"Transacción de {action} completada por ${amount} MXN."}

        elif action == 'cobrar':
            return {"error": "El sistema automático de cobro de sueldos está en mantenimiento en la web. Por favor, utiliza el comando /cobrar-sueldo en el canal #banco de Discord."}, 400

    except ValueError:
        return {"error": "Los campos de ID o cantidad deben ser numéricos."}, 400
    except Exception as e:
        print(f"Error en economy: {e}")
        return {"error": "Error interno al procesar la transacción."}, 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/cedula', methods=['POST'])
def handle_cedula():
    """Maneja las acciones del Registro Civil: ver_propia, ver_otra, crear, eliminar."""
    if 'user_id' not in session:
        return {"error": "No has iniciado sesión."}, 401
        
    data = request.json
    action = data.get('action')
    user_id = int(session['user_id'])
    
    conn = get_db_connection()
    # Use RealDictCursor to easily JSON serialize the row
    cursor = conn.cursor(cursor_factory=RealDictCursor) if hasattr(conn, 'cursor_factory') else conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if action == 'ver_propia' or action == 'ver_otra':
            target_id = user_id if action == 'ver_propia' else int(data.get('target_id', 0))
            
            cursor.execute('SELECT * FROM cedulas WHERE discord_id = %s', (target_id,))
            ine = cursor.fetchone()
            
            if not ine:
                return {"error": "El usuario no cuenta con un registro en el INE."}, 404
                
            # Convert values to strings for JSON serializability (dates, integers, etc)
            ine_data = {
                "discord_id": str(ine['discord_id']),
                "rob_user": ine['rob_user'],
                "nombres": ine['nombres'],
                "apellidos": ine['apellidos'],
                "fecha_nac": ine['fecha_nac'],
                "edad": ine['edad'],
                "nacionalidad": ine['nacionalidad'],
                "sexo": "Hombre" if ine['sexo'] == 'H' else "Mujer" if ine['sexo'] == 'M' else ine['sexo'],
                "curp": ine['curp'],
                "pfp_url": ine['pfp_url'],
                "fecha_vencimiento": ine['fecha_vencimiento']
            }
            return {"ine": ine_data}

        elif action in ['crear', 'eliminar']:
            if not session.get('is_admin'):
                return {"error": "Acceso denegado. Se requieren permisos de Administración."}, 403
                
            target_id = data.get('target_id')
            
            if action == 'eliminar':
                # Can delete by Discord ID or CURP
                cursor.execute('SELECT discord_id FROM cedulas WHERE discord_id = %s OR curp = %s', (target_id, target_id))
                ine = cursor.fetchone()
                if not ine:
                    return {"error": "Registro no encontrado."}, 404
                    
                target_discord_id = ine['discord_id']
                cursor.execute('DELETE FROM cedulas WHERE discord_id = %s', (target_discord_id,))
                conn.commit()
                
                # Send Discord DM to notify them of removal
                headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
                dm_req = requests.post("https://discord.com/api/users/@me/channels", headers=headers, json={"recipient_id": target_discord_id})
                if dm_req.status_code == 200:
                    ch_id = dm_req.json().get('id')
                    dm_embed = {
                        "title": "⚖️ ANULACIÓN DE IDENTIDAD",
                        "description": "Tu Credencial para Votar (INE) ha sido **anulada y eliminada** del sistema por la administración.\n\n*Si consideras que fue un error, abre un ticket.*",
                        "color": 15158332
                    }
                    requests.post(f"https://discord.com/api/channels/{ch_id}/messages", headers=headers, json={"embeds": [dm_embed]})
                    
                return {"message": "Registro eliminado exitosamente."}
                
            elif action == 'crear':
                roblox_user = data.get('roblox_user')
                nombres = data.get('nombres')
                apellidos = data.get('apellidos')
                fecha_nac = data.get('fecha_nac')
                sexo = data.get('sexo')
                
                if not all([target_id, roblox_user, nombres, apellidos, fecha_nac, sexo]):
                    return {"error": "Faltan datos obligatorios."}, 400
                    
                # Validar fecha
                import re, datetime
                match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", fecha_nac)
                if not match:
                    return {"error": "El formato de fecha debe ser DD/MM/AAAA."}, 400
                    
                dia, mes, año = map(int, match.groups())
                try:
                    fecha_nac_dt = datetime.date(año, mes, dia)
                except ValueError:
                    return {"error": "La fecha proporcionada no es válida."}, 400
                    
                hoy = datetime.date.today()
                edad = hoy.year - fecha_nac_dt.year - ((hoy.month, hoy.day) < (fecha_nac_dt.month, fecha_nac_dt.day))
                
                if edad < 18 or edad > 80:
                    return {"error": f"La persona debe tener entre 18 y 80 años. Edad calculada: {edad}"}, 400
                    
                # Fetch roblox avatar via API
                pfp_url = "https://cdn.discordapp.com/embed/avatars/0.png"
                try:
                    rbx_req = requests.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [roblox_user], "excludeBannedUsers": True})
                    if rbx_req.status_code == 200:
                        rbx_data = rbx_req.json()
                        if rbx_data.get('data') and len(rbx_data['data']) > 0:
                            rbx_id = rbx_data['data'][0]['id']
                            thumb_req = requests.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={rbx_id}&size=420x420&format=Png&isCircular=false")
                            if thumb_req.status_code == 200:
                                thumb_data = thumb_req.json()
                                if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                    pfp_url = thumb_data['data'][0]['imageUrl']
                except Exception as e:
                    print(f"Error fetching roblox avatar: {e}")
                    
                # Generate pseudo CURP
                import random
                letras1 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
                nums = f"{random.randint(0, 99):02d}{random.randint(1, 12):02d}{random.randint(1, 28):02d}"
                letras2 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6))
                nums2 = f"{random.randint(0, 99):02d}"
                curp = f"{letras1}{nums}{letras2}{nums2}"
                
                vigencia_dt = hoy + datetime.timedelta(days=365)
                
                try:
                    cursor.execute('''
                        INSERT INTO cedulas (discord_id, rob_user, nombres, apellidos, fecha_nac, edad, nacionalidad, sexo, curp, pfp_url, fecha_vencimiento)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (target_id, roblox_user, nombres, apellidos, fecha_nac, edad, "México", sexo, curp, pfp_url, vigencia_dt.strftime("%d/%m/%Y")))
                    conn.commit()
                except Exception as e:
                    return {"error": "El usuario ya tiene un registro activo."}, 400
                    
                return {"message": f"INE generado exitosamente para {target_id}. CURP: {curp}"}

    except Exception as e:
        print(f"Error en cedula API: {e}")
        return {"error": "Error interno al procesar la solicitud."}, 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/sanciones', methods=['POST'])
def handle_sanciones():
    """Maneja las sanciones: ver propias, ver de otros, crear y eliminar."""
    if 'user_id' not in session:
        return {"error": "No has iniciado sesión."}, 401
        
    data = request.json
    action = data.get('action')
    user_id = int(session['user_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if hasattr(conn, 'cursor_factory') else conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if action == 'ver_propia' or action == 'ver_otra':
            target_id = user_id if action == 'ver_propia' else int(data.get('target_id', 0))
            
            cursor.execute('SELECT tipo, razon, prueba FROM sanciones WHERE usuario_id = %s', (target_id,))
            sanciones = cursor.fetchall()
            
            # Formatear
            sanc_list = []
            for s in sanciones:
                sanc_list.append({
                    "tipo": s['tipo'].replace('_', ' '),
                    "razon": s['razon'],
                    "prueba": s['prueba']
                })
                
            return {"sanciones": sanc_list}

        elif action in ['crear', 'eliminar']:
            if not session.get('is_admin'):
                return {"error": "Acceso denegado. Se requieren permisos de Administración."}, 403
                
            target_id = int(data.get('target_id', 0))
            tipo = data.get('tipo')
            
            if action == 'eliminar':
                cursor.execute('DELETE FROM sanciones WHERE usuario_id = %s AND tipo = %s', (target_id, tipo))
                if cursor.rowcount == 0:
                    return {"error": "El usuario no tiene ese castigo específico."}, 404
                conn.commit()
                
                # Opcional: Logs de discord
                return {"message": "Sanción/Advertencia retirada exitosamente."}
                
            elif action == 'crear':
                razon = data.get('razon')
                prueba = data.get('prueba')
                
                if not all([target_id, tipo, razon, prueba]):
                    return {"error": "Todos los campos son obligatorios."}, 400
                    
                cursor.execute('SELECT 1 FROM sanciones WHERE usuario_id = %s AND tipo = %s', (target_id, tipo))
                if cursor.fetchone():
                    return {"error": "El usuario ya tiene ese castigo específico (cada tipo es único)."}, 400
                    
                cursor.execute('INSERT INTO sanciones (usuario_id, tipo, razon, prueba) VALUES (%s, %s, %s, %s)', (target_id, tipo, razon, prueba))
                conn.commit()
                
                headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
                
                # Enviar DM al sancionado
                dm_req = requests.post("https://discord.com/api/users/@me/channels", headers=headers, json={"recipient_id": target_id})
                if dm_req.status_code == 200:
                    ch_id = dm_req.json().get('id')
                    dm_embed = {
                        "title": "⚠️ NUEVA SANCIÓN REGISTRADA",
                        "description": f"Se ha añadido un nuevo castigo a tu expediente (Vía Web).\n\n**Tipo:** {tipo}\n**Motivo:** {razon}\n**Evidencia:** [Ver]({prueba})",
                        "color": 16711680 if 'sancion' in tipo else 16753920
                    }
                    requests.post(f"https://discord.com/api/channels/{ch_id}/messages", headers=headers, json={"embeds": [dm_embed]})
                    
                # Log en el canal oficial
                log_embed = {
                    "title": "📝 Registro de Sistema - Nueva Sanción Web",
                    "description": f"**Moderador:** <@{user_id}>\n**Usuario Sancionado:** <@{target_id}>\n**Tipo Asignado:** {tipo}\n**Razón:** {razon}\n**Evidencia:** {prueba}",
                    "color": 16776960
                }
                requests.post("https://discord.com/api/channels/1501012505785532549/messages", headers=headers, json={"embeds": [log_embed]})
                
                return {"message": "Sanción/Advertencia aplicada exitosamente."}

    except Exception as e:
        print(f"Error en sanciones API: {e}")
        return {"error": "Error interno al procesar la solicitud."}, 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/calificaciones', methods=['POST'])
def handle_calificaciones():
    """Maneja las calificaciones de staff: consultar semana, calificar, ver un staff"""
    if 'user_id' not in session:
        return {"error": "No has iniciado sesión."}, 401
        
    data = request.json
    action = data.get('action')
    user_id = int(session['user_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) if hasattr(conn, 'cursor_factory') else conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if action == 'semana':
            cursor.execute('''
                SELECT staff_id, AVG(estrellas) as promedio, COUNT(estrellas) as total 
                FROM calificaciones_staffs 
                GROUP BY staff_id 
                ORDER BY promedio DESC, total DESC 
                LIMIT 1
            ''')
            top = cursor.fetchone()
            if top:
                return {"staff_semana": {"id": str(top['staff_id']), "promedio": round(top['promedio'], 1), "total": top['total']}}
            return {"staff_semana": None}
            
        elif action == 'consultar':
            target_id = int(data.get('target_id', 0))
            cursor.execute('SELECT estrellas, mensaje FROM calificaciones_staffs WHERE staff_id = %s ORDER BY id DESC', (target_id,))
            resenas = cursor.fetchall()
            
            if not resenas:
                return {"stats": {"promedio": 0, "total": 0, "resenas": []}}
                
            promedio = sum(r['estrellas'] for r in resenas) / len(resenas)
            
            # Formatear las últimas 5
            lista_resenas = []
            for r in resenas[:5]:
                lista_resenas.append({"estrellas": r['estrellas'], "mensaje": r['mensaje']})
                
            return {"stats": {"promedio": round(promedio, 1), "total": len(resenas), "resenas": lista_resenas}}
            
        elif action == 'calificar':
            target_id = int(data.get('target_id', 0))
            estrellas = int(data.get('estrellas', 0))
            mensaje = data.get('mensaje', '').strip()
            
            if user_id == target_id:
                return {"error": "No puedes autocalificarte a ti mismo."}, 400
                
            if estrellas < 1 or estrellas > 5:
                return {"error": "La puntuación debe ser entre 1 y 5 estrellas."}, 400
                
            if not mensaje:
                return {"error": "Debes proporcionar un mensaje de retroalimentación."}, 400
                
            cursor.execute('INSERT INTO calificaciones_staffs (usuario_id, staff_id, estrellas, mensaje) VALUES (%s, %s, %s, %s)', 
                          (user_id, target_id, estrellas, mensaje))
            conn.commit()
            
            # Enviar mensaje a Discord canal de calificaciones
            headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}
            embed_publico = {
                "title": "✨ ¡NUEVA VALORACIÓN DE STAFF RECIBIDA (Web)!",
                "description": f"La comunidad acaba de evaluar la atención de un Staff.\n\n*ℹ️ Recuerda: Cada semana las calificaciones se borrarán automáticamente.*\n",
                "color": 15844367,
                "fields": [
                    {"name": "🙎‍♂️ Calificado por:", "value": f"<@{user_id}>", "inline": True},
                    {"name": "🛡️ Staff Evaluado:", "value": f"<@{target_id}>", "inline": True},
                    {"name": "🎖️ Puntuación:", "value": "⭐" * estrellas, "inline": False},
                    {"name": "📝 Mensaje:", "value": f"```\n{mensaje}\n```", "inline": False}
                ]
            }
            requests.post("https://discord.com/api/channels/1481747743230656570/messages", headers=headers, json={"embeds": [embed_publico]})
            
            # Mandar log a admins
            embed_log = {
                "title": "📝 Registro de Sistema - Valoración Web",
                "color": 3447003,
                "fields": [
                    {"name": "Usuario", "value": f"<@{user_id}>", "inline": True},
                    {"name": "Staff", "value": f"<@{target_id}>", "inline": True},
                    {"name": "Puntaje Real", "value": f"{estrellas}/5", "inline": True},
                    {"name": "Mensaje", "value": f"```\n{mensaje}\n```", "inline": False}
                ]
            }
            requests.post("https://discord.com/api/channels/1501007004171239464/messages", headers=headers, json={"embeds": [embed_log]})
            
            return {"message": "Reseña enviada correctamente. ¡Gracias por tu opinión!"}

    except Exception as e:
        print(f"Error en calificaciones API: {e}")
        return {"error": "Error interno al procesar la solicitud."}, 500
    finally:
        cursor.close()
        conn.close()

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
