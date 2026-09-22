import datetime
import pandas as pd

class HorarioController:
    def __init__(self, db_model):
        self.db = db_model

    def validar_y_procesar_excel(self, uploaded_file):
        """Lee y estandariza la estructura del archivo Excel subido."""
        xls = pd.ExcelFile(uploaded_file)
        
        # 1. Si viene en formato BD directa
        if "BD_Calendario_Semestre" in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name="BD_Calendario_Semestre")
            columnas_req = ["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]
            
            for col in columnas_req:
                if col not in df.columns:
                    raise ValueError(f"Falta la columna requerida: {col}")
            return df

        # 2. Si viene en formato Matriz/Cuadrícula
        df_raw = pd.read_excel(xls, sheet_name=0)
        registros = []
        
        # Procesamiento de la matriz de horarios
        for index, row in df_raw.iterrows():
            pass

        df_result = pd.DataFrame(registros)
        if df_result.empty:
            raise ValueError("No se pudieron extraer datos válidos del Excel.")
        return df_result

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

        self.db.guardar_horarios_masivos(registros_proyectados, fecha_inicio, fecha_fin)

    def actualizar_horarios_desde_editor(self, df_editado):
        """Sincroniza los cambios directos realizados desde la pestaña 'Edición Rápida'."""
        f_ini, f_fin = self.db.obtener_rango_semestre()
        if not f_ini or not f_fin:
            f_ini = datetime.date.today()
            f_fin = f_ini + datetime.timedelta(days=120)

        self.db.vaciar_base_de_datos()
        self.proyectar_y_guardar_semestre(df_editado, f_ini, f_fin)