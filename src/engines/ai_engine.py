"""
AI Engine - Motor de Inteligencia Artificial
==============================================
Este módulo gestiona la comunicación con diferentes proveedores de IA
(DeepSeek, OpenAI, Gemini) para el análisis de mercado y toma de decisiones.

Autor: Trading Bot System
Versión: 1.0
"""

import json
import os
from typing import Dict, Any, Optional
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv
import yaml
import logging

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)


class AIEngine:
    """
    Motor de IA que soporta múltiples proveedores (DeepSeek, OpenAI, Gemini).
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Inicializa el motor de IA.

        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.config = self._load_config(config_path)
        self.provider = self.config['ai_provider']
        self.model = self.config['ai_model']

        # Arquitectura híbrida: modelos para diferentes tareas
        self.model_fast = self.config.get('ai_model_fast', self.model)  # DeepSeek-V3/chat
        self.model_deep = self.config.get('ai_model_deep', self.model)  # DeepSeek-R1/reasoner
        self.use_hybrid = self.config.get('ai_use_hybrid_analysis', False)

        self.client = None

        self._initialize_provider()

        if self.use_hybrid:
            logger.info(f"AI Engine inicializado en MODO HÍBRIDO:")
            logger.info(f"  - Filtrado rápido: {self.model_fast}")
            logger.info(f"  - Decisión profunda: {self.model_deep}")
        else:
            logger.info(f"AI Engine inicializado: {self.provider} - {self.model}")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga la configuración desde el archivo YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            raise

    def _initialize_provider(self):
        """Inicializa el cliente del proveedor de IA seleccionado."""
        try:
            if self.provider == 'deepseek':
                api_key = os.getenv('DEEPSEEK_API_KEY')
                if not api_key:
                    raise ValueError("DEEPSEEK_API_KEY no encontrada en .env")
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com"
                )
                logger.info("DeepSeek API inicializada correctamente")

            elif self.provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY no encontrada en .env")
                self.client = OpenAI(api_key=api_key)
                logger.info("OpenAI API inicializada correctamente")

            elif self.provider == 'gemini':
                api_key = os.getenv('GEMINI_API_KEY')
                if not api_key:
                    raise ValueError("GEMINI_API_KEY no encontrada en .env")
                genai.configure(api_key=api_key)
                self.model_instance = genai.GenerativeModel(self.model)
                logger.info("Gemini API inicializada correctamente")

            else:
                raise ValueError(f"Proveedor de IA no soportado: {self.provider}")

        except Exception as e:
            logger.error(f"Error inicializando proveedor de IA: {e}")
            raise

    def analyze_market(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analiza los datos del mercado y retorna una decisión de trading.

        Args:
            market_data: Diccionario con datos técnicos del mercado

        Returns:
            Diccionario con la decisión, razonamiento y parámetros
        """
        try:
            prompt = self._build_analysis_prompt(market_data)
            response_text = self._get_ai_response(prompt)

            # Parsear la respuesta JSON de la IA
            decision = self._parse_ai_response(response_text)

            logger.info(f"Análisis completado - Decisión: {decision.get('decision', 'UNKNOWN')}")
            return decision

        except Exception as e:
            logger.error(f"Error en análisis de mercado: {e}")
            return None

    def _build_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """
        Construye el prompt para el análisis de mercado.

        Args:
            market_data: Datos del mercado

        Returns:
            Prompt estructurado para la IA
        """
        prompt = f"""
Eres un trader institucional experto con 20 años de experiencia en gestión de riesgos y análisis cuantitativo.
Tu tarea es analizar los siguientes datos del mercado y proporcionar una decisión de trading.

=== DATOS DEL MERCADO ===
Símbolo: {market_data.get('symbol', 'N/A')}
Precio Actual: {market_data.get('current_price', 'N/A')}
Tipo de Mercado: {market_data.get('market_type', 'N/A')}

=== INDICADORES TÉCNICOS ===
RSI (14): {market_data.get('rsi', 'N/A')}
EMA 50: {market_data.get('ema_50', 'N/A')}
EMA 200: {market_data.get('ema_200', 'N/A')}
MACD: {market_data.get('macd', 'N/A')}
Señal MACD: {market_data.get('macd_signal', 'N/A')}
Bandas de Bollinger (Superior, Media, Inferior): {market_data.get('bollinger_bands', 'N/A')}
ATR: {market_data.get('atr', 'N/A')}
Volumen (últimas 24h): {market_data.get('volume_24h', 'N/A')}

=== TENDENCIA ===
{market_data.get('trend_analysis', 'No disponible')}

=== INSTRUCCIONES ===
Analiza estos datos y responde ESTRICTAMENTE en el siguiente formato JSON:

{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0 - 1.0,
    "razonamiento": "Explicación breve y técnica de tu decisión",
    "stop_loss_sugerido": "precio numérico",
    "take_profit_sugerido": "precio numérico",
    "tamaño_posicion_sugerido": "porcentaje del capital (1-5)",
    "alertas": ["lista de riesgos o advertencias identificadas"]
}}

REGLAS IMPORTANTES:
1. SOLO responde con el JSON, sin texto adicional
2. Sé conservador - es mejor esperar que perder dinero
3. Si hay señales contradictorias, siempre elige "ESPERA"
4. El stop loss debe ser razonable (2-5% del precio)
5. El ratio riesgo/beneficio debe ser mínimo 1:1.5

RESPONDE AHORA:
"""
        return prompt

    def _get_ai_response(self, prompt: str) -> str:
        """
        Obtiene la respuesta del proveedor de IA.

        Args:
            prompt: Prompt a enviar a la IA

        Returns:
            Respuesta en texto de la IA
        """
        try:
            if self.provider in ['deepseek', 'openai']:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un trader profesional experto en análisis técnico y gestión de riesgos. Respondes siempre en formato JSON válido."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,  # Baja temperatura para respuestas más deterministas
                    max_tokens=1000
                )
                return response.choices[0].message.content

            elif self.provider == 'gemini':
                response = self.model_instance.generate_content(prompt)
                return response.text

        except Exception as e:
            logger.error(f"Error obteniendo respuesta de IA: {e}")
            raise

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parsea la respuesta de la IA y extrae el JSON.

        Args:
            response_text: Texto de respuesta de la IA

        Returns:
            Diccionario con la decisión parseada
        """
        try:
            # Intentar encontrar el JSON en la respuesta
            # Algunas IAs agregan texto antes o después del JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                logger.warning("No se encontró JSON en la respuesta de la IA")
                return {
                    "decision": "ESPERA",
                    "confidence": 0.0,
                    "razonamiento": "Error parseando respuesta de IA",
                    "alertas": ["Formato de respuesta inválido"]
                }

            json_str = response_text[start_idx:end_idx]
            decision_data = json.loads(json_str)

            # Validar campos requeridos
            required_fields = ['decision', 'razonamiento']
            for field in required_fields:
                if field not in decision_data:
                    logger.warning(f"Campo requerido '{field}' no encontrado en respuesta")
                    decision_data[field] = "N/A"

            # Normalizar la decisión
            decision_data['decision'] = decision_data['decision'].upper()
            if decision_data['decision'] not in ['COMPRA', 'VENTA', 'ESPERA']:
                logger.warning(f"Decisión inválida: {decision_data['decision']}")
                decision_data['decision'] = 'ESPERA'

            return decision_data

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de IA: {e}")
            logger.debug(f"Respuesta completa: {response_text}")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": "Error parseando respuesta JSON",
                "alertas": [f"JSONDecodeError: {str(e)}"]
            }

    def analyze_market_hybrid(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Análisis híbrido de dos niveles (estrategia óptima para reducir costos).

        Nivel 1: Filtrado rápido con modelo chat (DeepSeek-V3 / GPT-4o-mini)
                 Detecta si hay oportunidad potencial.

        Nivel 2: Razonamiento profundo con modelo reasoner (DeepSeek-R1 / o1)
                 Solo se ejecuta si el filtro detecta oportunidad.

        Args:
            market_data: Diccionario con datos técnicos del mercado

        Returns:
            Diccionario con la decisión final, o None si no hay oportunidad
        """
        logger.info("=== ANÁLISIS HÍBRIDO DE DOS NIVELES ===")

        # NIVEL 1: Filtrado Rápido (Modelo Chat - Económico)
        logger.info(f"Nivel 1: Filtrado rápido con {self.model_fast}")

        quick_decision = self._quick_filter_analysis(market_data)

        if not quick_decision:
            logger.warning("Filtro rápido falló")
            return None

        is_interesting = quick_decision.get('is_interesting', False)
        quick_signal = quick_decision.get('signal', 'ESPERA')

        logger.info(f"Filtro rápido: {quick_signal} (Interesante: {is_interesting})")

        # Si no es interesante, retornar ESPERA sin gastar créditos en R1
        if not is_interesting or quick_signal == 'ESPERA':
            logger.info("❌ Oportunidad descartada por filtro rápido - Ahorrando créditos")
            return {
                "decision": "ESPERA",
                "confidence": quick_decision.get('confidence', 0.3),
                "razonamiento": quick_decision.get('reason', 'Descartado en filtro inicial'),
                "analysis_type": "quick_filter_only"
            }

        # NIVEL 2: Análisis Profundo (Modelo Reasoner - Solo si vale la pena)
        logger.info(f"✅ Oportunidad detectada! Nivel 2: Razonamiento profundo con {self.model_deep}")

        deep_decision = self._deep_reasoning_analysis(market_data, quick_decision)

        if deep_decision:
            deep_decision['analysis_type'] = 'hybrid_two_level'
            deep_decision['quick_filter_signal'] = quick_signal
            logger.info(f"Decisión final (híbrido): {deep_decision.get('decision', 'UNKNOWN')}")

        return deep_decision

    def _quick_filter_analysis(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Filtro rápido - Detecta si hay señal técnica interesante.
        Usa modelo chat (rápido y barato).
        """
        prompt = f"""
Eres un filtro técnico rápido. Analiza estos datos de {market_data.get('symbol', 'N/A')}:

DATOS:
- Precio: {market_data.get('current_price', 'N/A')}
- RSI: {market_data.get('rsi', 'N/A')}
- EMA 50: {market_data.get('ema_50', 'N/A')} | EMA 200: {market_data.get('ema_200', 'N/A')}
- MACD: {market_data.get('macd', 'N/A')} | Señal: {market_data.get('macd_signal', 'N/A')}
- Volatilidad: {market_data.get('volatility_level', 'N/A')}

TAREA: Detectar si hay oportunidad técnica clara (COMPRA/VENTA) o si debemos ESPERAR.

Responde SOLO en JSON:
{{
    "is_interesting": true/false,
    "signal": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0-1.0,
    "reason": "breve explicación"
}}

REGLA: Solo di "is_interesting: true" si hay señal técnica CLARA y FUERTE.
"""

        try:
            if self.provider in ['deepseek', 'openai']:
                response = self.client.chat.completions.create(
                    model=self.model_fast,
                    messages=[
                        {"role": "system", "content": "Eres un filtro técnico rápido. Solo JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=150
                )
                content = response.choices[0].message.content

                # Parsear JSON
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)

        except Exception as e:
            logger.error(f"Error en filtro rápido: {e}")
            return None

    def _deep_reasoning_analysis(
        self,
        market_data: Dict[str, Any],
        quick_decision: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Análisis profundo con razonamiento (DeepSeek-R1 o OpenAI o1).
        Solo se llama cuando el filtro detectó oportunidad.
        """
        prompt = f"""
Eres un trader institucional profesional. El filtro técnico detectó una posible oportunidad en {market_data.get('symbol')}:

SEÑAL PRELIMINAR: {quick_decision.get('signal')}
RAZÓN: {quick_decision.get('reason')}

DATOS COMPLETOS DEL MERCADO:
- Símbolo: {market_data.get('symbol')}
- Precio actual: {market_data.get('current_price')}
- RSI (14): {market_data.get('rsi')}
- EMA 50: {market_data.get('ema_50')} | EMA 200: {market_data.get('ema_200')}
- MACD: {market_data.get('macd')} (Señal: {market_data.get('macd_signal')})
- Bandas de Bollinger: {market_data.get('bollinger_bands')}
- ATR (Volatilidad): {market_data.get('atr')}
- Volumen 24h: {market_data.get('volume_24h')}
- Tendencia general: {market_data.get('trend_analysis')}

TAREA CRÍTICA:
Analiza PROFUNDAMENTE si esta oportunidad es REAL o una TRAMPA de mercado.

Considera:
1. ¿Es una ruptura real o falsa señal?
2. ¿El volumen confirma el movimiento?
3. ¿Hay divergencias peligrosas?
4. ¿La volatilidad permite stop loss razonable?

Responde en JSON:
{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0-1.0,
    "razonamiento": "análisis profundo paso por paso",
    "stop_loss_sugerido": precio_numérico,
    "take_profit_sugerido": precio_numérico,
    "tamaño_posicion_sugerido": 1-5,
    "alertas": ["riesgos identificados"],
    "confirmacion_filtro": "¿confirmas la señal del filtro? sí/no/parcial"
}}

SÉ EXTREMADAMENTE CONSERVADOR. Mejor perder una oportunidad que perder dinero.
"""

        try:
            if self.provider in ['deepseek', 'openai']:
                response = self.client.chat.completions.create(
                    model=self.model_deep,
                    messages=[
                        {
                            "role": "system",
                            "content": "Eres un trader institucional experto en detectar trampas de mercado. Respondes en JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=800
                )
                content = response.choices[0].message.content
                return self._parse_ai_response(content)

        except Exception as e:
            logger.error(f"Error en análisis profundo: {e}")
            return None

    def get_sentiment_analysis(self, symbol: str, news_data: Optional[list] = None) -> Dict[str, Any]:
        """
        Realiza análisis de sentimiento basado en noticias (funcionalidad futura).

        Args:
            symbol: Símbolo del activo
            news_data: Lista de noticias/tweets relacionados

        Returns:
            Análisis de sentimiento
        """
        # Placeholder para futura implementación
        logger.info(f"Análisis de sentimiento para {symbol} - Función en desarrollo")
        return {
            "sentiment": "neutral",
            "score": 0.0,
            "sources": []
        }


if __name__ == "__main__":
    # Prueba básica del módulo
    logging.basicConfig(level=logging.INFO)

    try:
        # Inicializar motor
        ai_engine = AIEngine()

        # Datos de prueba
        test_data = {
            "symbol": "BTC/USDT",
            "current_price": 45000,
            "market_type": "crypto",
            "rsi": 35,
            "ema_50": 44000,
            "ema_200": 42000,
            "trend_analysis": "Tendencia alcista, precio por encima de EMA 200"
        }

        # Analizar
        decision = ai_engine.analyze_market(test_data)
        print("\n=== RESULTADO DEL ANÁLISIS ===")
        print(json.dumps(decision, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Error en prueba: {e}")
