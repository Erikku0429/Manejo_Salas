import datetime
import sqlite3
import pandas as pd
import streamlit as st

# Manejo flexible de imports para Turso / LibSQL
HAS_TURSO = False
libsql = None

try:
  import libsql_experimental as libsql

  HAS_TURSO = True
except ImportError:
  try:
    import libsql_client as libsql

    HAS_TURSO = True
  except ImportError:
    HAS_TURSO = False


class DatabaseModel:

  def __init__(self, db_name="horarios.db"):
    self.db_name = db_name

    # Obtenemos URL y Token de Streamlit Secrets si existen
    self.turso_url = st.secrets.get("turso", {}).get("url", None)
    self.turso_token = st.secrets.get("turso", {}).get("auth_token", None)

    self.crear_tablas()

  def _obtener_conexion(self):
    """Establece conexión a Turso en la nube si hay credenciales, de lo contrario a SQLite local."""
    if HAS_TURSO and self.turso_url and self.turso_token:
      return libsql.connect(database=self.turso_url, auth_token=self.turso_token)
    else:
      return sqlite3.connect(self.db_name)

  def crear_tablas(self):
    conn = self._obtener_conexion()
    cursor = conn.cursor()

    # Tabla de horarios y eventos
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS horarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                espacio TEXT,
                fecha TEXT,
                mes TEXT,
                dia_num INTEGER,
                dia TEXT,
                hora_inicio INTEGER,
                hora_fin INTEGER,
                asignatura TEXT,
                docente TEXT,
                tipo_evento TEXT DEFAULT 'clase',
                observacion TEXT DEFAULT ''
            )
        """)

    # Tabla de vigencia del semestre
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS vigencia_semestre (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_inicio TEXT,
                fecha_fin TEXT
            )
        """)

    conn.commit()
    conn.close()

  def obtener_todos_los_horarios(self):
    conn = self._obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM horarios")
    rows = cursor.fetchall()

    # Obtener los nombres de las columnas
    columnas = [description[0] for description in cursor.description]
    conn.close()

    if not rows:
      return pd.DataFrame(columns=columnas)

    return pd.DataFrame(rows, columns=columnas)

  def eliminar_horario_por_id(self, record_id):
    """Elimina un evento o clase específica usando su ID."""
    conn = self._obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM horarios WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

  def actualizar_horario_por_id(
      self, record_id, asignatura, docente, observacion=""
  ):
    """Actualiza los datos de una clase o evento existente."""
    conn = self._obtener_conexion()
    cursor = conn.cursor()
    cursor.execute(
        """
            UPDATE horarios 
            SET asignatura = ?, docente = ?, observacion = ?
            WHERE id = ?
        """,
        (asignatura, docente, observacion, record_id),
    )
    conn.commit()
    conn.close()

  def vaciar_base_de_datos(self):
    conn = self._obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM horarios")
    cursor.execute("DELETE FROM vigencia_semestre")
    conn.commit()
    conn.close()

  def agregar_evento_especial(
      self,
      espacio,
      fecha,
      h_ini,
      h_fin,
      asignatura,
      docente,
      observacion="",
  ):
    conn = self._obtener_conexion()
    cursor = conn.cursor()

    fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d").date()
    meses = [
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    dias = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]

    mes = meses[fecha_dt.month - 1]
    dia_num = fecha_dt.day
    dia = dias[fecha_dt.weekday()]

    cursor.execute(
        """
            INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'evento', ?)
        """,
        (
            espacio,
            fecha,
            mes,
            dia_num,
            dia,
            h_ini,
            h_fin,
            asignatura,
            docente,
            observacion,
        ),
    )

    conn.commit()
    conn.close()

  def obtener_vigencia_semestre(self):
    conn = self._obtener_conexion()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT fecha_inicio, fecha_fin FROM vigencia_semestre ORDER BY id DESC"
        " LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
      return (
          False,
          "No se han configurado las fechas del semestre.",
          None,
          None,
      )

    f_ini = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
    f_fin = datetime.datetime.strptime(row[1], "%Y-%m-%d").date()
    hoy = datetime.date.today()

    if f_ini <= hoy <= f_fin:
      return True, "Semestre activo.", f_ini, f_fin
    elif hoy < f_ini:
      return (
          False,
          f"El semestre aún no inicia (Inicia el {f_ini}).",
          f_ini,
          f_fin,
      )
    else:
      return False, f"El semestre finalizó el {f_fin}.", f_ini, f_fin

  def verificar_conflicto_horario(self, espacio, fecha, h_ini, h_fin):
    conn = self._obtener_conexion()
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT id, asignatura, docente, hora_inicio, hora_fin, tipo_evento 
            FROM horarios 
            WHERE espacio = ? AND fecha = ? AND (
                (hora_inicio < ? AND hora_fin > ?)
            )
        """,
        (espacio, fecha, h_fin, h_ini),
    )
    conflictos = cursor.fetchall()
    conn.close()
    return conflictos