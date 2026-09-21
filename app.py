import os
import sqlite3
import pandas as pd
import streamlit as st

# Importar controlador de autenticación y validación
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
# 2. BASE DE DATOS Y BINDINGS SEGUROS (?)
# -----------------------------------------------------------------------------
def obtener_conexion():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def inicializar_bd():
  conn = obtener_conexion()
  cursor = conn.cursor()

  # Tabla de configuración (Semestre activo)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

  # Tabla de horarios
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

  # Tabla de eventos
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
    return "No configurado"
  conn = obtener_conexion()
  cursor = conn.cursor()
  cursor.execute(
      "SELECT valor FROM configuracion WHERE clave = 'semestre_activo'"
  )
  fila = cursor.fetchone()
  conn.close()
  return fila["valor"] if fila else "Sin Semestre Cargar"


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


def consultar_horario_aula(aula_seleccionada):
  conn = obtener_conexion()
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


# Inicializar la base de datos
inicializar_bd()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL (SIDEBAR) Y LOGIN ADMIN
# -----------------------------------------------------------------------------
st.sidebar.title("🏫 Sistema DTE")
st.sidebar.markdown("Portal Institucional de Gestión de Aulas y Horarios.")
st.sidebar.divider()

renderizar_login_admin()

st.sidebar.divider()
st.sidebar.caption("© 2026 Universidad - Sistema DTE")

# -----------------------------------------------------------------------------
# 4. ENCABEZADO
# -----------------------------------------------------------------------------
st.title("🏫 Consulta de Aulas y Horarios DTE")
semestre_actual = obtener_semestre_activo()

if semestre_actual == "Sin Semestre Cargar" or semestre_actual == "No configurado":
  st.warning(
      "⚠️ **Estado:** No hay un semestre activo cargado en el sistema."
  )
else:
  st.info(f"📌 **Semestre Activo:** {semestre_actual}")

# -----------------------------------------------------------------------------
# 5. VISTA PÚBLICA (CONSULTA PARA ESTUDIANTES / DOCENTES)
# -----------------------------------------------------------------------------
aulas = obtener_aulas_disponibles()

if not aulas:
  st.info(
      "ℹ️ La base de datos no contiene horarios registrados. Un administrador"
      " debe realizar el cargue del semestre."
  )
