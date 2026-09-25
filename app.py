import datetime
import hashlib
import unicodedata
import os
import urllib.parse
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
# FUNCIONES AUXILIARES Y FORMATO 12 HORAS (AM/PM)
# -----------------------------------------------------------------------------
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

def generar_estilo_materia_inline(nombre_asignatura):
    nombre_norm = normalizar_texto(nombre_asignatura)
    hash_hex = hashlib.md5(nombre_norm.encode("utf-8")).hexdigest()
    hue = int(hash_hex[:4], 16) % 360
    return f"background: hsl({hue}, 65%, 15%); border-left: 4px solid hsl({hue}, 85%, 55%); color: hsl({hue}, 90%, 90%);"

def formatear_12h(hora_24):
    """Convierte un entero (7 a 19) a string limpio en formato 12 horas (ej. 7 -> 07:00 AM, 14 -> 02:00 PM)."""
    h = int(hora_24)
    dt = datetime.time(hour=h)
    return dt.strftime("%I:00 %p").lstrip("0")

def parsear_12h_a_24h(str_12h):
    """Convierte un texto tipo '02:00 PM' a entero de 24H (ej. 14)."""
    if isinstance(str_12h, (int, float)):
        return int(str_12h)
    
    str_clean = str(str_12h).replace("%00", ":00").strip()
    if ":" in str_clean:
        dt = datetime.datetime.strptime(str_clean, "%I:%M %p")
    else:
        dt = datetime.datetime.strptime(str_clean, "%I %p")
        
    return dt.hour

OPCIONES_HORAS_12H = [formatear_12h(h) for h in range(7, 20)]

def resetear_filtros_callback():
    st.session_state["input_asig"] = ""
    st.session_state["input_doc"] = ""
    st.session_state["input_salon"] = "TODOS"
    st.session_state["input_horas"] = (7, 19)
    if "salon" in st.query_params:
        del st.query_params["salon"]

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

def generar_url_qr(texto_url, tamano=300):
    """Genera una URL directa de imagen QR usando la API nativa de QuickChart."""
    url_encode = urllib.parse.quote(texto_url, safe="")
    return f"https://quickchart.io/qr?text={url_encode}&size={tamano}&margin=2"

# -----------------------------------------------------------------------------
# ESTILOS CSS
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

    .grid-vertical-table td.header-time {
        background: var(--secondary-background-color);
        color: var(--text-color);
        font-weight: 700;
        font-size: 0.78rem;
        padding: 8px 10px;
        border-radius: 6px;
        border: 1px solid rgba(128, 128, 128, 0.25);
        min-width: 110px;
        white-space: nowrap;
        vertical-align: middle;
    }

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
        f"• **Horario:** **{formatear_12h(hora_ini)} - {formatear_12h(hora_fin)}**\n"
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
    lista_tabs = [
        "📅 Consulta de Horarios (Público / QR)",
        "📢 Próximos Eventos",
        "✏️ Edición Rápida de Materias (Admin)",
        "📋 Confirmación de Carga Semestral (Admin)",
        "➕ Eventos y Cambios (Admin)",
    ]
else:
    lista_tabs = ["📅 Consulta de Horarios (Público / QR)", "📢 Próximos Eventos"]

if "active_tab" not in st.session_state or st.session_state["active_tab"] not in lista_tabs:
    st.session_state["active_tab"] = lista_tabs[0]

tabs = st.tabs(lista_tabs)

if st.session_state.authenticated:
    tab_horarios, tab_eventos_pub, tab_edicion, tab_cargue, tab_eventos_adm = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4]
else:
    tab_horarios, tab_eventos_pub = tabs[0], tabs[1]
    tab_edicion, tab_cargue, tab_eventos_adm = None, None, None

