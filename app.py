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
    st.error(f"No se encontró {USUARIOS_EXCEL}.")
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
    # --- MÉTRICA DE CONTEO Y CONFIGURACIÓN DE FECHA BASE DINÁMICA ---
    # --------------------------------------------------------------------------
    
    # **Añadir métrica de conteo:** Columna para contar cada actividad/fila.
    datos_base['Conteo de Actividades'] = 1 
    
    # 1. Identificar columnas candidatas a fecha
    columnas_candidatas_fecha = []
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
    # Se reordena para incluir la nueva pestaña de gráficos automáticos
    tab1, tab2, tab3_auto, tab4_gen, tab5_filtros = st.tabs([
        "📄 Datos", 
        "📈 KPIs", 
        "📊 Actividad por Tiempo", # <--- Nueva pestaña de gráficos automáticos
        "⚙️ Generador de Gráficos",
        "🔎 Filtros Avanzados"
    ])

    # ----------------------------------------------------------------------
    # --- FILTROS AVANZADOS (Se ejecuta primero para obtener datos_filtrados) ---
    # ----------------------------------------------------------------------
    with tab5_filtros:
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
        
        # Excluir 'Conteo de Actividades' del filtro/vista si no la quieren ver
        if 'Conteo de Actividades' in columnas_visibles:
            columnas_visibles.remove('Conteo de Actividades')

        with st.container():
            
            cols_per_row = 3
            num_columnas_visibles = len(columnas_ordenadas) # Usar ordenadas para iteración
            
            for i in range(0, num_columnas_visibles, cols_per_row):
                cols = st.columns(cols_per_row) 
                
                for j in range(cols_per_row):
                    col_index = i + j
                    
                    if col_index < num_columnas_visibles:
                        col = columnas_ordenadas[col_index] 
                        
                        # Excluir el filtro de 'Conteo de Actividades'
                        if col == 'Conteo de Actividades':
                            continue
                            
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
                            orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                            opciones_filtro = [d for d in orden_dias if d in valores_unicos]
                            opciones_filtro.append(" (Vacío / N/A)")
                        
                        else:
                            # Filtro tradicional o para Mes y Semana del Mes
                            opciones_filtro = [str(v) if pd.notna(v) else " (Vacío / N/A)" for v in valores_unicos]
                            if col == 'Semana del Mes':
                                sin_na = [v for v in opciones_filtro if v != " (Vacío / N/A)" and str(v).isdigit()]
                                ordenadas = sorted(sin_na, key=int)
                                opciones_filtro = ordenadas + [v for v in opciones_filtro if v == " (Vacío / N/A)"]
                            else:
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
            st.dataframe(datos_filtrados[[c for c in columnas_visibles if c != 'Conteo de Actividades']], use_container_width=True)


    # ----------------------------------------------------------------------
    # --- TABLA DE DATOS (AHORA USA DATOS FILTRADOS EN LUGAR DE BASE) ---
    # ----------------------------------------------------------------------
    with tab1:
        st.subheader("Vista de datos")
        # Aquí se usa datos_base, que es lo más común para la vista de datos base
        st.dataframe(datos_base, use_container_width=True)

    # ----------------------------------------------------------------------
    # --- KPIs (AHORA USA DATOS FILTRADOS EN LUGAR DE BASE) ---
    # ----------------------------------------------------------------------
    with tab2:
        st.subheader("Indicadores clave")
        # Usar datos_filtrados para que los KPIs reflejen el filtro
        df_kpi = datos_filtrados.copy()
        
        num_cols = df_kpi.select_dtypes(include='number').columns.tolist()
        if 'Conteo de Actividades' in num_cols:
            num_cols.remove('Conteo de Actividades') # No mostrar el conteo como KPI principal
            
        # Añadir el KPI de conteo total
        col_count, *kpi_cols = st.columns([1] + [1] * min(3, len(num_cols)))
        
        with col_count:
             st.metric(
                label="Total de Actividades Filtradas",
                value=f"{len(df_kpi):,.0f}",
                delta=f"{(len(df_kpi) / len(datos_base) * 100):.1f}% del total" if len(datos_base) > 0 else "0%"
            )
        
        # Mostrar otros KPIs numéricos
        if num_cols:
            display_cols = num_cols[:min(3, len(num_cols))]
            for i, col in enumerate(display_cols):
                with kpi_cols[i]:
                    st.metric(
                        label=f"{col} - Total",
                        value=f"{df_kpi[col].sum():,.0f}"
                    )
        else:
            if len(df_kpi) > 0:
                st.info("Solo se encontró la columna de conteo. No hay otras columnas numéricas para calcular KPIs.")

    # ----------------------------------------------------------------------
    # --- GRÁFICOS AUTOMÁTICOS POR TIEMPO (NUEVA TAB 3) ---
    # ----------------------------------------------------------------------
    with tab3_auto:
        st.subheader("Actividad por Periodo de Tiempo (Gráficos Automáticos)")
        
        if COLUMNA_FECHA_BASE is None:
            st.warning("Selecciona una Columna de Fecha Base en la sección de Configuración para ver los gráficos de tiempo.")
        elif datos_filtrados.empty:
            st.warning("No hay datos para graficar con los filtros aplicados.")
        else:
            df_plot = datos_filtrados.copy()
            
            # --- GRÁFICO 1: ACTIVIDADES POR SEMANA ---
            if 'Semana del Mes' in df_plot.columns:
                st.markdown("### Actividades por Semana del Mes")
                
                df_semana = df_plot.groupby('Semana del Mes', as_index=False)['Conteo de Actividades'].sum()
                
                orden_semana = sorted([w for w in df_semana['Semana del Mes'].unique() if str(w).isdigit()], key=int)
                
                fig_semana = px.bar(
                    df_semana,
                    x='Semana del Mes',
                    y='Conteo de Actividades',
                    title='Total de Actividades por Semana del Mes',
                    category_orders={"Semana del Mes": orden_semana},
                    text='Conteo de Actividades' # Muestra el valor sobre la barra
                )
                fig_semana.update_traces(textposition='outside', marker_color='#8e44ad')
                fig_semana.update_layout(xaxis={'categoryorder':'array', 'categoryarray':orden_semana})
                st.plotly_chart(fig_semana, use_container_width=True)
            
            # --- GRÁFICO 2: ACTIVIDADES POR DÍA DE LA SEMANA ---
            if 'Día de la Semana' in df_plot.columns:
                st.markdown("### Actividades por Día de la Semana")

                df_dia = df_plot.groupby('Día de la Semana', as_index=False)['Conteo de Actividades'].sum()
                
                orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                
                fig_dia = px.line(
                    df_dia,
                    x='Día de la Semana',
                    y='Conteo de Actividades',
                    title='Tendencia de Actividades por Día de la Semana',
                    category_orders={"Día de la Semana": orden_dias}
                )
                fig_dia.update_traces(mode='lines+markers+text', text=df_dia['Conteo de Actividades'], textposition="top center", line=dict(color='#2ecc71'))
                fig_dia.update_layout(xaxis={'categoryorder':'array', 'categoryarray':orden_dias})
                st.plotly_chart(fig_dia, use_container_width=True)


    # ----------------------------------------------------------------------
    # --- GENERADOR DE GRÁFICOS (TAB 4) ---
    # ----------------------------------------------------------------------
    with tab4_gen:
        st.subheader("Generador de gráficos (Personalizado)")
        
        # Usar datos_filtrados para que el generador respete los filtros
        columnas = datos_filtrados.columns.tolist() 
        
        col_chart, col_data = st.columns([1, 1])
        with col_chart:
            tipo_grafico = st.selectbox("Tipo de gráfico", ["Barras", "Pastel", "Líneas", "Scatter", "Box", "Área", "Histograma"])
        
        columnas_numericas = [c for c in columnas if pd.api.types.is_numeric_dtype(datos_filtrados[c])]
        
        with col_data:
            x_col = st.selectbox("Eje X", columnas)
            # Asegurar que Conteo de Actividades esté al inicio de las opciones para el Eje Y
            y_options = ['Conteo de Actividades'] + [c for c in columnas_numericas if c != 'Conteo de Actividades']
            y_col = st.selectbox("Eje Y", [None] + y_options, index=1 if 'Conteo de Actividades' in y_options else 0)
            color_col = st.selectbox("Color (opcional)", [None] + columnas)

        fig = None
        
        if datos_filtrados.empty:
            st.warning("No hay datos filtrados para generar el gráfico.")
        elif tipo_grafico in ["Barras", "Líneas", "Scatter", "Box", "Área", "Pastel"] and y_col is None:
            st.warning(f"El gráfico de {tipo_grafico} requiere que el Eje Y sea una columna numérica. Considera usar 'Conteo de Actividades'.")
        
        else:
            try:
                # Lógica para ordenar los ejes de tiempo correctamente
                orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                category_orders = {}

                if x_col == 'Día de la Semana':
                    category_orders[x_col] = orden_dias
                elif x_col == 'Semana del Mes':
                    valid_weeks = [w for w in datos_filtrados['Semana del Mes'].unique() if pd.notna(w) and str(w).isdigit()]
                    category_orders[x_col] = sorted(valid_weeks, key=int)
                
                # Generación de Gráficos
                if tipo_grafico == "Barras":
                    fig = px.bar(datos_filtrados, x=x_col, y=y_col, color=color_col, category_orders=category_orders)
                elif tipo_grafico == "Pastel":
                    fig = px.pie(datos_filtrados, names=x_col, values=y_col, color=color_col)
                elif tipo_grafico == "Líneas":
                    fig = px.line(datos_filtrados, x=x_col, y=y_col, color=color_col, category_orders=category_orders)
                elif tipo_grafico == "Scatter":
                    fig = px.scatter(datos_filtrados, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Box":
                    fig = px.box(datos_filtrados, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Área":
                    fig = px.area(datos_filtrados, x=x_col, y=y_col, color=color_col)
                elif tipo_grafico == "Histograma":
                    fig = px.histogram(datos_filtrados, x=x_col, y=y_col, color=color_col)

                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error al generar el gráfico. Verifica la combinación de ejes. Detalle: {e}")