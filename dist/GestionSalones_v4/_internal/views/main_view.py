import datetime
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controllers.horario_controller import HorarioController
import streamlit as st


@st.dialog('⚠️ Base de Datos Requerida')
def mostrar_popup_carga_inicial(controller):
  st.warning('No se encontraron horarios cargados en el sistema.')
  st.write(
      'Por favor, sube el archivo Excel (.xlsx) con la programación del'
      ' semestre para activar las consultas.'
  )
  archivo_cargado = st.file_uploader(
      'Selecciona el archivo Excel:', type=['xlsx', 'xls'], key='init_upload'
  )

  if archivo_cargado is not None:
    if st.button('📥 Procesar y Cargar Base de Datos', use_container_width=True):
      try:
        n_bloques = controller.cargar_nuevo_excel(archivo_cargado)
        st.success(f'¡Carga exitosa! Se procesaron {n_bloques} bloques.')
        st.rerun()
      except Exception as e:
        st.error(f'Error al procesar el archivo: {e}')


@st.dialog('🎉 Carga Exitosa')
def mostrar_popup_exito(n_bloques):
  st.success('¡La base de datos ha sido actualizada correctamente!')
  st.write(
      f'Se han procesado e importado un total de **{n_bloques} bloques** de'
      ' clase.'
  )
  if st.button('Entendido', use_container_width=True):
    st.rerun()


@st.dialog('📋 Validación de Disponibilidad')
def mostrar_popup_validacion_reserva(
    controller, datos_evento, es_libre, conflictos
):
  espacio = datos_evento['espacio']
  dia = datos_evento['dia']
  hi = datos_evento['hora_inicio']
  hf = datos_evento['hora_fin']
  asig = datos_evento['asignatura']
  doc = datos_evento['docente']

  if es_libre:
    st.success(f'🟢 El espacio **{espacio}** está **DISPONIBLE**.')
    st.write(f'• **Día:** {dia}')
    st.write(f'• **Franja:** {hi}:00 - {hf}:00 ({hf-hi}h)')
    st.write(f'• **Evento:** {asig}')
    st.write(f'• **Encargado:** {doc}')

    if st.button('✅ Confirmar y Agendar Evento', use_container_width=True):
      controller.registrar_nuevo_evento(espacio, dia, hi, hf, asig, doc)
      st.success('¡Evento agendado exitosamente!')
      st.rerun()
  else:
    st.error(
        f'🔴 El espacio **{espacio}** está **OCUPADO** en ese horario por:'
    )
    for _, c in conflictos.iterrows():
      st.markdown(
          f'• ⚡ **{c["asignatura"]}** ({c["docente"]}) — {c["franja_horaria"]}'
      )

    st.warning(
        '⚠️ **Asignación Temporal / Sobreescritura requerida**\nIndica la fecha'
        ' y motivo del apartado.'
    )

    fecha_reserva = st.date_input(
        '📅 Fecha del apartado temporal:', min_value=datetime.date.today()
    )
    motivo = st.text_area(
        '📝 Motivo / Justificación del apartado:',
        placeholder='Ej. Práctica especial, examen departamental...',
    )

    if st.button('⚠️ Asignar Temporalmente', use_container_width=True):
      if not motivo.strip():
        st.error('Es obligatorio ingresar el motivo del apartado.')
      else:
        fecha_str = fecha_reserva.strftime('%Y-%m-%d')
        asig_temp = f'[RESERVA TEMPORAL] {asig}'
        controller.registrar_nuevo_evento(
            espacio,
            dia,
            hi,
            hf,
            asig_temp,
            doc,
            fecha_especifica=fecha_str,
            motivo=motivo.strip(),
        )
        st.success(f'¡Reserva temporal registrada para el día {fecha_str}!')
        st.rerun()


