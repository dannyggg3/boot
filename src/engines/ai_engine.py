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

# v1.4: Importar parseo robusto con Pydantic
try:
    from schemas.ai_responses import parse_ai_response_safe, TradingDecision, QuickFilterDecision
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    parse_ai_response_safe = None

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

        # Sistema de Agentes Especializados (v1.2) + v1.8.1 retries
        self.agents_config = self.config.get('ai_agents', {})
        self.use_specialized_agents = self.agents_config.get('enabled', True)
        self.min_volatility_percent = self.agents_config.get('min_volatility_percent', 0.5)
        self.min_volume_ratio = self.agents_config.get('min_volume_ratio', 0.8)
        # v1.8.1: Reintentos configurables para errores de conexión
        self.max_retries = self.agents_config.get('max_retries', 3)
        self.retry_delay = self.agents_config.get('retry_delay_seconds', 2)

        # v1.5: Cache inteligente de decisiones (reduce llamadas API)
        self._decision_cache = {}  # {cache_key: {decision, timestamp}}
        self._cache_ttl = 300  # 5 minutos de TTL
        self._cache_hits = 0
        self._cache_misses = 0

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

    # ========================================================================
    # v1.5: PRE-FILTRO LOCAL + CACHE INTELIGENTE
    # ========================================================================

    def _local_pre_filter(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        v1.9 INSTITUCIONAL: Pre-filtro LOCAL antes de llamar a cualquier API.
        Filtra mercados "aburridos" sin gastar créditos de IA.

        Filtros aplicados (en orden):
        1. ADX < 20 = Mercado lateral (CRÍTICO - ahorra más tokens)
        2. RSI neutral + volumen bajo
        3. MACD plano
        4. Volatilidad muy baja

        Returns:
            None si debe continuar al análisis de IA
            Dict con decisión ESPERA si el mercado es aburrido
        """
        symbol = market_data.get('symbol', 'N/A')
        rsi = market_data.get('rsi', 50)
        volume_ratio = market_data.get('volume_ratio', 0)
        atr_percent = market_data.get('atr_percent', 0)
        macd = market_data.get('macd', 0)
        macd_signal = market_data.get('macd_signal', 0)
        current_price = market_data.get('current_price', 1)

        # v1.9: Obtener datos de ADX
        adx = market_data.get('adx', 0)
        adx_tradeable = market_data.get('adx_tradeable', True)
        adx_trend_strength = market_data.get('adx_trend_strength', 'unknown')

        # ========================================
        # FILTRO 1 (v1.9 CRÍTICO): ADX < 20 = Mercado lateral
        # ========================================
        # ADX es el MEJOR indicador para detectar mercados sin tendencia
        # ADX < 20 significa que NO hay tendencia clara - NO OPERAR
        # Esto ahorra la mayoría de tokens en mercados laterales
        if adx > 0 and adx < 20:
            logger.info(f"🚫 PRE-FILTRO ADX [{symbol}]: ADX={adx:.1f} < 20 (mercado lateral)")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": f"Pre-filtro ADX: Mercado lateral sin tendencia (ADX {adx:.1f} < 20). "
                               f"Esperando tendencia confirmada (ADX > 25).",
                "analysis_type": "local_pre_filter",
                "filtered_reason": "adx_no_trend",
                "adx_value": adx,
                "adx_trend_strength": adx_trend_strength
            }

        # ========================================
        # FILTRO 2: RSI neutral + volumen bajo
        # ========================================
        if 45 < rsi < 55 and volume_ratio < 1.5:
            logger.info(f"🚫 PRE-FILTRO LOCAL [{symbol}]: RSI neutral ({rsi:.1f}) + volumen bajo ({volume_ratio:.2f}x)")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": f"Pre-filtro local: Mercado lateral (RSI {rsi:.1f} neutral + volumen {volume_ratio:.2f}x bajo)",
                "analysis_type": "local_pre_filter",
                "filtered_reason": "rsi_neutral_low_volume"
            }

        # ========================================
        # FILTRO 3: MACD plano (sin momentum)
        # ========================================
        macd_threshold = current_price * 0.0001  # 0.01% del precio
        if abs(macd) < macd_threshold and abs(macd - macd_signal) < macd_threshold:
            logger.info(f"🚫 PRE-FILTRO LOCAL [{symbol}]: MACD plano (sin momentum)")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": f"Pre-filtro local: MACD plano ({macd:.6f}) - sin momentum",
                "analysis_type": "local_pre_filter",
                "filtered_reason": "macd_flat"
            }

        # ========================================
        # FILTRO 4: Volatilidad extremadamente baja
        # ========================================
        if atr_percent < self.min_volatility_percent * 0.5:
            logger.info(f"🚫 PRE-FILTRO LOCAL [{symbol}]: Volatilidad muy baja ({atr_percent:.3f}%)")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": f"Pre-filtro local: Volatilidad muy baja ({atr_percent:.3f}%)",
                "analysis_type": "local_pre_filter",
                "filtered_reason": "very_low_volatility"
            }

        # v1.9: Log cuando ADX confirma tendencia operativa
        if adx >= 25:
            logger.info(f"✅ PRE-FILTRO ADX [{symbol}]: ADX={adx:.1f} >= 25 (tendencia confirmada)")

        # Pasó el pre-filtro, continuar al análisis de IA
        return None

    def _get_cache_key(self, market_data: Dict[str, Any]) -> str:
        """
        Genera una clave de cache basada en condiciones de mercado redondeadas.
        Si las condiciones no cambiaron significativamente, retorna la misma clave.
        """
        symbol = market_data.get('symbol', 'N/A')
        rsi = market_data.get('rsi', 50)
        current_price = market_data.get('current_price', 0)
        ema_50 = market_data.get('ema_50', 0)
        ema_200 = market_data.get('ema_200', 0)

        # Redondear RSI a bandas de 5 (50.3 -> 50, 52.8 -> 55)
        rsi_rounded = round(rsi / 5) * 5

        # Posición relativa del precio vs EMAs (más importante que el precio exacto)
        price_vs_ema50 = "above" if current_price > ema_50 else "below"
        price_vs_ema200 = "above" if current_price > ema_200 else "below"

        # Precio redondeado a 0.5% (para BTC $43,500 -> redondea a ~$200)
        price_precision = max(current_price * 0.005, 1)
        price_rounded = round(current_price / price_precision) * price_precision

        cache_key = f"{symbol}|rsi{rsi_rounded}|p{price_rounded:.0f}|{price_vs_ema50}50|{price_vs_ema200}200"
        return cache_key

    def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Verifica si hay una decisión cacheada válida.

        Returns:
            Decisión cacheada si es válida, None si expiró o no existe
        """
        import time

        if cache_key not in self._decision_cache:
            return None

        cached = self._decision_cache[cache_key]
        age = time.time() - cached['timestamp']

        if age > self._cache_ttl:
            # Cache expirado, eliminarlo
            del self._decision_cache[cache_key]
            return None

        # Cache válido
        self._cache_hits += 1
        cached_decision = cached['decision'].copy()
        cached_decision['from_cache'] = True
        cached_decision['cache_age_seconds'] = int(age)

        logger.info(f"💾 CACHE HIT: Usando decisión cacheada (edad: {age:.0f}s)")
        return cached_decision

    def _save_to_cache(self, cache_key: str, decision: Dict[str, Any]):
        """Guarda una decisión en el cache."""
        import time

        self._decision_cache[cache_key] = {
            'decision': decision,
            'timestamp': time.time()
        }
        self._cache_misses += 1

        # Limpiar cache viejo (máximo 50 entradas)
        if len(self._decision_cache) > 50:
            oldest_key = min(self._decision_cache.keys(),
                           key=lambda k: self._decision_cache[k]['timestamp'])
            del self._decision_cache[oldest_key]

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas del cache."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 1),
            "cached_entries": len(self._decision_cache)
        }

    def analyze_market(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analiza los datos del mercado y retorna una decisión de trading.
        v1.4: Incluye lógica de reintento para fallos de API o de parseo JSON.

        Args:
            market_data: Diccionario con datos técnicos del mercado

        Returns:
            Diccionario con la decisión, razonamiento y parámetros
        """
        import time

        try:
            prompt = self._build_analysis_prompt(market_data)

            # v1.8.1: Usar reintentos configurables
            for attempt in range(self.max_retries):
                try:
                    # Llamada a la API
                    response_text = self._get_ai_response(prompt)

                    # Parsear la respuesta JSON de la IA (usa Pydantic si está disponible)
                    decision = self._parse_ai_response(response_text)

                    # v1.4: Verificar si el parseo falló (detectar errores en razonamiento)
                    razonamiento = decision.get('razonamiento', '')

                    # Si el razonamiento indica un error de parseo, forzamos un reintento
                    if 'Error' in razonamiento or 'error' in razonamiento.lower() or 'inválido' in razonamiento.lower():
                        if attempt < self.max_retries - 1:
                            logger.warning(f"Respuesta inválida de IA (intento {attempt + 1}/{self.max_retries}). Reintentando...")
                            time.sleep(self.retry_delay)
                            continue

                    # Si llegamos aquí, tenemos una decisión válida
                    logger.info(f"Análisis completado - Decisión: {decision.get('decision', 'UNKNOWN')}")
                    return decision

                except Exception as e:
                    logger.error(f"Error en análisis de mercado (intento {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        logger.info("Reintentando...")
                        continue

            # Si fallan todos los intentos
            logger.error("Se agotaron los reintentos de análisis")
            return None

        except Exception as e:
            logger.error(f"Error crítico en analyze_market: {e}")
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
Volumen Actual: {market_data.get('volume_current', 'N/A')} | Promedio (20): {market_data.get('volume_mean', 'N/A')} | Ratio: {market_data.get('volume_ratio', 'N/A')}x
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
        v1.4: Usa Pydantic para validación robusta si está disponible.

        Args:
            response_text: Texto de respuesta de la IA

        Returns:
            Diccionario con la decisión parseada
        """
        # v1.4: Usar Pydantic si está disponible (más robusto)
        if PYDANTIC_AVAILABLE and parse_ai_response_safe:
            logger.debug("Usando parseo Pydantic para validación robusta")
            return parse_ai_response_safe(response_text, TradingDecision, "ESPERA")

        # Fallback: método original con regex
        import re

        try:
            # 1. Intentar extraer JSON de bloques de código markdown
            json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
            json_blocks = re.findall(json_block_pattern, response_text)

            json_str = None

            # Buscar en bloques de código primero
            for block in json_blocks:
                block = block.strip()
                if block.startswith('{') and block.endswith('}'):
                    try:
                        json.loads(block)  # Validar que es JSON válido
                        json_str = block
                        break
                    except json.JSONDecodeError:
                        continue

            # 2. Si no se encontró en bloques, buscar JSON raw
            if not json_str:
                # Buscar el último JSON completo en el texto (modelos reasoner ponen JSON al final)
                json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                json_matches = re.findall(json_pattern, response_text)

                for match in reversed(json_matches):  # Empezar por el final
                    try:
                        json.loads(match)
                        json_str = match
                        break
                    except json.JSONDecodeError:
                        continue

            # 3. Fallback: método simple de encontrar { y }
            if not json_str:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]

            if not json_str:
                logger.warning("No se encontró JSON en la respuesta de la IA")
                logger.warning(f"Respuesta completa ({len(response_text)} chars): {response_text[:1000]}...")
                return {
                    "decision": "ESPERA",
                    "confidence": 0.0,
                    "razonamiento": "Error parseando respuesta de IA",
                    "alertas": ["Formato de respuesta inválido"]
                }

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

        v1.5: Ahora incluye PRE-FILTRO LOCAL + CACHE para reducir llamadas API.

        Nivel 0 (NUEVO): Pre-filtro local (Python puro, $0)
        Nivel 0.5 (NUEVO): Cache inteligente (si condiciones similares, $0)
        Nivel 1: Filtrado rápido con modelo chat (DeepSeek-V3 / GPT-4o-mini)
                 Detecta si hay oportunidad potencial.
        Nivel 2: Razonamiento profundo con modelo reasoner (DeepSeek-R1 / o1)
                 Solo se ejecuta si el filtro detecta oportunidad.

        Args:
            market_data: Diccionario con datos técnicos del mercado

        Returns:
            Diccionario con la decisión final, o None si no hay oportunidad
        """
        symbol = market_data.get('symbol', 'N/A')
        logger.info(f"=== ANÁLISIS HÍBRIDO [{symbol}] ===")

        # NIVEL 0: Pre-filtro LOCAL (Python puro - GRATIS)
        pre_filter_result = self._local_pre_filter(market_data)
        if pre_filter_result:
            logger.info(f"⚡ Filtrado por PRE-FILTRO LOCAL - $0 gastado")
            return pre_filter_result

        # NIVEL 0.5: Cache inteligente (si las condiciones son similares, reusar decisión)
        cache_key = self._get_cache_key(market_data)
        cached_decision = self._check_cache(cache_key)
        if cached_decision:
            logger.info(f"⚡ Usando decisión CACHEADA - $0 gastado")
            return cached_decision

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
            espera_decision = {
                "decision": "ESPERA",
                "confidence": quick_decision.get('confidence', 0.3),
                "razonamiento": quick_decision.get('reason', 'Descartado en filtro inicial'),
                "analysis_type": "quick_filter_only"
            }
            # Guardar en cache para no volver a llamar si condiciones similares
            self._save_to_cache(cache_key, espera_decision)
            return espera_decision

        # NIVEL 2: Análisis Profundo (Modelo Reasoner - Solo si vale la pena)
        logger.info(f"✅ Oportunidad detectada! Nivel 2: Razonamiento profundo con {self.model_deep}")

        deep_decision = self._deep_reasoning_analysis(market_data, quick_decision)

        if deep_decision:
            deep_decision['analysis_type'] = 'hybrid_two_level'
            deep_decision['quick_filter_signal'] = quick_signal
            logger.info(f"Decisión final (híbrido): {deep_decision.get('decision', 'UNKNOWN')}")
            # Guardar decisión profunda en cache
            self._save_to_cache(cache_key, deep_decision)

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
- Volumen Ratio: {market_data.get('volume_ratio', 'N/A')}x (>1 = volumen sobre promedio)

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
                    max_tokens=150,
                    response_format={"type": "json_object"}  # v1.5: Forzar JSON
                )
                content = response.choices[0].message.content
                return json.loads(content)  # Ya es JSON válido

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
- Volumen Actual: {market_data.get('volume_current', 'N/A')} | Promedio (20): {market_data.get('volume_mean', 'N/A')} | Ratio: {market_data.get('volume_ratio', 'N/A')}x
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
                is_reasoner = 'reasoner' in self.model_deep.lower() or 'r1' in self.model_deep.lower()

                api_params = {
                    "model": self.model_deep,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Eres un trader institucional experto en detectar trampas de mercado. Respondes en JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 4000 if is_reasoner else 800
                }

                # Reasoner no soporta temperature ni response_format
                if not is_reasoner:
                    api_params["temperature"] = 0.1
                    api_params["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**api_params)
                message = response.choices[0].message
                content = message.content or ""

                # DeepSeek-R1: Si content vacío, extraer de reasoning_content
                if not content and is_reasoner:
                    if hasattr(message, 'reasoning_content') and message.reasoning_content:
                        content = message.reasoning_content
                        logger.info(f"Usando reasoning_content ({len(content)} chars)")

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

    # ========================================================================
    # SISTEMA DE AGENTES ESPECIALIZADOS (v1.2)
    # ========================================================================

    def determine_market_regime(self, market_data: Dict[str, Any]) -> str:
        """
        Determina el régimen de mercado actual para seleccionar el agente apropiado.

        Returns:
            'trending' | 'reversal' | 'ranging' | 'volatile' | 'low_volatility'
        """
        rsi = market_data.get('rsi', 50)
        ema_50 = market_data.get('ema_50', 0)
        ema_200 = market_data.get('ema_200', 0)
        current_price = market_data.get('current_price', 0)
        atr_percent = market_data.get('atr_percent', 0)
        volatility = market_data.get('volatility_level', 'media')

        # Detectar baja volatilidad (NO OPERAR)
        # SOLO usamos el porcentaje configurado, ignoramos la etiqueta 'baja'
        if atr_percent < self.min_volatility_percent:
            return 'low_volatility'

        # Detectar condiciones de reversión (RSI extremo)
        if rsi <= 30 or rsi >= 70:
            return 'reversal'

        # Detectar tendencia fuerte
        if ema_50 and ema_200 and current_price:
            price_above_ema200 = current_price > ema_200
            ema_50_above_200 = ema_50 > ema_200

            if price_above_ema200 and ema_50_above_200:
                return 'trending'  # Tendencia alcista
            elif not price_above_ema200 and not ema_50_above_200:
                return 'trending'  # Tendencia bajista

        # Mercado lateral/ranging
        return 'ranging'

    def analyze_with_specialized_agent(
        self,
        market_data: Dict[str, Any],
        advanced_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Análisis con agentes especializados según el régimen de mercado.

        Args:
            market_data: Datos técnicos del mercado
            advanced_data: Datos avanzados (order book, open interest, correlaciones)

        Returns:
            Decisión del agente especializado
        """
        # Determinar régimen de mercado
        regime = self.determine_market_regime(market_data)
        logger.info(f"📊 Régimen de mercado detectado: {regime.upper()}")

        # FILTRO CRÍTICO: No operar en baja volatilidad
        if regime == 'low_volatility':
            logger.info("⏸️ BAJA VOLATILIDAD - No hay movimientos explosivos. Esperando...")
            return {
                "decision": "ESPERA",
                "confidence": 0.1,
                "razonamiento": "Volatilidad demasiado baja. Sin movimientos explosivos.",
                "analysis_type": "volatility_filter",
                "regime": regime
            }

        # FILTRO: Mercado lateral sin dirección clara
        if regime == 'ranging':
            logger.info("↔️ MERCADO LATERAL - Sin tendencia clara. Esperando breakout...")
            return {
                "decision": "ESPERA",
                "confidence": 0.2,
                "razonamiento": "Mercado lateral sin dirección clara. Esperando ruptura.",
                "analysis_type": "ranging_filter",
                "regime": regime
            }

        # Seleccionar agente especializado
        if regime == 'trending':
            return self._trend_agent_analysis(market_data, advanced_data)
        elif regime == 'reversal':
            return self._reversal_agent_analysis(market_data, advanced_data)

        return None

    def _trend_agent_analysis(
        self,
        market_data: Dict[str, Any],
        advanced_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        AGENTE DE TENDENCIA: Busca entradas de continuación en retrocesos.
        Solo opera cuando el precio está en tendencia clara (sobre/bajo EMA 200).
        """
        symbol = market_data.get('symbol', 'N/A')
        logger.info(f"🚀 AGENTE DE TENDENCIA activado para {symbol}")

        # Construir contexto de datos avanzados
        advanced_context = self._build_advanced_context(advanced_data)

        prompt = f"""
Eres un AGENTE DE TENDENCIA especializado. Tu ÚNICA misión es encontrar entradas de CONTINUACIÓN de tendencia en RETROCESOS.

=== REGLAS DE ENTRADA ===
1. SOLO operas a FAVOR de la tendencia (precio sobre EMA 200 = COMPRA, bajo EMA 200 = VENTA)
2. NUNCA operas contra la tendencia principal
3. Buscas entradas en CONTINUACIÓN DE TENDENCIA:
   - Si la tendencia es FUERTE (precio alejado de EMA 50, momentum alto): entra en BREAKOUTS o retrocesos menores
   - Si la tendencia es moderada: espera retroceso hacia EMA 50 o EMA 20
   - NO esperes retrocesos profundos en tendencias explosivas
4. Si el RSI está muy sobrecomprado (>80), considera esperar un pequeño retroceso
5. Volumen: ratio > 1.0 es ideal, pero ratio > 0.3 es ACEPTABLE. Volumen bajo NO invalida una señal técnica fuerte.

=== DATOS DEL MERCADO: {symbol} ===
Precio Actual: {market_data.get('current_price')}
EMA 50: {market_data.get('ema_50')} | EMA 200: {market_data.get('ema_200')}
RSI (14): {market_data.get('rsi')}
MACD: {market_data.get('macd')} (Señal: {market_data.get('macd_signal')})
ATR: {market_data.get('atr')} ({market_data.get('atr_percent', 0):.2f}%)
Volumen Actual: {market_data.get('volume_current', 'N/A')} | Promedio (20): {market_data.get('volume_mean', 'N/A')} | Ratio: {market_data.get('volume_ratio', 'N/A')}x
Volumen 24h: {market_data.get('volume_24h')}
Tendencia: {market_data.get('trend_analysis')}

{advanced_context}

=== ANÁLISIS REQUERIDO ===
1. ¿El precio está en tendencia clara? (Sobre/bajo EMA 200)
2. ¿Es buena zona de entrada? (Retroceso a EMA 50/20, breakout, o tendencia fuerte)
3. ¿El volumen apoya? (ratio > 1.0 ideal, > 0.3 aceptable - NO es bloqueante)
4. ¿El RSI permite entrada? (Evitar extremos >80 o <20)

Responde SOLO en JSON:
{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0-1.0,
    "razonamiento": "Análisis paso a paso de tendencia y punto de entrada",
    "stop_loss_sugerido": precio_numérico,
    "take_profit_sugerido": precio_numérico,
    "tamaño_posicion_sugerido": 1-3,
    "tipo_entrada": "continuacion_tendencia" | "retroceso_ema" | "breakout",
    "alertas": ["riesgos identificados"]
}}

