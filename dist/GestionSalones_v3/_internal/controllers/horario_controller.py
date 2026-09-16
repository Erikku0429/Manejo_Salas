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

  def obtener_bloques_por_salon(self, salon_sel):
    df_bloques = self.model.obtener_bloques()
    if df_bloques.empty:
      return df_bloques
    return df_bloques[df_bloques['espacio'] == salon_sel].sort_values(
        by=['dia', 'hora_inicio']
    )

  def buscar_bloques_globales(self, termino_busqueda):
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

  def registrar_nuevo_evento(
      self, espacio, dia, hora_inicio, hora_fin, asignatura, docente
  ):
    """Registra una reserva o nueva clase."""
    if hora_fin <= hora_inicio:
      raise ValueError('La hora de fin debe ser mayor a la hora de inicio.')
    self.model.agregar_evento(
        espacio, dia, hora_inicio, hora_fin, asignatura, docente
    )

  def modificar_evento_existente(
      self, record_id, espacio, dia, hora_inicio, hora_fin, asignatura, docente
  ):
    """Actualiza una clase o evento existente."""
    if hora_fin <= hora_inicio:
      raise ValueError('La hora de fin debe ser mayor a la hora de inicio.')
    self.model.actualizar_evento(
        record_id, espacio, dia, hora_inicio, hora_fin, asignatura, docente
    )

  def eliminar_evento_existente(self, record_id):
    """Elimina una clase o evento de la base de datos."""
    self.model.eliminar_evento(record_id)