import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURACIÓN ---
MASTER_EXCEL = "datos.xlsx"
USUARIOS_EXCEL = "usuarios.xlsx"
UPLOAD_FOLDER = "ExcelUploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.set_page_config(page_title="Dashboard Profesional", layout="wide")

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
    st.title("📊 Dashboard Profesional")
    usuario_input = st.text_input("Usuario")
    contrasena_input = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión"):
        user_row = usuarios_df[
            (usuarios_df["Usuario"].str.lower() == usuario_input.strip().lower()) &
            (usuarios_df["Contraseña"] == contrasena_input.strip())
        ]
        if not user_row.empty:
            st.session_state.login = True
            st.session_state.rol = user_row.iloc[0]["Rol"]
            st.session_state.usuario = usuario_input.strip()
            # CORRECCIÓN: Usar st.rerun()
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

else:
    st.sidebar.success(f"Bienvenido {st.session_state.usuario} ({st.session_state.rol})")
    st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update({"login": False, "rol": None}), key="logout_btn")

    # --- ADMIN: SUBIR / ELIMINAR EXCELS (MEJORADO) ---
    if st.session_state.rol.lower() == "admin":
        st.sidebar.header("⚙️ Administración")
        
        # SUBIR ARCHIVOS
        nuevos_archivos = st.sidebar.file_uploader("Subir archivos Excel", type="xlsx", accept_multiple_files=True)
        if nuevos_archivos:
            for f in nuevos_archivos:
                save_path = os.path.join(UPLOAD_FOLDER, f.name)
                with open(save_path, "wb") as file:
                    file.write(f.getbuffer())
            st.sidebar.success(f"{len(nuevos_archivos)} archivos guardados")
            st.rerun() 

        archivos_actuales = os.listdir(UPLOAD_FOLDER)
        st.sidebar.markdown("---")

        # ELIMINAR SELECCIONADOS
        eliminar = st.sidebar.multiselect("Selecciona archivos a eliminar", archivos_actuales)
        if st.sidebar.button("🗑️ Eliminar seleccionados", key="del_selected"):
            if eliminar:
                for f in eliminar:
                    os.remove(os.path.join(UPLOAD_FOLDER, f))
                st.sidebar.success(f"{len(eliminar)} archivos eliminados.")
                st.rerun()
            else:
                 st.sidebar.info("No seleccionaste archivos para eliminar.")
        
        # ELIMINAR TODOS Y VACIAR DASHBOARD
        st.sidebar.markdown("---")
        if archivos_actuales and st.sidebar.button("🔴 Eliminar TODOS los archivos", key="del_all"):
            archivos_eliminados_count = len(archivos_actuales)
            
            # 1. Eliminar todos los archivos de la carpeta de subidas
            for f in archivos_actuales:
                os.remove(os.path.join(UPLOAD_FOLDER, f))
            
            # 2. Eliminar el archivo maestro consolidado
            if os.path.exists(MASTER_EXCEL):
                os.remove(MASTER_EXCEL)
            
            st.sidebar.success(f"{archivos_eliminados_count} archivos eliminados y Master Excel borrado. Dashboard vacío.")
            st.rerun()
        elif not archivos_actuales:
             st.sidebar.info("La carpeta de subidas está vacía.")
        # -------------------------------------------------------------

    # --- CARGAR DATOS ---
    archivos_para_combinar = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER)]
    datos = None
    if archivos_para_combinar:
        try:
            df_list = [pd.read_excel(f) for f in archivos_para_combinar]
            datos = pd.concat(df_list, ignore_index=True)
            datos.to_excel(MASTER_EXCEL, index=False)
        except Exception as e:
            st.error(f"Error al combinar o leer archivos de la carpeta de subidas: {e}")
            st.stop()
    else:
        try:
            datos = pd.read_excel(MASTER_EXCEL)
        except FileNotFoundError:
            # Estado de dashboard vacío
            st.info("⚠️ No hay datos disponibles para el dashboard. El administrador debe subir archivos.")
            st.stop()
        except Exception as e:
            st.error(f"Error al leer el archivo maestro {MASTER_EXCEL}: {e}")
            st.stop()

    if datos is None or datos.empty:
        st.warning("No hay datos para mostrar.")
        st.stop()

    # --- MENU DE PESTAÑAS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Datos", "📈 KPIs", "📊 Gráficos", "🔎 Filtros Avanzados"])

    # --- TABLA DE DATOS ---
    with tab1:
        st.subheader("Vista de datos")
        st.dataframe(datos, use_container_width=True)

    # --- KPIs ---
    with tab2:
        st.subheader("Indicadores clave")
        num_cols = datos.select_dtypes(include='number').columns.tolist()
        if num_cols:
            display_cols = num_cols[:4] if len(num_cols) > 4 else num_cols
            kpi_cols = st.columns(len(display_cols))
            
            for i, col in enumerate(display_cols):
                with kpi_cols[i]:
                    st.metric(
                        label=f"{col} - Total",
                        value=f"{datos[col].sum():,.0f}"
                    )
                    st.metric(
                        label=f"{col} - Promedio",
                        value=f"{datos[col].mean():,.2f}"
                    )
                    st.metric(
                        label=f"{col} - Máx",
                        value=f"{datos[col].max():,.0f}"
                    )
        else:
            st.info("No se encontraron columnas numéricas para calcular KPIs.")

    # --- GRAFICOS ---
    with tab3:
        st.subheader("Generador de gráficos")
        columnas = datos.columns.tolist()
        
        col_chart, col_data = st.columns([1, 1])
        with col_chart:
            tipo_grafico = st.selectbox("Tipo de gráfico", ["Barras", "Pastel", "Líneas", "Scatter", "Box", "Área", "Histograma"])
        
        columnas_numericas = [c for c in columnas if pd.api.types.is_numeric_dtype(datos[c])]
        
        with col_data:
            x_col = st.selectbox("Eje X", columnas)
            y_col = st.selectbox("Eje Y", [None] + columnas_numericas)
            color_col = st.selectbox("Color (opcional)", [None] + columnas)

        fig = None
        
        if tipo_grafico in ["Barras", "Líneas", "Scatter", "Box", "Área", "Pastel"] and y_col is None:
            st.warning(f"El gráfico de {tipo_grafico} requiere que el Eje Y sea una columna numérica.")
        
        else:
            try:
                if tipo_grafico == "Barras":
                    fig = px.bar(datos, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Pastel":
                    fig = px.pie(datos, names=x_col, values=y_col, color=color_col)
                elif tipo_grafico == "Líneas":
                    fig = px.line(datos, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Scatter":
                    fig = px.scatter(datos, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Box":
                    fig = px.box(datos, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Área":
                    fig = px.area(datos, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Histograma":
                    fig = px.histogram(datos, x=x_col, y=y_col, color=color_col)

                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error al generar el gráfico. Verifica la combinación de ejes. Detalle: {e}")


    # --- FILTROS AVANZADOS (MEJORADO: Agrupación por Raíz y Filtro por Contenido) ---
    with tab4:
        st.title("🔎 Filtros Dinámicos Rigurosos")
        st.markdown("Utiliza las listas desplegables. Para columnas de texto (ej. Ubicación), las opciones muestran la **primera palabra** (la raíz, ej. 'Quito') y al seleccionar, **filtra todas** las entradas que contengan esa raíz.")
        
        datos_filtrados = datos.copy()
        
        with st.container():
            
            cols_per_row = 3
            columnas_df = datos.columns.tolist()
            num_columnas = len(columnas_df)
            
            for i in range(0, num_columnas, cols_per_row):
                cols = st.columns(cols_per_row) 
                
                for j in range(cols_per_row):
                    col_index = i + j
                    
                    if col_index < num_columnas:
                        col = columnas_df[col_index]
                        
                        with cols[j]:
                            # --- LÓGICA DE FILTRADO PARA LA COLUMNA ACTUAL ---
                            try:
                                # Prepara valores únicos como strings
                                valores_unicos = datos[col].unique()
                                columna_es_texto = pd.api.types.is_object_dtype(datos[col]) or pd.api.types.is_string_dtype(datos[col])
                                
                                if columna_es_texto:
                                    # Generar las opciones de filtro (la "raíz" del texto)
                                    opciones_raíz = set()
                                    for v in valores_unicos:
                                        if pd.notna(v) and isinstance(v, str):
                                            # Extrae la primera palabra (la raíz)
                                            raíz = v.strip().split(',')[0].strip().split(' ')[0]
                                            opciones_raíz.add(raíz)
                                    opciones_filtro = sorted(list(opciones_raíz))
                                    opciones_filtro.append(" (Vacío / N/A)")
                                    
                                    # El desplegable de selección
                                    seleccion_str = st.multiselect(
                                        label=f"Filtro: {col} (Raíz)",
                                        options=opciones_filtro,
                                        default=opciones_filtro, 
                                        key=f"filter_{col}"
                                    )
                                    
                                    if seleccion_str and len(seleccion_str) < len(opciones_filtro):
                                        
                                        # 1. Manejar NaNs (Vacío)
                                        filtrar_nans = " (Vacío / N/A)" in seleccion_str
                                        
                                        # 2. Obtener las raíces a buscar
                                        raíces_a_buscar = [r for r in seleccion_str if r != " (Vacío / N/A)"]
                                        
                                        # 3. Aplicar el filtro de CONTENIDO (lo que pediste)
                                        # Crear una máscara booleana inicial
                                        filtro_final = pd.Series([False] * len(datos_filtrados), index=datos_filtrados.index)
                                        
                                        if raíces_a_buscar:
                                            # Genera la máscara buscando cada raíz como subcadena (ej. "Quito" está en "Quito, San Roque")
                                            for raíz in raíces_a_buscar:
                                                mascara_raíz = datos_filtrados[col].astype(str).str.contains(raíz, case=False, na=False)
                                                filtro_final = filtro_final | mascara_raíz # Lógica OR entre las raíces
                                        
                                        if filtrar_nans:
                                            # Incluir las filas que son NaN
                                            filtro_final = filtro_final | datos_filtrados[col].isna()
                                        
                                        datos_filtrados = datos_filtrados[filtro_final]


                                # --- Lógica de Multiselect simple (para Numéricos/Fechas) ---
                                else:
                                    # Para numéricos o fechas, usamos el multiselect tradicional
                                    valores_unicos_str = [str(v) if pd.notna(v) else " (Vacío / N/A)" for v in valores_unicos]
                                    seleccion_str = st.multiselect(
                                        label=f"Filtro: {col}",
                                        options=valores_unicos_str,
                                        default=valores_unicos_str, 
                                        key=f"filter_{col}_simple"
                                    )
                                    
                                    if seleccion_str and len(seleccion_str) < len(valores_unicos_str):
                                        filtrar_nans = " (Vacío / N/A)" in seleccion_str
                                        valores_a_filtrar_str = [v for v in seleccion_str if v != " (Vacío / N/A)"]
                                        
                                        filtro_principal = datos_filtrados[col].astype(str).isin(valores_a_filtrar_str)
                                        
                                        if filtrar_nans:
                                            datos_filtrados = datos_filtrados[filtro_principal | datos_filtrados[col].isna()]
                                        else:
                                            datos_filtrados = datos_filtrados[filtro_principal]


                            except Exception as e:
                                st.error(f"Error al configurar filtro de columna '{col}'. Detalle: {e}")
                                
        st.markdown("---")
        st.subheader(f"Vista Filtrada ({len(datos_filtrados)} de {len(datos)} registros)")
        
        if datos_filtrados.empty:
            st.warning("No hay registros que coincidan con la selección de filtros.")
        else:
            st.dataframe(datos_filtrados, use_container_width=True)