IMPORTANTE: En tendencias fuertes, NO esperes retrocesos profundos. El mercado puede subir sin ti.
"""

        return self._execute_agent_prompt(prompt, "trend_agent")

    def _reversal_agent_analysis(
        self,
        market_data: Dict[str, Any],
        advanced_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        AGENTE DE REVERSIÓN: Busca divergencias y agotamiento de tendencia.
        Solo opera cuando RSI está en extremos (<30 o >70).
        """
        symbol = market_data.get('symbol', 'N/A')
        rsi = market_data.get('rsi', 50)

        logger.info(f"🔄 AGENTE DE REVERSIÓN activado para {symbol} (RSI: {rsi})")

        # Construir contexto de datos avanzados
        advanced_context = self._build_advanced_context(advanced_data)

        # Determinar dirección esperada de reversión
        reversal_direction = "COMPRA" if rsi <= 30 else "VENTA"

        prompt = f"""
Eres un AGENTE DE REVERSIÓN especializado. Tu ÚNICA misión es detectar AGOTAMIENTO de tendencia y puntos de GIRO.

=== REGLAS DE ENTRADA (REVERSIÓN) ===
1. SOLO operas en EXTREMOS de RSI (< 30 sobrevendido = buscar COMPRA, > 70 sobrecomprado = buscar VENTA)
2. Divergencia RSI es IDEAL pero no obligatoria si hay señales claras de agotamiento
3. BUSCAS señales de agotamiento: velas de rechazo, Bollinger extremo, MACD cruzando
4. Volumen: ratio > 0.3 es suficiente. El Order Book Imbalance puede confirmar la reversión
5. Stop loss MUY AJUSTADO porque operas contra la tendencia - POSICIÓN PEQUEÑA

=== DATOS DEL MERCADO: {symbol} ===
Precio Actual: {market_data.get('current_price')}
RSI (14): {rsi} {'(SOBREVENDIDO)' if rsi <= 30 else '(SOBRECOMPRADO)'}
EMA 50: {market_data.get('ema_50')} | EMA 200: {market_data.get('ema_200')}
MACD: {market_data.get('macd')} (Señal: {market_data.get('macd_signal')})
Bandas Bollinger: {market_data.get('bollinger_bands')}
ATR: {market_data.get('atr')} ({market_data.get('atr_percent', 0):.2f}%)
Volumen Actual: {market_data.get('volume_current', 'N/A')} | Promedio (20): {market_data.get('volume_mean', 'N/A')} | Ratio: {market_data.get('volume_ratio', 'N/A')}x
Volumen 24h: {market_data.get('volume_24h')}

{advanced_context}

=== ANÁLISIS REQUERIDO ===
1. ¿Hay DIVERGENCIA entre precio y RSI? (Crítico para reversión)
2. ¿El precio tocó banda de Bollinger inferior/superior?
3. ¿Hay señales de agotamiento? (Velas de rechazo, volumen decreciente)
4. ¿El MACD muestra cruce o divergencia?

DIRECCIÓN ESPERADA: {reversal_direction} (porque RSI está en {'sobrevendido' if rsi <= 30 else 'sobrecomprado'})

Responde SOLO en JSON:
{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0-1.0,
    "razonamiento": "Análisis de divergencia y agotamiento paso a paso",
    "stop_loss_sugerido": precio_numérico,
    "take_profit_sugerido": precio_numérico,
    "tamaño_posicion_sugerido": 1-2,
    "tipo_entrada": "divergencia_rsi" | "banda_bollinger" | "agotamiento",
    "divergencia_detectada": true | false,
    "alertas": ["riesgos - ALTO RIESGO por operar contra tendencia"]
}}

IMPORTANTE: Las reversiones son ALTO RIESGO. Busca múltiples confirmaciones (RSI extremo + Bollinger + MACD). Posición PEQUEÑA siempre.
"""

        return self._execute_agent_prompt(prompt, "reversal_agent")

    def _build_advanced_context(self, advanced_data: Optional[Dict[str, Any]]) -> str:
        """Construye el contexto de datos avanzados para el prompt."""
        if not advanced_data:
            return ""

        context_parts = ["=== DATOS AVANZADOS ==="]

        # Order Book
        if 'order_book' in advanced_data:
            ob = advanced_data['order_book']
            context_parts.append(f"Order Book - Bid Wall: {ob.get('bid_wall', 'N/A')} | Ask Wall: {ob.get('ask_wall', 'N/A')}")
            context_parts.append(f"Imbalance: {ob.get('imbalance', 'N/A')}")

        # Open Interest
        if 'open_interest' in advanced_data:
            oi = advanced_data['open_interest']
            context_parts.append(f"Open Interest: {oi.get('value', 'N/A')} (Cambio 24h: {oi.get('change_24h', 'N/A')}%)")

        # Funding Rate
        if 'funding_rate' in advanced_data:
            context_parts.append(f"Funding Rate: {advanced_data['funding_rate']}%")

        # Correlaciones
        if 'correlations' in advanced_data:
            corr = advanced_data['correlations']
            context_parts.append(f"Correlación BTC: {corr.get('btc', 'N/A')} | S&P500: {corr.get('sp500', 'N/A')}")

        return "\n".join(context_parts) if len(context_parts) > 1 else ""

    def _execute_agent_prompt(self, prompt: str, agent_type: str) -> Optional[Dict[str, Any]]:
        """Ejecuta el prompt del agente y parsea la respuesta."""
        try:
            if self.provider in ['deepseek', 'openai']:
                # Usar modelo profundo para agentes especializados
                model = self.model_deep if self.use_hybrid else self.model
                is_reasoner = 'reasoner' in model.lower() or 'r1' in model.lower()

                # Construir parámetros según el tipo de modelo
                api_params = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": f"Eres un {agent_type.upper()} de trading profesional. Solo respondes en JSON válido. Eres EXTREMADAMENTE selectivo."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4000 if is_reasoner else 800
                }

                # Reasoner no soporta temperature ni response_format
                if not is_reasoner:
                    api_params["temperature"] = 0.1
                    api_params["response_format"] = {"type": "json_object"}  # v1.5: Forzar JSON

                logger.debug(f"Llamando a {model} (reasoner={is_reasoner})...")
                response = self.client.chat.completions.create(**api_params)

                # Extraer contenido de la respuesta
                message = response.choices[0].message
                content = message.content or ""

                # Si content está vacío, intentar reasoning_content (DeepSeek R1)
                if not content:
                    if hasattr(message, 'reasoning_content') and message.reasoning_content:
                        content = message.reasoning_content
                        logger.info(f"Usando reasoning_content ({len(content)} chars)")
                    else:
                        # Intentar model_dump como último recurso
                        try:
                            msg_dict = message.model_dump() if hasattr(message, 'model_dump') else {}
                            content = msg_dict.get('content', '') or msg_dict.get('reasoning_content', '')
                        except Exception:
                            pass

                if not content:
                    logger.warning(f"Respuesta vacía del modelo {model}")
                    return None

                logger.debug(f"Respuesta recibida ({len(content)} chars)")
                result = self._parse_ai_response(content)

                if result:
                    result['agent_type'] = agent_type
                    result['analysis_type'] = 'specialized_agent'

                return result

        except Exception as e:
            logger.error(f"Error en agente {agent_type}: {e}")
            return None

    def analyze_market_v2(
        self,
        market_data: Dict[str, Any],
        advanced_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Análisis de mercado v2 con agentes especializados y filtros avanzados.

        Flujo:
        1. Pre-filtro de volatilidad (rechaza baja volatilidad)
        2. Detección de régimen de mercado
        3. Agente especializado según régimen
        4. Validación con arquitectura híbrida si está habilitada

        Args:
            market_data: Datos técnicos del mercado
            advanced_data: Datos avanzados opcionales

        Returns:
            Decisión final del análisis
        """
        symbol = market_data.get('symbol', 'N/A')
        logger.info(f"=== ANÁLISIS v2 CON AGENTES ESPECIALIZADOS: {symbol} ===")

        # Pre-filtro de volatilidad (ahorra llamadas a API cuando no hay oportunidad)
        atr_percent = market_data.get('atr_percent', 0)
        if atr_percent < self.min_volatility_percent:
            logger.info(f"⏸️ ATR {atr_percent:.2f}% < mínimo {self.min_volatility_percent}% - SIN MOVIMIENTO EXPLOSIVO")
            return {
                "decision": "ESPERA",
                "confidence": 0.1,
                "razonamiento": f"Volatilidad muy baja (ATR: {atr_percent:.2f}%). Esperando movimientos explosivos.",
                "analysis_type": "volatility_pre_filter"
            }

        # Análisis con agentes especializados
        if self.use_specialized_agents:
            result = self.analyze_with_specialized_agent(market_data, advanced_data)
            if result:
                return result

        # Fallback a análisis híbrido tradicional
        if self.use_hybrid:
            return self.analyze_market_hybrid(market_data)

        # Fallback a análisis simple
        return self.analyze_market(market_data)


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
