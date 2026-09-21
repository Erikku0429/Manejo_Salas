import sqlite3
import pandas as pd

DB_PATH = "horarios.db"

def obtener_conexion():
    """Retorna una conexión activa a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_bd():
    """Crea la estructura inicial de tablas si no existen."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aula TEXT NOT NULL,
            dia TEXT NOT NULL,
            bloque_horario TEXT NOT NULL,
            asignatura TEXT,
            docente TEXT,
            grupo TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aula TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            nombre_evento TEXT NOT NULL,
            descripcion TEXT
        )
    """)
    conn.commit()
    conn.close()

def obtener_todas_las_aulas():
    """Obtiene la lista única de aulas de forma segura."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT aula FROM horarios ORDER BY aula ASC")
    filas = cursor.fetchall()
    conn.close()
    return [filas[i]["aula"] for i in range(len(filas))]

def obtener_horario_por_aula_bd(aula):
    """Consulta segura de horarios utilizando parámetro tupla ?."""
    conn = obtener_conexion()
    query = """
        SELECT dia, bloque_horario, asignatura, docente, grupo 
        FROM horarios 
        WHERE aula = ? 
        ORDER BY bloque_horario ASC
    """
    df = pd.read_sql_query(query, conn, params=(aula,))
    conn.close()
    return df

def obtener_eventos_por_aula_bd(aula):
    """Consulta segura de eventos especiales utilizando parámetro tupla ?."""
    conn = obtener_conexion()
    query = """
        SELECT fecha, hora_inicio, hora_fin, nombre_evento, descripcion 
        FROM eventos 
        WHERE aula = ? 
        ORDER BY fecha ASC, hora_inicio ASC
    """
    df = pd.read_sql_query(query, conn, params=(aula,))
    conn.close()
    return df

def reemplazar_matriz_horarios(lista_registros):
    """Limpia e inserta la nueva matriz de horarios usando consultas parametrizadas."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM horarios")
    
    query_insert = """
        INSERT INTO horarios (aula, dia, bloque_horario, asignatura, docente, grupo)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    cursor.executemany(query_insert, lista_registros)
    conn.commit()
    conn.close()

def registrar_evento_bd(aula, fecha, hora_inicio, hora_fin, nombre_evento, descripcion):
    """Inserta un evento especial de forma segura."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    query = """
        INSERT INTO eventos (aula, fecha, hora_inicio, hora_fin, nombre_evento, descripcion)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (aula, fecha, hora_inicio, hora_fin, nombre_evento, descripcion))
    conn.commit()
    conn.close()