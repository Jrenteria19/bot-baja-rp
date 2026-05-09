import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime

CANAL_PANEL_TICKETS = 1481747742475944136
CANAL_LOGS_TICKETS = 1501012124669972550
CANAL_CALIFICAR_STAFF = 1481747743230656570

# Roles con acceso visual a todos los tickets creados
ROLES_STAFF_TICKETS = [
    1501010943239258322, 1481747742047994023
]

# Mapeo de Categorías (ID de Categorías en Discord)
CATEGORIAS = {
    "general": {"nombre": "Soporte General", "id": 1501022888151617588, "emoji": "🎫", "desc": "Resuelve dudas del servidor o cualquier tema general."},
    "reportes": {"nombre": "Reportes", "id": 1501022982552813588, "emoji": "🚨", "desc": "Reporta problemas, usuarios o facciones al staff."},
    "apelaciones": {"nombre": "Apelaciones", "id": 1501023102891593879, "emoji": "⚖️", "desc": "Apela sanciones o baneos injustos con pruebas."},
    "reportar_staff": {"nombre": "Reportar Staff", "id": 1501023271511134218, "emoji": "🛡️", "desc": "Reporta irregularidades de un miembro de administración."},
    "ck": {"nombre": "Solicitar CK", "id": 1501023446879043585, "emoji": "☠️", "desc": "Solicita la muerte de tu personaje (CK) o la de otro."},
    "problemas_bot": {"nombre": "Problemas de bot/web", "id": 1501023582854185140, "emoji": "💻", "desc": "Contacta desarrollo por fallos o dudas de Bot/Web."},
    "compras": {"nombre": "Compras", "id": 1501023719772913734, "emoji": "🛒", "desc": "Recibe beneficios de tus compras VIP o donaciones."},
    "roleplay": {"nombre": "Roleplay", "id": 1501023816518864966, "emoji": "🎭", "desc": "Reclama botines de robo o soporte de moderación IC."},
    "sugerencias": {"nombre": "Sugerencias", "id": 1501023948681379840, "emoji": "💡", "desc": "Sugiere ideas para el servidor, bot o web."}
}

