import os
import sqlite3
import pandas as pd
import streamlit as st

# Importación de controladores de seguridad y negocio
from controllers.auth_controller import (
    renderizar_login_admin,
    validar_archivo_excel,
)

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Consulta Aulas DTE",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "horarios.db"


# -----------------------------------------------------------------------------
# 2. FUNCIONES DE BASE DE DATOS (CON CONSULTAS PARAMETRIZADAS SEGURAS)
# -----------------------------------------------------------------------------
def obtener_conexion():
  """Crea y retorna la conexión a la base de datos SQLite local."""
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def inicializar_bd():
  """Crea las tablas principales si no existen."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aula TEXT NOT NULL,
            dia TEXT NOT NULL,
            bloque_horario TEXT NOT NULL,
            asignatura TEXT,
            docente TEXT,
            grupo TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aula TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            nombre_evento TEXT NOT NULL,
            descripcion TEXT
        )
    """)
  conn.commit()
  conn.close()


def obtener_aulas_disponibles():
  """Obtiene la lista de aulas registradas ordenadas alfabéticamente."""
  if not os.path.exists(DB_PATH):
    return []
  conn = obtener_conexion()
  cursor = conn.cursor()
  cursor.execute("SELECT DISTINCT aula FROM horarios ORDER BY aula ASC")
  filas = cursor.fetchall()
  conn.close()
  return [f["aula"] for f in filas]


def consultar_horario_aula(aula_seleccionada):
  """Obtiene la matriz de horario semanal para un aula usando consultas seguras."""
  conn = obtener_conexion()
  # Consulta parametrizada con '?' para evitar inyección SQL
  query = """
        SELECT dia, bloque_horario, asignatura, docente, grupo 
        FROM horarios 
        WHERE aula = ?
        ORDER BY bloque_horario ASC
    """
  df = pd.read_sql_query(query, conn, params=(aula_seleccionada,))
  conn.close()
  return df


def consultar_eventos_aula(aula_seleccionada):
  """Obtiene los eventos especiales programados para un aula."""
  conn = obtener_conexion()
  query = """
        SELECT fecha, hora_inicio, hora_fin, nombre_evento, descripcion 
        FROM eventos 
        WHERE aula = ?
        ORDER BY fecha ASC, hora_inicio ASC
    """
  df = pd.read_sql_query(query, conn, params=(aula_seleccionada,))
  conn.close()
  return df


# Inicializar la base de datos al cargar la app
inicializar_bd()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL (SIDEBAR) & AUTENTICACIÓN
# -----------------------------------------------------------------------------
st.sidebar.title("🏫 Sistema DTE")
st.sidebar.markdown(
    "Módulo de Consulta de Espacios y Aulas del Departamento de Tecnología"
    " Educativa."
)
st.sidebar.divider()

# Módulo de Login Administrativo
renderizar_login_admin()

st.sidebar.divider()
st.sidebar.caption("© 2026 Universidad - Sistema de Horarios DTE")

# -----------------------------------------------------------------------------
# 4. ENCABEZADO PRINCIPAL
# -----------------------------------------------------------------------------
st.title("📚 Consulta de Aulas y Horarios DTE")
st.markdown(
    "Bienvenido al portal de consulta de espacios académicos. Utilice los"
    " filtros a continuación para verificar la disponibilidad y programación"
    " de las aulas."
)

# -----------------------------------------------------------------------------
# 5. VISTA PÚBLICA: CONSULTA DE HORARIOS Y EVENTOS
# -----------------------------------------------------------------------------
aulas = obtener_aulas_disponibles()

if not aulas:
  st.info(
      "ℹ️ **Estado:** La base de datos no contiene horarios registrados"
      " actualmente. Si es administrador, inicie sesión en la barra lateral"
      " para cargar la matriz en Excel."
  )
