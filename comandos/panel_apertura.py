import discord
from discord.ext import commands
from discord import app_commands

class BotonesApertura(discord.ui.View):
    def __init__(self):
        # timeout=None hace que los botones sean permanentes.
        super().__init__(timeout=None)

    @discord.ui.button(label="🔓 Abrir Servidor", style=discord.ButtonStyle.success, custom_id="btn_abrir_servidor")
    async def btn_abrir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        # Verificar si el usuario que presionó tiene permiso de administrador o el rol permitido
        ROLES_PERMITIDOS = [1481747742047994023]
        tiene_rol = any(role.id in ROLES_PERMITIDOS for role in interaction.user.roles)
        
        if not interaction.user.guild_permissions.administrator and not tiene_rol:
            roles_mencion = " o ".join([f"<@&{r}>" for r in ROLES_PERMITIDOS])
            embed_error = discord.Embed(
                title="⛔ Acceso Denegado",
                description=(
                    "No tienes los permisos necesarios para interactuar con este panel.\n\n"
                    f"Necesitas: {roles_mencion} o permisos de Administrador."
                ),
                color=discord.Color.red()
            )
            embed_error.set_footer(text="Seguridad el servidor — Derechos de Autor: Smile")
            if interaction.guild and interaction.guild.icon:
                embed_error.set_thumbnail(url=interaction.guild.icon.url)
            return await interaction.followup.send(embed=embed_error, ephemeral=True)
            
        # Mensaje de Apertura
        guild_name = interaction.guild.name if interaction.guild else "la comunidad"
        descripcion_apertura = (
            f"El servidor de **{guild_name}** ha sido abierto por {interaction.user.mention}\n\n"
            "**MODOS DE ACCESO AL SERVIDOR:**\n\n"
            "**Método 1:**\n"
            f"> Entra al juego de Emergency Response: Liberty County. Abre el menú, ve a la pestaña de 'Servidores Listados' y busca: **{guild_name}**\n\n"
            "**Método 2:**\n"
            "> En el mismo menú del juego, ve a 'Servidor por código' e introduce el código: **BAJARP**\n\n"
            "**Método 3:**\n"
            "> Haz clic directamente en el siguiente enlace para unirte automáticamente:\n"
            "> [🔗 Unirse vía Enlace](https://policeroleplay.community/join?code=BAJARP)"
        )

        embed_abrir = discord.Embed(
            title="✅ ¡SERVIDOR ABIERTO!",
            description=descripcion_apertura,
            color=discord.Color.green()
        )
        if interaction.guild and interaction.guild.icon:
            embed_abrir.set_thumbnail(url=interaction.guild.icon.url)
        embed_abrir.set_image(url="attachment://abierto.gif")
        embed_abrir.set_footer(text="Derechos de Autor: Smile")

        # Obtenemos el canal de anuncios
        canal_anuncios = interaction.guild.get_channel(1481747742698246258)
        if canal_anuncios:
            try:
                await canal_anuncios.purge(limit=100) # Purga hasta los últimos 100 mensajes en el canal
                purgado = True
            except discord.Forbidden:
                purgado = False

            img_file = discord.File(r"c:\Users\junio\OneDrive\Escritorio\BOT-BAJARP\public\imagenes\abierto.gif", filename="abierto.gif")
            mensaje_anuncio = await canal_anuncios.send(content="@everyone", file=img_file, embed=embed_abrir)
            
            # Reacciones que forman "BAJA RP" (Aproximación con emojis permitidos)
            emojis_baja_rp = ["🅱️", "🇦", "🇯", "🅰️", "🇷", "🅿️"]
            for emoji in emojis_baja_rp:
                try:
                    await mensaje_anuncio.add_reaction(emoji)
                except Exception:
                    pass
            
            if purgado:
                await interaction.followup.send("✅ El canal fue limpiado, el anuncio de apertura fue enviado correctamente y se añadieron las reacciones.", ephemeral=True)
            else:
                await interaction.followup.send("✅ El anuncio fue enviado con reacciones, pero **no pude limpiar el canal** (Me faltan permisos de 'Gestionar mensajes' o 'Leer historial').", ephemeral=True)
        else:
            await interaction.followup.send("❌ Error: No se encontró el canal de anuncios configurado.", ephemeral=True)

        # Enviamos el log de apertura
        canal_logs = interaction.guild.get_channel(1501018257568825395)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro de Sistema - Apertura",
                description=f"**Acción:** El servidor fue **ABIERTO**.\n**Ejecutado por:** {interaction.user.mention} (`{interaction.user.id}`)",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            embed_log.set_thumbnail(url=interaction.user.display_avatar.url)
            embed_log.set_footer(text="Derechos de Autor: Smile")
            await canal_logs.send(embed=embed_log)

    @discord.ui.button(label="🔒 Cerrar Servidor", style=discord.ButtonStyle.danger, custom_id="btn_cerrar_servidor")
    async def btn_cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar si el usuario que presionó tiene permiso de administrador o el rol permitido
        ROLES_PERMITIDOS = [1481747742047994023]
        tiene_rol = any(role.id in ROLES_PERMITIDOS for role in interaction.user.roles)
        
        if not interaction.user.guild_permissions.administrator and not tiene_rol:
            roles_mencion = " o ".join([f"<@&{r}>" for r in ROLES_PERMITIDOS])
            embed_error = discord.Embed(
                title="⛔ Acceso Denegado",
                description=(
                    "No tienes los permisos necesarios para interactuar con este panel.\n\n"
                    f"Necesitas: {roles_mencion} o permisos de Administrador."
                ),
                color=discord.Color.red()
            )
            embed_error.set_footer(text="Seguridad el servidor — Derechos de Autor: Smile")
            if interaction.guild and interaction.guild.icon:
                embed_error.set_thumbnail(url=interaction.guild.icon.url)
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)
            
        # Abrimos el Modal para pedir la razón (Validado para que no pongan cualquier cosa)
        await interaction.response.send_modal(CierreModal())


