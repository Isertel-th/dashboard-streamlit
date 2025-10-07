import streamlit as st
import pandas as pd
import os
import plotly.express as px

# --- FUNCIÓN DE COMPACIDAD Y CONFIGURACIÓN ---
def set_page_config_and_style():
    # 1. Configurar layout en modo ancho ("wide") y título
    st.set_page_config(layout="wide", page_title="Estadístico Isertel")
    
    # 2. Custom CSS para máxima compacidad y minimalismo
    st.markdown("""
        <style>
        /* Ahorro vertical general: Reducir padding en el área principal de la aplicación */
        .block-container {
            padding-top: 1rem !important; /* Mínimo arriba */
            padding-bottom: 0rem !important; /* Mínimo abajo */
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Reducir espacio vertical entre st.columns */
        div[data-testid="stHorizontalBlock"] {
            gap: 1rem !important; /* Espacio reducido entre columnas */
        }
        
        /* Reducir padding interno en contenedores (st.container con borde) */
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stContainer"]) > div[data-testid="stContainer"] { 
            padding: 0.5rem !important; 
        }
        
        /* Reducir espacio vertical para todos los títulos (H3, H4, H5) */
        h3, h4, h5 {
            margin-top: 0.5rem !important;
            margin-bottom: 0.3rem !important;
        }

        /* Reducir espacio vertical en los widgets de formulario (select, date, multiselect) */
        .stSelectbox, .stMultiSelect, .stDateInput, div[data-testid="stForm"] {
            margin-bottom: 0.2rem !important;
        }
        
        /* Reducir padding en los st.metric (las tarjetas de KPIs) */
        div[data-testid="stMetric"] {
            padding: 0.5rem 0 !important;
        }

        /* >>> MODIFICACIÓN PARA AUMENTAR EL TAMAÑO DE LAS MÉTRICAS <<< */
        /* Aumenta el valor principal (el número) */
        div[data-testid="stMetricValue"] {
            font-size: 3rem; 
        }
        /* Aumenta la etiqueta/título */
        div[data-testid="stMetricLabel"] {
            font-size: 1.1rem; 
        }
        /* ----------------------------------------------------------- */
        
        /* Ajustar texto de los st.radio para que sea más compacto */
        .st-emotion-cache-1px5e8u p { 
            margin-bottom: 0.1rem;
        }
        
        /* CSS Específico de Header para hacerlo más delgado */
        div[data-testid="stSuccess"] {
            padding: 0.5rem 1rem !important;
            margin-bottom: 0px;
            display: flex;
            justify-content: flex-end; 
        }
        .stButton>button {
            height: 30px;
            padding-top: 5px !important;
            padding-bottom: 5px !important;
        }

        /* ---------------------------------------------------------------------------------- */
        /* >>> SOLUCIÓN ROBUSTA: Empujar TODO el contenido hacia abajo <<< */
        /* Afecta al contenedor principal de Streamlit para liberar el espacio del banner de deploy */
        .main {
            padding-top: 60px !important; 
        }
        /* ---------------------------------------------------------------------------------- */

        /* Ajustar el título principal para que no quede demasiado pegado al header */
        .main [data-testid="stTitle"] {
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }

        /* NUEVO CÓDIGO: Bajar la fila de bienvenida/cerrar sesión AUN MÁS */
        .header-push-down {
            margin-top: 15px !important; /* Se agrega un margen superior al bloque para bajarlo */
        }
        
        </style>
        """, unsafe_allow_html=True) # <--- ¿Falta una comilla o un triple-comilla anterior a esta línea?

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

