import datetime
import re
import pandas as pd


class HorarioController:

  def __init__(self, db_model):
    self.db = db_model

  def normalizar_texto(self, texto):
    import unicodedata

    if not isinstance(texto, str):
      return ""
    texto = texto.strip().lower()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

  def procesar_cuadricula_coordinacion(self, file_path_or_bytes):
    """Procesa el archivo Excel extrayendo de forma precisa el nombre de cada aula,

    evitando tomar números de horas o encabezados como nombres de salón.
    """
    xls = pd.ExcelFile(file_path_or_bytes)
    registros = []

    for sheet_name in xls.sheet_names:
      df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
      filas, columnas = df_raw.shape

      i = 0
      nombre_salon_actual = None

      while i < filas:
        row_vals = [
            str(x).strip() for x in df_raw.iloc[i].dropna() if str(x).strip()
        ]

        # 1. Identificar si la fila actual define la cabecera con los días de la semana
        dias_detectados = {}
        for col_idx in range(columnas):
          val_celda = df_raw.iloc[i, col_idx]
          val_norm = self.normalizar_texto(str(val_celda))
          if val_norm in [
              "lunes",
              "martes",
              "miercoles",
              "jueves",
              "viernes",
              "sabado",
              "domingo",
          ]:
            dias_detectados[col_idx] = str(val_celda).strip().upper()

        # Si encontramos una fila con 3 o más días de la semana
        if len(dias_detectados) >= 3:
          # Buscar el nombre real del salón en las filas anteriores
          posible_salon = ""
          for k in range(max(0, i - 4), i):
            vals_prev = [
                str(x).strip()
                for x in df_raw.iloc[k].dropna()
                if str(x).strip()
            ]
            cand = " ".join(vals_prev).upper()

            # Evitar tomar filas numéricas (ej. '19', '20') o palabras clave reservadas
            if cand and not cand.isdigit() and len(cand) > 2:
              if not any(
                  term in cand
                  for term in [
                      "HORA",
                      "LUNES",
                      "MARTES",
                      "MIÉRCOLES",
                      "JUEVES",
                      "VIERNES",
                      "SÁBADO",
                      "DÍA",
                      "SEMANA",
                  ]
              ):
                posible_salon = cand

          if posible_salon:
            nombre_salon_actual = posible_salon
          elif not nombre_salon_actual:
            nombre_salon_actual = "AULA GENERAL"

          # 2. Recorrer las filas de horas y clases para esta tabla de días
          j = i + 1
          while j < filas:
            col_hora_val = df_raw.iloc[j, 0]
            if pd.isna(col_hora_val) and columnas > 1:
              col_hora_val = df_raw.iloc[j, 1]

            row_text = " ".join(
                [str(x) for x in df_raw.iloc[j].dropna().values]
            ).upper()

            # Romper si llegamos a otra cabecera de días o de nuevo salón
            if (
                sum(
                    1
                    for d in [
                        "LUNES",
                        "MARTES",
                        "MIÉRCOLES",
                        "JUEVES",
                        "VIERNES",
                    ]
                    if d in row_text
                )
                >= 2
            ):
              i = j - 1
              break

            # Extraer número de hora (7 a 19)
            hora_ini = None
            if pd.notna(col_hora_val):
              match_hora = re.search(r"\b(\d{1,2})\b", str(col_hora_val))
              if match_hora:
                val_h = int(match_hora.group(1))
                if 7 <= val_h <= 19:
                  hora_ini = val_h

            if hora_ini is not None:
              hora_fin = hora_ini + 1 if hora_ini < 19 else 19

              for col_idx, dia_nombre in dias_detectados.items():
                celda_contenido = df_raw.iloc[j, col_idx]
                if (
                    pd.notna(celda_contenido)
                    and str(celda_contenido).strip() != ""
                ):
                  texto_clase = str(celda_contenido).strip()

                  # Separar asignatura y docente
                  partes = [
                      p.strip()
                      for p in re.split(r"[\n\r\t]+", texto_clase)
                      if p.strip()
                  ]
                  asig = partes[0].upper() if partes else "ASIGNATURA"
                  docente = (
                      partes[1].upper()
                      if len(partes) > 1
                      else "DOCENTE NO ASIGNADO"
                  )

                  registros.append({
                      "ESPACIO / SALÓN": nombre_salon_actual,
                      "DÍA": dia_nombre,
                      "HORA INICIO (24H)": hora_ini,
                      "HORA FIN (24H)": hora_fin,
                      "ASIGNATURA": asig,
                      "DOCENTE": docente,
                  })
            j += 1
          i = j
        else:
          i += 1

    return pd.DataFrame(registros)

  def validar_y_procesar_excel(self, uploaded_file):
    xls = pd.ExcelFile(uploaded_file)

    if "BD_Calendario_Semestre" in xls.sheet_names:
      df_bd = pd.read_excel(xls, sheet_name="BD_Calendario_Semestre")
      cols_req = [
          "ESPACIO / SALÓN",
          "DÍA",
          "HORA INICIO (24H)",
          "HORA FIN (24H)",
          "ASIGNATURA",
          "DOCENTE",
      ]
      if all(col in df_bd.columns for col in cols_req):
        return df_bd[cols_req].dropna(subset=["ESPACIO / SALÓN", "ASIGNATURA"])

    df_cuadricula = self.procesar_cuadricula_coordinacion(uploaded_file)
    if not df_cuadricula.empty:
      return df_cuadricula

    raise ValueError("El archivo Excel no cumple con los formatos soportados.")

  def validar_rango_laboral(self, df):
    errores = []
    for idx, row in df.iterrows():
      h_ini = int(row["HORA INICIO (24H)"])
      h_fin = int(row["HORA FIN (24H)"])
      if h_ini < 7 or h_fin > 19 or h_fin <= h_ini:
        errores.append(
            f"Fila {idx + 1}: Horario no permitido ({h_ini} a {h_fin})"
        )
    return errores

  def proyectar_y_guardar_semestre(self, df_unicas, f_inicio, f_fin):
    MAPA_DIAS = {
        "LUNES": 0,
        "MARTES": 1,
        "MIÉRCOLES": 2,
        "MIERCOLES": 2,
        "JUEVES": 3,
        "VIERNES": 4,
        "SÁBADO": 5,
        "SABADO": 5,
        "DOMINGO": 6,
    }

    registros_proyectados = []
    num_dias = (f_fin - f_inicio).days + 1

    for i in range(num_dias):
      fecha_curr = f_inicio + datetime.timedelta(days=i)
      dia_num_week = fecha_curr.weekday()

      for _, row in df_unicas.iterrows():
        dia_str = str(row["DÍA"]).upper().strip()
        dia_target_num = MAPA_DIAS.get(dia_str)

        if dia_target_num == dia_num_week:
          registros_proyectados.append({
              "espacio": str(row["ESPACIO / SALÓN"]).upper().strip(),
              "fecha": fecha_curr.strftime("%Y-%m-%d"),
              "mes": fecha_curr.strftime("%B").upper(),
              "dia_num": fecha_curr.day,
              "dia": dia_str,
              "hora_inicio": int(row["HORA INICIO (24H)"]),
              "hora_fin": int(row["HORA FIN (24H)"]),
              "asignatura": str(row["ASIGNATURA"]).upper().strip(),
              "docente": str(row["DOCENTE"]).upper().strip(),
              "tipo_evento": "clase",
              "observacion": "",
          })

    df_final = pd.DataFrame(registros_proyectados)
    self.db.reemplazar_horarios_semestre(df_final, f_inicio, f_fin)
    return len(df_final)