import os
import subprocess
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# Recolectar metadatos y archivos requeridos por Streamlit
datas = collect_data_files('streamlit')
datas += copy_metadata('streamlit')
datas += copy_metadata('click')
datas += copy_metadata('altair')

# Incluir archivos y carpetas del proyecto
datas.append(('app.py', '.'))
datas.append(('controllers', 'controllers'))
datas.append(('models', 'models'))
datas.append(('sources', 'sources'))

hiddenimports = collect_submodules('streamlit')

cmd = [
    'run_server.py',
    '--noconfirm',
    '--onedir',
    '--name=Servidor_Consulta_Aulas_DTE',
    '--noconsole',  # Oculta completamente la consola de comandos CMD
    '--windowed',   # Modo aplicación de ventana sin consola en Windows
]

for src, dst in datas:
    cmd.append(f'--add-data={src};{dst}')

for hidden in hiddenimports:
    cmd.append(f'--hidden-import={hidden}')

cmd.append('--copy-metadata=streamlit')

print("📦 Compilando aplicación en modo silencioso (Sin Consola CMD)...")
PyInstaller.__main__.run(cmd)
print("✅ ¡Compilación completada en dist/Servidor_Consulta_Aulas_DTE!")