# --- FUNCIÓN DE COMPARACIÓN POR TÉCNICO ---
@st.cache_data
def prepare_comparison_data(df):
    """
    Prepara el DataFrame para los gráficos de comparación de rendimiento por técnico 
    (REQUIERE FILTRO DE UNA SOLA CIUDAD).
    """
    if df.empty:
        return pd.DataFrame()
    
    df_temp = df.copy()
    
    # 1. Identificación de tipos de órdenes (Instalación vs. Visita Técnica)
    if COL_TIPO_ORDEN_KEY in df_temp.columns:
        # 1 si contiene 'INSTALACION', 0 si no
        df_temp[COL_TIPO_INST] = df_temp[COL_TIPO_ORDEN_KEY].astype(str).str.contains('INSTALACION', case=False, na=False).astype(int)
        # 1 si contiene 'VISITA TÉCNICA', 0 si no
        df_temp[COL_TIPO_VISITA] = df_temp[COL_TIPO_ORDEN_KEY].astype(str).str.contains('VISITA TÉCNICA', case=False, na=False).astype(int)
    else:
        df_temp[COL_TIPO_INST] = 0
        df_temp[COL_TIPO_VISITA] = 0
        
    # 2. Agrupación y Conteo por Técnico dentro de la Ubicación filtrada
    if COL_FILTRO_TECNICO not in df_temp.columns or COL_FILTRO_CIUDAD not in df_temp.columns:
        return pd.DataFrame()

    df_grouped = df_temp.groupby([COL_FILTRO_CIUDAD, COL_FILTRO_TECNICO]).agg(
        Total_Instalaciones=(COL_TIPO_INST, 'sum'),
        Total_Visitas=(COL_TIPO_VISITA, 'sum')
    ).reset_index()

    # 3. Asegurar el tipo de dato y el orden 
    df_grouped['Total_Instalaciones'] = df_grouped['Total_Instalaciones'].astype(int)
    df_grouped['Total_Visitas'] = df_grouped['Total_Visitas'].astype(int)
    
    # Ordenamos por técnico para tener una secuencia de línea fija (como en tu ejemplo)
    df_grouped = df_grouped.sort_values(by=COL_FILTRO_TECNICO) 

    return df_grouped

