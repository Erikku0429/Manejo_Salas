import datetime
import hashlib
import os
import unicodedata
import pandas as pd
import streamlit as st
from controllers.horario_controller import HorarioController
from models.database import DatabaseModel

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA (Plegado por defecto para móviles)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Consulta Aulas DTE",
    page_icon=(
        "sources/lg_upn.png" if os.path.exists("sources/lg_upn.png") else "🏫"
    ),
    layout="wide",
    initial_sidebar_state="collapsed",  # Mantiene el menú cerrado en celulares al cargar
)

db = DatabaseModel()
controller = HorarioController(db)


# -----------------------------------------------------------------------------
# 2. FUNCIONES AUXILIARES Y SEGURIDAD
# -----------------------------------------------------------------------------
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

  # Fondo con contraste equilibrado y texto blanco garantizado
  bg_color = f"hsl({hue}, 60%, 22%)"
  border_color = f"hsl({hue}, 85%, 50%)"
  text_color = "#ffffff"

  return (
      f"background: {bg_color}; border-left: 4px solid {border_color}; color:"
      f" {text_color};"
  )


def resetear_filtros_callback():
  st.session_state["input_asig"] = ""
  st.session_state["input_doc"] = ""
  st.session_state["input_salon"] = "TODOS"
  st.session_state["input_horas"] = (7, 19)


def ir_a_pestaña(nombre_tab):
  st.session_state["active_tab"] = nombre_tab


def validar_archivo_excel(uploaded_file, max_mb=10):
  """Valida extensión y tamaño del archivo cargado para proteger el servidor."""
  if uploaded_file is not None:
    if uploaded_file.size > max_mb * 1024 * 1024:
      st.error(f"⚠️ El archivo supera el límite permitido de {max_mb} MB.")
      return False
    if not uploaded_file.name.endswith((".xlsx", ".xls")):
      st.error(
          "⚠️ Formato no permitido. Solo se aceptan archivos Excel (.xlsx,"
          " .xls)."
      )
      return False
    return True
  return False


