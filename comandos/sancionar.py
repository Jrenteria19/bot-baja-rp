import discord
from discord.ext import commands
from discord import app_commands
from db_connect import get_db_connection
import os

CANAL_SANCIONES = 1481747742475944137
CANAL_LOGS_SANCION = 1501012505785532549

# Roles que pueden usar los comandos de sanciones
ROLES_PERMITIDOS = [
    1481747742047994023
]

# Mapeo de valores de sanciones a IDs de roles
TIPOS_SANCION = {
    # Advertencias (Usuarios)
    "sancion_1": {"id": 1481747741561458845, "nombre": "Sancion 1"},
    "sancion_2": {"id": 1481747741561458844, "nombre": "Sancion 2"},
    "sancion_3": {"id": 1481747741561458843, "nombre": "Sancion 3"},
}

class Sancionar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()

    def init_db(self):
        import mysql.connector
        # Crear la estructura de Base de datos en MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sanciones (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                usuario_id BIGINT,
                tipo VARCHAR(100),
                razon TEXT,
                prueba TEXT
            )
        ''')
        # Añade la columna si ya estaba la tabla antes (en caso de actualización sin perder datos)
        try:
            cursor.execute("ALTER TABLE sanciones ADD COLUMN prueba TEXT;")
        except mysql.connector.Error:
            pass # Si ya existe no hay que crearla
        conn.commit()
        conn.close()

    @app_commands.command(name="sancionar-a", description="Sanciona a un usuario otorgándole un Castigo, Warn o Strike.")
    @app_commands.describe(
        usuario="El usuario que recibirá la sanción/warn",
        tipo="El nivel de castigo a aplicar",
        razon="El motivo específico de la sanción",
        prueba="Enlace o link (imagen/video) de la prueba que acredite la sanción"
    )
    # Autocompletado fijo con los tipos que solicitas
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Sanción 1", value="sancion_1"),
        app_commands.Choice(name="Sanción 2", value="sancion_2"),
        app_commands.Choice(name="Sanción 3", value="sancion_3")
    ])
    async def sancionar_a(self, interaction: discord.Interaction, usuario: discord.Member, tipo: app_commands.Choice[str], razon: str, prueba: str):
        
        # 0. Validar Rol Permitido
        tiene_permiso = any(role.id in ROLES_PERMITIDOS for role in interaction.user.roles)
        if not tiene_permiso and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso Denegado",
                description="No tienes los permisos o el rango necesario para gestionar sanciones.",
                color=discord.Color.red()
            )
            embed_error.set_footer(text="Seguridad el servidor — Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)
        
        # 1. Validar si está en el canal correcto
        if interaction.channel_id != CANAL_SANCIONES:
            embed_error = discord.Embed(
                title="🚫 Canal Incorrecto",
                description=f"Este comando no se puede usar aquí.\nDirígete al canal designado: <#{CANAL_SANCIONES}> para aplicar sanciones.",
                color=discord.Color.dark_red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
            embed_error.set_footer(text="Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # Retrasamos la respuesta ya que haremos cosas en la base de datos y DM
        await interaction.response.defer(ephemeral=True)

        # 2. Base de Datos MySQL: Validar duplicados y registrarlo
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ¿El usuario ya tiene exactamente esta sanción en la BD de el servidor?
        cursor.execute('SELECT 1 FROM sanciones WHERE usuario_id = %s AND tipo = %s', (usuario.id, tipo.value))
        existe = cursor.fetchone()
        
        if existe:
            conn.close()
            # Si ya la tiene, le enviamos otro efímero diciéndole que ponga la del escalón de arriba
            embed_dup = discord.Embed(
                title="⚠️ Sanción Duplicada",
                description=f"El usuario {usuario.mention} ya cuenta con **{tipo.name}** en el historial.\nNo puedes duplicarla. Por favor, aplícale una sanción o warn **superior** (ej. la de un nivel más alto).",
                color=discord.Color.orange()
            )
            embed_dup.set_footer(text="Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_dup, ephemeral=True)

        # INSERTAR en la DB
        cursor.execute('INSERT INTO sanciones (usuario_id, tipo, razon, prueba) VALUES (%s, %s, %s, %s)', (usuario.id, tipo.value, razon, prueba))
        conn.commit()
        conn.close()

        # Opcional: Entregar el respectivo Rol de sanción a través de la ID del rol (Warn 1, Sancion 2, etc.)
        rol_id = TIPOS_SANCION[tipo.value]["id"]
        rol_obj = interaction.guild.get_role(rol_id)
        if rol_obj:
            try:
                await usuario.add_roles(rol_obj, reason=f"Sancionado por {interaction.user.name}: {razon}")
            except Exception:
                pass # Si el bot no tiene jerarquía para dar el rol, simplemente lo ignora

        # 3. Mandar el Embed Público en el Canal de Sanciones
        embed_canal = discord.Embed(
            title="🔨 NUEVA SANCIÓN REGISTRADA",
            description=f"Se ha dictaminado una nueva sanción a un miembro de la comunidad.",
            color=discord.Color.red()
        )
        embed_canal.add_field(name="🙎‍♂️ Usuario Sancionado:", value=usuario.mention, inline=True)
        embed_canal.add_field(name="🛑 Tipo de Castigo:", value=f"**{tipo.name}**", inline=True)
        embed_canal.add_field(name="📄 Razón/Motivo:", value=f"```\n{razon}\n```", inline=False)
        embed_canal.add_field(name="🔗 Prueba Presentada:", value=f"[Haz clic aquí para ver la evidencia]({prueba})", inline=False)
        embed_canal.add_field(name="🛡️ Moderador:", value=interaction.user.mention, inline=False)
        embed_canal.set_thumbnail(url=usuario.display_avatar.url if usuario.display_avatar else interaction.guild.icon.url)
        embed_canal.set_footer(text="Derechos de Autor: Smile")

        mensaje_sancion = await interaction.channel.send(embed=embed_canal)
        link_al_mensaje = mensaje_sancion.jump_url # Extrae directamente el hiperenlace hacia este mensaje
        
        # Confirmamos al Staff (Efímero)
        await interaction.followup.send(f"✅ Has registrado existosamente el **{tipo.name}** a {usuario.mention}.", ephemeral=True)

        # 4. Enviar DM al Usuario
        embed_dm = discord.Embed(
            title="⚠️ HAS RECIBIDO UNA SANCIÓN",
            description=f"Hola {usuario.name}, has sido advertido/sancionado en **{interaction.guild.name}**.",
            color=discord.Color.dark_red()
        )
        embed_dm.add_field(name="Nivel de Castigo aplicado", value=tipo.name, inline=True)
        embed_dm.add_field(name="Motivo exacto", value=razon, inline=False)
        embed_dm.add_field(name="📷 Evidencia / Prueba", value=f"[Ver evidencia de la sanción]({prueba})", inline=False)
        embed_dm.add_field(name="Comprobante / Registro Público", value=f"[🔗 Haz clic aquí para ver tu sanción en el servidor]({link_al_mensaje})", inline=False)
        
        # El aviso extra para prevenir abusos
        aviso_importante = (
            "Recuerda que estas son acumulativas. Mantén una buena conducta.\n"
            "> 🔸 Si acumulas más de **3 WARNS**, pasarás a recibir una **Sanción**.\n"
            "> 🛑 Si acumulas más de **3 Sanciones**, se te aplicará un **BAN TEMPORAL**."
        )
        embed_dm.add_field(name="🛑 INFORMACIÓN IMPORTANTE", value=aviso_importante, inline=False)
        
        if interaction.guild.icon:
            embed_dm.set_thumbnail(url=interaction.guild.icon.url)
        embed_dm.set_footer(text="Derechos de Autor: Smile")

        try:
            await usuario.send(embed=embed_dm)
        except discord.Forbidden:
            pass # Si el usuario tiene los DMs bloqueados, esto evita que el bot crashee.

        # 5. Log exclusivo visible para los Administradores
        canal_logs = interaction.guild.get_channel(CANAL_LOGS_SANCION)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro de Sistema - Nueva Sanción",
                color=discord.Color.yellow(),
                timestamp=interaction.created_at
            )
            embed_log.add_field(name="Moderador/Admin", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            embed_log.add_field(name="Usuario Sancionado", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
            embed_log.add_field(name="Tipo Asignado", value=tipo.name, inline=True)
            embed_log.add_field(name="Razón Dictada", value=f"```{razon}```", inline=False)
            embed_log.add_field(name="Evidencia Adjuntada", value=prueba, inline=False)
            embed_log.set_thumbnail(url=usuario.display_avatar.url)
            embed_log.set_footer(text="Derechos de Autor: Smile")

            await canal_logs.send(embed=embed_log)

    @app_commands.command(name="advertir", description="Advierte a un usuario de nivel 1 al 4 (sin rol, solo registro).")
    @app_commands.describe(
        usuario="El usuario que recibirá la advertencia",
        nivel="El nivel de advertencia a aplicar",
        razon="El motivo de la advertencia",
        prueba="Enlace o link de la prueba"
    )
    @app_commands.choices(nivel=[
        app_commands.Choice(name="Advertencia 1", value="adv_1"),
        app_commands.Choice(name="Advertencia 2", value="adv_2"),
        app_commands.Choice(name="Advertencia 3", value="adv_3"),
        app_commands.Choice(name="Advertencia 4", value="adv_4")
    ])
    async def advertir(self, interaction: discord.Interaction, usuario: discord.Member, nivel: app_commands.Choice[str], razon: str, prueba: str):
        tiene_permiso = any(role.id in ROLES_PERMITIDOS for role in interaction.user.roles)
        if not tiene_permiso and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso Denegado",
                description="No tienes los permisos o el rango necesario para gestionar advertencias.",
                color=discord.Color.red()
            )
            embed_error.set_footer(text="Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        if interaction.channel_id != CANAL_SANCIONES:
            embed_error = discord.Embed(
                title="🚫 Canal Incorrecto",
                description=f"Este comando no se puede usar aquí.\nDirígete al canal designado: <#{CANAL_SANCIONES}> para aplicar advertencias.",
                color=discord.Color.dark_red()
            )
            embed_error.set_footer(text="Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM sanciones WHERE usuario_id = %s AND tipo = %s', (usuario.id, nivel.value))
        existe = cursor.fetchone()
        
        if existe:
            conn.close()
            embed_dup = discord.Embed(
                title="⚠️ Advertencia Duplicada",
                description=f"El usuario {usuario.mention} ya cuenta con **{nivel.name}** en el historial.",
                color=discord.Color.orange()
            )
            embed_dup.set_footer(text="Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_dup, ephemeral=True)

        cursor.execute('INSERT INTO sanciones (usuario_id, tipo, razon, prueba) VALUES (%s, %s, %s, %s)', (usuario.id, nivel.value, razon, prueba))
        conn.commit()
        conn.close()

        embed_canal = discord.Embed(
            title="⚠️ NUEVA ADVERTENCIA REGISTRADA",
            description=f"Se ha dictaminado una nueva advertencia a un miembro.",
            color=discord.Color.orange()
        )
        embed_canal.add_field(name="🙎‍♂️ Usuario:", value=usuario.mention, inline=True)
        embed_canal.add_field(name="🛑 Nivel:", value=f"**{nivel.name}**", inline=True)
        embed_canal.add_field(name="📄 Motivo:", value=f"```\n{razon}\n```", inline=False)
        embed_canal.add_field(name="🔗 Prueba:", value=f"[Ver evidencia]({prueba})", inline=False)
        embed_canal.add_field(name="🛡️ Moderador:", value=interaction.user.mention, inline=False)
        embed_canal.set_thumbnail(url=usuario.display_avatar.url if usuario.display_avatar else interaction.guild.icon.url)
        embed_canal.set_footer(text="Derechos de Autor: Smile")

        mensaje_adv = await interaction.channel.send(embed=embed_canal)
        
        await interaction.followup.send(f"✅ Has registrado existosamente la **{nivel.name}** a {usuario.mention}.", ephemeral=True)

        embed_dm = discord.Embed(
            title="⚠️ HAS RECIBIDO UNA ADVERTENCIA",
            description=f"Hola {usuario.name}, has sido advertido en **{interaction.guild.name}**.",
            color=discord.Color.gold()
        )
        embed_dm.add_field(name="Nivel", value=nivel.name, inline=True)
        embed_dm.add_field(name="Motivo", value=razon, inline=False)
        embed_dm.add_field(name="📷 Evidencia", value=f"[Ver evidencia]({prueba})", inline=False)
        embed_dm.set_footer(text="Recuerda mantener un buen comportamiento.")
        
        if interaction.guild.icon:
            embed_dm.set_thumbnail(url=interaction.guild.icon.url)

        try:
            await usuario.send(embed=embed_dm)
        except discord.Forbidden:
            pass 

        canal_logs = interaction.guild.get_channel(CANAL_LOGS_SANCION)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro - Nueva Advertencia",
                color=discord.Color.orange(),
                timestamp=interaction.created_at
            )
            embed_log.add_field(name="Moderador/Admin", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            embed_log.add_field(name="Usuario", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
            embed_log.add_field(name="Nivel", value=nivel.name, inline=True)
            embed_log.add_field(name="Motivo", value=f"```{razon}```", inline=False)
            embed_log.set_thumbnail(url=usuario.display_avatar.url)
            await canal_logs.send(embed=embed_log)

async def setup(bot):
    await bot.add_cog(Sancionar(bot))
