import datetime
import pandas as pd

class HorarioController:
    def __init__(self, db_model):
        self.db = db_model

    def validar_y_procesar_excel(self, uploaded_file):
        """Lee y estandariza la estructura del archivo Excel subido (Soporta Tablas Planas y Matrices Apiladas por Salón)."""
        xls = pd.ExcelFile(uploaded_file)
        
        # ---------------------------------------------------------------------
        # FORMATO 1: Hoja de Base de Datos Directa ('BD_Calendario_Semestre')
        # ---------------------------------------------------------------------
        if "BD_Calendario_Semestre" in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name="BD_Calendario_Semestre")
            cols_map = {}
            for c in df.columns:
                c_str = str(c).upper().strip()
                if any(k in c_str for k in ["ESPACIO", "SALON", "SALÓN", "AULA"]):
                    cols_map[c] = "ESPACIO / SALÓN"
                elif any(k in c_str for k in ["DIA", "DÍA"]):
                    cols_map[c] = "DÍA"
                elif "INICIO" in c_str:
                    cols_map[c] = "HORA INICIO (24H)"
                elif "FIN" in c_str:
                    cols_map[c] = "HORA FIN (24H)"
                elif any(k in c_str for k in ["ASIGNATURA", "MATERIA"]):
                    cols_map[c] = "ASIGNATURA"
                elif any(k in c_str for k in ["DOCENTE", "PROFESOR"]):
                    cols_map[c] = "DOCENTE"
            df = df.rename(columns=cols_map)
            reqs = ["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]
            if all(r in df.columns for r in reqs):
                return df[reqs].dropna(subset=["ESPACIO / SALÓN", "ASIGNATURA"])

        # ---------------------------------------------------------------------
        # FORMATO 2: Tabla Plana Convencional
        # ---------------------------------------------------------------------
        df_raw = pd.read_excel(xls, sheet_name=0)
        cols_map = {}
        for c in df_raw.columns:
            c_str = str(c).upper().strip()
            if any(k in c_str for k in ["ESPACIO", "SALON", "SALÓN", "AULA"]):
                cols_map[c] = "ESPACIO / SALÓN"
            elif any(k in c_str for k in ["DIA", "DÍA"]):
                cols_map[c] = "DÍA"
            elif "INICIO" in c_str:
                cols_map[c] = "HORA INICIO (24H)"
            elif "FIN" in c_str:
                cols_map[c] = "HORA FIN (24H)"
            elif any(k in c_str for k in ["ASIGNATURA", "MATERIA"]):
                cols_map[c] = "ASIGNATURA"
            elif any(k in c_str for k in ["DOCENTE", "PROFESOR"]):
                cols_map[c] = "DOCENTE"
                
        df_flat = df_raw.rename(columns=cols_map)
        reqs = ["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]
        if all(r in df_flat.columns for r in reqs):
            return df_flat[reqs].dropna(subset=["ESPACIO / SALÓN", "ASIGNATURA"])

        # ---------------------------------------------------------------------
        # FORMATO 3: Matriz / Cuadrícula Apilada por Salones (HORARIOS X SALONES DTE)
        # ---------------------------------------------------------------------
        df_grid = pd.read_excel(xls, sheet_name=0, header=None)
        registros = []
        
        i = 0
        num_rows = len(df_grid)
        dias_validos = ["LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO"]
        
        while i < num_rows:
            row_vals = df_grid.iloc[i].values
            row_strs = [str(v).strip() for v in row_vals if pd.notna(v) and str(v).strip() != '']
            
            is_hora_row = any("HORA" == s.upper() for s in row_strs)
            
            if is_hora_row:
                # Búsqueda hacia atrás para obtener el nombre exacto de la sala justo encima de HORA
                current_salon = "AULA GENERAL"
                for back in range(i - 1, -1, -1):
                    p_vals = df_grid.iloc[back].values
                    p_strs = [str(v).strip() for v in p_vals if pd.notna(v) and str(v).strip() != '']
                    if p_strs:
                        current_salon = " ".join(p_strs).strip()
                        break
                
                # Mapeo de columnas a Días de la semana
                col_to_day = {}
                for col_idx, val in enumerate(row_vals):
                    val_upper = str(val).strip().upper() if pd.notna(val) else ""
                    for d in dias_validos:
                        if d in val_upper:
                            norm_day = "MIÉRCOLES" if "MIER" in d else ("SÁBADO" if "SÁB" in d or "SAB" in d else d)
                            col_to_day[col_idx] = norm_day
                            break
                
                i += 1
                hour_entries = []
                
                # Lectura de filas que contienen las horas y materias del bloque
                while i < num_rows:
                    r_vals = df_grid.iloc[i].values
                    h_val = r_vals[0]
                    try:
                        h_int = int(float(h_val))
                        if 6 <= h_int <= 22:
                            day_cells = {}
                            for c_idx, day_name in col_to_day.items():
                                if c_idx < len(r_vals) and pd.notna(r_vals[c_idx]):
                                    cell_txt = str(r_vals[c_idx]).strip()
                                    if cell_txt and cell_txt.upper() != 'NAN':
                                        day_cells[day_name] = cell_txt
                            hour_entries.append((h_int, day_cells))
                            i += 1
                            continue
                    except (ValueError, TypeError):
                        pass
                    break
                
                hour_entries.sort(key=lambda x: x[0])
                all_hours = [h for h, _ in hour_entries]
                max_h = max(all_hours) + 1 if all_hours else 20
                
                # Procesar clases por día para el aula detectada
                for day_name in set(col_to_day.values()):
                    classes_in_day = []
                    for idx_h, (h_int, day_cells) in enumerate(hour_entries):
                        cell_txt = day_cells.get(day_name)
                        if cell_txt:
                            classes_in_day.append((idx_h, h_int, cell_txt))
                    
                    for idx_c, (entry_idx, h_start, cell_txt) in enumerate(classes_in_day):
                        if idx_c + 1 < len(classes_in_day):
                            next_h_start = classes_in_day[idx_c + 1][1]
                            h_end = next_h_start
                        else:
                            h_end = min(h_start + 3, max_h)
                        
                        parts = [p.strip() for p in cell_txt.split('\n') if p.strip()]
                        asig = parts[0] if len(parts) > 0 else cell_txt
                        doc = parts[1] if len(parts) > 1 else "POR ASIGNAR"
                        
                        registros.append({
                            "ESPACIO / SALÓN": current_salon,
                            "DÍA": day_name,
                            "HORA INICIO (24H)": h_start,
                            "HORA FIN (24H)": h_end,
                            "ASIGNATURA": asig,
                            "DOCENTE": doc
                        })
                continue
            i += 1
            
        df_res = pd.DataFrame(registros)
        if not df_res.empty:
            return df_res[["ESPACIO / SALÓN", "DÍA", "HORA INICIO (24H)", "HORA FIN (24H)", "ASIGNATURA", "DOCENTE"]]
            
        raise ValueError("No se pudieron extraer datos válidos del archivo Excel subido.")

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