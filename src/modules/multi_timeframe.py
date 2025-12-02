"""
Multi-Timeframe Analysis (MTF) - Análisis Multi-Temporal
=========================================================
Analiza múltiples timeframes para confirmar tendencias y mejorar timing.

Nivel Institucional: Solo operar cuando hay ALINEACIÓN de timeframes.

Timeframes:
- Higher (4H/1D): Tendencia macro - Dirección principal
- Medium (1H): Contexto - Confirmación de tendencia
- Lower (15m): Timing - Punto de entrada

Autor: Trading Bot System
Versión: 1.7
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Dirección de tendencia."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class MTFAnalyzer:
    """
    Analizador Multi-Timeframe para confirmar tendencias.

    Principio: "The trend is your friend" - Solo operar a favor de la tendencia
    en el timeframe superior.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el analizador MTF.

        Args:
            config: Configuración del bot
        """
        self.config = config

        # Configuración MTF
        mtf_config = config.get('multi_timeframe', {})
        self.enabled = mtf_config.get('enabled', True)

        # Timeframes a analizar
        self.higher_tf = mtf_config.get('higher_timeframe', '4h')
        self.medium_tf = mtf_config.get('medium_timeframe', '1h')
        self.lower_tf = mtf_config.get('lower_timeframe', '15m')

        # Peso de cada timeframe en la decisión
        self.weights = mtf_config.get('weights', {
            'higher': 0.50,  # 50% peso - dirección principal
            'medium': 0.30,  # 30% peso - confirmación
            'lower': 0.20    # 20% peso - timing
        })

        # Umbral mínimo de alineación para operar
        self.min_alignment_score = mtf_config.get('min_alignment_score', 0.70)

        logger.info(f"MTF Analyzer: {self.higher_tf} → {self.medium_tf} → {self.lower_tf}")
        logger.info(f"Min alignment score: {self.min_alignment_score}")

    def analyze_timeframe(
        self,
        market_data: Dict[str, Any],
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Analiza un timeframe específico y determina su tendencia.

        Args:
            market_data: Datos técnicos del mercado para este timeframe
            timeframe: Timeframe analizado (ej: '4h', '1h', '15m')

        Returns:
            Análisis del timeframe
        """
        rsi = market_data.get('rsi', 50)
        ema_50 = market_data.get('ema_50', 0)
        ema_200 = market_data.get('ema_200', 0)
        current_price = market_data.get('current_price', 0)
        macd = market_data.get('macd', 0)
        macd_signal = market_data.get('macd_signal', 0)

        # Determinar tendencia
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0

        # 1. Precio vs EMA 200 (señal más importante)
        if current_price > 0 and ema_200 > 0:
            total_signals += 2  # Doble peso
            if current_price > ema_200:
                bullish_signals += 2
            else:
                bearish_signals += 2

        # 2. EMA 50 vs EMA 200 (Golden/Death Cross)
        if ema_50 > 0 and ema_200 > 0:
            total_signals += 1
            if ema_50 > ema_200:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # 3. RSI
        if rsi > 0:
            total_signals += 1
            if rsi > 50:
                bullish_signals += 1
            elif rsi < 50:
                bearish_signals += 1

        # 4. MACD
        if macd != 0:
            total_signals += 1
            if macd > macd_signal:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # Calcular score de tendencia (-1 a 1)
        if total_signals > 0:
            trend_score = (bullish_signals - bearish_signals) / total_signals
        else:
            trend_score = 0

        # Determinar dirección
        if trend_score > 0.3:
            direction = TrendDirection.BULLISH
        elif trend_score < -0.3:
            direction = TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL

        # Calcular fuerza de la tendencia (0 a 1)
        strength = abs(trend_score)

        return {
            'timeframe': timeframe,
            'direction': direction,
            'trend_score': round(trend_score, 3),
            'strength': round(strength, 3),
            'bullish_signals': bullish_signals,
            'bearish_signals': bearish_signals,
            'total_signals': total_signals,
            'details': {
                'price_vs_ema200': 'above' if current_price > ema_200 else 'below',
                'ema_cross': 'golden' if ema_50 > ema_200 else 'death',
                'rsi': rsi,
                'macd_vs_signal': 'above' if macd > macd_signal else 'below'
            }
        }

    def calculate_alignment(
        self,
        higher_analysis: Dict[str, Any],
        medium_analysis: Dict[str, Any],
        lower_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcula el score de alineación entre los 3 timeframes.

        Args:
            higher_analysis: Análisis del timeframe superior
            medium_analysis: Análisis del timeframe medio
            lower_analysis: Análisis del timeframe inferior

        Returns:
            Score de alineación y recomendación
        """
        higher_dir = higher_analysis['direction']
        medium_dir = medium_analysis['direction']
        lower_dir = lower_analysis['direction']

        # Calcular score ponderado
        def direction_to_score(direction: TrendDirection) -> float:
            if direction == TrendDirection.BULLISH:
                return 1.0
            elif direction == TrendDirection.BEARISH:
                return -1.0
            return 0.0

        weighted_score = (
            direction_to_score(higher_dir) * self.weights['higher'] +
            direction_to_score(medium_dir) * self.weights['medium'] +
            direction_to_score(lower_dir) * self.weights['lower']
        )

        # Calcular alineación (qué tan de acuerdo están los timeframes)
        directions = [higher_dir, medium_dir, lower_dir]
        bullish_count = sum(1 for d in directions if d == TrendDirection.BULLISH)
        bearish_count = sum(1 for d in directions if d == TrendDirection.BEARISH)
        neutral_count = sum(1 for d in directions if d == TrendDirection.NEUTRAL)

        # Alineación perfecta = 3/3 en la misma dirección
        max_alignment = max(bullish_count, bearish_count)
        alignment_score = max_alignment / 3.0

        # Penalizar si hay neutrales (indecisión)
        alignment_score -= neutral_count * 0.15
        alignment_score = max(0, alignment_score)

        # Determinar señal final
        if alignment_score >= self.min_alignment_score:
            if weighted_score > 0:
                signal = "COMPRA"
                confidence_boost = alignment_score * 0.2  # Hasta +20% confianza
            elif weighted_score < 0:
                signal = "VENTA"
                confidence_boost = alignment_score * 0.2
            else:
                signal = "ESPERA"
                confidence_boost = 0
        else:
            signal = "ESPERA"
            confidence_boost = 0

        # Razón de la decisión
        if signal == "ESPERA":
            if alignment_score < self.min_alignment_score:
                reason = f"Timeframes no alineados ({alignment_score:.0%} < {self.min_alignment_score:.0%})"
            else:
                reason = "Sin tendencia clara"
        else:
            aligned = [tf for tf, d in [
                (self.higher_tf, higher_dir),
                (self.medium_tf, medium_dir),
                (self.lower_tf, lower_dir)
            ] if (d == TrendDirection.BULLISH and signal == "COMPRA") or
                 (d == TrendDirection.BEARISH and signal == "VENTA")]
            reason = f"Alineación {signal}: {', '.join(aligned)} ({alignment_score:.0%})"

        return {
            'signal': signal,
            'alignment_score': round(alignment_score, 3),
            'weighted_score': round(weighted_score, 3),
            'confidence_boost': round(confidence_boost, 3),
            'reason': reason,
            'details': {
                'higher': {
                    'timeframe': self.higher_tf,
                    'direction': higher_dir.value,
                    'strength': higher_analysis['strength']
                },
                'medium': {
                    'timeframe': self.medium_tf,
                    'direction': medium_dir.value,
                    'strength': medium_analysis['strength']
                },
                'lower': {
                    'timeframe': self.lower_tf,
                    'direction': lower_dir.value,
                    'strength': lower_analysis['strength']
                }
            },
            'recommendation': self._generate_recommendation(
                signal, alignment_score, higher_dir, lower_analysis
            )
        }

    def _generate_recommendation(
        self,
        signal: str,
        alignment_score: float,
        higher_direction: TrendDirection,
        lower_analysis: Dict[str, Any]
    ) -> str:
        """Genera recomendación textual para el trader."""
        if signal == "ESPERA":
            return "⏸️ Esperar alineación de timeframes antes de entrar"

        direction_text = "alcista" if higher_direction == TrendDirection.BULLISH else "bajista"
        strength_text = "fuerte" if lower_analysis['strength'] > 0.6 else "moderada"

        return (
            f"✅ Tendencia {direction_text} confirmada en múltiples TF "
            f"(alineación {alignment_score:.0%}, fuerza {strength_text})"
        )

    def get_mtf_filter_result(
        self,
        market_data_higher: Dict[str, Any],
        market_data_medium: Dict[str, Any],
        market_data_lower: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Método principal: Obtiene el resultado del filtro MTF.

        Args:
            market_data_higher: Datos del timeframe superior (4H)
            market_data_medium: Datos del timeframe medio (1H)
            market_data_lower: Datos del timeframe inferior (15m)

        Returns:
            Resultado completo del análisis MTF
        """
        if not self.enabled:
            return {
                'enabled': False,
                'signal': 'SKIP',
                'reason': 'MTF disabled'
            }

        # Analizar cada timeframe
        higher_analysis = self.analyze_timeframe(market_data_higher, self.higher_tf)
        medium_analysis = self.analyze_timeframe(market_data_medium, self.medium_tf)
        lower_analysis = self.analyze_timeframe(market_data_lower, self.lower_tf)

        # Calcular alineación
        alignment = self.calculate_alignment(
            higher_analysis,
            medium_analysis,
            lower_analysis
        )

        logger.info(f"📊 MTF Analysis: {self.higher_tf}={higher_analysis['direction'].value} | "
                   f"{self.medium_tf}={medium_analysis['direction'].value} | "
                   f"{self.lower_tf}={lower_analysis['direction'].value}")
        logger.info(f"📈 Alignment: {alignment['alignment_score']:.0%} → {alignment['signal']}")

        return {
            'enabled': True,
            **alignment,
            'analyses': {
                'higher': higher_analysis,
                'medium': medium_analysis,
                'lower': lower_analysis
            }
        }


# Singleton para uso global
_mtf_analyzer = None


def get_mtf_analyzer(config: Dict[str, Any] = None) -> Optional[MTFAnalyzer]:
    """Obtiene el singleton del MTF Analyzer."""
    global _mtf_analyzer
    if _mtf_analyzer is None and config:
        _mtf_analyzer = MTFAnalyzer(config)
    return _mtf_analyzer


if __name__ == "__main__":
    # Test del módulo
    logging.basicConfig(level=logging.INFO)

    config = {
        'multi_timeframe': {
            'enabled': True,
            'higher_timeframe': '4h',
            'medium_timeframe': '1h',
            'lower_timeframe': '15m',
            'min_alignment_score': 0.70
        }
    }

    mtf = MTFAnalyzer(config)

    # Simular datos de mercado alineados (bullish)
    bullish_data = {
        'current_price': 50000,
        'ema_50': 49000,
        'ema_200': 48000,
        'rsi': 60,
        'macd': 100,
        'macd_signal': 80
    }

    # Simular datos mixtos
    mixed_data = {
        'current_price': 50000,
        'ema_50': 51000,
        'ema_200': 48000,
        'rsi': 45,
        'macd': -50,
        'macd_signal': -30
    }

    result = mtf.get_mtf_filter_result(bullish_data, bullish_data, bullish_data)
    print("\n=== MTF RESULT (Aligned Bullish) ===")
    print(f"Signal: {result['signal']}")
    print(f"Alignment: {result['alignment_score']:.0%}")
    print(f"Recommendation: {result['recommendation']}")

    result2 = mtf.get_mtf_filter_result(bullish_data, mixed_data, bullish_data)
    print("\n=== MTF RESULT (Mixed) ===")
    print(f"Signal: {result2['signal']}")
    print(f"Alignment: {result2['alignment_score']:.0%}")
    print(f"Reason: {result2['reason']}")
