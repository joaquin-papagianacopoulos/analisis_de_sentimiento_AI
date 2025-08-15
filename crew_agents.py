import os
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_groq import ChatGroq
from typing import Dict, Any
import json
from datetime import datetime

# Configurar Groq como LLM
def setup_llm():
    """Configurar Groq LLM para los agentes"""
    return ChatGroq(
        model="groq/llama-3.3-70b-versatile",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1
    )

# Herramienta personalizada para análisis de sentimientos
class SentimentAnalysisTool(BaseTool):
    name: str = "sentiment_analyzer"
    description: str = "Analiza el sentimiento de un texto y proporciona una puntuación del 0 al 5"
    
    def _run(self, text: str) -> str:
        """Ejecutar análisis básico de sentimientos"""
        # Palabras clave para clasificación básica
        positive_words = ['bueno', 'excelente', 'positivo', 'crecimiento', 'éxito', 'logro', 'mejora', 'beneficio']
        negative_words = ['malo', 'crisis', 'problema', 'conflicto', 'caída', 'pérdida', 'daño', 'riesgo']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Calcular puntuación básica
        if positive_count > negative_count:
            score = min(5.0, 3.0 + positive_count * 0.5)
            sentiment = "positivo"
        elif negative_count > positive_count:
            score = max(0.0, 2.0 - negative_count * 0.5)
            sentiment = "negativo"
        else:
            score = 2.5
            sentiment = "neutral"
            
        return f"Sentimiento: {sentiment}, Puntuación: {score}"

# Agente Analista Principal
def create_sentiment_analyst():
    """Crear agente analista de sentimientos"""
    return Agent(
        role='Analista de Sentimientos Senior',
        goal='Analizar objetivamente el sentimiento de títulos de noticias y proporcionar una evaluación precisa',
        backstory="""Eres un analista de sentimientos senior con 10 años de experiencia en análisis de medios.
        Tu especialidad es evaluar títulos de noticias de manera completamente objetiva y fría, sin dejarte 
        llevar por emociones personales. Tienes experiencia específica en medios latinoamericanos.""",
        verbose=True,
        allow_delegation=True,
        llm=setup_llm(),
        tools=[SentimentAnalysisTool()]
    )

# Agente Validador
def create_sentiment_validator():
    """Crear agente validador de análisis"""
    return Agent(
        role='Validador de Análisis',
        goal='Verificar y refinar el análisis de sentimientos para asegurar precisión',
        backstory="""Eres un especialista en control de calidad para análisis de sentimientos.
        Tu trabajo es revisar análisis de otros agentes y asegurar que sean precisos, objetivos
        y sigan los criterios establecidos. Tienes experiencia en validación de datos textuales.""",
        verbose=True,
        allow_delegation=False,
        llm=setup_llm()
    )

# Agente Explicador
def create_sentiment_explainer():
    """Crear agente que explica el razonamiento"""
    return Agent(
        role='Explicador de Análisis',
        goal='Proporcionar explicaciones claras y concisas del análisis realizado',
        backstory="""Eres un comunicador experto que toma análisis técnicos complejos y los
        convierte en explicaciones claras y comprensibles. Tu especialidad es explicar 
        razonamientos de análisis de sentimientos de manera concisa pero informativa.""",
        verbose=True,
        allow_delegation=False,
        llm=setup_llm()
    )

# Tareas para los agentes
def create_analysis_task(titulo: str):
    """Crear tarea de análisis principal"""
    return Task(
        description=f"""
        Analiza el sentimiento del siguiente título de noticia de manera completamente objetiva:
        
        Título: "{titulo}"
        
        Criterios de evaluación:
        - Positivo (3.1-5.0): Títulos que indican logros, mejoras, noticias favorables
        - Neutral (1.5-3.0): Títulos informativos sin carga emocional clara
        - Negativo (0.0-1.4): Títulos que indican problemas, crisis, conflictos
        
        Proporciona:
        1. Clasificación: positivo, neutral, o negativo
        2. Puntuación numérica del 0.0 al 5.0
        3. Justificación breve de tu análisis
        
        Sé completamente objetivo y analítico en tu evaluación.
        """,
        expected_output="Análisis de sentimiento con clasificación, puntuación y justificación",
        agent=create_sentiment_analyst()
    )

