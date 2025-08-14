import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Noticias",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de la base de datos
@st.cache_resource
def init_connection():
    """Inicializar conexión a MySQL usando SQLAlchemy"""
    try:
        # Crear string de conexión
        connection_string = (
            f"mysql+pymysql://"
            f"{st.secrets['mysql']['user']}:"
            f"{st.secrets['mysql']['password']}@"
            f"{st.secrets['mysql']['host']}:"
            f"{st.secrets['mysql']['port']}/"
            f"{st.secrets['mysql']['database']}"
            f"?charset=utf8mb4"
        )
        
        # Crear engine de SQLAlchemy
        engine = create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        
        # Probar la conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return engine
        
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return None

# Función para cargar noticias desde la base de datos
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_news_data():
    """Cargar noticias desde MySQL"""
    engine = init_connection()
    if engine is None:
        return pd.DataFrame()  # Retornar DataFrame vacío si no hay conexión
    
    try:
        query = """
        SELECT 
            id,
            fecha,
            fuente,
            autor,
            url,
            titulo,
            descripcion,
            contenido,
            palabra_clave,
            sentimiento_label,
            sentimiento_score,
            idioma
        FROM noticias 
        ORDER BY fecha DESC
        """
        
        # Usar SQLAlchemy engine directamente
        df = pd.read_sql(query, engine)
        
        # Convertir fecha a datetime si no lo está
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Mapear sentimientos al español
        sentiment_mapping = {
            'positive': 'Positivo',
            'neutral': 'Neutro', 
            'negative': 'Negativo'
        }
        df['sentimiento'] = df['sentimiento_label'].map(sentiment_mapping)
        
        return df
        
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

# Función para refrescar datos
def refresh_news():
    """Limpiar cache y refrescar datos"""
    st.cache_data.clear()
    st.success("¡Base de datos consultada y datos actualizados!")
    st.rerun()

# Cargar datos desde la base de datos
df = load_news_data()

# Panel de diagnóstico (temporal)
with st.expander("🔍 Diagnóstico de Conexión", expanded=True):
    st.write("**Estado de la conexión:**")
    
    # Probar conexión
    engine = init_connection()
    if engine is not None:
        st.success("✅ Conexión a la base de datos establecida")
        
        try:
            # Probar consulta simple
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) as total FROM noticias"))
                count = result.fetchone()[0]
                st.info(f"📊 Total de registros en la tabla 'noticias': {count}")
                
                if count > 0:
                    # Mostrar algunos datos de ejemplo
                    sample_query = text("SELECT fecha, fuente, titulo, sentimiento_label FROM noticias ORDER BY fecha DESC LIMIT 3")
                    sample_result = conn.execute(sample_query)
                    sample_data = sample_result.fetchall()
                    
                    st.write("**Últimas 3 noticias en la BD:**")
                    for row in sample_data:
                        st.write(f"- {row[0]} | {row[1]} | {row[2][:50]}... | {row[3]}")
                else:
                    st.warning("⚠️ La tabla 'noticias' está vacía")
                    
        except Exception as e:
            st.error(f"❌ Error ejecutando consulta: {e}")
            st.write("**Posibles causas:**")
            st.write("- La tabla 'noticias' no existe")
            st.write("- Permisos insuficientes")
            st.write("- Base de datos incorrecta")
    else:
        st.error("❌ No se pudo establecer conexión a la base de datos")
        st.write("**Verifica:**")
        st.write("- Archivo .streamlit/secrets.toml existe")
        st.write("- Credenciales correctas")
        st.write("- Servidor MySQL corriendo")
        st.write("- Puerto correcto")

# Verificar si hay datos
if df.empty:
    st.error("❌ No se pudieron cargar datos de la base de datos o la tabla está vacía.")
    st.write("👆 Revisa el panel de diagnóstico arriba para más detalles.")
    st.stop()
else:
    st.success(f"✅ Datos cargados correctamente: {len(df)} noticias encontradas")

# TÍTULO PRINCIPAL
st.title("📰 Análisis de Sentimientos en Noticias")
st.markdown("---")

# BARRA LATERAL CON FILTROS
st.sidebar.header("🔍 Filtros")

# Filtro por fecha
min_date = df['fecha'].min().date()
max_date = df['fecha'].max().date()

