import streamlit as st 
import pandas as pd 
import os 
import plotly.express as px 
import numpy as np
from datetime import datetime, timedelta 

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
    'FECHA': 'A', 
    'UBICACIÓN': 'B', 
    'TÉCNICO': 'C', 
    'CONTRATO': 'D', 
    'CLIENTE': 'E', 
    'TECNOLOGÍA': 'F',
    'TAREA': 'G', 
    'ESTADO TAREA': 'H',
    'TIPO DE ORDEN': 'I' 
}
# 💥 FIN NUEVO MAPEO 💥

COLUMNAS_SELECCIONADAS = list(MAPEO_COLUMNAS.values()) 
ENCABEZADOS_ESPERADOS = list(MAPEO_COLUMNAS.keys())

# 2. DEFINICIÓN DEL MAPEO INVERSO (Letra Corta -> Nombre Descriptivo) 
FINAL_RENAMING_MAP = {v: k for k, v in MAPEO_COLUMNAS.items()} 

# 💥 CORRECCIÓN DE CLAVES DE COLUMNA A LAS NUEVAS LETRAS 💥
COL_FECHA_KEY = 'A' 
COL_TECNICO_KEY = 'C' 
COL_CIUDAD_KEY = 'B' 
COL_TIPO_ORDEN_KEY = 'I'
COL_ESTADO_KEY = 'H' 
COL_CONTRATO_KEY = 'D'
COL_CLIENTE_KEY = 'E'
COL_TAREA_KEY = 'G'
COL_TECNOLOGIA_KEY = 'F'
# 💥 FIN CORRECCIÓN 💥

COL_FECHA_DESCRIPTIVA = FINAL_RENAMING_MAP[COL_FECHA_KEY] 
COL_TEMP_DATETIME = '_DATETIME_' + COL_FECHA_KEY 
COL_FINAL_SEMANA_GRAFICO = 'SEMANA_DE_GRÁFICO'

# Columnas clave para los filtros 
COL_TECNICO_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_TECNICO_KEY, 'TÉCNICO') 
COL_CIUDAD_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_CIUDAD_KEY, 'UBICACIÓN') 
COL_TIPO_ORDEN_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_TIPO_ORDEN_KEY, 'TIPO DE ORDEN')
COL_ESTADO_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_ESTADO_KEY, 'ESTADO TAREA')
COL_TECNOLOGIA_DESCRIPTIVA = FINAL_RENAMING_MAP.get(COL_TECNOLOGIA_KEY, 'TECNOLOGÍA')

# --- Nuevas columnas temporales para el filtrado limpio --- 
COL_FILTRO_TECNICO = '_Filtro_Tecnico_' 
COL_FILTRO_CIUDAD = '_Filtro_Ubicacion_'
COL_FILTRO_ESTADO = '_Filtro_Estado_' 
COL_FILTRO_TIPO_ORDEN = '_Filtro_TipoOrden_'
COL_FILTRO_TECNOLOGIA = '_Filtro_Tecnologia_'

# --- Nuevas columnas para los Gráficos de Comparación --- 
COL_SEGM_TIEMPO = '_SEGM_AÑO_MES_' 
COL_TIPO_INST = '_ES_INSTALACION_' 
COL_TIPO_VISITA = '_ES_VISITA_'
COL_TIPO_MIGRACION = '_ES_MIGRACION_'
COL_TIPO_MANUAL = '_ES_TAREA_MANUAL_'
COL_TIPO_CAMBIO_DIR = '_ES_CAMBIO_DIRECCION_'


# --- FUNCIONES DE LIMPIEZA PARA FILTROS (sin cambios) --- 
@st.cache_data 
def clean_tecnico(tecnico): 
    """
    Extrae el nombre del técnico después del '|' y elimina '(tecnico)' al final.
    """ 
    s = str(tecnico).strip()

    # 1. Extraer lo que está después del '|'
    if '|' in s: 
        s = s.split('|', 1)[1].strip() 

    # 2. Eliminar la cadena ' (tecnico)' al final (insensible a mayúsculas/minúsculas)
    suffix = ' (tecnico)'
    if s.lower().endswith(suffix):
        # Eliminamos el sufijo del texto original (manteniendo el case si no era el sufijo)
        s = s[:-len(suffix)]

    return s.strip() # Devolver el resultado final limpio

@st.cache_data 
def clean_ciudad(ciudad): 
    """Extrae la ciudad antes de la primera ','.""" 
    if isinstance(ciudad, str) and ',' in ciudad: 
        return ciudad.split(',', 1)[0].strip() 
    return str(ciudad).strip()

# --- FUNCIÓN DE SEGMENTACIÓN FIJA SOLICITADA (AJUSTADA A 5 DÍAS) (sin cambios) --- 
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

