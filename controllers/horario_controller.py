import datetime
import pandas as pd

class HorarioController:
    def __init__(self, db_model):
        self.db = db_model

    def validar_y_procesar_excel(self, uploaded_file):
        """Lee y estandariza la estructura del archivo Excel subido asegurando nombres de columnas requeridos."""
        xls = pd.ExcelFile(uploaded_file)
        df_procesado = None

        # CASO 1: Formato de Base de Datos Directa (pestaña 'BD_Calendario_Semestre')
        if "BD_Calendario_Semestre" in xls.sheet_names:
            df_procesado = pd.read_excel(xls, sheet_name="BD_Calendario_Semestre")
        else:
            # CASO 2: Leer la primera pestaña disponible
            df_procesado = pd.read_excel(xls, sheet_name=0)

        if df_procesado is None or df_procesado.empty:
            raise ValueError("El archivo Excel se encuentra vacío.")

        # Normalización flexible de nombres de columnas
        mapeo = {}
        for col in df_procesado.columns:
            col_str = str(col).upper().strip()
            if any(k in col_str for k in ["ESPACIO", "SALON", "SALÓN", "AULA"]):
                mapeo[col] = "ESPACIO / SALÓN"
            elif any(k in col_str for k in ["DIA", "DÍA"]):
                mapeo[col] = "DÍA"
            elif "INICIO" in col_str or "DESDE" in col_str:
                mapeo[col] = "HORA INICIO (24H)"
            elif "FIN" in col_str or "HASTA" in col_str:
                mapeo[col] = "HORA FIN (24H)"
            elif any(k in col_str for k in ["ASIGNATURA", "MATERIA"]):
                mapeo[col] = "ASIGNATURA"
            elif any(k in col_str for k in ["DOCENTE", "PROFESOR"]):
                mapeo[col] = "DOCENTE"

        df_res = df_procesado.rename(columns=mapeo)

        # Garantizar que existan las 6 columnas requeridas por app.py
        cols_obligatorias = ["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]
        
        for col in cols_obligatorias:
            if col not in df_res.columns:
                if col == "HORA INICIO (24H)":
                    df_res[col] = 7
                elif col == "HORA FIN (24H)":
                    df_res[col] = 9
                elif col == "DOCENTE":
                    df_res[col] = "POR ASIGNAR"
                else:
                    raise ValueError(f"No se encontró la columna '{col}' ni un equivalente en el archivo Excel.")

        # Limpiar y retornar solo las columnas requeridas
        df_res = df_res[cols_obligatorias].dropna(subset=["ESPACIO / SALÓN", "ASIGNATURA"])
        return df_res

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