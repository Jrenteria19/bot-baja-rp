import os
import datetime
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# =====================================================================
# CONFIGURACIÓN INICIAL
# =====================================================================
# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Obtener el Token del Bot
TOKEN = os.getenv('DISCORD_TOKEN')

# =====================================================================
# CLASE PRINCIPAL DEL BOT
# =====================================================================
class ServidorBot(commands.Bot):
    def __init__(self):
        """
        Configuración de Intenciones (Intents) necesarias para que el bot
        pueda leer mensajes y detectar miembros al entrar al servidor.
        """
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # Obligatorio para detectar las llegadas y asignar roles
        
        # Inicializamos el bot con el prefijo '!'
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        """
        Este método se ejecuta automáticamente al iniciar el bot.
        Se encarga de cargar todos los comandos (Cogs) y sincronizar
        los comandos de barra (Slash Commands).
        """
        # =====================================================================
        # SISTEMA DE CARGA DE COMANDOS (COGS)
        # =====================================================================
        if not os.path.exists('./comandos'):
            os.makedirs('./comandos')

        print("Cargando comandos...")
        for filename in os.listdir('./comandos'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'comandos.{filename[:-3]}')
                    print(f'✅ Comando cargado: {filename}')
                except Exception as e:
                    print(f'Error al cargar el comando {filename}: {e}')

        # Sincronización de Slash Commands con Discord
        try:
            synced = await self.tree.sync()
            print(f'🌐 Sincronizados {len(synced)} comandos de barra (slash commands).')
        except Exception as e:
            print(f'Error al sincronizar comandos de barra: {e}')

        # Iniciar el bucle de estado dinámico
        self.cambiar_estado.start()

    # =====================================================================
    # TAREAS EN SEGUNDO PLANO (BACKGROUND TASKS)
    # =====================================================================
    @tasks.loop(seconds=20)
    async def cambiar_estado(self):
        """
        Cambia el "Jugando a..." del bot cada 20 segundos de forma rotativa.
        """
        estados = [
            "🏙️ la comunidad",
            "🛠️ Bot desarrollado por: Smile",
            "🌐 bot-baja-rp.onrender.com",
            "🛡️ BajaRP"
        ]
        
        # Seleccionamos el mensaje según el tiempo (rotación infinita)
        index = int((datetime.datetime.now().timestamp() / 20) % len(estados))
        mensaje_actual = estados[index]
        
        await self.change_presence(activity=discord.Game(name=mensaje_actual))

    @cambiar_estado.before_loop
    async def before_cambiar_estado(self):
        """Espera a que el bot esté listo antes de empezar a cambiar su estado."""
        await self.wait_until_ready()

    # =====================================================================
    # EVENTOS DEL BOT
    # =====================================================================
    async def on_command_error(self, ctx, error):
        """Manejo global de errores para comandos antiguos de prefijo."""
        if isinstance(error, commands.CommandNotFound):
            return # Ignoramos si alguien escribe '!comando_que_no_existe'
        else:
            print(f'⚠️ Error en comando: {error}')

    async def on_ready(self):
        """Evento que se dispara cuando el bot se ha conectado exitosamente."""
        print('\n' + '='*40)
        print(f'🤖 Bot Logueado como: {self.user.name}')
        print(f'🆔 ID del Bot: {self.user.id}')
        print('='*40 + '\n')

# =====================================================================
# INICIALIZACIÓN DEL SCRIPT
# =====================================================================
bot = ServidorBot()

if __name__ == '__main__':
    # Verificación final antes de arrancar
    if not TOKEN:
        print("❌ ERROR: No se encontró el DISCORD_TOKEN en el archivo .env")
    else:
        bot.run(TOKEN)
