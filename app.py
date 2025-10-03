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
    """
    for col in columnas_df:
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
    # --- CONTEO DE ARCHIVOS CARGADOS ---
    archivos_para_combinar_nombres = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.xlsx') or f.endswith('.xls')]
    num_archivos_cargados = len(archivos_para_combinar_nombres)
    
    st.sidebar.success(f"Bienvenido {st.session_state.usuario} ({st.session_state.rol})")
    st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update({"login": False, "rol": None}), key="logout_btn")
    
    # MENÚ CONTEXTUAL DE CONTEO DE ARCHIVOS
    if num_archivos_cargados > 0:
        st.sidebar.info(f"💾 **{num_archivos_cargados}** archivo(s) Excel cargado(s) y combinado(s).")
    else:
        st.sidebar.warning("⚠️ No hay archivos Excel cargados.")

    # --- ADMIN: SUBIR / ELIMINAR EXCELS ---
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
            
            for f in archivos_actuales:
                os.remove(os.path.join(UPLOAD_FOLDER, f))
            
            if os.path.exists(MASTER_EXCEL):
                os.remove(MASTER_EXCEL)
            
            st.sidebar.success(f"{archivos_eliminados_count} archivos eliminados y Master Excel borrado. Dashboard vacío.")
            st.rerun()
        elif not archivos_actuales:
             st.sidebar.info("La carpeta de subidas está vacía.")
        # -------------------------------------------------------------

    # --- CARGAR DATOS (FUSIÓN ESTADÍSTICA) ---
    datos = None
    if archivos_para_combinar_nombres: 
        archivos_completos = [os.path.join(UPLOAD_FOLDER, f) for f in archivos_para_combinar_nombres]
        try:
            df_list = [pd.read_excel(f) for f in archivos_completos]
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
    
    datos_base = datos.copy()
    
    # --------------------------------------------------------------------------
    # --- CONFIGURACIÓN DE FECHA BASE DINÁMICA ---
    # --------------------------------------------------------------------------
    
    # 1. Identificar columnas candidatas a fecha
    columnas_candidatas_fecha = []
    # Heurística: columnas que contienen 'fecha', 'date', o que son de tipo datetime
    for col in datos_base.columns:
        if pd.api.types.is_datetime64_any_dtype(datos_base[col]):
            columnas_candidatas_fecha.append(col)
        elif 'fecha' in str(col).lower() or 'date' in str(col).lower():
            columnas_candidatas_fecha.append(col)
            
    columnas_candidatas_fecha = sorted(list(set(columnas_candidatas_fecha)))

    COLUMNA_FECHA_BASE = None
    nuevas_cols_tiempo = []
    
    # Sección de selección de fecha (antes de las pestañas)
    if columnas_candidatas_fecha:
        st.subheader("🗓️ Configuración de Análisis de Tiempo")
        COLUMNA_FECHA_BASE = st.selectbox(
            "Selecciona la **Fecha Base** para el análisis por Mes/Semana/Día:",
            options=[None] + columnas_candidatas_fecha,
            index=1 if columnas_candidatas_fecha else 0,
            key="fecha_base_selector"
        )
        st.markdown("---")

    # --------------------------------------------------------------------------
    # --- CREACIÓN DE COLUMNAS DE TIEMPO (DINÁMICO) ---
    # --------------------------------------------------------------------------
    if COLUMNA_FECHA_BASE and COLUMNA_FECHA_BASE in datos_base.columns:
        try:
            # Convertir la columna seleccionada a datetime
            datos_base[COLUMNA_FECHA_BASE] = pd.to_datetime(datos_base[COLUMNA_FECHA_BASE], errors='coerce')
            
            # Crear 'Día de la Semana'
            datos_base['Día de la Semana'] = datos_base[COLUMNA_FECHA_BASE].dt.dayofweek.map({
                0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
                4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
            })
            nuevas_cols_tiempo.append('Día de la Semana')
            
            # Crear 'Semana del Mes'
            datos_base['Semana del Mes'] = (datos_base[COLUMNA_FECHA_BASE].dt.day - 1) // 7 + 1
            datos_base['Semana del Mes'] = datos_base['Semana del Mes'].astype(str) 
            nuevas_cols_tiempo.append('Semana del Mes')
            
            # Crear 'Mes'
            datos_base['Mes'] = datos_base[COLUMNA_FECHA_BASE].dt.strftime('%Y-%m')
            nuevas_cols_tiempo.append('Mes')
            
        except Exception as e:
            st.warning(f"Error al procesar la columna de fecha '{COLUMNA_FECHA_BASE}'. El análisis de tiempo no estará disponible. Detalle: {e}")
            nuevas_cols_tiempo = [] 

    # --- MENU DE PESTAÑAS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Datos", "📈 KPIs", "📊 Gráficos", "🔎 Filtros Avanzados"])

    # --- TABLA DE DATOS ---
    with tab1:
        st.subheader("Vista de datos")
        st.dataframe(datos_base, use_container_width=True)

    # --- KPIs ---
    with tab2:
        st.subheader("Indicadores clave")
        # KPI's se calculan sobre la base de datos completa por ahora
        num_cols = datos_base.select_dtypes(include='number').columns.tolist()
        if num_cols:
            display_cols = num_cols[:4] if len(num_cols) > 4 else num_cols
            kpi_cols = st.columns(len(display_cols))
            
            for i, col in enumerate(display_cols):
                with kpi_cols[i]:
                    st.metric(
                        label=f"{col} - Total",
                        value=f"{datos_base[col].sum():,.0f}"
                    )
                    st.metric(
                        label=f"{col} - Promedio",
                        value=f"{datos_base[col].mean():,.2f}"
                    )
                    st.metric(
                        label=f"{col} - Máx",
                        value=f"{datos_base[col].max():,.0f}"
                    )
        else:
            st.info("No se encontraron columnas numéricas para calcular KPIs.")

    # --- GRAFICOS ---
    with tab3:
        st.subheader("Generador de gráficos")
        columnas = datos_base.columns.tolist()
        
        col_chart, col_data = st.columns([1, 1])
        with col_chart:
            tipo_grafico = st.selectbox("Tipo de gráfico", ["Barras", "Pastel", "Líneas", "Scatter", "Box", "Área", "Histograma"])
        
        columnas_numericas = [c for c in columnas if pd.api.types.is_numeric_dtype(datos_base[c])]
        
        with col_data:
            x_col = st.selectbox("Eje X", columnas)
            y_col = st.selectbox("Eje Y", [None] + columnas_numericas)
            color_col = st.selectbox("Color (opcional)", [None] + columnas)

        fig = None
        
        if tipo_grafico in ["Barras", "Líneas", "Scatter", "Box", "Área", "Pastel"] and y_col is None:
            st.warning(f"El gráfico de {tipo_grafico} requiere que el Eje Y sea una columna numérica.")
        
        else:
            try:
                # Lógica para ordenar los ejes de tiempo correctamente
                orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                category_orders = {}

                if x_col == 'Día de la Semana':
                    category_orders[x_col] = orden_dias
                elif x_col == 'Semana del Mes':
                    valid_weeks = [w for w in datos_base['Semana del Mes'].unique() if pd.notna(w) and str(w).isdigit()]
                    category_orders[x_col] = sorted(valid_weeks, key=int)
                
                # Generación de Gráficos
                if tipo_grafico == "Barras":
                    fig = px.bar(datos_base, x=x_col, y=y_col, color=color_col, category_orders=category_orders)
                elif tipo_grafico == "Pastel":
                    fig = px.pie(datos_base, names=x_col, values=y_col, color=color_col)
                elif tipo_grafico == "Líneas":
                    # Si el eje X es una fecha, se ordena automáticamente. Si es Mes/Semana/Día se usa category_orders.
                    fig = px.line(datos_base, x=x_col, y=y_col, color=color_col, category_orders=category_orders)
                elif tipo_grafico == "Scatter":
                    fig = px.scatter(datos_base, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Box":
                    fig = px.box(datos_base, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Área":
                    fig = px.area(datos_base, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Histograma":
                    fig = px.histogram(datos_base, x=x_col, y=y_col, color=color_col)

                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error al generar el gráfico. Verifica la combinación de ejes. Detalle: {e}")


    # ----------------------------------------------------------------------
    # --- FILTROS AVANZADOS (Filtros Dinámicos / en Cascada) ---
    # ----------------------------------------------------------------------
    with tab4:
        st.title("🔎 Filtros Dinámicos Rigurosos")
        st.markdown("Los filtros ahora son en **cascada**: cada filtro se basa solo en los datos restantes de los filtros anteriores.")
        
        columnas_df = datos_base.columns.tolist()
        
        # --- SECCIÓN DE CONTROL DE VISIBILIDAD ---
        col_clean, col_hide = st.columns([1, 2])
        
        with col_clean:
            st.button("🧹 Limpiar TODOS los Filtros", 
                    on_click=clear_filters, 
                    args=(columnas_df,), 
                    key="clear_all_filters")

        with col_hide:
            columnas_a_ocultar = st.multiselect(
                "👁️ Columnas a ocultar (se oculta el filtro y la columna en la tabla)",
                options=columnas_df,
                default=[],
                key="hidden_columns_selector"
            )
            
        st.markdown("---")
            
        datos_filtrados = datos_base.copy()
        
        # Ordenar las columnas para mostrar las de tiempo primero
        columnas_base_filtrables = [col for col in columnas_df if col not in nuevas_cols_tiempo]
        columnas_ordenadas = nuevas_cols_tiempo + columnas_base_filtrables
        columnas_visibles = [col for col in columnas_ordenadas if col not in columnas_a_ocultar]

        with st.container():
            
            cols_per_row = 3
            num_columnas_visibles = len(columnas_visibles)
            
            for i in range(0, num_columnas_visibles, cols_per_row):
                cols = st.columns(cols_per_row) 
                
                for j in range(cols_per_row):
                    col_index = i + j
                    
                    if col_index < num_columnas_visibles:
                        col = columnas_visibles[col_index] 
                        
                        # Los valores únicos se calculan sobre el DataFrame YA FILTRADO
                        df_para_opciones = datos_filtrados.copy()
                        
                        # --- PREPARACIÓN DE OPCIONES DINÁMICAS ---
                        valores_unicos = df_para_opciones[col].unique()
                        columna_es_texto = pd.api.types.is_object_dtype(df_para_opciones[col]) or pd.api.types.is_string_dtype(df_para_opciones[col])
                        
                        
                        # 1. Definición de la lista de opciones (opciones_filtro)
                        if columna_es_texto and col not in nuevas_cols_tiempo:
                            # Lógica de Raíz solo para columnas que no son de tiempo
                            opciones_raíz = set()
                            for v in valores_unicos:
                                if pd.notna(v) and isinstance(v, str):
                                    raíz = v.strip().split(',')[0].strip() 
                                    opciones_raíz.add(raíz)
                            opciones_filtro = sorted(list(opciones_raíz))
                            opciones_filtro.append(" (Vacío / N/A)")
                        
                        elif col == 'Día de la Semana':
                            # Orden específico para los días de la semana
                            orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                            opciones_filtro = [d for d in orden_dias if d in valores_unicos]
                            opciones_filtro.append(" (Vacío / N/A)")
                        
                        else:
                            # Filtro tradicional o para Mes y Semana del Mes
                            opciones_filtro = [str(v) if pd.notna(v) else " (Vacío / N/A)" for v in valores_unicos]
                            if col == 'Semana del Mes':
                                # Asegurar el orden numérico para las semanas (1, 2, 3, ...)
                                sin_na = [v for v in opciones_filtro if v != " (Vacío / N/A)"]
                                ordenadas = sorted(sin_na, key=lambda x: int(x) if x.isdigit() else 99)
                                opciones_filtro = ordenadas + [v for v in opciones_filtro if v == " (Vacío / N/A)"]
                            else:
                                # Orden alfabético/cronológico para Mes y otras
                                sin_na = [v for v in opciones_filtro if v != " (Vacío / N/A)"]
                                ordenadas = sorted(sin_na)
                                opciones_filtro = ordenadas + [v for v in opciones_filtro if v == " (Vacío / N/A)"]
                            
                        # --- MANEJO DEL ESTADO DE SESIÓN Y SANITIZACIÓN ---
                        if f"filter_{col}" not in st.session_state:
                            st.session_state[f"filter_{col}"] = []
                            
                        # Sanitizar el valor por defecto (Soluciona el error StreamlitAPIException)
                        current_default = st.session_state[f"filter_{col}"]
                        sanitized_default = [item for item in current_default if item in opciones_filtro]
                        st.session_state[f"filter_{col}"] = sanitized_default 
                        
                        with cols[j]:
                            # El desplegable de selección
                            etiqueta_filtro = 'Raíz' if columna_es_texto and col not in nuevas_cols_tiempo else 'Valor'
                            seleccion_str = st.multiselect(
                                label=f"Filtro: {col} ({etiqueta_filtro})",
                                options=opciones_filtro,
                                default=st.session_state[f"filter_{col}"],
                                key=f"filter_{col}"
                            )
                            
                            # --- APLICACIÓN DEL FILTRO (ACTUALIZA datos_filtrados) ---
                            if seleccion_str:
                                
                                filtrar_nans = " (Vacío / N/A)" in seleccion_str
                                items_a_filtrar = [r for r in seleccion_str if r != " (Vacío / N/A)"]
                                
                                # Las nuevas columnas de tiempo (Mes, Semana, Día) no usan la lógica de "Raíz"
                                if columna_es_texto and col not in nuevas_cols_tiempo:
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
                                    # Lógica de Valor Único (incluye columnas de tiempo)
                                    filtro_principal = datos_filtrados[col].astype(str).isin(items_a_filtrar)
                                    
                                    if filtrar_nans:
                                        datos_filtrados = datos_filtrados[filtro_principal | datos_filtrados[col].isna()]
                                    else:
                                        datos_filtrados = datos_filtrados[filtro_principal]

        
        st.markdown("---")
        st.subheader(f"Vista Filtrada ({len(datos_filtrados)} de {len(datos_base)} registros)")
        
        if datos_filtrados.empty:
            st.warning("No hay registros que coincidan con la selección de filtros.")
        else:
            # Mostrar solo las columnas que no fueron seleccionadas para ocultar
            st.dataframe(datos_filtrados[columnas_visibles], use_container_width=True)