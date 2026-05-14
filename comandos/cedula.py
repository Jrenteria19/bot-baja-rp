import discord
from discord.ext import commands, tasks
from discord import app_commands
from db_connect import get_db_connection
import aiohttp
import random
import datetime
import re

CANAL_CEDULAS = 1501013466285211851
CANAL_VER_CEDULAS = 1501013466285211851
CANAL_LOGS_CEDULAS = 1499226745793024233
ROL_CIUDADANO = 1481747742018769108

ROLES_ELIMINAR = [
    1481747742047994023
]

ESTADOS_MEXICO = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
]

class INE(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()
        self.verificador_vencimiento.start()

    def cog_unload(self):
        self.verificador_vencimiento.cancel()

    def init_db(self):
        import mysql.connector
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cedulas (
                id SERIAL PRIMARY KEY,
                discord_id BIGINT UNIQUE,
                rob_user VARCHAR(255),
                nombres VARCHAR(255),
                apellidos VARCHAR(255),
                fecha_nac VARCHAR(50),
                edad INTEGER,
                nacionalidad VARCHAR(100),
                sexo VARCHAR(50),
                curp VARCHAR(50) UNIQUE,
                pfp_url VARCHAR(1000),
                fecha_vencimiento VARCHAR(50),
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            cursor.execute('ALTER TABLE cedulas ADD COLUMN IF NOT EXISTS fecha_vencimiento VARCHAR(50)')
        except psycopg2.Error:
            pass 
            
        try:
            cursor.execute('ALTER TABLE cedulas RENAME COLUMN run TO curp')
        except psycopg2.Error:
            pass 
            
        try:
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_cedulas_curp ON cedulas(curp)')
        except psycopg2.Error:
            pass 
        conn.commit()
        conn.close()

    def generar_curp(self, cursor):
        while True:
            letras1 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
            nums = f"{random.randint(0, 99):02d}{random.randint(1, 12):02d}{random.randint(1, 28):02d}"
            letras2 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6))
            nums2 = f"{random.randint(0, 99):02d}"
            curp = f"{letras1}{nums}{letras2}{nums2}"
            
            cursor.execute('SELECT 1 FROM cedulas WHERE curp = %s', (curp,))
            if not cursor.fetchone():
                return curp

    async def obtener_datos_roblox(self, username):
        async with aiohttp.ClientSession() as session:
            payload = {"usernames": [username], "excludeBannedUsers": True}
            async with session.post("https://users.roblox.com/v1/usernames/users", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['data'] and len(data['data']) > 0:
                        user_id = data['data'][0]['id']
                        
                        thumb_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
                        async with session.get(thumb_url) as resp_thumb:
                            if resp_thumb.status == 200:
                                thumb_data = await resp_thumb.json()
                                if thumb_data['data'] and 'imageUrl' in thumb_data['data'][0]:
                                    return thumb_data['data'][0]['imageUrl']
            return None

    @tasks.loop(hours=24)
    async def verificador_vencimiento(self):
        await self.bot.wait_until_ready()
        hoy_str = datetime.date.today().isoformat()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT discord_id, curp FROM cedulas WHERE fecha_vencimiento = %s', (hoy_str,))
        vencidos = cursor.fetchall()
        
        for user_id, curp in vencidos:
            user = self.bot.get_user(user_id)
            if not user:
                try:
                    user = await self.bot.fetch_user(user_id)
                except:
                    continue
            
            if user:
                embed_aviso = discord.Embed(
                    title="⌛ TU CREDENCIAL HA VENCIDO",
                    description=(
                        f"Hola {user.name}, te informamos que tu **Credencial para Votar** (CURP: {curp}) ha llegado a su fecha de vencimiento.\n\n"
                        "Debes proceder a la renovación obligatoria:\n"
                        "1️⃣ Abre un **ticket** con el Staff para solicitar que eliminen tu registro actual.\n"
                        "2️⃣ Una vez eliminado, vuelve al canal correspondiente y crea una nueva.\n\n"
                        "*Este trámite es necesario para mantener tu documentación IC al día.*"
                    ),
                    color=discord.Color.orange()
                )
                embed_aviso.set_footer(text="Instituto Nacional Electoral — Derechos de Autor: Smile")
                
                try:
                    await user.send(embed=embed_aviso)
                except discord.Forbidden:
                    pass
        
        conn.close()

    @app_commands.command(name="crear-ine", description="Tramita tu Credencial para Votar (INE) de forma oficial.")
    @app_commands.describe(
        nombres="Tus nombres (IC)",
        apellidos="Tus apellidos (IC)",
        fecha_de_nacimiento="Tu fecha de nacimiento (DD/MM/AAAA)",
        estado="Tu estado de residencia (Ej. Ciudad de México)",
        sexo="Género de tu personaje",
        roblox_user="Tu nombre de usuario de Roblox"
    )
    @app_commands.choices(sexo=[
        app_commands.Choice(name="Hombre", value="H"),
        app_commands.Choice(name="Mujer", value="M")
    ])
    async def crear_ine(self, interaction: discord.Interaction, nombres: str, apellidos: str, fecha_de_nacimiento: str, roblox_user: str, sexo: app_commands.Choice[str], estado: str = "Ciudad de México"):
        
        if interaction.channel_id != CANAL_CEDULAS:
            embed_error = discord.Embed(
                title="🚫 Acceso Restringido",
                description=f"Para emitir documentos legales, debes encontrarte en el canal oficial.\n\n📍 Ubicación correcta: <#{CANAL_CEDULAS}>",
                color=discord.Color.red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3596/3596041.png")
            embed_error.set_footer(text=f"Seguridad {interaction.guild.name} — Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        tiene_rol = any(r.id == ROL_CIUDADANO for r in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Permisos Insuficientes",
                description=f"No hemos podido verificar tu ciudadanía en {interaction.guild.name}.\n\n*Asegúrate de contar con el rol necesario para tramitar este documento.*",
                color=discord.Color.dark_red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2889/2889312.png")
            embed_error.set_footer(text="Control de Identidad — Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT curp FROM cedulas WHERE discord_id = %s', (interaction.user.id,))
        existe_cedula = cursor.fetchone()

        if existe_cedula:
            conn.close()
            embed_error = discord.Embed(
                title="⚠️ Registro Duplicado",
                description=f"Nuestro sistema indica que el ciudadano {interaction.user.mention} ya posee una identificación activa.\n\n🆔 **CURP registrado:** {existe_cedula[0]}\n\n*Si necesitas realizar modificaciones, por favor abre un ticket de soporte.*",
                color=discord.Color.orange()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/9038/9038844.png")
            embed_error.set_footer(text="Registro Nacional — Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_error, ephemeral=True)

        match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", fecha_de_nacimiento)
        if not match:
            embed_error = discord.Embed(
                title="📅 Formato Incorrecto",
                description="La fecha de nacimiento proporcionada no es válida.\n\n✅ **Formato esperado:** `DD/MM/AAAA` (Ejemplo: 15/05/1995)",
                color=discord.Color.red()
            )
            embed_error.set_footer(text="Validación de Datos — Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_error, ephemeral=True)

        dia, mes, año = map(int, match.groups())
        try:
            fecha_nac_dt = datetime.date(año, mes, dia)
        except ValueError:
            embed_error = discord.Embed(
                title="📆 Fecha Inexistente",
                description="La fecha ingresada no corresponde a un día real en el calendario.\n\n*Por favor, verifica el día y el mes introducidos.*",
                color=discord.Color.red()
            )
            embed_error.set_footer(text="Validación de Calendario — Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_error, ephemeral=True)

        hoy = datetime.date.today()
        expedicion_str = hoy.strftime("%d/%m/%Y")
        
        vigencia_dt = hoy + datetime.timedelta(days=365) # Vigencia 1 año, or 10 years, let's keep it long
        vigencia_str = vigencia_dt.strftime("%d/%m/%Y")
        
        edad = hoy.year - fecha_nac_dt.year - ((hoy.month, hoy.day) < (fecha_nac_dt.month, fecha_nac_dt.day))

        if edad < 18 or edad > 80:
            embed_error = discord.Embed(
                title="🔞 Fuera de Rango de Edad",
                description=f"Lo sentimos, para tramitar la Credencial para Votar debes ser mayor de 18 años.\n\n📊 **Edad calculada:** `{edad} años`",
                color=discord.Color.gold()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3358/3358826.png")
            embed_error.set_footer(text="Restricción de Edad — Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_error, ephemeral=True)

        pfp_url = await self.obtener_datos_roblox(roblox_user)
        
        if pfp_url is None:
            embed_error = discord.Embed(
                title="🔍 Usuario no Encontrado",
                description=f"No pudimos localizar la cuenta de Roblox: **{roblox_user}**.\n\n*Verifica que el nombre de usuario esté bien escrito e inténtalo de nuevo.*",
                color=discord.Color.red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1152/1152912.png")
            embed_error.set_footer(text="Roblox Social — Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_error, ephemeral=True)

        curp = self.generar_curp(cursor)

        try:
            cursor.execute('''
                INSERT INTO cedulas (discord_id, rob_user, nombres, apellidos, fecha_nac, edad, nacionalidad, sexo, curp, pfp_url, fecha_vencimiento)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (interaction.user.id, roblox_user, nombres, apellidos, fecha_de_nacimiento, edad, estado, sexo.value, curp, pfp_url, vigencia_dt.isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            conn.close()
            embed_error = discord.Embed(
                title="💥 Error Crítico",
                description=f"Ocurrió un error inesperado al intentar procesar tu documentación.\n\n`Código: {e}`",
                color=discord.Color.red()
            )
            embed_error.set_footer(text="Error de Base de Datos — Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_error, ephemeral=True)

        embed = discord.Embed(
            title="🇲🇽 INSTITUTO NACIONAL ELECTORAL",
            description="**CREDENCIAL PARA VOTAR**",
            color=discord.Color.from_rgb(229, 38, 104) # Rosa INE
        )
        
        embed.set_thumbnail(url=pfp_url)
        
        embed.add_field(name="NOMBRE", value=f"**{apellidos.upper()}**\n**{nombres.upper()}**", inline=True)
        embed.add_field(name="EDAD", value=f"{edad}", inline=True)
        embed.add_field(name="SEXO", value=sexo.value.upper(), inline=True)
        
        embed.add_field(name="FECHA DE NACIMIENTO", value=fecha_de_nacimiento, inline=True)
        embed.add_field(name="CLAVE DE ELECTOR", value=curp, inline=True)
        embed.add_field(name="CURP", value=curp, inline=True)
        
        embed.add_field(name="ESTADO", value=estado.upper(), inline=True)
        embed.add_field(name="AÑO DE REGISTRO", value=expedicion_str[-4:], inline=True)
        embed.add_field(name="VIGENCIA", value=vigencia_str[-4:], inline=True)

        embed.add_field(name="✍️ FIRMA DIGITAL", value=f"*{roblox_user}*", inline=False)
        
        embed.set_footer(text=f"{interaction.guild.name} | Si algún dato es incorrecto, abre un ticket con el staff para eliminar esta credencial.")
        
        await interaction.channel.send(f"✅ ¡Credencial oficial expedida, {interaction.user.mention}!", embed=embed)
        
        await interaction.followup.send("✅ Tu documentación ha sido aprobada y enviada al canal exitosamente.", ephemeral=True)

    @crear_ine.autocomplete('estado')
    async def estado_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=est, value=est)
            for est in ESTADOS_MEXICO if current.lower() in est.lower()
        ][:25]

    @app_commands.command(name="ver-ine", description="Muestra tu credencial del INE o la de otro ciudadano.")
    @app_commands.describe(ciudadano="El ciudadano al que quieres revisar la credencial (Opcional)")
    async def ver_ine(self, interaction: discord.Interaction, ciudadano: discord.Member = None):
        if interaction.channel_id != CANAL_VER_CEDULAS:
            embed_error = discord.Embed(
                title="🚫 Canal Incorrecto",
                description=f"Este comando de consulta solo funciona en <#{CANAL_VER_CEDULAS}>.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        tiene_rol = any(r.id == ROL_CIUDADANO for r in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso Denegado",
                description="No tienes los permisos de ciudadano para realizar esta consulta.",
                color=discord.Color.dark_red()
            )
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        target = ciudadano if ciudadano else interaction.user
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT nombres, apellidos, nacionalidad, sexo, fecha_nac, edad, curp, pfp_url, fecha_vencimiento FROM cedulas WHERE discord_id = %s', (target.id,))
        datos = cursor.fetchone()
        conn.close()

        if not datos:
            embed_vacio = discord.Embed(
                title="📉 Sin Registro",
                description=f"El usuario {target.mention} no posee una credencial para votar registrada.",
                color=discord.Color.light_grey()
            )
            return await interaction.response.send_message(embed=embed_vacio, ephemeral=True)

        nombres, apellidos, estado, sexo, fecha_nac, edad, curp, pfp_url, fecha_vence_iso = datos
        
        vence_dt = datetime.date.fromisoformat(fecha_vence_iso)
        vence_str = vence_dt.strftime("%d/%m/%Y")
        
        embed = discord.Embed(
            title="🇲🇽 INSTITUTO NACIONAL ELECTORAL",
            description=f"**CREDENCIAL PARA VOTAR**\n\n🔎 *Extrayendo información del padrón de {interaction.guild.name}...*\n\n"
                        f"⚠️ **ADVERTENCIA DE ROL:** Solo usa este comando si tienes a la persona **FRENTE A TI** "
                        f"y ha simulado entregarte el documento físicamente.",
            color=discord.Color.from_rgb(229, 38, 104)
        )
        
        embed.set_thumbnail(url=pfp_url)
        embed.add_field(name="NOMBRE", value=f"**{apellidos.upper()}**\n**{nombres.upper()}**", inline=True)
        embed.add_field(name="EDAD", value=f"{edad}", inline=True)
        embed.add_field(name="SEXO", value=sexo.upper(), inline=True)
        
        embed.add_field(name="FECHA DE NACIMIENTO", value=fecha_nac, inline=True)
        embed.add_field(name="CLAVE DE ELECTOR", value=curp, inline=True)
        embed.add_field(name="CURP", value=curp, inline=True)
        
        embed.add_field(name="ESTADO", value=estado.upper(), inline=True)
        embed.add_field(name="VIGENCIA", value=vence_str[-4:], inline=True)
        embed.add_field(name="FIRMA DIGITAL", value=f"*{target.name}*", inline=False)
        
        embed.set_footer(text=f"Consulta Privada de Documentación | {interaction.guild.name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="eliminar-ine", description="Administración: Elimina la credencial de un ciudadano.")
    @app_commands.describe(usuario="El ciudadano al que se le revocará la credencial", razon="Motivo de la eliminación del documento")
    async def eliminar_ine(self, interaction: discord.Interaction, usuario: discord.Member, razon: str):
        if interaction.channel_id != CANAL_CEDULAS:
            return await interaction.response.send_message(f"❌ Este comando solo se puede usar en <#{CANAL_CEDULAS}>.", ephemeral=True)

        tiene_permiso = any(r.id in ROLES_ELIMINAR for r in interaction.user.roles)
        if not tiene_permiso and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso Denegado",
                description="No tienes el rango administrativo necesario para revocar documentos legales.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT curp, nombres, apellidos FROM cedulas WHERE discord_id = %s', (usuario.id,))
        datos = cursor.fetchone()

        if not datos:
            conn.close()
            return await interaction.response.send_message(f"❌ El usuario {usuario.mention} no tiene ninguna credencial registrada.", ephemeral=True)

        curp, nombres, apellidos = datos

        cursor.execute('DELETE FROM cedulas WHERE discord_id = %s', (usuario.id,))
        conn.commit()
        conn.close()

        embed_dm = discord.Embed(
            title="🚫 TU CREDENCIAL PARA VOTAR HA SIDO REVOCADA",
            description=(
                f"Hola {usuario.name}, te informamos que la administración de **{interaction.guild.name}** ha eliminado tu registro del padrón electoral.\n\n"
                f"📝 **Razón:** {razon}\n"
                f"🆔 **CURP Eliminada:** {curp}\n\n"
                "*Para obtener una nueva, deberás realizar el trámite correspondiente nuevamente en el canal oficial.*"
            ),
            color=discord.Color.red()
        )
        embed_dm.set_footer(text=f"Instituto Nacional Electoral — {interaction.guild.name}")
        
        try:
            await usuario.send(embed=embed_dm)
            dm_status = "✅ Notificado por DM"
        except discord.Forbidden:
            dm_status = "⚠️ No se pudo enviar DM (Privados cerrados)"

        canal_logs = self.bot.get_channel(CANAL_LOGS_CEDULAS)
        if canal_logs:
            embed_log = discord.Embed(
                title="🗑️ Registro de Credencial Eliminada",
                color=discord.Color.dark_grey(),
                timestamp=interaction.created_at
            )
            embed_log.add_field(name="Administrador", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            embed_log.add_field(name="Ciudadano Afectado", value=f"{usuario.mention} (`{usuario.id}`)", inline=False)
            embed_log.add_field(name="Datos Revocados", value=f"**Nombre:** {nombres} {apellidos}\n**CURP:** {curp}", inline=False)
            embed_log.add_field(name="Motivo", value=f"```{razon}```", inline=False)
            embed_log.set_footer(text=f"Estado del DM: {dm_status}")
            await canal_logs.send(embed=embed_log)

        await interaction.response.send_message(f"✅ La credencial de **{usuario.name}** ha sido eliminada exitosamente. {dm_status}", ephemeral=False)

async def setup(bot):
    await bot.add_cog(INE(bot))
