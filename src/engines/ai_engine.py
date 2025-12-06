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
        v2.2 INSTITUCIONAL: Pre-filtro LOCAL CONFIGURABLE antes de llamar a cualquier API.
        Filtra mercados "aburridos" sin gastar créditos de IA.

        Filtros aplicados (en orden):
        1. ADX < min_adx_trend = Mercado lateral (configurable)
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
        # FILTRO 1 (v2.2 CONFIGURABLE): ADX < min_adx_trend
        # ========================================
        # v2.2: Usa el threshold de configuración (default 20, institucional 25)
        min_adx = self.min_adx_trend
        if adx > 0 and adx < min_adx:
            trend_type = "lateral" if adx < 15 else "débil/transición"
            logger.info(f"🚫 PRE-FILTRO ADX [{symbol}]: ADX={adx:.1f} < {min_adx} (tendencia {trend_type})")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": f"Pre-filtro ADX: Tendencia {trend_type} (ADX {adx:.1f} < {min_adx}). "
                               f"Configurado para ADX >= {min_adx} para confirmar tendencia.",
                "analysis_type": "local_pre_filter",
                "filtered_reason": "adx_weak_trend",
                "adx_value": adx,
                "adx_trend_strength": adx_trend_strength
            }

        # ========================================
        # FILTRO 2: RSI neutral + volumen bajo promedio
        # ========================================
        # v2.2: Usa min_volume_ratio de configuración
        if 45 < rsi < 55 and volume_ratio < self.min_volume_ratio:
            logger.info(f"🚫 PRE-FILTRO LOCAL [{symbol}]: RSI neutral ({rsi:.1f}) + volumen bajo ({volume_ratio:.2f}x < {self.min_volume_ratio}x)")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": f"Pre-filtro local: Sin momentum (RSI {rsi:.1f} neutral + volumen {volume_ratio:.2f}x bajo)",
                "analysis_type": "local_pre_filter",
                "filtered_reason": "rsi_neutral_low_volume"
            }

        # ========================================
        # FILTRO 3: MACD plano (sin momentum)
        # ========================================
        # v2.2: Threshold más realista - 0.03% del precio (reducido para más oportunidades)
        macd_threshold = current_price * 0.0003  # 0.03% del precio
        if abs(macd) < macd_threshold and abs(macd - macd_signal) < macd_threshold:
            logger.info(f"🚫 PRE-FILTRO LOCAL [{symbol}]: MACD plano (sin momentum significativo)")
            return {
                "decision": "ESPERA",
                "confidence": 0.0,
                "razonamiento": f"Pre-filtro local: MACD plano ({macd:.4f}) - sin momentum significativo",
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

        # v2.2: Log cuando ADX confirma tendencia operativa
        if adx >= min_adx:
            logger.info(f"✅ PRE-FILTRO ADX [{symbol}]: ADX={adx:.1f} >= {min_adx} (tendencia confirmada)")

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
        # v2.0: Calcular SL/TP sugeridos basados en ATR para guiar a la IA
        atr = market_data.get('atr', 0)
        atr_percent = market_data.get('atr_percent', 0)
        current_price = market_data.get('current_price', 0)

        # Calcular rangos sugeridos (2.5x ATR para SL, 5x ATR para TP)
        sl_distance = atr * 2.5 if atr else current_price * 0.02
        tp_distance = atr * 5.0 if atr else current_price * 0.04

        prompt = f"""
Eres un trader institucional con 20 años de experiencia. Capital LIMITADO ($300).
FILOSOFÍA: Es mejor NO operar que perder dinero. Solo trades de ALTA PROBABILIDAD.

=== DATOS DEL MERCADO: {market_data.get('symbol', 'N/A')} ===
Precio Actual: ${current_price:,.2f}

=== VOLATILIDAD (INFO) ===
ATR (14): ${atr:.2f} ({atr_percent:.2f}% del precio)
NOTA: El sistema calculará SL/TP automáticamente con ATR. NO necesitas sugerirlos.

=== INDICADORES TÉCNICOS ===
RSI (14): {market_data.get('rsi', 'N/A')}
EMA 50: ${market_data.get('ema_50', 0):,.2f} | EMA 200: ${market_data.get('ema_200', 0):,.2f}
MACD: {market_data.get('macd', 'N/A')} | Señal: {market_data.get('macd_signal', 'N/A')}
Volumen Ratio: {market_data.get('volume_ratio', 'N/A')}x (>1 = sobre promedio)
ADX: {market_data.get('adx', 'N/A')} (>25 = tendencia fuerte)

=== TENDENCIA ===
{market_data.get('trend_analysis', 'No disponible')}

=== RESPUESTA REQUERIDA (JSON) ===
{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0 - 1.0,
    "razonamiento": "Checklist: EMA200[✓/✗], RSI[✓/✗], MACD[✓/✗], Vol[✓/✗], ADX[✓/✗]",
    "alertas": ["riesgos identificados"]
}}

=== REGLAS DE ENTRADA (CRÍTICAS) ===
1. Si hay CUALQUIER duda → "ESPERA"
2. COMPRA solo si: precio > EMA200, RSI 35-65, MACD > Signal, Vol > 1.0x, ADX > 25
3. VENTA solo si: precio < EMA200, RSI 35-65, MACD < Signal, Vol > 1.0x, ADX > 25
4. RSI < 35 o RSI > 65 = ESPERA (zonas extremas, riesgo de reversión)
5. ADX < 25 = ESPERA (sin tendencia clara)
6. NUNCA operes contra EMA 200

RESPONDE:
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
        v2.2: Parsea la respuesta de la IA con manejo ROBUSTO de JSON.
        Usa Pydantic para validación si está disponible.

        Soporta:
        - JSON directo
        - JSON dentro de bloques ```json
        - JSON con texto adicional antes/después
        - Modelos "reasoner" que ponen JSON al final de su razonamiento
        - v2.2 NUEVO: Fallback inteligente para extraer decisiones de texto

        Args:
            response_text: Texto de respuesta de la IA

        Returns:
            Diccionario con la decisión parseada
        """
        # v1.4: Usar Pydantic si está disponible (más robusto)
        if PYDANTIC_AVAILABLE and parse_ai_response_safe:
            logger.debug("Usando parseo Pydantic para validación robusta")
            result = parse_ai_response_safe(response_text, TradingDecision, "ESPERA")
            # v2.2: Si Pydantic falló, intentar fallback
            if result.get('decision') == 'ESPERA' and result.get('confidence', 0) == 0:
                fallback = self._fallback_text_parser(response_text)
                if fallback.get('confidence', 0) > 0:
                    return fallback
            return result

        # Fallback: método original con regex mejorado v2.2
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

            # 4. v2.2 NUEVO: Fallback inteligente - extraer decisión de texto
            if not json_str:
                logger.warning("No se encontró JSON - Intentando fallback de texto")
                return self._fallback_text_parser(response_text)

            decision_data = json.loads(json_str)

            # Validar campos requeridos
            required_fields = ['decision', 'razonamiento']
            for field in required_fields:
                if field not in decision_data:
                    logger.warning(f"Campo requerido '{field}' no encontrado en respuesta")
                    decision_data[field] = "N/A"

            # v2.2: Normalizar la decisión con mapeo de sinónimos
            decision_data['decision'] = str(decision_data['decision']).upper()
            decision_map = {
                'COMPRA': 'COMPRA', 'BUY': 'COMPRA', 'LONG': 'COMPRA',
                'VENTA': 'VENTA', 'SELL': 'VENTA', 'SHORT': 'VENTA',
                'ESPERA': 'ESPERA', 'HOLD': 'ESPERA', 'WAIT': 'ESPERA', 'NEUTRAL': 'ESPERA'
            }
            decision_data['decision'] = decision_map.get(decision_data['decision'], 'ESPERA')

            # v2.2: Validar y normalizar confidence
            if 'confidence' in decision_data:
                try:
                    conf = float(decision_data['confidence'])
                    decision_data['confidence'] = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    decision_data['confidence'] = 0.5

            return decision_data

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de IA: {e}")
            logger.debug(f"Respuesta completa: {response_text}")
            return self._fallback_text_parser(response_text)

    def _fallback_text_parser(self, text: str) -> Dict[str, Any]:
        """
        v2.2: Fallback inteligente para extraer decisiones de texto libre.
        Usa cuando el parsing JSON falla completamente.
        """
        text_lower = text.lower()

        # Detectar decisión por palabras clave
        decision = 'ESPERA'
        confidence = 0.5

        # Buscar señales de COMPRA
        buy_keywords = ['compra', 'buy', 'long', 'bullish', 'alcista', 'subir', 'up', 'comprar']
        sell_keywords = ['venta', 'sell', 'short', 'bearish', 'bajista', 'bajar', 'down', 'vender']
        wait_keywords = ['espera', 'wait', 'hold', 'neutral', 'lateral', 'no operar', 'esperar']

        buy_score = sum(1 for kw in buy_keywords if kw in text_lower)
        sell_score = sum(1 for kw in sell_keywords if kw in text_lower)
        wait_score = sum(1 for kw in wait_keywords if kw in text_lower)

        if buy_score > sell_score and buy_score > wait_score:
            decision = 'COMPRA'
            confidence = min(0.7, 0.4 + buy_score * 0.1)
        elif sell_score > buy_score and sell_score > wait_score:
            decision = 'VENTA'
            confidence = min(0.7, 0.4 + sell_score * 0.1)
        else:
            decision = 'ESPERA'
            confidence = 0.3

        # Extraer razonamiento (primeras 500 chars del texto)
        razonamiento = text[:500] if len(text) > 500 else text
        razonamiento = razonamiento.replace('\n', ' ').strip()

        logger.info(f"🔄 Fallback parser: {decision} (conf: {confidence:.2f}) - buy:{buy_score} sell:{sell_score} wait:{wait_score}")

        return {
            "decision": decision,
            "confidence": confidence,
            "razonamiento": f"[Fallback] {razonamiento}",
            "alertas": ["Respuesta parseada con fallback - confianza reducida"],
            "analysis_type": "fallback_parser"
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
        v2.1 INSTITUCIONAL: Determina el régimen de mercado usando ADX + indicadores.

        Returns:
            'trending' | 'reversal' | 'ranging' | 'volatile' | 'low_volatility'
        """
        rsi = market_data.get('rsi', 50)
        ema_50 = market_data.get('ema_50', 0)
        ema_200 = market_data.get('ema_200', 0)
        current_price = market_data.get('current_price', 0)
        atr_percent = market_data.get('atr_percent', 0)
        adx = market_data.get('adx', 0)

        # v2.1: Obtener threshold de ADX desde config
        min_adx = self.agents_config.get('min_adx_trend', 25)

        # 1. Detectar baja volatilidad (NO OPERAR)
        if atr_percent < self.min_volatility_percent:
            return 'low_volatility'

        # 2. Detectar condiciones de reversión (RSI extremo)
        # Solo si RSI está en extremos Y hay algo de tendencia (ADX > 20)
        if (rsi <= 30 or rsi >= 70) and adx >= 20:
            return 'reversal'

        # 3. v2.1: Usar ADX para determinar si hay tendencia operable
        # ADX >= 25 = Tendencia fuerte, operable
        # ADX < 25 = Sin tendencia clara (ranging o transición)
        if adx > 0 and adx < min_adx:
            # ADX bajo pero puede haber oportunidad de rango
            # Solo si Bollinger está en extremos (precio cerca de bandas)
            bb = market_data.get('bollinger_bands', {})
            bb_lower = bb.get('lower', 0) if isinstance(bb, dict) else 0
            bb_upper = bb.get('upper', 0) if isinstance(bb, dict) else 0

            if bb_lower and bb_upper and current_price:
                bb_range = bb_upper - bb_lower
                # Si precio está en el 20% inferior o superior del rango BB
                if current_price <= bb_lower + (bb_range * 0.2):
                    return 'ranging'  # Potencial compra en soporte
                elif current_price >= bb_upper - (bb_range * 0.2):
                    return 'ranging'  # Potencial venta en resistencia

            # Si no hay oportunidad de rango clara, es low_volatility
            return 'low_volatility'

        # 4. Detectar tendencia fuerte (ADX >= 25 + EMAs alineados)
        if ema_50 and ema_200 and current_price and adx >= min_adx:
            price_above_ema200 = current_price > ema_200
            ema_50_above_200 = ema_50 > ema_200

            if price_above_ema200 and ema_50_above_200:
                return 'trending'  # Tendencia alcista confirmada
            elif not price_above_ema200 and not ema_50_above_200:
                return 'trending'  # Tendencia bajista confirmada

        # 5. EMAs cruzados o precio en medio = mercado lateral
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
            logger.info("⏸️ BAJA VOLATILIDAD - No hay movimientos significativos. Esperando...")
            return {
                "decision": "ESPERA",
                "confidence": 0.1,
                "razonamiento": "Volatilidad demasiado baja o sin oportunidad clara.",
                "analysis_type": "volatility_filter",
                "regime": regime
            }

        # Seleccionar agente especializado según régimen
        if regime == 'trending':
            return self._trend_agent_analysis(market_data, advanced_data)
        elif regime == 'reversal':
            return self._reversal_agent_analysis(market_data, advanced_data)
        elif regime == 'ranging':
            # v2.1: Ahora SÍ operamos en rangos con el range_agent
            return self._range_agent_analysis(market_data, advanced_data)

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

        # v2.0: Calcular niveles ATR para guiar a la IA
        atr = market_data.get('atr', 0)
        atr_percent = market_data.get('atr_percent', 0)
        current_price = market_data.get('current_price', 0)
        sl_distance = atr * 2.5 if atr else current_price * 0.02
        tp_distance = atr * 5.0 if atr else current_price * 0.04

        prompt = f"""
Eres un AGENTE DE TENDENCIA INSTITUCIONAL. Capital LIMITADO ($300).
SOLO operas señales de ALTA PROBABILIDAD. Es mejor NO operar que perder.

=== REGLAS DE ENTRADA (ESTRICTAS) ===
1. SOLO a FAVOR de tendencia: precio > EMA200 = COMPRA, precio < EMA200 = VENTA
2. RSI debe estar entre 35-65 para entrar (evitar extremos)
3. MACD debe confirmar la dirección (MACD > Signal para COMPRA)
4. Volumen ratio > 0.7 (liquidez suficiente)
5. Si hay CUALQUIER duda → ESPERA

=== DATOS DEL MERCADO: {symbol} ===
Precio: ${current_price:,.2f}
EMA 50: ${market_data.get('ema_50', 0):,.2f} | EMA 200: ${market_data.get('ema_200', 0):,.2f}
RSI: {market_data.get('rsi', 50):.1f}
MACD: {market_data.get('macd', 0):.4f} | Signal: {market_data.get('macd_signal', 0):.4f}
Volumen Ratio: {market_data.get('volume_ratio', 0):.2f}x

=== VOLATILIDAD (CRÍTICO) ===
ATR: ${atr:.2f} ({atr_percent:.2f}%)
SL mínimo recomendado: ${sl_distance:.2f} del precio (2.5x ATR)
TP mínimo recomendado: ${tp_distance:.2f} del precio (5x ATR = R/R 2:1)

{advanced_context}

=== CHECKLIST OBLIGATORIO ===
✓ ¿Precio en lado correcto de EMA 200?
✓ ¿RSI entre 35-65?
✓ ¿MACD confirma dirección?
✓ ¿Volumen > 0.7x?
Si CUALQUIERA falla → ESPERA

Responde SOLO en JSON:
{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0-1.0,
    "razonamiento": "Checklist: EMA200[✓/✗], RSI[✓/✗], MACD[✓/✗], Vol[✓/✗], ADX[✓/✗]. Conclusión.",
    "tipo_entrada": "continuacion_tendencia" | "retroceso_ema",
    "alertas": ["riesgos"]
}}

NOTA: El sistema calculará SL/TP automáticamente con ATR. NO necesitas sugerirlos.
IMPORTANTE: Confianza > 0.75 SOLO si TODOS los criterios pasan. Mejor ESPERAR que perder.
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
    "tipo_entrada": "divergencia_rsi" | "banda_bollinger" | "agotamiento",
    "divergencia_detectada": true | false,
    "alertas": ["riesgos - ALTO RIESGO por operar contra tendencia"]
}}