# Calcular fecha de inicio por defecto (30 días antes del máximo, pero no antes del mínimo)
default_start = max(min_date, max_date - timedelta(days=30))

fecha_inicio = st.sidebar.date_input(
    "Fecha inicio",
    value=default_start,
    min_value=min_date,
    max_value=max_date
)

fecha_fin = st.sidebar.date_input(
    "Fecha fin",
    value=max_date,
    min_value=min_date,
    max_value=max_date
)

# Filtro por sentimiento
sentimientos_seleccionados = st.sidebar.multiselect(
    "Sentimiento",
    options=df['sentimiento'].unique(),
    default=df['sentimiento'].unique()
)

# Filtro por fuente (obtener fuentes únicas de la BD)
fuentes_disponibles = df['fuente'].dropna().unique().tolist()
fuentes_seleccionadas = st.sidebar.multiselect(
    "Fuente",
    options=sorted(fuentes_disponibles) if fuentes_disponibles else [],
    default=sorted(fuentes_disponibles) if fuentes_disponibles else []
)

# Filtro por palabra clave (buscar en título y palabra_clave)
palabra_clave = st.sidebar.text_input("Palabra clave en título o descripción")

# Filtro por autor
autores_disponibles = df['autor'].dropna().unique().tolist()
if autores_disponibles:
    autores_seleccionados = st.sidebar.multiselect(
        "Autor",
        options=sorted(autores_disponibles),
        default=[]
    )

# Botón de refresco
if st.sidebar.button("🔄 Refrescar Noticias", type="primary"):
    refresh_news()

# APLICAR FILTROS
df_filtrado = df.copy()

# Filtrar por fecha
df_filtrado = df_filtrado[
    (df_filtrado['fecha'].dt.date >= fecha_inicio) & 
    (df_filtrado['fecha'].dt.date <= fecha_fin)
]

# Filtrar por sentimiento
if sentimientos_seleccionados:
    df_filtrado = df_filtrado[df_filtrado['sentimiento'].isin(sentimientos_seleccionados)]

# Filtrar por fuente
if fuentes_seleccionadas:
    df_filtrado = df_filtrado[df_filtrado['fuente'].isin(fuentes_seleccionadas)]

# Filtrar por palabra clave (buscar en título, descripción y palabra_clave)
if palabra_clave:
    mask_titulo = df_filtrado['titulo'].str.contains(palabra_clave, case=False, na=False)
    mask_descripcion = df_filtrado['descripcion'].str.contains(palabra_clave, case=False, na=False)
    mask_keyword = df_filtrado['palabra_clave'].str.contains(palabra_clave, case=False, na=False)
    df_filtrado = df_filtrado[mask_titulo | mask_descripcion | mask_keyword]

# Filtrar por autor
if 'autores_seleccionados' in locals() and autores_seleccionados:
    df_filtrado = df_filtrado[df_filtrado['autor'].isin(autores_seleccionados)]

# MÉTRICAS RÁPIDAS
st.header("📊 Métricas Rápidas")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_noticias = len(df_filtrado)
    st.metric("Total de Noticias", total_noticias)

with col2:
    noticias_positivas = len(df_filtrado[df_filtrado['sentimiento'] == 'Positivo'])
    st.metric("Noticias Positivas", noticias_positivas, 
              delta=f"{(noticias_positivas/total_noticias*100):.1f}%" if total_noticias > 0 else "0%")

with col3:
    noticias_negativas = len(df_filtrado[df_filtrado['sentimiento'] == 'Negativo'])
    st.metric("Noticias Negativas", noticias_negativas,
              delta=f"{(noticias_negativas/total_noticias*100):.1f}%" if total_noticias > 0 else "0%")

with col4:
    if not df_filtrado.empty:
        noticia_mas_reciente = df_filtrado['fecha'].max().strftime('%d/%m/%Y')
        st.metric("Noticia más Reciente", noticia_mas_reciente)
    else:
        st.metric("Noticia más Reciente", "N/A")

# VISUALIZACIÓN DE DATOS
st.header("📈 Visualización de Datos")

