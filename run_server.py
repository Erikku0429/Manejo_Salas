import multiprocessing
import os
import socket
import sys
import threading
import time
import webbrowser

# Redirigir salidas de consola estándar a nulo cuando se ejecuta sin consola (--noconsole)
if sys.stdout is None:
  sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
  sys.stderr = open(os.devnull, "w")

# Protección obligatoria para PyInstaller en Windows
multiprocessing.freeze_support()


def obtener_ip_local():
  """Obtiene la IP local asignada en la red Wi-Fi / LAN de la universidad."""
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  try:
    s.connect(("8.8.8.8", 80))
    ip_local = s.getsockname()[0]
  except Exception:
    ip_local = "127.0.0.1"
  finally:
    s.close()
  return ip_local


def generar_imagen_qr(url):
  """Genera y guarda la imagen PNG del código QR."""
  try:
    import qrcode

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    nombre_qr = "QR_Acceso_DTE.png"
    img.save(nombre_qr)
  except Exception:
    pass


def abrir_navegador_una_vez(url):
  """Abre el navegador en primer plano tras iniciar el servidor."""
  time.sleep(3.0)
  webbrowser.open(url)


if __name__ == "__main__":
  if os.environ.get("STREAMLIT_DTE_RUNNING") != "1":
    os.environ["STREAMLIT_DTE_RUNNING"] = "1"

    ip = obtener_ip_local()
    puerto = 8501
    url_red = f"http://{ip}:{puerto}"

    # Generar la imagen PNG del QR
    generar_imagen_qr(url_red)

    # Hilo para abrir la interfaz en el navegador
    threading.Thread(
        target=abrir_navegador_una_vez, args=(url_red,), daemon=True
    ).start()

  # Determinar la ruta dinámica del archivo app.py
  base_dir = getattr(
      sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
  )
  app_path = os.path.join(base_dir, "app.py")

  import streamlit.web.cli as stcli

  sys.argv = [
      "streamlit",
      "run",
      app_path,
      "--server.address=0.0.0.0",
      "--server.port=8501",
      "--server.headless=true",
      "--server.fileWatcherType=none",
      "--global.developmentMode=false",
  ]

  try:
    stcli.main()
  except SystemExit:
    pass