# -----------------------------------------------------------------------------
# RENDERIZADOR MATRICIAL CON HORAS EN FORMATO 12 HORAS (AM/PM) A LA IZQUIERDA
# -----------------------------------------------------------------------------
def renderizar_matriz_vertical_con_horas_izq(
    df_datos, columnas, es_vista_dias=False, dia_hoy_nombre=None, rango_horas=(7, 19), solo_clases_ocupadas=False
):
    h_min, h_max = rango_horas
    
    if solo_clases_ocupadas and not df_datos.empty:
        franjas_activas = set()
        for _, r in df_datos.iterrows():
            ini = max(int(r["hora_inicio"]), h_min)
            fin = min(int(r["hora_fin"]), h_max)
            for hh in range(ini, fin):
                franjas_activas.add(hh)
        franjas = sorted(list(franjas_activas))
    else:
        franjas = list(range(h_min, h_max))

    if not franjas or not columnas:
        st.info("No se encontraron clases para la consulta especificada.")
        return

    skip_filas = {col: 0 for col in columnas}

    html = "<div class='vertical-schedule-container'><table class='grid-vertical-table'><thead><tr>"
    html += "<th class='header-time' style='text-align:center;'>HORA / FRANJA</th>"

    for col in columnas:
        es_hoy = es_vista_dias and dia_hoy_nombre and normalizar_texto(col) == normalizar_texto(dia_hoy_nombre)
        cls_header = "header-col header-col-hoy" if es_hoy else "header-col"
        prefix = "📍 HOY<br>" if es_hoy else ""
        icon = "" if es_vista_dias else "🏛️ "
        html += f"<th class='{cls_header}'>{prefix}{icon}{col}</th>"
    html += "</tr></thead><tbody>"

    for h in franjas:
        lbl_h_ini = formatear_12h(h)
        lbl_h_fin = formatear_12h(h + 1)
        html += f"<tr><td class='header-time'>⏰ {lbl_h_ini} - {lbl_h_fin}</td>"

        for col in columnas:
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
                
                if solo_clases_ocupadas:
                    rowspan = sum(1 for hh in franjas if h_ini <= hh < h_fin)
                else:
                    rowspan = h_fin - h

                if rowspan < 1:
                    rowspan = 1

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
                if solo_clases_ocupadas:
                    html += "<td style='background: transparent; border: none;'></td>"
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

        # DETECTAR SI LA URL TRAE UN PARÁMETRO DE SALÓN DESDE CÓDIGO QR
        params = st.query_params
        salon_param = params.get("salon", None)
        
        default_salon = "TODOS"
        if salon_param:
            norm_param = normalizar_texto(salon_param)
            for s in salones_unicos:
                if normalizar_texto(s) == norm_param:
                    default_salon = s
                    break

        if "input_asig" not in st.session_state:
            st.session_state["input_asig"] = ""
        if "input_doc" not in st.session_state:
            st.session_state["input_doc"] = ""
        if "input_salon" not in st.session_state or st.session_state["input_salon"] not in (["TODOS"] + salones_unicos):
            st.session_state["input_salon"] = default_salon
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
            "⏰ **Filtrar Franja Horaria:**",
            min_value=7,
            max_value=19,
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

        if salon_sel == "TODOS":
            dia_def_idx = min(fecha_hoy.weekday(), 5)
            dia_seleccionado = st.radio("📌 **Seleccionar Día de Consulta:**", DIAS_NOMBRES, index=dia_def_idx, horizontal=True)

            idx_dia_sel = DIAS_NOMBRES.index(dia_seleccionado)
            fecha_consulta = lunes_semana + datetime.timedelta(days=idx_dia_sel)
            fecha_consulta_str = fecha_consulta.strftime("%d/%m/%Y")

            df_filtered = df_horarios.copy()
            df_filtered["fecha_dt"] = pd.to_datetime(df_filtered["fecha"]).dt.date
            df_filtered = df_filtered[df_filtered["fecha_dt"] == fecha_consulta]

            hay_filtro_asig = bool(q_asig.strip())
            hay_filtro_doc = bool(q_doc.strip())

            if hay_filtro_asig:
                df_filtered = df_filtered[df_filtered["asignatura"].apply(normalizar_texto).str.contains(q_asig, regex=False)]
            if hay_filtro_doc:
                df_filtered = df_filtered[df_filtered["docente"].apply(normalizar_texto).str.contains(q_doc, regex=False)]

            if hay_filtro_asig or hay_filtro_doc:
                criterios = []
                if hay_filtro_asig:
                    criterios.append(f"materia **'{busqueda_asig.strip()}'**")
                if hay_filtro_doc:
                    criterios.append(f"profesor(a) **'{busqueda_doc.strip()}'**")
                criterio_txt = " y ".join(criterios)

                if df_filtered.empty:
                    st.info(
                        f"ℹ️ Para el día **{dia_seleccionado} ({fecha_consulta_str})** "
                        f"la/el {criterio_txt} **no tiene asignación de clases** en las aulas pertenecientes al departamento, "
                        f"por favor valide con su coordinador(a)."
                    )
                else:
                    aulas_con_clase = sorted([str(s).upper() for s in df_filtered["espacio"].unique() if pd.notna(s)])
                    
                    st.markdown(
                        f"##### 📍 **Clases Encontradas ({criterio_txt}) el {dia_seleccionado} ({fecha_consulta_str}):**"
                    )

                    renderizar_matriz_vertical_con_horas_izq(
                        df_filtered,
                        aulas_con_clase,
                        es_vista_dias=False,
                        rango_horas=rango_horas,
                        solo_clases_ocupadas=True
                    )
            else:
                st.markdown(f"##### 📍 **Vista General de Aulas del Día:** {dia_seleccionado} ({fecha_consulta_str})")

                renderizar_matriz_vertical_con_horas_izq(
                    df_filtered,
                    salones_unicos,
                    es_vista_dias=False,
                    rango_horas=rango_horas,
                    solo_clases_ocupadas=False
                )
        else:
            # VISTA DE UN SALÓN ESPECÍFICO CON GENERADOR DINÁMICO DE CÓDIGO QR
            sabado_semana = lunes_semana + datetime.timedelta(days=5)
            df_filtered = df_horarios.copy()
            df_filtered["fecha_dt"] = pd.to_datetime(df_filtered["fecha"]).dt.date
            df_filtered = df_filtered[
                (df_filtered["fecha_dt"] >= lunes_semana) &
                (df_filtered["fecha_dt"] <= sabado_semana) &
                (df_filtered["espacio"].apply(normalizar_texto) == normalizar_texto(salon_sel))
            ]

            hay_filtro_asig = bool(q_asig.strip())
            hay_filtro_doc = bool(q_doc.strip())

            if hay_filtro_asig:
                df_filtered = df_filtered[df_filtered["asignatura"].apply(normalizar_texto).str.contains(q_asig, regex=False)]
            if hay_filtro_doc:
                df_filtered = df_filtered[df_filtered["docente"].apply(normalizar_texto).str.contains(q_doc, regex=False)]

            col_title, col_qr = st.columns([3, 1])
            with col_title:
                st.markdown(f"##### 🏛️ **Horario Semanal del Salón:** {salon_sel}")
            
            with col_qr:
                with st.popover("📱 Código QR de este Salón"):
                    # Se remueven barras sobrantes al final de APP_URL
                    raw_app_url = str(st.secrets.get("APP_URL", "https://horariosdte.streamlit.app")).strip()
                    url_base_app = raw_app_url.rstrip("/")
                    
                    # Codificación web limpia para evitar errores en móviles
                    salon_encoded = urllib.parse.quote(salon_sel)
                    full_qr_url = f"{url_base_app}/?salon={salon_encoded}"
                    
                    qr_img_src = generar_url_qr(full_qr_url, tamano=250)
                    
                    st.markdown(f"**Escanea para abrir directo en:**<br>`{salon_sel}`", unsafe_allow_html=True)
                    st.image(qr_img_src, width=200)
                    st.caption("📱 *Imprime este código y pégalo en la puerta de la sala.*")

            if (hay_filtro_asig or hay_filtro_doc):
                if df_filtered.empty:
                    criterios = []
                    if hay_filtro_asig:
                        criterios.append(f"materia **'{busqueda_asig.strip()}'**")
                    if hay_filtro_doc:
                        criterios.append(f"profesor(a) **'{busqueda_doc.strip()}'**")
                    criterio_txt = " y ".join(criterios)
                    st.info(f"ℹ️ El salón **{salon_sel}** no tiene clases registradas para {criterio_txt} durante esta semana.")
                else:
                    dias_con_clase = []
                    for d_nom in DIAS_NOMBRES:
                        tiene_clase = not df_filtered[
                            df_filtered["dia"].apply(normalizar_texto) == normalizar_texto(d_nom)
                        ].empty
                        if tiene_clase:
                            dias_con_clase.append(d_nom)

                    renderizar_matriz_vertical_con_horas_izq(
                        df_filtered,
                        dias_con_clase,
                        es_vista_dias=True,
                        dia_hoy_nombre=dia_nombre_hoy,
                        rango_horas=rango_horas,
                        solo_clases_ocupadas=True
                    )
            else:
                renderizar_matriz_vertical_con_horas_izq(
                    df_filtered,
                    DIAS_NOMBRES,
                    es_vista_dias=True,
                    dia_hoy_nombre=dia_nombre_hoy,
                    rango_horas=rango_horas,
                    solo_clases_ocupadas=False
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
                            <div style="font-size:0.82rem; opacity:0.85;">⏰ <b>Horario:</b> {formatear_12h(h_i)} - {formatear_12h(h_f)}</div>
                            <div style="font-size:0.82rem; opacity:0.85;">👨‍🏫 <b>Responsable:</b> {resp_ev}</div>
                            {obs_html}
                        </div>
                        """
                        st.markdown(card_agenda_html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 3: EDICIÓN RÁPIDA DE MATERIAS (SIN ID Y EN FORMATO 12 HORAS)
# -----------------------------------------------------------------------------
if st.session_state.authenticated and tab_edicion:
    with tab_edicion:
        st.subheader("✏️ Edición Directa de Horarios y Materias")
        st.caption("Modifica, agrega o elimina clases directamente en la tabla interactiva sin recargar la base de datos.")

        df_db = db.obtener_todos_los_horarios()

        if df_db.empty:
            st.info("La base de datos se encuentra vacía. Un administrador debe realizar el cargue inicial.")
        else:
            df_unicos = df_db.drop_duplicates(subset=["espacio", "dia", "hora_inicio", "hora_fin", "asignatura", "docente"]).copy()
            
            df_editor = pd.DataFrame()
            df_editor["ESPACIO / SALÓN"] = df_unicos["espacio"].astype(str).str.upper()
            df_editor["DÍA"] = df_unicos["dia"].astype(str).str.upper()
            df_editor["HORA INICIO"] = df_unicos["hora_inicio"].apply(formatear_12h)
            df_editor["HORA FIN"] = df_unicos["hora_fin"].apply(formatear_12h)
            df_editor["ASIGNATURA"] = df_unicos["asignatura"].astype(str).str.upper()
            df_editor["DOCENTE"] = df_unicos["docente"].astype(str).str.upper()

            salones_existentes = sorted([str(s).upper() for s in df_editor["ESPACIO / SALÓN"].unique() if pd.notna(s)])

            st.info("💡 **Instrucciones:** Haz doble clic sobre cualquier casilla para editar. Usa las listas desplegables para las horas AM/PM.")

            df_modificado = st.data_editor(
                df_editor,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "ESPACIO / SALÓN": st.column_config.SelectboxColumn("Salón / Aula", options=salones_existentes, required=True),
                    "DÍA": st.column_config.SelectboxColumn("Día", options=["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO"], required=True),
                    "HORA INICIO": st.column_config.SelectboxColumn("Hora Inicio", options=OPCIONES_HORAS_12H[:-1], required=True),
                    "HORA FIN": st.column_config.SelectboxColumn("Hora Fin", options=OPCIONES_HORAS_12H[1:], required=True),
                    "ASIGNATURA": st.column_config.TextColumn("Asignatura", required=True),
                    "DOCENTE": st.column_config.TextColumn("Docente / Responsable"),
                },
                key="editor_materias_db"
            )

            st.markdown("---")
            if st.button("💾 Guardar Cambios en la Base de Datos", type="primary"):
                try:
                    df_guardar = df_modificado.copy()
                    df_guardar["HORA INICIO (24H)"] = df_guardar["HORA INICIO"].apply(parsear_12h_a_24h)
                    df_guardar["HORA FIN (24H)"] = df_guardar["HORA FIN"].apply(parsear_12h_a_24h)

                    controller.actualizar_horarios_desde_editor(df_guardar)
                    st.success("✅ ¡Base de datos actualizada con éxito!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Error al guardar los cambios: {err}")

# -----------------------------------------------------------------------------
# TAB 4 & 5: CARGA Y EVENTOS (ADMIN)
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
                    
                    df_edit["HORA INICIO"] = df_edit["HORA INICIO (24H)"].apply(formatear_12h)
                    df_edit["HORA FIN"] = df_edit["HORA FIN (24H)"].apply(formatear_12h)
                    
                    df_edit_vis = df_edit[["ESPACIO / SALÓN", "DÍA", "HORA INICIO", "HORA FIN", "ASIGNATURA", "DOCENTE"]].copy()

                    st.markdown("---")
                    st.markdown("### 3️⃣ Paso 3: Confirmar Oferta Académica")

                    aulas_detectadas_excel = sorted(df_edit_vis["ESPACIO / SALÓN"].unique().tolist())

                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("📚 Clases a Programar", len(df_edit_vis))
                    col_m2.metric("🏛️ Aulas Asignadas", len(aulas_detectadas_excel))
                    col_m3.metric("⏰ Horario Oficial Funcionarios", "07:00 AM a 07:00 PM")

                    df_editado_vis = st.data_editor(
                        df_edit_vis,
                        num_rows="dynamic",
                        use_container_width=True,
                        column_config={
                            "ESPACIO / SALÓN": st.column_config.SelectboxColumn("Salón / Aula", options=aulas_detectadas_excel, required=True),
                            "DÍA": st.column_config.SelectboxColumn("Día de la Semana", options=["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO"], required=True),
                            "HORA INICIO": st.column_config.SelectboxColumn("Hora Inicio", options=OPCIONES_HORAS_12H[:-1], required=True),
                            "HORA FIN": st.column_config.SelectboxColumn("Hora Fin", options=OPCIONES_HORAS_12H[1:], required=True),
                            "ASIGNATURA": st.column_config.TextColumn("Asignatura / Materia", required=True),
                            "DOCENTE": st.column_config.TextColumn("Docente / Profesor"),
                        },
                    )

                    df_editado_final = df_editado_vis.copy()
                    df_editado_final["HORA INICIO (24H)"] = df_editado_final["HORA INICIO"].apply(parsear_12h_a_24h)
                    df_editado_final["HORA FIN (24H)"] = df_editado_final["HORA FIN"].apply(parsear_12h_a_24h)

                    errores_rango = controller.validar_rango_laboral(df_editado_final)

                    if errores_rango:
                        st.error("🚨 **Horario No Permitido:** Hay clases configuradas fuera del rango oficial (07:00 AM a 07:00 PM).")
                    else:
                        st.markdown("---")
                        if st.button("🚀 Confirmar y Guardar Semestre", type="primary"):
                            controller.proyectar_y_guardar_semestre(df_editado_final, f_inicio, f_fin)
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
        ev_h_ini_lbl = col_h1.selectbox("3️⃣ Hora Inicio:", options=OPCIONES_HORAS_12H[:-1], index=3)
        ev_h_fin_lbl = col_h2.selectbox("4️⃣ Hora Fin:", options=OPCIONES_HORAS_12H[1:], index=4)

        ev_h_ini = parsear_12h_a_24h(ev_h_ini_lbl)
        ev_h_fin = parsear_12h_a_24h(ev_h_fin_lbl)

        ev_asig = st.text_input("5️⃣ Nombre del Evento / Clase Faltante:", placeholder="Ej. CONTINGENCIA MATEMATICAS")
        ev_doc = st.text_input("6️⃣ Responsable / Docente:", placeholder="Ej. ING. GARCÍA")

        fecha_ev_str = ev_fecha.strftime("%Y-%m-%d")
        conflictos = db.verificar_conflicto_horario(ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin)

        ev_obs = ""
        requiere_obs = False

        if conflictos:
            requiere_obs = True
            st.error(f"🚨 **Espacio Ya Ocupado:** El salón **{ev_salon}** ya tiene programación el **{fecha_ev_str}** entre las **{formatear_12h(ev_h_ini)} y {formatear_12h(ev_h_fin)}**:")
            for c in conflictos:
                c_asig, c_doc, c_tipo, c_ini, c_fin = c[1].upper(), c[2].upper(), c[5].upper(), c[3], c[4]
                st.warning(f"• **{c_asig}** ({c_tipo}) | Responsable: **{c_doc}** | Horario: {formatear_12h(c_ini)} - {formatear_12h(c_fin)}")

            st.markdown("---")
            ev_obs = st.text_area("7️⃣ Observaciones (OBLIGATORIO por ocupar un espacio asignado):", placeholder="Especifica la razón por la cual se reasigna el espacio...")
        else:
            st.success(f"🟢 **Aula Libre:** El salón {ev_salon} está completamente disponible en la franja {formatear_12h(ev_h_ini)} a {formatear_12h(ev_h_fin)}.")

        st.markdown("---")
        if st.button("💾 Guardar y Asignar Espacio", type="primary"):
            if ev_h_fin <= ev_h_ini:
                st.error("La Hora Fin debe ser posterior a la Hora Inicio.")
            elif not ev_asig.strip() or not ev_doc.strip():
                st.error("Debes ingresar el Nombre del Evento / Clase y el Responsable.")
            elif requiere_obs and not ev_obs.strip():
                st.error("⚠️ **Observación Requerida:** Debes ingresar la razón de la asignación sobre un espacio que ya estaba ocupado.")
            else:
                db.agregar_evento_especial(ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin, ev_asig, ev_doc, ev_obs)
                mostrar_popup_evento_exito(ev_asig, ev_salon, fecha_ev_str, ev_h_ini, ev_h_fin, ev_doc)