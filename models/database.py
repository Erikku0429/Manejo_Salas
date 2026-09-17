import os
import sqlite3
import sys
import unicodedata
import pandas as pd


def normalizar_texto(texto):
  if not isinstance(texto, str):
    return ""
  texto = texto.strip().lower()
  nfkd = unicodedata.normalize("NFKD", texto)
  return "".join([c for c in nfkd if not unicodedata.combining(c)])


def obtener_ruta_persistente_db(nombre_db="horarios.db"):
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
                    tipo_evento TEXT DEFAULT 'regular',
                    observacion TEXT
                )
            """)

      cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_semestre (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    fecha_inicio TEXT NOT NULL,
                    fecha_fin TEXT NOT NULL,
                    fecha_cargue TEXT NOT NULL
                )
            """)
      conn.commit()

    # Ejecutar siempre la limpieza de eventos caducados al iniciar
    self.limpiar_eventos_expirados()

  def limpiar_eventos_expirados(self):
    """Elimina automáticamente de la BD los eventos puntuales cuya fecha sea menor a HOY."""
    import datetime

    fecha_hoy_str = datetime.date.today().strftime("%Y-%m-%d")
    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          "DELETE FROM horarios WHERE tipo_evento = 'evento' AND fecha < ?",
          (fecha_hoy_str,),
      )
      conn.commit()

  def guardar_carga_semestral(
      self, df_confirmado, fecha_inicio_str, fecha_fin_str, reemplazar=True
  ):
    import datetime

    with self.get_connection() as conn:
      cursor = conn.cursor()
      if reemplazar:
        cursor.execute("DELETE FROM horarios WHERE tipo_evento = 'regular'")

      registros = []
      for _, row in df_confirmado.iterrows():
        registros.append((
            normalizar_texto(str(row["ESPACIO / SALÓN"])),
            str(row["FECHA"]).strip(),
            normalizar_texto(str(row["MES"])),
            int(row["DÍA NUM"]),
            normalizar_texto(str(row["DÍA"])),
            int(row["HORA INICIO (24H)"]),
            int(row["HORA FIN (24H)"]),
            normalizar_texto(str(row["ASIGNATURA"])),
            normalizar_texto(str(row["DOCENTE"])),
        ))

      cursor.executemany(
          """
                INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'regular')
            """,
          registros,
      )

      fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
      cursor.execute(
          """
                INSERT OR REPLACE INTO config_semestre (id, fecha_inicio, fecha_fin, fecha_cargue)
                VALUES (1, ?, ?, ?)
            """,
          (fecha_inicio_str, fecha_fin_str, fecha_hoy),
      )
      conn.commit()

  def verificar_conflicto_horario(self, espacio, fecha_str, h_inicio, h_fin):
    """Verifica si en esa fecha, espacio y franja horaria existe alguna clase o evento."""
    espacio_norm = normalizar_texto(espacio)
    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          """
                SELECT espacio, asignatura, docente, hora_inicio, hora_fin, tipo_evento, observacion
                FROM horarios
                WHERE espacio = ? AND fecha = ?
                AND NOT (hora_fin <= ? OR hora_inicio >= ?)
            """,
          (espacio_norm, fecha_str, h_inicio, h_fin),
      )
      rows = cursor.fetchall()
    return rows

  def obtener_vigencia_semestre(self):
    import datetime

    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          "SELECT fecha_inicio, fecha_fin FROM config_semestre WHERE id = 1"
      )
      row = cursor.fetchone()

    if not row:
      return False, "No hay ningún semestre cargado en el sistema.", None, None

    f_inicio_str, f_fin_str = row
    today = datetime.date.today()
    f_fin_date = datetime.datetime.strptime(f_fin_str, "%Y-%m-%d").date()

    if today > f_fin_date:
      return (
          False,
          f"El semestre guardado finalizó el {f_fin_str}. Se requiere un nuevo"
          " cargue semestral.",
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
    self.limpiar_eventos_expirados()
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
        0: "lunes",
        1: "martes",
        2: "miercoles",
        3: "jueves",
        4: "viernes",
        5: "sabado",
        6: "domingo",
    }
    dia_str = dias_esp[fecha_dt.weekday()]
    meses_esp = {
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
    mes_str = meses_esp[fecha_dt.month]

    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'evento', ?)
            """,
          (
              normalizar_texto(espacio),
              fecha,
              mes_str,
              fecha_dt.day,
              dia_str,
              hora_inicio,
              hora_fin,
              normalizar_texto(asignatura),
              normalizar_texto(docente),
              normalizar_texto(observacion),
          ),
      )
      conn.commit()

  def vaciar_base_de_datos(self):
    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("DELETE FROM horarios")
      cursor.execute("DELETE FROM config_semestre")
      conn.commit()