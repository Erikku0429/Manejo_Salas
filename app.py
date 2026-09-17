import datetime
import pandas as pd
import streamlit as st
from controllers.horario_controller import HorarioController
from models.database import DatabaseModel

st.set_page_config(
    page_title="Gestión de Aulas Universitarias",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db = DatabaseModel()
controller = HorarioController(db)

# -----------------------------------------------------------------------------
# ESTILOS CSS CORREGIDOS (COMPATIBLES CON MODO OSCURO / CLARO Y FILA RESALTADA)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* 1. Resaltado de la Fila Completa seleccionada en la tabla */
    [data-testid="stDataEditor"] div[role="row"]:has(div[aria-selected="true"]) {
        background-color: rgba(59, 130, 246, 0.22) !important;
        border-left: 4px solid #3b82f6 !important;
    }

    /* 2. Resaltado enfocado para la Celda en edición activa */
    [data-testid="stDataEditor"] div[aria-selected="true"] {
        background-color: rgba(59, 130, 246, 0.35) !important;
        outline: 2px solid #60a5fa !important;
        outline-offset: -2px;
    }

    /* 3. Corrección de color de las tarjetas de métricas para Dark / Light Mode */
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-left: 4px solid #3b82f6 !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
    }

    /* Ajuste de contraste para el texto dentro de métricas */
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: inherit !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# Modal / Popup de Éxito
@st.dialog("🎉 Carga Exitosa")
def mostrar_popup_exito(total_registros, f_ini, f_fin):
  st.success("### ¡Las asignaturas han sido guardadas!")
  st.write(
      f"• **Periodo Configurado:** Del **{f_ini}** al **{f_fin}**\n"
      f"• **Sesiones Proyectadas:** **{total_registros} clases** registradas"
      " automáticamente en la base de datos."
  )
  st.info("La información ya está lista y guardada de forma permanente.")
  if st.button("Entendido / Cerrar", type="primary"):
    st.rerun()


# Encabezado Principal
st.title("🏫 Gestión de Aulas y Carga Semestral")

tab_cargue, tab_horarios, tab_eventos = st.tabs([
    "📋 Confirmación de Carga Semestral",
    "📅 Consulta de Horarios",
    "➕ Eventos y Cambios",
])

# -----------------------------------------------------------------------------
# TAB 1: CONFIRMACIÓN DE ASIGNATURAS CON RESALTADO DE FILA COMPLETA
# -----------------------------------------------------------------------------
with tab_cargue:
  st.markdown("### 1️⃣ Paso 1: Configurar Fechas del Semestre")
  st.caption(
      "Selecciona la fecha de inicio y finalización del periodo académico:"
  )

  c_f1, c_f2 = st.columns(2)
  f_inicio = c_f1.date_input(
      "Fecha de Inicio del Semestre:", value=datetime.date(2026, 2, 2)
  )
  f_fin = c_f2.date_input(
      "Fecha de Finalización del Semestre:", value=datetime.date(2026, 6, 30)
  )

  if f_fin <= f_inicio:
    st.error("⚠️ La fecha de finalización debe ser posterior a la de inicio.")
  else:
    st.markdown("---")
    st.markdown("### 2️⃣ Paso 2: Cargar Archivo de Horarios")

    uploaded_file = st.file_uploader(
        "Sube el archivo Excel formateado (`.xlsx`):", type=["xlsx"]
    )

    if uploaded_file is not None:
      try:
        if "df_unicas" not in st.session_state:
          st.session_state.df_unicas = controller.procesar_excel_ordenado(
              uploaded_file
          )

        cols_visibles = [
            "ESPACIO / SALÓN",
            "DÍA",
            "HORA INICIO (24H)",
            "HORA FIN (24H)",
            "ASIGNATURA",
            "DOCENTE",
        ]
        df_edit = st.session_state.df_unicas[cols_visibles]

        st.markdown("---")
        st.markdown("### 3️⃣ Paso 3: Confirmar Oferta Académica")
        st.info(
            "💡 **Tip de Edición:** Al hacer clic sobre cualquier celda,"
            " **toda la fila de la clase se resaltará** para mantener la guía"
            " visual de lo que estás editando."
        )

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("📚 Clases a Programar", len(df_edit))
        col_m2.metric(
            "🏛️ Aulas Asignadas", len(df_edit["ESPACIO / SALÓN"].unique())
        )
        col_m3.metric("⏰ Horario Oficial Funcionarios", "07:00 a 19:00")

        # Tabla interactiva con resaltado dinámico de fila completa
        df_editado = st.data_editor(
            df_edit,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "ESPACIO / SALÓN": st.column_config.SelectboxColumn(
                    "Salón / Aula",
                    options=[
                        "E105 (SALA CAD)",
                        "B222 (SALA COMPUTADORES)",
                        "B222 (SALÓN POSGRADOS)",
                    ],
                    required=True,
                ),
                "DÍA": st.column_config.SelectboxColumn(
                    "Día de la Semana",
                    options=[
                        "LUNES",
                        "MARTES",
                        "MIÉRCOLES",
                        "JUEVES",
                        "VIERNES",
                        "SÁBADO",
                    ],
                    required=True,
                ),
                "HORA INICIO (24H)": st.column_config.NumberColumn(
                    "Hora Inicio (7 a 18)", min_value=7, max_value=18, step=1
                ),
                "HORA FIN (24H)": st.column_config.NumberColumn(
                    "Hora Fin (8 a 19)", min_value=8, max_value=19, step=1
                ),
                "ASIGNATURA": st.column_config.TextColumn(
                    "Asignatura / Materia", required=True
                ),
                "DOCENTE": st.column_config.TextColumn("Docente / Profesor"),
            },
        )

        # Validaciones de seguridad de horario (07:00 a 19:00)
        errores_rango = controller.validar_rango_laboral(df_editado)

        if errores_rango:
          st.error(
              "🚨 **Horario No Permitido:** Hay clases configuradas fuera del"
              " rango oficial de funcionarios (07:00 a 19:00):"
          )
          for err in errores_rango:
            st.warning(
                f"• **{err['asignatura']}** ({err['salon']} - {err['dia']}):"
                f" Horario {err['inicio']}:00 a {err['fin']}:00 hrs."
            )
          st.error(
              "⚠️ Modifica las horas marcadas en la tabla para habilitar el"
              " guardado."
          )
        else:
          st.markdown("---")
          if st.button("🚀 Confirmar y Guardar Semestre", type="primary"):
            controller.proyectar_y_guardar_semestre(
                df_editado, f_inicio, f_fin
            )
            total_registros = len(db.obtener_todos_los_horarios())
            mostrar_popup_exito(total_registros, f_inicio, f_fin)

      except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

