import subprocess
import sys
import time
import os

def main():
    # Obtener la ruta absoluta del directorio donde está run.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Iniciando la aplicación web (Flask) y el bot de Discord...")
    
    # Iniciar app.py (Flask Web App)
    flask_process = subprocess.Popen([sys.executable, "app.py"], cwd=current_dir)
    print("✅ Flask (app.py) iniciado.")
    
    # Iniciar main.py (Discord Bot)
    bot_process = subprocess.Popen([sys.executable, "main.py"], cwd=current_dir)
    print("✅ Discord Bot (main.py) iniciado.")
    
    try:
        # Monitorear que ambos procesos sigan corriendo
        while True:
            time.sleep(1)
            
            if flask_process.poll() is not None:
                print("⚠️ El proceso de la aplicación web (app.py) se detuvo inesperadamente.")
                break
                
            if bot_process.poll() is not None:
                print("⚠️ El proceso del bot de Discord (main.py) se detuvo inesperadamente.")
                break
                
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...")
        
    finally:
        # Terminar procesos limpiamente si aún se están ejecutando
        if flask_process.poll() is None:
            flask_process.terminate()
            flask_process.wait()
            print("🛑 Aplicación web detenida.")
            
        if bot_process.poll() is None:
            bot_process.terminate()
            bot_process.wait()
            print("🛑 Bot de Discord detenido.")

if __name__ == '__main__':
    main()