class CierreModal(discord.ui.Modal, title="Motivo del Cierre"):
    razon = discord.ui.TextInput(
        label="¿Por qué se cierra el servidor?",
        style=discord.TextStyle.paragraph,
        placeholder="Ej: Mantenimiento programado, fin de la sesión de rol...",
        required=True,
        min_length=15,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Mensaje de Cierre
        guild_name = interaction.guild.name if interaction.guild else "la comunidad"
        embed_cerrar = discord.Embed(
            title="🛑 ¡SERVIDOR CERRADO!",
            description=f"El servidor de **{guild_name}** ha sido cerrado por {interaction.user.mention}\n\n**📝 Motivo:**\n```{self.razon.value}```\nPor favor, manténganse atentos a próximos avisos.",
            color=discord.Color.red()
        )
        if interaction.guild and interaction.guild.icon:
            embed_cerrar.set_thumbnail(url=interaction.guild.icon.url)
        embed_cerrar.set_image(url="attachment://cerrado.gif")
        embed_cerrar.set_footer(text="Derechos de Autor: Smile")

        # Obtenemos el canal de anuncios
        canal_anuncios = interaction.guild.get_channel(1481747742698246258)
        if canal_anuncios:
            try:
                await canal_anuncios.purge(limit=100)
                purgado = True
            except discord.Forbidden:
                purgado = False

            img_file = discord.File(r"c:\Users\junio\OneDrive\Escritorio\BOT-BAJARP\public\imagenes\cerrado.gif", filename="cerrado.gif")
            await canal_anuncios.send(content="@here", file=img_file, embed=embed_cerrar)
            
            if purgado:
                await interaction.followup.send("✅ El canal fue limpiado y el anuncio de cierre fue enviado correctamente.", ephemeral=True)
            else:
                await interaction.followup.send("✅ El anuncio fue enviado, pero **no pude limpiar el canal** (Me faltan permisos de 'Gestionar mensajes' o 'Leer historial').", ephemeral=True)
        else:
            await interaction.followup.send("❌ Error: No se encontró el canal de anuncios configurado.", ephemeral=True)

        # Enviamos el log de cierre
        canal_logs = interaction.guild.get_channel(1501018257568825395)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro de Sistema - Cierre",
                description=f"**Acción:** El servidor fue **CERRADO**.\n**Ejecutado por:** {interaction.user.mention} (`{interaction.user.id}`)\n**Razón:** {self.razon.value}",
                color=discord.Color.red(),
                timestamp=interaction.created_at
            )
            embed_log.set_thumbnail(url=interaction.user.display_avatar.url)
            embed_log.set_footer(text="Derechos de Autor: Smile")
            await canal_logs.send(embed=embed_log)


