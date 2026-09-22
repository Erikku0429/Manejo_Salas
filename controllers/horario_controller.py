import datetime
import pandas as pd

class HorarioController:
    def __init__(self, db_model):
        self.db = db_model

    def validar_y_procesar_excel(self, uploaded_file):
        """Lee y estandariza la estructura del archivo Excel subido (Soporta Formato BD y Formato Matriz)."""
        xls = pd.ExcelFile(uploaded_file)
        
        # CASO 1: Formato de Base de Datos Directa (pestaña 'BD_Calendario_Semestre')
        if "BD_Calendario_Semestre" in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name="BD_Calendario_Semestre")
            columnas_req = ["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]
            
            for col in columnas_req:
                if col not in df.columns:
                    raise ValueError(f"Falta la columna requerida: {col}")
            return df

        # CASO 2: Formato de Matriz / Cuadrícula Semestral (pestaña principal)
        df_raw = pd.read_excel(xls, sheet_name=0)
        registros = []
        
        # Buscar la fila de encabezados o procesar columnas
        # Se normalizan los nombres de las columnas para detectar el salón, día, horas y materia
        for col in df_raw.columns:
            # Si el DataFrame ya viene con columnas estándar
            pass

        # Si el archivo tiene la estructura matricial común, leemos las columnas requeridas directamente
        cols_directas = [c for c in df_raw.columns if any(k in str(c).upper() for k in ["SALON", "ESPACIO", "AULA", "DIA", "DÍA", "HORA", "ASIGNATURA", "MATERIA"])]
        
        if len(cols_directas) >= 4:
            df_renombrado = df_raw.copy()
            # Mapeo flexible de columnas para garantizar la lectura
            mapeo = {}
            for col in df_raw.columns:
                col_upper = str(col).upper()
                if "SALON" in col_upper or "ESPACIO" in col_upper or "AULA" in col_upper:
                    mapeo[col] = "ESPACIO / SALÓN"
                elif "DIA" in col_upper or "DÍA" in col_upper:
                    mapeo[col] = "DÍA"
                elif "INICIO" in col_upper or "DESDE" in col_upper:
                    mapeo[col] = "HORA INICIO (24H)"
                elif "FIN" in col_upper or "HASTA" in col_upper:
                    mapeo[col] = "HORA FIN (24H)"
                elif "ASIGNATURA" in col_upper or "MATERIA" in col_upper:
                    mapeo[col] = "ASIGNATURA"
                elif "DOCENTE" in col_upper or "PROFESOR" in col_upper:
                    mapeo[col] = "DOCENTE"
            
            df_renombrado = df_renombrado.rename(columns=mapeo)
            
            # Verificar si se mapearon las columnas esenciales
            cols_esenciales = ["ESPACIO / SALÓN", "DÍA", "ASIGNATURA"]
            if all(c in df_renombrado.columns for c in cols_esenciales):
                if "HORA INICIO (24H)" not in df_renombrado.columns:
                    df_renombrado["HORA INICIO (24H)"] = 7
                if "HORA FIN (24H)" not in df_renombrado.columns:
                    df_renombrado["HORA FIN (24H)"] = 9
                if "DOCENTE" not in df_renombrado.columns:
                    df_renombrado["DOCENTE"] = "POR ASIGNAR"
                
                return df_renombrado[["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]].dropna(subset=["ESPACIO / SALÓN", "ASIGNATURA"])

        # Si no se pudo procesar con los mapeos flexibilizados, retornar el DataFrame crudo leído
        if not df_raw.empty:
            return df_raw

        raise ValueError("No se pudieron extraer datos válidos del Excel subido. Verifica el nombre de la pestaña o el formato.")

    def validar_rango_laboral(self, df):
        """Verifica que las clases no estén fuera del rango oficial (07:00 a 19:00)."""
        fuera_de_rango = df[
            (df["HORA INICIO (24H)"] < 7) | 
            (df["HORA FIN (24H)"] > 19) | 
            (df["HORA INICIO (24H)"] >= df["HORA FIN (24H)"])
        ]
        return not fuera_de_rango.empty

    def proyectar_y_guardar_semestre(self, df, fecha_inicio, fecha_fin):
        """Genera todas las fechas individuales del semestre y las guarda en la BD."""
        MAPA_DIAS = {
            "LUNES": 0, "MARTES": 1, "MIÉRCOLES": 2, "MIERCOLES": 2,
            "JUEVES": 3, "VIERNES": 4, "SÁBADO": 5, "SABADO": 5
        }
        
        registros_proyectados = []
        curr_date = fecha_inicio

        # 1. Proyectar las fechas día a día
        while curr_date <= fecha_fin:
            dia_num = curr_date.weekday()
            for _, row in df.iterrows():
                dia_str = str(row["DÍA"]).strip().upper()
                if MAPA_DIAS.get(dia_str) == dia_num:
                    registros_proyectados.append((
                        str(row["ESPACIO / SALÓN"]).strip().upper(),
                        dia_str,
                        curr_date.strftime("%Y-%m-%d"),
                        int(row["HORA INICIO (24H)"]),
                        int(row["HORA FIN (24H)"]),
                        str(row["ASIGNATURA"]).strip().upper(),
                        str(row["DOCENTE"]).strip().upper() if pd.notna(row["DOCENTE"]) else "POR ASIGNAR",
                        "clase",
                        ""
                    ))
            curr_date += datetime.timedelta(days=1)

        # 2. Convertir la lista a un DataFrame estructurado
        cols = ["espacio", "dia", "fecha", "hora_inicio", "hora_fin", "asignatura", "docente", "tipo_evento", "observacion"]
        df_proj = pd.DataFrame(registros_proyectados, columns=cols)

        # 3. Calcular los campos adicionales (mes y día numérico) que exige database.py
        if not df_proj.empty:
            df_proj["fecha_dt"] = pd.to_datetime(df_proj["fecha"])
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            df_proj["mes"] = df_proj["fecha_dt"].dt.month.apply(lambda m: meses[m - 1])
            df_proj["dia_num"] = df_proj["fecha_dt"].dt.day

        # 4. Enviar el DataFrame formateado a la BD
        self.db.reemplazar_horarios_semestre(df_proj, fecha_inicio, fecha_fin)
    def actualizar_horarios_desde_editor(self, df_editado):
        """Sincroniza los cambios realizados en la pestaña Edición Rápida con la BD."""
        es_vigente, msj, f_ini, f_fin = self.db.obtener_vigencia_semestre()
        
        # Si no hay fechas definidas previamente, se usa una ventana por defecto de 120 días
        if not f_ini or not f_fin:
            f_ini = datetime.date.today()
            f_fin = f_ini + datetime.timedelta(days=120)

        # Se llama a proyectar_y_guardar_semestre, el cual se encarga de formatear
        # el DataFrame y reemplazar las clases anteriores sin romper la vigencia
        self.proyectar_y_guardar_semestre(df_editado, f_ini, f_fin)