# --- FUNCIONES DE COMPARACIÓN --- 
@st.cache_data 
def prepare_comparison_data(df): 
    # Mantiene la agrupación por [CIUDAD, TÉCNICO] para permitir filtrado por una sola ciudad
    if df.empty: 
        return pd.DataFrame()

    df_temp = df.copy()

    if COL_TIPO_ORDEN_KEY in df_temp.columns: 
        tipo_orden = df_temp[COL_TIPO_ORDEN_KEY].astype(str)
        df_temp[COL_TIPO_INST] = tipo_orden.str.contains('INSTALACION', case=False, na=False).astype(int) 
        df_temp[COL_TIPO_VISITA] = tipo_orden.str.contains('VISITA TECNICA', case=False, na=False).astype(int)
        
        # --- CORRECCIÓN DE DETECCIÓN DE TILDES CON REGEX ---
        df_temp[COL_TIPO_MIGRACION] = tipo_orden.str.contains(r'MIGRACI[ÓO]N', case=False, na=False, regex=True).astype(int)
        df_temp[COL_TIPO_MANUAL] = tipo_orden.str.contains('TAREA MANUAL', case=False, na=False).astype(int)
        df_temp[COL_TIPO_CAMBIO_DIR] = tipo_orden.str.contains(r'CAMBIO DE DIRECCI[ÓO]N', case=False, na=False, regex=True).astype(int)
        # --- FIN CORRECCIÓN ---
    else: 
        df_temp[COL_TIPO_INST] = 0 
        df_temp[COL_TIPO_VISITA] = 0
        df_temp[COL_TIPO_MIGRACION] = 0
        df_temp[COL_TIPO_MANUAL] = 0
        df_temp[COL_TIPO_CAMBIO_DIR] = 0

    if COL_FILTRO_TECNICO not in df_temp.columns or COL_FILTRO_CIUDAD not in df_temp.columns: 
        return pd.DataFrame()

    # Se agrupa por CIUDAD y TÉCNICO
    df_grouped = df_temp.groupby([COL_FILTRO_CIUDAD, COL_FILTRO_TECNICO]).agg( 
        Total_Instalaciones=(COL_TIPO_INST, 'sum'), 
        Total_Visitas=(COL_TIPO_VISITA, 'sum'),
        # Agregamos las nuevas métricas 
        Total_Migracion=(COL_TIPO_MIGRACION, 'sum'),
        Total_TareaManual=(COL_TIPO_MANUAL, 'sum'),
        Total_CambioDireccion=(COL_TIPO_CAMBIO_DIR, 'sum'),
        # Columna Total_Tareas para cualquier uso futuro, incluyendo la vista
        Total_Tareas=(COL_TIPO_INST, 'count') # Contar todas las filas en el grupo
    ).reset_index()

    df_grouped['Total_Instalaciones'] = df_grouped['Total_Instalaciones'].astype(int) 
    df_grouped['Total_Visitas'] = df_grouped['Total_Visitas'].astype(int)
    df_grouped['Total_Migracion'] = df_grouped['Total_Migracion'].astype(int)
    df_grouped['Total_TareaManual'] = df_grouped['Total_TareaManual'].astype(int)
    df_grouped['Total_CambioDireccion'] = df_grouped['Total_CambioDireccion'].astype(int)
    df_grouped['Total_Tareas'] = df_grouped['Total_Tareas'].astype(int) # Asegurar el tipo

    return df_grouped.sort_values(by=COL_FILTRO_TECNICO)

@st.cache_data 
def prepare_city_comparison_data(df): 
    if df.empty: 
        return pd.DataFrame()

    df_temp = df.copy()

    if COL_TIPO_ORDEN_KEY in df_temp.columns: 
        tipo_orden = df_temp[COL_TIPO_ORDEN_KEY].astype(str)
        df_temp[COL_TIPO_INST] = tipo_orden.str.contains('INSTALACION', case=False, na=False).astype(int) 
        df_temp[COL_TIPO_VISITA] = tipo_orden.str.contains('VISITA TECNICA', case=False, na=False).astype(int)
        
        # --- CORRECCIÓN DE DETECCIÓN DE TILDES CON REGEX ---
        # Match 'MIGRACION' o 'MIGRACIÓN' (case-insensitive)
        df_temp[COL_TIPO_MIGRACION] = tipo_orden.str.contains(r'MIGRACI[ÓO]N', case=False, na=False, regex=True).astype(int)
        df_temp[COL_TIPO_MANUAL] = tipo_orden.str.contains('TAREA MANUAL', case=False, na=False).astype(int)
        # Match 'CAMBIO DE DIRECCION' o 'CAMBIO DE DIRECCIÓN' (case-insensitive)
        df_temp[COL_TIPO_CAMBIO_DIR] = tipo_orden.str.contains(r'CAMBIO DE DIRECCI[ÓO]N', case=False, na=False, regex=True).astype(int)
        # --- FIN CORRECCIÓN ---
    else: 
        df_temp[COL_TIPO_INST] = 0 
        df_temp[COL_TIPO_VISITA] = 0
        df_temp[COL_TIPO_MIGRACION] = 0
        df_temp[COL_TIPO_MANUAL] = 0
        df_temp[COL_TIPO_CAMBIO_DIR] = 0

    if COL_FILTRO_CIUDAD not in df_temp.columns: 
        return pd.DataFrame()

    # Se agrupa solo por CIUDAD 
    df_grouped = df_temp.groupby([COL_FILTRO_CIUDAD]).agg( 
        Total_Instalaciones=(COL_TIPO_INST, 'sum'), 
        Total_Visitas=(COL_TIPO_VISITA, 'sum'),
        # Agregamos las nuevas métricas 
        Total_Migracion=(COL_TIPO_MIGRACION, 'sum'),
        Total_TareaManual=(COL_TIPO_MANUAL, 'sum'),
        Total_CambioDireccion=(COL_TIPO_CAMBIO_DIR, 'sum'),
    ).reset_index()

    df_grouped['Total_Instalaciones'] = df_grouped['Total_Instalaciones'].astype(int) 
    df_grouped['Total_Visitas'] = df_grouped['Total_Visitas'].astype(int)
    # Convertimos a int 
    df_grouped['Total_Migracion'] = df_grouped['Total_Migracion'].astype(int)
    df_grouped['Total_TareaManual'] = df_grouped['Total_TareaManual'].astype(int)
    df_grouped['Total_CambioDireccion'] = df_grouped['Total_CambioDireccion'].astype(int)

    return df_grouped.sort_values(by=COL_FILTRO_CIUDAD)