# -----------------------------------------------------------------------------
# 3. ESTILOS CSS ADAPTATIVOS (MODO CLARO Y MODO OSCURO)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Título principal adaptativo */
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        margin-top: 0px;
        margin-bottom: 4px;
        color: var(--text-color, #1e293b);
        text-align: center;
    }

    /* Cajas de cabecera de salones y días */
    .day-header-box {
        border-radius: 8px;
        background: rgba(150, 150, 150, 0.08);
        border: 1px solid rgba(150, 150, 150, 0.25);
        margin-bottom: 12px;
        box-sizing: border-box;
    }

    .day-header-hoy {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%) !important;
        border: 2px solid #10b981 !important;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }

    /* Títulos de salón y días en alto contraste */
    .day-title {
        font-weight: 800;
        font-size: 0.85rem;
        margin: 0;
        line-height: 1.2;
        color: var(--text-color, #0f172a) !important;
    }

    .day-date {
        font-size: 0.82rem;
        opacity: 0.85;
        margin-top: 2px;
        color: var(--text-color, #334155);
    }

    /* Tarjetas de clase y disponibilidad */
    .class-card, .card-disponible {
        border-radius: 6px;
        padding: 6px 8px;
        margin-bottom: 8px;
        min-height: 75px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        box-sizing: border-box;
        cursor: pointer;
        position: relative;
        outline: none;
        transition: transform 0.18s cubic-bezier(0.25, 1, 0.5, 1), box-shadow 0.18s ease-in-out;
    }

    .class-card-evento {
        background: linear-gradient(135deg, #78350f 0%, #451a03 100%) !important;
        border-left: 4px solid #f59e0b !important;
        color: #fef3c7 !important;
    }

    /* Tarjeta DISPONIBLE adaptada con alto contraste */
    .card-disponible {
        background: rgba(16, 185, 129, 0.15) !important;
        border: 1px dashed #059669 !important;
        border-left: 4px solid #059669 !important;
        color: #047857 !important;
        text-align: center;
    }

    .card-disponible .class-time, 
    .card-disponible div {
        color: #047857 !important;
        font-weight: 700 !important;
    }

    .class-title {
        font-weight: 700;
        font-size: 0.76rem;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .class-doc {
        font-size: 0.70rem;
        opacity: 0.9;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .class-time {
        font-size: 0.68rem;
        font-weight: 600;
        margin-bottom: 3px;
        opacity: 0.95;
    }

    .event-agenda-card {
        background: linear-gradient(135deg, #451a03 0%, #1c0901 100%);
        border: 1px solid #78350f;
        border-left: 5px solid #f59e0b;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 14px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        color: #fef3c7;
    }

    .excel-template-box {
        background-color: rgba(139, 92, 246, 0.08);
        border: 2px dashed #8b5cf6;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
        font-family: monospace;
        color: var(--text-color, #1e293b);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 4. AUTENTICACIÓN ADMIN SEGURA (SIDEBAR)
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False

st.sidebar.title("🔐 Acceso Administrativo")

# Manejo de credenciales con fallback seguro para desarrollo local sin secrets.toml
try:
  ADMIN_USER = st.secrets["admin_credentials"]["username"]
  ADMIN_PASSWORD_HASH = st.secrets["admin_credentials"]["password_hash"]
except Exception:
  ADMIN_USER = "admin"
  ADMIN_PASSWORD_HASH = (
      "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
  )

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


# -----------------------------------------------------------------------------
# 5. MODALES / VENTANAS EMERGENTES (DIALOGS)
# -----------------------------------------------------------------------------
@st.dialog("🎉 Carga Semestral Exitosa")
def mostrar_popup_exito(total_registros, f_ini, f_fin):
  st.success("### ¡Las asignaturas han sido guardadas!")
  st.write(
      f"• **Periodo Configurado:** Del **{f_ini}** al **{f_fin}**\n"
      f"• **Sesiones Proyectadas:** **{total_registros} clases** registradas."
  )
  if st.button(
      "Ir a Consulta de Horarios ➡️",
      type="primary",
      on_click=ir_a_pestaña,
      args=("📅 Consulta de Horarios (Público / QR)",),
  ):
    st.rerun()


@st.dialog("🎉 Evento Asignado con Éxito")
def mostrar_popup_evento_exito(
    nombre_evento, salon, fecha, hora_ini, hora_fin, responsable
):
  st.success("### ¡El evento ha sido registrado correctamente!")
  st.markdown(
      f"• **Evento:** **{nombre_evento}**\n"
      f"• **Lugar:** **{salon}**\n"
      f"• **Fecha:** **{fecha}**\n"
      f"• **Horario:** **{hora_ini}:00 - {hora_fin}:00 hrs**\n"
      f"• **Responsable:** **{responsable}**"
  )
  if st.button(
      "Ir a Próximos Eventos ➡️",
      type="primary",
      on_click=ir_a_pestaña,
      args=("📢 Próximos Eventos",),
  ):
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
# 6. ENCABEZADO Y TABS
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
  lista_tabs = [
      "📅 Consulta de Horarios (Público / QR)",
      "📢 Próximos Eventos",
      "📋 Confirmación de Carga Semestral (Admin)",
      "➕ Eventos y Cambios (Admin)",
  ]
else:
  lista_tabs = [
      "📅 Consulta de Horarios (Público / QR)",
      "📢 Próximos Eventos",
  ]

if "active_tab" not in st.session_state or st.session_state[
    "active_tab"
] not in lista_tabs:
  st.session_state["active_tab"] = lista_tabs[0]

tabs = st.tabs(lista_tabs)

if st.session_state.authenticated:
  tab_horarios, tab_eventos_pub, tab_cargue, tab_eventos_adm = (
      tabs[0],
      tabs[1],
      tabs[2],
      tabs[3],
  )
else:
  tab_horarios, tab_eventos_pub = tabs[0], tabs[1]
  tab_cargue, tab_eventos_adm = None, None


# -----------------------------------------------------------------------------
# 7. HELPER DE RENDERIZADO MATRICIAL CON ALINEACIÓN PERFECTA
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
    mostrar_encabezado_dia=True,
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
  es_admin = st.session_state.authenticated

  aulas_totales = (
      sorted(
          [
              str(s).upper()
              for s in df_aula["espacio"].unique()
              if pd.notna(s) and str(s).strip()
          ]
      )
      if "espacio" in df_aula.columns
      else []
  )

  for idx_col, dia_nom in enumerate(dias_semana_nombres):
    idx_d = MAPA_DIAS_INDEX.get(dia_nom.upper(), idx_col)
    fecha_dia_actual = lunes_semana + datetime.timedelta(days=idx_d)
    dia_norm = normalizar_texto(dia_nom)
    es_dia_hoy = fecha_dia_actual == fecha_hoy

    with cols_dias[idx_col]:
      if mostrar_encabezado_dia:
        header_class = (
            "day-header-box day-header-hoy" if es_dia_hoy else "day-header-box"
        )
        hoy_badge = (
            "<div style='font-size:0.65rem; font-weight:800; color:#6ee7b7;"
            " margin-bottom:1px;'>📍 HOY</div>"
            if es_dia_hoy
            else ""
        )
        color_title = "#6ee7b7" if es_dia_hoy else "var(--text-color, #0f172a)"
        fecha_fmt = fecha_dia_actual.strftime("%d/%m")

        header_html = (
            f"<div class='{header_class}'>"
            f"{hoy_badge}"
            f"<div class='day-title'"
            f" style='color:{color_title};'>{dia_nom}</div>"
            f"<div class='day-date'>{fecha_fmt}</div>"
            "</div>"
        )
        st.markdown(header_html, unsafe_allow_html=True)

      clases_dia = df_aula[
          df_aula["dia"].apply(normalizar_texto) == dia_norm
      ].sort_values(by="hora_inicio")

      hora_cursor = hora_min_filtro
      hora_limite = hora_max_filtro

      def renderizar_bloque_disponible(h_inicio_bloque, h_fin_bloque):
        if salon_upper:
          label_btn = (
              f"🟢 DISPONIBLE\n⏰ {h_inicio_bloque:02d}:00 -"
              f" {h_fin_bloque:02d}:00 | {salon_upper}"
          )
          if es_admin:
            with st.popover(label_btn, use_container_width=True):
              st.markdown(
                  f"**➕ Asignar Clase / Materia en {salon_upper}**\n"
                  f"*Día: {dia_nom} ({fecha_dia_actual})*"
              )
              f_asig = st.text_input(
                  "Asignatura:",
                  key=(
                      f"pop_a_{salon_upper}_{fecha_dia_actual}_{h_inicio_bloque}"
                  ),
              )
              f_doc = st.text_input(
                  "Docente:",
                  key=(
                      f"pop_d_{salon_upper}_{fecha_dia_actual}_{h_inicio_bloque}"
                  ),
              )
              col_p1, col_p2 = st.columns(2)
              f_h1 = col_p1.number_input(
                  "Hora Inicio:",
                  min_value=7,
                  max_value=18,
                  value=h_inicio_bloque,
                  key=(
                      f"pop_h1_{salon_upper}_{fecha_dia_actual}_{h_inicio_bloque}"
                  ),
              )
              f_h2 = col_p2.number_input(
                  "Hora Fin:",
                  min_value=8,
                  max_value=19,
                  value=min(h_inicio_bloque + 2, 19),
                  key=(
                      f"pop_h2_{salon_upper}_{fecha_dia_actual}_{h_inicio_bloque}"
                  ),
              )

              if st.button(
                  "💾 Asignar Espacio",
                  key=(
                      f"btn_save_{salon_upper}_{fecha_dia_actual}_{h_inicio_bloque}"
                  ),
                  type="primary",
              ):
                if f_asig.strip() and f_doc.strip():
                  db.agregar_evento_especial(
                      salon_upper,
                      fecha_dia_actual.strftime("%Y-%m-%d"),
                      f_h1,
                      f_h2,
                      f_asig,
                      f_doc,
                      "Asignación rápida de espacio",
                  )
                  st.success("¡Espacio asignado!")
                  st.rerun()
                else:
                  st.error("Ingresa asignatura y docente.")
          else:
            card_free = (
                "<div class='card-disponible' tabindex='0'><div"
                " style='font-weight:700; font-size:0.85rem;'>🟢"
                " DISPONIBLE</div><div class='class-time'"
                f" style='margin-top:3px;'>⏰ {h_inicio_bloque:02d}:00 -"
                f" {h_fin_bloque:02d}:00 | {salon_upper}</div></div>"
            )
            st.markdown(card_free, unsafe_allow_html=True)
        else:
          aulas_ocupadas_franja = set(
              clases_dia[
                  (clases_dia["hora_inicio"] < h_fin_bloque)
                  & (clases_dia["hora_fin"] > h_inicio_bloque)
              ]["espacio"]
              .apply(lambda x: str(x).upper())
              .unique()
          )
          aulas_libres_franja = [
              a for a in aulas_totales if a not in aulas_ocupadas_franja
          ]

          label_btn = (
              f"🟢 DISPONIBLE\n⏰ {h_inicio_bloque:02d}:00 -"
              f" {h_fin_bloque:02d}:00 | VARIAS AULAS"
          )

          with st.popover(label_btn, use_container_width=True):
            st.markdown(
                f"##### 🏛️ **Aulas Disponibles ({h_inicio_bloque:02d}:00 -"
                f" {h_fin_bloque:02d}:00)**"
            )
            if aulas_libres_franja:
              st.caption(
                  "Las siguientes salas no tienen clases programadas en esta"
                  " franja:"
              )
              for a_libre in aulas_libres_franja:
                st.markdown(f"• 🟢 **{a_libre}**")
            else:
              st.info(
                  "No hay salas completamente libres en esta franja horaria."
              )

      if clases_dia.empty:
        if (
            not ocultar_disponibles or solo_disponibles
        ) and hora_limite > hora_cursor:
          renderizar_bloque_disponible(hora_cursor, hora_limite)
      else:
        for _, c in clases_dia.iterrows():
          h_ini = int(c["hora_inicio"])
          h_fin = int(c["hora_fin"])

          h_ini_vis = max(h_ini, hora_min_filtro)
          h_fin_vis = min(h_fin, hora_max_filtro)
          salon_row = str(c["espacio"]).upper()

          if h_ini_vis > hora_cursor:
            if not ocultar_disponibles or solo_disponibles:
              renderizar_bloque_disponible(hora_cursor, h_ini_vis)

          if not solo_disponibles and h_fin_vis > h_ini_vis:
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

            style_card = (
                "" if es_evento else generar_estilo_color_materia(asig_upper)
            )
            class_attr = (
                "class-card class-card-evento" if es_evento else "class-card"
            )

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
            and (not ocultar_disponibles or solo_disponibles)
        ):
          renderizar_bloque_disponible(hora_cursor, hora_limite)


# -----------------------------------------------------------------------------
# 8. TAB 1: CONSULTA DE HORARIOS PÚBLICA
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
    salones_unicos = sorted([
        str(s).upper()
        for s in df_horarios["espacio"].unique()
        if pd.notna(s) and str(s).strip()
    ])

    if "input_asig" not in st.session_state:
      st.session_state["input_asig"] = ""
    if "input_doc" not in st.session_state:
      st.session_state["input_doc"] = ""
    if "input_salon" not in st.session_state:
      st.session_state["input_salon"] = "TODOS"
    if "input_horas" not in st.session_state:
      st.session_state["input_horas"] = (7, 19)

    col_f1, col_f2, col_f3, col_f4 = st.columns([3, 3, 3, 2])

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

    # Definición de la variable de estado del filtro
    filtro_hora_activo = rango_horas != (7, 19)

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

    # -------------------------------------------------------------------------
    # RENDERIZADO DE LA VISTA SEGÚN EL FILTRO DE SALÓN
    # -------------------------------------------------------------------------
    if (
        salon_sel == "TODOS"
        and not hay_busqueda_activa
        and not solo_disponibles
        and not filtro_hora_activo
    ):
      MAPA_DIAS_ESP = {
          0: "LUNES",
          1: "MARTES",
          2: "MIÉRCOLES",
          3: "JUEVES",
          4: "VIERNES",
          5: "SÁBADO",
          6: "DOMINGO",
      }
      dia_nombre_hoy = MAPA_DIAS_ESP.get(fecha_hoy.weekday(), "LUNES")

      st.markdown(
          f"##### 📍 **Vista General del Día:** {dia_nombre_hoy}"
          f" ({fecha_hoy.strftime('%d/%m/%Y')})"
      )

      # Columnas verticales para cada salón
      cols_salones = st.columns(len(salones_unicos))

      for idx_s, salon in enumerate(salones_unicos):
        with cols_salones[idx_s]:
          # Cabecera con altura estandarizada y color adaptativo
          st.markdown(
              f"<div class='day-header-box' style='height: 75px; display:"
              " flex; align-items: center; justify-content: center;"
              " padding: 6px; margin-bottom: 12px; border-radius: 8px;'><div"
              " class='day-title' style='text-align: center; font-size:"
              f" 0.80rem; font-weight: 800;' title='{salon}'>🏛️ {salon}</div></div>",
              unsafe_allow_html=True,
          )

          df_aula = df_filtered[
              df_filtered["espacio"].apply(normalizar_texto)
              == normalizar_texto(salon)
          ]

          # Renderizar solo el día actual omitiendo la fecha duplicada
          renderizar_matriz_semanal_aula(
              df_aula,
              [dia_nombre_hoy],
              lunes_semana,
              fecha_hoy,
              nombre_aula=salon,
              ocultar_disponibles=hay_busqueda_activa,
              solo_disponibles=solo_disponibles,
              rango_horas=rango_horas,
              mostrar_encabezado_dia=False,
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
          mostrar_encabezado_dia=True,
      )

# -----------------------------------------------------------------------------
# 9. TAB 2: PRÓXIMOS EVENTOS (PÚBLICO)
# -----------------------------------------------------------------------------
with tab_eventos_pub:
  st.subheader("📢 Agenda de Eventos y Reservas Especiales")

  df_todos = db.obtener_todos_los_horarios()

  if df_todos.empty:
    st.info("No hay eventos ni programaciones registradas en el sistema.")
  else:
    df_ev = df_todos[
        df_todos["tipo_evento"].apply(lambda x: str(x).lower()) == "evento"
    ].copy()

    if df_ev.empty:
      st.info("🟢 No hay eventos programados actualmente.")
    else:
      df_ev["fecha_dt"] = pd.to_datetime(df_ev["fecha"]).dt.date
      fecha_hoy_ev = datetime.date.today()

      col_e1, col_e2 = st.columns([2, 2])
      with col_e1:
        filtro_rango_ev = st.radio(
            "Ver eventos:",
            ["A partir de Hoy", "Todos los del Semestre"],
            horizontal=True,
        )
      with col_e2:
        salones_ev = ["TODOS"] + sorted(
            [str(s).upper() for s in df_ev["espacio"].unique()]
        )
        salon_ev_sel = st.selectbox("Filtrar por Salón:", salones_ev)

      if filtro_rango_ev == "A partir de Hoy":
        df_ev = df_ev[df_ev["fecha_dt"] >= fecha_hoy_ev]

      if salon_ev_sel != "TODOS":
        df_ev = df_ev[
            df_ev["espacio"].apply(normalizar_texto)
            == normalizar_texto(salon_ev_sel)
        ]

      df_ev = df_ev.sort_values(by=["fecha_dt", "hora_inicio"])

      if df_ev.empty:
        st.warning(
            "No hay eventos futuros registrados para el filtro seleccionado."
        )
      else:
        st.markdown(f"##### 📌 **Total de Eventos Encontrados:** {len(df_ev)}")

        cols_grid = st.columns(2)
        for idx_ev, (_, row_ev) in enumerate(df_ev.iterrows()):
          c_target = cols_grid[idx_ev % 2]
          with c_target:
            f_dt = row_ev["fecha_dt"]
            dia_nombre = row_ev["dia"].upper()
            fecha_card_fmt = f"{dia_nombre} {f_dt.strftime('%d/%m/%Y')}"
            h_i, h_f = int(row_ev["hora_inicio"]), int(row_ev["hora_fin"])
            titulo_ev = str(row_ev["asignatura"]).upper()
            resp_ev = str(row_ev["docente"]).upper()
            salon_ev = str(row_ev["espacio"]).upper()
            obs_ev = row_ev.get("observacion", "")

            obs_html = (
                f"<div style='font-size:0.78rem; color:#fcd34d;"
                f" margin-top:4px;'><b>Nota:</b> {obs_ev.upper()}</div>"
                if pd.notna(obs_ev) and str(obs_ev).strip()
                else ""
            )

            card_agenda_html = f"""
                        <div class="event-agenda-card">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                                <span style="background:#f59e0b; color:#000; font-size:0.72rem; font-weight:800; padding:2px 8px; border-radius:4px;">📆 {fecha_card_fmt}</span>
                                <span style="font-size:0.80rem; font-weight:700; color:#fbbf24;">🏛️ {salon_ev}</span>
                            </div>
                            <div style="font-size:1.05rem; font-weight:800; color:#f8fafc; margin-bottom:4px;">{titulo_ev}</div>
                            <div style="font-size:0.82rem; color:#d1d5db;">⏰ <b>Horario:</b> {h_i:02d}:00 - {h_f:02d}:00 hrs</div>
                            <div style="font-size:0.82rem; color:#d1d5db;">👨‍🏫 <b>Responsable:</b> {resp_ev}</div>
                            {obs_html}
                        </div>
                        """
            st.markdown(card_agenda_html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 10. TABS ADMINISTRATIVOS (CARGUE Y EVENTOS)
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
          "Sube el archivo Excel formateado (`.xlsx`):", type=["xlsx", "xls"]
      )

      if uploaded_file is not None and validar_archivo_excel(uploaded_file):
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

          aulas_detectadas_excel = sorted(
              df_edit["ESPACIO / SALÓN"].unique().tolist()
          )

          col_m1, col_m2, col_m3 = st.columns(3)
          col_m1.metric("📚 Clases a Programar", len(df_edit))
          col_m2.metric("🏛️ Aulas Asignadas", len(aulas_detectadas_excel))
          col_m3.metric("⏰ Horario Oficial Funcionarios", "07:00 a 19:00")

          df_editado = st.data_editor(
              df_edit,
              num_rows="dynamic",
              use_container_width=True,
              column_config={
                  "ESPACIO / SALÓN": st.column_config.SelectboxColumn(
                      "Salón / Aula",
                      options=aulas_detectadas_excel,
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

        except ValueError:
          st.error(
              "🚨 **Error de Formato:** El archivo subido no cumple con"
              " ninguno de los dos formatos soportados."
          )
          st.markdown(
              """
                    <div class="excel-template-box">
                    <h4>📋 Formatos de Excel Compatibles:</h4>
                    
                    <b>1. Formato Cuadrícula de Coordinación (Conversión Automática)</b><br>
                    • Libro con la matriz de horarios distribuida por franjas horarias (7 a 19) y salones.<br>
                    • La fila inicial de cada salón debe listar los días de la semana y la primera columna las horas.<br><br>
                    
                    <b>2. Formato Estructurado de Base de Datos</b><br>
                    • Nombre obligatorio de pestaña: <b><code>BD_Calendario_Semestre</code></b><br>
                    • Columnas requeridas:<br>
                    | ESPACIO / SALÓN | DÍA | HORA INICIO (24H) | HORA FIN (24H) | ASIGNATURA | DOCENTE |<br>
                    | E105 (SALA CAD) | LUNES | 10 | 12 | PROGRAMACION | NICOLAS |
                    </div>
                """,
              unsafe_allow_html=True,
          )

if st.session_state.authenticated and tab_eventos_adm:
  with tab_eventos_adm:
    st.subheader("➕ Registrar Evento o Reserva Especial")

    df_horarios = db.obtener_todos_los_horarios()
    salones_db_dinamicos = (
        sorted([
            str(s).upper()
            for s in df_horarios["espacio"].unique()
            if pd.notna(s)
        ])
        if not df_horarios.empty
        else ["AULA GENERAL"]
    )

    ev_salon = st.selectbox("1️⃣ Salón / Aula:", options=salones_db_dinamicos)
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
        "5️⃣ Nombre del Evento / Clase Faltante:",
        placeholder="Ej. CONTINGENCIA MATEMATICAS",
    )
    ev_doc = st.text_input(
        "6️⃣ Responsable / Docente:", placeholder="Ej. ING. GARCÍA"
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
    if st.button("💾 Guardar y Asignar Espacio", type="primary"):
      if ev_h_fin <= ev_h_ini:
        st.error("La Hora Fin debe ser mayor a la Hora Inicio.")
      elif not ev_asig.strip() or not ev_doc.strip():
        st.error(
            "Debes ingresar el Nombre del Evento / Clase y el Responsable."
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
        mostrar_popup_evento_exito(
            ev_asig, ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin, ev_doc
        )