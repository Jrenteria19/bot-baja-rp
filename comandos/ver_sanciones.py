import discord
from discord.ext import commands
from discord import app_commands
from db_connect import get_db_connection

CANAL_CONSULTAS = 1481747742953963716
ROL_PERMITIDO = 1481747742047994023

class ConsultarSanciones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ver-sanciones", description="Consulta las sanciones tuyas o de otro usuario en la base de datos.")
    @app_commands.describe(
        usuario="Usuario a consultar (si lo dejas vacío, verás tu propio historial)"
    )
    async def ver_sanciones(self, interaction: discord.Interaction, usuario: discord.Member = None):
        
        # 1. Validar el Canal Correcto
        if interaction.channel_id != CANAL_CONSULTAS:
            embed_error_canal = discord.Embed(
                title="🚫 Canal Incorrecto",
                description=f"Este comando no se puede usar aquí.\nPor favor, dirígete al canal designado: <#{CANAL_CONSULTAS}>.",
                color=discord.Color.dark_red()
            )
            embed_error_canal.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
            embed_error_canal.set_footer(text="Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error_canal, ephemeral=True)

        # 2. Validar el Rol Permitido
        tiene_rol = any(role.id == ROL_PERMITIDO for role in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error_rol = discord.Embed(
                title="⛔ Acceso Denegado",
                description="No tienes los permisos o el rol necesario para utilizar este comando de consulta.",
                color=discord.Color.red()
            )
            embed_error_rol.set_footer(text="Derechos de Autor: Smile")
            if interaction.guild and interaction.guild.icon:
                embed_error_rol.set_thumbnail(url=interaction.guild.icon.url)
            return await interaction.response.send_message(embed=embed_error_rol, ephemeral=True)

        # Usar Defer para consultas que puedan demorar unos segundos en bases de datos MySQL
        await interaction.response.defer(ephemeral=True)

        # Establecer a quién buscaremos en la DB
        objetivo = usuario if usuario is not None else interaction.user

        # 3. Consulta a la Base de Datos
        try:
            import psycopg2
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Traer todas las sanciones del usuario seleccionado
            cursor.execute('SELECT tipo, razon, prueba FROM sanciones WHERE usuario_id = %s ORDER BY id ASC', (objetivo.id,))
            resultados = cursor.fetchall()
            conn.close()
        except psycopg2.Error as e:
            await interaction.followup.send(f"❌ Ocurrió un error al contactar con la base de datos: {e}", ephemeral=True)
            return

        # 4. Formatear y construir el mensaje Embebido de Resultados
        if not resultados:
            # Caso en que está limpio
            embed_limpio = discord.Embed(
                title="✅ HISTORIAL LIMPIO",
                description=f"El usuario **{objetivo.mention}** NO registra sanciones ni Warns activos en su historial.",
                color=discord.Color.brand_green()
            )
            embed_limpio.set_thumbnail(url=objetivo.display_avatar.url)
            embed_limpio.set_footer(text="Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_limpio, ephemeral=True)

        # Caso en que sí tiene historial:
        titulos = {
            "adv_1": "⚠️ Advertencia 1",
            "adv_2": "⚠️ Advertencia 2",
            "adv_3": "⚠️ Advertencia 3",
            "adv_4": "⚠️ Advertencia 4",
            "sancion_1": "🔨 Sanción 1",
            "sancion_2": "🔨 Sanción 2",
            "sancion_3": "🔨 Sanción 3"
        }

        embed_historial = discord.Embed(
            title="📂 HISTORIAL DE SANCIONES",
            description=f"Mostrando los registros activos correspondientes a {objetivo.mention}:\n",
            color=discord.Color.from_rgb(255, 165, 0) # Color Naranja llamativo
        )
        embed_historial.set_thumbnail(url=objetivo.display_avatar.url)

        # Iterar todos sus castigos encontrados iterando de 1 en adelante
        for i, registro in enumerate(resultados, start=1):
            tipo_db, razon_db, prueba_db = registro
            
            tipo_legible = titulos.get(tipo_db, tipo_db.capitalize())
            
            # Estructurar la información del "Box" de manera bonita dentro del Embebido (uso de saltos de linea y bloque de código)
            info = f"**Motivo:** ```\n{razon_db}\n```\n**Evidencia adjunta:** [🔗 Ver Aquí]({prueba_db})"
            
            embed_historial.add_field(
                name=f"[{i}] {tipo_legible}",
                value=info,
                inline=False
            )

        # Resumen de Cuántas tiene
        embed_historial.set_footer(text=f"Total acumuladas: {len(resultados)} | Derechos de Autor: Smile")

        # 5. Todo el envío se mantiene efímero como se solicitó
        await interaction.followup.send(embed=embed_historial, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConsultarSanciones(bot))