else:
  col_filtro, col_espacio = st.columns([1, 3])

  with col_filtro:
    st.subheader("🔍 Selección de Aula")
    aula_seleccionada = st.selectbox("Seleccione el aula o espacio:", aulas)

    dia_filtro = st.selectbox(
        "Filtrar por día (Opcional):",
        ["Todos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
    )

  with col_espacio:
    st.header(f"📍 Espacio: {aula_seleccionada}")

    tab_horario, tab_eventos = st.tabs(
        ["🗓️ Horario Semanal", "📢 Próximos Eventos"]
    )

    with tab_horario:
      df_horario = consultar_horario_aula(aula_seleccionada)

      if df_horario.empty:
        st.warning("No hay clases registradas para este espacio.")
      else:
        if dia_filtro != "Todos":
          df_horario = df_horario[df_horario["dia"] == dia_filtro]

        st.dataframe(
            df_horario,
            use_container_width=True,
            hide_index=True,
            column_config={
                "dia": "Día",
                "bloque_horario": "Bloque Horario",
                "asignatura": "Asignatura / Asignación",
                "docente": "Docente",
                "grupo": "Grupo",
            },
        )

    with tab_eventos:
      df_eventos = consultar_eventos_aula(aula_seleccionada)

      if df_eventos.empty:
        st.info("No hay eventos especiales ni reservas en este espacio.")
      else:
        st.dataframe(
            df_eventos,
            use_container_width=True,
            hide_index=True,
            column_config={
                "fecha": "Fecha",
                "hora_inicio": "Inicio",
                "hora_fin": "Fin",
                "nombre_evento": "Evento",
                "descripcion": "Descripción",
            },
        )

# -----------------------------------------------------------------------------
# 6. VISTA ADMINISTRATIVA PROTEGIDA
# -----------------------------------------------------------------------------
if st.session_state.get("admin_autenticado", False):
  st.divider()
  st.header("⚙️ Panel de Gestión Administrativa")
  st.success("Acceso concedido. Puede realizar la actualización de datos.")

  col_carga, col_eventos_admin = st.columns(2)

  with col_carga:
    st.subheader("📤 Cargar Matriz de Horarios (Excel)")
    archivo_excel = st.file_uploader(
        "Seleccione el archivo .xlsx generado por la coordinación:",
        type=["xlsx", "xls"],
        help="El archivo debe contener las columnas oficiales de aulas y bloques horarios.",
    )

    if archivo_excel and validar_archivo_excel(archivo_excel):
      if st.button("🚀 Procesar y Actualizar Semestre", type="primary"):
        try:
          # Lectura y procesamiento del archivo con pandas
          df_cargado = pd.read_excel(archivo_excel)

          # Ejemplo de integración a SQLite
          # (Asegúrate de ajustar los nombres de columnas según tu Excel)
          conn = obtener_conexion()
          cursor = conn.cursor()
          cursor.execute("DELETE FROM horarios")  # Reemplazo de datos antiguos

          for _, row in df_cargado.iterrows():
            cursor.execute(
                """
                            INSERT INTO horarios (aula, dia, bloque_horario, asignatura, docente, grupo)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                (
                    str(row.get("AULA", "")),
                    str(row.get("DIA", "")),
                    str(row.get("HORA", "")),
                    str(row.get("ASIGNATURA", "")),
                    str(row.get("DOCENTE", "")),
                    str(row.get("GRUPO", "")),
                ),
            )

          conn.commit()
          conn.close()
          st.success(
              "✅ ¡Matriz de horarios procesada y cargada con éxito en la base de"
              " datos!"
          )
          st.rerun()
        except Exception as e:
          st.error(
              f"⚠️ Error al procesar la estructura del archivo Excel: {str(e)}"
          )

  with col_eventos_admin:
    st.subheader("➕ Registrar Evento Especial / Reserva")
    with st.form("form_nuevo_evento"):
      aula_evento = st.selectbox(
          "Aula para el evento:",
          aulas if aulas else ["Aula 101", "Aula 102", "Auditorio"],
      )
      fecha_evento = st.date_input("Fecha del evento:")
      col_h1, col_h2 = st.columns(2)
      with col_h1:
        hora_ini = st.time_input("Hora Inicio:")
      with col_h2:
        hora_fin = st.time_input("Hora Fin:")

      nom_evento = st.text_input("Nombre del evento / Reserva:")
      desc_evento = st.text_area("Descripción u observaciones:")

      btn_guardar_evento = st.form_submit_button("Guardar Reserva")

      if btn_guardar_evento:
        if nom_evento:
          conn = obtener_conexion()
          cursor = conn.cursor()
          cursor.execute(
              """
                        INSERT INTO eventos (aula, fecha, hora_inicio, hora_fin, nombre_evento, descripcion)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
              (
                  aula_evento,
                  str(fecha_evento),
                  str(hora_ini),
                  str(hora_fin),
                  nom_evento,
                  desc_evento,
              ),
          )
          conn.commit()
          conn.close()
          st.success("✅ Evento o reserva registrado correctamente.")
          st.rerun()
        else:
          st.error("⚠️ El nombre del evento es obligatorio.")