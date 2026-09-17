import datetime
from controllers.horario_controller import HorarioController
from models.database import DatabaseModel
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title='Gestión de Aulas Universitarias',
    page_icon='🏫',
    layout='wide',
    initial_sidebar_state='expanded',
)

db = DatabaseModel()
controller = HorarioController(db)


# Modal / Popup de Éxito
@st.dialog('🎉 Confirmación de Carga')
def mostrar_popup_exito(total_registros):
  st.success('### ¡La carga de asignaturas ha sido exitosa!')
  st.write(
      f'Se han proyectado y guardado **{total_registros} sesiones de clase**'
      ' para todo el semestre en la base de datos.'
  )
  st.write(
      'La información está lista para ser consultada de forma persistente.'
  )
  if st.button('Entendido / Cerrar', type='primary'):
    st.rerun()


# Encabezado Princpal
st.title('🏫 Gestión de Aulas y Carga Semestral')

tab_cargue, tab_horarios, tab_eventos = st.tabs([
    '📋 Confirmación de Carga Semestral',
    '📅 Consulta de Horarios',
    '➕ Eventos y Cambios',
])

# -----------------------------------------------------------------------------
# TAB 1: CONFIRMACIÓN Y EDICIÓN AMIGABLE POR CLASES ÚNICAS
# -----------------------------------------------------------------------------
with tab_cargue:
  st.markdown('### 📥 Revisión de la Oferta Académica Semestral')
  st.info(
      '👋 **Instrucciones:** Carga el archivo formateado. El sistema extraerá la'
      ' **lista única de clases del semestre** para que confirmes o ajustes las'
      ' horas de forma sencilla antes de guardar.'
  )

  uploaded_file = st.file_uploader(
      'Selecciona el archivo Excel del semestre (`.xlsx`):', type=['xlsx']
  )

  if uploaded_file is not None:
    try:
      if 'df_unicas' not in st.session_state:
        st.session_state.df_unicas = controller.procesar_excel_cargue_unico(
            uploaded_file
        )

      df_edit = st.session_state.df_unicas

      # Métricas resumen amigables
      col_m1, col_m2, col_m3 = st.columns(3)
      col_m1.metric('📚 Total Asignaturas Únicas', len(df_edit))
      col_m2.metric(
          '🏛️ Aulas Configuradas', len(df_edit['ESPACIO / SALÓN'].unique())
      )
      col_m3.metric('⏰ Rango Oficial Permito', '07:00 a 19:00')

      st.markdown(
          '#### ✏️ Tabla Interactiva de Horarios Base (Edita si es necesario)'
      )

      # Editor amigable sin filas repetidas
      df_editado = st.data_editor(
          df_edit,
          num_rows='dynamic',
          use_container_width=True,
          column_config={
              'ESPACIO / SALÓN': st.column_config.SelectboxColumn(
                  'Salón',
                  options=[
                      'E105 (SALA CAD)',
                      'B222 (SALA COMPUTADORES)',
                      'B222 (SALÓN POSGRADOS)',
                  ],
                  required=True,
              ),
              'DÍA': st.column_config.SelectboxColumn(
                  'Día de la semana',
                  options=[
                      'LUNES',
                      'MARTES',
                      'MIÉRCOLES',
                      'JUEVES',
                      'VIERNES',
                      'SÁBADO',
                  ],
                  required=True,
              ),
              'HORA INICIO (24H)': st.column_config.NumberColumn(
                  'Hora Inicio (7 to 18)', min_value=7, max_value=18, step=1
              ),
              'HORA FIN (24H)': st.column_config.NumberColumn(
                  'Hora Fin (8 to 19)', min_value=8, max_value=19, step=1
              ),
              'ASIGNATURA': st.column_config.TextColumn(
                  'Asignatura', required=True
              ),
              'DOCENTE': st.column_config.TextColumn('Docente'),
          },
      )

      # Configuración de rango de fechas del semestre
      st.markdown('#### 📅 Rango de Fechas para la Proyección del Semestre')
      c_f1, c_f2 = st.columns(2)
      f_inicio = c_f1.date_input(
          'Fecha de Inicio del Semestre:', value=datetime.date(2026, 2, 2)
      )
      f_fin = c_f2.date_input(
          'Fecha de Finalización del Semestre:', value=datetime.date(2026, 6, 30)
      )

      # Validaciones estrictas
      errores_rango = controller.validar_rango_laboral(df_editado)

      if errores_rango:
        st.error(
            '🚨 **Atención:** Hay clases configuradas fuera del rango laboral'
            ' de los funcionarios (07:00 a 19:00) o con horarios vacíos:'
        )
        for err in errores_rango:
          st.warning(
              f"• **{err['asignatura']}** ({err['salon']} - {err['dia']}):"
              f" Horario {err['inicio']}:00 a {err['fin']}:00 hrs."
          )
        st.error(
            '⚠️ Por favor corrige las horas en la tabla superior antes de'
            ' confirmar.'
        )
      else:
        st.markdown('---')
        if st.button('🚀 Confirmar y Guardar Semestre', type='primary'):
          controller.proyectar_y_guardar_semestre(
              df_editado, f_inicio, f_fin
          )
          total_registros = len(db.obtener_todos_los_horarios())
          mostrar_popup_exito(total_registros)

    except Exception as e:
      st.error(f'Error al procesar el archivo: {e}')

