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
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

else:
    st.sidebar.success(f"Bienvenido {st.session_state.usuario} ({st.session_state.rol})")
    st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update({"login": False, "rol": None}), key="logout_btn")

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
            st.rerun() # Rerun para consolidar datos inmediatamente

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
        
        # ⬇️ NUEVA FUNCIONALIDAD: ELIMINAR TODOS Y VACIAR DASHBOARD
        st.sidebar.markdown("---")
        if archivos_actuales and st.sidebar.button("🔴 Eliminar TODOS los archivos", key="del_all"):
            archivos_eliminados_count = len(archivos_actuales)
            
            # 1. Eliminar todos los archivos de la carpeta de subidas
            for f in archivos_actuales:
                os.remove(os.path.join(UPLOAD_FOLDER, f))
            
            # 2. Eliminar el archivo maestro consolidado para garantizar un dashboard vacío
            if os.path.exists(MASTER_EXCEL):
                os.remove(MASTER_EXCEL)
            
            st.sidebar.success(f"{archivos_eliminados_count} archivos eliminados y Master Excel borrado. Dashboard vacío.")
            st.rerun()
        elif not archivos_actuales:
             st.sidebar.info("La carpeta de subidas está vacía.")
        # ⬆️ FIN NUEVA FUNCIONALIDAD


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
        # Intenta cargar el master solo si no hay archivos en UPLOAD_FOLDER
        try:
            datos = pd.read_excel(MASTER_EXCEL)
        except FileNotFoundError:
            # Esto es lo que se mostrará cuando se eliminen todos los archivos
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


    # --- FILTROS AVANZADOS ---
    with tab4:
        st.subheader("Filtros dinámicos")
        datos_filtrados = datos.copy()
        
        with st.expander("Selecciona los filtros por columna"):
            for col in datos.columns:
                try:
                    valores = datos[col].dropna().unique().tolist()
                    if len(valores) <= 50:
                        seleccion = st.multiselect(f"Filtrar {col}", valores, default=valores, key=f"filter_{col}")
                        if seleccion:
                            datos_filtrados = datos_filtrados[datos_filtrados[col].isin(seleccion)]
                except TypeError:
                    st.warning(f"No se pudo aplicar el filtro a la columna '{col}' debido a tipos de datos complejos.")
                    
        st.subheader("Resultado Filtrado")
        st.dataframe(datos_filtrados, use_container_width=True)