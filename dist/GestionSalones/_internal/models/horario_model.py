import os
import sqlite3
import pandas as pd


class HorarioModel:

  def __init__(
      self,
      excel_path=os.path.join(
          'base_datos', 'HORARIOS X SALONES DTE (1).xlsx'
      ),
      db_path=os.path.join('base_datos', 'horarios.db'),
  ):
    self.excel_path = excel_path
    self.db_path = db_path
    self.target_rooms = [
        'E105 (Sala CAD)',
        'B222 (Sala computadores)',
        'B222 (Salón posgrados)',
    ]

  def procesar_excel_a_db(self, file_source=None):
    source = file_source if file_source is not None else self.excel_path

    if isinstance(source, str) and not os.path.exists(source):
      raise FileNotFoundError(f'No se encontró el archivo en {source}')

    df_raw = pd.read_excel(source, sheet_name=0, header=None)
    records_bloques = []

    for target_room in self.target_rooms:
      room_idx = -1
      for idx, r in df_raw.iterrows():
        if pd.notna(r[1]) and target_room in str(r[1]):
          room_idx = idx
          break

      if room_idx == -1:
        continue

      header_row = df_raw.iloc[room_idx + 1]
      dias = [
          str(c).strip().upper() for c in header_row.values[1:] if pd.notna(c)
      ]

      # Extraer clases ocupadas
      classes_by_day = {dia: [] for dia in dias}
      curr_r = room_idx + 2
      while curr_r < len(df_raw):
        row_val = df_raw.iloc[curr_r]
        if (
            pd.isna(row_val[0])
            or not str(row_val[0]).strip().replace('.0', '').isdigit()
        ):
          break
        hora = int(float(str(row_val[0]).strip()))
        for col_idx, dia in enumerate(dias):
          cell = row_val[col_idx + 1]
          if pd.notna(cell) and str(cell).strip() != '':
            txt = str(cell).strip()
            classes_by_day[dia].append((hora, txt))
        curr_r += 1

      # Generar bloques continuos para el día
      for dia, class_list in classes_by_day.items():
        class_list = sorted(class_list, key=lambda x: x[0])
        curr_hora = 7
        schedule_end = 20

        i = 0
        while i < len(class_list):
          start_hora, txt = class_list[i]

          # Franja libre antes de la clase
          if start_hora > curr_hora:
            records_bloques.append({
                'espacio': target_room,
                'dia': dia,
                'hora_inicio': curr_hora,
                'hora_fin': start_hora,
                'duracion_horas': start_hora - curr_hora,
                'franja_horaria': f'{curr_hora}:00 - {start_hora}:00',
                'asignatura': '🟩 LIBRE',
                'docente': 'Disponible',
                'estado': 'LIBRE',
            })
            curr_hora = start_hora

          # Determinar fin de la clase
          next_start = (
              class_list[i + 1][0]
              if i + 1 < len(class_list)
              else schedule_end
          )
          end_hora = next_start
          if (next_start - start_hora) > 4:
            end_hora = min(start_hora + 3, schedule_end)

          lines = [l.strip() for l in txt.split('\n') if l.strip()]
          asig = lines[0] if len(lines) > 0 else 'Sin Asignatura'
          doc = lines[1] if len(lines) > 1 else 'Por definir'

          records_bloques.append({
              'espacio': target_room,
              'dia': dia,
              'hora_inicio': start_hora,
              'hora_fin': end_hora,
              'duracion_horas': end_hora - start_hora,
              'franja_horaria': f'{start_hora}:00 - {end_hora}:00',
              'asignatura': asig,
              'docente': doc,
              'estado': 'OCUPADO',
          })
          curr_hora = end_hora
          i += 1

        if curr_hora < schedule_end:
          records_bloques.append({
              'espacio': target_room,
              'dia': dia,
              'hora_inicio': curr_hora,
              'hora_fin': schedule_end,
              'duracion_horas': schedule_end - curr_hora,
              'franja_horaria': f'{curr_hora}:00 - {schedule_end}:00',
              'asignatura': '🟩 LIBRE',
              'docente': 'Disponible',
              'estado': 'LIBRE',
          })

    df_clean = pd.DataFrame(records_bloques)
    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    conn = sqlite3.connect(self.db_path)
    df_clean.to_sql('bloques', conn, if_exists='replace', index=False)
    conn.close()
    return len(df_clean[df_clean['estado'] == 'OCUPADO'])

  def obtener_bloques(self):
    if not os.path.exists(self.db_path):
      if os.path.exists(self.excel_path):
        self.procesar_excel_a_db()
      else:
        return pd.DataFrame()

    conn = sqlite3.connect(self.db_path)
    df = pd.read_sql('SELECT * FROM bloques', conn)
    conn.close()
    return df