NOTA: El sistema calculará SL/TP automáticamente con ATR. NO necesitas sugerirlos.

IMPORTANTE: Las reversiones son ALTO RIESGO. Busca múltiples confirmaciones (RSI extremo + Bollinger + MACD). Posición PEQUEÑA siempre.
"""

        return self._execute_agent_prompt(prompt, "reversal_agent")

    def _range_agent_analysis(
        self,
        market_data: Dict[str, Any],
        advanced_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        v2.1 AGENTE DE RANGO: Opera mean reversion en mercados laterales.
        Compra en soporte (Bollinger inferior), vende en resistencia (Bollinger superior).
        SOLO opera cuando el precio está en extremos del rango, NO en el medio.
        """
        symbol = market_data.get('symbol', 'N/A')
        current_price = market_data.get('current_price', 0)
        rsi = market_data.get('rsi', 50)

        # Obtener datos de Bollinger
        bb = market_data.get('bollinger_bands', {})
        bb_lower = bb.get('lower', 0) if isinstance(bb, dict) else 0
        bb_upper = bb.get('upper', 0) if isinstance(bb, dict) else 0
        bb_middle = bb.get('middle', 0) if isinstance(bb, dict) else 0

        logger.info(f"↔️ AGENTE DE RANGO activado para {symbol}")

        # Determinar zona del rango
        if bb_lower and bb_upper:
            bb_range = bb_upper - bb_lower
            pct_in_range = ((current_price - bb_lower) / bb_range * 100) if bb_range > 0 else 50
            zone = "soporte" if pct_in_range <= 25 else "resistencia" if pct_in_range >= 75 else "medio"
        else:
            pct_in_range = 50
            zone = "desconocida"

        # Construir contexto de datos avanzados
        advanced_context = self._build_advanced_context(advanced_data)

        # v2.1: Calcular niveles ATR para información
        atr = market_data.get('atr', 0)
        atr_percent = market_data.get('atr_percent', 0)

        prompt = f"""
Eres un AGENTE DE RANGO INSTITUCIONAL especializado en mean reversion.
El mercado está en RANGO LATERAL (ADX bajo). Tu estrategia es COMPRAR en soporte y VENDER en resistencia.

=== REGLAS DE ENTRADA (RANGO) ===
1. COMPRA solo si: precio en zona INFERIOR del rango (Bollinger inferior), RSI < 40
2. VENTA solo si: precio en zona SUPERIOR del rango (Bollinger superior), RSI > 60
3. Si precio está en el MEDIO del rango → ESPERA (sin edge)
4. Volumen > 0.8x para confirmar
5. POSICIÓN PEQUEÑA siempre (rango = menor probabilidad que tendencia)

=== DATOS DEL MERCADO: {symbol} ===
Precio Actual: ${current_price:,.2f}
Zona del Rango: {zone.upper()} ({pct_in_range:.0f}% del rango)

=== BOLLINGER BANDS ===
Superior: ${bb_upper:,.2f}
Media: ${bb_middle:,.2f}
Inferior: ${bb_lower:,.2f}

=== INDICADORES ===
RSI: {rsi:.1f}
MACD: {market_data.get('macd', 0):.4f} | Signal: {market_data.get('macd_signal', 0):.4f}
Volumen Ratio: {market_data.get('volume_ratio', 0):.2f}x
ATR: ${atr:.2f} ({atr_percent:.2f}%)

{advanced_context}

=== CHECKLIST OBLIGATORIO ===
✓ ¿Precio en extremo del rango (no en medio)?
✓ ¿RSI confirma la dirección?
✓ ¿Volumen > 0.8x?
Si el precio está en el MEDIO del rango → ESPERA

Responde SOLO en JSON:
{{
    "decision": "COMPRA" | "VENTA" | "ESPERA",
    "confidence": 0.0-1.0,
    "razonamiento": "Zona: {zone}, RSI: X, Vol: X. Conclusión.",
    "tipo_entrada": "soporte_bollinger" | "resistencia_bollinger" | "sin_oportunidad",
    "alertas": ["rango = menor probabilidad, posición pequeña"]
}}

IMPORTANTE: Rangos tienen MENOR probabilidad que tendencias. Confianza máxima 0.70. Mejor ESPERAR que forzar.
"""

        return self._execute_agent_prompt(prompt, "range_agent")

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
