import datetime
import hashlib
import unicodedata
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


def normalizar_texto(texto):
  if not isinstance(texto, str):
    return ""
  texto = texto.strip().lower()
  nfkd = unicodedata.normalize("NFKD", texto)
  return "".join([c for c in nfkd if not unicodedata.combining(c)])


def generar_estilo_color_materia(nombre_asignatura):
  """Genera un estilo dinámico único por materia con excelente legibilidad de texto."""
  nombre_norm = normalizar_texto(nombre_asignatura)
  hash_hex = hashlib.md5(nombre_norm.encode("utf-8")).hexdigest()
  hue = int(hash_hex[:4], 16) % 360  # Tono HSL de 0 a 360

  bg_color = f"hsl({hue}, 65%, 18%)"
  border_color = f"hsl({hue}, 80%, 55%)"
  text_color = f"hsl({hue}, 90%, 85%)"

  return (
      f"background: {bg_color}; border-left: 4px solid {border_color}; color:"
      f" {text_color};"
  )


# Estilos CSS
st.markdown(
    """
    <style>
    .class-card {
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .class-card-evento {
        background: linear-gradient(135deg, #451a03 0%, #1c0901 100%) !important;
        border-left: 4px solid #f59e0b !important;
    }
    
    /* Tarjeta de Franja Horaria Disponible */
    .card-disponible {
        background: rgba(16, 185, 129, 0.12);
        border: 1px dashed #10b981;
        border-left: 4px solid #10b981;
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 8px;
        color: #a7f3d0;
    }

    /* Encabezado especial para el DÍA ACTUAL (Hoy) */
    .header-hoy {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%);
        border: 2px solid #10b981;
        border-radius: 8px;
        padding: 8px;
        text-align: center;
        color: #6ee7b7;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }

    .class-title {
        font-weight: 700;
        font-size: 0.88rem;
        margin-bottom: 3px;
    }
    .class-doc {
        font-size: 0.78rem;
        opacity: 0.85;
    }
    .class-time {
        font-size: 0.72rem;
        font-weight: 600;
        margin-bottom: 4px;
        opacity: 0.9;
    }

    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-left: 4px solid #8b5cf6 !important;
        padding: 12px;
        border-radius: 8px;
    }

    [data-testid="stDataEditor"] div[role="row"]:has(div[aria-selected="true"]) {
        background-color: rgba(139, 92, 246, 0.22) !important;
        border-left: 4px solid #8b5cf6 !important;
    }
    [data-testid="stDataEditor"] div[aria-selected="true"] {
        background-color: rgba(139, 92, 246, 0.35) !important;
        outline: 2px solid #a78bfa !important;
        outline-offset: -2px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# Modales
@st.dialog("🎉 Carga Exitosa")
def mostrar_popup_exito(total_registros, f_ini, f_fin):
  st.success("### ¡Las asignaturas han sido guardadas!")
  st.write(
      f"• **Periodo Configurado:** Del **{f_ini}** al **{f_fin}**\n"
      f"• **Sesiones Proyectadas:** **{total_registros} clases** registradas"
      " en la base de datos."
  )
  if st.button("Ir a Consulta de Horarios ➡️", type="primary"):
    st.session_state["pestana_activa"] = "📅 Consulta de Horarios"
    st.rerun()


@st.dialog("⚠️ Confirmar Vaciado de Base de Datos")
def mostrar_popup_vaciar_db():
  st.warning(
      "**¿Estás seguro de que deseas eliminar TODOS los horarios guardados?**"
  )
  col_v1, col_v2 = st.columns(2)
  with col_v1:
    if st.button("❌ Cancelar", use_container_width=True):
      st.rerun()
  with col_v2:
    if st.button(
        "🗑️ Sí, Vaciar Base de Datos", type="primary", use_container_width=True
    ):
      db.vaciar_base_de_datos()
      if "df_unicas" in st.session_state:
        del st.session_state.df_unicas
      st.success("Base de datos vaciada correctamente.")
      st.rerun()


# Evaluación de Vigencia del Semestre
es_vigente, msj_vigencia, f_ini_db, f_fin_db = db.obtener_vigencia_semestre()

st.title("🏫 Gestión de Aulas y Carga Semestral")

if es_vigente:
  st.caption(f"🟢 **Estado:** {msj_vigencia}")
else:
  st.warning(f"⚠️ **Atención:** {msj_vigencia}")

tab_horarios, tab_cargue, tab_eventos = st.tabs([
    "📅 Consulta de Horarios (Semanal)",
    "📋 Confirmación de Carga Semestral",
    "➕ Eventos y Cambios",
])

# -----------------------------------------------------------------------------
# TAB 1: CONSULTA SEMANAL CON RESALTADO DE HOY Y DISPONIBILIDAD HORARIA
# -----------------------------------------------------------------------------
with tab_horarios:
  col_h1, col_h2 = st.columns([3, 1])
  with col_h1:
    st.subheader("📅 Horario Semanal por Aulas")
  with col_h2:
    if st.button("🗑️ Vaciar Base de Datos", type="secondary"):
      mostrar_popup_vaciar_db()

  df_horarios = db.obtener_todos_los_horarios()

  if df_horarios.empty:
    st.info(
        "La base de datos se encuentra vacía. Dirígete a la pestaña"
        " **'Confirmación de Carga Semestral'** para importar el semestre."
    )
  else:
    # FILTROS
    col_f1, col_f2, col_f3 = st.columns([3, 3, 3])

    with col_f1:
      salones_unicos = sorted([
          str(s).upper() for s in df_horarios["espacio"].unique()
      ])
      salon_sel = st.selectbox(
          "Filtrar por Salón / Aula:", ["TODOS"] + salones_unicos
      )

    with col_f2:
      busqueda_asig = st.text_input(
          "🔍 Buscar por Asignatura:", placeholder="Ej. programacion"
      )

    with col_f3:
      busqueda_doc = st.text_input(
          "👨‍🏫 Buscar por Docente:", placeholder="Ej. nicolas"
      )

    # Cálculo del Rango de la Semana Activa basada en la fecha de HOY
    fecha_hoy = datetime.date.today()
    lunes_semana = fecha_hoy - datetime.timedelta(days=fecha_hoy.weekday())
    sabado_semana = lunes_semana + datetime.timedelta(days=5)

    # Filtrar datos por el rango semanal
    df_filtered = df_horarios.copy()
    df_filtered["fecha_dt"] = pd.to_datetime(df_filtered["fecha"]).dt.date
    df_filtered = df_filtered[
        (df_filtered["fecha_dt"] >= lunes_semana)
        & (df_filtered["fecha_dt"] <= sabado_semana)
    ]

    if salon_sel != "TODOS":
      df_filtered = df_filtered[
          df_filtered["espacio"].apply(normalizar_texto)
          == normalizar_texto(salon_sel)
      ]

    if busqueda_asig.strip():
      q_asig = normalizar_texto(busqueda_asig)
      df_filtered = df_filtered[
          df_filtered["asignatura"].apply(normalizar_texto).str.contains(q_asig)
      ]

    if busqueda_doc.strip():
      q_doc = normalizar_texto(busqueda_doc)
      df_filtered = df_filtered[
          df_filtered["docente"].apply(normalizar_texto).str.contains(q_doc)
      ]

    # Ocultar Sábado si no tiene clases
    hay_clases_sabado = "sabado" in df_filtered["dia"].apply(
        normalizar_texto
    ).values or "sábado" in df_filtered["dia"].apply(normalizar_texto).values

    if hay_clases_sabado:
      dias_semana_nombres = [
          "LUNES",
          "MARTES",
          "MIÉRCOLES",
          "JUEVES",
          "VIERNES",
          "SÁBADO",
      ]
      fin_txt = f"{sabado_semana.strftime('%Y-%m-%d')} (Sábado)"
    else:
      dias_semana_nombres = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES"]
      viernes_semana = lunes_semana + datetime.timedelta(days=4)
      fin_txt = f"{viernes_semana.strftime('%Y-%m-%d')} (Viernes)"

    st.markdown(
        f"##### 📆 **Semana Actual:** Del **{lunes_semana.strftime('%Y-%m-%d')}**"
        f" (Lunes) al **{fin_txt}**"
    )

    # RENDERIZADO DE MATRIZ SEMANAL CON DETECCIÓN DE FRANJAS LIBRES Y DÍA ACTUAL
    cols_dias = st.columns(len(dias_semana_nombres))

    for idx_d, dia_nom in enumerate(dias_semana_nombres):
      fecha_dia_actual = lunes_semana + datetime.timedelta(days=idx_d)
      dia_norm = normalizar_texto(dia_nom)
      es_dia_hoy = fecha_dia_actual == fecha_hoy

      with cols_dias[idx_d]:
        # Encabezado Verde Resaltado si es HOY
        if es_dia_hoy:
          st.markdown(
              f"""
                        <div class="header-hoy">
                            <div style="font-size:0.75rem; font-weight:800;">📍 HOY</div>
                            <h3 style="margin:0; padding:0; font-size:1.1rem; color:#6ee7b7;">{dia_nom}</h3>
                            <div style="font-size:0.85rem; font-weight:700;">{fecha_dia_actual.strftime('%d/%m')}</div>
                        </div>
                    """,
              unsafe_allow_html=True,
          )
        else:
          st.markdown(
              f"### {dia_nom}\n**{fecha_dia_actual.strftime('%d/%m')}**"
          )

        st.markdown("---")

        clases_dia = df_filtered[
            df_filtered["dia"].apply(normalizar_texto) == dia_norm
        ].sort_values(by="hora_inicio")

        # Rango operativo oficial (07:00 a 19:00)
        hora_cursor = 7
        hora_limite = 19

        if clases_dia.empty:
          st.markdown(
              """
                        <div class="card-disponible">
                            <div style="font-weight:700; font-size:0.85rem;">🟢 DISPONIBLE</div>
                            <div style="font-size:0.75rem; margin-top:2px;">07:00 - 19:00 (Todo el día libre)</div>
                        </div>
                    """,
              unsafe_allow_html=True,
          )
        else:
          for _, c in clases_dia.iterrows():
            h_ini = int(c["hora_inicio"])
            h_fin = int(c["hora_fin"])

            # Si hay un espacio libre antes de esta clase, dibujar recuadro verde DISPONIBLE
            if h_ini > hora_cursor:
              st.markdown(
                  f"""
                                <div class="card-disponible">
                                    <div style="font-weight:700; font-size:0.8rem;">🟢 DISPONIBLE</div>
                                    <div style="font-size:0.72rem; margin-top:2px;">⏰ {hora_cursor:02d}:00 - {h_ini:02d}:00</div>
                                </div>
                            """,
                  unsafe_allow_html=True,
              )

            # Dibujar la Clase
            es_evento = c["tipo_evento"].lower() == "evento"
            asig_upper = str(c["asignatura"]).upper()
            doc_upper = str(c["docente"]).upper()
            salon_upper = str(c["espacio"]).upper()

            if es_evento:
              style_card = ""
              class_attr = "class-card class-card-evento"
            else:
              style_card = generar_estilo_color_materia(asig_upper)
              class_attr = "class-card"

            st.markdown(
                f"""
                        <div class="{class_attr}" style="{style_card}">
                            <div class="class-time">⏰ {h_ini:02d}:00 - {h_fin:02d}:00 | {salon_upper}</div>
                            <div class="class-title">{asig_upper}</div>
                            <div class="class-doc">👨‍🏫 {doc_upper}</div>
                        </div>
                    """,
                unsafe_allow_html=True,
            )

            hora_cursor = max(hora_cursor, h_fin)

          # Si queda espacio libre al final de la jornada (hasta las 19:00)
          if hora_cursor < hora_limite:
            st.markdown(
                f"""
                            <div class="card-disponible">
                                <div style="font-weight:700; font-size:0.8rem;">🟢 DISPONIBLE</div>
                                <div style="font-size:0.72rem; margin-top:2px;">⏰ {hora_cursor:02d}:00 - {hora_limite:02d}:00</div>
                            </div>
                        """,
                unsafe_allow_html=True,
            )

# -----------------------------------------------------------------------------
# TAB 2: CONFIRMACIÓN DE CARGA SEMESTRAL
# -----------------------------------------------------------------------------
with tab_cargue:
  st.markdown("### 1️⃣ Paso 1: Configurar Fechas del Semestre")
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
    st.markdown("### 2️⃣ Paso 2: Cargar y Validar Archivo de Horarios")

    uploaded_file = st.file_uploader(
        "Sube el archivo Excel formateado (`.xlsx`):", type=["xlsx"]
    )

    if uploaded_file is not None:
      try:
        st.session_state.df_unicas = controller.validar_y_procesar_excel(
            uploaded_file
        )

        df_edit = st.session_state.df_unicas[[
            "ESPACIO / SALÓN",
            "DÍA",
            "HORA INICIO (24H)",
            "HORA FIN (24H)",
            "ASIGNATURA",
            "DOCENTE",
        ]].copy()
        df_edit["ESPACIO / SALÓN"] = df_edit["ESPACIO / SALÓN"].str.upper()
        df_edit["DÍA"] = df_edit["DÍA"].str.upper()
        df_edit["ASIGNATURA"] = df_edit["ASIGNATURA"].str.upper()
        df_edit["DOCENTE"] = df_edit["DOCENTE"].str.upper()

        st.markdown("---")
        st.markdown("### 3️⃣ Paso 3: Confirmar Oferta Académica")

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("📚 Clases a Programar", len(df_edit))
        col_m2.metric(
            "🏛️ Aulas Asignadas", len(df_edit["ESPACIO / SALÓN"].unique())
        )
        col_m3.metric("⏰ Horario Oficial Funcionarios", "07:00 a 19:00")

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
        else:
          st.markdown("---")
          if st.button("🚀 Confirmar y Guardar Semestre", type="primary"):
            controller.proyectar_y_guardar_semestre(
                df_editado, f_inicio, f_fin
            )
            total_registros = len(db.obtener_todos_los_horarios())
            mostrar_popup_exito(total_registros, f_inicio, f_fin)

      except ValueError as val_err:
        st.error(str(val_err))
      except Exception as e:
        st.error(f"Error inesperado al procesar el archivo: {e}")

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