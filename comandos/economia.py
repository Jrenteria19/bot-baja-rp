import discord
from discord.ext import commands
from discord import app_commands
from db_connect import get_db_connection
import random
import datetime

CANAL_BANCO = 1481747742698246263
ROL_PERMITIDO = 1481747742018769108

SALDO_MAX = 50000000       # Límite máximo en cuenta: 50 Millones de MXN
TRANSF_MIN = 10            # Mínimo a transferir: 10 MXN
TRANSF_MAX = 2000000       # Máximo por transferencia: 2 Millones de MXN

class BancoCentral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.init_db()

    def init_db(self):
        # Crear la tabla de cuentas bancarias si no existe
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cuentas_bancarias (
                id BIGINT PRIMARY KEY,
                saldo BIGINT DEFAULT 0 CHECK(saldo >= 0)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sueldos_roles (
                rol_id BIGINT PRIMARY KEY,
                cantidad BIGINT CHECK(cantidad > 0),
                dias INTEGER CHECK(dias >= 1)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cobros_sueldos (
                discord_id BIGINT,
                rol_id BIGINT,
                ultimo_cobro TIMESTAMP,
                PRIMARY KEY (discord_id, rol_id)
            )
        ''')
        conn.commit()
        conn.close()

    def obtener_o_crear_cuenta(self, usuario_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT saldo FROM cuentas_bancarias WHERE id = %s', (usuario_id,))
        cuenta = cursor.fetchone()
        
        if not cuenta:
            # Si no tiene cuenta, se la creamos automáticamente con 0 MXN
            cursor.execute('''
                INSERT INTO cuentas_bancarias (id, saldo)
                VALUES (%s, 0)
            ''', (usuario_id,))
            conn.commit()
            
            cursor.execute('SELECT saldo FROM cuentas_bancarias WHERE id = %s', (usuario_id,))
            cuenta = cursor.fetchone()
            
        conn.close()
        return cuenta[0] if cuenta else 0

    @app_commands.command(name="estado-cuenta", description="🏦 Accede a la plataforma del BBVA para consultar fondos.")
    @app_commands.describe(ciudadano="El ciudadano a consultar (Opcional, dejar en blanco para ver tu cuenta)")
    async def estado_cuenta(self, interaction: discord.Interaction, ciudadano: discord.Member = None):
        
        # 1. Validación de Canal
        if interaction.channel_id != CANAL_BANCO:
            embed_error = discord.Embed(
                title="🚫 Cajero Fuera de Servicio",
                description=f"Las transacciones bancarias y consultas de saldo solo operan en las sucursales oficiales.\n\n📍 Ubicación: <#{CANAL_BANCO}>",
                color=discord.Color.dark_red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # 2. Validación de Rango / Rol
        tiene_rol = any(role.id == ROL_PERMITIDO for role in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso a Bóveda Denegado",
                description="No posees los credenciales gubernamentales o de cuenta para acceder a este cajero.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        target = ciudadano if ciudadano else interaction.user
        
        # 3. Obtener o crear cuenta del usuario objetivo
        saldo = self.obtener_o_crear_cuenta(target.id)
        
        # Formatear el saldo como moneda mexicana ($ xx.xxx) sin decimales. Al ser INTEGER en DB, nunca habrá letras o decimales.
        saldo_formateado = f"${saldo:,.0f} MXN".replace(",", ".")
        
        # 4. Construir "Estado de Cuenta" Bancario Serio
        hora_actual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M Hrs")
        
        embed_banco = discord.Embed(
            title="🏦 BANCO DE MÉXICO (BANXICO)",
            description=f"**PLATAFORMA VIRTUAL - ESTADO DE CUENTA**\nEstimado(a) Cliente: **{target.name}**\n\nA continuación, se detalla el resumen de su capital disponible al corte del _{hora_actual}_.",
            color=discord.Color.from_rgb(0, 51, 153) # Azul corporativo bancario
        )
        
        # Detalles de la cuenta (El ID es su numero de cuenta)
        embed_banco.add_field(name="💳 Número de Cuenta", value=f"`{target.id}`", inline=True)
        embed_banco.add_field(name="💼 Tipo de Cuenta", value="Cuenta Vista Corporativa", inline=True)
        embed_banco.add_field(name="\u200b", value="\u200b", inline=True) # Espacio en blanco
        
        # Saldo en grande
        embed_banco.add_field(name="💰 BALANCE TOTAL DISPONIBLE", value=f"```diff\n+ {saldo_formateado}\n```", inline=False)
        
        embed_banco.set_thumbnail(url=target.display_avatar.url)
        embed_banco.set_footer(text=f"Seguridad Bancaria Cifrada | Secretaría de Hacienda y Crédito Público - {interaction.guild.name}", icon_url="https://cdn-icons-png.flaticon.com/512/2830/2830284.png")

        # Mensaje de advertencia de confidencialidad
        await interaction.followup.send(
            content=f"🔒 *Conexión segura establecida. Consulta estrictamente confidencial.*", 
            embed=embed_banco, 
            ephemeral=True
        )

    @app_commands.command(name="agregar-fondos", description="🏦 [ADMIN] Inyecta capital a la cuenta bancaria de un ciudadano.")
    @app_commands.describe(ciudadano="Ciudadano al que se le inyectarán los fondos", cantidad="Cantidad de MXN a depositar", razon="Razón o concepto del depósito")
    async def agregar_fondos(self, interaction: discord.Interaction, ciudadano: discord.Member, cantidad: int, razon: str):
        # 1. Validación de Roles
        ROLES_ADMIN_ECONOMIA = [1481747742047994026, 1481747742047994028]
        tiene_rol = any(role.id in ROLES_ADMIN_ECONOMIA for role in interaction.user.roles)
        
        if not interaction.user.guild_permissions.administrator and not tiene_rol:
            return await interaction.response.send_message("⛔ **Acceso Denegado:** No tienes los credenciales de Alta Administración Financiera para usar este comando.", ephemeral=True)

        if cantidad <= 0:
            return await interaction.response.send_message("❌ Error en la transacción: La cantidad a depositar debe ser mayor a 0 MXN.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        # 2. Sumar fondos en Base de Datos
        saldo_actual = self.obtener_o_crear_cuenta(ciudadano.id)
        nuevo_saldo = saldo_actual + cantidad
        
        if nuevo_saldo > SALDO_MAX:
            max_fmt = f"${SALDO_MAX:,.0f} MXN".replace(",", ".")
            return await interaction.followup.send(f"❌ **Límite Patrimonial Excedido:** El ciudadano no puede superar el tope bancario de `{max_fmt}` en su cuenta.", ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE cuentas_bancarias SET saldo = %s WHERE id = %s', (nuevo_saldo, ciudadano.id))
        conn.commit()
        conn.close()

        cantidad_fmt = f"${cantidad:,.0f} MXN".replace(",", ".")
        saldo_fmt = f"${nuevo_saldo:,.0f} MXN".replace(",", ".")

        # 3. Notificación Personal por Mensaje Directo (DM)
        embed_dm = discord.Embed(
            title="💰 DEPÓSITO BANCARIO APROBADO",
            description=f"La Secretaría de Hacienda y Crédito Público (SHCP) ha depositado fondos en tu cuenta.\n\n**Monto ingresado:** `{cantidad_fmt}`\n**Razón / Concepto:** {razon}\n**Saldo actual disponible:** `{saldo_fmt}`",
            color=discord.Color.green()
        )
        embed_dm.set_footer(text=f"BBVA México | {interaction.guild.name}")
        try:
            await ciudadano.send(embed=embed_dm)
        except discord.Forbidden:
            pass # Si el usuario tiene los DMs cerrados, el código ignora el error y continúa

        # 4. Registro en el libro de Logs
        canal_logs = interaction.guild.get_channel(1501013259271274543)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro Financiero | Depósito",
                description=f"**Oficial a cargo:** {interaction.user.mention}\n**Cuenta destino:** {ciudadano.mention}\n**Monto transferido:** `{cantidad_fmt}`\n**Comprobante (Razón):** {razon}",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            embed_log.set_thumbnail(url=ciudadano.display_avatar.url)
            await canal_logs.send(embed=embed_log)

        await interaction.followup.send(f"✅ Transacción exitosa. Se han depositado **{cantidad_fmt}** a la cuenta de {ciudadano.mention}.", ephemeral=True)

    @app_commands.command(name="quitar-fondos", description="🏦 [ADMIN] Extrae capital o multa la cuenta bancaria de un ciudadano.")
    @app_commands.describe(ciudadano="Ciudadano al que se le embargarán los fondos", cantidad="Cantidad de MXN a retirar", razon="Razón o concepto del retiro")
    async def quitar_fondos(self, interaction: discord.Interaction, ciudadano: discord.Member, cantidad: int, razon: str):
        # 1. Validación de Roles
        ROLES_ADMIN_ECONOMIA = [1481747742047994026, 1481747742047994028]
        tiene_rol = any(role.id in ROLES_ADMIN_ECONOMIA for role in interaction.user.roles)
        
        if not interaction.user.guild_permissions.administrator and not tiene_rol:
            return await interaction.response.send_message("⛔ **Acceso Denegado:** No tienes los credenciales de Alta Administración Financiera para usar este comando.", ephemeral=True)

        if cantidad <= 0:
            return await interaction.response.send_message("❌ Error en la transacción: La cantidad a extraer debe ser mayor a 0 MXN.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        
        # 2. Retirar fondos en Base de Datos (Si quitan más de lo que tiene, queda en 0)
        saldo_actual = self.obtener_o_crear_cuenta(ciudadano.id)
        
        if saldo_actual < cantidad:
            nuevo_saldo = 0
            retirado_real = saldo_actual # Solo le pudimos quitar lo que le quedaba
        else:
            nuevo_saldo = saldo_actual - cantidad
            retirado_real = cantidad

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE cuentas_bancarias SET saldo = %s WHERE id = %s', (nuevo_saldo, ciudadano.id))
        conn.commit()
        conn.close()

        retirado_fmt = f"${retirado_real:,.0f} MXN".replace(",", ".")
        saldo_fmt = f"${nuevo_saldo:,.0f} MXN".replace(",", ".")

        # 3. Notificación Personal por Mensaje Directo (DM)
        embed_dm = discord.Embed(
            title="📉 EMBARGO / RETIRO BANCARIO EJECUTADO",
            description=f"La Secretaría de Hacienda y Crédito Público (SHCP) ha extraído fondos de tu cuenta.\n\n**Monto retirado:** `{retirado_fmt}`\n**Razón / Concepto:** {razon}\n**Saldo actual disponible:** `{saldo_fmt}`",
            color=discord.Color.red()
        )
        embed_dm.set_footer(text=f"BBVA México | {interaction.guild.name}")
        try:
            await ciudadano.send(embed=embed_dm)
        except discord.Forbidden:
            pass # Si el usuario tiene los DMs cerrados, el código ignora el error

        # 4. Registro en el libro de Logs
        canal_logs = interaction.guild.get_channel(1501013259271274543)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro Financiero | Extracción",
                description=f"**Oficial a cargo:** {interaction.user.mention}\n**Cuenta afectada:** {ciudadano.mention}\n**Monto extraído:** `{retirado_fmt}`\n**Comprobante (Razón):** {razon}",
                color=discord.Color.red(),
                timestamp=interaction.created_at
            )
            embed_log.set_thumbnail(url=ciudadano.display_avatar.url)
            await canal_logs.send(embed=embed_log)

        await interaction.followup.send(f"✅ Transacción legal efectiva. Se han embargado **{retirado_fmt}** de la cuenta de {ciudadano.mention}.", ephemeral=True)

    @app_commands.command(name="transferir", description="💸 Transfiere fondos a la cuenta bancaria de otro ciudadano.")
    @app_commands.describe(ciudadano="Ciudadano que recibirá los fondos", cantidad="Cantidad de MXN a transferir", concepto="Motivo de la transferencia")
    async def transferir(self, interaction: discord.Interaction, ciudadano: discord.Member, cantidad: int, concepto: str):
        # 1. Validación de Canal
        if interaction.channel_id != CANAL_BANCO:
            embed_error = discord.Embed(
                title="🚫 Cajero Fuera de Servicio",
                description=f"Las transferencias bancarias solo pueden realizarse en las sucursales oficiales.\n\n📍 Ubicación: <#{CANAL_BANCO}>",
                color=discord.Color.dark_red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # 2. Validación de Rol
        tiene_rol = any(role.id == ROL_PERMITIDO for role in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso a Bóveda Denegado",
                description="No posees los credenciales necesarios ni la cuenta activa para operar en este cajero.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # 3. Validaciones estáticas de la transferencia
        if cantidad < TRANSF_MIN or cantidad > TRANSF_MAX:
            min_fmt = f"${TRANSF_MIN:,.0f} MXN".replace(",", ".")
            max_fmt = f"${TRANSF_MAX:,.0f} MXN".replace(",", ".")
            return await interaction.response.send_message(f"❌ **Error en monto:** Las transferencias deben ser desde `{min_fmt}` hasta un máximo de `{max_fmt}`.", ephemeral=True)
            
        if ciudadano.id == interaction.user.id:
            return await interaction.response.send_message("❌ Error: No puedes transferirte dinero a tu propia cuenta.", ephemeral=True)

        if ciudadano.bot:
             return await interaction.response.send_message("❌ Error: Los sistemas automatizados (Bots) no poseen cuenta bancaria.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # 4. Verificar fondos del emisor en BD
        saldo_emisor = self.obtener_o_crear_cuenta(interaction.user.id)
        
        if saldo_emisor < cantidad:
            saldo_fmt = f"${saldo_emisor:,.0f} MXN".replace(",", ".")
            cantidad_fmt = f"${cantidad:,.0f} MXN".replace(",", ".")
            return await interaction.followup.send(f"❌ **Fondos Insuficientes.** Intentaste transferir `{cantidad_fmt}`, pero el saldo de tu cuenta es de solo `{saldo_fmt}`.", ephemeral=True)

        # 5. Realizar la transferencia transaccional
        saldo_receptor = self.obtener_o_crear_cuenta(ciudadano.id)
        
        nuevo_saldo_emisor = saldo_emisor - cantidad
        nuevo_saldo_receptor = saldo_receptor + cantidad
        
        if nuevo_saldo_receptor > SALDO_MAX:
            max_fmt = f"${SALDO_MAX:,.0f} MXN".replace(",", ".")
            return await interaction.followup.send(f"❌ **Operación Rechazada:** La cuenta destino del receptor superaría el límite bancario permitido de `{max_fmt}`.", ephemeral=True)

        # Guardar en BD
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE cuentas_bancarias SET saldo = %s WHERE id = %s', (nuevo_saldo_emisor, interaction.user.id))
        cursor.execute('UPDATE cuentas_bancarias SET saldo = %s WHERE id = %s', (nuevo_saldo_receptor, ciudadano.id))
        conn.commit()
        conn.close()

        cantidad_fmt = f"${cantidad:,.0f} MXN".replace(",", ".")

        # 6. Mensaje Público Llamativo en el canal
        embed_publico = discord.Embed(
            title="🔄 TRANSFERENCIA BANCARIA EXITOSA",
            description=f"El ciudadano **{interaction.user.mention}** ha realizado un SPEI a favor de **{ciudadano.mention}**.\n\n**Monto:** `{cantidad_fmt}`\n**Comprobante (Concepto):** `{concepto}`",
            color=discord.Color.blue()
        )
        embed_publico.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2830/2830284.png")
        embed_publico.set_footer(text=f"BBVA México | {interaction.guild.name}")
        await interaction.channel.send(embed=embed_publico)

        # 7. Mensaje Efímero Secundario al Emisor
        await interaction.followup.send(f"✅ Has transferido exitosamente **{cantidad_fmt}** a {ciudadano.mention}.\n*Recuerda revisar tu `/estado-cuenta` actualizado.*", ephemeral=True)

        # 8. Log Administrativo Secreto
        canal_logs = interaction.guild.get_channel(1501013259271274543)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro Financiero | Transferencia Ciudadana",
                description=f"**Emisor:** {interaction.user.mention} (`{interaction.user.id}`)\n**Receptor:** {ciudadano.mention} (`{ciudadano.id}`)\n**Monto transferido:** `{cantidad_fmt}`\n**Concepto de pago:** {concepto}",
                color=discord.Color.blue(),
                timestamp=interaction.created_at
            )
            await canal_logs.send(embed=embed_log)

    @app_commands.command(name="asignar-sueldo", description="🏦 [ADMIN] Asigna un sueldo periódico a un rol (Trabajo o Beneficio).")
    @app_commands.describe(rol="Rol a configurar", cantidad="Monto de MXN a cobrar", dias="Frecuencia en días (Ej: cada 7 días)")
    async def asignar_sueldo(self, interaction: discord.Interaction, rol: discord.Role, cantidad: int, dias: int):
        ROLES_ADMIN_ECONOMIA = [1481747742047994026, 1481747742047994028]
        tiene_rol = any(r.id in ROLES_ADMIN_ECONOMIA for r in interaction.user.roles)
        
        if not interaction.user.guild_permissions.administrator and not tiene_rol:
            return await interaction.response.send_message("⛔ **Acceso Denegado:** No tienes los credenciales administrativos para configurar sueldos.", ephemeral=True)

        if cantidad <= 0 or cantidad > 10000000:
            return await interaction.response.send_message("❌ Error: La cantidad del sueldo debe ser de `1 MXN` hasta un máximo de `$ 10.000.000 MXN`.", ephemeral=True)
            
        if dias < 1 or dias > 60:
            return await interaction.response.send_message("❌ Error: Los días de cobro deben estar entre `1` y `60 días` para mantener la estabilidad del sistema.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar o actualizar la configuración de sueldo para este rol (upsert logic compatible con MySQL)
        cursor.execute('''
            INSERT INTO sueldos_roles (rol_id, cantidad, dias)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE cantidad=VALUES(cantidad), dias=VALUES(dias)
        ''', (rol.id, cantidad, dias))
        conn.commit()
        conn.close()

        cantidad_fmt = f"${cantidad:,.0f} MXN".replace(",", ".")
        
        # Log administrativo
        canal_logs = interaction.guild.get_channel(1501013259271274543)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro Financiero | Sueldo Nominal Configurado",
                description=f"**Oficial a cargo:** {interaction.user.mention}\n**Rol configurado:** {rol.mention}\n**Monto Oficial:** `{cantidad_fmt}`\n**Frecuencia:** Cada `{dias}` día(s)",
                color=discord.Color.gold(),
                timestamp=interaction.created_at
            )
            await canal_logs.send(embed=embed_log)

        await interaction.followup.send(f"✅ Se ha configurado correctamente un sueldo de **{cantidad_fmt}** cada **{dias} día(s)** para los portadores del rol {rol.mention}.", ephemeral=True)

    @app_commands.command(name="quitar-sueldo", description="🏦 [ADMIN] Revoca el sueldo asignado a un rol gubernamental o laboral.")
    @app_commands.describe(rol="Rol al cual se le quitará el derecho a cobrar sueldo")
    async def quitar_sueldo(self, interaction: discord.Interaction, rol: discord.Role):
        ROLES_ADMIN_ECONOMIA = [1481747742047994026, 1481747742047994028]
        tiene_rol = any(r.id in ROLES_ADMIN_ECONOMIA for r in interaction.user.roles)
        
        if not interaction.user.guild_permissions.administrator and not tiene_rol:
            return await interaction.response.send_message("⛔ **Acceso Denegado:** No tienes los credenciales administrativos necesarios.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM sueldos_roles WHERE rol_id = %s", (rol.id,))
        existe = cursor.fetchone()
        
        if not existe:
            conn.close()
            return await interaction.followup.send(f"❌ El rol {rol.mention} no tiene ningún sueldo asignado en la base de datos.", ephemeral=True)
            
        cursor.execute('DELETE FROM sueldos_roles WHERE rol_id = %s', (rol.id,))
        conn.commit()
        conn.close()

        # Log administrativo
        canal_logs = interaction.guild.get_channel(1501013259271274543)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Registro Financiero | Sueldo Eliminado",
                description=f"**Oficial a cargo:** {interaction.user.mention}\n**Rol afectado:** {rol.mention}\n**Acción:** Se le ha revocado el derecho permanentemente a cobrar un sueldo al rol.",
                color=discord.Color.red(),
                timestamp=interaction.created_at
            )
            await canal_logs.send(embed=embed_log)

        await interaction.followup.send(f"✅ Se ha eliminado y revocado correctamente el derecho a cobrar sueldo para el rol {rol.mention}.", ephemeral=True)

    @app_commands.command(name="cobrar-sueldo", description="🏦 Reclama el sueldo disponible de tus roles activos (Trabajo/Beneficio).")
    async def cobrar_sueldo(self, interaction: discord.Interaction):
        # 1. Validación de Canal
        if interaction.channel_id != CANAL_BANCO:
            embed_error = discord.Embed(
                title="🚫 Cajero Fuera de Servicio",
                description=f"El cobro de sueldos solo opera en las sucursales oficiales.\n\n📍 Ubicación: <#{CANAL_BANCO}>",
                color=discord.Color.dark_red()
            )
            embed_error.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # 2. Validación de Rol
        tiene_rol = any(role.id == ROL_PERMITIDO for role in interaction.user.roles)
        if not tiene_rol and not interaction.user.guild_permissions.administrator:
            embed_error = discord.Embed(
                title="⛔ Acceso a Bóveda Denegado",
                description="No posees la tarjeta ciudadana para interactuar con este cajero.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed_error, ephemeral=True)

        # Iniciar una respuesta Efímera para ocultar los errores al público
        await interaction.response.defer(ephemeral=True)

        user_roles_ids = [r.id for r in interaction.user.roles]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 3. Obtener todos los sueldos configurados que coincidan con los roles del usuario
        placeholders = ','.join('%s' for _ in user_roles_ids)
        if not placeholders:
            conn.close()
            return await interaction.followup.send("❌ No tienes ningún rol gubernamental o laboral asignado en la ciudad.", ephemeral=True)

        cursor.execute(f'SELECT rol_id, cantidad, dias FROM sueldos_roles WHERE rol_id IN ({placeholders})', tuple(user_roles_ids))
        sueldos_aplicables = cursor.fetchall()
        
        if not sueldos_aplicables:
            conn.close()
            return await interaction.followup.send("❌ Tus roles actuales no tienen configurado ningún sueldo en el Sistema de Administración Tributaria (SAT).", ephemeral=True)

        total_cobrado = 0
        roles_cobrados = []
        ahora = datetime.datetime.now()

        # 4. Proceso Inteligente: Verificar tiempo de espera para cada rol
        for rol_id, cantidad, dias in sueldos_aplicables:
            cursor.execute('SELECT ultimo_cobro FROM cobros_sueldos WHERE discord_id = %s AND rol_id = %s', (interaction.user.id, rol_id))
            registro = cursor.fetchone()
            
            puede_cobrar = False
            if not registro:
                puede_cobrar = True
            else:
                ultimo_cobro = registro[0]
                if (ahora - ultimo_cobro).days >= dias:
                    puede_cobrar = True
            
            if puede_cobrar:
                total_cobrado += cantidad
                roles_cobrados.append(f"<@&{rol_id}>: `${cantidad:,.0f} MXN`".replace(",", "."))
                
                # Actualizar la fecha y hora de este cobro al instante presente
                cursor.execute('''
                    INSERT INTO cobros_sueldos (discord_id, rol_id, ultimo_cobro) 
                    VALUES (%s, %s, %s) 
                    ON DUPLICATE KEY UPDATE ultimo_cobro=VALUES(ultimo_cobro)
                ''', (interaction.user.id, rol_id, ahora.strftime('%Y-%m-%d %H:%M:%S')))

        # 5. Respuesta final si no hubo cobros
        if total_cobrado == 0:
            conn.close()
            return await interaction.followup.send("⏳ **Nómina no disponible.** Aún bloqueada por políticas de tiempo. Recuerda que no han pasado los días suficientes para reclamar tu(s) sueldo(s).", ephemeral=True)

        # 6. Actualizar el saldo monetario del usuario
        saldo_actual = self.obtener_o_crear_cuenta(interaction.user.id)
        nuevo_saldo = saldo_actual + total_cobrado
        
        # Check de seguridad de límite máximo corporativo
        if nuevo_saldo > SALDO_MAX:
             nuevo_saldo = SALDO_MAX
             total_cobrado = SALDO_MAX - saldo_actual # Cobró solo lo necesario matemática para llegar a Tope

        cursor.execute('UPDATE cuentas_bancarias SET saldo = %s WHERE id = %s', (nuevo_saldo, interaction.user.id))
        conn.commit()
        conn.close()

        # 7. Imprimir boleta de pago PÚBLICA
        saldo_fmt = f"${nuevo_saldo:,.0f} MXN".replace(",", ".")
        cobrado_fmt = f"${total_cobrado:,.0f} MXN".replace(",", ".")
        detalles_roles = "\n".join(roles_cobrados)

        embed_pago = discord.Embed(
            title="💼 DEPÓSITO DE NÓMINA - GOBIERNO DE MÉXICO",
            description=f"¡La SHCP ha depositado con éxito tus honorarios, **{interaction.user.mention}**!\n\n**Total Depositado:** `{cobrado_fmt}`\n\n**Desglose Salarial:**\n{detalles_roles}\n\n**📈 Balance Total Actual:** `{saldo_fmt}`",
            color=discord.Color.green()
        )
        embed_pago.set_thumbnail(url=interaction.user.display_avatar.url)
        embed_pago.set_footer(text=f"BBVA México | {interaction.guild.name}", icon_url="https://cdn-icons-png.flaticon.com/512/2830/2830284.png")

        # Mandar al canal públicamente
        await interaction.channel.send(content=f"{interaction.user.mention}", embed=embed_pago)
        
        # Concluir la interacción efímera privada
        await interaction.followup.send("✅ Depósito cobrado exitosamente.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BancoCentral(bot))