# --- NUEVA FUNCIÓN PARA COMPARACIÓN POR CIUDAD (SIN FILTROS DE UBICACIÓN INDIVIDUAL) ---
@st.cache_data
def prepare_city_comparison_data(df):
    """
    Prepara el DataFrame para los gráficos de comparación de rendimiento por ciudad 
    (VISTA GLOBAL SIN FILTRO DE UNA SOLA CIUDAD).
    """
    if df.empty:
        return pd.DataFrame()
    
    df_temp = df.copy()
    
    # 1. Identificación de tipos de órdenes (Instalación vs. Visita Técnica)
    if COL_TIPO_ORDEN_KEY in df_temp.columns:
        df_temp[COL_TIPO_INST] = df_temp[COL_TIPO_ORDEN_KEY].astype(str).str.contains('INSTALACION', case=False, na=False).astype(int)
        df_temp[COL_TIPO_VISITA] = df_temp[COL_TIPO_ORDEN_KEY].astype(str).str.contains('VISITA TÉCNICA', case=False, na=False).astype(int)
    else:
        df_temp[COL_TIPO_INST] = 0
        df_temp[COL_TIPO_VISITA] = 0
        
    # 2. Agrupación y Conteo por Ciudad
    if COL_FILTRO_CIUDAD not in df_temp.columns:
        return pd.DataFrame()

    df_grouped = df_temp.groupby([COL_FILTRO_CIUDAD]).agg(
        Total_Instalaciones=(COL_TIPO_INST, 'sum'),
        Total_Visitas=(COL_TIPO_VISITA, 'sum')
    ).reset_index()

    # 3. Asegurar el tipo de dato y el orden 
    df_grouped['Total_Instalaciones'] = df_grouped['Total_Instalaciones'].astype(int)
    df_grouped['Total_Visitas'] = df_grouped['Total_Visitas'].astype(int)
    
    # Ordenamos por ciudad para tener una secuencia de línea fija
    df_grouped = df_grouped.sort_values(by=COL_FILTRO_CIUDAD) 

    return df_grouped

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
    # --- Interfaz Principal (CABECERA SUPERIOR DERECHA, DELGADA Y ANCHA) ---
    
    # 1. El CSS de compacidad ya está en set_page_config_and_style()
    
    # NUEVO: Abrir un bloque con la clase CSS para bajar la fila
    st.markdown('<div class="header-push-down">', unsafe_allow_html=True)
    
    # 2. Usamos columnas para colocar el mensaje y el botón en la esquina superior derecha
    col_spacer, col_welcome, col_logout = st.columns([8, 2, 1]) 

    with col_welcome:
        # st.success para el mensaje de bienvenida (se aplica el CSS de compacidad)
        st.success(f"Bienvenido {st.session_state.usuario} ({st.session_state.rol})")
        
    with col_logout:
        # El botón de cerrar sesión
        st.button(
            "Cerrar sesión", 
            on_click=lambda: st.session_state.update({"login": False, "rol": None, "usuario": None}), 
            key="logout_btn",
            use_container_width=True
        )

    # NUEVO: Cerrar el bloque
    st.markdown('</div>', unsafe_allow_html=True)

    # El título principal se mantiene en el cuerpo
    st.title("📊 Estadístico Isertel")

    # --- LÓGICA DE CARGA Y COMBINACIÓN DE DATOS ---
    archivos_para_combinar_nombres = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.xlsx', '.xls', '.csv'))]
    num_archivos_cargados = len(archivos_para_combinar_nombres)
    datos = None

    df_list = []
    
    if archivos_para_combinar_nombres: 
        # Mover la info de archivos cargados al cuerpo principal
        st.info(f"💾 **{num_archivos_cargados}** archivo(s) cargado(s) y combinado(s).")
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
        # Mover la advertencia de no archivos cargados al cuerpo principal
        st.warning("⚠️ No hay archivos cargados.")
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

    # ----------------------------------------------------------------------
    # --- PESTAÑA DEL DASHBOARD (Optimización de Layout) ---
    # ----------------------------------------------------------------------
    with tab_dashboard:
        if datos is None or datos.empty:
            st.warning("No hay datos para mostrar.")
        else:
            
            # 1. PREPARACIÓN DE DATOS BASE Y CONVERSIÓN DE FECHA (Lógica Preservada)
            datos_filtrados = datos.copy() 
            
            datos_filtrados[COL_TEMP_DATETIME] = pd.to_datetime(datos_filtrados[COL_FECHA_KEY], errors='coerce')
            
            datos_filtrados.dropna(subset=[COL_TEMP_DATETIME], inplace=True)
            
            if datos_filtrados.empty:
                st.warning("No hay registros válidos con fechas de finalización para mostrar después de la limpieza.")
                pass 
            else: # Solo si hay datos válidos, procedemos con filtros y gráficos
                
                # --- Contenedor de Filtros (MÁXIMA HORIZONTALIDAD) ---
                with st.container(border=True): 
                    
                    # Título compacto (H4 en lugar de st.subheader)
                    st.markdown("#### 📅 Filtros por Fechas y Segmentación") 
                    
                    # Usamos st.columns para distribuir los filtros horizontalmente en el banner
                    col_desde, col_hasta, col_ciu, col_tec = st.columns([1.5, 1.5, 2, 2]) 

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

                    # --- PRE-PROCESAMIENTO PARA FILTROS (Lógica Preservada) ---
                    if COL_TECNICO_KEY in datos_filtrados.columns:
                        datos_filtrados[COL_FILTRO_TECNICO] = datos_filtrados[COL_TECNICO_KEY].astype(str).apply(clean_tecnico)
                    if COL_CIUDAD_KEY in datos_filtrados.columns:
                        datos_filtrados[COL_FILTRO_CIUDAD] = datos_filtrados[COL_CIUDAD_KEY].astype(str).apply(clean_ciudad)
                    
                    df_all = datos_filtrados.copy()

                    # Funciones internas para multiselect (Lógica Preservada)
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
                    
                    filtro_ciudad_actual = st.session_state.get('multiselect_ubicacion', [])
                    filtro_tecnico_actual = st.session_state.get('multiselect_tecnico', [])

                    df_domain_ciu = apply_filter(df_all, COL_FILTRO_TECNICO, filtro_tecnico_actual)
                    opciones_ciudad = get_multiselect_options(df_domain_ciu, COL_FILTRO_CIUDAD)

                    df_domain_tec = apply_filter(df_all, COL_FILTRO_CIUDAD, filtro_ciudad_actual)
                    opciones_tecnico = get_multiselect_options(df_domain_tec, COL_FILTRO_TECNICO)

                    with col_ciu:
                        # Se ha simplificado el label
                        filtro_ciudad = st.multiselect(
                            f"Seleccionar **{COL_CIUDAD_DESCRIPTIVA}**:", 
                            options=opciones_ciudad,
                            default=filtro_ciudad_actual, 
                            key='multiselect_ubicacion'
                        )
                        
                    with col_tec:
                        # Se ha simplificado el label
                        filtro_tecnico = st.multiselect(
                            f"Seleccionar **{COL_TECNICO_DESCRIPTIVA}**:", 
                            options=opciones_tecnico,
                            default=filtro_tecnico_actual, 
                            key='multiselect_tecnico'
                        )

                    # --- APLICACIÓN FINAL DE FILTROS ---
                    df_final = apply_filter(df_all, COL_FILTRO_CIUDAD, filtro_ciudad)
                    df_final = apply_filter(df_final, COL_FILTRO_TECNICO, filtro_tecnico)
                    
                    datos_filtrados = df_final
                # --- FIN DEL BANNER DE FILTROS ---
                
                st.markdown("---") # Separador visual

                # 4. CÁLCULO Y VISTA DEL MENÚ CONTEXTUAL (Métricas) + TOP 5 PIE CHART
                with st.container(border=True): # <--- CONTENEDOR TIPO TARJETA
                    # Título compacto
                    st.markdown("#### 💡 Métricas Clave y Top Técnicos") 
                    
                    total_registros = len(datos_filtrados)
                    
                    # Cálculos (Lógica Preservada)
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

                    # --- FILA 1: TOTALES Y GRÁFICO ---
                    # 3 columnas para Totales y 1 columna ancha para el Gráfico
                    col_metric_1, col_metric_2, col_metric_3, col_top_tec = st.columns([1.5, 1.5, 1.5, 2.5])

                    with col_metric_1:
                        st.metric(label="📦 Total de Ordenes", value=f"{total_registros:,}")
                    with col_metric_2:
                        # NOTA: Se eliminó el delta para borrar el color verde del porcentaje
                        st.metric(label="✅ Total Instalaciones", value=f"{total_instalaciones:,}")
                    with col_metric_3:
                        # NOTA: Se eliminó el delta para que el formato de las 3 métricas superiores sea idéntico (solo valor y etiqueta)
                        st.metric(label="🛠️ Total Visitas Técnicas", value=f"{total_visitas_tecnicas:,}")
                    
                    # 6. GRÁFICO DE TAREAS POR TÉCNICO (PIE CHART) en la columna ancha
                    with col_top_tec:
                        st.markdown("##### Distribución del Top 5")
                        
                        if COL_FILTRO_TECNICO in datos_filtrados.columns and total_registros > 0:
                            top_tecnicos = datos_filtrados[COL_FILTRO_TECNICO].value_counts().reset_index()
                            top_tecnicos.columns = ['Técnico', 'Total Tareas']
                            top_tecnicos = top_tecnicos.head(5)
                            
                            fig_pie = px.pie(
                                top_tecnicos, 
                                values='Total Tareas', 
                                names='Técnico', 
                                title='Distribución del Top 5',
                                hole=.3, 
                                color_discrete_sequence=px.colors.qualitative.Pastel 
                            )
                            # Ajuste de layout para hacer el gráfico más compacto y alineado
                            fig_pie.update_layout(
                                showlegend=True, # Mantenemos la leyenda visible
                                margin=dict(l=0, r=0, t=20, b=0),
                                height=300 # Altura ajustada
                            ) 
                            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                        else:
                            st.info("Datos insuficientes para Top Técnico.")

                    # --- FILA 2: TASAS DE PORCENTAJE (Bajo los Totales) ---
                    # 3 columnas con el mismo ancho de los totales, y el resto espaciador
                    col_tasa_inst_spacer, col_tasa_inst, col_tasa_visita, col_tasa_spacer = st.columns([1.5, 1.5, 1.5, 2.5]) 
                    
                    # col_tasa_inst_spacer queda vacío

                    with col_tasa_inst:
                        # Tasa de Instalación (VISIBLE y GRANDE)
                        st.metric(label="📈 Tasa de Instalación", value=f"{tasa_instalacion:.1%}") 

                    with col_tasa_visita:
                        # Tasa de Visitas Técnicas (VISIBLE y GRANDE)
                        st.metric(label="📉 Tasa Visitas Técnicas", value=f"{tasa_visitas_tecnicas:.1%}") 
                    
                    # El resto del espacio queda vacío (col_tasa_spacer)

                
                st.markdown("---") # Separador visual

                # --- LAYOUT PRINCIPAL: 2x2 GRÁFICOS (Barra Fija y Comparación) ---
                col_grafico_barra, col_comparacion = st.columns(2) 
                
                # 5. GRÁFICO DE TAREAS REALIZADAS POR SEGMENTO FIJO (COLUMNA IZQUIERDA)
                with col_grafico_barra:
                    with st.container(border=True): # <--- Tarjeta para el Gráfico
                        st.markdown("#### 📊 Tareas Realizadas: Segmentos Fijos")

                        df_escala = pd.DataFrame() 
                        
                        if total_registros > 0:
                            
                            datos_temp = datos_filtrados.copy()
                            # ... (Lógica de preparación de datos para el gráfico de barras - Preservada) ...
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
                            
                            # GENERAR GRÁFICO (Lógica Preservada)
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

                
                # --- SECCIÓN DE GRÁFICOS DE COMPARACIÓN (COLUMNA DERECHA) ---
                with col_comparacion:
                    
                    # LÓGICA DE VISTA: (Preservada)
                    # 1. Si SELECCIONA UNA SOLA CIUDAD: Mostrar Comparación por TÉCNICO dentro de esa ciudad.
                    if len(filtro_ciudad) == 1 and COL_FILTRO_TECNICO in datos_filtrados.columns and len(datos_filtrados[COL_FILTRO_TECNICO].unique()) >= 1:
                        
                        # --- VISTA 1: COMPARACIÓN POR TÉCNICO (2 GRÁFICOS LADO A LADO) ---
                        df_comparacion = prepare_comparison_data(datos_filtrados) # Lógica Preservada
                        
                        if not df_comparacion.empty and (df_comparacion['Total_Instalaciones'].sum() > 0 or df_comparacion['Total_Visitas'].sum() > 0):
                            
                            ciudad_seleccionada = filtro_ciudad[0]
                            st.markdown(f"#### 📊 Rendimiento por **Técnico** en: **{ciudad_seleccionada}**")
                            
                            # Usamos columnas INTERNAS para poner los dos gráficos lado a lado
                            col_inst_tec, col_visita_tec = st.columns(2) 
                            
                            # GRÁFICO 1: COMPARACIÓN DE INSTALACIONES (TÉCNICO)
                            with col_inst_tec:
                                with st.container(border=True):
                                    st.markdown("##### Instalaciones por Técnico") # Título más pequeño
                                    if df_comparacion['Total_Instalaciones'].sum() > 0:
                                        
                                        fig_inst = px.line(
                                            df_comparacion, x=COL_FILTRO_TECNICO, y='Total_Instalaciones',
                                            title='Instalaciones por Técnico', # Título más corto para ahorrar espacio
                                            labels={COL_FILTRO_TECNICO: 'Técnico', 'Total_Instalaciones': 'Instalaciones'},
                                            markers=True, text='Total_Instalaciones', height=300 # Altura reducida
                                        )
                                        
                                        fig_inst.update_layout(xaxis_title='Técnico', yaxis_title='Total de Inst.', uniformtext_minsize=8, uniformtext_mode='hide', margin=dict(t=30, l=10, r=10, b=10)) 
                                        fig_inst.update_traces(textposition="top center") 
                                        
                                        st.plotly_chart(fig_inst, use_container_width=True)
                                    else:
                                        st.info("No hay **Instalaciones** registradas.")
                            
                            # GRÁFICO 2: COMPARACIÓN DE VISITAS TÉCNICAS (TÉCNICO)
                            with col_visita_tec:
                                with st.container(border=True):
                                    st.markdown("##### Visitas Técnicas por Técnico") # Título más pequeño
                                    if df_comparacion['Total_Visitas'].sum() > 0:
                                        
                                        fig_visita = px.line(
                                            df_comparacion, x=COL_FILTRO_TECNICO, y='Total_Visitas',
                                            title='Visitas Técnicas por Técnico', # Título más corto para ahorrar espacio
                                            labels={COL_FILTRO_TECNICO: 'Técnico', 'Total_Visitas': 'Visitas Técnicas'},
                                            markers=True, text='Total_Visitas', height=300 # Altura reducida
                                        )
                                        
                                        fig_visita.update_layout(xaxis_title='Técnico', yaxis_title='Total de Visitas', uniformtext_minsize=8, uniformtext_mode='hide', margin=dict(t=30, l=10, r=10, b=10)) 
                                        fig_visita.update_traces(textposition="top center") 
                                        
                                        st.plotly_chart(fig_visita, use_container_width=True)
                                    else:
                                        st.info("No hay **Visitas Técnicas** registradas.")
                                        
                        else:
                            st.info("💡 No hay datos de Instalaciones o Visitas Técnicas para mostrar en la comparación por técnico con los filtros aplicados.")
                                
                    else: 
                        # --- VISTA 2: COMPARACIÓN POR CIUDAD (2 GRÁFICOS LADO A LADO) ---
                        df_comparacion_city = prepare_city_comparison_data(datos_filtrados) # Lógica Preservada
                        
                        if not df_comparacion_city.empty and (df_comparacion_city['Total_Instalaciones'].sum() > 0 or df_comparacion_city['Total_Visitas'].sum() > 0):
                            
                            st.markdown("#### 📊 Rendimiento por **Ubicación/Ciudad**")
                            
                            # Usamos columnas INTERNAS para poner los dos gráficos lado a lado
                            col_inst_city, col_visita_city = st.columns(2)
                            
                            # GRÁFICO 1: COMPARACIÓN DE INSTALACIONES (CIUDAD)
                            with col_inst_city:
                                with st.container(border=True):
                                    st.markdown("##### Instalaciones por Ciudad") # Título más pequeño
                                    if df_comparacion_city['Total_Instalaciones'].sum() > 0:
                                        
                                        fig_inst_city = px.line(
                                            df_comparacion_city, x=COL_FILTRO_CIUDAD, y='Total_Instalaciones',
                                            title='Instalaciones por Ciudad',
                                            labels={COL_FILTRO_CIUDAD: 'Ciudad', 'Total_Instalaciones': 'Instalaciones'},
                                            markers=True, text='Total_Instalaciones', height=300
                                        )
                                        
                                        fig_inst_city.update_layout(xaxis_title='Ubicación/Ciudad', yaxis_title='Total de Inst.', uniformtext_minsize=8, uniformtext_mode='hide', margin=dict(t=30, l=10, r=10, b=10)) 
                                        fig_inst_city.update_traces(textposition="top center") 
                                        
                                        st.plotly_chart(fig_inst_city, use_container_width=True)
                                    else:
                                        st.info("No hay **Instalaciones** registradas.")
                            
                            # GRÁFICO 2: COMPARACIÓN DE VISITAS TÉCNICAS (CIUDAD)
                            with col_visita_city:
                                with st.container(border=True):
                                    st.markdown("##### Visitas Técnicas por Ciudad") # Título más pequeño
                                    if df_comparacion_city['Total_Visitas'].sum() > 0:
                                        
                                        fig_visita_city = px.line(
                                            df_comparacion_city, x=COL_FILTRO_CIUDAD, y='Total_Visitas',
                                            title='Visitas Técnicas por Ciudad',
                                            labels={COL_FILTRO_CIUDAD: 'Ciudad', 'Total_Visitas': 'Visitas Técnicas'},
                                            markers=True, text='Total_Visitas', height=300
                                        )
                                        
                                        fig_visita_city.update_layout(xaxis_title='Ubicación/Ciudad', yaxis_title='Total de Visitas', uniformtext_minsize=8, uniformtext_mode='hide', margin=dict(t=30, l=10, r=10, b=10)) 
                                        fig_visita_city.update_traces(textposition="top center") 
                                        
                                        st.plotly_chart(fig_visita_city, use_container_width=True)
                                    else:
                                        st.info("No hay **Visitas Técnicas** registradas.")

                            st.info("💡 Selecciona **una ubicación** para ver la comparación de rendimiento por técnico.")
                            
                        else:
                            st.info("💡 No hay datos de Instalaciones o Visitas Técnicas para mostrar en la comparación por ciudad con los filtros aplicados.")

                # --- FIN DE GRÁFICOS DE COMPARACIÓN ---
                            
                st.markdown("---") # Separador visual

                # 7. TABLA DE RESULTADOS RAW (OCULTA EN UN EXPANDER)
                
                # PREPARACIÓN FINAL DE LA TABLA (Lógica Preservada)
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

                # MEJORA DE LAYOUT: Ocultar la tabla densa en un expander
                if datos_vista.empty:
                    st.warning("No hay registros que coincidan con la selección de filtros.")
                else:
                    with st.expander(f"📑 Mostrar Tabla de Datos RAW ({len(datos_vista)} registros)", expanded=False):
                        st.info(f"Como {st.session_state.rol}, puedes ver los **{len(datos_vista)}** registros filtrados en su formato original.")
                        
                        # --- CONTROLES DE ORDENAMIENTO (COMPACTOS) ---
                        st.markdown("##### Opciones de Ordenamiento de la Tabla") # Título más pequeño
                        
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
                            # Se usa st.radio para mejor compacidad
                            sort_ascending_text = st.radio(
                                "Orden:",
                                options=["Descendente (Z-A, Más reciente)", "Ascendente (A-Z, Más antiguo)"],
                                index=0, # Por defecto Descendente (útil para fechas)
                                key="sort_order_radio"
                            )

                        # Convertir la selección del radio a valor booleano
                        sort_ascending_bool = True if "Ascendente" in sort_ascending_text else False
                        
                        # Aplicar ordenamiento (Lógica Preservada)
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