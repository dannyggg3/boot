"""
Technical Analysis Module - Módulo de Análisis Técnico
========================================================
Este módulo calcula indicadores técnicos a partir de datos OHLCV
para apoyar las decisiones de trading.

Autor: Trading Bot System
Versión: 1.0
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    Analizador técnico que calcula indicadores de trading.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el analizador técnico.

        Args:
            config: Configuración de indicadores técnicos
        """
        self.config = config
        self.indicators_config = config.get('technical_analysis', {}).get('indicators', {})
        logger.info("Technical Analyzer inicializado")

    def analyze(self, ohlcv_data: List[List]) -> Dict[str, Any]:
        """
        Analiza los datos OHLCV y calcula todos los indicadores.

        Args:
            ohlcv_data: Lista de velas [timestamp, open, high, low, close, volume]

        Returns:
            Diccionario con todos los indicadores calculados
        """
        if not ohlcv_data or len(ohlcv_data) < 200:
            logger.warning("Datos insuficientes para análisis técnico")
            return {}

        try:
            # Convertir a DataFrame
            df = self._create_dataframe(ohlcv_data)

            # Calcular indicadores
            indicators = {}

            if self.indicators_config.get('rsi', {}).get('enabled', True):
                indicators.update(self._calculate_rsi(df))

            if self.indicators_config.get('ema', {}).get('enabled', True):
                indicators.update(self._calculate_ema(df))

            if self.indicators_config.get('bollinger_bands', {}).get('enabled', True):
                indicators.update(self._calculate_bollinger_bands(df))

            if self.indicators_config.get('macd', {}).get('enabled', True):
                indicators.update(self._calculate_macd(df))

            if self.indicators_config.get('atr', {}).get('enabled', True):
                indicators.update(self._calculate_atr(df))

            # Análisis de tendencia
            indicators['trend_analysis'] = self._analyze_trend(df, indicators)

            # Análisis de volumen
            indicators['volume_24h'] = self._analyze_volume(df)

            # Precio actual
            indicators['current_price'] = float(df['close'].iloc[-1])

            logger.debug(f"Indicadores calculados: {list(indicators.keys())}")
            return indicators

        except Exception as e:
            logger.error(f"Error en análisis técnico: {e}")
            return {}

    def _create_dataframe(self, ohlcv_data: List[List]) -> pd.DataFrame:
        """
        Convierte datos OHLCV a DataFrame de pandas.

        Args:
            ohlcv_data: Lista de velas

        Returns:
            DataFrame con columnas [timestamp, open, high, low, close, volume]
        """
        df = pd.DataFrame(
            ohlcv_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Convertir a float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df

    def _calculate_rsi(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula el RSI (Relative Strength Index).

        Args:
            df: DataFrame con datos OHLCV

        Returns:
            Diccionario con valores de RSI
        """
        config = self.indicators_config.get('rsi', {})
        period = config.get('period', 14)
        overbought = config.get('overbought', 70)
        oversold = config.get('oversold', 30)

        rsi = ta.rsi(df['close'], length=period)
        current_rsi = float(rsi.iloc[-1])

        # Determinar estado
        if current_rsi > overbought:
            status = "sobrecomprado"
        elif current_rsi < oversold:
            status = "sobrevendido"
        else:
            status = "neutral"

        return {
            'rsi': round(current_rsi, 2),
            'rsi_status': status
        }

    def _calculate_ema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula las EMAs (Exponential Moving Averages).

        Args:
            df: DataFrame con datos OHLCV

        Returns:
            Diccionario con valores de EMA
        """
        config = self.indicators_config.get('ema', {})
        short_period = config.get('short_period', 50)
        long_period = config.get('long_period', 200)

        ema_short = ta.ema(df['close'], length=short_period)
        ema_long = ta.ema(df['close'], length=long_period)

        current_price = float(df['close'].iloc[-1])
        current_ema_50 = float(ema_short.iloc[-1])
        current_ema_200 = float(ema_long.iloc[-1])

        # Golden Cross / Death Cross
        cross_signal = "neutral"
        if current_ema_50 > current_ema_200:
            cross_signal = "golden_cross"  # Señal alcista
        elif current_ema_50 < current_ema_200:
            cross_signal = "death_cross"  # Señal bajista

        return {
            'ema_50': round(current_ema_50, 2),
            'ema_200': round(current_ema_200, 2),
            'ema_cross_signal': cross_signal,
            'price_above_ema_200': current_price > current_ema_200
        }

    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula las Bandas de Bollinger.

        Args:
            df: DataFrame con datos OHLCV

        Returns:
            Diccionario con valores de Bollinger Bands
        """
        config = self.indicators_config.get('bollinger_bands', {})
        period = config.get('period', 20)
        std_dev = config.get('std_dev', 2)

        bbands = ta.bbands(df['close'], length=period, std=std_dev)

        # Buscar columnas de forma robusta (maneja diferentes versiones de pandas-ta)
        upper_col = [col for col in bbands.columns if 'BBU' in col][0]
        middle_col = [col for col in bbands.columns if 'BBM' in col][0]
        lower_col = [col for col in bbands.columns if 'BBL' in col][0]

        current_price = float(df['close'].iloc[-1])
        upper_band = float(bbands[upper_col].iloc[-1])
        middle_band = float(bbands[middle_col].iloc[-1])
        lower_band = float(bbands[lower_col].iloc[-1])

        # Determinar posición del precio
        if current_price > upper_band:
            position = "por encima de banda superior"
        elif current_price < lower_band:
            position = "por debajo de banda inferior"
        else:
            position = "dentro de bandas"

        return {
            'bollinger_bands': {
                'upper': round(upper_band, 2),
                'middle': round(middle_band, 2),
                'lower': round(lower_band, 2)
            },
            'bb_position': position
        }

    def _calculate_macd(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula el MACD (Moving Average Convergence Divergence).

        Args:
            df: DataFrame con datos OHLCV

        Returns:
            Diccionario con valores de MACD
        """
        config = self.indicators_config.get('macd', {})
        fast = config.get('fast_period', 12)
        slow = config.get('slow_period', 26)
        signal = config.get('signal_period', 9)

        macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)

        current_macd = float(macd[f'MACD_{fast}_{slow}_{signal}'].iloc[-1])
        current_signal = float(macd[f'MACDs_{fast}_{slow}_{signal}'].iloc[-1])
        current_histogram = float(macd[f'MACDh_{fast}_{slow}_{signal}'].iloc[-1])

        # Señal de cruce
        cross_signal = "neutral"
        if current_macd > current_signal and current_histogram > 0:
            cross_signal = "bullish"  # MACD por encima de señal (alcista)
        elif current_macd < current_signal and current_histogram < 0:
            cross_signal = "bearish"  # MACD por debajo de señal (bajista)

        return {
            'macd': round(current_macd, 4),
            'macd_signal': round(current_signal, 4),
            'macd_histogram': round(current_histogram, 4),
            'macd_cross_signal': cross_signal
        }

    def _calculate_atr(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula el ATR (Average True Range) - Volatilidad.

        Args:
            df: DataFrame con datos OHLCV

        Returns:
            Diccionario con valores de ATR
        """
        config = self.indicators_config.get('atr', {})
        period = config.get('period', 14)

        atr = ta.atr(df['high'], df['low'], df['close'], length=period)
        current_atr = float(atr.iloc[-1])
        current_price = float(df['close'].iloc[-1])

        # ATR como porcentaje del precio (volatilidad normalizada)
        atr_percentage = (current_atr / current_price) * 100

        # Determinar nivel de volatilidad
        if atr_percentage > 3:
            volatility_level = "alta"
        elif atr_percentage < 1:
            volatility_level = "baja"
        else:
            volatility_level = "media"

        return {
            'atr': round(current_atr, 2),
            'atr_percentage': round(atr_percentage, 2),
            'volatility_level': volatility_level
        }

    def _analyze_trend(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> str:
        """
        Analiza la tendencia general del mercado.

        Args:
            df: DataFrame con datos OHLCV
            indicators: Indicadores ya calculados

        Returns:
            Descripción textual de la tendencia
        """
        current_price = float(df['close'].iloc[-1])

        # Factores de tendencia
        factors = []

        # 1. EMA Cross
        if 'ema_cross_signal' in indicators:
            if indicators['ema_cross_signal'] == 'golden_cross':
                factors.append("EMA golden cross (alcista)")
            elif indicators['ema_cross_signal'] == 'death_cross':
                factors.append("EMA death cross (bajista)")

        # 2. Posición respecto a EMA 200
        if 'price_above_ema_200' in indicators:
            if indicators['price_above_ema_200']:
                factors.append("precio por encima de EMA 200 (alcista)")
            else:
                factors.append("precio por debajo de EMA 200 (bajista)")

        # 3. RSI
        if 'rsi_status' in indicators:
            factors.append(f"RSI {indicators['rsi_status']}")

        # 4. MACD
        if 'macd_cross_signal' in indicators:
            factors.append(f"MACD {indicators['macd_cross_signal']}")

        # Unir factores
        trend_description = ", ".join(factors) if factors else "Sin tendencia clara"

        return trend_description

    def _analyze_volume(self, df: pd.DataFrame) -> float:
        """
        Analiza el volumen de las últimas 24 horas.

        Args:
            df: DataFrame con datos OHLCV

        Returns:
            Volumen total de las últimas 24 períodos
        """
        # Tomar las últimas 24 velas (si son de 1h, equivale a 24h)
        volume_24h = float(df['volume'].tail(24).sum())
        return round(volume_24h, 2)

    def get_support_resistance(self, df: pd.DataFrame, periods: int = 100) -> Dict[str, float]:
        """
        Calcula niveles de soporte y resistencia.

        Args:
            df: DataFrame con datos OHLCV
            periods: Número de períodos a analizar

        Returns:
            Diccionario con niveles de soporte y resistencia
        """
        try:
            recent_data = df.tail(periods)

            # Soporte: mínimo más alto en el período
            support = float(recent_data['low'].min())

            # Resistencia: máximo más alto en el período
            resistance = float(recent_data['high'].max())

            return {
                'support': round(support, 2),
                'resistance': round(resistance, 2)
            }

        except Exception as e:
            logger.error(f"Error calculando soporte/resistencia: {e}")
            return {'support': 0, 'resistance': 0}


if __name__ == "__main__":
    # Prueba básica del módulo
    logging.basicConfig(level=logging.INFO)

    # Configuración de prueba
    test_config = {
        'technical_analysis': {
            'indicators': {
                'rsi': {'enabled': True, 'period': 14},
                'ema': {'enabled': True, 'short_period': 50, 'long_period': 200},
                'bollinger_bands': {'enabled': True, 'period': 20, 'std_dev': 2},
                'macd': {'enabled': True},
                'atr': {'enabled': True, 'period': 14}
            }
        }
    }

    analyzer = TechnicalAnalyzer(test_config)

    # Generar datos de prueba (simulación de precios)
    import random
    test_ohlcv = []
    base_price = 50000
    for i in range(250):
        timestamp = 1700000000000 + (i * 3600000)  # 1 hora entre velas
        open_price = base_price + random.uniform(-100, 100)
        high_price = open_price + random.uniform(0, 200)
        low_price = open_price - random.uniform(0, 200)
        close_price = (high_price + low_price) / 2
        volume = random.uniform(1000, 5000)

        test_ohlcv.append([timestamp, open_price, high_price, low_price, close_price, volume])
        base_price = close_price

    # Analizar
    indicators = analyzer.analyze(test_ohlcv)

    print("\n=== INDICADORES TÉCNICOS ===")
    for key, value in indicators.items():
        print(f"{key}: {value}")
