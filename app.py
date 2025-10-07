import streamlit as st
import pandas as pd
import os
import plotly.express as px

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
MASTER_EXCEL = "datos.xlsx"
USUARIOS_EXCEL = "usuarios.xlsx"
UPLOAD_FOLDER = "ExcelUploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. DEFINICIÓN FINAL DEL MAPEO (Excel Header -> Letra Corta)
MAPEO_COLUMNAS = {
    'TAREA': 'A',
    'ORDEN': 'B',
    'ESTADO DE LA TAREA': 'F',
    'TIPO DE ORDEN DE TRABAJO': 'G', 
    'UBICACIÓN': 'O', 
    'TÉCNICO': 'P',    
    'CONTRATO': 'Q',
    'CLIENTE': 'R',
    'FECHA DE FINALIZACIÓN': 'T' 
}

COLUMNAS_SELECCIONADAS = list(MAPEO_COLUMNAS.values()) 
ENCABEZADOS_ESPERADOS = list(MAPEO_COLUMNAS.keys())

# 2. DEFINICIÓN DEL MAPEO INVERSO (Letra Corta -> Nombre Descriptivo)
FINAL_RENAMING_MAP = {v: k for k, v in MAPEO_COLUMNAS.items()}
COL_FECHA_KEY = 'T' 
COL_FECHA_DESCRIPTIVA = FINAL_RENAMING_MAP[COL_FECHA_KEY] 
COL_TEMP_DATETIME = '_DATETIME_' + COL_FECHA_KEY
COL_FINAL_SEMANA_GRAFICO = 'SEMANA_DE_GRÁFICO' 

# Columnas clave para los filtros
COL_TECNICO_KEY = 'P' 
COL_CIUDAD_KEY = 'O' 
COL_TIPO_ORDEN_KEY = 'G' 

COL_TECNICO_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_TECNICO_KEY, 'TÉCNICO')
COL_CIUDAD_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_CIUDAD_KEY, 'UBICACIÓN') 
COL_TIPO_ORDEN_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_TIPO_ORDEN_KEY, 'TIPO DE ORDEN DE TRABAJO')

# --- Nuevas columnas temporales para el filtrado limpio ---
COL_FILTRO_TECNICO = '_Filtro_Tecnico_'
COL_FILTRO_CIUDAD = '_Filtro_Ubicacion_'

# --- Nuevas columnas para los Gráficos de Trayectoria ---
COL_SEGM_TIEMPO = '_SEGM_AÑO_MES_'
COL_TIPO_INST = '_ES_INSTALACION_'
COL_TIPO_VISITA = '_ES_VISITA_'

st.set_page_config(page_title="Estadístico Isertel", layout="wide")

# --- FUNCIONES DE LIMPIEZA PARA FILTROS ---
def clean_tecnico(tecnico):
    """Extrae el nombre del técnico después del '|'."""
    if isinstance(tecnico, str) and '|' in tecnico:
        return tecnico.split('|', 1)[1].strip()
    return str(tecnico).strip()

def clean_ciudad(ciudad):
    """Extrae la ciudad antes de la primera ','."""
    if isinstance(ciudad, str) and ',' in ciudad:
        return ciudad.split(',', 1)[0].strip()
    return str(ciudad).strip()

# --- FUNCIÓN DE SEGMENTACIÓN FIJA SOLICITADA ---
@st.cache_data
def calculate_fixed_week(day):
    """
    Calcula el número de semana (1-5) basado en el día del mes.
    """
    if day <= 7:
        return 1
    elif day <= 14:
        return 2
    elif day <= 21:
        return 3
    elif day <= 28:
        return 4
    else: # 29, 30, 31
        return 5

