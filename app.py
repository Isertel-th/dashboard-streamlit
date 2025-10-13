import streamlit as st 
import pandas as pd 
import os 
import plotly.express as px 
import numpy as np

# --- FUNCIÓN DE COMPACIDAD Y CONFIGURACIÓN --- 
def set_page_config_and_style(): 
# 1. Configurar layout en modo ancho ("wide") y título 
    st.set_page_config(layout="wide", page_title="Estadístico Isertel")

# 2. Custom CSS para máxima compacidad y minimalismo (AJUSTES AGRESIVOS)
    st.markdown(""" 
    <style> 
    /* Ahorro vertical general: Reducir padding en el área principal de la aplicación */ 
    .block-container { 
        padding-top: 4rem !important; 
        padding-bottom: 0rem !important; 
        padding-left: 1rem !important; 
        padding-right: 1rem !important; 
    }

    /* Reducir espacio vertical entre st.columns */ 
    div[data-testid="stHorizontalBlock"] { 
        gap: 0.75rem !important; /* Espacio reducido entre columnas */ 
    }

    /* Reducir padding interno en contenedores (st.container con borde) */ 
    div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stContainer"]) > div[data-testid="stContainer"] { 
        padding: 0.5rem !important; 
    }

    /* Reducir espacio vertical para todos los títulos (MÁS AGRESIVO) */ 
    h3, h4, h5 { 
        margin-top: 0.1rem !important; /* De 0.5 a 0.1 */
        margin-bottom: 0.1rem !important; /* De 0.3 a 0.1 */
    }
    
    /* Reducir margen de la línea horizontal */
    hr {
        margin-top: 0.1rem !important;
        margin-bottom: 0.1rem !important;
    }

    /* Reducir espacio en los widgets de formulario (MÁS AGRESIVO) */ 
    .stSelectbox, .stMultiSelect, .stDateInput, div[data-testid="stForm"] { 
        margin-bottom: 0.0rem !important; /* De 0.1 a 0.0 */
    }

    /* Reducir padding en los st.metric (las tarjetas de KPIs) */ 
    div[data-testid="stMetric"] { 
        padding: 0.2rem 0 !important; 
    }

    /* Tamaño estándar de las métricas */ 
    div[data-testid="stMetricLabel"] { 
        font-size: 1rem; 
    }

    /* ESTILOS ESPECÍFICOS PARA LAS NUEVAS MÉTRICAS COMPACTAS */

    /* Contenedor de las métricas que contiene el valor */ 
    .metric-compact-container div[data-testid="stMetricValue"] { 
        font-size: 1.8rem; 
        color: #B71C1C; 
    } 
    .metric-compact-container-total div[data-testid="stMetricValue"] { 
        font-size: 1.8rem; 
        color: #0D47A1; 
    }

    /* Estilo para los valores de porcentaje */ 
    .percentage-value-compact div[data-testid="stMetricValue"] { 
        font-size: 1.8rem; 
        font-weight: bold; 
        color: #1E88E5; 
    } 
    .percentage-value-compact div[data-testid="stMetricLabel"] { 
        font-size: 1rem; 
        color: #1E88E5; 
    }

    /* Oculta los deltas estándar */ 
    div[data-testid="stMetricDelta"] { 
        visibility: hidden; 
        height: 0; 
    }

    /* ----------------------------------------------------------- */

    /* CSS Específico de Header para hacerlo más delgado */ 
    div[data-testid="stSuccess"] { 
        padding: 0.5rem 1rem !important; 
        margin-bottom: 0px; 
        display: flex; 
        justify-content: flex-end;
        align-items: center; 
        height: 100%; 
    } 
    .stButton>button { 
        height: 30px; 
        padding-top: 5px !important; 
        padding-bottom: 5px !important; 
    }

    /* Estilo para que el st.data_editor sea lo más compacto posible */ 
    .stDataFrame { 
        margin-top: 0.5rem; 
    } 
    .stDataFrame .css-1dp5fcv { 
        padding: 0.2rem 0.5rem; 
    } 
    .stDataFrame .css-1dp5fcv button { 
        padding: 0.1rem 0.4rem; 
        font-size: 0.8rem; 
    }
    </style> 
    """, unsafe_allow_html=True)

# Llama a la función al inicio de tu script 
set_page_config_and_style()

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

# --- Nuevas columnas para los Gráficos de Comparación --- 
COL_SEGM_TIEMPO = '_SEGM_AÑO_MES_' 
COL_TIPO_INST = '_ES_INSTALACION_' 
COL_TIPO_VISITA = '_ES_VISITA_'

