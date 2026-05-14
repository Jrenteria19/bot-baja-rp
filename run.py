import subprocess
import sys
import time
import os

def main():
    # Obtener la ruta absoluta del directorio donde está run.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Iniciando la aplicación web (Flask) y el bot de Discord...", flush=True)
    
    # Iniciar app.py (Flask Web App)
    flask_process = subprocess.Popen([sys.executable, "-u", "app.py"], cwd=current_dir)
    print("✅ Flask (app.py) iniciado.", flush=True)
    
    # Iniciar main.py (Discord Bot)
    bot_process = subprocess.Popen([sys.executable, "-u", "main.py"], cwd=current_dir)
    print("✅ Discord Bot (main.py) iniciado.", flush=True)
    
    try:
        # Monitorear que ambos procesos sigan corriendo
        while True:
            time.sleep(1)
            
            if flask_process.poll() is not None:
                print("⚠️ El proceso de la aplicación web (app.py) se detuvo inesperadamente.", flush=True)
                break
                
            if bot_process.poll() is not None:
                print("⚠️ El proceso del bot de Discord (main.py) se detuvo inesperadamente.", flush=True)
                break
                
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...", flush=True)
        
    finally:
        # Terminar procesos limpiamente si aún se están ejecutando
        if flask_process.poll() is None:
            flask_process.terminate()
            flask_process.wait()
            print("🛑 Aplicación web detenida.", flush=True)
            
        if bot_process.poll() is None:
            bot_process.terminate()
            bot_process.wait()
            print("🛑 Bot de Discord detenido.", flush=True)

if __name__ == '__main__':
    main()
