import discord
from discord.ext import commands, tasks
from discord import app_commands
from db_connect import get_db_connection

CANAL_CALIFICACIONES = 1481747743230656570
CANAL_LOGS_CALIFIC_STAFF = 1501007004171239464
CANAL_VER_SANCIONES = 1481747742953963716
ROL_PERMITIDO_CALIFICAR = 1481747742018769108

class CalificacionesStaff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()
        self.borrado_semanal.start() # Iniciar el sistema automático de la semana

    def init_db(self):
        # Asegurar la estructura de Base de datos en MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calificaciones_staffs (
                id SERIAL PRIMARY KEY,
                usuario_id BIGINT,
                staff_id BIGINT,
                estrellas INTEGER,
                mensaje TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def cog_unload(self):
        # Cuando el bot se apaga, apaga el temporizador
        self.borrado_semanal.cancel()

    @app_commands.command(name="calificar-staff", description="Califica el desempeño y la atención de un moderador/staff.")
    @app_commands.describe(
        staff="El staff que deseas calificar",
        estrellas="Puntuación (De 1 a 5 estrellas)",
        mensaje="Comentario o mensajito para el staff"
    )
    @app_commands.choices(estrellas=[
        app_commands.Choice(name="⭐⭐⭐⭐⭐ (5 - Excelente atención)", value=5),
        app_commands.Choice(name="⭐⭐⭐⭐ (4 - Muy buena atención)", value=4),
        app_commands.Choice(name="⭐⭐⭐ (3 - Buena atención)", value=3),
        app_commands.Choice(name="⭐⭐ (2 - Puede mejorar)", value=2),
        app_commands.Choice(name="⭐ (1 - Mala atención)", value=1),
    ])
    async def calificar_staff(self, interaction: discord.Interaction, staff: discord.Member, estrellas: app_commands.Choice[int], mensaje: str):
        # 1. Validar Rol Permitido
        tiene_rol = any(role.id == ROL_PERMITIDO_CALIFICAR for role in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso Denegado",
                description=(
                    "No tienes los permisos necesarios para calificar al Staff.\n\n"
                    f"Necesitas el rol <@&{ROL_PERMITIDO_CALIFICAR}> o ser Administrador."
                ),
                color=discord.Color.red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/564/564619.png")
            embed_error.set_footer(text="Control de Acceso — Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # 2. Validar que esten en el Canal Correcto de Calificaciones
        if interaction.channel_id != CANAL_CALIFICACIONES:
            embed_error_canal = discord.Embed(
                title="🚫 Ubicación Incorrecta",
                description=f"Las evaluaciones de desempeño deben realizarse en el canal oficial.\n\n📍 Dirígete a: <#{CANAL_CALIFICACIONES}>",
                color=discord.Color.dark_red()
            )
            embed_error_canal.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
            embed_error_canal.set_footer(text="Seguridad el servidor — Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error_canal, ephemeral=True)

        if staff.bot:
            return await interaction.response.send_message("❌ No puedes calificar a un Bot automatizado.", ephemeral=True)
            
        if staff.id == interaction.user.id:
            return await interaction.response.send_message("❌ ¡Tramposo! No puedes autocalificarte a ti mismo.", ephemeral=True)

        # 2. Agregar a la Base de Datos MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO calificaciones_staffs (usuario_id, staff_id, estrellas, mensaje) VALUES (%s, %s, %s, %s)', 
                      (interaction.user.id, staff.id, estrellas.value, mensaje))
        conn.commit()
        conn.close()

        puntaje_estrellas = "⭐" * estrellas.value

        # 3. Mandar el Embed Público en el Canal de Calificaciones (Llamativo)
        embed_publico = discord.Embed(
            title="✨ ¡NUEVA VALORACIÓN DE STAFF RECIBIDA!",
            description=(
                f"La comunidad acaba de evaluar la atención de un Staff de el servidor.\n\n"
                f"*ℹ️ Recuerda: Cada semana las calificaciones se borrarán automáticamente y saldrá premiado el Staff con el mejor progreso durante la semana.*\n"
            ),
            color=discord.Color.gold()
        )
        embed_publico.add_field(name="🙎‍♂️ Calificado por:", value=interaction.user.mention, inline=True)
        embed_publico.add_field(name="🛡️ Staff Evaluado:", value=staff.mention, inline=True)
        embed_publico.add_field(name="🎖️ Puntuación:", value=puntaje_estrellas, inline=False)
        embed_publico.add_field(name="📝 Mensaje/Reseña del Usuario:", value=f"```\n{mensaje}\n```", inline=False)
        
        embed_publico.set_thumbnail(url=staff.display_avatar.url if staff.display_avatar else interaction.guild.icon.url)
        embed_publico.set_footer(text="Derechos de Autor: Smile")

        await interaction.response.send_message(embed=embed_publico)
        
        # Recuperar el enlace de este mensaje que acabamos de enviar para agregarlo al DM
        mensaje_publico = await interaction.original_response()
        link_al_mensaje = mensaje_publico.jump_url

        # 4. Enviar DM Privado al Staff Calificado
        embed_dm = discord.Embed(
            title="📊 SE HA EVALUADO TU TRABAJO",
            description=f"Hola {staff.name}, un usuario acaba de enviarte retroalimentación sobre tu reciente atención en el servidor **{interaction.guild.name}**.",
            color=discord.Color.gold()
        )
        embed_dm.add_field(name="Estrellas Recibidas", value=puntaje_estrellas, inline=True)
        embed_dm.add_field(name="Feedback Entregado", value=f"```\n{mensaje}\n```", inline=False)
        embed_dm.add_field(name="Míralo aquí", value=f"[🔗 Pincha aquí para ir a leer tu calificación]({link_al_mensaje})", inline=False)
        embed_dm.set_footer(text="Derechos de Autor: Smile")

        try:
            await staff.send(embed=embed_dm)
        except discord.Forbidden:
            pass # Si el staff bloquea DMs saltamos al siguiente paso tranquilamente

        # 5. Enviar un Reporte Secreto de Logging a los Administradores Superiores
        canal_logs = interaction.guild.get_channel(CANAL_LOGS_CALIFIC_STAFF)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro de Sistema - Valoración",
                color=discord.Color.blue(),
                timestamp=interaction.created_at
            )
            embed_log.add_field(name="Usuario Evaluador", value=f"{interaction.user.mention}\n(`{interaction.user.id}`)", inline=True)
            embed_log.add_field(name="Staff Evaluado", value=f"{staff.mention}\n(`{staff.id}`)", inline=True)
            embed_log.add_field(name="Puntaje Real", value=f"{estrellas.value}/5", inline=True)
            embed_log.add_field(name="Mensaje Copiado", value=f"```\n{mensaje}\n```", inline=False)
            embed_log.set_thumbnail(url=staff.display_avatar.url)
            embed_log.set_footer(text="Derechos de Autor: Smile")
            await canal_logs.send(embed=embed_log)


    @app_commands.command(name="ver-calificaciones", description="Permite consultar el promedio de calificaciones de cualquier staff.")
    @app_commands.describe(staff="Menciona al staff al que le quieres revisar las notas")
    async def ver_calificaciones(self, interaction: discord.Interaction, staff: discord.Member):
        
        # Validar el uso solo en la sala correspondiente de los admins
        if interaction.channel_id != CANAL_VER_SANCIONES:
            embed_error = discord.Embed(
                title="🚫 Canal Incorrecto",
                description=f"Las consultas de desempeño solo operan aquí: <#{CANAL_VER_SANCIONES}>.",
                color=discord.Color.dark_red()
            )
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        ROL_PERMITIDO = 1481747742047994023
        tiene_rol = any(role.id == ROL_PERMITIDO for role in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error_rol = discord.Embed(
                title="⛔ Acceso Denegado",
                description="No tienes los permisos o el rol necesario para consultar encuestas de desempeño.",
                color=discord.Color.red()
            )
            embed_error_rol.set_footer(text="Derechos de Autor: Smile")
            return await interaction.response.send_message(embed=embed_error_rol, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extraer todas las resenas del staff
        cursor.execute('SELECT estrellas, mensaje FROM calificaciones_staffs WHERE staff_id = %s ORDER BY id DESC', (staff.id,))
        resultados = cursor.fetchall()

        if not resultados:
            conn.close()
            embed_vacio = discord.Embed(
                title="📉 SIN REGISTROS",
                description=f"El staff {staff.mention} aún no cuenta con calificaciones en esta semana vigente.",
                color=discord.Color.light_embed()
            )
            embed_vacio.set_thumbnail(url=staff.display_avatar.url)
            embed_vacio.set_footer(text="Derechos de Autor: Smile")
            return await interaction.followup.send(embed=embed_vacio, ephemeral=True)

        # Calcular el promedio matemático
        avg_calc = sum(r[0] for r in resultados) / len(resultados)
        promedio = round(avg_calc, 1) # Redondeado a 1 decimal
        total = len(resultados)
        conn.close()

        embed_stats = discord.Embed(
            title=f"📈 RESULTADOS DE {staff.name.upper()}",
            description=f"El rendimiento y aceptación de este miembro de Staff es el siguiente:",
            color=discord.Color.brand_green()
        )
        embed_stats.add_field(name="Estrellas Promedio", value=f"**{promedio}/5.0**", inline=True)
        embed_stats.add_field(name="Tickets Calificados", value=f"**{total}** personas", inline=True)
        embed_stats.set_thumbnail(url=staff.display_avatar.url)
        
        # Opcional: Mostrar las 5 reseñas más recientes en este embed para que el admin las vea
        max_mostrar = 5
        contador = 1
        for resena in resultados[:max_mostrar]:
            strellas_print = "⭐" * resena[0]
            embed_stats.add_field(name=f"Reseña #{contador} ({strellas_print})", value=f"```\n{resena[1]}\n```", inline=False)
            contador += 1
            
        if total > max_mostrar:
            embed_stats.description += f"\n\n*(Mostrando solo las {max_mostrar} calificaciones más recientes de un total de {total})*"

        embed_stats.set_footer(text="Consultas Privadas — Derechos de Autor: Smile")
        await interaction.followup.send(embed=embed_stats, ephemeral=True)


    # Bucle Semanal Automatizado
    # 168 horas = 7 dias
    @tasks.loop(hours=168.0)
    async def borrado_semanal(self):
        # Asegurar de esperar a que el bot cargue su Cache antes de enviar mensajes o causará error
        await self.bot.wait_until_ready()
        await self._ejecutar_limpieza_semanal()

    @app_commands.command(name="forzar-cierre-calificaciones", description="Admins: Resetea manualmente la semana y anuncia al ganador.")
    @app_commands.default_permissions(administrator=True)
    async def forzar_cierre(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        exito = await self._ejecutar_limpieza_semanal()
        if exito:
            await interaction.followup.send("✅ Se ha forzado el Cierre de la Semana. El ganador fue anunciado y las bases están limpias.", ephemeral=True)
        else:
            await interaction.followup.send("ℹ️ Se forzó el cierre de la semana, pero nadie ha calificado a nadie en la BD, así que no se anunció ganador.", ephemeral=True)

    async def _ejecutar_limpieza_semanal(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta mágica para agrupar las estrellas por Staff, sacar su promedio matemático, 
        # y que el ganador sea el que tenga el Promedio mas alto. (En caso de empatar promedio, el q tenga mas votos totales)
        cursor.execute('''
            SELECT staff_id, AVG(estrellas) as promedio, COUNT(estrellas) as total 
            FROM calificaciones_staffs 
            GROUP BY staff_id 
            ORDER BY promedio DESC, total DESC 
            LIMIT 1
        ''')
        top_staff = cursor.fetchone()
        
        if not top_staff:
            conn.close()
            return False

        mejor_id, prom, votos_totales = top_staff
        promedio_final = round(prom, 2)

        # Borrar y limpiar todos los datos pasados de la Tabla
        cursor.execute('DELETE FROM calificaciones_staffs')
        conn.commit()
        conn.close()

        # Felicitar Públicamente en el Canal (Intenta buscar el Canal)
        canal_destinatario = self.bot.get_channel(CANAL_CALIFICACIONES)
        if canal_destinatario:
            embed_premio = discord.Embed(
                title="🏆 ¡STAFF EJEMPLAR DE LA SEMANA!",
                description=(
                    f"¡Ha finalizado un ciclo más, y la comunidad ha dictado su veredicto!\n\n"
                    f"Queremos felicitar a nuestro queridísimo moderador <@{mejor_id}> por haber sido el Staff **mejor posicionado** estos últimos 7 días. "
                    f"Agradecemos su increíble disposición y su vocación de servicio.\n\n"
                    f"**⭐ Puntuación Final:** {promedio_final}/5.0\n"
                    f"**👥 Total de Valoraciones Recibidas:** {votos_totales}\n\n"
                    f"*(Las bases de datos han sido limpiadas y estamos listos para la próxima contienda)*"
                ),
                color=discord.Color.from_rgb(255, 215, 0)
            )
            # Decoración tipo trofeo
            embed_premio.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3112/3112946.png")
            embed_premio.set_footer(text="Administración Estatal — Derechos de Autor: Smile")

            await canal_destinatario.send(content=f"🎉 Felicidades <@{mejor_id}> 🎉", embed=embed_premio)

        return True

async def setup(bot):
    await bot.add_cog(CalificacionesStaff(bot))
