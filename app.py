import datetime
import hashlib
import unicodedata
import pandas as pd
import streamlit as st
from controllers.horario_controller import HorarioController
from models.database import DatabaseModel

st.set_page_config(
    page_title="Consulta Aulas DTE",
    page_icon="sources\\lg_upn.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

db = DatabaseModel()
controller = HorarioController(db)

ADMIN_USER = "admin"
ADMIN_PASSWORD_HASH = (
    "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
)


def normalizar_texto(texto):
  if not isinstance(texto, str):
    return ""
  texto = texto.strip().lower()
  nfkd = unicodedata.normalize("NFKD", texto)
  return "".join([c for c in nfkd if not unicodedata.combining(c)])


def generar_estilo_color_materia(nombre_asignatura):
  nombre_norm = normalizar_texto(nombre_asignatura)
  hash_hex = hashlib.md5(nombre_norm.encode("utf-8")).hexdigest()
  hue = int(hash_hex[:4], 16) % 360

  bg_color = f"hsl({hue}, 65%, 18%)"
  border_color = f"hsl({hue}, 80%, 55%)"
  text_color = f"hsl({hue}, 90%, 85%)"

  return (
      f"background: {bg_color}; border-left: 4px solid {border_color}; color:"
      f" {text_color};"
  )


# Función Callback para Resetear Filtros sin Violación de Estado en Streamlit
def resetear_filtros_callback():
  st.session_state["input_asig"] = ""
  st.session_state["input_doc"] = ""
  st.session_state["input_salon"] = "TODOS"
  st.session_state["input_horas"] = (7, 19)


# -----------------------------------------------------------------------------
# ESTILOS CSS CON TÍTULO CENTRADO Y TRANSICIONES INTERACTIVAS
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        margin-top: 0px;
        margin-bottom: 4px;
        color: #f8fafc;
        text-align: center;
    }

    .day-header-box {
        height: 65px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 12px;
        box-sizing: border-box;
    }

    .day-header-hoy {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%) !important;
        border: 2px solid #10b981 !important;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }

    .day-title {
        font-weight: 800;
        font-size: 1.05rem;
        margin: 0;
        line-height: 1.2;
    }

    .day-date {
        font-size: 0.82rem;
        opacity: 0.8;
        margin-top: 2px;
    }

    .class-card, .card-disponible {
        border-radius: 6px;
        padding: 8px 10px;
        margin-bottom: 8px;
        min-height: 85px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        box-sizing: border-box;
        cursor: pointer;
        position: relative;
        outline: none;
        transition: transform 0.18s cubic-bezier(0.25, 1, 0.5, 1), box-shadow 0.18s ease-in-out, z-index 0s 0.18s;
    }

    .class-card:focus, .card-disponible:focus,
    .class-card:active, .card-disponible:active {
        transform: scale(1.035);
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.5);
        z-index: 20;
        transition: transform 0.18s cubic-bezier(0.25, 1, 0.5, 1), box-shadow 0.18s ease-in-out;
    }

    .class-card-evento {
        background: linear-gradient(135deg, #451a03 0%, #1c0901 100%) !important;
        border-left: 4px solid #f59e0b !important;
    }

    .card-disponible {
        background: rgba(16, 185, 129, 0.10);
        border: 1px dashed #10b981;
        border-left: 4px solid #10b981;
        color: #a7f3d0;
        text-align: center;
    }

    .class-title {
        font-weight: 700;
        font-size: 0.82rem;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .class-card:focus .class-title,
    .class-card:focus .class-doc {
        white-space: normal !important;
        overflow: visible !important;
    }

    .class-doc {
        font-size: 0.74rem;
        opacity: 0.85;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .class-time {
        font-size: 0.70rem;
        font-weight: 600;
        margin-bottom: 3px;
        opacity: 0.9;
    }

    .excel-template-box {
        background-color: rgba(255, 255, 255, 0.04);
        border: 2px dashed #8b5cf6;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
        font-family: monospace;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# AUTENTICACIÓN ADMIN (SIDEBAR)
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False

st.sidebar.title("🔐 Acceso Administrativo")

if not st.session_state.authenticated:
  with st.sidebar.form("form_login"):
    user_input = st.text_input("Usuario:")
    pass_input = st.text_input("Contraseña:", type="password")
    submit_login = st.form_submit_button("Iniciar Sesión", type="primary")

    if submit_login:
      pass_hash = hashlib.sha256(pass_input.encode("utf-8")).hexdigest()
      if user_input == ADMIN_USER and pass_hash == ADMIN_PASSWORD_HASH:
        st.session_state.authenticated = True
        st.sidebar.success("🔑 Sesión iniciada correctamente.")
        st.rerun()
      else:
        st.sidebar.error("Usuario o contraseña incorrectos.")
else:
  st.sidebar.success("🟢 Modo Administrador Activo")
  if st.sidebar.button("Cerrar Sesión"):
    st.session_state.authenticated = False
    st.rerun()


# Modales
@st.dialog("🎉 Carga Exitosa")
def mostrar_popup_exito(total_registros, f_ini, f_fin):
  st.success("### ¡Las asignaturas han sido guardadas!")
  st.write(
      f"• **Periodo Configurado:** Del **{f_ini}** al **{f_fin}**\n"
      f"• **Sesiones Proyectadas:** **{total_registros} clases** registradas."
  )
  if st.button("Ir a Consulta de Horarios ➡️", type="primary"):
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

# -----------------------------------------------------------------------------
# ENCABEZADO CENTRADO CON TÍTULO Y PERIODO
# -----------------------------------------------------------------------------
st.markdown(
    '<h1 class="main-title">Consulta Aulas DTE</h1>', unsafe_allow_html=True
)

if f_ini_db:
  semestre_num = 1 if f_ini_db.month <= 6 else 2
  periodo_str = f"{f_ini_db.year}-{semestre_num}"
else:
  periodo_str = "SIN CARGUE"

if es_vigente:
  st.caption(
      f"<div style='text-align: center; width: 100%;'>🟢 <b>Semestre"
      f" Activo:</b> {periodo_str} ({f_ini_db} al {f_fin_db})</div>",
      unsafe_allow_html=True,
  )
else:
  st.caption(
      f"<div style='text-align: center; width: 100%;'>⚠️ <b>Estado:</b>"
      f" {msj_vigencia}</div>",
      unsafe_allow_html=True,
  )

st.markdown("---")

if st.session_state.authenticated:
  tabs = st.tabs([
      "📅 Consulta de Horarios (Público / QR)",
      "📋 Confirmación de Carga Semestral (Admin)",
      "➕ Eventos y Cambios (Admin)",
  ])
  tab_horarios, tab_cargue, tab_eventos = tabs[0], tabs[1], tabs[2]
else:
  tabs = st.tabs(["📅 Consulta de Horarios (Público / QR)"])
  tab_horarios = tabs[0]
  tab_cargue, tab_eventos = None, None


# -----------------------------------------------------------------------------
# HELPER DE RENDERIZADO MATRICIAL SIMÉTRICO DINÁMICO
# -----------------------------------------------------------------------------
def renderizar_matriz_semanal_aula(
    df_aula,
    dias_semana_nombres,
    lunes_semana,
    fecha_hoy,
    nombre_aula=None,
    ocultar_disponibles=False,
    solo_disponibles=False,
    rango_horas=(7, 19),
):
  MAPA_DIAS_INDEX = {
      "LUNES": 0,
      "MARTES": 1,
      "MIÉRCOLES": 2,
      "JUEVES": 3,
      "VIERNES": 4,
      "SÁBADO": 5,
      "DOMINGO": 6,
  }

  cols_dias = st.columns(len(dias_semana_nombres))
  salon_upper = str(nombre_aula).upper() if nombre_aula else None
  hora_min_filtro, hora_max_filtro = rango_horas

  for idx_col, dia_nom in enumerate(dias_semana_nombres):
    idx_d = MAPA_DIAS_INDEX.get(dia_nom.upper(), idx_col)
    fecha_dia_actual = lunes_semana + datetime.timedelta(days=idx_d)
    dia_norm = normalizar_texto(dia_nom)
    es_dia_hoy = fecha_dia_actual == fecha_hoy

    with cols_dias[idx_col]:
      header_class = (
          "day-header-box day-header-hoy" if es_dia_hoy else "day-header-box"
      )
      hoy_badge = (
          "<div style='font-size:0.65rem; font-weight:800; color:#6ee7b7;"
          " margin-bottom:1px;'>📍 HOY</div>"
          if es_dia_hoy
          else ""
      )
      color_title = "#6ee7b7" if es_dia_hoy else "#f8fafc"
      fecha_fmt = fecha_dia_actual.strftime("%d/%m")

      header_html = (
          f"<div class='{header_class}'>"
          f"{hoy_badge}"
          f"<div class='day-title' style='color:{color_title};'>{dia_nom}</div>"
          f"<div class='day-date'>{fecha_fmt}</div>"
          "</div>"
      )
      st.markdown(header_html, unsafe_allow_html=True)

      clases_dia = df_aula[
          df_aula["dia"].apply(normalizar_texto) == dia_norm
      ].sort_values(by="hora_inicio")

      hora_cursor = hora_min_filtro
      hora_limite = hora_max_filtro

      if clases_dia.empty:
        if not ocultar_disponibles or solo_disponibles:
          salon_txt = f" | {salon_upper}" if salon_upper else ""
          card_free = (
              "<div class='card-disponible' tabindex='0'><div"
              " style='font-weight:700; font-size:0.85rem;'>🟢"
              " DISPONIBLE</div><div class='class-time' style='margin-top:3px;'>⏰"
              f" {hora_cursor:02d}:00 - {hora_limite:02d}:00{salon_txt}</div></div>"
          )
          st.markdown(card_free, unsafe_allow_html=True)
      else:
        for _, c in clases_dia.iterrows():
          h_ini = int(c["hora_inicio"])
          h_fin = int(c["hora_fin"])

          h_ini_vis = max(h_ini, hora_min_filtro)
          h_fin_vis = min(h_fin, hora_max_filtro)
          salon_row = str(c["espacio"]).upper()

          if (
              h_ini_vis > hora_cursor
              and not ocultar_disponibles
              or solo_disponibles
          ):
            card_prev = (
                "<div class='card-disponible' tabindex='0'><div"
                " style='font-weight:700; font-size:0.8rem;'>🟢"
                " DISPONIBLE</div><div class='class-time'"
                f" style='margin-top:3px;'>⏰ {hora_cursor:02d}:00 -"
                f" {h_ini_vis:02d}:00 | {salon_row}</div></div>"
            )
            st.markdown(card_prev, unsafe_allow_html=True)

          if not solo_disponibles:
            tipo_ev = str(c.get("tipo_evento", "")).lower()
            es_evento = tipo_ev == "evento"
            asig_upper = str(c.get("asignatura", "")).upper()
            doc_upper = str(c.get("docente", "")).upper()

            obs_val = c.get("observacion", "")
            obs_txt = (
                f"<br><small><b>Obs:</b> {str(obs_val).upper()}</small>"
                if pd.notna(obs_val) and str(obs_val).strip()
                else ""
            )

            if es_evento:
              style_card = ""
              class_attr = "class-card class-card-evento"
            else:
              style_card = generar_estilo_color_materia(asig_upper)
              class_attr = "class-card"

            card_class_html = (
                f"<div class='{class_attr}' style='{style_card}'"
                f" tabindex='0'><div class='class-time'>⏰ {h_ini:02d}:00 -"
                f" {h_fin:02d}:00 | {salon_row}</div><div class='class-title'"
                f" title='{asig_upper}'>{asig_upper}</div><div"
                f" class='class-doc' title='{doc_upper}'>👨‍🏫"
                f" {doc_upper}{obs_txt}</div></div>"
            )
            st.markdown(card_class_html, unsafe_allow_html=True)

          hora_cursor = max(hora_cursor, h_fin_vis)

        if (
            hora_cursor < hora_limite
            and not ocultar_disponibles
            or solo_disponibles
        ):
          card_post = (
              "<div class='card-disponible' tabindex='0'><div"
              " style='font-weight:700; font-size:0.8rem;'>🟢"
              " DISPONIBLE</div><div class='class-time'"
              " style='margin-top:3px;'>⏰"
              f" {hora_cursor:02d}:00 - {hora_limite:02d}:00 |"
              f" {salon_upper if salon_upper else 'VARIAS AULAS'}</div></div>"
          )
          st.markdown(card_post, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 1: CONSULTA DE HORARIOS PÚBLICA CON FILTROS AVANZADOS
# -----------------------------------------------------------------------------
with tab_horarios:
  col_h1, col_h2 = st.columns([3, 1])
  with col_h1:
    st.subheader("📅 Horario Semanal por Aulas")
  with col_h2:
    if st.session_state.authenticated:
      if st.button("🗑️ Vaciar Base de Datos", type="secondary"):
        mostrar_popup_vaciar_db()

  df_horarios = db.obtener_todos_los_horarios()

  if df_horarios.empty:
    st.info(
        "La base de datos se encuentra vacía. Un administrador debe realizar el"
        " cargue del semestre."
    )
  else:
    # Inicializar valores en session_state ANTES de crear los widgets
    if "input_asig" not in st.session_state:
      st.session_state["input_asig"] = ""
    if "input_doc" not in st.session_state:
      st.session_state["input_doc"] = ""
    if "input_salon" not in st.session_state:
      st.session_state["input_salon"] = "TODOS"
    if "input_horas" not in st.session_state:
      st.session_state["input_horas"] = (7, 19)

    col_f1, col_f2, col_f3, col_f4 = st.columns([3, 3, 3, 2])

    salones_unicos = sorted(
        [str(s).upper() for s in df_horarios["espacio"].unique()]
    )

    with col_f1:
      salon_sel = st.selectbox(
          "Filtrar por Salón / Aula:",
          ["TODOS"] + salones_unicos,
          key="input_salon",
      )

    with col_f2:
      busqueda_asig = st.text_input(
          "🔍 Buscar por Asignatura:",
          placeholder="Ej. programacion o disponible",
          key="input_asig",
      )

    with col_f3:
      busqueda_doc = st.text_input(
          "👨‍🏫 Buscar por Docente:",
          placeholder="Ej. nicolas",
          key="input_doc",
      )

    with col_f4:
      st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
      st.button(
          "🧹 Limpiar Filtros",
          on_click=resetear_filtros_callback,
          use_container_width=True,
      )

    st.markdown("⏰ **Filtrar Franja Horaria (Horas exactas):**")
    rango_horas = st.slider(
        "Seleccionar rango de horas:",
        min_value=7,
        max_value=19,
        format="%d:00 hrs",
        label_visibility="collapsed",
        key="input_horas",
    )

    fecha_hoy = datetime.date.today()
    lunes_semana = fecha_hoy - datetime.timedelta(days=fecha_hoy.weekday())
    sabado_semana = lunes_semana + datetime.timedelta(days=5)

    df_filtered = df_horarios.copy()
    df_filtered["fecha_dt"] = pd.to_datetime(df_filtered["fecha"]).dt.date
    df_filtered = df_filtered[
        (df_filtered["fecha_dt"] >= lunes_semana)
        & (df_filtered["fecha_dt"] <= sabado_semana)
    ]

    q_asig = normalizar_texto(busqueda_asig)
    q_doc = normalizar_texto(busqueda_doc)

    solo_disponibles = (
        "disponible" in q_asig
        or "libre" in q_asig
        or "disponible" in q_doc
        or "libre" in q_doc
    )
    hay_busqueda_activa = bool(
        q_asig.strip() or q_doc.strip()
    ) and not solo_disponibles

    # Filtrado exacto / parcial sin residuo
    if hay_busqueda_activa:
      if q_asig.strip():
        df_filtered = df_filtered[
            df_filtered["asignatura"]
            .apply(normalizar_texto)
            .str.contains(q_asig, regex=False)
        ]
      if q_doc.strip():
        df_filtered = df_filtered[
            df_filtered["docente"]
            .apply(normalizar_texto)
            .str.contains(q_doc, regex=False)
        ]

    h_min, h_max = rango_horas
    df_filtered = df_filtered[
        (df_filtered["hora_inicio"] < h_max)
        & (df_filtered["hora_fin"] > h_min)
    ]

    DIAS_ORDENADOS = [
        "LUNES",
        "MARTES",
        "MIÉRCOLES",
        "JUEVES",
        "VIERNES",
        "SÁBADO",
    ]

    if hay_busqueda_activa:
      dias_con_clase = (
          df_filtered["dia"].apply(lambda x: str(x).upper()).unique()
      )
      dias_semana_nombres = [
          d
          for d in DIAS_ORDENADOS
          if normalizar_texto(d)
          in [normalizar_texto(dc) for dc in dias_con_clase]
      ]
    else:
      hay_clases_sabado = "sabado" in df_filtered["dia"].apply(
          normalizar_texto
      ).values or "sábado" in df_filtered["dia"].apply(normalizar_texto).values
      dias_semana_nombres = (
          ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO"]
          if hay_clases_sabado
          else ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES"]
      )

    fin_txt = (
        f"{sabado_semana.strftime('%Y-%m-%d')} (Sábado)"
        if "SÁBADO" in dias_semana_nombres
        else (
            f"{(lunes_semana + datetime.timedelta(days=4)).strftime('%Y-%m-%d')}"
            " (Viernes)"
        )
    )

    filtro_hora_activo = rango_horas != (7, 19)
    st.markdown(
        f"##### 📆 **Semana Actual:** Del **{lunes_semana.strftime('%Y-%m-%d')}**"
        f" (Lunes) al **{fin_txt}**"
        + (
            f" | ⏰ **Franja:** {rango_horas[0]}:00 - {rango_horas[1]}:00"
            if filtro_hora_activo
            else ""
        )
    )

    if hay_busqueda_activa and df_filtered.empty:
      st.warning(
          "⚠️ **No se encontraron resultados.** Por favor verifica lo que"
          " escribiste o limpia los filtros."
      )
    else:
      if (
          salon_sel == "TODOS"
          and not hay_busqueda_activa
          and not solo_disponibles
          and not filtro_hora_activo
      ):
        for salon in salones_unicos:
          df_aula = df_filtered[
              df_filtered["espacio"].apply(normalizar_texto)
              == normalizar_texto(salon)
          ]
          with st.expander(f"🏛️ **{salon}**", expanded=True):
            renderizar_matriz_semanal_aula(
                df_aula,
                dias_semana_nombres,
                lunes_semana,
                fecha_hoy,
                nombre_aula=salon,
                ocultar_disponibles=hay_busqueda_activa,
                solo_disponibles=solo_disponibles,
                rango_horas=rango_horas,
            )
      else:
        if salon_sel != "TODOS":
          df_filtered = df_filtered[
              df_filtered["espacio"].apply(normalizar_texto)
              == normalizar_texto(salon_sel)
          ]

        renderizar_matriz_semanal_aula(
            df_filtered,
            dias_semana_nombres,
            lunes_semana,
            fecha_hoy,
            nombre_aula=salon_sel if salon_sel != "TODOS" else None,
            ocultar_disponibles=hay_busqueda_activa,
            solo_disponibles=solo_disponibles,
            rango_horas=rango_horas,
        )

# -----------------------------------------------------------------------------
# TAB 2 & 3: ADMINISTRACIÓN
# -----------------------------------------------------------------------------
if st.session_state.authenticated and tab_cargue:
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
                " rango oficial (07:00 a 19:00)."
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
          err_msg = str(val_err)
          st.error(
              "🚨 **Error de Formato:** El archivo subido no cumple con"
              " ninguno de los dos formatos soportados."
          )

          st.markdown(
              """
                    <div class="excel-template-box">
                    <h4>📋 Formatos de Excel Compatibles:</h4>
                    
                    <b>1. Formato Cuadrícula de Coordinación (Conversión Automática)</b><br>
                    • Libro con la matriz de horarios distribuida por franjas horarias (7 a 19) y salones (E105, B222).<br>
                    • La fila inicial de cada salón debe listar los días de la semana y la columna A las horas en formato entero.<br><br>
                    
                    <b>2. Formato Estructurado de Base de Datos</b><br>
                    • Nombre obligatorio de pestaña: <b><code>BD_Calendario_Semestre</code></b><br>
                    • Columnas requeridas:<br>
                    | ESPACIO / SALÓN | DÍA | HORA INICIO (24H) | HORA FIN (24H) | ASIGNATURA | DOCENTE |<br>
                    | E105 (SALA CAD) | LUNES | 10 | 12 | PROGRAMACION | NICOLAS |
                    </div>
                """,
              unsafe_allow_html=True,
          )

if st.session_state.authenticated and tab_eventos:
  with tab_eventos:
    st.subheader("➕ Registrar Evento o Reserva Especial")

    ev_salon = st.selectbox("1️⃣ Salón / Aula:", [
        "E105 (SALA CAD)",
        "B222 (SALA COMPUTADORES)",
        "B222 (SALÓN POSGRADOS)",
    ])
    ev_fecha = st.date_input(
        "2️⃣ Fecha del Evento:", value=datetime.date.today()
    )

    col_h1, col_h2 = st.columns(2)
    ev_h_ini = col_h1.number_input(
        "3️⃣ Hora Inicio (24H):", min_value=7, max_value=18, value=10
    )
    ev_h_fin = col_h2.number_input(
        "4️⃣ Hora Fin (24H):", min_value=8, max_value=19, value=12
    )

    ev_asig = st.text_input(
        "5️⃣ Nombre del Evento:", placeholder="Ej. CONFERENCIA IA"
    )
    ev_doc = st.text_input(
        "6️⃣ Responsable del Evento:", placeholder="Ej. ING. GARCÍA"
    )

    fecha_ev_str = ev_fecha.strftime("%Y-%m-%d")
    conflictos = db.verificar_conflicto_horario(
        ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin
    )

    ev_obs = ""
    requiere_obs = False

    if conflictos:
      requiere_obs = True
      st.error(
          f"🚨 **Espacio Ya Ocupado:** El salón **{ev_salon}** ya tiene"
          f" programación el **{fecha_ev_str}** entre las **{ev_h_ini}:00 y"
          f" {ev_h_fin}:00 hrs**:"
      )
      for c in conflictos:
        c_asig, c_doc, c_tipo, c_ini, c_fin = (
            c[1].upper(),
            c[2].upper(),
            c[5].upper(),
            c[3],
            c[4],
        )
        st.warning(
            f"• **{c_asig}** ({c_tipo}) | Responsable: **{c_doc}** | Horario:"
            f" {c_ini}:00 - {c_fin}:00"
        )

      st.markdown("---")
      ev_obs = st.text_area(
          "7️⃣ Observaciones (OBLIGATORIO por ocupar un espacio asignado):",
          placeholder=(
              "Especifica la razón por la cual se reasigna el espacio..."
          ),
      )
    else:
      st.success(
          f"🟢 **Aula Libre:** El salón {ev_salon} está completamente"
          f" disponible en la franja {ev_h_ini}:00 a {ev_h_fin}:00 hrs."
      )

    st.markdown("---")
    if st.button("💾 Guardar y Asignar Evento", type="primary"):
      if ev_h_fin <= ev_h_ini:
        st.error("La Hora Fin debe ser mayor a la Hora Inicio.")
      elif not ev_asig.strip() or not ev_doc.strip():
        st.error(
            "Debes ingresar el Nombre del Evento y el Responsable."
        )
      elif requiere_obs and not ev_obs.strip():
        st.error(
            "⚠️ **Observación Requerida:** Debes ingresar la razón de la"
            " asignación sobre un espacio que ya estaba ocupado."
        )
      else:
        db.agregar_evento_especial(
            ev_salon,
            fecha_ev_str,
            ev_h_ini,
            ev_h_fin,
            ev_asig,
            ev_doc,
            ev_obs,
        )
        st.success("🎉 Evento asignado correctamente.")
        st.rerun()