import hashlib
import streamlit as st


def verificar_password(password_ingresada):
  """Compara el hash SHA-256 de la contraseña ingresada con el guardado en Secrets."""
  try:
    hash_ingresado = hashlib.sha256(password_ingresada.encode()).hexdigest()
    hash_guardado = st.secrets["admin_credentials"]["password_hash"]
    return hash_ingresado == hash_guardado
  except Exception:
    return False


def validar_archivo_excel(uploaded_file, max_mb=10):
  """Valida extensión y tamaño máximo del archivo cargado para evitar DoS."""
  if uploaded_file is not None:
    if uploaded_file.size > max_mb * 1024 * 1024:
      st.error(
          f"⚠️ El archivo supera el límite de {max_mb} MB. Cargue un archivo"
          " más liviano."
      )
      return False
    if not uploaded_file.name.endswith((".xlsx", ".xls")):
      st.error(
          "⚠️ Formato inválido. Solo se admiten archivos de Excel (.xlsx,"
          " .xls)."
      )
      return False
    return True
  return False


def renderizar_login_admin():
  """Muestra el formulario de inicio de sesión para administradores."""
  if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False

  if not st.session_state.admin_autenticado:
    with st.expander("🔐 Acceso Administrativo"):
      with st.form("form_login"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        btn_login = st.form_submit_button("Iniciar Sesión")

        if btn_login:
          user_correcto = st.secrets.get("admin_credentials", {}).get(
              "username", "admin_dte"
          )
          if usuario == user_correcto and verificar_password(clave):
            st.session_state.admin_autenticado = True
            st.success("✅ Autenticado con éxito.")
            st.rerun()
          else:
            st.error("❌ Usuario o contraseña incorrectos.")
  else:
    st.sidebar.success("👨‍💼 Sesión Admin Activa")
    if st.sidebar.button("Cerrar Sesión"):
      st.session_state.admin_autenticado = False
      st.rerun()