# Función auxiliar para renderizar los gráficos de comparación (APILADOS VERTICALMENTE) (sin cambios)
def render_comparison_charts_vertical(df_comparacion, x_col, title_prefix, is_city_view=False):
    # Definición de los gráficos a renderizar
    chart_configs = [
        {'col_name': 'Total_Instalaciones', 'title': 'Instalaciones', 'color': '#4CAF50'},
        {'col_name': 'Total_Visitas', 'title': 'Visitas', 'color': '#FF9800'},
        # Nuevos gráficos
        {'col_name': 'Total_Migracion', 'title': 'Migración', 'color': '#2196F3'},
        {'col_name': 'Total_TareaManual', 'title': 'Tarea Manual', 'color': '#9C27B0'},
        {'col_name': 'Total_CambioDireccion', 'title': 'Cambio de Dirección', 'color': '#F44336'}
    ]

    # El título del grupo de gráficos (Rendimiento por Técnico o Ubicación)
    st.markdown(f"#### Rendimiento {title_prefix} (Base Dinámica)")
    
    bottom_margin = 60
    CHART_HEIGHT = 200 
    
    # La configuración del eje X ahora rota las etiquetas siempre a -45 grados.
    xaxis_config = {
        'tickangle': -45, 
        'tickfont': {'size': 9 if not is_city_view else 10} 
    }

    # CONFIGURACIÓN DE LAS LÍNEAS DE REJIDA VERTICALES DISCONTINUAS (PUNTEADAS) 
    grid_config = {
        'showgrid': True,
        'gridcolor': '#cccccc',  # Un color gris claro para la rejilla
        'griddash': 'dot'       # Tipo de línea: 'dot' (punteada)
    }

    # Iteramos sobre la nueva configuración de gráficos
    for config in chart_configs:
        with st.container(border=True):
            st.markdown(f"##### {config['title']}")
            
            # Usamos la nueva altura
            fig = px.line(
                df_comparacion, 
                x=x_col, 
                y=config['col_name'], 
                markers=True, 
                text=config['col_name'], 
                height=CHART_HEIGHT,
                color_discrete_sequence=[config['color']]
            ) 
            
            # Mostrar el texto permanentemente encima del punto
            fig.update_traces(textposition='top center') 
            
            fig.update_layout(
                xaxis_title=None, 
                yaxis_title='Total', 
                # Margen inferior corregido a 60px
                margin=dict(t=20,b=bottom_margin,l=10,r=10), 
                xaxis=xaxis_config # Aplicamos la configuración rotada
            )
            # Aplicamos la configuración de rejilla vertical
            fig.update_xaxes(**grid_config)
            # Desactivamos las líneas horizontales (rejilla Y)
            fig.update_yaxes(showgrid=False) 
            st.plotly_chart(fig, use_container_width=True)


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

