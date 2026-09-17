import os
import sys
import sqlite3
import pandas as pd

def obtener_ruta_persistente_db(nombre_db="horarios.db"):
    """
    Garantiza que la base de datos SQLite se guarde en la carpeta física
    donde se encuentra el archivo .exe (o el ejecutable), evitando que se
    cree en la carpeta temporal que borra PyInstaller al cerrarse.
    """
    if getattr(sys, 'frozen', False):
        # Si el programa está ejecutándose como un ejecutable (.exe empaquetado)
        base_dir = os.path.dirname(sys.executable)
    else:
        # Si se está ejecutando desde el código fuente (.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_dir, nombre_db)


class DatabaseModel:
    def __init__(self, db_filename="horarios.db"):
        self.db_path = obtener_ruta_persistente_db(db_filename)
        self.init_db()

    def get_connection(self):
        # Usa timeout largo y isolation_level para evitar bloqueos por concurrencia
        return sqlite3.connect(self.db_path, timeout=10)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Habilitar modo WAL para escritura/lectura ultrarrápida sin bloqueos
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
                    tipo_evento TEXT DEFAULT 'REGULAR',
                    observacion TEXT
                )
            """)
            conn.commit()

    def guardar_carga_semestral(self, df_confirmado, reemplazar=True):
        """Guarda y asegura el commit físico en disco de la carga del semestre."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if reemplazar:
                cursor.execute("DELETE FROM horarios WHERE tipo_evento = 'REGULAR'")

            registros = []
            for _, row in df_confirmado.iterrows():
                registros.append((
                    str(row['ESPACIO / SALÓN']).strip().upper(),
                    str(row['FECHA']).strip(),
                    str(row['MES']).strip().upper(),
                    int(row['DÍA NUM']),
                    str(row['DÍA']).strip().upper(),
                    int(row['HORA INICIO (24H)']),
                    int(row['HORA FIN (24H)']),
                    str(row['ASIGNATURA']).strip().upper(),
                    str(row['DOCENTE']).strip().upper()
                ))

            cursor.executemany("""
                INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'REGULAR')
            """, registros)
            
            # Commit explícito para asegurar persistencia en disco
            conn.commit()

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

        columns = ['id', 'espacio', 'fecha', 'mes', 'dia_num', 'dia', 'hora_inicio', 
                   'hora_fin', 'asignatura', 'docente', 'tipo_evento', 'observacion']
        return pd.DataFrame(rows, columns=columns)

    def agregar_evento_especial(self, espacio, fecha, hora_inicio, hora_fin, asignatura, docente, observacion=""):
        import datetime
        fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
        dias_esp = {0: "LUNES", 1: "MARTES", 2: "MIÉRCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SÁBADO", 6: "DOMINGO"}
        dia_str = dias_esp[fecha_dt.weekday()]
        mes_str = fecha_dt.strftime("%B").upper()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'EVENTO', ?)
            """, (espacio.upper(), fecha, mes_str, fecha_dt.day, dia_str, hora_inicio, hora_fin, asignatura.upper(), docente.upper(), observacion))
            conn.commit()