class PanelApertura(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Esto registra la vista para que los botones funcionen incluso si el bot se reinicia.
        self.bot.add_view(BotonesApertura())

    @app_commands.command(name="panel_apertura", description="Despliega el panel de apertura y cierre del servidor.")
    async def panel_apertura(self, interaction: discord.Interaction):
        # 1. Validación de Roles/Permisos
        ROLES_PERMITIDOS = [1481747742047994023]
        tiene_rol = any(role.id in ROLES_PERMITIDOS for role in interaction.user.roles)
        
        if not interaction.user.guild_permissions.administrator and not tiene_rol:
            roles_mencion = " o ".join([f"<@&{r}>" for r in ROLES_PERMITIDOS])
            embed_no_rol = discord.Embed(
                title="❌ Requerimiento de Rango",
                description=(
                    "Para desplegar el panel de control, debes disponer del rango autorizado.\n\n"
                    f"🛡️ **Requerido:** {roles_mencion}\n"
                    "O poseer permisos de Administrador."
                ),
                color=discord.Color.red()
            )
            embed_no_rol.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/564/564619.png")
            embed_no_rol.set_footer(text="Control de Acceso — Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_no_rol, ephemeral=True)

        CANAL_PERMITIDO = 1501018093734854816
        
        # 2. Validación del Canal Permitido
        if interaction.channel_id != CANAL_PERMITIDO:
            embed_error = discord.Embed(
                title="🚫 ¡Te has equivocado de lugar!",
                description=f"Este comando no está permitido aquí.\nPor favor, dirígete al canal designado: <#{CANAL_PERMITIDO}> para ejecutar este panel.",
                color=discord.Color.dark_red()
            )
            embed_error.set_footer(text="Derechos de Autor: Smile")
            if interaction.guild and interaction.guild.icon:
                embed_error.set_thumbnail(url=interaction.guild.icon.url)
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # Si el canal es correcto, armamos el embed del Panel
        guild_name = interaction.guild.name if interaction.guild else "Servidor"
        embed_panel = discord.Embed(
            title=f"🎮 {guild_name} - Panel de Conexión",
            description=(
                "Bienvenidos al **Panel de Apertura / Cierre**.\n"
                "Desde aquí, la Administración informará a los usuarios sobre el estado del servidor.\n\n"
                "🔓 **Abrir Servidor**: Anuncia la apertura del servidor a la comunidad.\n"
                "🔒 **Cerrar Servidor**: Anuncia el cierre del servidor."
            ),
            color=discord.Color.dark_embed()
        )
        
        # Añade logo del server si existe en el entorno
        if interaction.guild and interaction.guild.icon:
            embed_panel.set_thumbnail(url=interaction.guild.icon.url)
            
        embed_panel.set_footer(text="Derechos de Autor: Smile")

        # Enviamos el embed incluyendo los BotonesApertura()
        await interaction.response.send_message(embed=embed_panel, view=BotonesApertura())


async def setup(bot):
    await bot.add_cog(PanelApertura(bot))