# --- LOGIN / INTERFAZ PRINCIPAL (con imagen) (sin cambios) --- 
if not st.session_state.login: 
    
    # MODIFICACIÓN APLICADA: Cabecera con Imagen y Título 
    # Definir columnas para la cabecera de Login (Imagen, Título, Espaciador)
    # Se usan las mismas proporciones relativas para imagen y título que en el dashboard: [0.8, 3.8, ...]
    col_img_login, col_title_login, col_spacer_login = st.columns([0.8, 3.8, 6.2]) 

    # Columna para la Imagen de Login
    with col_img_login:
        IMAGE_PATH = "logge.png" 
        if os.path.exists(IMAGE_PATH):
            # Carga la imagen con el mismo ancho (100px)
            st.image(IMAGE_PATH, width=100) 
        else:
            # Espacio vacío si la imagen no se encuentra, para mantener la alineación
            st.markdown("&nbsp;") 

    # Columna para el Título de Login
    with col_title_login:
        # Usar el estilo para asegurar la alineación vertical con la imagen
        st.markdown("<h2 style='margin-top:0.5rem; margin-left: -0.5rem;'>📊 Estadístico Isertel</h2>", unsafe_allow_html=True) 

    # Subtítulo de bienvenida (debajo de la cabecera)
    st.subheader("Inicia sesión para acceder")

    # Definir las columnas para el formulario de login (centrado)
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
    
    # MODIFICACIÓN: Se añade una columna para la imagen ('logge.png').
    # Orden: [Imagen, Título, Espaciador, Bienvenida, Logout]
    col_img, col_title, col_spacer, col_welcome, col_logout = st.columns([0.8, 3.8, 3, 2, 1]) 
    
    # Columna para la Imagen
    with col_img:
        IMAGE_PATH = "logge.png" # Usando el nombre de archivo solicitado
        if os.path.exists(IMAGE_PATH):
            # Carga la imagen y la ajusta a un tamaño pequeño
            st.image(IMAGE_PATH, width=100) # Ajusta el ancho según necesites
        else:
            # Si no se encuentra la imagen, deja un espacio o un marcador
            st.markdown("&nbsp;") # Espacio vacío para mantener la alineación

    with col_title:
        # Usamos estilo para asegurar la alineación vertical con la imagen
        st.markdown("<h2 style='margin-top:0.5rem; margin-left: -0.5rem;'>📊 Estadístico Isertel</h2>", unsafe_allow_html=True) 

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
            # 💥 DATOS DE PRUEBA ACTUALIZADOS PARA EL NUEVO MAPEO (A-I) 💥
            data = { 
                'ID_TAREA': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110] * 10, # Usado como TAREA (G)
                'TECNOLOGIA_COL': ['ADSL', 'ADSL', 'HFC', 'HFC', 'GPON', 'GPON', 'ADSL', 'HFC', 'GPON', 'ADSL'] * 10, # Usado como TECNOLOGÍA (F)
                # IMPORTANTE: Usamos SATISFACTORIA e INSATISFACTORIA para probar la corrección de conteo
                'ESTADO': ['SATISFACTORIA', 'Pendiente', 'INSATISFACTORIA', 'SATISFACTORIA', 'Pendiente', 'INSATISFACTORIA', 'SATISFACTORIA', 'Pendiente', 'INSATISFACTORIA', 'SATISFACTORIA'] * 10, # Usado como ESTADO (H)
                'TIPO_ORDEN': ['INSTALACION', 'VISITA TECNICA', 'MIGRACIÓN', 'TAREA MANUAL', 'CAMBIO DE DIRECCIÓN', 'OTRO TIPO', 'INSTALACION', 'VISITA TECNICA', 'MIGRACIÓN', 'TAREA MANUAL'] * 10, # Usado como TIPO_ORDEN (I)
                'UBICACION': ['Bogotá, 123', 'Bogotá, 456', 'Cali, 123', 'Cali, 456', 'Bogotá, 789', 'Medellín, 123', 'Medellín, 456', 'Medellín, 789', 'Cali, 789', 'Bogotá, 123'] * 10, # Usado como UBICACIÓN (B)
                'TECNICO': ['T|Juan Pérez (tecnico)', 'T|Juan Pérez (tecnico)', 'T|Pedro López (tecnico)', 'T|Pedro López', 'T|Ana Gómez (tecnico)', 'T|Ana Gómez', 'T|Juan Pérez (tecnico)', 'T|Juan Pérez', 'T|Pedro López (tecnico)', 'T|Ana Gómez (tecnico)'] * 10, # Usado como TÉCNICO (C)
                'CONTRATO': ['C1']*100,                                              # Usado como CONTRATO (D)
                'CLIENTE': ['Cliente A']*100,                                         # Usado como CLIENTE (E)
                'FECHA': pd.to_datetime([f'2025-10-{d:02d}' for d in range(1, 11)] * 10) # Usado como FECHA (A)
            } 
            datos = pd.DataFrame(data) 
            
            # Renombramiento a las claves A-I
            RENAME_DUMMY = {
                'FECHA': 'A', 'UBICACION': 'B', 'TECNICO': 'C', 'CONTRATO': 'D', 'CLIENTE': 'E', 
                'TECNOLOGIA_COL': 'F', 'ID_TAREA': 'G', 'ESTADO': 'H', 'TIPO_ORDEN': 'I'
            }
            datos = datos.rename(columns=RENAME_DUMMY)
            datos.columns = COLUMNAS_SELECCIONADAS # Aseguramos el orden y las columnas finales
            # 💥 FIN DATOS DE PRUEBA ACTUALIZADOS 💥

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
                    # Importante: Si selected_options está vacío, devolver el DF completo (comportamiento de filtro limpio)
                    if not selected_options:
                        return df
                    if col_key_filtro not in df.columns: 
                        return df 
                    return df[df[col_key_filtro].astype(str).isin(selected_options)]
                    
                # Se mantiene la función render_comparison_charts_vertical aquí por si el usuario la copia

                # -----------------------------------------------------------------------------
                # --- INICIO DEL PANEL DE CONTROL COMPACTO (1/2): FILTROS --- 
                # -----------------------------------------------------------------------------
                with st.container(border=True):
                    st.markdown("#### ⚙️ Filtros de Segmentación") # Título para la caja de filtros
                    
                    # Redefinición de 7 columnas para los FILTROS
                    col_desde, col_hasta, col_ciu, col_tec, col_est, col_tipo_orden, col_tecnologia = st.columns(
                        [1.0, 1.0, 1.3, 1.3, 1.3, 1.3, 1.3] # 7 columnas para los filtros
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

                    # Estandarizar la columna de ESTADO (H)
                    if COL_ESTADO_KEY in datos_filtrados.columns:
                        datos_filtrados[COL_FILTRO_ESTADO] = datos_filtrados[COL_ESTADO_KEY].astype(str).str.upper().str.strip()
                        datos_filtrados[COL_FILTRO_ESTADO].fillna("SIN ESTADO", inplace=True) 
                    
                    # Estandarizar la columna de TIPO DE ORDEN (I)
                    if COL_TIPO_ORDEN_KEY in datos_filtrados.columns:
                        datos_filtrados[COL_FILTRO_TIPO_ORDEN] = datos_filtrados[COL_TIPO_ORDEN_KEY].astype(str).str.upper().str.strip()
                        datos_filtrados[COL_FILTRO_TIPO_ORDEN].fillna("SIN TIPO", inplace=True) 
                    
                    # Estandarizar la columna de TECNOLOGÍA (F)
                    if COL_TECNOLOGIA_KEY in datos_filtrados.columns:
                        datos_filtrados[COL_FILTRO_TECNOLOGIA] = datos_filtrados[COL_TECNOLOGIA_KEY].astype(str).str.upper().str.strip()
                        datos_filtrados[COL_FILTRO_TECNOLOGIA].fillna("SIN TECNOLOGIA", inplace=True) 
                    
                    df_all = datos_filtrados.copy()
                    
                    # 💥 MANTENER FILTROS SELECCIONADOS EN SESSION STATE 💥
                    filtro_ciudad_actual = st.session_state.get('multiselect_ubicacion', []) 
                    filtro_tecnico_actual = st.session_state.get('multiselect_tecnico', [])
                    filtro_estado_actual = st.session_state.get('multiselect_estado', []) 
                    filtro_tipo_orden_actual = st.session_state.get('multiselect_tipo_orden', []) 
                    filtro_tecnologia_actual = st.session_state.get('multiselect_tecnologia', []) 

                    # --- DEFINICIÓN DE DOMINIOS DINÁMICOS (CASCADA) ---
                    
                    # Dominios base para los cálculos
                    df_domain_base = df_all.copy()
                    
                    # Dominio CIUDAD
                    df_domain_ciu = apply_filter(df_domain_base, COL_FILTRO_TECNICO, filtro_tecnico_actual)
                    df_domain_ciu = apply_filter(df_domain_ciu, COL_FILTRO_ESTADO, filtro_estado_actual)
                    df_domain_ciu = apply_filter(df_domain_ciu, COL_FILTRO_TIPO_ORDEN, filtro_tipo_orden_actual) 
                    df_domain_ciu = apply_filter(df_domain_ciu, COL_FILTRO_TECNOLOGIA, filtro_tecnologia_actual) 
                    opciones_ciudad = get_multiselect_options(df_domain_ciu, COL_FILTRO_CIUDAD)

                    # Dominio TÉCNICO
                    df_domain_tec = apply_filter(df_domain_base, COL_FILTRO_CIUDAD, filtro_ciudad_actual)
                    df_domain_tec = apply_filter(df_domain_tec, COL_FILTRO_ESTADO, filtro_estado_actual)
                    df_domain_tec = apply_filter(df_domain_tec, COL_FILTRO_TIPO_ORDEN, filtro_tipo_orden_actual) 
                    df_domain_tec = apply_filter(df_domain_tec, COL_FILTRO_TECNOLOGIA, filtro_tecnologia_actual) 
                    opciones_tecnico = get_multiselect_options(df_domain_tec, COL_FILTRO_TECNICO)

                    # Dominio ESTADO
                    df_domain_est = apply_filter(df_domain_base, COL_FILTRO_CIUDAD, filtro_ciudad_actual)
                    df_domain_est = apply_filter(df_domain_est, COL_FILTRO_TECNICO, filtro_tecnico_actual)
                    df_domain_est = apply_filter(df_domain_est, COL_FILTRO_TIPO_ORDEN, filtro_tipo_orden_actual) 
                    df_domain_est = apply_filter(df_domain_est, COL_FILTRO_TECNOLOGIA, filtro_tecnologia_actual) 
                    opciones_estado = get_multiselect_options(df_domain_est, COL_FILTRO_ESTADO)

                    # Dominio TIPO DE ORDEN 
                    df_domain_tipo_orden = apply_filter(df_domain_base, COL_FILTRO_CIUDAD, filtro_ciudad_actual)
                    df_domain_tipo_orden = apply_filter(df_domain_tipo_orden, COL_FILTRO_TECNICO, filtro_tecnico_actual)
                    df_domain_tipo_orden = apply_filter(df_domain_tipo_orden, COL_FILTRO_ESTADO, filtro_estado_actual)
                    df_domain_tipo_orden = apply_filter(df_domain_tipo_orden, COL_FILTRO_TECNOLOGIA, filtro_tecnologia_actual) 
                    opciones_tipo_orden = get_multiselect_options(df_domain_tipo_orden, COL_FILTRO_TIPO_ORDEN) 

                    # Dominio TECNOLOGÍA 
                    df_domain_tecnologia = apply_filter(df_domain_base, COL_FILTRO_CIUDAD, filtro_ciudad_actual)
                    df_domain_tecnologia = apply_filter(df_domain_tecnologia, COL_FILTRO_TECNICO, filtro_tecnico_actual)
                    df_domain_tecnologia = apply_filter(df_domain_tecnologia, COL_FILTRO_ESTADO, filtro_estado_actual)
                    df_domain_tecnologia = apply_filter(df_domain_tecnologia, COL_FILTRO_TIPO_ORDEN, filtro_tipo_orden_actual) 
                    opciones_tecnologia = get_multiselect_options(df_domain_tecnologia, COL_FILTRO_TECNOLOGIA) 
                    
                    # --- RENDERIZADO DE FILTROS DE SEGMENTACIÓN (Ubicación, Técnico, ESTADO, TIPO ORDEN, TECNOLOGÍA) ---
                    with col_ciu:
                        filtro_ciudad = st.multiselect(
                            f"**{COL_CIUDAD_DESCRIPTIVA}**:", 
                            options=opciones_ciudad, 
                            default=filtro_ciudad_actual, 
                            key='multiselect_ubicacion',
                            placeholder="Ciudad"
                        )

                    with col_tec:
                        filtro_tecnico = st.multiselect(
                            f"**{COL_TECNICO_DESCRIPTIVA}**:", 
                            options=opciones_tecnico, 
                            default=filtro_tecnico_actual, 
                            key='multiselect_tecnico',
                            placeholder="Código"
                        )

                    with col_est:
                        filtro_estado = st.multiselect(
                            f"**{COL_ESTADO_DESCRIPTIVA}**:", 
                            options=opciones_estado, 
                            default=filtro_estado_actual, 
                            key='multiselect_estado',
                            placeholder="Estado"
                        )

                    # RENDERIZADO: Tipo de Orden 
                    with col_tipo_orden:
                        filtro_tipo_orden = st.multiselect(
                            f"**{COL_TIPO_ORDEN_DESCRIPTIVA}**:", 
                            options=opciones_tipo_orden, 
                            default=filtro_tipo_orden_actual, 
                            key='multiselect_tipo_orden',
                            placeholder="Tipo Orden"
                        )

                    # RENDERIZADO: Tecnología 
                    with col_tecnologia:
                        filtro_tecnologia = st.multiselect(
                            f"**{COL_TECNOLOGIA_DESCRIPTIVA}**:", 
                            options=opciones_tecnologia, 
                            default=filtro_tecnologia_actual, 
                            key='multiselect_tecnologia',
                            placeholder="Tecnología"
                        )
                        
                    # APLICACIÓN FINAL DE FILTROS DE SEGMENTACIÓN 
                    # Se aplican los filtros de multiselect al DataFrame ya filtrado por fecha (df_all)
                    df_final = apply_filter(df_all, COL_FILTRO_CIUDAD, filtro_ciudad) 
                    df_final = apply_filter(df_final, COL_FILTRO_TECNICO, filtro_tecnico) 
                    df_final = apply_filter(df_final, COL_FILTRO_ESTADO, filtro_estado) 
                    
                    # NUEVOS FILTROS APLICADOS 
                    if COL_FILTRO_TIPO_ORDEN:
                        df_final = apply_filter(df_final, COL_FILTRO_TIPO_ORDEN, filtro_tipo_orden) 
                    if COL_FILTRO_TECNOLOGIA:
                        df_final = apply_filter(df_final, COL_FILTRO_TECNOLOGIA, filtro_tecnologia) 
                    # FIN NUEVOS FILTROS 
                    
                    datos_filtrados = df_final # Actualizamos datos_filtrados para que refleje todos los filtros.

                # --- FIN DEL PANEL DE CONTROL COMPACTO (1/2): FILTROS ---
                
# -----------------------------------------------------------------------------
                # --- INICIO DEL PANEL DE CONTROL COMPACTO (2/2): MÉTRICAS (SIN 'Total Ordenes') --- 
                # -----------------------------------------------------------------------------
                # Este contenedor está inmediatamente debajo del anterior (Filtros)
                with st.container(border=True):
                    st.markdown("#### 🎯 Métricas Clave (KPIs)") # Título para la caja de métricas
                    
                    # 💥 Redefinición de 6 columnas para MÉTRICAS (Se eliminó col_m_total_abs) 💥
                    col_m_inst_abs, col_m_vis_abs, col_m_mig_abs, col_m_man_abs, col_m_cd_abs, col_m_sat_abs = st.columns(
                        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0] # Ahora son 6 columnas en total
                    )

                    # ------------------------------------------------------------------------------------- 
                    # --- CÁLCULO DE MÉTRICAS CLAVE (DINÁMICO BASADO EN FILTRO DE ESTADO) --- 
                    # -------------------------------------------------------------------------------------

                    # El cálculo de total_registros_unfiltered ya no se usará para mostrar, pero se mantiene por si es necesario en el futuro.
                    if COL_TAREA_KEY in datos_filtrados.columns:
                        total_registros_unfiltered = datos_filtrados[COL_TAREA_KEY].count()
                    else:
                        total_registros_unfiltered = len(datos_filtrados) 

                    # 1. Lógica para determinar el DataFrame base para las métricas de tipo de orden
                    
                    # Si el usuario seleccionó EXACTAMENTE UN estado en el filtro, usamos ese estado como base.
                    if len(filtro_estado) == 1:
                        # Usar el estado seleccionado por el usuario como la nueva base
                        estado_base = filtro_estado[0]
                        datos_base_metricas = datos_filtrados[datos_filtrados[COL_FILTRO_ESTADO] == estado_base].copy()
                        etiqueta_estado = f" ({estado_base.title().replace(' ','')[:3]}.)"
                        etiqueta_total_base = f"Total Base ({estado_base.title().replace(' ','')[:3]}.)"
                    else:
                        # Si se seleccionaron Múltiples estados, o Ningún estado, volvemos a la lógica de SATISFACTORIA
                        estado_tarea = datos_filtrados[COL_ESTADO_KEY].astype(str)
                        es_satisfactoria = estado_tarea.str.contains('SATISFACTORIA', case=False, na=False)
                        es_insatisfactoria = estado_tarea.str.contains('INSATISFACTORIA', case=False, na=False)
                        
                        # Definimos la base como el subconjunto Satisfactorio
                        datos_base_metricas = datos_filtrados[es_satisfactoria & ~es_insatisfactoria].copy()
                        estado_base = "SATISFACTORIA"
                        etiqueta_estado = " (Sat.)" # Etiqueta por defecto
                        etiqueta_total_base = "Total Satisfactorias"


                    # Contar el total de registros de la base seleccionada
                    total_base = len(datos_base_metricas)
                    
                    # 4. Cálculo de Métricas de Tipo de Orden usando SOLO datos_base_metricas
                    if COL_TIPO_ORDEN_KEY in datos_base_metricas.columns: 
                        tipo_orden_base = datos_base_metricas[COL_TIPO_ORDEN_KEY].astype(str)
                        
                        # --- CÁLCULO DE MÉTRICAS CON REGEX (TIPOS DE ORDEN) ---
                        total_instalaciones = len(datos_base_metricas[tipo_orden_base.str.contains('INSTALACION', case=False, na=False)]) 
                        total_visitas_tecnicas = len(datos_base_metricas[tipo_orden_base.str.contains('VISITA TECNICA', case=False, na=False)])
                        total_migracion = len(datos_base_metricas[tipo_orden_base.str.contains(r'MIGRACI[ÓO]N', case=False, na=False, regex=True)])
                        total_tarea_manual = len(datos_base_metricas[tipo_orden_base.str.contains('TAREA MANUAL', case=False, na=False)])
                        total_cambio_direccion = len(datos_base_metricas[tipo_orden_base.str.contains(r'CAMBIO DE DIRECCI[ÓO]N', case=False, na=False, regex=True)])
                        # --- FIN CÁLCULO REGEX ---
                    else: 
                        total_instalaciones, total_visitas_tecnicas = 0, 0 
                        total_migracion, total_tarea_manual, total_cambio_direccion = 0, 0, 0 
                    
                    # --- RENDERIZADO DE MÉTRICAS COMPACTAS (Una sola fila) --- 
                    
                    # 💥 Columna para Total Órdenes (Absoluto - ELIMINADA) 💥
                    
                    # Columna para Instalaciones (Absoluto)
                    with col_m_inst_abs: 
                        st.markdown('<div class="metric-compact-container">', unsafe_allow_html=True) 
                        st.metric(label=f"Instalaciones{etiqueta_estado}", value=f"{total_instalaciones:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Columna para Visitas Téc. (Absoluto)
                    with col_m_vis_abs: 
                        st.markdown('<div class="metric-compact-container">', unsafe_allow_html=True) 
                        st.metric(label=f"Visitas Téc.{etiqueta_estado}", value=f"{total_visitas_tecnicas:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Columna para Migración (Absoluto)
                    with col_m_mig_abs: 
                        st.markdown('<div class="metric-compact-container">', unsafe_allow_html=True) 
                        st.metric(label=f"Migración{etiqueta_estado}", value=f"{total_migracion:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Columna para Tarea Manual (Absoluto)
                    with col_m_man_abs: 
                        st.markdown('<div class="metric-compact-container">', unsafe_allow_html=True) 
                        st.metric(label=f"Tarea Manual{etiqueta_estado}", value=f"{total_tarea_manual:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Columna para Cambio de Dirección (Absoluto)
                    with col_m_cd_abs: 
                        st.markdown('<div class="metric-compact-container">', unsafe_allow_html=True) 
                        st.metric(label=f"Cambio Dir.{etiqueta_estado}", value=f"{total_cambio_direccion:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    # Columna para Total de la Base seleccionada (Satisfactoria, Insatisfactoria, etc.)
                    with col_m_sat_abs: 
                        st.markdown('<div class="metric-compact-container-total">', unsafe_allow_html=True) 
                        st.metric(label=etiqueta_total_base, value=f"{total_base:,}") 
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                # --- FIN DEL PANEL DE CONTROL COMPACTO (2/2): MÉTRICAS ---

                st.markdown("---")
                
                # ------------------------------------------------------------------------------------- 
                # --- PROPAGACIÓN DEL FILTRO DINÁMICO PARA GRÁFICOS Y RAW DATA --- 
                # Ahora usamos datos_base_metricas para que la Tabla RAW y los gráficos
                # muestren solo las tareas del estado seleccionado.
                # -------------------------------------------------------------------------------------
                datos_filtrados = datos_base_metricas.copy() 
                # ------------------------------------------------------------------------------------- 
                
                # ------------------------------------------------------------------------------------- 
                # --- LAYOUT PRINCIPAL: DOS COLUMNAS (RAW vs. GRÁFICOS) --- 
                # -------------------------------------------------------------------------------------
                col_raw, col_graphs_group = st.columns([5, 15]) 

                # ------------------------------------------------------------------------------------- 
                # --- COLUMNA 1: TABLA DE DATOS RAW (IZQUIERDA) --- 
                # -------------------------------------------------------------------------------------
                with col_raw:
                    # ... (El código de la tabla RAW permanece sin cambios) ...
                    st.markdown(f"#### 📑 Datos RAW ({len(datos_filtrados)} registros - Base Dinámica)")

                    # 1. ORDENAR LOS DATOS POR FECHA (MÁS ANTIGUA A MÁS RECIENTE)
                    datos_filtrados_ordenados = datos_filtrados.sort_values(by=COL_TEMP_DATETIME, ascending=True).copy()

                    # Preparamos la vista de datos (renombramos) 
                    datos_vista = datos_filtrados_ordenados.rename(columns=FINAL_RENAMING_MAP) 
                    columnas_finales = [col for col in FINAL_RENAMING_MAP.values() if col in datos_vista.columns] 
                    
                    # CORRECCIÓN KEYERROR 'P': Usar 'C' para el campo TÉCNICO 
                    if COL_FILTRO_TECNICO in datos_filtrados_ordenados.columns and FINAL_RENAMING_MAP['C'] in datos_vista.columns:
                         datos_vista[FINAL_RENAMING_MAP['C']] = datos_filtrados_ordenados[COL_FILTRO_TECNICO]
                    # FIN CORRECCIÓN 
                    
                    datos_vista = datos_vista[columnas_finales]

                    # 2. Definición Final de Columnas por defecto 
                    col_fecha_finalizacion = FINAL_RENAMING_MAP['A'] 
                    col_tarea = FINAL_RENAMING_MAP['G'] 
                    col_tecnico = FINAL_RENAMING_MAP['C'] 
                    col_cliente = FINAL_RENAMING_MAP['E'] 
                    col_contrato = FINAL_RENAMING_MAP['D'] 
                    
                    
                    # Columnas por defecto (ORDEN SOLICITADO: Fecha, Técnico, Tarea, Contrato, Cliente)
                    default_cols_raw = [
                        col_fecha_finalizacion,
                        col_tecnico,
                        col_tarea, 
                        col_contrato,
                        col_cliente
                    ]

                    all_cols = datos_vista.columns.tolist() 
                    
                    # Asegurarse de que las columnas por defecto existan en el DataFrame antes de usarlas
                    default_cols = [c for c in default_cols_raw if c in all_cols]

                    # 3. Selector de Columnas 
                    cols_to_show = st.multiselect( 
                        "**Columnas a mostrar**:", 
                        options=all_cols, 
                        default=default_cols, 
                        key='raw_table_col_select_narrow'
                    )

                    df_to_display = datos_vista[cols_to_show] if cols_to_show else datos_vista

# 4. Implementación de overflow horizontal 
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

                    # --- INICIO NUEVA EXPORTACIÓN FULL (Contiene todos los registros filtrados) ---
                    import io 
                    from datetime import datetime
                    
                    # 1. PREPARAR DATOS COMPLETOS PARA EXPORTACIÓN
                    # Usamos 'df_final' porque ya tiene aplicados TODOS los filtros de segmentación (fechas, multiselect).
                    df_export_full = df_final.copy()
                    
                    # Renombrar todas las columnas (columnas originales) al formato final
                    # Esto asegura que el archivo exportado tenga todas las columnas que el usuario espera,
                    # no solo las seleccionadas en el multiselect de la tabla RAW.
                    df_export_full.rename(columns=FINAL_RENAMING_MAP, inplace=True)
                    
                    # Filtra las columnas para que solo queden las renombradas y las usa en el orden deseado
                    columnas_exportacion = [col for col in FINAL_RENAMING_MAP.values() if col in df_export_full.columns]
                    df_export_full = df_export_full[columnas_exportacion]

                    # 2. Crear un buffer en memoria para guardar el archivo Excel
                    excel_buffer = io.BytesIO()
                    
                    # 3. Escribir el DataFrame COMPLETO en el buffer como un archivo XLSX
                    df_export_full.to_excel(excel_buffer, index=False, sheet_name='Exportacion_Completa')
                    
                    # 4. Volver al inicio del buffer antes de la descarga
                    excel_buffer.seek(0)
                    
                    st.download_button(
                        label=f"⬇️ Descargar TODOS los {len(df_export_full)} Registros Filtrados (Excel .xlsx)",
                        data=excel_buffer, 
                        file_name=f'exportacion_full_filtrada_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True,
                        key='download_raw_excel_full'
                    )
                    # --- FIN NUEVA EXPORTACIÓN FULL ---

                # ------------------------------------------------------------------------------------- 
                # --- COLUMNA 2: GRUPO DE GRÁFICOS (DERECHA) --- 
                # -------------------------------------------------------------------------------------
                with col_graphs_group: 
                    
                    # 1. Primera Fila de Gráficos (Anidada)
                    col_graphs_izq, col_graphs_der = st.columns([8, 7])

                    # --- GRÁFICO TAREAS POR SEGMENTO (sin cambios) --- 
                    with col_graphs_izq: 
                        with st.container(border=True): 
                            st.markdown(f"#### Tareas por Segmento (5 días - Base: {estado_base.title()})")

                            if len(datos_filtrados) > 0: 
                                datos_temp = datos_filtrados.copy() 
                                datos_temp['DAY'] = datos_temp[COL_TEMP_DATETIME].dt.day 
                                datos_temp['MONTH'] = datos_temp[COL_TEMP_DATETIME].dt.month 
                                datos_temp['YEAR'] = datos_temp[COL_TEMP_DATETIME].dt.year 
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
                                    height=200, # ALTURA AUMENTADA
                                    xaxis={'tickangle': -45}
                                ) 
                                fig.update_traces(textposition='outside') 
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}) 
                            else: 
                                st.info("No hay datos para el gráfico semanal con la base seleccionada.")

                    # --- GRÁFICO TOP 5 TÉCNICOS (sin cambios) --- 
                    with col_graphs_der: 
                        with st.container(border=True): 
                            st.markdown(f"#### Top 5 Técnicos (Base: {estado_base.title()})") 
                            if COL_FILTRO_TECNICO in datos_filtrados.columns and len(datos_filtrados) > 0: 
                                top_tecnicos = datos_filtrados[COL_FILTRO_TECNICO].value_counts().head(5).reset_index() 
                                top_tecnicos.columns = ['Técnico', 'Total Tareas']

                                fig_pie = px.pie(top_tecnicos, values='Total Tareas', names='Técnico', hole=.4, color_discrete_sequence=px.colors.qualitative.Pastel) 
                                fig_pie.update_layout(showlegend=True, margin=dict(l=0, r=0, t=20, b=0), height=200) # ALTURA AUMENTADA
                                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False}) 
                            else: 
                                st.info("Datos insuficientes para Top Técnico con la base seleccionada.")
                    
                    