if not df_filtrado.empty:
    # Crear tabs para diferentes visualizaciones
    tab1, tab2, tab3 = st.tabs(["Distribución por Día", "Distribución General", "Análisis por Fuente"])
    
    with tab1:
        # Gráfico de distribución de sentimientos por día
        df_por_dia = df_filtrado.groupby([df_filtrado['fecha'].dt.date, 'sentimiento']).size().unstack(fill_value=0)
        
        if not df_por_dia.empty:
            fig_linea = px.line(
                df_por_dia.reset_index(), 
                x='fecha', 
                y=df_por_dia.columns.tolist(),
                title="Distribución de Sentimientos por Día",
                labels={'fecha': 'Fecha', 'value': 'Cantidad de Noticias'},
                color_discrete_map={
                    'Positivo': '#2E8B57',
                    'Neutro': '#4682B4', 
                    'Negativo': '#DC143C'
                }
            )
            fig_linea.update_layout(height=400)
            st.plotly_chart(fig_linea, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de torta
            sentimiento_counts = df_filtrado['sentimiento'].value_counts()
            fig_pie = px.pie(
                values=sentimiento_counts.values,
                names=sentimiento_counts.index,
                title="Distribución de Sentimientos",
                color_discrete_map={
                    'Positivo': '#2E8B57',
                    'Neutro': '#4682B4',
                    'Negativo': '#DC143C'
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Gráfico de barras por fuente
            fuente_counts = df_filtrado['fuente'].value_counts()
            fig_bar = px.bar(
                x=fuente_counts.values,
                y=fuente_counts.index,
                orientation='h',
                title="Noticias por Fuente",
                labels={'x': 'Cantidad', 'y': 'Fuente'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with tab3:
        # Análisis de sentimientos por fuente
        df_fuente_sentimiento = df_filtrado.groupby(['fuente', 'sentimiento']).size().unstack(fill_value=0)
        
        if not df_fuente_sentimiento.empty:
            fig_stack = px.bar(
                df_fuente_sentimiento.reset_index(),
                x='fuente',
                y=['Positivo', 'Neutro', 'Negativo'],
                title="Análisis de Sentimientos por Fuente",
                labels={'fuente': 'Fuente', 'value': 'Cantidad'},
                color_discrete_map={
                    'Positivo': '#2E8B57',
                    'Neutro': '#4682B4',
                    'Negativo': '#DC143C'
                }
            )
            st.plotly_chart(fig_stack, use_container_width=True)

# LISTA DE NOTICIAS FILTRADAS
st.header("📋 Lista de Noticias")

if not df_filtrado.empty:
    # Ordenar por fecha más reciente
    df_mostrar = df_filtrado.sort_values('fecha', ascending=False)
    
    # Mostrar cantidad de resultados
    st.write(f"Mostrando {len(df_mostrar)} noticias")
    
    # Crear un DataFrame para mostrar con información más completa
    for idx, row in df_mostrar.head(20).iterrows():  # Mostrar solo las primeras 20
        with st.expander(f"📰 {row['titulo'][:100]}{'...' if len(row['titulo']) > 100 else ''} - {row['fecha'].strftime('%d/%m/%Y %H:%M')}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if pd.notna(row['descripcion']):
                    st.write(f"**Descripción:** {row['descripcion']}")
                
                if pd.notna(row['autor']):
                    st.write(f"**Autor:** {row['autor']}")
                
                if pd.notna(row['palabra_clave']):
                    st.write(f"**Palabra clave:** {row['palabra_clave']}")
                
                if pd.notna(row['url']):
                    st.write(f"**URL:** [Ver noticia completa]({row['url']})")
                
            with col2:
                if pd.notna(row['fuente']):
                    st.write(f"**Fuente:** {row['fuente']}")
                
                # Score de sentimiento
                score = row['sentimiento_score'] if pd.notna(row['sentimiento_score']) else 0
                st.write(f"**Score:** {score:.3f}")
                
                # Color del sentimiento
                if row['sentimiento'] == 'Positivo':
                    st.success(f"**Sentimiento:** {row['sentimiento']}")
                elif row['sentimiento'] == 'Negativo':
                    st.error(f"**Sentimiento:** {row['sentimiento']}")
                else:
                    st.info(f"**Sentimiento:** {row['sentimiento']}")
    
    # Paginación básica
    if len(df_mostrar) > 20:
        st.info(f"Mostrando las 20 noticias más recientes de {len(df_mostrar)} total")
        
else:
    st.warning("No se encontraron noticias con los filtros aplicados.")

# PIE DE PÁGINA
st.markdown("---")
st.markdown("*Desarrollado con Streamlit - Análisis de Sentimientos en Noticias*")