else:
  col_filtro, col_espacio = st.columns([1, 3])

  with col_filtro:
    st.subheader("🔍 Filtros de Búsqueda")
    aula_seleccionada = st.selectbox("Seleccione el Aula:", aulas)
    dia_filtro = st.selectbox(
        "Filtrar por Día:",
        ["Todos", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
    )

  with col_espacio:
    st.header(f"📍 Aula: {aula_seleccionada}")
    tab_horario, tab_eventos = st.tabs(
        ["📅 Horario Semanal", "📢 Próximos Eventos"]
    )

    with tab_horario:
      df_horario = consultar_horario_aula(aula_seleccionada)
      if df_horario.empty:
        st.warning("No hay programación registrada para esta aula.")
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
                "asignatura": "Asignatura",
                "docente": "Docente",
                "grupo": "Grupo",
            },
        )

    with tab_eventos:
      df_eventos = consultar_eventos_aula(aula_seleccionada)
      if df_eventos.empty:
        st.info("No hay eventos ni reservas especiales para esta aula.")
      else:
        st.dataframe(df_eventos, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 6. PANEL ADMINISTRATIVO INTUITIVO Y ESTRUCTURADO (SOLO ADMINS)
# -----------------------------------------------------------------------------
if st.session_state.get("admin_autenticado", False):
  st.divider()
  st.header("⚙️ Panel de Gestión Administrativa")

  # Pestañas claras para separar las acciones
  tab_admin_semestre, tab_admin_cargue, tab_admin_eventos = st.tabs([
      "📌 Semestre Activo",
      "📤 Cargue de Horarios (Excel)",
      "➕ Eventos y Reservas",
  ])

  # --- PESTAÑA 1: GESTIÓN DEL SEMESTRE ACTIVO ---
  with tab_admin_semestre:
    st.subheader("Configuración del Período Académico")
    col_sem1, col_sem2 = st.columns([2, 1])

    with col_sem1:
      nuevo_semestre_input = st.text_input(
          "Definir nombre o código del semestre:",
          value=semestre_actual
          if semestre_actual != "Sin Semestre Cargar"
          else "2026-2",
          help="Ejemplo: 2026-1, 2026-2, Intersemestral 2026",
      )

    with col_sem2:
      st.write("")  # Espaciado vertical
      st.write("")
      if st.button("💾 Guardar Semestre", type="primary"):
        guardar_semestre_activo(nuevo_semestre_input)
        st.success(f"Semestre actualizado a: {nuevo_semestre_input}")
        st.rerun()

  # --- PESTAÑA 2: CARGUE Y EDICIÓN INTERACTIVA DE EXCEL ---
  with tab_admin_cargue:
    st.subheader("Cargar y Previsualizar Matriz de Horarios")
    archivo_excel = st.file_uploader(
        "Seleccione el archivo Excel (.xlsx) con los horarios:",
        type=["xlsx", "xls"],
        key="uploader_excel",
    )

    if archivo_excel and validar_archivo_excel(archivo_excel):
      try:
        # Cargar dataframe inicial
        df_preview = pd.read_excel(archivo_excel)

        st.warning(
            "📝 **Previsualización interactiva:** Puede modificar cualquier"
            " celda en la tabla antes de guardar los datos en el sistema."
        )

        # Editor de datos interactivo
        df_editado = st.data_editor(
            df_preview,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_matriz",
        )

        st.divider()
        if st.button(
            "🚀 Confirmar y Reemplazar Horarios en la BD", type="primary"
        ):
          conn = obtener_conexion()
          cursor = conn.cursor()

          # Limpiar tabla previa de horarios
          cursor.execute("DELETE FROM horarios")

          # Insertar registros editados con parámetros seguros (?)
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

          st.success(
              "✅ ¡Matriz cargada y guardada exitosamente en la base de datos!"
          )
          st.rerun()

      except Exception as e:
        st.error(f"Error al leer la estructura del archivo Excel: {str(e)}")

  # --- PESTAÑA 3: GESTIÓN DE EVENTOS ESPECIALES ---
  with tab_admin_eventos:
    st.subheader("Registrar Evento Especial / Reserva de Aula")

    listado_aulas_eventos = (
        aulas if aulas else ["Aula 101", "Aula 102", "Auditorio DTE"]
    )

    with st.form("form_nuevo_evento_admin"):
      col_e1, col_e2 = st.columns(2)

      with col_e1:
        aula_ev = st.selectbox("Aula:", listado_aulas_eventos)
        fecha_ev = st.date_input("Fecha del Evento:")
        nom_ev = st.text_input("Nombre del Evento / Conferencia / Reserva:")

      with col_e2:
        col_h1, col_h2 = st.columns(2)
        with col_h1:
          hora_ini_ev = st.time_input("Hora Inicio:")
        with col_h2:
          hora_fin_ev = st.time_input("Hora Fin:")

        desc_ev = st.text_area("Descripción u observaciones:")

      btn_guardar_ev = st.form_submit_button(
          "📌 Guardar Reserva", type="primary"
      )

      if btn_guardar_ev:
        if nom_ev.strip():
          conn = obtener_conexion()
          cursor = conn.cursor()
          cursor.execute(
              """
                        INSERT INTO eventos (aula, fecha, hora_inicio, hora_fin, nombre_evento, descripcion)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
              (
                  aula_ev,
                  str(fecha_ev),
                  str(hora_ini_ev),
                  str(hora_fin_ev),
                  nom_ev,
                  desc_ev,
              ),
          )
          conn.commit()
          conn.close()
          st.success("✅ Evento guardado con éxito.")
          st.rerun()
        else:
          st.error("⚠️ Ingrese un nombre válido para el evento.")