import streamlit as st
import requests
from datetime import datetime
import plotly.express as px
import pandas as pd

# Configuración de la página
st.set_page_config(
    page_title="Análisis de sentimientos con NewsAPI + AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

# Configuración de API
API_BASE_URL = "http://localhost:8000"

def check_api_health():
    """Verifica el estado de la API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def analyze_sentiment_with_crewai(prompt: str, use_llm: bool = True):
    """
    Función para llamar a la API con análisis CrewAI
    """
    try:
        params = {
            "prompt": prompt,
            "use_llm": use_llm,
            "page_size": 10
        }
        
        response = requests.get(
            f"{API_BASE_URL}/api/news", 
            params=params, 
            timeout=120  # Timeout más largo para análisis LLM
        )
        
        if response.status_code == 200:
            data = response.json()
            
            noticias = data.get("noticias", [])
            
            if not noticias:
                return {
                    "error": "No se encontraron noticias",
                    "message": "No hay noticias disponibles para el término buscado."
                }
            
            stats = data.get("estadisticas", {})
            total_noticias = data.get("totalResults", 0)
            promedio = data.get("promedio_sentimiento", 0)
            
            # Determinar sentimiento predominante
            if stats.get("positive", 0) > stats.get("negative", 0) and stats.get("positive", 0) > stats.get("neutral", 0):
                sentimiento_general = "positivo"
            elif stats.get("negative", 0) > stats.get("positive", 0) and stats.get("negative", 0) > stats.get("neutral", 0):
                sentimiento_general = "negativo"
            else:
                sentimiento_general = "neutral"
            
            return {
                "sentimiento": sentimiento_general,
                "puntuacion": promedio,
                "analisis": f"Análisis {'con IA' if use_llm else 'básico'} de {total_noticias} noticias: {stats.get('positive', 0)} positivas, {stats.get('negative', 0)} negativas, {stats.get('neutral', 0)} neutrales.",
                "total_noticias": total_noticias,
                "noticias": noticias[:5],  # Solo las primeras 5
                "estadisticas": stats,
                "use_llm": use_llm
            }
        else:
            return {
                "error": f"Error HTTP {response.status_code}",
                "message": "Error en la API de análisis."
            }
            
    except requests.exceptions.Timeout:
        return {
            "error": "Timeout",
            "message": "El análisis con IA tomó demasiado tiempo. Intenta con menos noticias."
        }
    except requests.exceptions.ConnectionError:
        return {
            "error": "Error de conexión",
            "message": "No se pudo conectar con la API. Verifica que esté corriendo."
        }
    except Exception as e:
        return {
            "error": "Error inesperado",
            "message": f"Ocurrió un error: {str(e)}"
        }

def get_sentiment_stats(palabra_clave=None):
    """Obtiene estadísticas de la base de datos"""
    try:
        params = {}
        if palabra_clave:
            params["palabra_clave"] = palabra_clave
            
        response = requests.get(f"{API_BASE_URL}/api/stats", params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# Header de la aplicación
st.title("Análisis de sentimientos con NewsAPI + AI")
st.markdown("ChatBot usando **CrewAI** y **LLM de Groq**")

# Verificar estado de la API
health_status = check_api_health()

# Sidebar
with st.sidebar:
    st.header("🔧 Configuración")
    
    # Estado del sistema
    if health_status:
        services = health_status.get("services", {})
        st.success("✅ API Conectada")
        
        st.markdown("**Servicios disponibles:**")
        st.write(f"🗞️ NewsAPI: {'✅' if services.get('newsapi_key_configured') else '❌'}")
        st.write(f"🤖 Groq AI: {'✅' if services.get('groq_key_configured') else '❌'}")
        st.write(f"💾 Base de Datos: {'✅' if services.get('database_available') else '❌'}")
        st.write(f"👥 CrewAI: {'✅' if services.get('crewai_available') else '❌'}")
    else:
        st.error("❌ API No disponible")
        st.markdown("Verifica que la API esté corriendo en `localhost:8000`")
    
    st.divider()
    
    # Configuraciones de análisis
    st.header("⚙️ Opciones de Análisis")
    use_ai_analysis = st.toggle("Usar análisis con IA", value=True, help="Usa CrewAI con LLM de Groq para análisis más preciso")
    
    if not use_ai_analysis:
        st.warning("⚠️ Sin IA se usará análisis básico menos preciso")
    
    st.divider()
    
    # Historial
    if st.session_state.analysis_history:
        st.header("📊 Historial Reciente")
        for item in reversed(st.session_state.analysis_history[-5:]):
            with st.expander(f"🔍 {item['palabra_clave']}"):
                st.write(f"📊 **Sentimiento:** {item['sentimiento'].capitalize()}")
                st.write(f"⭐ **Puntuación:** {item['puntuacion']:.1f}/5")
                st.write(f"📰 **Noticias:** {item.get('total_noticias', 0)}")
                st.write(f"🤖 **Con IA:** {'Sí' if item.get('use_llm', False) else 'No'}")

# Crear contenedores principales
col1, col2 = st.columns([2, 1])

with col2:
    st.header("📈 Estadísticas Globales")
    
    # Obtener estadísticas generales
    global_stats = get_sentiment_stats()
    if global_stats and global_stats.get("estadisticas"):
        stats = global_stats["estadisticas"]
        
        # Crear gráfico de barras
        sentiment_data = {
            'Sentimiento': ['Positivo', 'Neutral', 'Negativo'],
            'Cantidad': [
                stats.get('positive', {}).get('count', 0),
                stats.get('neutral', {}).get('count', 0),
                stats.get('negative', {}).get('count', 0)
            ]
        }
        
        df = pd.DataFrame(sentiment_data)
        fig = px.bar(df, x='Sentimiento', y='Cantidad', 
                    color='Sentimiento',
                    color_discrete_map={
                        'Positivo': '#00CC96',
                        'Neutral': '#AB63FA', 
                        'Negativo': '#EF553B'
                    })
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        # Métricas
        total = stats.get('total_noticias', 0)
        avg_score = stats.get('overall_avg_score', 0)
        
        st.metric("Total Noticias", total)
        st.metric("Puntuación Promedio", f"{avg_score:.2f}/5")
    else:
        st.info("No hay estadísticas disponibles")

with col1:
    # Crear el contenedor del chat
    chat_container = st.container(height=500)
    
    # Chat interface
    with chat_container:
        # Mostrar historial de mensajes
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Input del usuario
    if prompt := st.chat_input("Ingresa una palabra clave para analizar noticias con IA..."):
        # Agregar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)
        
        # Respuesta del agente
        with chat_container.chat_message("assistant"):
            with st.spinner("🤖 Analizando con IA..." if use_ai_analysis else "📊 Analizando..."):
                # Llamar a la API
                result = analyze_sentiment_with_crewai(prompt, use_ai_analysis)
                
                if "error" in result:
                    response = f"❌ **Error:** {result['error']}\n\n{result['message']}"
                    st.error(response)
                else:
                    # Procesar respuesta exitosa
                    sentimiento = result.get("sentimiento", "neutral").lower()
                    puntuacion = result.get("puntuacion", 0)
                    analisis = result.get("analisis", "Análisis no disponible")
                    total_noticias = result.get("total_noticias", 0)
                    noticias_muestra = result.get("noticias", [])
                    stats = result.get("estadisticas", {})
                    use_llm = result.get("use_llm", False)
                    
                    # Formatear respuesta
                    if sentimiento == "positivo":
                        emoji = "😊"
                    elif sentimiento == "negativo":
                        emoji = "😔"
                    else:
                        emoji = "😐"
                    
                    response = f"""
**🔍 Palabra clave:** {prompt}
**🤖 Método:** {'Análisis con IA (CrewAI + Groq)' if use_llm else 'Análisis básico'}

{emoji} **Sentimiento general:** {sentimiento.capitalize()}
⭐ **Puntuación promedio:** {puntuacion:.2f}/5
📊 **Noticias analizadas:** {total_noticias}
📈 **Distribución:** {stats.get('positive', 0)} pos | {stats.get('neutral', 0)} neu | {stats.get('negative', 0)} neg

📝 **Análisis:** {analisis}

**🗞️ Ejemplos de titulares:**
"""
                    
                    # Agregar ejemplos de titulares
                    for i, noticia in enumerate(noticias_muestra, 1):
                        sent_label = noticia.get("sentimiento_label", "neutral")
                        sent_emoji = "😊" if sent_label == "positive" else "😔" if sent_label == "negative" else "😐"
                        score = noticia.get("sentimiento_score", 0)
                        fuente = noticia.get("fuente", "Desconocida")
                        
                        response += f"\n{i}. {sent_emoji} **{noticia['titulo']}** ({score:.1f}/5)\n   *{fuente}*"
                    
                    st.markdown(response)
                    
                    # Agregar al historial local
                    st.session_state.analysis_history.append({
                        "fecha": datetime.now(),
                        "palabra_clave": prompt,
                        "sentimiento": sentimiento,
                        "puntuacion": puntuacion,
                        "total_noticias": total_noticias,
                        "use_llm": use_llm
                    })
        
        # Agregar respuesta del agente al historial
        st.session_state.messages.append({"role": "assistant", "content": response})

# Controles en la parte inferior
st.divider()

col1, col2, col3= st.columns(3)

with col1:
    if st.button("🗑️ Limpiar Chat"):
        st.session_state.messages = []
        st.rerun()

with col2:
    if st.button("🔄 Test API"):
        with st.spinner("Probando conexión..."):
            health = check_api_health()
            if health:
                st.success("✅ API funcionando correctamente")
            else:
                st.error("❌ API no disponible")

with col3:
    if st.button("📊 Actualizar Stats"):
        st.rerun()


# Footer
st.divider()
st.markdown("*Hecho por Joaquin Papagianacopoulos & Lucas Bigiatti*")