class MainView:

  def __init__(self):
    self.controller = HorarioController()

  def render(self):
    st.set_page_config(
        page_title='Gestión de Espacios DTE', page_icon='🏫', layout='wide'
    )

    df_verificacion = self.controller.model.obtener_bloques()

    if df_verificacion.empty or 'estado' not in df_verificacion.columns:
      st.sidebar.title('🏢 Perfil de Acceso')
      st.sidebar.info('Sistema pendiente de inicialización.')
      st.title('🏫 Control y Ocupación de Espacios (DTE)')
      st.info(
          '👋 Bienvenido. Por favor, completa la carga inicial en la ventana'
          ' emergente.'
      )
      mostrar_popup_carga_inicial(self.controller)
      return

    es_modo_publico = os.environ.get('PUBLIC_MODE', '0') == '1'

    # --------------------------------------------------
    # SECCIÓN LATERAL (SIDEBAR): SELECTOR DE FECHA Y FEED DE EVENTOS
    # --------------------------------------------------
    st.sidebar.title('📅 Fecha de Consulta')
    fecha_sel = st.sidebar.date_input(
        'Selecciona una fecha:', value=datetime.date.today()
    )

    dia_nombre_txt = self.controller.obtener_dia_semana_texto(fecha_sel)
    st.sidebar.caption(
        f'📆 **Día:** {dia_nombre_txt} ({fecha_sel.strftime("%d/%m/%Y")})'
    )

    st.sidebar.divider()

    # Feed lateral de Eventos Especiales de la Fecha
    st.sidebar.subheader('⚡ Eventos Específicos del Día')
    df_evts_dia = self.controller.obtener_eventos_especiales_del_dia(fecha_sel)

    if not df_evts_dia.empty:
      for _, e in df_evts_dia.iterrows():
        st.sidebar.info(
            f"📍 **{e['espacio']}**\n\n"
            f"🕒 **{e['franja_horaria']}**: {e['asignatura']}\n\n"
            f"👨‍🏫 *{e['docente']}*\n\n"
            f"📝 Motivo: {e['motivo']}"
        )
    else:
      st.sidebar.caption('No hay reservas especiales registradas para esta fecha.')

    st.sidebar.divider()

    if es_modo_publico:
      self._render_vista_usuario(fecha_sel)
    else:
      perfil = st.sidebar.radio(
          'Perfil:', ['👤 Usuario (Consulta)', '🔐 Administrador']
      )
      st.sidebar.divider()
      if perfil == '👤 Usuario (Consulta)':
        self._render_vista_usuario(fecha_sel)
      else:
        self._render_vista_admin()

  def _render_vista_usuario(self, fecha_sel):
    dia_nombre_txt = self.controller.obtener_dia_semana_texto(fecha_sel)
    st.title(
        f'🏫 Disponibilidad de Aulas — {dia_nombre_txt}'
        f' ({fecha_sel.strftime("%d/%m/%Y")})'
    )

    col_sal, col_bus = st.columns([1, 2])

    with col_bus:
      busqueda = st.text_input(
          '🔎 Buscar Docente o Asignatura (Global):',
          placeholder='Ej. Yovanni, joaquin sanchez, estadistica...',
      ).strip()

    with col_sal:
      salon_sel = st.selectbox(
          'Filtrar por salón (si no hay búsqueda):',
          self.controller.salones_disponibles,
          disabled=bool(busqueda),
      )

    if busqueda:
      df_bloques = self.controller.buscar_bloques_globales(busqueda, fecha_sel)
      if df_bloques.empty:
        st.warning(f'No se encontraron clases coincidentes con "{busqueda}".')
        return
    else:
      df_bloques = self.controller.obtener_bloques_por_fecha_y_salon(
          fecha_sel, salon_sel
      )

    if not df_bloques.empty:
      st.markdown(
          """
            <style>
            @keyframes energyWave {
                0% { box-shadow: 0 0 4px rgba(255, 136, 51, 0.3); border-color: #ff8833; }
                50% { box-shadow: 0 0 12px rgba(255, 170, 85, 0.7); border-color: #ffaa55; }
                100% { box-shadow: 0 0 4px rgba(255, 136, 51, 0.3); border-color: #ff8833; }
            }
            @keyframes shieldGlow {
                0% { box-shadow: 0 0 4px rgba(0, 255, 136, 0.3); }
                50% { box-shadow: 0 0 12px rgba(0, 255, 136, 0.8); }
                100% { box-shadow: 0 0 4px rgba(0, 255, 136, 0.3); }
            }
            .block-card-libre {
                background-color: #052216;
                color: #00ffaa;
                border: 1.5px solid #00ff88;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 10px;
                min-height: 125px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                animation: shieldGlow 2.5s infinite ease-in-out;
            }
            .block-card-ocupado {
                background: linear-gradient(135deg, #2b1a12 0%, #3d2215 100%);
                color: #ffe3d1;
                border: 1.5px solid #ff8833;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 10px;
                min-height: 125px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                animation: energyWave 3s infinite ease-in-out;
            }
            .room-badge {
                background-color: rgba(255, 255, 255, 0.15);
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.75rem;
                margin-top: 4px;
                display: inline-block;
            }
            </style>
            """,
          unsafe_allow_html=True,
      )

      for _, b in df_bloques.iterrows():
        if b.get('estado') == 'LIBRE':
          st.markdown(
              f"""
                        <div class="block-card-libre">
                            <b>🕒 {b['franja_horaria']}</b> ({b['duracion_horas']}h)<br>
                            🟢 <b>AULA DISPONIBLE</b>
                        </div>
                        """,
              unsafe_allow_html=True,
          )
        else:
          motivo_lbl = (
              f"<br><small>📝 {b['motivo']}</small>" if b.get('motivo') else ''
          )
          st.markdown(
              f"""
                        <div class="block-card-ocupado">
                            <b>🕒 {b['franja_horaria']}</b> ({b['duracion_horas']}h)<br>
                            ⚡ <b>{b['asignatura']}</b><br>
                            <small>👨‍🏫 {b['docente']}</small>
                            {motivo_lbl}<br>
                            <span class="room-badge">📍 {b['espacio']}</span>
                        </div>
                        """,
              unsafe_allow_html=True,
          )

  def _render_vista_admin(self):
    st.title('🔐 Panel de Administración y Gestión de Eventos')

    password = st.text_input(
        'Ingresa la contraseña de administrador:', type='password'
    )

    if password == '1234':
      st.success('Acceso Autorizado')

      tab1, tab2, tab3 = st.tabs([
          '➕ Añadir Evento / Reserva',
          '✏️ Eliminar Clases / Eventos',
          '📥 Cargar Semestre Excel',
      ])

      with tab1:
        st.subheader('📌 Agendar Nuevo Evento o Reserva')
        col1, col2 = st.columns(2)

        with col1:
          espacio = st.selectbox(
              'Espacio / Salón:',
              self.controller.salones_disponibles,
              key='add_espacio',
          )
          dia = st.selectbox(
              'Día de la semana:',
              self.controller.dias_semana,
              key='add_dia',
          )
          h_inicio = st.number_input('Hora Inicio (24h):', 7, 19, 13)
          h_fin = st.number_input('Hora Fin (24h):', 8, 20, 15)

        with col2:
          asignatura = st.text_input(
              'Nombre del Evento / Asignatura:',
              placeholder='Ej. Conferencia Robótica',
          )
          docente = st.text_input(
              'Encargado / Docente:', placeholder='Ej. Dr. Carlos Pérez'
          )

        if st.button('🔍 Verificar y Agendar', use_container_width=True):
          if not asignatura.strip() or not docente.strip():
            st.error('Por favor completa el nombre del evento y el encargado.')
          elif h_fin <= h_inicio:
            st.error('La hora de fin debe ser mayor a la hora de inicio.')
          else:
            datos_evt = {
                'espacio': espacio,
                'dia': dia,
                'hora_inicio': h_inicio,
                'hora_fin': h_fin,
                'asignatura': asignatura,
                'docente': docente,
            }

            es_libre, conflictos = (
                self.controller.verificar_traslape_evento(
                    espacio, dia, h_inicio, h_fin
                )
            )
            mostrar_popup_validacion_reserva(
                self.controller, datos_evt, es_libre, conflictos
            )

      with tab2:
        st.subheader('🗑️ Gestionar y Eliminar Registros')
        df_todos = self.controller.model.obtener_bloques()
        df_ocupados = df_todos[df_todos['estado'] == 'OCUPADO']

        if not df_ocupados.empty:
          opciones = {
              f"{row['id']} - {row['espacio']} | {row['dia']} ({row['franja_horaria']}): {row['asignatura']}": row[
                  'id'
              ]
              for _, row in df_ocupados.iterrows()
          }

          item_sel = st.selectbox(
              'Selecciona el evento o clase:', list(opciones.keys())
          )
          record_id = opciones[item_sel]

          if st.button('🗑️ Eliminar Registro', use_container_width=True):
            self.controller.eliminar_evento_existente(record_id)
            st.warning('¡Registro eliminado!')
            st.rerun()
        else:
          st.info('No hay eventos u ocupaciones registradas.')

      with tab3:
        st.subheader('⚙️ Cargar Nuevo Semestre Académico desde Excel')
        archivo_cargado = st.file_uploader(
            'Selecciona el archivo Excel (.xlsx):', type=['xlsx', 'xls']
        )

        if archivo_cargado is not None:
          if st.button('📥 Procesar y Cargar Horarios'):
            try:
              n_bloques = self.controller.cargar_nuevo_excel(archivo_cargado)
              mostrar_popup_exito(n_bloques)
            except Exception as e:
              st.error(f'Error al procesar el archivo: {e}')

    elif password != '':
      st.error('Contraseña incorrecta.')