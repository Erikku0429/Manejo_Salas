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

    st.sidebar.title('🏢 Perfil de Acceso')
    perfil = st.sidebar.radio(
        'Selecciona tu perfil:',
        ['👤 Usuario (Consulta)', '🔐 Administrador'],
    )

    st.sidebar.divider()

    if perfil == '👤 Usuario (Consulta)':
      self._render_vista_usuario()
    else:
      self._render_vista_admin()

  def _render_vista_usuario(self):
    st.title('🏫 Disponibilidad y Horarios por Bloques')
    st.markdown(
        'Consulta por salón o realiza una **búsqueda global de docentes y'
        ' asignaturas**.'
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
      df_bloques = self.controller.buscar_bloques_globales(busqueda)
      if df_bloques.empty:
        st.warning(f'No se encontraron clases coincidentes con "{busqueda}".')
        return
    else:
      df_bloques = self.controller.obtener_bloques_por_salon(salon_sel)

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

      dias_presentes = [
          d for d in self.controller.dias_semana if d in df_bloques['dia'].unique()
      ]
      cols = st.columns(len(dias_presentes))

      for idx, dia in enumerate(dias_presentes):
        with cols[idx]:
          st.subheader(f'📅 {dia}')
          bloques_dia = df_bloques[df_bloques['dia'] == dia]

          for _, b in bloques_dia.iterrows():
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
              st.markdown(
                  f"""
                                <div class="block-card-ocupado">
                                    <b>🕒 {b['franja_horaria']}</b> ({b['duracion_horas']}h)<br>
                                    ⚡ <b>{b['asignatura']}</b><br>
                                    <small>👨‍🏫 {b['docente']}</small><br>
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
          '✏️ Modificar / Eliminar Clases',
          '📥 Cargar Semestre Excel',
      ])

      # TAB 1: Añadir Nuevo Evento / Reserva
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

        if st.button('✅ Guardar Evento / Reserva', use_container_width=True):
          if not asignatura or not docente:
            st.error('Por favor completa el nombre del evento y el encargado.')
          else:
            try:
              self.controller.registrar_nuevo_evento(
                  espacio, dia, h_inicio, h_fin, asignatura, docente
              )
              st.success('¡Evento agendado exitosamente!')
              st.rerun()
            except Exception as e:
              st.error(f'Error al registrar evento: {e}')

      # TAB 2: Modificar o Eliminar Eventos
      with tab2:
        st.subheader('✏️ Gestionar Clases y Reservas Existentes')
        df_todos = self.controller.model.obtener_bloques()
        df_ocupados = df_todos[df_todos['estado'] == 'OCUPADO']

        if not df_ocupados.empty:
          # Selector interactivo de evento
          opciones = {
              f"{row['id']} - {row['espacio']} | {row['dia']} ({row['franja_horaria']}): {row['asignatura']}": row[
                  'id'
              ]
              for _, row in df_ocupados.iterrows()
          }

          item_sel = st.selectbox('Selecciona la clase o evento a modificar:', list(opciones.keys()))
          record_id = opciones[item_sel]
          row_curr = df_ocupados[df_ocupados['id'] == record_id].iloc[0]

          c_mod1, c_mod2 = st.columns(2)
          with c_mod1:
            esp_mod = st.selectbox(
                'Salón:',
                self.controller.salones_disponibles,
                index=self.controller.salones_disponibles.index(
                    row_curr['espacio']
                ),
            )
            dia_mod = st.selectbox(
                'Día:',
                self.controller.dias_semana,
                index=self.controller.dias_semana.index(row_curr['dia']),
            )
            hi_mod = st.number_input(
                'Hora Inicio:', 7, 19, int(row_curr['hora_inicio'])
            )
            hf_mod = st.number_input(
                'Hora Fin:', 8, 20, int(row_curr['hora_fin'])
            )

          with c_mod2:
            asig_mod = st.text_input(
                'Asignatura / Evento:', value=row_curr['asignatura']
            )
            doc_mod = st.text_input('Docente:', value=row_curr['docente'])

          col_btn1, col_btn2 = st.columns(2)
          with col_btn1:
            if st.button('💾 Guardar Cambios', use_container_width=True):
              try:
                self.controller.modificar_evento_existente(
                    record_id,
                    esp_mod,
                    dia_mod,
                    hi_mod,
                    hf_mod,
                    asig_mod,
                    doc_mod,
                )
                st.success('¡Evento actualizado!')
                st.rerun()
              except Exception as e:
                st.error(f'Error al actualizar: {e}')

          with col_btn2:
            if st.button('🗑️ Eliminar Evento', use_container_width=True):
              self.controller.eliminar_evento_existente(record_id)
              st.warning('¡Evento eliminado de la base de datos!')
              st.rerun()
        else:
          st.info('No hay eventos u ocupaciones registradas.')

      # TAB 3: Carga de Archivo Excel
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