def create_validation_task():
    """Crear tarea de validación"""
    return Task(
        description="""
        Revisa el análisis de sentimiento realizado por el analista principal.
        
        Verifica:
        1. Que la clasificación (positivo/neutral/negativo) sea apropiada
        2. Que la puntuación esté en el rango correcto para la clasificación
        3. Que la justificación sea lógica y objetiva
        
        Si encuentras errores, corrígelos y explica por qué.
        Si el análisis es correcto, confirma su validez.
        """,
        expected_output="Validación del análisis con correcciones si es necesario",
        agent=create_sentiment_validator()
    )

def create_explanation_task():
    """Crear tarea de explicación"""
    return Task(
        description="""
        Toma el análisis validado y crea una explicación clara y concisa.
        
        La explicación debe:
        1. Ser comprensible para usuarios no técnicos
        2. Mencionar los elementos clave que influenciaron la clasificación
        3. Ser breve pero informativa (máximo 2-3 oraciones)
        
        Mantén un tono profesional y objetivo.
        """,
        expected_output="Explicación clara y concisa del análisis de sentimiento",
        agent=create_sentiment_explainer()
    )

# Función principal para ejecutar el análisis
def analyze_sentiment_crew(titulo: str) -> Dict[str, Any]:
    """
    Ejecutar análisis de sentimiento usando CrewAI
    
    Args:
        titulo: Título de noticia a analizar
        
    Returns:
        Dict con sentimiento, puntuación y análisis
    """
    try:
        # Crear agentes
        analyst = create_sentiment_analyst()
        validator = create_sentiment_validator()
        explainer = create_sentiment_explainer()
        
        # Crear tareas
        analysis_task = create_analysis_task(titulo)
        validation_task = create_validation_task()
        explanation_task = create_explanation_task()
        
        # Crear crew
        crew = Crew(
            agents=[analyst, validator, explainer],
            tasks=[analysis_task, validation_task, explanation_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Ejecutar análisis
        result = crew.kickoff()
        
        # Procesar resultado (assumiendo que viene en formato texto)
        result_text = str(result)
        
        # Extraer información del resultado
        # Nota: Esto puede necesitar ajustes según el formato exacto de salida
        sentimiento = extract_sentiment_from_result(result_text)
        puntuacion = extract_score_from_result(result_text)
        analisis = extract_explanation_from_result(result_text)
        
        return {
            "sentimiento": sentimiento,
            "puntuacion": puntuacion,
            "analisis": analisis,
            "timestamp": datetime.now().isoformat(),
            "titulo_analizado": titulo
        }
        
    except Exception as e:
        return {
            "error": "Error en CrewAI",
            "message": str(e),
            "sentimiento": "neutral",
            "puntuacion": 2.5,
            "analisis": "Error en el análisis"
        }

# Funciones auxiliares para extraer información
def extract_sentiment_from_result(text: str) -> str:
    """Extraer sentimiento del resultado"""
    text_lower = text.lower()
    if "positivo" in text_lower and "negativo" not in text_lower:
        return "positivo"
    elif "negativo" in text_lower:
        return "negativo"
    else:
        return "neutral"

def extract_score_from_result(text: str) -> float:
    """Extraer puntuación del resultado"""
    import re
    # Buscar números decimales en el texto
    scores = re.findall(r'\b([0-4]\.?\d?|5\.0?)\b', text)
    if scores:
        try:
            score = float(scores[-1])  # Tomar la última puntuación encontrada
            return max(0.0, min(5.0, score))
        except ValueError:
            pass
    return 2.5  # Valor por defecto

def extract_explanation_from_result(text: str) -> str:
    """Extraer explicación del resultado"""
    # Simplemente devolver el texto completo limpio
    # Puedes ajustar esto según el formato de salida de tu crew
    lines = text.split('\n')
    explanation_lines = [line.strip() for line in lines if line.strip()]
    return ' '.join(explanation_lines[:3])  # Primeras 3 líneas

# Función de prueba
def test_analysis():
    """Función de prueba para el sistema"""
    test_titles = [
        "Economía argentina muestra signos de recuperación tras crisis",
        "Nuevo conflicto social genera tensión en la región",
        "Presentación de resultados financieros del tercer trimestre"
    ]
    
    for title in test_titles:
        print(f"\n--- Analizando: {title} ---")
        result = analyze_sentiment_crew(title)
        print(f"Resultado: {result}")

if __name__ == "__main__":
    # Establecer variable de entorno (para pruebas)
    # os.environ["GROQ_API_KEY"] = "tu_api_key_aqui"
    
    # Ejecutar prueba
    test_analysis()