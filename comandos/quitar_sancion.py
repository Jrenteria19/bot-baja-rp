import discord
from discord.ext import commands
from discord import app_commands
from db_connect import get_db_connection

CANAL_SANCIONES = 1481747742475944137
CANAL_LOGS_SANCION = 1501012505785532549

# Roles que pueden usar los comandos de sanciones
ROLES_PERMITIDOS = [
    1481747742047994023
]

# Mapeo de valores de sanciones a IDs de roles
TIPOS_SANCION = {
    "sancion_1": {"id": 1481747741561458845, "nombre": "Sancion 1"},
    "sancion_2": {"id": 1481747741561458844, "nombre": "Sancion 2"},
    "sancion_3": {"id": 1481747741561458843, "nombre": "Sancion 3"},
}

class QuitarSancion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="remover-sancion", description="Elimina una sanción, warn o strike de un usuario.")
    @app_commands.describe(
        usuario="Usuario al que se le quitará la sanción/warn",
        tipo="Tipo de castigo a eliminar"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Advertencia 1", value="adv_1"),
        app_commands.Choice(name="Advertencia 2", value="adv_2"),
        app_commands.Choice(name="Advertencia 3", value="adv_3"),
        app_commands.Choice(name="Advertencia 4", value="adv_4"),
        app_commands.Choice(name="Sanción 1", value="sancion_1"),
        app_commands.Choice(name="Sanción 2", value="sancion_2"),
        app_commands.Choice(name="Sanción 3", value="sancion_3"),
    ])
    async def remover_sancion(self, interaction: discord.Interaction, usuario: discord.Member, tipo: app_commands.Choice[str]):
        
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
        
        # Validar Canal Permitido
        if interaction.channel_id != CANAL_SANCIONES:
            embed_error = discord.Embed(
                title="🚫 Canal Incorrecto",
                description=f"Este comando no se puede usar aquí.\nDirígete al canal designado: <#{CANAL_SANCIONES}> para gestionar sanciones.",
                color=discord.Color.dark_red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
            embed_error.set_footer(text="Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        
        # Base de Datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si esa sancion existe en la base de datos
        cursor.execute('SELECT 1 FROM sanciones WHERE usuario_id = %s AND tipo = %s', (usuario.id, tipo.value))
        existe = cursor.fetchone()
        
        if not existe:
            conn.close()
            embed_no_existe = discord.Embed(
                title="❌ No Encontrado",
                description=f"El usuario {usuario.mention} no tiene registrado el castigo **{tipo.name}** en la base de datos.",
                color=discord.Color.red()
            )
            embed_no_existe.set_footer(text="Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_no_existe, ephemeral=True)
        
        # Eliminar de la base de datos
        cursor.execute('DELETE FROM sanciones WHERE usuario_id = %s AND tipo = %s', (usuario.id, tipo.value))
        conn.commit()
        conn.close()
        
        # Quitar el rol en Discord
        rol_removido = False
        if tipo.value in TIPOS_SANCION:
            rol_id = TIPOS_SANCION[tipo.value]["id"]
            rol_obj = interaction.guild.get_role(rol_id)
            
            if rol_obj and rol_obj in usuario.roles:
                try:
                    await usuario.remove_roles(rol_obj, reason=f"Sanción perdonada/removida por {interaction.user.name}")
                    rol_removido = True
                except discord.Forbidden:
                    pass # Ignorar si falta jerarquía para quitar roles
                
        # Embed de éxito efímero
        embed_exito = discord.Embed(
            title="✅ Sanción Removida",
            description=f"Se le ha removido satisfactoriamente el castigo de **{tipo.name}** a {usuario.mention} de la base de datos.",
            color=discord.Color.green()
        )
        if rol_removido:
            embed_exito.description += f"\nTambién se le ha quitado el rol de Discord asociado."
            
        embed_exito.set_thumbnail(url=usuario.display_avatar.url)
        embed_exito.set_footer(text="Derechos de Autor: Smile")
        
        await interaction.followup.send(embed=embed_exito, ephemeral=True)
        
        # Anuncio público en el Canal de Sanciones
        embed_publico = discord.Embed(
            title="🕊️ SANCIÓN REMOVIDA",
            description=f"Se ha perdonado/removido un castigo del historial a un miembro de la comunidad.",
            color=discord.Color.green()
        )
        embed_publico.add_field(name="🙎‍♂️ Usuario Perdonado:", value=usuario.mention, inline=True)
        embed_publico.add_field(name="🛑 Castigo Removido:", value=f"**{tipo.name}**", inline=True)
        embed_publico.add_field(name="🛡️ Moderador:", value=interaction.user.mention, inline=False)
        embed_publico.set_thumbnail(url=usuario.display_avatar.url if usuario.display_avatar else interaction.guild.icon.url)
        embed_publico.set_footer(text="Derechos de Autor: Smile")
        
        await interaction.channel.send(embed=embed_publico)
        
        # Generar un Log Público para los Admins
        canal_logs = interaction.guild.get_channel(CANAL_LOGS_SANCION)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro de Sistema - Sanción Removida",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            embed_log.add_field(name="Moderador/Admin", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            embed_log.add_field(name="Usuario Perdonado", value=f"{usuario.mention} (`{usuario.id}`)", inline=True)
            embed_log.add_field(name="Tipo Removido", value=f"**{tipo.name}**", inline=True)
            embed_log.set_thumbnail(url=usuario.display_avatar.url)
            embed_log.set_footer(text="Derechos de Autor: Smile")
            
            await canal_logs.send(embed=embed_log)

        # Enviar DM al usuario perdonado
        embed_dm_perdonado = discord.Embed(
            title="🕊️ SANCIÓN REMOVIDA EN BAJA RP",
            description=f"Hola {usuario.name}, un administrador ha revisado tu historial y te ha retirado un castigo.\n\n"
                        f"**Castigo Removido:** {tipo.name}\n"
                        f"**Administrador:** {interaction.user.mention}\n\n"
                        "Agradecemos tu buen comportamiento. ¡Sigue disfrutando de la comunidad!",
            color=discord.Color.brand_green()
        )
        if interaction.guild and interaction.guild.icon:
            embed_dm_perdonado.set_thumbnail(url=interaction.guild.icon.url)
        embed_dm_perdonado.set_footer(text="Derechos de Autor: Smile")

        try:
            await usuario.send(embed=embed_dm_perdonado)
        except discord.Forbidden:
            pass # Si el usuario tiene los DMs bloqueados, no falla el bot


async def setup(bot):
    await bot.add_cog(QuitarSancion(bot))
