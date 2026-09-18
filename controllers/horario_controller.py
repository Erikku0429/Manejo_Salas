import datetime
import io
import openpyxl
import pandas as pd


class HorarioController:

  def __init__(self, db_model):
    self.db = db_model

  def intentar_convertir_matriz_raw(self, uploaded_file):
    """Intenta interpretar un Excel en formato matriz/cuadrícula de Coordinación

    y lo convierte en un DataFrame estructurado equivalente a
    BD_Calendario_Semestre.
    """
    SALONES_OBJETIVO = [
        "E105 (SALA CAD)",
        "B222 (SALA COMPUTADORES)",
        "B222 (SALÓN POSGRADOS)",
    ]

    try:
      # Leer la primera pestaña sin encabezados
      df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)
      bloques_semanales = []

      for target_room in SALONES_OBJETIVO:
        room_idx = -1
        for idx, r in df_raw.iterrows():
          if pd.notna(r[1]) and target_room.upper() in str(r[1]).upper():
            room_idx = idx
            break

        if room_idx == -1:
          continue

        header_row = df_raw.iloc[room_idx + 1]
        dias = [
            str(c).strip().upper()
            for c in header_row.values[1:]
            if pd.notna(c)
        ]

        grid_rows = []
        curr_r = room_idx + 2
        while curr_r < len(df_raw):
          row_val = df_raw.iloc[curr_r]
          if pd.isna(row_val[0]) or not str(
              row_val[0]
          ).strip().replace(".0", "").isdigit():
            break
          hora = int(float(str(row_val[0]).strip()))
          grid_rows.append((hora, row_val[1 : 1 + len(dias)].values))
          curr_r += 1

        for col_idx, dia in enumerate(dias):
          i = 0
          while i < len(grid_rows):
            hora_start, vals = grid_rows[i]
            cell = vals[col_idx]
            txt = str(cell).strip() if pd.notna(cell) else ""

            if txt != "" and txt.lower() != "nan":
              j = i + 1
              bloque_texto = [txt]

              while j < len(grid_rows):
                next_cell = grid_rows[j][1][col_idx]
                next_txt = (
                    str(next_cell).strip() if pd.notna(next_cell) else ""
                )
                if next_txt != "" and next_txt.lower() != "nan":
                  if next_txt == txt or len(bloque_texto) < 2:
                    bloque_texto.append(next_txt)
                    j += 1
                  else:
                    break
                else:
                  break

              hora_end = grid_rows[j - 1][0] + 1
              if hora_end > 19:
                hora_end = 19

              lines = [
                  l.strip().upper() for l in txt.split("\n") if l.strip()
              ]
              asig = lines[0] if len(lines) > 0 else "SIN ASIGNATURA"
              doc = (
                  lines[1]
                  if len(lines) > 1
                  else (
                      " ".join(bloque_texto[1:])
                      .replace("\n", " ")
                      .strip()
                      .upper()
                      if len(bloque_texto) > 1
                      else "POR DEFINIR"
                  )
              )

              bloques_semanales.append({
                  "espacio": target_room.upper(),
                  "dia": dia.upper(),
                  "hora_inicio": hora_start,
                  "hora_fin": hora_end,
                  "asignatura": asig,
                  "docente": doc,
              })
              i = j
            else:
              i += 1

      if not bloques_semanales:
        return None

      # Convertir los bloques únicos a DataFrame base
      df_unicas = pd.DataFrame(bloques_semanales)
      df_unicas.rename(
          columns={
              "espacio": "ESPACIO / SALÓN",
              "dia": "DÍA",
              "hora_inicio": "HORA INICIO (24H)",
              "hora_fin": "HORA FIN (24H)",
              "asignatura": "ASIGNATURA",
              "docente": "DOCENTE",
          },
          inplace=True,
      )

      return df_unicas

    except Exception:
      return None

  def validar_y_procesar_excel(self, uploaded_file):
    """Procesa y valida el archivo subido.

    Intenta primero la lectura directa y, si falla, ejecuta la conversión
    automática del formato cuadrícula de Coordinación.
    """
    xls = pd.ExcelFile(uploaded_file)

    # 1. Si ya incluye la pestaña estructurada
    if "BD_Calendario_Semestre" in xls.sheet_names:
      df = pd.read_excel(xls, sheet_name="BD_Calendario_Semestre")
      cols_requeridas = [
          "ESPACIO / SALÓN",
          "DÍA",
          "HORA INICIO (24H)",
          "HORA FIN (24H)",
          "ASIGNATURA",
          "DOCENTE",
      ]
      faltantes = [c for c in cols_requeridas if c not in df.columns]
      if faltantes:
        raise ValueError(f"COLUMNAS_MISSING:{', '.join(faltantes)}")

      # Eliminar duplicados semanales
      df_unicas = df[cols_requeridas].drop_duplicates()
      return df_unicas

    # 2. Si no tiene la pestaña, intentar conversión automática desde matriz
    df_convertido = self.intentar_convertir_matriz_raw(uploaded_file)

    if df_convertido is not None and not df_convertido.empty:
      return df_convertido

    # 3. Si ambos métodos fallan, notificar incompatibilidad de formato
    raise ValueError("FORMATO_INCOMPATIBLE")

  def validar_rango_laboral(self, df_editado):
    errores = []
    for idx, row in df_editado.iterrows():
      ini = int(row["HORA INICIO (24H)"])
      fin = int(row["HORA FIN (24H)"])
      if ini < 7 or fin > 19 or ini >= fin:
        errores.append(idx)
    return errores

  def proyectar_y_guardar_semestre(self, df_unicas, f_inicio, f_fin):
    MAPA_DIAS = {
        0: "LUNES",
        1: "MARTES",
        2: "MIÉRCOLES",
        3: "JUEVES",
        4: "VIERNES",
        5: "SÁBADO",
        6: "DOMINGO",
    }
    registros_proyectados = []

    curr_date = f_inicio
    while curr_date <= f_fin:
      dia_str = MAPA_DIAS.get(curr_date.weekday(), "")
      clases_dia = df_unicas[df_unicas["DÍA"].str.upper() == dia_str]

      for _, row in clases_dia.iterrows():
        registros_proyectados.append({
            "espacio": row["ESPACIO / SALÓN"],
            "fecha": curr_date.strftime("%Y-%m-%d"),
            "mes": curr_date.strftime("%B").upper(),
            "dia_num": curr_date.day,
            "dia": dia_str,
            "hora_inicio": int(row["HORA INICIO (24H)"]),
            "hora_fin": int(row["HORA FIN (24H)"]),
            "asignatura": row["ASIGNATURA"],
            "docente": row["DOCENTE"],
            "tipo_evento": "clase",
            "observacion": "",
        })

      curr_date += datetime.timedelta(days=1)

    df_final = pd.DataFrame(registros_proyectados)
    self.db.reemplazar_horarios_semestre(df_final, f_inicio, f_fin)