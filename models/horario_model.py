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

  def _asegurar_columnas_extra(self, conn):
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(bloques)')
    cols = [column[1] for column in cursor.fetchall()]
    if 'fecha_especifica' not in cols:
      cursor.execute(
          'ALTER TABLE bloques ADD COLUMN fecha_especifica TEXT DEFAULT ""'
      )
    if 'motivo' not in cols:
      cursor.execute('ALTER TABLE bloques ADD COLUMN motivo TEXT DEFAULT ""')
    conn.commit()

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

      grid_rows = []
      curr_r = room_idx + 2
      while curr_r < len(df_raw):
        row_val = df_raw.iloc[curr_r]
        if (
            pd.isna(row_val[0])
            or not str(row_val[0]).strip().replace('.0', '').isdigit()
        ):
          break
        hora = int(float(str(row_val[0]).strip()))
        grid_rows.append((hora, row_val[1 : 1 + len(dias)].values))
        curr_r += 1

      for col_idx, dia in enumerate(dias):
        i = 0
        while i < len(grid_rows):
          hora_start, vals = grid_rows[i]
          cell = vals[col_idx]
          txt = str(cell).strip() if pd.notna(cell) else ''

          if txt == '' or txt.lower() == 'nan':
            j = i + 1
            while j < len(grid_rows):
              next_cell = grid_rows[j][1][col_idx]
              next_txt = str(next_cell).strip() if pd.notna(next_cell) else ''
              if next_txt != '' and next_txt.lower() != 'nan':
                break
              j += 1

            hora_end = grid_rows[j - 1][0] + 1 if j > i else hora_start + 1
            records_bloques.append({
                'espacio': target_room,
                'dia': dia,
                'hora_inicio': hora_start,
                'hora_fin': hora_end,
                'duracion_horas': hora_end - hora_start,
                'franja_horaria': f'{hora_start}:00 - {hora_end}:00',
                'asignatura': '🟩 LIBRE',
                'docente': 'Disponible',
                'estado': 'LIBRE',
                'fecha_especifica': '',
                'motivo': '',
            })
            i = j
          else:
            j = i + 1
            while j < len(grid_rows):
              next_cell = grid_rows[j][1][col_idx]
              next_txt = str(next_cell).strip() if pd.notna(next_cell) else ''
              if (
                  next_txt == ''
                  or next_txt.lower() == 'nan'
                  or next_txt == txt
              ):
                j += 1
              else:
                break

            hora_end = grid_rows[j - 1][0] + 1 if j > i else hora_start + 1
            lines = [l.strip() for l in txt.split('\n') if l.strip()]
            asig = lines[0] if len(lines) > 0 else 'Sin Asignatura'
            doc = lines[1] if len(lines) > 1 else 'Por definir'

            records_bloques.append({
                'espacio': target_room,
                'dia': dia,
                'hora_inicio': hora_start,
                'hora_fin': hora_end,
                'duracion_horas': hora_end - hora_start,
                'franja_horaria': f'{hora_start}:00 - {hora_end}:00',
                'asignatura': asig,
                'docente': doc,
                'estado': 'OCUPADO',
                'fecha_especifica': '',
                'motivo': '',
            })
            i = j

    df_clean = pd.DataFrame(records_bloques)
    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    conn = sqlite3.connect(self.db_path)
    df_clean.to_sql('bloques', conn, if_exists='replace', index=False)
    self._asegurar_columnas_extra(conn)
    conn.close()
    return len(df_clean[df_clean['estado'] == 'OCUPADO'])

  def obtener_bloques(self):
    if not os.path.exists(self.db_path):
      if os.path.exists(self.excel_path):
        self.procesar_excel_a_db()
      else:
        return pd.DataFrame()

    conn = sqlite3.connect(self.db_path)
    self._asegurar_columnas_extra(conn)
    df = pd.read_sql('SELECT rowid as id, * FROM bloques', conn)
    conn.close()
    return df

  def agregar_evento(
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
    conn = sqlite3.connect(self.db_path)
    self._asegurar_columnas_extra(conn)
    cursor = conn.cursor()

    duracion = hora_fin - hora_inicio
    franja = f'{hora_inicio}:00 - {hora_fin}:00'

    cursor.execute(
        """
            INSERT INTO bloques (espacio, dia, hora_inicio, hora_fin, duracion_horas, franja_horaria, asignatura, docente, estado, fecha_especifica, motivo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OCUPADO', ?, ?)
        """,
        (
            espacio,
            dia,
            hora_inicio,
            hora_fin,
            duracion,
            franja,
            asignatura,
            docente,
            fecha_especifica,
            motivo,
        ),
    )
    conn.commit()
    conn.close()

  def eliminar_evento(self, record_id):
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bloques WHERE rowid = ?', (record_id,))
    conn.commit()
    conn.close()