# --- FUNCIÓN DE TRAYECTORIA ---
@st.cache_data
def prepare_trajectory_data(df):
    """
    Prepara el DataFrame para los gráficos de trayectoria secuencial (conteo por segmento de tiempo).
    """
    if df.empty:
        return pd.DataFrame(), []
    
    # Asegurar que las columnas de tiempo existen
    if COL_TEMP_DATETIME not in df.columns:
        df[COL_TEMP_DATETIME] = pd.to_datetime(df[COL_FECHA_KEY], errors='coerce')
    
    df_temp = df.copy()
    
    # 1. Creación del segmento de tiempo (Año-Mes-SemanaFija)
    df_temp['DAY'] = df_temp[COL_TEMP_DATETIME].dt.day.astype(int, errors='ignore')
    df_temp['MONTH'] = df_temp[COL_TEMP_DATETIME].dt.month.astype(int, errors='ignore')
    df_temp['YEAR'] = df_temp[COL_TEMP_DATETIME].dt.year.astype(int, errors='ignore')
    
    # Manejar posibles errores en la conversión a int si hay NaT
    df_temp.dropna(subset=['DAY', 'MONTH', 'YEAR'], inplace=True)
    df_temp['DAY'] = df_temp['DAY'].astype(int)
    df_temp['MONTH'] = df_temp['MONTH'].astype(int)
    df_temp['YEAR'] = df_temp['YEAR'].astype(int)


    df_temp['FIXED_WEEK'] = df_temp['DAY'].apply(calculate_fixed_week).astype(int)
    df_temp[COL_SEGM_TIEMPO] = df_temp['YEAR'].astype(str) + '-' + df_temp['MONTH'].astype(str).str.zfill(2) + '-' + df_temp['FIXED_WEEK'].astype(str)
    
    # 2. Identificación de tipos de órdenes
    if COL_TIPO_ORDEN_KEY in df_temp.columns:
        df_temp[COL_TIPO_INST] = df_temp[COL_TIPO_ORDEN_KEY].astype(str).str.contains('INSTALACION', case=False, na=False).astype(int)
        df_temp[COL_TIPO_VISITA] = df_temp[COL_TIPO_ORDEN_KEY].astype(str).str.contains('VISITA TÉCNICA', case=False, na=False).astype(int)
    else:
        df_temp[COL_TIPO_INST] = 0
        df_temp[COL_TIPO_VISITA] = 0
    
    # 3. Agrupación y Conteo por Segmento de Tiempo y Técnico
    df_grouped = df_temp.groupby([COL_SEGM_TIEMPO, COL_FILTRO_TECNICO]).agg(
        Total_Instalaciones=(COL_TIPO_INST, 'sum'),
        Total_Visitas=(COL_TIPO_VISITA, 'sum')
    ).reset_index()

    # 4. Creación de la etiqueta del segmento de tiempo (Para el eje X legible)
    def get_segment_label(year_month_segm):
        if pd.isna(year_month_segm): return "N/A"
        try:
            parts = year_month_segm.split('-')
            if len(parts) < 3: return year_month_segm
            
            year, month, week_num = parts
            
            ranges = {1: 'Día 1-7', 2: 'Día 8-14', 3: 'Día 15-21', 4: 'Día 22-28', 5: 'Día 29-31'}
            month_name = pd.to_datetime(month, format='%m').strftime('%b')
            week_num_int = int(week_num) if week_num.isdigit() else 5
            
            return f"{ranges.get(week_num_int, 'S5+')} ({month_name}/{year[-2:]})" # Usar solo los dos últimos dígitos del año
        except:
            return year_month_segm
        
    df_grouped['Segmento_Label'] = df_grouped[COL_SEGM_TIEMPO].apply(get_segment_label)
    
    # 5. Asegurar el orden correcto de los segmentos de tiempo para el eje X
    df_grouped = df_grouped.sort_values(by=COL_SEGM_TIEMPO)
    segment_order = df_grouped[COL_SEGM_TIEMPO].unique()
    segment_label_order = [get_segment_label(s) for s in segment_order]

    return df_grouped, segment_label_order


# --- LECTURA DE USUARIOS ---
try:
    usuarios_df = pd.read_excel(USUARIOS_EXCEL)
    usuarios_df['Usuario'] = usuarios_df['Usuario'].astype(str).str.strip()
    usuarios_df['Contraseña'] = usuarios_df['Contraseña'].astype(str).str.strip()
    usuarios_df['Rol'] = usuarios_df['Rol'].astype(str).str.strip()
except FileNotFoundError:
    st.error(f"No se encontró {USUARIOS_EXCEL}. Asegúrate de tener un archivo de usuarios.")
    st.stop()

# --- SESSION STATE ---
if 'login' not in st.session_state:
    st.session_state.login = False
if 'rol' not in st.session_state:
    st.session_state.rol = None
if 'usuario' not in st.session_state:
    st.session_state.usuario = None

# --- LOGIN ---
if not st.session_state.login:
    st.title("📊 Estadístico Isertel - Login")
    st.subheader("Inicia sesión para acceder")
    
    # Centrar la caja de login ligeramente
    col_login_spacer_l, col_login_box, col_login_spacer_r = st.columns([1, 2, 1])
    
    with col_login_box:
        usuario_input = st.text_input("Usuario")
        contrasena_input = st.text_input("Contraseña", type="password")

        if st.button("Iniciar sesión", use_container_width=True):
            user_row = usuarios_df[
                (usuarios_df["Usuario"].str.lower() == usuario_input.strip().lower()) &
                (usuarios_df["Contraseña"] == contrasena_input.strip())
            ]
            if not user_row.empty:
                st.session_state.login = True
                st.session_state.rol = user_row.iloc[0]["Rol"]
                st.session_state.usuario = usuario_input.strip()
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