# ----------------- MODAL DE CREACIÓN -----------------
class TicketModal(discord.ui.Modal):
    def __init__(self, categoria_key):
        self.categoria_key = categoria_key
        info = CATEGORIAS[categoria_key]
        super().__init__(title=f"Apertura: {info['nombre']}", custom_id=f"modal_ticket_{categoria_key}")

        if categoria_key == "reporte_staff":
            self.asunto = discord.ui.TextInput(
                label="Caso por el que se le reporta",
                style=discord.TextStyle.short,
                placeholder="Ej: Abuso de poder, Anti-rol...",
                required=True,
                max_length=150
            )
            self.staff_acusado = discord.ui.TextInput(
                label="Staff al que reportas",
                style=discord.TextStyle.short,
                placeholder="Discord ID o Nombre del Staff",
                required=True,
                max_length=100
            )
            self.descripcion = discord.ui.TextInput(
                label="Descripción del caso",
                style=discord.TextStyle.paragraph,
                placeholder="Explica qué pasó de forma clara y directa.",
                required=True,
                max_length=1500
            )
            self.add_item(self.asunto)
            self.add_item(self.staff_acusado)
            self.add_item(self.descripcion)
        else:
            self.asunto = discord.ui.TextInput(
                label="Asunto a tratar",
                style=discord.TextStyle.short,
                placeholder="Menciona el asunto principal de tu ticket.",
                required=True,
                max_length=150
            )
            self.descripcion = discord.ui.TextInput(
                label="Descripción del asunto",
                style=discord.TextStyle.paragraph,
                placeholder="Explica detalladamente tu problemática o necesidad.",
                required=True,
                max_length=1500
            )
            self.add_item(self.asunto)
            self.add_item(self.descripcion)
            self.staff_acusado = None

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        info = CATEGORIAS[self.categoria_key]
        
        nombre_usuario = interaction.user.name.lower().replace(" ", "-")
        channel_name = f"ticket-{self.categoria_key}-{nombre_usuario}"

        category_obj = interaction.guild.get_channel(info["id"])
        
        if not category_obj:
            return await interaction.followup.send(f"❌ Error Crítico: No se encontró la categoría de Discord (ID: {info['id']}). Revisa la configuración.", ephemeral=True)

        # 1. Validación de seguridad: Limitar a 1 ticket activo por categoría
        for ch in category_obj.channels:
            if ch.name == channel_name:
                return await interaction.followup.send(f"❌ Ya tienes un ticket abierto en esta sección: {ch.mention}.\n*Cierra ese antes de crear otro igual.*", ephemeral=True)

        # 2. Configuración de Permisos Base
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False), # Nadie lo ve general
            interaction.user: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, attach_files=True, read_message_history=True), # El creador lo ve
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True, manage_channels=True, manage_messages=True) # El bot lo ve
        }

        # Iterar y dar permiso explícito de visión y escritura a los roles del Staff
        for rol_id in ROLES_STAFF_TICKETS:
            rol_staff = interaction.guild.get_role(rol_id)
            if rol_staff:
                overwrites[rol_staff] = discord.PermissionOverwrite(
                    view_channel=True, 
                    read_messages=True, 
                    send_messages=True, 
                    attach_files=True, 
                    read_message_history=True
                )

        # 3. Crear el Canal en su Categoría
        try:
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category_obj,
                overwrites=overwrites,
                reason=f"Ticket Creado por {interaction.user.name} - Categoría: {info['nombre']}"
            )
        except Exception as e:
            return await interaction.followup.send(f"❌ Error al crear el canal: {e}", ephemeral=True)

        # 4. Mensaje Principal Fijado del Ticket (Atractivo)
        detalles_texto = f"**📖 ASUNTO:** `{self.asunto.value}`\n"
        if self.categoria_key == "reporte_staff" and self.staff_acusado:
            detalles_texto += f"**👮 STAFF ACUSADO:** `{self.staff_acusado.value}`\n"
        detalles_texto += f"**📝 DESCRIPCIÓN:**\n```{self.descripcion.value}```\n\n"

        embed_ticket = discord.Embed(
            title=f"{info['emoji']} {info['nombre'].upper()} - EL SERVIDOR",
            description=f"Hola {interaction.user.mention},\n\n"
                        f"El equipo administrativo revisará tu caso pronto. Mientras tanto, prepárate para ser atendido.\n\n"
                        f"{detalles_texto}"
                        f"⏱️ **Tiempo de Respuesta:** Entre `1h a 2d`. Si superó las `8h`, puedes etiquetar al Staff.\n"
                        f"⚠️ **ADVERTENCIA:** Sube tus pruebas (imágenes, videos, links) a este canal **AHORA MISMO**. Tu ticket debe contener pruebas contundentes que sustenten la problemática o de lo contrario, no podremos ayudarte y será cerrado de inmediato.",
            color=discord.Color.blue()
        )
        embed_ticket.set_thumbnail(url=interaction.user.display_avatar.url)
        embed_ticket.set_footer(text="Centro de Atención Ciudadana | EL SERVIDOR")
        
        # Campo invisible (para almacenar internamente la ID del creador)
        embed_ticket.add_field(name="\u200b", value=f"ID_CREADOR:{interaction.user.id}", inline=False)

        # Enviar mensaje que pinnearemos y que tiene los botones
        mensaje_ticket = await ticket_channel.send(content=f"👋 ¡Atención <@&1501010943239258322>! Un nuevo caso ha sido abierto por {interaction.user.mention}.", embed=embed_ticket, view=ControlTicketView())
        
        try:
            await mensaje_ticket.pin()
            # Ocultamos el mensaje del sistema de "bot ha fijado un mensaje"
            async for msg in ticket_channel.history(limit=5):
                if msg.type == discord.MessageType.pins_add:
                    await msg.delete()
        except:
            pass # Si no tiene permiso de fijar, continúa

        # 5. Respuesta Efímera
        await interaction.followup.send(f"✅ ¡Tu formulario fue enviado y el ticket fue creado! Dirígete a: {ticket_channel.mention}", ephemeral=True)


