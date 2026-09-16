import os
import sys
import webbrowser
import streamlit.web.cli as stcli


def get_base_dir():
  if getattr(sys, 'frozen', False):
    return sys._MEIPASS
  return os.path.dirname(os.path.abspath(__file__))


if __name__ == '__main__':
  base_dir = get_base_dir()
  app_path = os.path.join(base_dir, 'app.py')

  # Asegurar que el directorio activo sea la carpeta base
  os.chdir(base_dir)

  # Configuración explícita para evitar 404 / Not Found en PyInstaller
  sys.argv = [
      'streamlit',
      'run',
      app_path,
      '--server.port=8501',
      '--server.headless=true',
      '--global.developmentMode=false',
  ]

  webbrowser.open('http://localhost:8501')
  sys.exit(stcli.main())




def get_base_dir():
  if getattr(sys, 'frozen', False):
    return sys._MEIPASS
  return os.path.dirname(os.path.abspath(__file__))


if __name__ == '__main__':
  base_dir = get_base_dir()
  app_path = os.path.join(base_dir, 'app.py')

  # Asegurar que el directorio de trabajo coincida con el entorno empaquetado
  os.chdir(base_dir)

  sys.argv = [
      'streamlit',
      'run',
      app_path,
      '--server.port=8501',
      '--server.headless=true',
      '--global.developmentMode=false',
  ]

  webbrowser.open('http://localhost:8501')
  sys.exit(stcli.main())