else:
    # --- Interfaz Principal ---
    st.title("📊 Estadístico Isertel")
    
    st.sidebar.success(f"Bienvenido {st.session_state.usuario} ({st.session_state.rol})")
    st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update({"login": False, "rol": None, "usuario": None}), key="logout_btn")

    # --- LÓGICA DE CARGA Y COMBINACIÓN DE DATOS ---
    archivos_para_combinar_nombres = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.xlsx', '.xls', '.csv'))]
    num_archivos_cargados = len(archivos_para_combinar_nombres)
    datos = None

    df_list = []
    
    if archivos_para_combinar_nombres: 
        st.sidebar.info(f"💾 **{num_archivos_cargados}** archivo(s) cargado(s) y combinado(s).")
        archivos_completos = [os.path.join(UPLOAD_FOLDER, f) for f in archivos_para_combinar_nombres]
        
        try:
            total_columnas_mapeadas = 0
            
            for f in archivos_completos:
                if f.lower().endswith('.csv'):
                    try:
                        df = pd.read_csv(f, encoding='utf-8')
                    except UnicodeDecodeError:
                        df = pd.read_csv(f, encoding='latin1')
                else:
                    df = pd.read_excel(f)
                
                # --- SOLUCIÓN ROBUSTA PARA DUPLICADOS EN CABECERA ---
                cleaned_names = []
                name_counts = {}
                for name in df.columns:
                    cleaned_name = str(name).upper().strip()
                    name_counts[cleaned_name] = name_counts.get(cleaned_name, 0) + 1
                    
                    if name_counts[cleaned_name] > 1:
                        cleaned_name = f"{cleaned_name}_{name_counts[cleaned_name]}"
                        
                    cleaned_names.append(cleaned_name)
                
                df.columns = cleaned_names
                # --------------------------------------------------

                df_temp = pd.DataFrame()
                columnas_encontradas_en_archivo = 0
                
                for encabezado_excel, columna_final in MAPEO_COLUMNAS.items():
                    
                    if encabezado_excel in df.columns:
                        df_temp[columna_final] = df[encabezado_excel]
                        columnas_encontradas_en_archivo += 1
                
                if not df_temp.empty:
                    df_temp = df_temp.reindex(columns=COLUMNAS_SELECCIONADAS, fill_value=None)
                    df_list.append(df_temp)
                    total_columnas_mapeadas += columnas_encontradas_en_archivo 

            
            if df_list:
                datos = pd.concat(df_list, ignore_index=True)
                datos.to_excel(MASTER_EXCEL, index=False)

            if datos is None or datos.empty or total_columnas_mapeadas == 0:
                 st.warning(f"Ninguno de los encabezados de columnas esperados ({', '.join(ENCABEZADOS_ESPERADOS)}) se encontró en los archivos combinados. La tabla estará vacía.")
            
        except Exception as e:
            st.error(f"Error al combinar o leer archivos de la carpeta de subidas: {e}")
            datos = None
    else:
        st.sidebar.warning("⚠️ No hay archivos cargados.")
        try:
            datos = pd.read_excel(MASTER_EXCEL)
            
            columnas_existentes = [col for col in COLUMNAS_SELECCIONADAS if col in datos.columns]
            datos = datos[columnas_existentes]

            if not columnas_existentes:
                 st.warning("El archivo maestro no contiene las columnas necesarias (A, B, F, G, O, P, Q, R, T).")
                 datos = None

        except FileNotFoundError:
            st.info("⚠️ No hay datos disponibles. El administrador debe subir archivos.")
            datos = None
        except Exception as e:
            st.error(f"Error al leer el archivo maestro {MASTER_EXCEL}: {e}")
            datos = None

    
    # --- Estructura con PESTAÑAS (Mejora visual clave) ---
    tabs = ["📊 Dashboard", "⚙️ Administración de Datos"] if st.session_state.rol.lower() == "admin" else ["📊 Dashboard"]
    
    if datos is not None and not datos.empty:
        tab_dashboard, *tab_admin = st.tabs(tabs) 
    elif st.session_state.rol.lower() == "admin":
        tab_dashboard, tab_admin_content = st.tabs(tabs) 
        tab_admin = [tab_admin_content]
    else:
        st.warning("No hay datos para mostrar y no tienes permisos de administrador para subir.")
        st.stop()


    # --- PESTAÑA DE ADMINISTRACIÓN (solo para ADMIN) ---
    if st.session_state.rol.lower() == "admin" and tab_admin:
        with tab_admin[0]:
            st.header("⚙️ Administración de Archivos Fuente")
            
            # MENÚ CONTEXTUAL DE ARCHIVOS
            st.metric(label="Documentos Excel/CSV Cargados", value=f"{num_archivos_cargados} archivos")
            st.markdown("---") 

            # Columna para Subir y columna para Eliminar
            col_upload, col_delete = st.columns(2)

            with col_upload:
                st.subheader("Subir y Añadir Archivos")
                nuevos_archivos = st.file_uploader("Subir archivos Excel/CSV", type=["xlsx", "xls", "csv"], accept_multiple_files=True)
                if nuevos_archivos:
                    for f in nuevos_archivos:
                        save_path = os.path.join(UPLOAD_FOLDER, f.name)
                        with open(save_path, "wb") as file:
                            file.write(f.getbuffer())
                    st.success(f"{len(nuevos_archivos)} archivos guardados. Recargando datos...")
                    st.rerun() 

            with col_delete:
                st.subheader("Eliminar Archivos")
                archivos_actuales = os.listdir(UPLOAD_FOLDER)
                
                # Opción 1: Eliminar uno por uno
                eliminar = st.multiselect("Selecciona archivos a eliminar", archivos_actuales, key="admin_multiselect_del")
                if st.button("🗑️ Eliminar seleccionados", key="del_selected"):
                    if eliminar:
                        for f in eliminar:
                            os.remove(os.path.join(UPLOAD_FOLDER, f))
                        st.success(f"{len(eliminar)} archivos eliminados. Recargando datos...")
                        st.rerun()
                    else:
                         st.info("No seleccionaste archivos para eliminar.")
                
                # Opción 2: Eliminar todo
                if archivos_actuales and st.button("🔴 Eliminar TODOS los archivos", key="del_all"):
                    archivos_eliminados_count = len(archivos_actuales)
                    
                    for f in archivos_actuales:
                        os.remove(os.path.join(UPLOAD_FOLDER, f))
                    
                    if os.path.exists(MASTER_EXCEL):
                        os.remove(MASTER_EXCEL)
                    
                    st.success(f"{archivos_eliminados_count} archivos eliminados y Master Excel borrado. Dashboard vacío. Recargando...")
                    st.rerun()
                elif not archivos_actuales:
                     st.info("La carpeta de subidas está vacía.")
            
            st.markdown("---")

    # --- PESTAÑA DEL DASHBOARD (Disponible para ADMIN y USER) ---
    with tab_dashboard:
        if datos is None or datos.empty:
            st.warning("No hay datos para mostrar.")
        else:
            
            # 1. PREPARACIÓN DE DATOS BASE Y CONVERSIÓN DE FECHA
            datos_filtrados = datos.copy() 
            
            datos_filtrados[COL_TEMP_DATETIME] = pd.to_datetime(datos_filtrados[COL_FECHA_KEY], errors='coerce')
            
            datos_filtrados.dropna(subset=[COL_TEMP_DATETIME], inplace=True)
            
            if datos_filtrados.empty:
                st.warning("No hay registros válidos con fechas de finalización para mostrar después de la limpieza.")
                pass 
            else: # Solo si hay datos válidos, procedemos con filtros y gráficos
                
                # --- Contenedor de Filtros (para agrupar y acercar) ---
                # MEJORA VISUAL: Usamos st.expander para ocultar los filtros y limpiar el dashboard inicialmente
                with st.expander("🔎 Opciones de Filtro y Rango de Fechas", expanded=True): 
                    
                    # 2. FILTRO DE RANGO DE FECHAS
                    st.subheader(f"📅 Rango de {COL_FECHA_DESCRIPTIVA} y Filtros de Segmentación")
                    
                    col_desde, col_hasta, _, _ = st.columns([1.5, 1.5, 0.5, 5]) 

                    # Filtro de fecha en las primeras dos columnas
                    with col_desde:
                        min_date_global = datos_filtrados[COL_TEMP_DATETIME].min().date()
                        max_date_global = datos_filtrados[COL_TEMP_DATETIME].max().date()
                        date_from = st.date_input("Desde:", value=min_date_global, min_value=min_date_global, max_value=max_date_global, key='filter_date_from')
                    
                    with col_hasta:
                        date_to = st.date_input("Hasta:", value=max_date_global, min_value=min_date_global, max_value=max_date_global, key='filter_date_to')

                    if date_from > date_to:
                        st.error("⚠️ La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'.")
                        datos_filtrados = pd.DataFrame() 
                        st.stop() 
                    
                    filtro_inicio = pd.to_datetime(date_from)
                    filtro_fin = pd.to_datetime(date_to) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1) 
                    
                    datos_filtrados = datos_filtrados[
                        (datos_filtrados[COL_TEMP_DATETIME] >= filtro_inicio) & 
                        (datos_filtrados[COL_TEMP_DATETIME] <= filtro_fin)
                    ].copy()

                    # --- PRE-PROCESAMIENTO PARA FILTROS (solo para las opciones de los desplegables) ---
                    if COL_TECNICO_KEY in datos_filtrados.columns:
                        datos_filtrados[COL_FILTRO_TECNICO] = datos_filtrados[COL_TECNICO_KEY].astype(str).apply(clean_tecnico)
                    if COL_CIUDAD_KEY in datos_filtrados.columns:
                        datos_filtrados[COL_FILTRO_CIUDAD] = datos_filtrados[COL_CIUDAD_KEY].astype(str).apply(clean_ciudad)
                    
                    df_all = datos_filtrados.copy()

                    @st.cache_data
                    def get_multiselect_options(df, col_key_filtro):
                        """Obtiene opciones únicas (limpias) de una columna para el multiselect."""
                        if col_key_filtro not in df.columns:
                            return []
                        
                        valores = df[col_key_filtro].astype(str).unique().tolist()
                        
                        opciones = []
                        hay_nulos = False
                        
                        for v in valores:
                            if pd.isna(v) or v.lower() in ('nan', 'none', '') or (isinstance(v, str) and not v.strip()):
                                hay_nulos = True
                            else:
                                opciones.append(v)
                        
                        opciones = sorted(opciones)
                        if hay_nulos:
                            opciones.insert(0, '(Nulos/Vacíos)')
                        return opciones

                    @st.cache_data
                    def apply_filter(df, col_key_filtro, selected_options):
                        """Aplica un filtro a un DataFrame basada en las opciones seleccionadas (limpias)."""
                        if not selected_options or col_key_filtro not in df.columns:
                            return df
                        
                        filtro_valido = [val for val in selected_options if val != '(Nulos/Vacíos)']
                        filtro_nulos = '(Nulos/Vacíos)' in selected_options
                        
                        mascara_validos = df[col_key_filtro].astype(str).isin(filtro_valido)
                        
                        if filtro_nulos:
                            mascara_nulos = df[col_key_filtro].isna() | (df[col_key_filtro].astype(str).str.strip() == '')
                            mascara = mascara_validos | mascara_nulos
                        else:
                            mascara = mascara_validos

                        return df[mascara]

                    # 3. FILTROS DE SEGMENTACIÓN (CASCADA DOBLE VÍA)
                    st.markdown("---")
                    
                    col_ciu, col_tec = st.columns(2)
                    
                    filtro_ciudad_actual = st.session_state.get('multiselect_ubicacion', [])
                    filtro_tecnico_actual = st.session_state.get('multiselect_tecnico', [])

                    df_domain_ciu = apply_filter(df_all, COL_FILTRO_TECNICO, filtro_tecnico_actual)
                    opciones_ciudad = get_multiselect_options(df_domain_ciu, COL_FILTRO_CIUDAD)

                    df_domain_tec = apply_filter(df_all, COL_FILTRO_CIUDAD, filtro_ciudad_actual)
                    opciones_tecnico = get_multiselect_options(df_domain_tec, COL_FILTRO_TECNICO)

                    with col_ciu:
                        filtro_ciudad = st.multiselect(
                            f"Seleccionar **{COL_CIUDAD_DESCRIPTIVA}** (Limpio):", 
                            options=opciones_ciudad,
                            default=filtro_ciudad_actual, 
                            key='multiselect_ubicacion'
                        )
                        
                    with col_tec:
                        filtro_tecnico = st.multiselect(
                            f"Seleccionar **{COL_TECNICO_DESCRIPTIVA}** (Limpio):", 
                            options=opciones_tecnico,
                            default=filtro_tecnico_actual, 
                            key='multiselect_tecnico'
                        )

                    # --- APLICACIÓN FINAL DE FILTROS ---
                    df_final = apply_filter(df_all, COL_FILTRO_CIUDAD, filtro_ciudad)
                    df_final = apply_filter(df_final, COL_FILTRO_TECNICO, filtro_tecnico)
                    
                    datos_filtrados = df_final
                
                # NUEVO SEPARADOR VISUAL: Separa los filtros de las métricas/resultados
                st.markdown("---")

                # 4. CÁLCULO Y VISTA DEL MENÚ CONTEXTUAL (Métricas)
                st.subheader("💡 Métricas Clave y Desempeño") 
                
                # --- TARJETA DE KPIS ---
                with st.container(border=True): # <--- CONTENEDOR TIPO TARJETA
                    total_registros = len(datos_filtrados)
                    
                    # Cálculos
                    if COL_TIPO_ORDEN_KEY in datos_filtrados.columns:
                        total_instalaciones = len(datos_filtrados[
                            datos_filtrados[COL_TIPO_ORDEN_KEY].astype(str).str.contains('INSTALACION', case=False, na=False)
                        ])
                        total_visitas_tecnicas = len(datos_filtrados[
                            datos_filtrados[COL_TIPO_ORDEN_KEY].astype(str).str.contains('VISITA TÉCNICA', case=False, na=False)
                        ])
                    else:
                        total_instalaciones = 0
                        total_visitas_tecnicas = 0

                    tasa_instalacion = total_instalaciones / total_registros if total_registros > 0 else 0.0
                    tasa_visitas_tecnicas = total_visitas_tecnicas / total_registros if total_registros > 0 else 0.0

                    # Columnas para las métricas (5 columnas)
                    col_metric_1, col_metric_2, col_metric_3, col_metric_4, col_metric_5 = st.columns(5)

                    with col_metric_1:
                        st.metric(label="📦 Total de Ordenes", value=f"{total_registros:,}")
                    with col_metric_2:
                        st.metric(label="✅ Total Instalaciones", value=f"{total_instalaciones:,}")
                    with col_metric_3:
                        st.metric(label="🛠️ Total Visitas Técnicas", value=f"{total_visitas_tecnicas:,}")
                    with col_metric_4:
                        # Se elimina el 'delta' con el "Objetivo 80%"
                        st.metric(label="📈 Tasa de Instalación", value=f"{tasa_instalacion:.1%}") 
                    with col_metric_5:
                        st.metric(label="📉 Tasa de Visitas Técnicas", value=f"{tasa_visitas_tecnicas:.1%}")
                
                
                # --- LAYOUT PRINCIPAL: GRÁFICO (Columna 1) y OTROS (Columna 2) ---
                col_grafico, col_otros = st.columns([3, 1])
                
                # 5. GRÁFICO DE TAREAS REALIZADAS POR SEGMENTO FIJO (BARRA)
                with col_grafico:
                    with st.container(border=True): # <--- Tarjeta para el Gráfico
                        st.subheader("📊 Tareas Realizadas: Últimos 5 Segmentos Fijos")

                        df_escala = pd.DataFrame() 
                        
                        if total_registros > 0:
                            
                            datos_temp = datos_filtrados.copy()
                            datos_temp['DAY'] = datos_temp[COL_TEMP_DATETIME].dt.day.astype(int, errors='ignore')
                            datos_temp['MONTH'] = datos_temp[COL_TEMP_DATETIME].dt.month.astype(int, errors='ignore')
                            datos_temp['YEAR'] = datos_temp[COL_TEMP_DATETIME].dt.year.astype(int, errors='ignore')
                            datos_temp.dropna(subset=['DAY', 'MONTH', 'YEAR'], inplace=True)
                            datos_temp['DAY'] = datos_temp['DAY'].astype(int)
                            datos_temp['MONTH'] = datos_temp['MONTH'].astype(int)
                            datos_temp['YEAR'] = datos_temp['YEAR'].astype(int)
                            
                            datos_temp['FIXED_WEEK'] = datos_temp['DAY'].apply(calculate_fixed_week).astype(int)
                            datos_temp[COL_SEGM_TIEMPO] = datos_temp['YEAR'].astype(str) + '-' + datos_temp['MONTH'].astype(str).str.zfill(2) + '-' + datos_temp['FIXED_WEEK'].astype(str)
                            
                            conteo_segmentos = datos_temp.groupby(COL_SEGM_TIEMPO).size().reset_index(name='Total_Tareas')
                            
                            top_5_segmentos = conteo_segmentos.sort_values(by=COL_SEGM_TIEMPO, ascending=False).head(5)
                            df_escala = top_5_segmentos.sort_values(by=COL_SEGM_TIEMPO, ascending=True).copy()
                            
                            def get_segment_range(year_month_segm):
                                week_num = int(year_month_segm.split('-')[2])
                                ranges = {1: 'Día 1-7', 2: 'Día 8-14', 3: 'Día 15-21', 4: 'Día 22-28', 5: 'Día 29-31'}
                                month_num = int(year_month_segm.split('-')[1])
                                month_name = pd.to_datetime(str(month_num), format='%m').strftime('%b')
                                year = year_month_segm.split('-')[0]
                                return f"{ranges.get(week_num, 'S5+')} ({month_name}/{year[-2:]})"

                            df_escala['Segmento_Label'] = df_escala.apply(lambda row: get_segment_range(row[COL_SEGM_TIEMPO]), axis=1)

                            conteo_5_segmentos = df_escala[[COL_SEGM_TIEMPO, 'Segmento_Label']].merge(
                                conteo_segmentos[[COL_SEGM_TIEMPO, 'Total_Tareas']], 
                                on=COL_SEGM_TIEMPO, 
                                how='left'
                            ).fillna(0)
                            
                            conteo_5_segmentos['Total_Tareas'] = conteo_5_segmentos['Total_Tareas'].astype(int)
                            
                            # GENERAR GRÁFICO
                            fig = px.bar(
                                conteo_5_segmentos, 
                                x='Segmento_Label', 
                                y='Total_Tareas',
                                title='Conteo de Tareas Finalizadas por Segmento Fijo (Últimos 5)',
                                labels={'Segmento_Label': 'Período Semanal Fijo', 'Total_Tareas': 'Cantidad de Tareas'},
                                text='Total_Tareas',
                                color_discrete_sequence=['#4CAF50']
                            )
                            
                            fig.update_layout(
                                uniformtext_minsize=8, 
                                uniformtext_mode='hide', 
                                xaxis_title=None, 
                                yaxis_title='Cantidad de Tareas',
                                xaxis={'categoryorder':'array', 'categoryarray': conteo_5_segmentos['Segmento_Label']} 
                            )
                            fig.update_traces(textposition='outside')
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                        else:
                            st.info("No hay datos filtrados para generar el gráfico semanal.")

                
                # --- SECCIÓN DE GRÁFICOS DE TRAYECTORIA (NUEVA MÉTRICA SOLICITADA) ---
                
                # Solo si se ha aplicado el filtro de ubicación Y hay al menos 2 técnicos.
                if filtro_ciudad and COL_FILTRO_TECNICO in datos_filtrados.columns and len(datos_filtrados[COL_FILTRO_TECNICO].unique()) > 1:
                    
                    df_trayectoria, segment_label_order = prepare_trajectory_data(datos_filtrados)
                    
                    if not df_trayectoria.empty and df_trayectoria['Total_Instalaciones'].sum() + df_trayectoria['Total_Visitas'].sum() > 0:
                        
                        st.markdown("---")
                        st.subheader(f"📈 Trayectoria Semanal por Técnico en {', '.join(filtro_ciudad)}")
                        
                        col_trayectoria_inst, col_trayectoria_visita = st.columns(2)
                        
                        # GRÁFICO 1: TRAYECTORIA DE INSTALACIONES
                        with col_trayectoria_inst:
                            with st.container(border=True):
                                if df_trayectoria['Total_Instalaciones'].sum() > 0:
                                    
                                    # Gráfico de Líneas para Instalaciones
                                    fig_inst = px.line(
                                        df_trayectoria, 
                                        x='Segmento_Label', 
                                        y='Total_Instalaciones',
                                        color=COL_FILTRO_TECNICO,
                                        title='Trayectoria de **Instalaciones** por Técnico (Conteo por Segmento)',
                                        labels={'Segmento_Label': 'Período Semanal Fijo', 'Total_Instalaciones': 'Instalaciones Realizadas', COL_FILTRO_TECNICO: 'Técnico'},
                                        markers=True
                                    )
                                    
                                    fig_inst.update_layout(
                                        xaxis={'categoryorder':'array', 'categoryarray': segment_label_order},
                                        yaxis_title='Total de Instalaciones',
                                        legend_title='Técnico'
                                    )
                                    st.plotly_chart(fig_inst, use_container_width=True)
                                else:
                                    st.info("No hay **Instalaciones** registradas para el filtro seleccionado.")

                        # GRÁFICO 2: TRAYECTORIA DE VISITAS TÉCNICAS
                        with col_trayectoria_visita:
                            with st.container(border=True):
                                if df_trayectoria['Total_Visitas'].sum() > 0:
                                    
                                    # Gráfico de Líneas para Visitas Técnicas
                                    fig_visita = px.line(
                                        df_trayectoria, 
                                        x='Segmento_Label', 
                                        y='Total_Visitas',
                                        color=COL_FILTRO_TECNICO,
                                        title='Trayectoria de **Visitas Técnicas** por Técnico (Conteo por Segmento)',
                                        labels={'Segmento_Label': 'Período Semanal Fijo', 'Total_Visitas': 'Visitas Técnicas Realizadas', COL_FILTRO_TECNICO: 'Técnico'},
                                        markers=True
                                    )
                                    
                                    fig_visita.update_layout(
                                        xaxis={'categoryorder':'array', 'categoryarray': segment_label_order},
                                        yaxis_title='Total de Visitas Técnicas',
                                        legend_title='Técnico'
                                    )
                                    st.plotly_chart(fig_visita, use_container_width=True)
                                else:
                                    st.info("No hay **Visitas Técnicas** registradas para el filtro seleccionado.")
                                
                    else:
                        st.info("💡 No hay datos de Instalaciones o Visitas Técnicas en este filtro.")
                                
                elif filtro_ciudad and COL_FILTRO_TECNICO in datos_filtrados.columns:
                     st.info("💡 Selecciona una ubicación con **al menos dos técnicos** para ver la Trayectoria de Desempeño.")
                # --- FIN DE GRÁFICOS DE TRAYECTORIA ---


                # 6. GRÁFICO DE TAREAS POR TÉCNICO (COLUMNA DERECHA)
                with col_otros:
                    with st.container(border=True): # <--- Tarjeta para el Top Técnico
                        st.subheader("Top 5 Técnicos")
                        
                        if COL_FILTRO_TECNICO in datos_filtrados.columns and total_registros > 0:
                            top_tecnicos = datos_filtrados[COL_FILTRO_TECNICO].value_counts().reset_index()
                            top_tecnicos.columns = ['Técnico', 'Total Tareas']
                            top_tecnicos = top_tecnicos.head(5)
                            
                            # Gráfico circular (Pie Chart) para distribución
                            fig_pie = px.pie(
                                top_tecnicos, 
                                values='Total Tareas', 
                                names='Técnico', 
                                title='Distribución del Top 5',
                                hole=.3, 
                                color_discrete_sequence=px.colors.qualitative.Pastel 
                            )
                            fig_pie.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
                            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                        else:
                            st.info("Datos insuficientes para Top Técnico.")
                            
                # 7. TABLA DE RESULTADOS RAW (OCULTA EN UN EXPANDER)
                
                # PREPARACIÓN FINAL DE LA TABLA
                # Re-calculamos estas columnas para la tabla si se han perdido por NaT
                if 'DAY' not in datos_filtrados.columns:
                    datos_filtrados['DAY'] = datos_filtrados[COL_TEMP_DATETIME].dt.day.astype(int, errors='ignore')
                    datos_filtrados['MONTH'] = datos_filtrados[COL_TEMP_DATETIME].dt.month.astype(int, errors='ignore')
                    datos_filtrados['YEAR'] = datos_filtrados[COL_TEMP_DATETIME].dt.year.astype(int, errors='ignore')
                    datos_filtrados.dropna(subset=['DAY', 'MONTH', 'YEAR'], inplace=True)
                    datos_filtrados['DAY'] = datos_filtrados['DAY'].astype(int)
                    datos_filtrados['FIXED_WEEK'] = datos_filtrados['DAY'].apply(calculate_fixed_week).astype(int)

                if 'FIXED_WEEK' in datos_filtrados.columns:
                    datos_filtrados[COL_FINAL_SEMANA_GRAFICO] = datos_filtrados['FIXED_WEEK'].astype(str)
                else:
                    datos_filtrados[COL_FINAL_SEMANA_GRAFICO] = 'Sin Datos'
                
                
                temp_cols_to_drop = [COL_TEMP_DATETIME, 'DAY', 'MONTH', 'YEAR', 'FIXED_WEEK', COL_SEGM_TIEMPO, COL_FILTRO_CIUDAD, COL_FILTRO_TECNICO, COL_TIPO_INST, COL_TIPO_VISITA]
                for col in temp_cols_to_drop:
                    if col in datos_filtrados.columns:
                        datos_filtrados.drop(columns=[col], inplace=True) 

                datos_vista = datos_filtrados.rename(columns=FINAL_RENAMING_MAP)
                
                orden_descriptivo = list(FINAL_RENAMING_MAP.values())
                columnas_finales = [col for col in orden_descriptivo if col in datos_vista.columns]
                
                try:
                     idx_fecha = columnas_finales.index(FINAL_RENAMING_MAP[COL_FECHA_KEY])
                     columnas_finales.insert(idx_fecha + 1, COL_FINAL_SEMANA_GRAFICO) 
                except ValueError:
                     columnas_finales.append(COL_FINAL_SEMANA_GRAFICO)
                     
                datos_vista = datos_vista.rename(columns={COL_FINAL_SEMANA_GRAFICO: "SEMANA FIJA (1-5)"})

                columnas_finales = [col for col in columnas_finales if col in datos_vista.columns] 
                datos_vista = datos_vista[columnas_finales]

                st.markdown("---") 

                # MEJORA DE LAYOUT: Ocultar la tabla densa en un expander
                if datos_vista.empty:
                    st.warning("No hay registros que coincidan con la selección de filtros.")
                else:
                    with st.expander(f"📑 Mostrar Tabla de Datos RAW ({len(datos_vista)} registros)", expanded=False):
                        st.info(f"Como {st.session_state.rol}, puedes ver los **{len(datos_vista)}** registros filtrados en su formato original.")
                        
                        # --- NUEVOS CONTROLES DE ORDENAMIENTO ---
                        st.subheader("Opciones de Ordenamiento de la Tabla")
                        
                        col_sort_by, col_sort_order = st.columns([2, 1])
                        
                        # Columnas clave para el ordenamiento
                        sortable_columns = [
                            "FECHA DE FINALIZACIÓN", 
                            "TÉCNICO", 
                            "UBICACIÓN", 
                            "SEMANA FIJA (1-5)",
                            "ORDEN",
                            "TAREA"
                        ]
                        
                        with col_sort_by:
                            sort_column = st.selectbox(
                                "Ordenar por columna:",
                                options=[col for col in sortable_columns if col in datos_vista.columns],
                                index=0, # Por defecto la FECHA DE FINALIZACIÓN
                                key="sort_col"
                            )
                        
                        with col_sort_order:
                            sort_ascending_text = st.radio(
                                "Orden:",
                                options=["Descendente (Z-A, Más reciente)", "Ascendente (A-Z, Más antiguo)"],
                                index=0, # Por defecto Descendente (útil para fechas)
                                key="sort_order_radio"
                            )

                        # Convertir la selección del radio a valor booleano
                        sort_ascending_bool = True if "Ascendente" in sort_ascending_text else False
                        
                        # Aplicar ordenamiento
                        if sort_column in datos_vista.columns:
                            datos_vista_sorted = datos_vista.sort_values(
                                by=sort_column, 
                                ascending=sort_ascending_bool,
                                ignore_index=True,
                                na_position='last' 
                            )
                        else:
                            datos_vista_sorted = datos_vista # Si la columna no se encuentra, no ordenar
                        # --- FIN DE CONTROLES DE ORDENAMIENTO ---
                        
                        st.dataframe(datos_vista_sorted, use_container_width=True)