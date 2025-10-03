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

# --- FUNCIONES DE FILTRO ---
def clear_filters(columnas_df):
    """
    Reinicia la selección de todos los filtros en el st.session_state a una lista vacía ([]).
    Esto hace que los multiselects muestren "Choose options" al recargarse.
    """
    for col in columnas_df:
        # Establece el valor de la clave de sesión del filtro a una lista vacía
        st.session_state[f"filter_{col}"] = []
        
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


    # --- FILTROS AVANZADOS (FINAL: Agrupación por Raíz y Limpieza Rápida) ---
    with tab4:
        st.title("🔎 Filtros Dinámicos Rigurosos")
        
        columnas_df = datos.columns.tolist()
        
        # --- SECCIÓN DE CONTROL DE VISIBILIDAD ---
        # Usamos una columna para el botón de limpieza y el selector de ocultar
        col_clean, col_hide = st.columns([1, 2])
        
        with col_clean:
            st.button("🧹 Limpiar TODOS los Filtros", 
                    on_click=clear_filters, 
                    args=(columnas_df,), 
                    key="clear_all_filters")

        with col_hide:
            # Selector de columnas a ocultar (el "ojo")
            columnas_a_ocultar = st.multiselect(
                "👁️ Columnas a ocultar (se oculta el filtro y la columna en la tabla)",
                options=columnas_df,
                default=[],
                key="hidden_columns_selector"
            )
            
        st.markdown("---")
            
        datos_filtrados = datos.copy()
        
        # Las columnas que REALMENTE se van a filtrar y mostrar
        columnas_visibles = [col for col in columnas_df if col not in columnas_a_ocultar]

        with st.container():
            
            cols_per_row = 3
            num_columnas_visibles = len(columnas_visibles)
            
            for i in range(0, num_columnas_visibles, cols_per_row):
                cols = st.columns(cols_per_row) 
                
                for j in range(cols_per_row):
                    col_index = i + j
                    
                    if col_index < num_columnas_visibles:
                        col = columnas_visibles[col_index] # Solo iteramos sobre las visibles
                        
                        # --- PREPARACIÓN DE OPCIONES ---
                        valores_unicos = datos[col].unique()
                        columna_es_texto = pd.api.types.is_object_dtype(datos[col]) or pd.api.types.is_string_dtype(datos[col])
                        
                        if columna_es_texto:
                            opciones_raíz = set()
                            for v in valores_unicos:
                                if pd.notna(v) and isinstance(v, str):
                                    # Lógica de Raíz Corregida
                                    raíz = v.strip().split(',')[0].strip() 
                                    opciones_raíz.add(raíz)
                            opciones_filtro = sorted(list(opciones_raíz))
                            opciones_filtro.append(" (Vacío / N/A)")
                        else:
                            opciones_filtro = [str(v) if pd.notna(v) else " (Vacío / N/A)" for v in valores_unicos]
                            opciones_filtro = sorted(opciones_filtro)
                            
                        # --- MANEJO DEL ESTADO DE SESIÓN ---
                        if f"filter_{col}" not in st.session_state:
                            st.session_state[f"filter_{col}"] = []
                        
                        with cols[j]:
                            # El desplegable de selección
                            seleccion_str = st.multiselect(
                                label=f"Filtro: {col} ({'Raíz' if columna_es_texto else 'Valor'})",
                                options=opciones_filtro,
                                default=st.session_state[f"filter_{col}"],
                                key=f"filter_{col}"
                            )
                            
                            # --- APLICACIÓN DEL FILTRO ---
                            if seleccion_str:
                                
                                filtrar_nans = " (Vacío / N/A)" in seleccion_str
                                items_a_filtrar = [r for r in seleccion_str if r != " (Vacío / N/A)"]
                                
                                if columna_es_texto:
                                    # Lógica de Raíz (Filtro por Contenido)
                                    filtro_final = pd.Series([False] * len(datos_filtrados), index=datos_filtrados.index)
                                    
                                    if items_a_filtrar:
                                        for raíz in items_a_filtrar:
                                            mascara_raíz = datos_filtrados[col].astype(str).str.contains(raíz, case=False, na=False)
                                            filtro_final = filtro_final | mascara_raíz
                                    
                                    if filtrar_nans:
                                        filtro_final = filtro_final | datos_filtrados[col].isna()
                                        
                                    datos_filtrados = datos_filtrados[filtro_final]
                                    
                                else:
                                    # Lógica de Valor Único (Filtro Tradicional)
                                    filtro_principal = datos_filtrados[col].astype(str).isin(items_a_filtrar)
                                    
                                    if filtrar_nans:
                                        datos_filtrados = datos_filtrados[filtro_principal | datos_filtrados[col].isna()]
                                    else:
                                        datos_filtrados = datos_filtrados[filtro_principal]

        
        st.markdown("---")
        st.subheader(f"Vista Filtrada ({len(datos_filtrados)} de {len(datos)} registros)")
        
        if datos_filtrados.empty:
            st.warning("No hay registros que coincidan con la selección de filtros.")
        else:
            # Mostrar solo las columnas que no fueron seleccionadas para ocultar
            st.dataframe(datos_filtrados[columnas_visibles], use_container_width=True)