# ----------------- BOTONES DE CONTROL DE TICKETS -----------------
class AgregarPersonaModal(discord.ui.Modal, title="Agregar Participante al Ticket"):
    usuario_input = discord.ui.TextInput(
        label="ID o Nombre Exacto del Usuario",
        style=discord.TextStyle.short,
        placeholder="Ej: 123456789012345678 o juanito123",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        valor = self.usuario_input.value.strip()
        miembro = None
        
        # 1. Intentar buscar por ID numérica
        if valor.isdigit():
            miembro = interaction.guild.get_member(int(valor))
            if not miembro:
                try:
                    miembro = await interaction.guild.fetch_member(int(valor))
                except:
                    pass
        
        # 2. Intentar buscar por nombre o apodo si no se encontró por ID
        if not miembro:
            miembro = discord.utils.find(lambda m: m.name.lower() == valor.lower() or m.display_name.lower() == valor.lower() or str(m.id) == valor, interaction.guild.members)
            
        if not miembro:
            return await interaction.followup.send(f"❌ No pude encontrar a ningún usuario en el servidor llamado o con la ID: `{valor}`. Asegúrate de intentar buscarlo por su ID númerica para ser exactos.", ephemeral=True)
            
        # 3. Dar permisos en el canal a ese miembro
        try:
            await interaction.channel.set_permissions(miembro, view_channel=True, read_messages=True, send_messages=True, attach_files=True, read_message_history=True)
            # Acusar públicamente en el ticket que fue agregado
            await interaction.channel.send(f"✅ **{interaction.user.mention}** ha autorizado y añadido a **{miembro.mention}** a este ticket.")
            # Cerrar el modal con éxito
            await interaction.followup.send(f"✅ El usuario {miembro.mention} puede ver y mensajear en este ticket ahora.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ocurrió un error al darle acceso al usuario: {e}", ephemeral=True)


class ControlTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.success, emoji="🙋‍♂️", custom_id="btn_reclamar_ticket_admin")
    async def btn_reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Permitir solo a los que tienen permiso de Banear o Administrar (Para proteger que un usuario no pueda reclamar su propio ticket)
        if not interaction.user.guild_permissions.ban_members and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Acción restringida al Cuerpo Administrativo.", ephemeral=True)

        # 1. Actualizar el botón
        button.disabled = True
        button.label = f"Reclamado por {interaction.user.name}"
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(f"✅ Has reclamado este ticket exitosamente.", ephemeral=True)

        # 2. Extraer Creador iterando los permisos del canal para mayor fiabilidad
        try:
            creador = None
            for target, overwrite in interaction.channel.overwrites.items():
                if isinstance(target, discord.Member) and not target.bot:
                    if target.id not in ROLES_STAFF_TICKETS: # Confirmamos que no es un rol de staff agregado como miembro o algo raro
                        creador = target
                        break

            if creador:
                embed_dm = discord.Embed(
                    title="🙋‍♂️ TICKET RECLAMADO",
                    description=f"Hola {creador.name},\n\nTu ticket en el canal **#{interaction.channel.name}** ha sido reclamado y está siendo atendido por **{interaction.user.mention}**.\n\n*Por favor, mantente atento al canal, puede que ya hayas recibido respuesta.*",
                    color=discord.Color.green()
                )
                await creador.send(embed=embed_dm)
        except Exception as e:
            print(f"Error reclamar ticket: {e}")
            pass # Falla silenciosa si no localiza el id o manda DMs cerrados

    @discord.ui.button(label="Añadir un Usuario", style=discord.ButtonStyle.primary, emoji="➕", custom_id="btn_agregar_persona_admin")
    async def btn_agregar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Permitir solo a los que tienen permiso (Staff)
        if not interaction.user.guild_permissions.ban_members and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Acción restringida al Cuerpo Administrativo.", ephemeral=True)
        
        # Abrir el modal para escribir el nombre/ID
        await interaction.response.send_modal(AgregarPersonaModal())

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_cerrar_ticket_admin")
    async def btn_cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ Acción restringida al Cuerpo Administrativo.", ephemeral=True)

        # 1. Mandar advertencia PÚBLICA de cerrado (no efímero)
        embed_cierre = discord.Embed(
            title="🔒 CERRANDO TICKET...",
            description="Este canal será completamente eliminado y purgado de la base de datos en **5 segundos**. Gracias por usar el soporte gubernamental.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed_cierre, ephemeral=False)

        # Extraemos ID del creador leyendo los permisos directos que el bot le dio al crear el canal
        user_id = None
        for target, overwrite in interaction.channel.overwrites.items():
            if isinstance(target, discord.Member) and not target.bot:
                if target.id not in ROLES_STAFF_TICKETS:
                    user_id = target.id
                    break

        # Esperamos 5 segs
        await asyncio.sleep(5)
        
        canal_nombre = interaction.channel.name
        
        # Eliminar
        try:
            await interaction.channel.delete()
        except discord.NotFound:
            return

        # 2. Notificaciones Pos-Eliminación (DMs al Usuario)
        if user_id:
            creador = interaction.guild.get_member(user_id)
            if creador:
                embed_dm = discord.Embed(
                    title="🔒 TICKET FINALIZADO",
                    description=f"Hola {creador.name},\nTu sesión de soporte para el caso **{canal_nombre}** ha concluido y fue cerrada por la Administración de EL SERVIDOR.\n\n"
                                f"⭐⭐⭐⭐⭐\n"
                                f"**¡Tú opinión es clave para el proyecto!**\n"
                                f"Nos encantaría que nos dieras feedback. Dirígete a <#{CANAL_CALIFICAR_STAFF}> y utiliza el comando `/calificar-staff` para evaluar la atención del oficial que te ayudó.",
                    color=discord.Color.gold()
                )
                try:
                    await creador.send(embed=embed_dm)
                except discord.Forbidden:
                    pass

            # 3. Guardar en Sistema de Logs Administrativos
            canal_logs = interaction.guild.get_channel(CANAL_LOGS_TICKETS)
            if canal_logs:
                embed_log = discord.Embed(
                    title="📝 Auditoría | Cierre de Ticket",
                    description=f"**Canal Eliminado:** `#{canal_nombre}`\n"
                                f"**Oficial a Cargo (Cierre):** {interaction.user.mention}\n"
                                f"**Ciudadano Creador:** <@{user_id}>",
                    color=discord.Color.dark_grey(),
                    timestamp=interaction.created_at
                )
                await canal_logs.send(embed=embed_log)


# ----------------- DROPDOWN DEL PANEL PRINCIPAL -----------------
class TicketsDropdown(discord.ui.Select):
    def __init__(self):
        opciones = [
            discord.SelectOption(label=info["nombre"], emoji=info["emoji"], value=key, description=info.get("desc"))
            for key, info in CATEGORIAS.items()
        ]
        super().__init__(placeholder="Selecciona el área de soporte que necesitas...", min_values=1, max_values=1, options=opciones, custom_id="select_tickets_v3")

    async def callback(self, interaction: discord.Interaction):
        # 1. Al clickear, no respondemos con defer, respondemos enviando el Modal para recolectar información.
        categoria_key = self.values[0]
        await interaction.response.send_modal(TicketModal(categoria_key))


# ----------------- COG PRINCIPAL -----------------
class TicketsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketsDropdown())

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketsView())
        self.bot.add_view(ControlTicketView())

    @app_commands.command(name="panel-tickets", description="🎫 [ADMIN] Despliega el Centro interactivo de Soporte (Tickets).")
    async def panel_tickets(self, interaction: discord.Interaction):
        # 1. Validación de Canal
        if interaction.channel_id != CANAL_PANEL_TICKETS:
            return await interaction.response.send_message(f"❌ Panel Restringido. El sistema de tickets debe instalarse únicamente en <#{CANAL_PANEL_TICKETS}>.", ephemeral=True)

        # 2. Validación de Permisos de Administrador
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ **Acceso Denegado:** Solo la Alta Administración tiene permisos para purgar e instalar paneles de interacción.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # 3. Purgar el Canal (Borrar limpieza anterior)
        try:
            await interaction.channel.purge(limit=50) # Borramos los últimos 50 mensajes para instalar el panel limpio
        except discord.Forbidden:
            return await interaction.followup.send("⚠️ El Bot no cuenta con los permisos de 'Gestionar Mensajes' e 'Historial' para purgar este canal. Añade los permisos en los ajustes del canal.", ephemeral=True)

        # 4. Formatear y construir el Embed Atractivo solicitado
        embed = discord.Embed(
            title=f"Sistemas de Tickets de {interaction.guild.name}",
            description="¿Necesitas ayuda o tienes una duda/problema?\n**Abre un ticket y los miembros del staff te ayudarán.**\n\nDespliega el menú interactivo para contactar con el departamento correspondiente.",
            color=discord.Color.from_rgb(0, 102, 255) # Azul Vivo Atractivo
        )
        
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        else:
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3242/3242257.png")
        
        embed.add_field(
            name="⸺ 🎫 Importante",
            value="El soporte de staff puede tardar entre **1h a 2d** en atenderte, se paciente, hacemos las cosas lo más rápido posible.\n\n"
                  "👉 *Si no has sido atendido o no has obtenido respuesta en **8h** puedes etiquetarnos sin problema.*",
            inline=False
        )
        
        embed.add_field(
            name="⸺ ⚠️ Normativas de Infracción",
            value=(
                "🔸 **Apertura sin Pruebas:** Recuerda que abrir un ticket sin las debidas pruebas o motivos, **será acto de una sanción o hasta un baneo**.\n"
                "🔸 **Límites:** Solo se permite abrir **1 ticket por categoría**.\n"
                "🔸 **Dudas Minúsculas:** Abrir tickets por cosas obvias o que se resuelven en Rol está prohibido.\n"
                "🔸 **Tickets Vacíos:** Abrir el ticket sin explicar ni decir nada, **será sancionado** directamente por la administración."
            ),
            inline=False
        )
        
        embed.set_footer(text="Derechos de Autor: Smile | la comunidad")

        # 5. Desplegar
        await interaction.channel.send(embed=embed, view=TicketsView())
        
        await interaction.followup.send("✅ La limpieza se completó y el panel interactivo fue instalado exitosamente.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
