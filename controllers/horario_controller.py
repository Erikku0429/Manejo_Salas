import datetime
import unicodedata
import pandas as pd


def normalizar_texto(texto):
  if not isinstance(texto, str):
    return ""
  texto = texto.strip().lower()
  nfkd = unicodedata.normalize("NFKD", texto)
  return "".join([c for c in nfkd if not unicodedata.combining(c)])


class HorarioController:

  def __init__(self, db_model):
    self.db = db_model

  def validar_y_procesar_excel(self, uploaded_file):
    try:
      xls = pd.ExcelFile(uploaded_file)
    except Exception:
      raise ValueError("El archivo subido no es un libro de Excel válido.")

    if "BD_Calendario_Semestre" not in xls.sheet_names:
      raise ValueError("PESTAÑA_MISSING")

    df = pd.read_excel(uploaded_file, sheet_name="BD_Calendario_Semestre")

    columnas_requeridas = [
        "ESPACIO / SALÓN",
        "DÍA",
        "HORA INICIO (24H)",
        "HORA FIN (24H)",
        "ASIGNATURA",
        "DOCENTE",
    ]
    columnas_faltantes = [
        col for col in columnas_requeridas if col not in df.columns
    ]

    if columnas_faltantes:
      raise ValueError(f"COLUMNAS_MISSING:{', '.join(columnas_faltantes)}")

    if df.empty:
      raise ValueError("El archivo cargado se encuentra totalmente vacío.")

    # Normalización para deduplicación
    df["ESPACIO / SALÓN_norm"] = df["ESPACIO / SALÓN"].apply(normalizar_texto)
    df["DÍA_norm"] = df["DÍA"].apply(normalizar_texto)
    df["ASIGNATURA_norm"] = df["ASIGNATURA"].apply(normalizar_texto)
    df["DOCENTE_norm"] = df["DOCENTE"].apply(normalizar_texto)
    df["HORA INICIO (24H)"] = pd.to_numeric(
        df["HORA INICIO (24H)"], errors="coerce"
    ).fillna(7)
    df["HORA FIN (24H)"] = pd.to_numeric(
        df["HORA FIN (24H)"], errors="coerce"
    ).fillna(9)

    df_unicas = df.drop_duplicates(
        subset=[
            "ESPACIO / SALÓN_norm",
            "DÍA_norm",
            "ASIGNATURA_norm",
            "DOCENTE_norm",
        ]
    ).copy()

    mapa_orden_dias = {
        "lunes": 1,
        "martes": 2,
        "miercoles": 3,
        "jueves": 4,
        "viernes": 5,
        "sabado": 6,
        "domingo": 7,
    }
    df_unicas["_orden_dia"] = (
        df_unicas["DÍA_norm"].map(mapa_orden_dias).fillna(8)
    )
    df_unicas = df_unicas.sort_values(
        by=["ESPACIO / SALÓN_norm", "_orden_dia", "HORA INICIO (24H)"]
    ).drop(columns=["_orden_dia"])

    return df_unicas.reset_index(drop=True)

  def validar_rango_laboral(self, df_editado):
    fuera_de_rango = []
    for idx, row in df_editado.iterrows():
      h_ini = row["HORA INICIO (24H)"]
      h_fin = row["HORA FIN (24H)"]
      if h_ini < 7 or h_fin > 19 or h_ini >= h_fin:
        fuera_de_rango.append({
            "asignatura": str(row["ASIGNATURA"]).upper(),
            "salon": str(row["ESPACIO / SALÓN"]).upper(),
            "dia": str(row["DÍA"]).upper(),
            "inicio": h_ini,
            "fin": h_fin,
        })
    return fuera_de_rango

  def proyectar_y_guardar_semestre(
      self, df_oferta_confirmada, fecha_inicio, fecha_fin
  ):
    mapa_dias = {
        0: "lunes",
        1: "martes",
        2: "miercoles",
        3: "jueves",
        4: "viernes",
        5: "sabado",
        6: "domingo",
    }
    mapa_meses_es = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    registros_diarios = []
    curr_date = fecha_inicio

    while curr_date <= fecha_fin:
      dia_txt = mapa_dias.get(curr_date.weekday(), "")

      for _, row in df_oferta_confirmada.iterrows():
        dia_row_norm = normalizar_texto(str(row["DÍA"]))
        if dia_row_norm == dia_txt:
          registros_diarios.append({
              "ESPACIO / SALÓN": row["ESPACIO / SALÓN"],
              "FECHA": curr_date.strftime("%Y-%m-%d"),
              "MES": mapa_meses_es[curr_date.month],
              "DÍA NUM": curr_date.day,
              "DÍA": dia_txt,
              "HORA INICIO (24H)": int(row["HORA INICIO (24H)"]),
              "HORA FIN (24H)": int(row["HORA FIN (24H)"]),
              "ASIGNATURA": row["ASIGNATURA"],
              "DOCENTE": row["DOCENTE"],
          })

      curr_date += datetime.timedelta(days=1)

    df_semestre_completo = pd.DataFrame(registros_diarios)
    self.db.guardar_carga_semestral(
        df_semestre_completo,
        fecha_inicio.strftime("%Y-%m-%d"),
        fecha_fin.strftime("%Y-%m-%d"),
    )