import os
import subprocess
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = collect_data_files('streamlit')
datas += copy_metadata('streamlit')
datas += copy_metadata('click')
datas += copy_metadata('altair')

# Incluir archivos y binarios del proyecto
datas.append(('app.py', '.'))
datas.append(('cloudflared.exe', '.'))  # Incluye el binario del túnel
datas.append(('controllers', 'controllers'))
datas.append(('models', 'models'))
datas.append(('sources', 'sources'))

hiddenimports = collect_submodules('streamlit')

cmd = [
    'run_server.py',
    '--noconfirm',
    '--onedir',
    '--name=Servidor_Consulta_Aulas_DTE',
    '--noconsole',
    '--windowed',
]

for src, dst in datas:
    cmd.append(f'--add-data={src};{dst}')

for hidden in hiddenimports:
    cmd.append(f'--hidden-import={hidden}')

cmd.append('--copy-metadata=streamlit')

print("📦 Compilando servidor con soporte para acceso público por túnel HTTPS...")
PyInstaller.__main__.run(cmd)
print("✅ ¡Compilación completada en dist/Servidor_Consulta_Aulas_DTE!")