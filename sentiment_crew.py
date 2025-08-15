# sentiment_crew.py
import os
from typing import List, Dict, Any
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from crewai_tools import tools
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import json

# Modelo para el resultado del análisis
class SentimentAnalysis(BaseModel):
    sentiment_label: str = Field(description="Categoría del sentimiento: positive, neutral, negative")
    sentiment_score: float = Field(description="Puntuación de 0 a 5 basada en el sentimiento")
    confidence: float = Field(description="Nivel de confianza del análisis (0-1)")
    reasoning: str = Field(description="Explicación del análisis realizado")

class NewsAnalyzer:
    def __init__(self, groq_api_key: str):
        """
        Inicializa el analizador de noticias con CrewAI y Groq
        """
        os.environ["GROQ_API_KEY"] = groq_api_key
        
        # Configurar el modelo LLM
        self.llm = ChatGroq(
            model="groq/llama-3.3-70b-versatile",  # Modelo potente de Groq
            temperature=0.1,  # Baja temperatura para consistencia
            max_tokens=1000
        )
        
        # Crear agentes
        self.sentiment_analyst = self._create_sentiment_analyst()
        self.quality_checker = self._create_quality_checker()
        
    def _create_sentiment_analyst(self) -> Agent:
        """Crea el agente especializado en análisis de sentimientos"""
        return Agent(
            role='Analista de Sentimientos de Noticias',
            goal='Analizar el sentimiento de titulares de noticias con alta precisión',
            backstory="""Eres un experto analista de sentimientos especializado en noticias en español.
            Tu trabajo es categorizar titulares de noticias como positivo, neutral o negativo,
            y asignar una puntuación precisa del 0 al 5. Tienes experiencia en el análisis
            de contexto periodístico y entiendes las sutilezas del lenguaje español.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            max_iter=2,
            memory=True
        )
    
    def _create_quality_checker(self) -> Agent:
        """Crea el agente verificador de calidad"""
        return Agent(
            role='Verificador de Calidad',
            goal='Verificar y validar la precisión del análisis de sentimientos',
            backstory="""Eres un supervisor experto que verifica la calidad y consistencia
            de los análisis de sentimientos. Tu trabajo es asegurar que las clasificaciones
            sean precisas y coherentes con el contenido analizado.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            max_iter=1,
            memory=True
        )
    
    def analyze_news_sentiment(self, news_data: List[Dict]) -> List[Dict]:
        """
        Analiza el sentimiento de una lista de noticias usando CrewAI
        """
        analyzed_news = []
        
        for news_item in news_data:
            titulo = news_item.get('titulo', '')
            descripcion = news_item.get('descripcion', '')
            
            # Crear tareas para el análisis
            analysis_task = Task(
                description=f"""
                Analiza el sentimiento del siguiente titular de noticia:
                
                TITULAR: "{titulo}"
                DESCRIPCIÓN: "{descripcion}"
                
                Debes:
                1. Clasificar el sentimiento como: positive, neutral, o negative
                2. Asignar una puntuación del 0 al 5:
                   - 0-1: Muy negativo
                   - 1-2: Negativo
                   - 2-3: Neutral
                   - 3-4: Positivo  
                   - 4-5: Muy positivo
                3. Explicar tu razonamiento
                4. Indicar tu nivel de confianza (0-1)
                
                Responde SOLO en formato JSON válido:
                {{
                    "sentiment_label": "positive/neutral/negative",
                    "sentiment_score": 2.5,
                    "confidence": 0.85,
                    "reasoning": "Explicación detallada del análisis"
                }}
                """,
                agent=self.sentiment_analyst,
                expected_output="JSON con análisis de sentimiento completo"
            )
            
            validation_task = Task(
                description=f"""
                Revisa y valida el siguiente análisis de sentimiento:
                
                TITULAR ORIGINAL: "{titulo}"
                ANÁLISIS PREVIO: {{analysis_result}}
                
                Verifica:
                1. ¿Es coherente la clasificación con el contenido?
                2. ¿Es apropiada la puntuación asignada?
                3. ¿Es sólido el razonamiento?
                
                Si encuentras errores, corrige el análisis.
                Responde en el mismo formato JSON.
                """,
                agent=self.quality_checker,
                expected_output="JSON validado del análisis de sentimiento",
                context=[analysis_task]
            )
            
            # Crear y ejecutar el crew
            crew = Crew(
                agents=[self.sentiment_analyst, self.quality_checker],
                tasks=[analysis_task, validation_task],
                process=Process.sequential,
                verbose=True
            )
            
            try:
                # Ejecutar el análisis
                result = crew.kickoff()
                
                # Parsear resultado
                analysis = self._parse_analysis_result(str(result))
                
                # Agregar análisis a la noticia
                analyzed_item = news_item.copy()
                analyzed_item.update({
                    'sentimiento_label': analysis['sentiment_label'],
                    'sentimiento_score': round(analysis['sentiment_score'], 4),
                    'confidence': analysis.get('confidence', 0.0),
                    'reasoning': analysis.get('reasoning', ''),
                    'analyzed_at': datetime.now().isoformat()
                })
                
                analyzed_news.append(analyzed_item)
                
            except Exception as e:
                print(f"Error analizando noticia: {e}")
                # Fallback: mantener datos originales con valores por defecto
                analyzed_item = news_item.copy()
                analyzed_item.update({
                    'sentimiento_label': 'neutral',
                    'sentimiento_score': 2.5,
                    'confidence': 0.0,
                    'reasoning': f'Error en análisis: {str(e)}',
                    'analyzed_at': datetime.now().isoformat()
                })
                analyzed_news.append(analyzed_item)
        
        return analyzed_news
    
    def _parse_analysis_result(self, result_text: str) -> Dict:
        """
        Parsea el resultado del análisis desde texto a diccionario
        """
        try:
            # Intentar extraer JSON del resultado
            import re
            json_match = re.search(r'\{[^}]*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # Validar y normalizar valores
                sentiment_label = result.get('sentiment_label', 'neutral')
                if sentiment_label not in ['positive', 'neutral', 'negative']:
                    sentiment_label = 'neutral'
                
                sentiment_score = float(result.get('sentiment_score', 2.5))
                sentiment_score = max(0.0, min(5.0, sentiment_score))  # Clamp entre 0-5
                
                return {
                    'sentiment_label': sentiment_label,
                    'sentiment_score': sentiment_score,
                    'confidence': float(result.get('confidence', 0.0)),
                    'reasoning': result.get('reasoning', 'Sin explicación disponible')
                }
        except Exception as e:
            print(f"Error parseando resultado: {e}")
        
        # Fallback por defecto
        return {
            'sentiment_label': 'neutral',
            'sentiment_score': 2.5,
            'confidence': 0.0,
            'reasoning': 'Error en el procesamiento'
        }

# Función de conveniencia para uso fácil
def analyze_sentiment_with_crewai(news_list: List[Dict], groq_api_key: str) -> List[Dict]:
    """
    Función simple para analizar sentimientos usando CrewAI
    
    Args:
        news_list: Lista de diccionarios con noticias
        groq_api_key: API key de Groq
    
    Returns:
        Lista de noticias con análisis de sentimiento añadido
    """
    analyzer = NewsAnalyzer(groq_api_key)
    return analyzer.analyze_news_sentiment(news_list)