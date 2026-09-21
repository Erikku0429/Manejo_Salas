import sqlite3
import datetime
import pandas as pd

class DatabaseModel:
    def __init__(self, db_name="horarios.db"):
        self.db_name = db_name
        self.crear_tablas()

    def crear_tablas(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabla de horarios y eventos
        cursor.execute('''
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
        ''')
        
        # Tabla de vigencia del semestre
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vigencia_semestre (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_inicio TEXT,
                fecha_fin TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def obtener_todos_los_horarios(self):
        conn = sqlite3.connect(self.db_name)
        df = pd.read_sql_query("SELECT * FROM horarios", conn)
        conn.close()
        return df

    # -------------------------------------------------------------------------
    # NUEVOS MÉTODOS PARA ELIMINAR Y ACTUALIZAR
    # -------------------------------------------------------------------------
    def eliminar_horario_por_id(self, record_id):
        """Elimina un evento o clase específica usando su ID."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM horarios WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()

    def actualizar_horario_por_id(self, record_id, asignatura, docente, observacion=""):
        """Actualiza los datos de una clase o evento existente."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE horarios 
            SET asignatura = ?, docente = ?, observacion = ?
            WHERE id = ?
        ''', (asignatura, docente, observacion, record_id))
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # RESTO DE MÉTODOS EXISTENTES
    # -------------------------------------------------------------------------
    def vaciar_base_de_datos(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM horarios")
        cursor.execute("DELETE FROM vigencia_semestre")
        conn.commit()
        conn.close()

    def agregar_evento_especial(self, espacio, fecha, h_ini, h_fin, asignatura, docente, observacion=""):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d").date()
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        mes = meses[fecha_dt.month - 1]
        dia_num = fecha_dt.day
        dia = dias[fecha_dt.weekday()]

        cursor.execute('''
            INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'evento', ?)
        ''', (espacio, fecha, mes, dia_num, dia, h_ini, h_fin, asignatura, docente, observacion))
        
        conn.commit()
        conn.close()

    def obtener_vigencia_semestre(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT fecha_inicio, fecha_fin FROM vigencia_semestre ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, "No se han configurado las fechas del semestre.", None, None

        f_ini = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
        f_fin = datetime.datetime.strptime(row[1], "%Y-%m-%d").date()
        hoy = datetime.date.today()

        if f_ini <= hoy <= f_fin:
            return True, "Semestre activo.", f_ini, f_fin
        elif hoy < f_ini:
            return False, f"El semestre aún no inicia (Inicia el {f_ini}).", f_ini, f_fin
        else:
            return False, f"El semestre finalizó el {f_fin}.", f_ini, f_fin

    def verificar_conflicto_horario(self, espacio, fecha, h_ini, h_fin):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, asignatura, docente, hora_inicio, hora_fin, tipo_evento 
            FROM horarios 
            WHERE espacio = ? AND fecha = ? AND (
                (hora_inicio < ? AND hora_fin > ?)
            )
        ''', (espacio, fecha, h_fin, h_ini))
        conflictos = cursor.fetchall()
        conn.close()
        return conflictos