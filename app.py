import datetime
import hashlib
import unicodedata
import os
import pandas as pd
import streamlit as st
from controllers.horario_controller import HorarioController
from models.database import DatabaseModel

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Consulta Aulas DTE",
    page_icon="sources/lg_upn.png" if os.path.exists("sources/lg_upn.png") else "🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db = DatabaseModel()
controller = HorarioController(db)

# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES Y SEGURIDAD
# -----------------------------------------------------------------------------
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def generar_estilo_materia_inline(nombre_asignatura):
    """Genera fondo oscuro, borde vivo y texto claro según el hash del nombre."""
    nombre_norm = normalizar_texto(nombre_asignatura)
    hash_hex = hashlib.md5(nombre_norm.encode("utf-8")).hexdigest()
    hue = int(hash_hex[:4], 16) % 360
    return f"background: hsl({hue}, 65%, 15%); border-left: 4px solid hsl({hue}, 85%, 55%); color: hsl({hue}, 90%, 90%);"

def resetear_filtros_callback():
    st.session_state["input_asig"] = ""
    st.session_state["input_doc"] = ""
    st.session_state["input_salon"] = "TODOS"
    st.session_state["input_horas"] = (7, 19)

def ir_a_pestaña(nombre_tab):
    st.session_state["active_tab"] = nombre_tab

def validar_archivo_excel(uploaded_file, max_mb=10):
    if uploaded_file is not None:
        if uploaded_file.size > max_mb * 1024 * 1024:
            st.error(f"⚠️ El archivo supera el límite permitido de {max_mb} MB.")
            return False
        if not uploaded_file.name.endswith((".xlsx", ".xls")):
            st.error("⚠️ Formato no permitido. Solo se aceptan archivos Excel (.xlsx, .xls).")
            return False
        return True
    return False

