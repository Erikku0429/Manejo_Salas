import multiprocessing
import os
import re
import socket
import sys
import threading
import time
import webbrowser
import subprocess

# Redirigir salidas de consola en modo sin ventana
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

multiprocessing.freeze_support()

def obtener_ruta_base():
    """Obtiene la ruta física donde se ejecuta el archivo .exe o script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def obtener_ip_red_real():
    """Obtiene la IP local asignada por Ethernet o Wi-Fi en la red."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        return ip_local
    except Exception:
        return "127.0.0.1"

def generar_imagen_qr(url):
    """Genera y guarda siempre la imagen PNG del código QR."""
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
        base_path = obtener_ruta_base()
        nombre_qr = os.path.join(base_path, "QR_Acceso_DTE.png")
        img.save(nombre_qr)
    except Exception:
        pass

def obtener_url_tunel_o_ip(puerto=8501):
    """Intenta arrancar cloudflared en modo directo o retorna la IP asignada en red."""
    base_dir_meipass = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    cloudflared_path = os.path.join(base_dir_meipass, "cloudflared.exe")

    if not os.path.exists(cloudflared_path):
        cloudflared_path = os.path.join(obtener_ruta_base(), "cloudflared.exe")

    ip_red = obtener_ip_red_real()
    url_fall_back = f"http://{ip_red}:{puerto}"

    if os.path.exists(cloudflared_path):
        try:
            cmd = [
                cloudflared_path,
                "tunnel",
                "--url", f"http://127.0.0.1:{puerto}",
                "--no-autoupdate"
            ]

            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                creationflags = subprocess.CREATE_NO_WINDOW

            proceso = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                startupinfo=startupinfo,
                creationflags=creationflags,
                bufsize=1
            )

            inicio = time.time()
            while time.time() - inicio < 12:
                linea = proceso.stdout.readline()
                if not linea:
                    time.sleep(0.1)
                    continue

                if "trycloudflare.com" in linea and "api.trycloudflare.com" not in linea:
                    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", linea)
                    if match:
                        return match.group(0)
        except Exception:
            pass

    return url_fall_back

def abrir_navegador(url):
    """Abre el navegador en el equipo servidor."""
    time.sleep(3.0)
    webbrowser.open(url)

if __name__ == "__main__":
    if os.environ.get("STREAMLIT_DTE_RUNNING") != "1":
        os.environ["STREAMLIT_DTE_RUNNING"] = "1"

        puerto = 8501

        # 1. Resolver enlace dinámico
        url_destino = obtener_url_tunel_o_ip(puerto)

        # 2. Generar el código QR con la dirección real obtenida
        generar_imagen_qr(url_destino)

        # 3. Lanzar apertura de navegador con la IP/URL pública
        threading.Thread(target=abrir_navegador, args=(url_destino,), daemon=True).start()

    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    app_path = os.path.join(base_dir, "app.py")

    import streamlit.web.cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.address=0.0.0.0",
        f"--server.port={puerto}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--global.developmentMode=false"
    ]

    try:
        stcli.main()
    except SystemExit:
        pass