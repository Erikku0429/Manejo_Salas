import datetime
import os
import sys
import unicodedata

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.horario_model import HorarioModel


def normalizar_texto(texto):
  if not texto or not isinstance(texto, str):
    return ''
  texto_norm = unicodedata.normalize('NFD', texto)
  texto_sin_tildes = texto_norm.encode('ascii', 'ignore').decode('utf-8')
  return texto_sin_tildes.lower().strip()


MAPA_DIAS_ESP = {
    0: 'LUNES',
    1: 'MARTES',
    2: 'MIÉRCOLES',
    3: 'JUEVES',
    4: 'VIERNES',
    5: 'SÁBADO',
    6: 'DOMINGO',
}


class HorarioController:

  def __init__(self):
    self.model = HorarioModel()
    self.salones_disponibles = [
        'E105 (Sala CAD)',
        'B222 (Sala computadores)',
        'B222 (Salón posgrados)',
    ]
    self.dias_semana = [
        'LUNES',
        'MARTES',
        'MIÉRCOLES',
        'JUEVES',
        'VIERNES',
        'SÁBADO',
    ]

  def cargar_nuevo_excel(self, file_object):
    return self.model.procesar_excel_a_db(file_source=file_object)

  def obtener_dia_semana_texto(self, fecha_dt):
    return MAPA_DIAS_ESP.get(fecha_dt.weekday(), 'LUNES')

  def obtener_bloques_por_fecha_y_salon(self, fecha_dt, salon_sel):
    df_todos = self.model.obtener_bloques()
    if df_todos.empty:
      return df_todos

    dia_nombre = self.obtener_dia_semana_texto(fecha_dt)
    fecha_str = fecha_dt.strftime('%Y-%m-%d')

    # Filtrar bloques del salón para ese día de la semana
    df_salon = df_todos[
        (df_todos['espacio'] == salon_sel) & (df_todos['dia'] == dia_nombre)
    ].copy()

    # Si hay eventos específicos para esa fecha, aplicarlos/priorizarlos
    df_eventos_fecha = df_todos[
        (df_todos['espacio'] == salon_sel)
        & (df_todos['fecha_especifica'] == fecha_str)
    ]

    if not df_eventos_fecha.empty:
      # Eliminar o sobreescribir los que entren en conflicto
      for _, evt in df_eventos_fecha.iterrows():
        hi, hf = evt['hora_inicio'], evt['hora_fin']
        mask_conflicto = (df_salon['hora_inicio'] < hf) & (
            df_salon['hora_fin'] > hi
        )
        df_salon = df_salon[~mask_conflicto]

      # Concatenar eventos específicos
      df_salon = pd.concat([df_salon, df_eventos_fecha], ignore_index=True)

    return df_salon.sort_values(by=['hora_inicio'])

  def obtener_eventos_especiales_del_dia(self, fecha_dt):
    """Devuelve los eventos agendados específicamente para la fecha seleccionada."""
    df_todos = self.model.obtener_bloques()
    if df_todos.empty or 'fecha_especifica' not in df_todos.columns:
      return pd.DataFrame()

    fecha_str = fecha_dt.strftime('%Y-%m-%d')
    return df_todos[df_todos['fecha_especifica'] == fecha_str].sort_values(
        by=['espacio', 'hora_inicio']
    )

  def buscar_bloques_globales(self, termino_busqueda, fecha_dt):
    df_bloques = self.model.obtener_bloques()
    if df_bloques.empty:
      return df_bloques

    busqueda_norm = normalizar_texto(termino_busqueda)
    if not busqueda_norm:
      return df_bloques

    def coincide_busqueda(row):
      if row['estado'] == 'LIBRE':
        return False
      asig_norm = normalizar_texto(row['asignatura'])
      doc_norm = normalizar_texto(row['docente'])
      return (busqueda_norm in asig_norm) or (busqueda_norm in doc_norm)

    mask = df_bloques.apply(coincide_busqueda, axis=1)
    return df_bloques[mask].sort_values(by=['dia', 'hora_inicio'])

  def verificar_traslape_evento(self, espacio, dia, hora_inicio, hora_fin):
    df_bloques = self.model.obtener_bloques()
    if df_bloques.empty:
      return True, pd.DataFrame()

    conflictos = df_bloques[
        (df_bloques['espacio'] == espacio)
        & (df_bloques['dia'] == dia)
        & (df_bloques['estado'] == 'OCUPADO')
        & (df_bloques['hora_inicio'] < hora_fin)
        & (df_bloques['hora_fin'] > hora_inicio)
    ]

    return conflictos.empty, conflictos

  def registrar_nuevo_evento(
      self,
      espacio,
      dia,
      hora_inicio,
      hora_fin,
      asignatura,
      docente,
      fecha_especifica='',
      motivo='',
  ):
    if hora_fin <= hora_inicio:
      raise ValueError('La hora de fin debe ser mayor a la hora de inicio.')
    self.model.agregar_evento(
        espacio,
        dia,
        hora_inicio,
        hora_fin,
        asignatura,
        docente,
        fecha_especifica,
        motivo,
    )

  def eliminar_evento_existente(self, record_id):
    self.model.eliminar_evento(record_id)