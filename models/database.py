import os
import sqlite3
import sys
import pandas as pd


def obtener_ruta_persistente_db(nombre_db="horarios.db"):
  """Garantiza la ruta física portable al lado del ejecutable o script."""
  if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
  else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
  return os.path.join(base_dir, nombre_db)


class DatabaseModel:

  def __init__(self, db_filename="horarios.db"):
    self.db_path = obtener_ruta_persistente_db(db_filename)
    self.init_db()

  def get_connection(self):
    return sqlite3.connect(self.db_path, timeout=10)

  def init_db(self):
    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("PRAGMA journal_mode=WAL;")

      # Tabla principal de horarios
      cursor.execute("""
                CREATE TABLE IF NOT EXISTS horarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    espacio TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    mes TEXT NOT NULL,
                    dia_num INTEGER NOT NULL,
                    dia TEXT NOT NULL,
                    hora_inicio INTEGER NOT NULL,
                    hora_fin INTEGER NOT NULL,
                    asignatura TEXT NOT NULL,
                    docente TEXT NOT NULL,
                    tipo_evento TEXT DEFAULT 'REGULAR',
                    observacion TEXT
                )
            """)

      # Tabla de configuración y vigencia del semestre
      cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_semestre (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    fecha_inicio TEXT NOT NULL,
                    fecha_fin TEXT NOT NULL,
                    fecha_cargue TEXT NOT NULL
                )
            """)
      conn.commit()

  def guardar_carga_semestral(
      self, df_confirmado, fecha_inicio_str, fecha_fin_str, reemplazar=True
  ):
    """Guarda los horarios y registra el periodo de vigencia del semestre."""
    import datetime

    with self.get_connection() as conn:
      cursor = conn.cursor()
      if reemplazar:
        cursor.execute("DELETE FROM horarios WHERE tipo_evento = 'REGULAR'")

      registros = []
      for _, row in df_confirmado.iterrows():
        registros.append((
            str(row["ESPACIO / SALÓN"]).strip().upper(),
            str(row["FECHA"]).strip(),
            str(row["MES"]).strip().upper(),
            int(row["DÍA NUM"]),
            str(row["DÍA"]).strip().upper(),
            int(row["HORA INICIO (24H)"]),
            int(row["HORA FIN (24H)"]),
            str(row["ASIGNATURA"]).strip().upper(),
            str(row["DOCENTE"]).strip().upper(),
        ))

      cursor.executemany(
          """
                INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'REGULAR')
            """,
          registros,
      )

      # Actualizar metadatos de vigencia del semestre
      fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
      cursor.execute(
          """
                INSERT OR REPLACE INTO config_semestre (id, fecha_inicio, fecha_fin, fecha_cargue)
                VALUES (1, ?, ?, ?)
            """,
          (fecha_inicio_str, fecha_fin_str, fecha_hoy),
      )

      conn.commit()

  def obtener_vigencia_semestre(self):
    """Verifica si la base de datos contiene un semestre vigente."""
    import datetime

    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          "SELECT fecha_inicio, fecha_fin, fecha_cargue FROM config_semestre"
          " WHERE id = 1"
      )
      row = cursor.fetchone()

    if not row:
      return False, "No hay ningún semestre cargado en el sistema.", None, None

    f_inicio_str, f_fin_str, _ = row
    today = datetime.date.today()
    f_fin_date = datetime.datetime.strptime(f_fin_str, "%Y-%m-%d").date()

    if today > f_fin_date:
      return (
          False,
          (
              f"El semestre guardado finalizó el {f_fin_str}. Se requiere"
              " realizar un nuevo cargue semestral."
          ),
          f_inicio_str,
          f_fin_str,
      )

    return (
        True,
        f"Semestre vigente (Del {f_inicio_str} al {f_fin_str}).",
        f_inicio_str,
        f_fin_str,
    )

  def obtener_todos_los_horarios(self):
    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("""
                SELECT id, espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, 
                       asignatura, docente, tipo_evento, observacion 
                FROM horarios 
                ORDER BY fecha, hora_inicio
            """)
      rows = cursor.fetchall()

    columns = [
        "id",
        "espacio",
        "fecha",
        "mes",
        "dia_num",
        "dia",
        "hora_inicio",
        "hora_fin",
        "asignatura",
        "docente",
        "tipo_evento",
        "observacion",
    ]
    return pd.DataFrame(rows, columns=columns)

  def agregar_evento_especial(
      self,
      espacio,
      fecha,
      hora_inicio,
      hora_fin,
      asignatura,
      docente,
      observacion="",
  ):
    import datetime

    fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
    dias_esp = {
        0: "LUNES",
        1: "MARTES",
        2: "MIÉRCOLES",
        3: "JUEVES",
        4: "VIERNES",
        5: "SÁBADO",
        6: "DOMINGO",
    }
    dia_str = dias_esp[fecha_dt.weekday()]
    meses_esp = {
        1: "ENERO",
        2: "FEBRERO",
        3: "MARZO",
        4: "ABRIL",
        5: "MAYO",
        6: "JUNIO",
        7: "JULIO",
        8: "AGOSTO",
        9: "SEPTIEMBRE",
        10: "OCTUBRE",
        11: "NOVIEMBRE",
        12: "DICIEMBRE",
    }
    mes_str = meses_esp[fecha_dt.month]

    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'EVENTO', ?)
            """,
          (
              espacio.upper(),
              fecha,
              mes_str,
              fecha_dt.day,
              dia_str,
              hora_inicio,
              hora_fin,
              asignatura.upper(),
              docente.upper(),
              observacion,
          ),
      )
      conn.commit()

  def vaciar_base_de_datos(self):
    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("DELETE FROM horarios")
      cursor.execute("DELETE FROM config_semestre")
      conn.commit()