# -----------------------------------------------------------------------------
# TAB 2: CONSULTA DE HORARIOS
# -----------------------------------------------------------------------------
with tab_horarios:
  st.subheader('Consulta de Horarios')
  df_horarios = db.obtener_todos_los_horarios()

  if df_horarios.empty:
    st.info('No hay horarios cargados aún.')
  else:
    col1, col2 = st.columns(2)
    s_filter = col1.selectbox(
        'Filtrar Salón:',
        ['TODOS'] + sorted(df_horarios['espacio'].unique().tolist()),
    )
    d_filter = col2.date_input('Filtrar Fecha:', value=None)

    df_view = df_horarios.copy()
    if s_filter != 'TODOS':
      df_view = df_view[df_view['espacio'] == s_filter]
    if d_filter is not None:
      df_view = df_view[df_view['fecha'] == d_filter.strftime('%Y-%m-%d')]

    st.dataframe(
        df_view[[
            'espacio',
            'fecha',
            'dia',
            'hora_inicio',
            'hora_fin',
            'asignatura',
            'docente',
            'tipo_evento',
        ]],
        use_container_width=True,
    )

# -----------------------------------------------------------------------------
# TAB 3: REGISTRO DE EVENTOS
# -----------------------------------------------------------------------------
with tab_eventos:
  st.subheader('Registrar Evento o Reserva Especial')
  with st.form('form_evento_nuevo'):
    col_a, col_b = st.columns(2)
    ev_salon = col_a.selectbox('Salón:', [
        'E105 (SALA CAD)',
        'B222 (SALA COMPUTADORES)',
        'B222 (SALÓN POSGRADOS)',
    ])
    ev_fecha = col_a.date_input('Fecha:', value=datetime.date.today())
    ev_h_ini = col_a.number_input(
        'Hora Inicio (7 a 18):', min_value=7, max_value=18, value=10
    )

    ev_h_fin = col_b.number_input(
        'Hora Fin (8 a 19):', min_value=8, max_value=19, value=12
    )
    ev_asig = col_b.text_input('Asignatura / Evento:', value='EXAMEN PARCIAL')
    ev_doc = col_b.text_input('Docente / Responsable:', value='POR DEFINIR')
    ev_obs = st.text_area('Observación:', value='Reserva puntual de aula')

    if st.form_submit_button('Guardar Evento'):
      if ev_h_fin <= ev_h_ini:
        st.error('La Hora Fin debe ser mayor a la Hora Inicio.')
      else:
        db.agregar_evento_especial(
            ev_salon,
            ev_fecha.strftime('%Y-%m-%d'),
            ev_h_ini,
            ev_h_fin,
            ev_asig,
            ev_doc,
            ev_obs,
        )
        st.success('🎉 Evento registrado correctamente.')
        st.rerun()