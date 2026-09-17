import datetime
import pandas as pd


class HorarioController:

  def __init__(self, db_model):
    self.db = db_model

  def procesar_excel_cargue_unico(self, uploaded_file):
    """Lee el Excel y extrae únicamente la oferta académica base semanal (sin repetición diaria)."""
    df = pd.read_excel(uploaded_file, sheet_name='BD_Calendario_Semestre')

    columnas_requeridas = [
        'ESPACIO / SALÓN',
        'DÍA',
        'HORA INICIO (24H)',
        'HORA FIN (24H)',
        'ASIGNATURA',
        'DOCENTE',
    ]
    for col in columnas_requeridas:
      if col not in df.columns:
        raise ValueError(
            f"El archivo no contiene la columna requerida: '{col}'"
        )

    # Limpieza previa
    df['ESPACIO / SALÓN'] = df['ESPACIO / SALÓN'].astype(str).str.upper().str.strip()
    df['DÍA'] = df['DÍA'].astype(str).str.upper().str.strip()
    df['ASIGNATURA'] = df['ASIGNATURA'].astype(str).str.upper().str.strip()
    df['DOCENTE'] = df['DOCENTE'].astype(str).str.upper().str.strip()
    df['HORA INICIO (24H)'] = pd.to_numeric(
        df['HORA INICIO (24H)'], errors='coerce'
    ).fillna(7)
    df['HORA FIN (24H)'] = pd.to_numeric(
        df['HORA FIN (24H)'], errors='coerce'
    ).fillna(9)

    # DEDUPLICACIÓN: Mantiene únicamente la lista única de asignaturas semanales
    df_unicas = df.drop_duplicates(
        subset=['ESPACIO / SALÓN', 'DÍA', 'ASIGNATURA', 'DOCENTE']
    ).copy()
    return df_unicas.reset_index(drop=True)

  def validar_rango_laboral(self, df_editado):
    """Verifica que ninguna clase esté antes de las 07:00 o después de las 19:00."""
    fuera_de_rango = []
    for idx, row in df_editado.iterrows():
      h_ini = row['HORA INICIO (24H)']
      h_fin = row['HORA FIN (24H)']

      if h_ini < 7 or h_fin > 19 or h_ini >= h_fin:
        fuera_de_rango.append({
            'asignatura': row['ASIGNATURA'],
            'salon': row['ESPACIO / SALÓN'],
            'dia': row['DÍA'],
            'inicio': h_ini,
            'fin': h_fin,
        })
    return fuera_de_rango

  def proyectar_y_guardar_semestre(
      self, df_oferta_confirmada, fecha_inicio, fecha_fin
  ):
    """Toma las clases semanales confirmadas y genera automáticamente el semestre en la BD."""
    mapa_dias = {
        0: 'LUNES',
        1: 'MARTES',
        2: 'MIÉRCOLES',
        3: 'JUEVES',
        4: 'VIERNES',
        5: 'SÁBADO',
        6: 'DOMINGO',
    }

    registros_diarios = []
    curr_date = fecha_inicio

    while curr_date <= fecha_fin:
      dia_txt = mapa_dias.get(curr_date.weekday(), '')

      # Filtrar clases que corresponden a este día de la semana
      clases_dia = df_oferta_confirmada[df_oferta_confirmada['DÍA'] == dia_txt]

      for _, row in clases_dia.iterrows():
        registros_diarios.append({
            'ESPACIO / SALÓN': row['ESPACIO / SALÓN'],
            'FECHA': curr_date.strftime('%Y-%m-%d'),
            'MES': curr_date.strftime('%B').upper(),
            'DÍA NUM': curr_date.day,
            'DÍA': dia_txt,
            'HORA INICIO (24H)': int(row['HORA INICIO (24H)']),
            'HORA FIN (24H)': int(row['HORA FIN (24H)']),
            'ASIGNATURA': row['ASIGNATURA'],
            'DOCENTE': row['DOCENTE'],
        })

      curr_date += datetime.timedelta(days=1)

    df_semestre_completo = pd.DataFrame(registros_diarios)
    self.db.guardar_carga_semestral(df_semestre_completo)