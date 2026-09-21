import os
import sqlite3
import pandas as pd
import streamlit as st

# Importar validación y login de seguridad
from controllers.auth_controller import (
    renderizar_login_admin,
    validar_archivo_excel,
)

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Consulta Aulas DTE",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "horarios.db"


# -----------------------------------------------------------------------------
# 2. FUNCIONES DE BASE DE DATOS (SEGURAS CON Y SIN IMPACTO EN VISUALIZACIÓN)
# -----------------------------------------------------------------------------
def obtener_conexion():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def inicializar_bd():
  conn = obtener_conexion()
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)
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


def obtener_semestre_activo():
  if not os.path.exists(DB_PATH):
    return "Sin Cargar"
  conn = obtener_conexion()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT valor FROM configuracion WHERE clave = 'semestre_activo'"
  )
  fila = cursor.fetchone()
  conn.close()
  return fila["valor"] if fila else "Sin Cargar"


def guardar_semestre_activo(nuevo_semestre):
  conn = obtener_conexion()
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO configuracion (clave, valor) VALUES ('semestre_activo', ?)
        ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
    """,
      (nuevo_semestre,),
  )
  conn.commit()
  conn.close()


def obtener_aulas_disponibles():
  if not os.path.exists(DB_PATH):
    return []
  conn = obtener_conexion()
  cursor = conn.cursor()
  cursor.execute("SELECT DISTINCT aula FROM horarios ORDER BY aula ASC")
  filas = cursor.fetchall()
  conn.close()
  return [f["aula"] for f in filas]


def consultar_horario_aula(aula):
  conn = obtener_conexion()
  query = """
        SELECT dia, bloque_horario, asignatura, docente, grupo 
        FROM horarios 
        WHERE aula = ?
        ORDER BY bloque_horario ASC
    """
  df = pd.read_sql_query(query, conn, params=(aula,))
  conn.close()
  return df


def consultar_eventos_aula(aula):
  conn = obtener_conexion()
  query = """
        SELECT fecha, hora_inicio, hora_fin, nombre_evento, descripcion 
        FROM eventos 
        WHERE aula = ?
        ORDER BY fecha ASC, hora_inicio ASC
    """
  df = pd.read_sql_query(query, conn, params=(aula,))
  conn.close()
  return df


# Inicializar tablas
inicializar_bd()

# -----------------------------------------------------------------------------
# 3. SIDEBAR & AUTENTICACIÓN
# -----------------------------------------------------------------------------
st.sidebar.title("🏫 Sistema DTE")
st.sidebar.markdown("Consulta y Gestión de Aulas")
st.sidebar.divider()

renderizar_login_admin()

# -----------------------------------------------------------------------------
# 4. ENCABEZADO Y ESTADO DE SEMESTRE
# -----------------------------------------------------------------------------
st.title("Consulta Aulas DTE")
semestre_actual = obtener_semestre_activo()

if semestre_actual in ["Sin Cargar", "No configurado"]:
  st.warning("⚠️ **Estado:** No hay un semestre cargado en el sistema.")
else:
  st.info(f"📌 **Semestre Activo:** {semestre_actual}")

st.divider()

# -----------------------------------------------------------------------------
# 5. VISTA PÚBLICA DE CONSULTA (HORARIOS Y EVENTOS)
# -----------------------------------------------------------------------------
aulas = obtener_aulas_disponibles()

if not aulas:
  st.info(
      "La base de datos se encuentra vacía. Un administrador debe realizar el"
      " cargue del semestre."
  )
else:
  col_tab1, col_tab2 = st.columns([1, 3])

  with col_tab1:
    aula_sel = st.selectbox("Seleccionar Aula:", aulas)
    dia_sel = st.selectbox(
        "Día de la semana:",
        ["Todos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
    )

  with col_tab2:
    tab1, tab2 = st.tabs(
        ["🗓️ Consulta de Horarios (Público / QR)", "📢 Próximos Eventos"]
    )

    with tab1:
      st.subheader(f"Horario Semanal por Aulas - {aula_sel}")
      df_h = consultar_horario_aula(aula_sel)

      if df_h.empty:
        st.warning("No hay programación registrada.")
      else:
        if dia_sel != "Todos":
          df_h = df_h[df_h["dia"] == dia_sel]
        st.dataframe(df_h, use_container_width=True, hide_index=True)

    with tab2:
      st.subheader(f"Eventos Programados - {aula_sel}")
      df_e = consultar_eventos_aula(aula_sel)

      if df_e.empty:
        st.info("Sin eventos programados.")
      else:
        st.dataframe(df_e, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 6. PANEL ADMINISTRATIVO (INTERFAZ ORIGINAL Y FLUIDA)
# -----------------------------------------------------------------------------
if st.session_state.get("admin_autenticado", False):
  st.divider()
  st.header("⚙️ Panel Administrativo")

  # Módulo 1: Semestre Activo
  st.subheader("1. Gestión de Semestre")
  col_s1, col_s2 = st.columns([3, 1])
  with col_s1:
    input_semestre = st.text_input(
        "Código o Nombre del Semestre:",
        value=semestre_actual if semestre_actual != "Sin Cargar" else "2026-2",
    )
  with col_s2:
    st.write("")
    st.write("")
    if st.button("Guardar Semestre"):
      guardar_semestre_activo(input_semestre)
      st.success("Semestre guardado.")
      st.rerun()

  st.divider()

  # Módulo 2: Cargue con Previsualización Editable
  st.subheader("2. Cargar Matriz de Horarios (Excel)")
  archivo_excel = st.file_uploader(
      "Seleccionar archivo Excel:", type=["xlsx", "xls"]
  )

  if archivo_excel and validar_archivo_excel(archivo_excel):
    try:
      df_preview = pd.read_excel(archivo_excel)

      st.subheader("📋 Previsualización y Edición de Datos")
      st.caption(
          "Puede editar valores directamente en la tabla antes de guardar los"
          " cambios."
      )

      # Tabla interactiva editable
      df_editado = st.data_editor(
          df_preview, num_rows="dynamic", use_container_width=True
      )

      if st.button("💾 Guardar y Reemplazar Horarios", type="primary"):
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM horarios")

        for _, fila in df_editado.iterrows():
          cursor.execute(
              """
                        INSERT INTO horarios (aula, dia, bloque_horario, asignatura, docente, grupo)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
              (
                  str(fila.get("AULA", fila.get("aula", ""))),
                  str(fila.get("DIA", fila.get("dia", ""))),
                  str(
                      fila.get(
                          "HORA",
                          fila.get("bloque_horario", fila.get("hora", "")),
                      )
                  ),
                  str(fila.get("ASIGNATURA", fila.get("asignatura", ""))),
                  str(fila.get("DOCENTE", fila.get("docente", ""))),
                  str(fila.get("GRUPO", fila.get("grupo", ""))),
              ),
          )

        conn.commit()
        conn.close()
        st.success("✅ Base de datos actualizada con éxito.")
        st.rerun()
    except Exception as err:
      st.error(f"Error procesando el archivo: {err}")

  st.divider()

  # Módulo 3: Eventos Especiales
  st.subheader("3. Registrar Evento Especial / Reserva")
  listado_aulas = aulas if aulas else ["Aula 101", "Aula 102", "Auditorio"]

  with st.form("form_evento"):
    col_e1, col_e2 = st.columns(2)
    with col_e1:
      a_ev = st.selectbox("Aula:", listado_aulas)
      f_ev = st.date_input("Fecha:")
      n_ev = st.text_input("Nombre del Evento:")
    with col_e2:
      h_i = st.time_input("Hora Inicio:")
      h_f = st.time_input("Hora Fin:")
      d_ev = st.text_area("Descripción:")

    if st.form_submit_button("Guardar Evento"):
      if n_ev.strip():
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(
            """
                    INSERT INTO eventos (aula, fecha, hora_inicio, hora_fin, nombre_evento, descripcion)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
            (a_ev, str(f_ev), str(h_i), str(h_f), n_ev, d_ev),
        )
        conn.commit()
        conn.close()
        st.success("Evento registrado.")
        st.rerun()
      else:
        st.error("Ingrese el nombre del evento.")