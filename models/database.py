import sqlite3


class DatabaseModel:

  def __init__(self, db_name='aulas_universitarias.db'):
    self.db_name = db_name
    self.crear_tablas()

  def crear_tablas(self):
    conn = sqlite3.connect(self.db_name)
    cursor = conn.cursor()

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
                tipo_evento TEXT DEFAULT 'clase',
                observacion TEXT DEFAULT ''
            )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS vigencia_semestre (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_inicio TEXT NOT NULL,
                fecha_fin TEXT NOT NULL
            )
        """)

    conn.commit()
    conn.close()

  def obtener_todos_los_horarios(self):
    import pandas as pd

    conn = sqlite3.connect(self.db_name)
    df = pd.read_sql_query("SELECT * FROM horarios", conn)
    conn.close()
    return df

  def vaciar_base_de_datos(self):
    conn = sqlite3.connect(self.db_name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM horarios")
    cursor.execute("DELETE FROM vigencia_semestre")
    conn.commit()
    conn.close()

  def obtener_vigencia_semestre(self):
    import datetime

    conn = sqlite3.connect(self.db_name)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT fecha_inicio, fecha_fin FROM vigencia_semestre ORDER BY id DESC"
        " LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if row:
      f_ini = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
      f_fin = datetime.datetime.strptime(row[1], "%Y-%m-%d").date()
      hoy = datetime.date.today()

      if hoy < f_ini:
        return (
            False,
            f"El semestre aún no ha iniciado. Programado del {f_ini} al {f_fin}",
            f_ini,
            f_fin,
        )
      elif hoy > f_fin:
        return (
            False,
            f"El semestre ha finalizado. Periodo: {f_ini} al {f_fin}",
            f_ini,
            f_fin,
        )
      else:
        return True, f"Semestre activo ({f_ini} al {f_fin})", f_ini, f_fin

    return (
        False,
        "No hay un semestre cargado en el sistema.",
        None,
        None,
    )

  def reemplazar_horarios_semestre(self, df_final, f_inicio, f_fin):
    conn = sqlite3.connect(self.db_name)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM horarios")
    cursor.execute("DELETE FROM vigencia_semestre")

    cursor.execute(
        "INSERT INTO vigencia_semestre (fecha_inicio, fecha_fin) VALUES (?,"
        " ?)",
        (f_inicio.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")),
    )

    for _, row in df_final.iterrows():
      cursor.execute(
          """
            INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
          (
              row["espacio"],
              row["fecha"],
              row["mes"],
              row["dia_num"],
              row["dia"],
              row["hora_inicio"],
              row["hora_fin"],
              row["asignatura"],
              row["docente"],
              row.get("tipo_evento", "clase"),
              row.get("observacion", ""),
          ),
      )

    conn.commit()
    conn.close()

  def verificar_conflicto_horario(self, espacio, fecha, hora_ini, hora_fin):
    conn = sqlite3.connect(self.db_name)
    cursor = conn.cursor()

    cursor.execute(
        """
            SELECT id, asignatura, docente, hora_inicio, hora_fin, tipo_evento
            FROM horarios
            WHERE espacio = ? AND fecha = ? AND hora_inicio < ? AND hora_fin > ?
        """,
        (espacio, fecha, hora_fin, hora_ini),
    )

    conflictos = cursor.fetchall()
    conn.close()
    return conflictos

  def agregar_evento_especial(
      self, espacio, fecha, hora_ini, hora_fin, asignatura, docente, observacion
  ):
    import datetime

    conn = sqlite3.connect(self.db_name)
    cursor = conn.cursor()

    dt_fecha = datetime.datetime.strptime(fecha, "%Y-%m-%d")
    MAPA_DIAS = {
        0: "LUNES",
        1: "MARTES",
        2: "MIÉRCOLES",
        3: "JUEVES",
        4: "VIERNES",
        5: "SÁBADO",
        6: "DOMINGO",
    }
    dia_str = MAPA_DIAS.get(dt_fecha.weekday(), "")

    # Reemplazar o eliminar traslapes directos si existen
    cursor.execute(
        """
            DELETE FROM horarios
            WHERE espacio = ? AND fecha = ? AND hora_inicio < ? AND hora_fin > ?
        """,
        (espacio, fecha, hora_fin, hora_ini),
    )

    cursor.execute(
        """
            INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'evento', ?)
        """,
        (
            espacio,
            fecha,
            dt_fecha.strftime("%B").upper(),
            dt_fecha.day,
            dia_str,
            hora_ini,
            hora_fin,
            asignatura,
            docente,
            observacion,
        ),
    )

    conn.commit()
    conn.close()