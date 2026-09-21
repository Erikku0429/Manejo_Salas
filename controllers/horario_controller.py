import pandas as pd
from models.database import (
    obtener_todas_las_aulas,
    obtener_horario_por_aula_bd,
    obtener_eventos_por_aula_bd,
    reemplazar_matriz_horarios,
    registrar_evento_bd
)

def listar_aulas():
    """Retorna las aulas disponibles."""
    return obtener_todas_las_aulas()

def consultar_horario(aula):
    """Retorna el DataFrame con el horario del aula seleccionada."""
    return obtener_horario_por_aula_bd(aula)

def consultar_eventos(aula):
    """Retorna el DataFrame con los eventos del aula seleccionada."""
    return obtener_eventos_por_aula_bd(aula)

def procesar_excel_a_bd(uploaded_file):
    """Procesa el archivo Excel y reemplaza la información en la base de datos."""
    df = pd.read_excel(uploaded_file)
    
    # Mapeo de columnas según el formato de la matriz
    registros = []
    for _, fila in df.iterrows():
        aula = str(fila.get("AULA", "")).strip()
        dia = str(fila.get("DIA", "")).strip()
        bloque = str(fila.get("HORA", "")).strip()
        asignatura = str(fila.get("ASIGNATURA", "")).strip()
        docente = str(fila.get("DOCENTE", "")).strip()
        grupo = str(fila.get("GRUPO", "")).strip()
        
        if aula and dia:
            registros.append((aula, dia, bloque, asignatura, docente, grupo))
            
    if registros:
        reemplazar_matriz_horarios(registros)
        return True
    return False

def guardar_nuevo_evento(aula, fecha, hora_inicio, hora_fin, nombre, descripcion):
    """Valida y guarda un nuevo evento en la base de datos."""
    if not nombre:
        return False, "El nombre del evento es obligatorio."
    
    registrar_evento_bd(
        str(aula),
        str(fecha),
        str(hora_inicio),
        str(hora_fin),
        str(nombre).strip(),
        str(descripcion).strip()
    )
    return True, "Evento registrado con éxito."