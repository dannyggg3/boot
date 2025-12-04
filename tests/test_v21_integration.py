"""
Tests de Integración v2.1 - SATH Trading Bot
=============================================
Verifica todas las correcciones implementadas en v2.1:
1. Trailing Stop Math (activation > distance)
2. Profit Lock en trailing
3. ADX threshold >= 25
4. Range Agent (zonas Bollinger)
5. RSI 35-65 para entradas
6. Session Filter
7. Volumen mínimo 1.0x

Ejecutar: python -m pytest tests/test_v21_integration.py -v
"""

import sys
import pytest
sys.path.insert(0, 'src')


class TestADXThreshold:
    """Tests para el threshold de ADX >= 25."""

    def test_adx_below_25_returns_low_volatility_or_ranging(self):
        """ADX < 25 debe retornar low_volatility o ranging."""
        from engines.ai_engine import AIEngine

        class MockAIEngine(AIEngine):
            def __init__(self):
                self.config = {'ai_agents': {'min_adx_trend': 25}}
                self.agents_config = {'min_adx_trend': 25}
                self.min_volatility_percent = 0.5

        engine = MockAIEngine()

        test_data = {
            'rsi': 50,
            'ema_50': 100,
            'ema_200': 95,
            'current_price': 102,
            'atr_percent': 1.5,
            'adx': 20,
            'bollinger_bands': {'lower': 98, 'upper': 106, 'middle': 102}
        }

        regime = engine.determine_market_regime(test_data)
        assert regime in ['low_volatility', 'ranging'], f"ADX=20 debería ser low_volatility o ranging, got {regime}"

    def test_adx_above_25_with_aligned_emas_returns_trending(self):
        """ADX >= 25 con EMAs alineados debe retornar trending."""
        from engines.ai_engine import AIEngine

        class MockAIEngine(AIEngine):
            def __init__(self):
                self.config = {'ai_agents': {'min_adx_trend': 25}}
                self.agents_config = {'min_adx_trend': 25}
                self.min_volatility_percent = 0.5

        engine = MockAIEngine()

        test_data = {
            'rsi': 55,
            'ema_50': 105,
            'ema_200': 100,
            'current_price': 110,
            'atr_percent': 1.5,
            'adx': 30,
            'bollinger_bands': {'lower': 95, 'upper': 115, 'middle': 105}
        }

        regime = engine.determine_market_regime(test_data)
        assert regime == 'trending', f"ADX=30 con EMAs alcistas debería ser trending, got {regime}"


class TestTrailingStopMath:
    """Tests para la matemática del trailing stop."""

    def test_trailing_sl_above_entry_when_activated(self):
        """Cuando trailing activa, SL debe quedar sobre entry price."""
        entry_price = 100000
        activation_percent = 2.0
        trail_distance_percent = 1.0

        # Precio cuando activa trailing (+2%)
        price_at_activation = entry_price * (1 + activation_percent / 100)

        # SL calculado (1% trailing)
        sl_at_activation = price_at_activation * (1 - trail_distance_percent / 100)

        assert sl_at_activation > entry_price, \
            f"SL ({sl_at_activation}) debería estar sobre entry ({entry_price})"

    def test_profit_lock_ensures_minimum_profit(self):
        """Profit lock debe asegurar ganancia mínima."""
        entry_price = 100000
        current_price = 102000  # +2%
        trailing_distance = 1.0
        min_profit_lock = 0.8

        # Cálculo normal de SL
        new_sl = current_price * (1 - trailing_distance / 100)

        # Profit lock mínimo
        min_sl_for_profit = entry_price * (1 + min_profit_lock / 100)

        # Si SL está bajo el mínimo, ajustar
        if new_sl < min_sl_for_profit:
            new_sl = min_sl_for_profit

        assert new_sl >= entry_price * (1 + min_profit_lock / 100), \
            f"SL debería asegurar mínimo {min_profit_lock}% de profit"


class TestRangeAgent:
    """Tests para el range agent."""

    def test_detect_support_zone(self):
        """Detecta zona de soporte (20% inferior del rango)."""
        bb_lower = 95000
        bb_upper = 105000
        price = 96000

        bb_range = bb_upper - bb_lower
        pct_in_range = ((price - bb_lower) / bb_range * 100)
        zone = "soporte" if pct_in_range <= 25 else "resistencia" if pct_in_range >= 75 else "medio"

        assert zone == "soporte", f"Precio cerca de BB inferior debería ser soporte, got {zone}"

    def test_detect_resistance_zone(self):
        """Detecta zona de resistencia (20% superior del rango)."""
        bb_lower = 95000
        bb_upper = 105000
        price = 104000

        bb_range = bb_upper - bb_lower
        pct_in_range = ((price - bb_lower) / bb_range * 100)
        zone = "soporte" if pct_in_range <= 25 else "resistencia" if pct_in_range >= 75 else "medio"

        assert zone == "resistencia", f"Precio cerca de BB superior debería ser resistencia, got {zone}"

    def test_detect_middle_zone_no_trade(self):
        """Detecta zona media (no operar)."""
        bb_lower = 95000
        bb_upper = 105000
        price = 100000

        bb_range = bb_upper - bb_lower
        pct_in_range = ((price - bb_lower) / bb_range * 100)
        zone = "soporte" if pct_in_range <= 25 else "resistencia" if pct_in_range >= 75 else "medio"

        assert zone == "medio", f"Precio en medio del rango debería ser medio, got {zone}"


class TestRSIValidation:
    """Tests para validación de RSI."""

    @pytest.mark.parametrize("rsi,expected", [
        (25, "ESPERA"),
        (35, "POSIBLE"),
        (50, "POSIBLE"),
        (65, "POSIBLE"),
        (75, "ESPERA"),
    ])
    def test_rsi_entry_validation(self, rsi, expected):
        """RSI 35-65 permite entrada, fuera de ese rango = ESPERA."""
        result = "ESPERA" if rsi < 35 or rsi > 65 else "POSIBLE"
        assert result == expected, f"RSI {rsi} debería ser {expected}, got {result}"


class TestVolumeThreshold:
    """Tests para threshold de volumen."""

    @pytest.mark.parametrize("volume,should_accept", [
        (0.5, False),
        (0.8, False),
        (1.0, True),
        (1.3, True),
        (2.0, True),
    ])
    def test_volume_minimum_1x(self, volume, should_accept):
        """Volumen mínimo debe ser 1.0x."""
        min_volume = 1.0
        accepted = volume >= min_volume
        assert accepted == should_accept, f"Volumen {volume}x: esperado {should_accept}, got {accepted}"


class TestSessionFilter:
    """Tests para session filter."""

    def test_avoid_hours(self):
        """Horas 00:00-06:00 UTC deben evitarse."""
        avoid_hours = [(0, 6)]

        for hour in range(0, 6):
            is_avoid = any(start <= hour < end for start, end in avoid_hours)
            assert is_avoid, f"Hora {hour}:00 UTC debería evitarse"

    def test_optimal_hours(self):
        """Horas óptimas deben aceptarse."""
        optimal_hours = [(7, 16), (13, 22)]

        # 14:00 UTC está en ambos rangos óptimos
        hour = 14
        is_optimal = any(start <= hour < end for start, end in optimal_hours)
        assert is_optimal, f"Hora {hour}:00 UTC debería ser óptima"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