# *************************************************************************************
                    # *** SECCIÓN: RENDIMIENTO DINÁMICO (Lógica Modificada) ***
                    # *************************************************************************************
                    st.markdown("---") # Separador para la nueva sección
                    st.markdown(f"### 📈 Rendimiento Detallado de Órdenes (Base: {estado_base.title()})")

                    # Contenedor principal para la sección de rendimiento
                    with st.container(border=True): 
                        
                        # Definición de las condiciones
                        is_single_technician = len(filtro_tecnico) == 1
                        is_single_city = len(filtro_ciudad) == 1

                        if is_single_technician:
                            # CASO 1: Un solo técnico seleccionado -> Mostrar distribución por CIUDAD
                            df_comparacion_view = prepare_city_comparison_data(datos_filtrados) # Agrupación por Ciudad
                            x_column_to_plot = COL_FILTRO_CIUDAD # Eje X: Ciudad
                            title = f"por Ubicación para Técnico: **{filtro_tecnico[0]}**"
                            is_city_view = True
                            
                        elif is_single_city:
                            # CASO 2: Varios técnicos, pero una sola ciudad -> Mostrar por TÉCNICO
                            # Nota: prepare_comparison_data agrupa por Ciudad/Técnico.
                            df_comparacion_view = prepare_comparison_data(datos_filtrados)
                            x_column_to_plot = COL_FILTRO_TECNICO # Eje X: Técnico
                            title = f"por Técnico en: **{filtro_ciudad[0]}**"
                            is_city_view = False
                            
                        else:
                            # CASO 3: Múltiples técnicos y múltiples ciudades / Sin filtros -> Mostrar por CIUDAD (Vista general)
                            df_comparacion_view = prepare_city_comparison_data(datos_filtrados) # Agrupación por Ciudad
                            x_column_to_plot = COL_FILTRO_CIUDAD # Eje X: Ciudad
                            title = "por Ubicación"
                            is_city_view = True

                        
                        # --- RENDERIZADO FINAL ---
                        if not df_comparacion_view.empty: 
                            render_comparison_charts_vertical( 
                                df_comparacion_view, 
                                x_column_to_plot, 
                                title, 
                                is_city_view=is_city_view 
                            ) 
                        else:
                            st.info("No hay datos de rendimiento con los filtros aplicados para esta visualización.")
                    # *************************************************************************************