# -----------------------------------------------------------------------------
# TAB 2: CONSULTA DE HORARIOS
# -----------------------------------------------------------------------------
with tab_horarios:
  st.subheader("Consulta de Horarios Cargados")
  df_horarios = db.obtener_todos_los_horarios()

  if df_horarios.empty:
    st.info("No hay horarios cargados aún.")
  else:
    col1, col2 = st.columns(2)
    s_filter = col1.selectbox(
        "Filtrar Salón:",
        ["TODOS"] + sorted(df_horarios["espacio"].unique().tolist()),
    )
    d_filter = col2.date_input("Filtrar Fecha:", value=None)

    df_view = df_horarios.copy()
    if s_filter != "TODOS":
      df_view = df_view[df_view["espacio"] == s_filter]
    if d_filter is not None:
      df_view = df_view[df_view["fecha"] == d_filter.strftime("%Y-%m-%d")]

    st.dataframe(
        df_view[[
            "espacio",
            "fecha",
            "dia",
            "hora_inicio",
            "hora_fin",
            "asignatura",
            "docente",
            "tipo_evento",
        ]],
        use_container_width=True,
    )

# -----------------------------------------------------------------------------
# TAB 3: REGISTRO DE EVENTOS
# -----------------------------------------------------------------------------
with tab_eventos:
  st.subheader("Registrar Evento o Reserva Especial")
  with st.form("form_evento_nuevo"):
    col_a, col_b = st.columns(2)
    ev_salon = col_a.selectbox("Salón:", [
        "E105 (SALA CAD)",
        "B222 (SALA COMPUTADORES)",
        "B222 (SALÓN POSGRADOS)",
    ])
    ev_fecha = col_a.date_input("Fecha:", value=datetime.date.today())
    ev_h_ini = col_a.number_input(
        "Hora Inicio (7 a 18):", min_value=7, max_value=18, value=10
    )

    ev_h_fin = col_b.number_input(
        "Hora Fin (8 a 19):", min_value=8, max_value=19, value=12
    )
    ev_asig = col_b.text_input("Asignatura / Evento:", value="EXAMEN PARCIAL")
    ev_doc = col_b.text_input("Docente / Responsable:", value="POR DEFINIR")
    ev_obs = st.text_area("Observación:", value="Reserva puntual de aula")

    if st.form_submit_button("Guardar Evento"):
      if ev_h_fin <= ev_h_ini:
        st.error("La Hora Fin debe ser mayor a la Hora Inicio.")
      else:
        db.agregar_evento_especial(
            ev_salon,
            ev_fecha.strftime("%Y-%m-%d"),
            ev_h_ini,
            ev_h_fin,
            ev_asig,
            ev_doc,
            ev_obs,
        )
        st.success("🎉 Evento registrado correctamente.")
        st.rerun()