# -----------------------------------------------------------------------------
# ESTILOS CSS CON EJE VERTICAL DE HORAS Y TARJETAS APILADAS
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        margin-top: 0px;
        margin-bottom: 4px;
        color: var(--text-color);
        text-align: center;
    }

    /* Contenedor responsivo para la matriz */
    .vertical-schedule-container {
        width: 100%;
        overflow-x: auto;
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.25);
        background: var(--background-color);
        margin-bottom: 20px;
    }

    .grid-vertical-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 6px;
        font-size: 0.8rem;
        text-align: center;
    }

    /* Encabezados Superiores (Salones o Días) */
    .grid-vertical-table th.header-col {
        background: var(--secondary-background-color);
        color: #10b981;
        font-weight: 800;
        font-size: 0.85rem;
        padding: 10px 6px;
        border-radius: 6px;
        border: 1px solid rgba(16, 185, 129, 0.3);
        min-width: 130px;
        vertical-align: middle;
    }

    .grid-vertical-table th.header-col-hoy {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%) !important;
        border: 2px solid #10b981 !important;
        color: #6ee7b7 !important;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
    }

    /* Encabezados Izquierdos (Franjas Horarias) */
    .grid-vertical-table td.header-time {
        background: var(--secondary-background-color);
        color: var(--text-color);
        font-weight: 700;
        font-size: 0.78rem;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid rgba(128, 128, 128, 0.25);
        min-width: 100px;
        white-space: nowrap;
        vertical-align: middle;
    }

    /* Tarjetas Ocupadas */
    .card-cell-occupied {
        border-radius: 6px;
        padding: 8px 6px;
        font-size: 0.76rem;
        line-height: 1.2;
        font-weight: 700;
        vertical-align: middle;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        box-sizing: border-box;
    }

    .card-cell-occupied .doc-txt {
        font-size: 0.70rem;
        opacity: 0.85;
        font-weight: 400;
        display: block;
        margin-top: 3px;
    }

    .card-cell-evento {
        background: linear-gradient(135deg, #451a03 0%, #1c0901 100%) !important;
        border-left: 4px solid #f59e0b !important;
        color: #fef3c7 !important;
    }

    /* Tarjetas Disponibles */
    .card-cell-free {
        background: rgba(16, 185, 129, 0.06);
        color: #10b981;
        font-size: 0.75rem;
        font-weight: 600;
        vertical-align: middle;
        border: 1px dashed rgba(16, 185, 129, 0.4);
        border-radius: 6px;
    }

    .event-agenda-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(245, 158, 11, 0.4);
        border-left: 5px solid #f59e0b;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 14px;
        color: var(--text-color);
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# AUTENTICACIÓN ADMIN SEGURA
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

st.sidebar.title("🔐 Acceso Administrativo")

def obtener_secreto(seccion, clave, default=None):
    try:
        if hasattr(st, "secrets") and seccion in st.secrets:
            return st.secrets[seccion].get(clave, default)
    except Exception:
        pass
    return default

ADMIN_USER = obtener_secreto("admin_credentials", "username", "admin")
ADMIN_PASSWORD_HASH = obtener_secreto(
    "admin_credentials",
    "password_hash",
    "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
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

# Modales
@st.dialog("🎉 Carga Semestral Exitosa")
def mostrar_popup_exito(total_registros, f_ini, f_fin):
    st.success("### ¡Las asignaturas han sido guardadas!")
    st.write(
        f"• **Periodo Configurado:** Del **{f_ini}** al **{f_fin}**\n"
        f"• **Sesiones Proyectadas:** **{total_registros} clases** registradas."
    )
    if st.button("Ir a Consulta de Horarios ➡️", type="primary", on_click=ir_a_pestaña, args=("📅 Consulta de Horarios (Público / QR)",)):
        st.rerun()

@st.dialog("🎉 Evento Asignado con Éxito")
def mostrar_popup_evento_exito(nombre_evento, salon, fecha, hora_ini, hora_fin, responsable):
    st.success("### ¡El evento ha sido registrado correctamente!")
    st.markdown(
        f"• **Evento:** **{nombre_evento}**\n"
        f"• **Lugar:** **{salon}**\n"
        f"• **Fecha:** **{fecha}**\n"
        f"• **Horario:** **{hora_ini}:00 - {hora_fin}:00 hrs**\n"
        f"• **Responsable:** **{responsable}**"
    )
    if st.button("Ir a Próximos Eventos ➡️", type="primary", on_click=ir_a_pestaña, args=("📢 Próximos Eventos",)):
        st.rerun()

@st.dialog("⚠️ Confirmar Vaciado de Base de Datos")
def mostrar_popup_vaciar_db():
    st.warning("**¿Estás seguro de que deseas eliminar TODOS los horarios guardados?**")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if st.button("❌ Cancelar", use_container_width=True):
            st.rerun()
    with col_v2:
        if st.button("🗑️ Sí, Vaciar Base de Datos", type="primary", use_container_width=True):
            db.vaciar_base_de_datos()
            if "df_unicas" in st.session_state:
                del st.session_state.df_unicas
            st.success("Base de datos vaciada correctamente.")
            st.rerun()

es_vigente, msj_vigencia, f_ini_db, f_fin_db = db.obtener_vigencia_semestre()

# ENCABEZADO
st.markdown('<h1 class="main-title">Consulta Aulas DTE</h1>', unsafe_allow_html=True)

if f_ini_db:
    semestre_num = 1 if f_ini_db.month <= 6 else 2
    periodo_str = f"{f_ini_db.year}-{semestre_num}"
else:
    periodo_str = "SIN CARGUE"

if es_vigente:
    st.caption(f"<div style='text-align: center; width: 100%;'>🟢 <b>Semestre Activo:</b> {periodo_str} ({f_ini_db} al {f_fin_db})</div>", unsafe_allow_html=True)
else:
    st.caption(f"<div style='text-align: center; width: 100%;'>⚠️ <b>Estado:</b> {msj_vigencia}</div>", unsafe_allow_html=True)

st.markdown("---")

if st.session_state.authenticated:
    lista_tabs = ["📅 Consulta de Horarios (Público / QR)", "📢 Próximos Eventos", "📋 Confirmación de Carga Semestral (Admin)", "➕ Eventos y Cambios (Admin)"]
else:
    lista_tabs = ["📅 Consulta de Horarios (Público / QR)", "📢 Próximos Eventos"]

if "active_tab" not in st.session_state or st.session_state["active_tab"] not in lista_tabs:
    st.session_state["active_tab"] = lista_tabs[0]

tabs = st.tabs(lista_tabs)

if st.session_state.authenticated:
    tab_horarios, tab_eventos_pub, tab_cargue, tab_eventos_adm = tabs[0], tabs[1], tabs[2], tabs[3]
else:
    tab_horarios, tab_eventos_pub = tabs[0], tabs[1]
    tab_cargue, tab_eventos_adm = None, None

# -----------------------------------------------------------------------------
# RENDERIZADOR MATRICIAL CON HORAS A LA IZQUIERDA Y EXPANSION VERTICAL
# -----------------------------------------------------------------------------
def renderizar_matriz_vertical_con_horas_izq(df_datos, columnas, es_vista_dias=False, dia_hoy_nombre=None, rango_horas=(7, 19)):
    h_min, h_max = rango_horas
    franjas = list(range(h_min, h_max))

    # Diccionario para rastrear cuántos bloques verticales le quedan a cada columna
    skip_filas = {col: 0 for col in columnas}

    html = "<div class='vertical-schedule-container'><table class='grid-vertical-table'><thead><tr>"
    html += "<th class='header-time' style='text-align:center;'>HORA / FRANJA</th>"
    
    # Encabezados de columnas (Aulas o Días)
    for col in columnas:
        es_hoy = es_vista_dias and dia_hoy_nombre and normalizar_texto(col) == normalizar_texto(dia_hoy_nombre)
        cls_header = "header-col header-col-hoy" if es_hoy else "header-col"
        prefix = "📍 HOY<br>" if es_hoy else ""
        icon = "" if es_vista_dias else "🏛️ "
        html += f"<th class='{cls_header}'>{prefix}{icon}{col}</th>"
    html += "</tr></thead><tbody>"

    # Recorrer fila por fila (por hora)
    for h in franjas:
        html += f"<tr><td class='header-time'>⏰ {h}:00 - {h+1}:00</td>"

        for col in columnas:
            # Si esta celda está siendo abarcada por un rowspan anterior, se omite
            if skip_filas[col] > 0:
                skip_filas[col] -= 1
                continue

            if es_vista_dias:
                df_celda = df_datos[
                    (df_datos["dia"].apply(normalizar_texto) == normalizar_texto(col)) &
                    (df_datos["hora_inicio"] <= h) &
                    (df_datos["hora_fin"] > h)
                ].sort_values(by="hora_inicio")
            else:
                df_celda = df_datos[
                    (df_datos["espacio"].apply(normalizar_texto) == normalizar_texto(col)) &
                    (df_datos["hora_inicio"] <= h) &
                    (df_datos["hora_fin"] > h)
                ].sort_values(by="hora_inicio")

            if not df_celda.empty:
                c = df_celda.iloc[0]
                h_ini = max(int(c["hora_inicio"]), h_min)
                h_fin = min(int(c["hora_fin"]), h_max)
                rowspan = h_fin - h

                if rowspan < 1:
                    rowspan = 1

                # Guardar las filas siguientes que deben saltarse
                skip_filas[col] = rowspan - 1

                asig = str(c["asignatura"]).upper()
                doc = str(c["docente"]).upper()
                tipo_ev = str(c.get("tipo_evento", "")).lower()

                if tipo_ev == "evento":
                    cell_class = "card-cell-occupied card-cell-evento"
                    style = ""
                else:
                    cell_class = "card-cell-occupied"
                    style = generar_estilo_materia_inline(asig)

                html += f"<td rowspan='{rowspan}' class='{cell_class}' style='{style}' title='{asig} ({doc})'>"
                html += f"<div>{asig}</div><span class='doc-txt'>👨‍🏫 {doc}</span>"
                html += "</td>"
            else:
                html += "<td class='card-cell-free'>🟢 Libre</td>"

        html += "</tr>"

    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 1: CONSULTA DE HORARIOS PÚBLICA
# -----------------------------------------------------------------------------
with tab_horarios:
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.subheader("📅 Consulta de Horarios")
    with col_h2:
        if st.session_state.authenticated:
            if st.button("🗑️ Vaciar Base de Datos", type="secondary"):
                mostrar_popup_vaciar_db()

    df_horarios = db.obtener_todos_los_horarios()

    if df_horarios.empty:
        st.info("La base de datos se encuentra vacía. Un administrador debe realizar el cargue del semestre.")
    else:
        salones_unicos = sorted([str(s).upper() for s in df_horarios["espacio"].unique() if pd.notna(s) and str(s).strip()])

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
            salon_sel = st.selectbox("Filtrar por Salón / Aula:", ["TODOS"] + salones_unicos, key="input_salon")
        with col_f2:
            busqueda_asig = st.text_input("🔍 Buscar por Asignatura:", placeholder="Ej. programacion", key="input_asig")
        with col_f3:
            busqueda_doc = st.text_input("👨‍🏫 Buscar por Docente:", placeholder="Ej. nicolas", key="input_doc")
        with col_f4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button("🧹 Limpiar Filtros", on_click=resetear_filtros_callback, use_container_width=True)

        rango_horas = st.slider(
            "⏰ **Filtrar Franja Horaria (Horas exactas):**",
            min_value=7,
            max_value=19,
            value=st.session_state["input_horas"],
            format="%d:00 hrs",
            key="input_horas",
        )

        fecha_hoy = datetime.date.today()
        lunes_semana = fecha_hoy - datetime.timedelta(days=fecha_hoy.weekday())

        DIAS_NOMBRES = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO"]
        MAPA_DIAS_ESP = {0: "LUNES", 1: "MARTES", 2: "MIÉRCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SÁBADO"}
        dia_nombre_hoy = MAPA_DIAS_ESP.get(fecha_hoy.weekday(), "LUNES")

        q_asig = normalizar_texto(busqueda_asig)
        q_doc = normalizar_texto(busqueda_doc)

        # CASO 1: VISTA GENERAL DE TODOS LOS SALONES PARA UN DÍA ESPECÍFICO
        if salon_sel == "TODOS":
            dia_def_idx = min(fecha_hoy.weekday(), 5)
            dia_seleccionado = st.radio("📌 **Seleccionar Día de Consulta:**", DIAS_NOMBRES, index=dia_def_idx, horizontal=True)

            idx_dia_sel = DIAS_NOMBRES.index(dia_seleccionado)
            fecha_consulta = lunes_semana + datetime.timedelta(days=idx_dia_sel)

            df_filtered = df_horarios.copy()
            df_filtered["fecha_dt"] = pd.to_datetime(df_filtered["fecha"]).dt.date
            df_filtered = df_filtered[df_filtered["fecha_dt"] == fecha_consulta]

            if q_asig.strip():
                df_filtered = df_filtered[df_filtered["asignatura"].apply(normalizar_texto).str.contains(q_asig, regex=False)]
            if q_doc.strip():
                df_filtered = df_filtered[df_filtered["docente"].apply(normalizar_texto).str.contains(q_doc, regex=False)]

            st.markdown(f"##### 📍 **Vista General de Aulas del Día:** {dia_seleccionado} ({fecha_consulta.strftime('%d/%m/%Y')})")

            renderizar_matriz_vertical_con_horas_izq(
                df_filtered,
                salones_unicos,
                es_vista_dias=False,
                rango_horas=rango_horas
            )

        # CASO 2: VISTA SEMANAL INDIVIDUAL PARA UN SALÓN SELECCIONADO
        else:
            sabado_semana = lunes_semana + datetime.timedelta(days=5)
            df_filtered = df_horarios.copy()
            df_filtered["fecha_dt"] = pd.to_datetime(df_filtered["fecha"]).dt.date
            df_filtered = df_filtered[
                (df_filtered["fecha_dt"] >= lunes_semana) &
                (df_filtered["fecha_dt"] <= sabado_semana) &
                (df_filtered["espacio"].apply(normalizar_texto) == normalizar_texto(salon_sel))
            ]

            if q_asig.strip():
                df_filtered = df_filtered[df_filtered["asignatura"].apply(normalizar_texto).str.contains(q_asig, regex=False)]
            if q_doc.strip():
                df_filtered = df_filtered[df_filtered["docente"].apply(normalizar_texto).str.contains(q_doc, regex=False)]

            st.markdown(f"##### 🏛️ **Horario Semanal del Salón:** {salon_sel}")

            renderizar_matriz_vertical_con_horas_izq(
                df_filtered,
                DIAS_NOMBRES,
                es_vista_dias=True,
                dia_hoy_nombre=dia_nombre_hoy,
                rango_horas=rango_horas
            )

# -----------------------------------------------------------------------------
# TAB 2: PRÓXIMOS EVENTOS
# -----------------------------------------------------------------------------
with tab_eventos_pub:
    st.subheader("📢 Agenda de Eventos y Reservas Especiales")
    df_todos = db.obtener_todos_los_horarios()

    if df_todos.empty:
        st.info("No hay eventos ni programaciones registradas en el sistema.")
    else:
        df_ev = df_todos[df_todos["tipo_evento"].apply(lambda x: str(x).lower()) == "evento"].copy()

        if df_ev.empty:
            st.info("🟢 No hay eventos programados actualmente.")
        else:
            df_ev["fecha_dt"] = pd.to_datetime(df_ev["fecha"]).dt.date
            fecha_hoy_ev = datetime.date.today()

            col_e1, col_e2 = st.columns([2, 2])
            with col_e1:
                filtro_rango_ev = st.radio("Ver eventos:", ["A partir de Hoy", "Todos los del Semestre"], horizontal=True)
            with col_e2:
                salones_ev = ["TODOS"] + sorted([str(s).upper() for s in df_ev["espacio"].unique()])
                salon_ev_sel = st.selectbox("Filtrar por Salón:", salones_ev)

            if filtro_rango_ev == "A partir de Hoy":
                df_ev = df_ev[df_ev["fecha_dt"] >= fecha_hoy_ev]

            if salon_ev_sel != "TODOS":
                df_ev = df_ev[df_ev["espacio"].apply(normalizar_texto) == normalizar_texto(salon_ev_sel)]

            df_ev = df_ev.sort_values(by=["fecha_dt", "hora_inicio"])

            if df_ev.empty:
                st.warning("No hay eventos futuros registrados para el filtro seleccionado.")
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

                        obs_html = f"<div style='font-size:0.78rem; color:#f59e0b; margin-top:4px;'><b>Nota:</b> {obs_ev.upper()}</div>" if pd.notna(obs_ev) and str(obs_ev).strip() else ""

                        card_agenda_html = f"""
                        <div class="event-agenda-card">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                                <span style="background:#f59e0b; color:#000; font-size:0.72rem; font-weight:800; padding:2px 8px; border-radius:4px;">📆 {fecha_card_fmt}</span>
                                <span style="font-size:0.80rem; font-weight:700; color:#10b981;">🏛️ {salon_ev}</span>
                            </div>
                            <div style="font-size:1.05rem; font-weight:800; margin-bottom:4px;">{titulo_ev}</div>
                            <div style="font-size:0.82rem; opacity:0.85;">⏰ <b>Horario:</b> {h_i:02d}:00 - {h_f:02d}:00 hrs</div>
                            <div style="font-size:0.82rem; opacity:0.85;">👨‍🏫 <b>Responsable:</b> {resp_ev}</div>
                            {obs_html}
                        </div>
                        """
                        st.markdown(card_agenda_html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 3 & 4: ADMINISTRACIÓN
# -----------------------------------------------------------------------------
if st.session_state.authenticated and tab_cargue:
    with tab_cargue:
        st.markdown("### 1️⃣ Paso 1: Configurar Fechas del Semestre")
        c_f1, c_f2 = st.columns(2)
        f_inicio = c_f1.date_input("Fecha de Inicio del Semestre:", value=datetime.date(2026, 2, 2))
        f_fin = c_f2.date_input("Fecha de Finalización del Semestre:", value=datetime.date(2026, 6, 30))

        if f_fin <= f_inicio:
            st.error("⚠️ La fecha de finalización debe ser posterior a la de inicio.")
        else:
            st.markdown("---")
            st.markdown("### 2️⃣ Paso 2: Cargar y Validar Archivo de Horarios")
            uploaded_file = st.file_uploader("Sube el archivo Excel formateado (`.xlsx`):", type=["xlsx", "xls"])

            if uploaded_file is not None and validar_archivo_excel(uploaded_file):
                try:
                    st.session_state.df_unicas = controller.validar_y_procesar_excel(uploaded_file)
                    df_edit = st.session_state.df_unicas[
                        ["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]
                    ].copy()
                    df_edit["ESPACIO / SALÓN"] = df_edit["ESPACIO / SALÓN"].str.upper()
                    df_edit["DÍA"] = df_edit["DÍA"].str.upper()
                    df_edit["ASIGNATURA"] = df_edit["ASIGNATURA"].str.upper()
                    df_edit["DOCENTE"] = df_edit["DOCENTE"].str.upper()

                    st.markdown("---")
                    st.markdown("### 3️⃣ Paso 3: Confirmar Oferta Académica")

                    aulas_detectadas_excel = sorted(df_edit["ESPACIO / SALÓN"].unique().tolist())

                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("📚 Clases a Programar", len(df_edit))
                    col_m2.metric("🏛️ Aulas Asignadas", len(aulas_detectadas_excel))
                    col_m3.metric("⏰ Horario Oficial Funcionarios", "07:00 a 19:00")

                    df_editado = st.data_editor(
                        df_edit,
                        num_rows="dynamic",
                        use_container_width=True,
                        column_config={
                            "ESPACIO / SALÓN": st.column_config.SelectboxColumn("Salón / Aula", options=aulas_detectadas_excel, required=True),
                            "DÍA": st.column_config.SelectboxColumn("Día de la Semana", options=["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO"], required=True),
                            "HORA INICIO (24H)": st.column_config.NumberColumn("Hora Inicio (7 a 18)", min_value=7, max_value=18, step=1),
                            "HORA FIN (24H)": st.column_config.NumberColumn("Hora Fin (8 a 19)", min_value=8, max_value=19, step=1),
                            "ASIGNATURA": st.column_config.TextColumn("Asignatura / Materia", required=True),
                            "DOCENTE": st.column_config.TextColumn("Docente / Profesor"),
                        },
                    )

                    errores_rango = controller.validar_rango_laboral(df_editado)

                    if errores_rango:
                        st.error("🚨 **Horario No Permitido:** Hay clases configuradas fuera del rango oficial (07:00 a 19:00).")
                    else:
                        st.markdown("---")
                        if st.button("🚀 Confirmar y Guardar Semestre", type="primary"):
                            controller.proyectar_y_guardar_semestre(df_editado, f_inicio, f_fin)
                            total_registros = len(db.obtener_todos_los_horarios())
                            mostrar_popup_exito(total_registros, f_inicio, f_fin)

                except ValueError as val_err:
                    st.error("🚨 **Error de Formato:** El archivo subido no cumple con ninguno de los dos formatos soportados.")

if st.session_state.authenticated and tab_eventos_adm:
    with tab_eventos_adm:
        st.subheader("➕ Registrar Evento o Reserva Especial")

        df_horarios = db.obtener_todos_los_horarios()
        salones_db_dinamicos = sorted([str(s).upper() for s in df_horarios["espacio"].unique() if pd.notna(s)]) if not df_horarios.empty else ["AULA GENERAL"]

        ev_salon = st.selectbox("1️⃣ Salón / Aula:", options=salones_db_dinamicos)
        ev_fecha = st.date_input("2️⃣ Fecha del Evento:", value=datetime.date.today())

        col_h1, col_h2 = st.columns(2)
        ev_h_ini = col_h1.number_input("3️⃣ Hora Inicio (24H):", min_value=7, max_value=18, value=10)
        ev_h_fin = col_h2.number_input("4️⃣ Hora Fin (24H):", min_value=8, max_value=19, value=12)

        ev_asig = st.text_input("5️⃣ Nombre del Evento / Clase Faltante:", placeholder="Ej. CONTINGENCIA MATEMATICAS")
        ev_doc = st.text_input("6️⃣ Responsable / Docente:", placeholder="Ej. ING. GARCÍA")

        fecha_ev_str = ev_fecha.strftime("%Y-%m-%d")
        conflictos = db.verificar_conflicto_horario(ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin)

        ev_obs = ""
        requiere_obs = False

        if conflictos:
            requiere_obs = True
            st.error(f"🚨 **Espacio Ya Ocupado:** El salón **{ev_salon}** ya tiene programación el **{fecha_ev_str}** entre las **{ev_h_ini}:00 y {ev_h_fin}:00 hrs**:")
            for c in conflictos:
                c_asig, c_doc, c_tipo, c_ini, c_fin = c[1].upper(), c[2].upper(), c[5].upper(), c[3], c[4]
                st.warning(f"• **{c_asig}** ({c_tipo}) | Responsable: **{c_doc}** | Horario: {c_ini}:00 - {c_fin}:00")

            st.markdown("---")
            ev_obs = st.text_area("7️⃣ Observaciones (OBLIGATORIO por ocupar un espacio asignado):", placeholder="Especifica la razón por la cual se reasigna el espacio...")
        else:
            st.success(f"🟢 **Aula Libre:** El salón {ev_salon} está completamente disponible en la franja {ev_h_ini}:00 a {ev_h_fin}:00 hrs.")

        st.markdown("---")
        if st.button("💾 Guardar y Asignar Espacio", type="primary"):
            if ev_h_fin <= ev_h_ini:
                st.error("La Hora Fin debe ser mayor a la Hora Inicio.")
            elif not ev_asig.strip() or not ev_doc.strip():
                st.error("Debes ingresar el Nombre del Evento / Clase y el Responsable.")
            elif requiere_obs and not ev_obs.strip():
                st.error("⚠️ **Observación Requerida:** Debes ingresar la razón de la asignación sobre un espacio que ya estaba ocupado.")
            else:
                db.agregar_evento_especial(ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin, ev_asig, ev_doc, ev_obs)
                mostrar_popup_evento_exito(ev_asig, ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin, ev_doc)