# --- FUNCIONES DE LIMPIEZA PARA FILTROS --- 
@st.cache_data 
def clean_tecnico(tecnico): 
    """Extrae el nombre del técnico después del '|'.""" 
    if isinstance(tecnico, str) and '|' in tecnico: 
        return tecnico.split('|', 1)[1].strip() 
    return str(tecnico).strip()

@st.cache_data 
def clean_ciudad(ciudad): 
    """Extrae la ciudad antes de la primera ','.""" 
    if isinstance(ciudad, str) and ',' in ciudad: 
        return ciudad.split(',', 1)[0].strip() 
    return str(ciudad).strip()

# --- FUNCIÓN DE SEGMENTACIÓN FIJA SOLICITADA (AJUSTADA A 5 DÍAS) --- 
@st.cache_data 
def calculate_fixed_week(day): 
    """ Calcula el número de segmento (1-7) basado en el día del mes, usando 5 días por segmento (1-5, 6-10, 11-15, 16-20, 21-25, 26-30, 31). """ 
    if day <= 5: 
        return 1 
    elif day <= 10: 
        return 2 
    elif day <= 15: 
        return 3 
    elif day <= 20: 
        return 4 
    elif day <= 25: 
        return 5 
    elif day <= 30: 
        return 6 
    else: # 31 
        return 7

# --- FUNCIONES DE COMPARACIÓN (Reposiciones eliminadas) --- 
@st.cache_data 
def prepare_comparison_data(df): 
    if df.empty: 
        return pd.DataFrame()

    df_temp = df.copy()

    if COL_TIPO_ORDEN_KEY in df_temp.columns: 
        tipo_orden = df_temp[COL_TIPO_ORDEN_KEY].astype(str)
        df_temp[COL_TIPO_INST] = tipo_orden.str.contains('INSTALACION', case=False, na=False).astype(int) 
        df_temp[COL_TIPO_VISITA] = tipo_orden.str.contains('VISITA TÉCNICA', case=False, na=False).astype(int)
    else: 
        df_temp[COL_TIPO_INST] = 0 
        df_temp[COL_TIPO_VISITA] = 0

    if COL_FILTRO_TECNICO not in df_temp.columns or COL_FILTRO_CIUDAD not in df_temp.columns: 
        return pd.DataFrame()

    # Se agrupa por CIUDAD y TÉCNICO
    df_grouped = df_temp.groupby([COL_FILTRO_CIUDAD, COL_FILTRO_TECNICO]).agg( 
        Total_Instalaciones=(COL_TIPO_INST, 'sum'), 
        Total_Visitas=(COL_TIPO_VISITA, 'sum'),
    ).reset_index()

    df_grouped['Total_Instalaciones'] = df_grouped['Total_Instalaciones'].astype(int) 
    df_grouped['Total_Visitas'] = df_grouped['Total_Visitas'].astype(int)

    return df_grouped.sort_values(by=COL_FILTRO_TECNICO)

@st.cache_data 
def prepare_city_comparison_data(df): 
    if df.empty: 
        return pd.DataFrame()

    df_temp = df.copy()

    if COL_TIPO_ORDEN_KEY in df_temp.columns: 
        tipo_orden = df_temp[COL_TIPO_ORDEN_KEY].astype(str)
        df_temp[COL_TIPO_INST] = tipo_orden.str.contains('INSTALACION', case=False, na=False).astype(int) 
        df_temp[COL_TIPO_VISITA] = tipo_orden.str.contains('VISITA TÉCNICA', case=False, na=False).astype(int)
    else: 
        df_temp[COL_TIPO_INST] = 0 
        df_temp[COL_TIPO_VISITA] = 0

    if COL_FILTRO_CIUDAD not in df_temp.columns: 
        return pd.DataFrame()

    # Se agrupa solo por CIUDAD 
    df_grouped = df_temp.groupby([COL_FILTRO_CIUDAD]).agg( 
        Total_Instalaciones=(COL_TIPO_INST, 'sum'), 
        Total_Visitas=(COL_TIPO_VISITA, 'sum'),
    ).reset_index()

    df_grouped['Total_Instalaciones'] = df_grouped['Total_Instalaciones'].astype(int) 
    df_grouped['Total_Visitas'] = df_grouped['Total_Visitas'].astype(int)

    return df_grouped.sort_values(by=COL_FILTRO_CIUDAD)

# --- LECTURA DE USUARIOS (sin cambios) ---
try: 
    usuarios_df = pd.read_excel(USUARIOS_EXCEL) 
    usuarios_df['Usuario'] = usuarios_df['Usuario'].astype(str).str.strip() 
    usuarios_df['Contraseña'] = usuarios_df['Contraseña'].astype(str).str.strip() 
    usuarios_df['Rol'] = usuarios_df['Rol'].astype(str).str.strip() 
except FileNotFoundError: 
    usuarios_data = { 
        'Usuario': ['admin', 'user'], 
        'Contraseña': ['12345', 'password'], 
        'Rol': ['admin', 'analyst'] 
    } 
    usuarios_df = pd.DataFrame(usuarios_data) 

# --- SESSION STATE (sin cambios) --- 
if 'login' not in st.session_state: 
    st.session_state.login = False 
if 'rol' not in st.session_state: 
    st.session_state.rol = None 
if 'usuario' not in st.session_state: 
    st.session_state.usuario = None

# --- LOGIN / INTERFAZ PRINCIPAL (sin cambios) --- 
if not st.session_state.login: 
    st.title("📊 Estadístico Isertel - Login") 
    st.subheader("Inicia sesión para acceder")

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
    # --- Interfaz Principal (CABECERA ALINEADA Y BAJADA) (sin cambios) --- 
    
    col_title, col_spacer, col_welcome, col_logout = st.columns([4, 4, 2, 1]) 

    with col_title:
        st.markdown("## 📊 Estadístico Isertel") 

    with col_welcome: 
        st.success(f"Bienvenido {st.session_state.usuario} ({st.session_state.rol})", icon=None) 

    with col_logout: 
        st.button( 
            "Cerrar sesión", 
            on_click=lambda: st.session_state.update({"login": False, "rol": None, "usuario": None}), 
            key="logout_btn", 
            use_container_width=True 
        )

    # --- LÓGICA DE CARGA Y COMBINACIÓN DE DATOS (sin cambios) --- 
    archivos_para_combinar_nombres = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.xlsx', '.xls', '.csv'))] 
    num_archivos_cargados = len(archivos_para_combinar_nombres) 
    datos = None 
    df_list = []

    if archivos_para_combinar_nombres: 
        st.info(f"💾 **{num_archivos_cargados}** archivo(s) cargado(s) y combinado(s).") 
        archivos_completos = [os.path.join(UPLOAD_FOLDER, f) for f in archivos_para_combinar_nombres]

        try: 
            total_columnas_mapeadas = 0 
            for f in archivos_completos: 
                # 1. Intentar leer el archivo (manejando CSVs y encodings) 
                try: 
                    df = pd.read_csv(f, encoding='latin1') if f.lower().endswith('.csv') else pd.read_excel(f) 
                except UnicodeDecodeError: 
                    try: 
                        df = pd.read_csv(f, encoding='utf-8') 
                    except Exception as csv_err: 
                        st.warning(f"No se pudo leer {f} (Error CSV/UTF-8: {csv_err}). Saltando archivo.") 
                        continue 
                except Exception as e: 
                    st.warning(f"No se pudo leer {f} (Error general: {e}). Saltando archivo.") 
                    continue

                # 2. Limpiar y des-duplicar nombres de columnas 
                cleaned_names = [] 
                name_counts = {} 
                for name in df.columns: 
                    cleaned_name = str(name).upper().strip() 
                    name_counts[cleaned_name] = name_counts.get(cleaned_name, 0) + 1 
                    if name_counts[cleaned_name] > 1: 
                        cleaned_name = f"{cleaned_name}_{name_counts[cleaned_name]}" 
                    cleaned_names.append(cleaned_name) 
                df.columns = cleaned_names

                # 3. Mapear columnas al formato interno y manejar el error de asignación 
                df_temp = pd.DataFrame() 
                columnas_encontradas_en_archivo = 0 
                for encabezado_excel, columna_final in MAPEO_COLUMNAS.items(): 
                    if encabezado_excel in df.columns: 
                        columna_data = df[encabezado_excel]

                        # --- CORRECCIÓN PARA EL ERROR DE ASIGNACIÓN (Cannot set a DataFrame...) --- 
                        if isinstance(columna_data, pd.DataFrame): 
                            columna_data = columna_data.iloc[:, 0]

                        # Manejo de múltiples columnas con el mismo nombre (ej. si existió duplicidad y se corrigió con el sufijo) 
                        if encabezado_excel in df.columns: 
                            df_temp[columna_final] = columna_data 
                            columnas_encontradas_en_archivo += 1

                if not df_temp.empty: 
                    df_temp = df_temp.reindex(columns=COLUMNAS_SELECCIONADAS, fill_value=None) 
                    df_list.append(df_temp) 
                    total_columnas_mapeadas += columnas_encontradas_en_archivo

            if df_list: 
                datos = pd.concat(df_list, ignore_index=True)

            if datos is None or datos.empty or total_columnas_mapeadas == 0: 
                st.warning("No se encontraron columnas mapeables en los archivos cargados.") 
                datos = None

        except Exception as e: 
            st.error(f"Error al combinar archivos: {e}") 
            datos = None

    if datos is None: 
        try: 
            datos = pd.read_excel(MASTER_EXCEL) 
            columnas_existentes = [col for col in COLUMNAS_SELECCIONADAS if col in datos.columns] 
            datos = datos[columnas_existentes] 
        except: 
            data = { 
                'A': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110] * 10, 
                'B': [f'O{i}' for i in range(100)], 
                'F': ['Finalizada'] * 100, 
                'G': ['INSTALACION', 'VISITA TÉCNICA', 'REPOSICION', 'INSTALACION', 'VISITA TÉCNICA'] * 20, 
                'O': ['Bogotá, 123', 'Bogotá, 456', 'Cali, 123', 'Cali, 456', 'Bogotá, 789', 'Medellín, 123', 'Medellín, 456', 'Medellín, 789', 'Cali, 789', 'Bogotá, 123'] * 10, 
                'P': ['T|Juan Pérez', 'T|Juan Pérez', 'T|Pedro López', 'T|Pedro López', 'T|Ana Gómez', 'T|Ana Gómez', 'T|Juan Pérez', 'T|Juan Pérez', 'T|Pedro López', 'T|Ana Gómez'] * 10, 
                'Q': ['C1']*100, 
                'R': ['Cliente A']*100, 
                'T': pd.to_datetime([f'2025-10-{d:02d}' for d in range(1, 11)] * 10) 
            } 
            datos = pd.DataFrame(data) 
            columnas_dummy = list(data.keys()) 
            datos = datos.rename(columns={k: v for k, v in MAPEO_COLUMNAS.items() if k in columnas_dummy}) 
            datos.columns = COLUMNAS_SELECCIONADAS

    if not archivos_para_combinar_nombres: 
        st.warning("Usando **Datos de Prueba** para mostrar la interfaz. Sube un archivo Excel para ver datos reales.")

    # --- Estructura con PESTAÑAS (sin cambios) --- 
    tabs = ["📊 Dashboard", "⚙️ Administración de Datos"] 
    if st.session_state.rol.lower() == "admin": 
        tab_dashboard, tab_admin = st.tabs(tabs) 
    else: 
        tab_dashboard = st.tabs(["📊 Dashboard"])[0] 
        tab_admin = None

    if st.session_state.rol.lower() == "admin" and tab_admin: 
        with tab_admin: 
            # ... (código de administración sin cambios) ...
            st.header("⚙️ Administración de Archivos Fuente") 
            st.metric(label="Documentos Excel/CSV Cargados", value=f"{num_archivos_cargados} archivos") 
            st.markdown("---")

            col_upload, col_delete = st.columns(2)

            with col_upload: 
                st.subheader("Subir y Añadir Archivos") 
                nuevos_archivos = st.file_uploader("Subir archivos", type=["xlsx", "xls", "csv"], accept_multiple_files=True) 
                if st.button("📤 Guardar archivos"): 
                    if nuevos_archivos: 
                        for f in nuevos_archivos: 
                            file_path = os.path.join(UPLOAD_FOLDER, f.name) 
                            if not os.path.exists(file_path): 
                                with open(file_path, "wb") as file: 
                                    file.write(f.getbuffer()) 
                                st.success(f"Archivo '{f.name}' guardado.") 
                            else: 
                                st.warning(f"Archivo '{f.name}' ya existe. No se sobreescribió.")

                    st.info("Recargando la aplicación para aplicar cambios...") 
                    st.rerun()

            with col_delete: 
                st.subheader("Eliminar Archivos") 
                archivos_actuales = os.listdir(UPLOAD_FOLDER)

                eliminar = st.multiselect("Selecciona archivos a eliminar", archivos_actuales) 
                if st.button("🗑️ Eliminar seleccionados"): 
                    if eliminar: 
                        for f in eliminar: 
                            os.remove(os.path.join(UPLOAD_FOLDER, f)) 
                        st.success(f"{len(eliminar)} archivos eliminados. Recargando...") 
                        st.rerun()

                if archivos_actuales and st.button("🔴 Eliminar TODOS los archivos", type="primary"): 
                    for f in archivos_actuales: 
                        os.remove(os.path.join(UPLOAD_FOLDER, f)) 
                    if os.path.exists(MASTER_EXCEL): 
                        os.remove(MASTER_EXCEL) 
                    st.success(f"Todos los archivos eliminados. Recargando...") 
                    st.rerun()

            st.markdown("---")

    # ---------------------------------------------------------------------- 
    # --- PESTAÑA DEL DASHBOARD --- 
    # ---------------------------------------------------------------------- 
    with tab_dashboard: 
        if datos is None or datos.empty: 
            st.warning("No hay datos para mostrar.") 
        else:
            # 1. PREPARACIÓN DE DATOS BASE (sin cambios)
            datos_filtrados = datos.copy() 
            datos_filtrados[COL_TEMP_DATETIME] = pd.to_datetime(datos_filtrados[COL_FECHA_KEY], errors='coerce') 
            datos_filtrados.dropna(subset=[COL_TEMP_DATETIME], inplace=True)

            if datos_filtrados.empty: 
                st.warning("No hay registros con fechas válidas para mostrar.") 
            else:
                
                # Definiciones necesarias para los filtros (dentro del contexto del dashboard)
                @st.cache_data 
                def get_multiselect_options(df, col_key_filtro): 
                    if col_key_filtro not in df.columns: 
                        return [] 
                    opciones = sorted([v for v in df[col_key_filtro].astype(str).unique() if pd.notna(v) and str(v).strip() not in ('nan', 'none', '')]) 
                    return opciones

                @st.cache_data 
                def apply_filter(df, col_key_filtro, selected_options): 
                    if not selected_options or col_key_filtro not in df.columns: 
                        return df 
                    return df[df[col_key_filtro].astype(str).isin(selected_options)]
                    
                # Función auxiliar para renderizar los gráficos de comparación (APILADOS VERTICALMENTE)
                def render_comparison_charts_vertical(df_comparacion, x_col, title_prefix, is_city_view=False):
                    # El título del grupo de gráficos (Rendimiento por Técnico o Ubicación)
                    st.markdown(f"#### Rendimiento {title_prefix}")
                    
                    # Gráfico 1: Instalaciones (APILADO - Se usa la nueva altura reducida de 120)
                    with st.container(border=True):
                        st.markdown("##### Instalaciones")
                        fig_inst = px.line(df_comparacion, x=x_col, y='Total_Instalaciones', markers=True, text='Total_Instalaciones', height=120) # ALTURA REDUCIDA
                        fig_inst.update_layout(
                            xaxis_title=None, 
                            yaxis_title='Total', 
                            margin=dict(t=20,b=10,l=10,r=10),
                            xaxis={'tickangle': -45 if not is_city_view else 0}
                        )
                        st.plotly_chart(fig_inst, use_container_width=True)

                    # Gráfico 2: Visitas (APILADO - Se usa la nueva altura reducida de 120)
                    with st.container(border=True):
                        st.markdown("##### Visitas")
                        fig_vis = px.line(df_comparacion, x=x_col, y='Total_Visitas', markers=True, text='Total_Visitas', height=120) # ALTURA REDUCIDA
                        fig_vis.update_layout(
                            xaxis_title=None, 
                            yaxis_title='Total', 
                            margin=dict(t=20,b=10,l=10,r=10),
                            xaxis={'tickangle': -45 if not is_city_view else 0}
                        )
                        st.plotly_chart(fig_vis, use_container_width=True)
                        
                
                # --- INICIO DEL PANEL DE CONTROL COMPACTO (Filtros y Métricas) --- 
                with st.container(border=True):
                    
                    # --- DECLARACIÓN ÚNICA DE COLUMNAS (1 Fila Horizontal) --- 
                    # Orden: [Fecha Desde, Fecha Hasta, Ubicación, Técnico, Total Abs., Total %, Inst. Abs., Inst. %, Vis. Abs., Vis. %]
                    col_desde, col_hasta, col_ciu, col_tec, col_m_total_abs, col_m_total_tasa, col_m_inst_abs, col_m_inst_tasa, col_m_vis_abs, col_m_vis_tasa = st.columns(
                        [1.0, 1.0, 1.5, 1.5, 1.5, 0.5, 1.5, 1.0, 1.5, 1.0]
                    )

                    # Lógica de Fechas (Filtrado) - Se mantiene en las primeras 2 columnas
                    with col_desde: 
                        min_date_global = datos_filtrados[COL_TEMP_DATETIME].min().replace(hour=0, minute=0, second=0, microsecond=0) 
                        max_date_global = datos_filtrados[COL_TEMP_DATETIME].max().replace(hour=0, minute=0, second=0, microsecond=0) 
                        date_from = st.date_input("Desde:", value=min_date_global, min_value=min_date_global, max_value=max_date_global, key='filter_date_from')
                    
                    with col_hasta: 
                        date_to = st.date_input("Hasta:", value=max_date_global, min_value=min_date_global, max_value=max_date_global, key='filter_date_to')
                    
                    if date_from > date_to: 
                        st.error("⚠️ La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'.") 
                        st.stop()
                    
                    filtro_inicio = pd.to_datetime(date_from) 
                    filtro_fin = pd.to_datetime(date_to) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)

                    datos_filtrados = datos_filtrados[ 
                        (datos_filtrados[COL_TEMP_DATETIME] >= filtro_inicio) & 
                        (datos_filtrados[COL_TEMP_DATETIME] <= filtro_fin) 
                    ].copy()
                    
                    # PRE-PROCESAMIENTO PARA FILTROS DE SEGMENTACIÓN 
                    if COL_TECNICO_KEY in datos_filtrados.columns: 
                        datos_filtrados[COL_FILTRO_TECNICO] = datos_filtrados[COL_TECNICO_KEY].astype(str).apply(clean_tecnico) 
                    if COL_CIUDAD_KEY in datos_filtrados.columns: 
                        datos_filtrados[COL_FILTRO_CIUDAD] = datos_filtrados[COL_CIUDAD_KEY].astype(str).apply(clean_ciudad)

                    df_all = datos_filtrados.copy()
                    
                    filtro_ciudad_actual = st.session_state.get('multiselect_ubicacion', []) 
                    filtro_tecnico_actual = st.session_state.get('multiselect_tecnico', [])

                    df_domain_ciu = apply_filter(df_all, COL_FILTRO_TECNICO, filtro_tecnico_actual) 
                    opciones_ciudad = get_multiselect_options(df_domain_ciu, COL_FILTRO_CIUDAD)

                    df_domain_tec = apply_filter(df_all, COL_FILTRO_CIUDAD, filtro_ciudad_actual) 
                    opciones_tecnico = get_multiselect_options(df_domain_tec, COL_FILTRO_TECNICO)
                    
                    # --- CÁLCULO DE MÉTRICAS CLAVE (antes de su renderizado) --- 
                    total_registros = len(datos_filtrados) 
                    if COL_TIPO_ORDEN_KEY in datos_filtrados.columns: 
                        tipo_orden = datos_filtrados[COL_TIPO_ORDEN_KEY].astype(str)
                        total_instalaciones = len(datos_filtrados[tipo_orden.str.contains('INSTALACION', case=False, na=False)]) 
                        total_visitas_tecnicas = len(datos_filtrados[tipo_orden.str.contains('VISITA TÉCNICA', case=False, na=False)])
                    else: 
                        total_instalaciones, total_visitas_tecnicas = 0, 0 

                    # CÁLCULO DE PORCENTAJES
                    porc_instalaciones = (total_instalaciones / total_registros) * 100 if total_registros > 0 else 0 
                    porc_visitas = (total_visitas_tecnicas / total_registros) * 100 if total_registros > 0 else 0
                    
                    # --- RENDERIZADO DE FILTROS DE SEGMENTACIÓN (Ubicación y Técnico) ---
                    with col_ciu:
                        filtro_ciudad = st.multiselect(f"**{COL_CIUDAD_DESCRIPTIVA}**:", options=opciones_ciudad, default=filtro_ciudad_actual, key='multiselect_ubicacion')

                    with col_tec:
                        filtro_tecnico = st.multiselect(f"**{COL_TECNICO_DESCRIPTIVA}**:", options=opciones_tecnico, default=filtro_tecnico_actual, key='multiselect_tecnico')


                    # --- RENDERIZADO DE MÉTRICAS COMPACTAS (Absolutos y Tasas) --- 
                    
                    # Columna para Total Órdenes (Absoluto)
                    with col_m_total_abs: 
                        st.markdown('<div class="metric-compact-container-total">', unsafe_allow_html=True) 
                        st.metric(label="Total Ordenes", value=f"{total_registros:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Columna para Espacio (Tasa Total - no aplica)
                    with col_m_total_tasa: 
                        st.markdown('<div class="percentage-value-compact">', unsafe_allow_html=True) 
                        st.metric(label=" ", value=" ") 
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Columna para Instalaciones (Absoluto)
                    with col_m_inst_abs: 
                        st.markdown('<div class="metric-compact-container">', unsafe_allow_html=True) 
                        st.metric(label="Instalaciones", value=f"{total_instalaciones:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Columna para Instalaciones (Tasa)
                    with col_m_inst_tasa: 
                        st.markdown('<div class="percentage-value-compact">', unsafe_allow_html=True) 
                        st.metric(label="Tasa %", value=f"{porc_instalaciones:.1f}%") 
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Columna para Visitas Téc. (Absoluto)
                    with col_m_vis_abs: 
                        st.markdown('<div class="metric-compact-container">', unsafe_allow_html=True) 
                        st.metric(label="Visitas Téc.", value=f"{total_visitas_tecnicas:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Columna para Visitas Téc. (Tasa)
                    with col_m_vis_tasa: 
                        st.markdown('<div class="percentage-value-compact">', unsafe_allow_html=True) 
                        st.metric(label="Tasa %", value=f"{porc_visitas:.1f}%") 
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # APLICACIÓN FINAL DE FILTROS DE SEGMENTACIÓN 
                    df_final = apply_filter(df_all, COL_FILTRO_CIUDAD, filtro_ciudad) 
                    df_final = apply_filter(df_final, COL_FILTRO_TECNICO, filtro_tecnico) 
                    datos_filtrados = df_final
                # --- FIN DEL PANEL DE CONTROL COMPACTO ---

                st.markdown("---")
                
                # ------------------------------------------------------------------------------------- 
                # --- LAYOUT PRINCIPAL: DOS COLUMNAS (RAW vs. GRÁFICOS) --- 
                # ------------------------------------------------------------------------------------- 
                # Dividimos el espacio en dos columnas: 
                # Columna 1 (izquierda): Tabla RAW (ancho 5) 
                # Columna 2 (derecha): Todos los gráficos apilados verticalmente (ancho 15)
                col_raw, col_graphs_group = st.columns([5, 15]) 

                # ------------------------------------------------------------------------------------- 
                # --- COLUMNA 1: TABLA DE DATOS RAW (IZQUIERDA) --- 
                # -------------------------------------------------------------------------------------
                with col_raw:
                    st.markdown(f"#### 📑 Datos RAW ({len(datos_filtrados)} registros)")

                    # Preparamos la vista de datos 
                    datos_vista = datos_filtrados.rename(columns=FINAL_RENAMING_MAP) 
                    columnas_finales = [col for col in FINAL_RENAMING_MAP.values() if col in datos_vista.columns] 
                    datos_vista = datos_vista[columnas_finales]

                    # 1. Selector de Columnas 
                    all_cols = datos_vista.columns.tolist() 
                    default_cols = [FINAL_RENAMING_MAP['O'], FINAL_RENAMING_MAP['T'], FINAL_RENAMING_MAP['P'], FINAL_RENAMING_MAP['G']]

                    cols_to_show = st.multiselect( 
                        "**Columnas a mostrar**:", 
                        options=all_cols, 
                        default=default_cols, 
                        key='raw_table_col_select_narrow'
                    )

                    df_to_display = datos_vista[cols_to_show] if cols_to_show else datos_vista

                    # 2. Implementación de overflow horizontal 
                    st.markdown('<div style="overflow-x: auto;">', unsafe_allow_html=True) 
                    st.data_editor( 
                        df_to_display, 
                        use_container_width=True, 
                        hide_index=True, 
                        key='editable_raw_data_narrow', 
                        column_config={ 
                            col: st.column_config.Column( 
                                width="small" 
                            ) for col in df_to_display.columns 
                        }, 
                        num_rows="fixed" 
                    ) 
                    st.markdown('</div>', unsafe_allow_html=True)

                # ------------------------------------------------------------------------------------- 
                # --- COLUMNA 2: GRUPO DE GRÁFICOS (DERECHA) --- 
                # -------------------------------------------------------------------------------------
                with col_graphs_group: 
                    
                    # 1. Primera Fila de Gráficos (Anidada)
                    col_graphs_izq, col_graphs_der = st.columns([8, 7])

                    # --- GRÁFICO TAREAS POR SEGMENTO --- 
                    with col_graphs_izq: 
                        with st.container(border=True): 
                            st.markdown("#### Tareas por Segmento (5 días)")

                            if total_registros > 0: 
                                datos_temp = datos_filtrados.copy() 
                                datos_temp['DAY'] = datos_temp[COL_TEMP_DATETIME].dt.day 
                                datos_temp['MONTH'] = datos_temp[COL_TEMP_DATETIME].dt.month 
                                datos_temp['YEAR'] = datos_temp[COL_TEMP_DATETIME].dt.year 
                                # Usa la función AJUSTADA de 5 días por segmento 
                                datos_temp['FIXED_WEEK'] = datos_temp['DAY'].apply(calculate_fixed_week) 
                                datos_temp[COL_SEGM_TIEMPO] = datos_temp['YEAR'].astype(str) + '-' + datos_temp['MONTH'].astype(str).str.zfill(2) + '-' + datos_temp['FIXED_WEEK'].astype(str).str.zfill(2)

                                conteo_segmentos = datos_temp.groupby(COL_SEGM_TIEMPO).size().reset_index(name='Total_Tareas')

                                df_escala = conteo_segmentos.sort_values(by=COL_SEGM_TIEMPO, ascending=True)

                                def get_segment_range(year_month_segm): 
                                    parts = year_month_segm.split('-') 
                                    if len(parts) != 3: return "Inválido" 
                                    try: 
                                        week_num, month_num, year = int(parts[2]), int(parts[1]), parts[0] 
                                    except ValueError: return "Inválido"

                                    ranges = { 
                                        1: 'S1 (1-5)', 2: 'S2 (6-10)', 3: 'S3 (11-15)', 4: 'S4 (16-20)', 
                                        5: 'S5 (21-25)', 6: 'S6 (26-30)', 7: 'S7 (31)' 
                                    } 
                                    month_name = pd.to_datetime(f"{month_num}", format='%m').strftime('%b') 
                                    return f"{ranges.get(week_num, f'S{week_num}')} {month_name}/{year[-2:]}"

                                df_escala['Segmento_Label'] = df_escala[COL_SEGM_TIEMPO].apply(get_segment_range)

                                fig = px.bar( 
                                    df_escala, 
                                    x='Segmento_Label', 
                                    y='Total_Tareas', 
                                    text='Total_Tareas', 
                                    color_discrete_sequence=['#4CAF50'] 
                                ) 
                                fig.update_layout( 
                                    uniformtext_minsize=8, uniformtext_mode='hide', 
                                    xaxis_title=None, 
                                    yaxis_title='Tareas', 
                                    margin=dict(t=20, b=10, l=10, r=10), 
                                    height=250, # ALTURA REDUCIDA
                                    xaxis={'tickangle': -45}
                                ) 
                                fig.update_traces(textposition='outside') 
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}) 
                            else: 
                                st.info("No hay datos para el gráfico semanal.")

                    # --- GRÁFICO TOP 5 TÉCNICOS --- 
                    with col_graphs_der: 
                        with st.container(border=True): 
                            st.markdown("#### Top 5 Técnicos") 
                            if COL_FILTRO_TECNICO in datos_filtrados.columns and total_registros > 0: 
                                top_tecnicos = datos_filtrados[COL_FILTRO_TECNICO].value_counts().head(5).reset_index() 
                                top_tecnicos.columns = ['Técnico', 'Total Tareas']

                                fig_pie = px.pie(top_tecnicos, values='Total Tareas', names='Técnico', hole=.4, color_discrete_sequence=px.colors.qualitative.Pastel) 
                                fig_pie.update_layout(showlegend=True, margin=dict(l=0, r=0, t=20, b=0), height=250) # ALTURA REDUCIDA
                                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False}) 
                            else: 
                                st.info("Datos insuficientes para Top Técnico.")
                    
                    
                    # *************************************************************************************
                    # *** SECCIÓN: RENDIMIENTO DINÁMICO (ALTURA REDUCIDA) ***
                    # *************************************************************************************
                    st.markdown("---") # Separador para la nueva sección
                    st.markdown("### 📈 Rendimiento Detallado de Órdenes")

                    # Contenedor principal para la sección de rendimiento
                    with st.container(border=True): 
                        
                        show_comparison_by_technician = (len(filtro_ciudad) == 1 and COL_FILTRO_TECNICO in datos_filtrados.columns)

                        if show_comparison_by_technician:
                            df_comparacion = prepare_comparison_data(datos_filtrados) 
                            if not df_comparacion.empty: 
                                render_comparison_charts_vertical( 
                                    df_comparacion, 
                                    COL_FILTRO_TECNICO, 
                                    f"por Técnico en: **{filtro_ciudad[0]}**", 
                                    is_city_view=False 
                                ) 
                            else:
                                st.info("No hay datos de rendimiento por técnico en la ubicación seleccionada.")
                        
                        else:
                            df_comparacion_city = prepare_city_comparison_data(datos_filtrados)
                            if not df_comparacion_city.empty:
                                render_comparison_charts_vertical(
                                    df_comparacion_city, 
                                    COL_FILTRO_CIUDAD, 
                                    "por Ubicación", 
                                    is_city_view=True
                                )
                            else:
                                st.info("No hay datos para la comparación por ubicación con los filtros actuales.")
                    # *************************************************************************************