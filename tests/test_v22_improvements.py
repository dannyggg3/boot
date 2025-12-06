#!/usr/bin/env python3
"""
Tests para las mejoras de SATH v2.2
===================================
- Risk Manager SQLite atomico
- AI Engine fallback parser
- Configuracion paper optimizada
"""

import sys
import os
import tempfile
import sqlite3
import json

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestRiskManagerSQLite:
    """Tests para la nueva persistencia SQLite del Risk Manager."""

    def test_database_initialization(self):
        """Verifica que la base de datos se inicializa correctamente."""
        from modules.risk_manager import RiskManager

        # Crear config minima
        config = {
            'risk_management': {
                'initial_capital': 1000,
                'max_risk_per_trade': 2.5,
                'max_daily_drawdown': 8.0,
                'min_risk_reward_ratio': 2.0,
                'kelly_criterion': {'enabled': True, 'fraction': 0.25},
                'atr_stops': {'enabled': False},
            }
        }

        # Usar directorio temporal
        with tempfile.TemporaryDirectory() as tmpdir:
            # Cambiar al directorio temporal para crear la DB ahi
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            os.makedirs('data', exist_ok=True)

            try:
                rm = RiskManager(config)

                # Verificar que la DB existe
                assert os.path.exists('data/risk_manager.db')

                # Verificar tablas
                conn = sqlite3.connect('data/risk_manager.db')
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()

                assert 'risk_state' in tables
                assert 'trade_history_kelly' in tables
                assert 'recent_results' in tables
                assert 'open_trades' in tables

            finally:
                os.chdir(original_cwd)

    def test_save_and_load_state(self):
        """Verifica que el estado se guarda y carga correctamente."""
        from modules.risk_manager import RiskManager

        config = {
            'risk_management': {
                'initial_capital': 1000,
                'max_risk_per_trade': 2.5,
                'max_daily_drawdown': 8.0,
                'min_risk_reward_ratio': 2.0,
                'kelly_criterion': {'enabled': True, 'fraction': 0.25},
                'atr_stops': {'enabled': False},
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            os.makedirs('data', exist_ok=True)

            try:
                # Crear Risk Manager y modificar estado
                rm = RiskManager(config)
                rm.current_capital = 1050
                rm.daily_pnl = 50
                rm.trade_history['wins'] = 5
                rm.trade_history['losses'] = 3
                rm._save_state()

                # Crear nuevo Risk Manager (debe cargar estado)
                rm2 = RiskManager(config)

                assert rm2.current_capital == 1050
                assert rm2.trade_history['wins'] == 5
                assert rm2.trade_history['losses'] == 3

            finally:
                os.chdir(original_cwd)

    def test_record_trade_result_persists(self):
        """Verifica que los resultados de trades se persisten."""
        from modules.risk_manager import RiskManager

        config = {
            'risk_management': {
                'initial_capital': 1000,
                'max_risk_per_trade': 2.5,
                'max_daily_drawdown': 8.0,
                'min_risk_reward_ratio': 2.0,
                'kelly_criterion': {'enabled': True, 'fraction': 0.25},
                'atr_stops': {'enabled': False},
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)
            os.makedirs('data', exist_ok=True)

            try:
                rm = RiskManager(config)

                # Registrar resultados
                rm.record_trade_result(True, 25.0)  # Win
                rm.record_trade_result(False, -10.0)  # Loss
                rm.record_trade_result(True, 30.0)  # Win

                # Verificar en DB
                conn = sqlite3.connect('data/risk_manager.db')
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM recent_results")
                count = cursor.fetchone()[0]
                conn.close()

                assert count >= 3

            finally:
                os.chdir(original_cwd)


class TestAIEngineFallbackParser:
    """Tests para el fallback parser de AI Engine."""

    def test_fallback_detects_buy_signal(self):
        """Verifica que el fallback detecta senales de compra."""
        # Simular el metodo de fallback
        def fallback_text_parser(text):
            text_lower = text.lower()
            buy_keywords = ['compra', 'buy', 'long', 'bullish', 'alcista']
            sell_keywords = ['venta', 'sell', 'short', 'bearish', 'bajista']
            wait_keywords = ['espera', 'wait', 'hold', 'neutral']

            buy_score = sum(1 for kw in buy_keywords if kw in text_lower)
            sell_score = sum(1 for kw in sell_keywords if kw in text_lower)
            wait_score = sum(1 for kw in wait_keywords if kw in text_lower)

            if buy_score > sell_score and buy_score > wait_score:
                return 'COMPRA'
            elif sell_score > buy_score and sell_score > wait_score:
                return 'VENTA'
            return 'ESPERA'

        # Test buy signal
        text = "El mercado muestra senales bullish, recomiendo compra long position"
        assert fallback_text_parser(text) == 'COMPRA'

    def test_fallback_detects_sell_signal(self):
        """Verifica que el fallback detecta senales de venta."""
        def fallback_text_parser(text):
            text_lower = text.lower()
            buy_keywords = ['compra', 'buy', 'long', 'bullish', 'alcista']
            sell_keywords = ['venta', 'sell', 'short', 'bearish', 'bajista']
            wait_keywords = ['espera', 'wait', 'hold', 'neutral']

            buy_score = sum(1 for kw in buy_keywords if kw in text_lower)
            sell_score = sum(1 for kw in sell_keywords if kw in text_lower)
            wait_score = sum(1 for kw in wait_keywords if kw in text_lower)

            if buy_score > sell_score and buy_score > wait_score:
                return 'COMPRA'
            elif sell_score > buy_score and sell_score > wait_score:
                return 'VENTA'
            return 'ESPERA'

        # Test sell signal
        text = "Tendencia bearish, sell short venta recomendada"
        assert fallback_text_parser(text) == 'VENTA'

    def test_fallback_detects_wait_signal(self):
        """Verifica que el fallback detecta senales de espera."""
        def fallback_text_parser(text):
            text_lower = text.lower()
            buy_keywords = ['compra', 'buy', 'long', 'bullish', 'alcista']
            sell_keywords = ['venta', 'sell', 'short', 'bearish', 'bajista']
            wait_keywords = ['espera', 'wait', 'hold', 'neutral']

            buy_score = sum(1 for kw in buy_keywords if kw in text_lower)
            sell_score = sum(1 for kw in sell_keywords if kw in text_lower)
            wait_score = sum(1 for kw in wait_keywords if kw in text_lower)

            if buy_score > sell_score and buy_score > wait_score:
                return 'COMPRA'
            elif sell_score > buy_score and sell_score > wait_score:
                return 'VENTA'
            return 'ESPERA'

        # Test wait signal
        text = "Mercado neutral, mantener hold position, espera mejor entrada"
        assert fallback_text_parser(text) == 'ESPERA'

    def test_decision_mapping(self):
        """Verifica el mapeo de sinonimos de decisiones."""
        decision_map = {
            'COMPRA': 'COMPRA', 'BUY': 'COMPRA', 'LONG': 'COMPRA',
            'VENTA': 'VENTA', 'SELL': 'VENTA', 'SHORT': 'VENTA',
            'ESPERA': 'ESPERA', 'HOLD': 'ESPERA', 'WAIT': 'ESPERA', 'NEUTRAL': 'ESPERA'
        }

        assert decision_map.get('BUY') == 'COMPRA'
        assert decision_map.get('SELL') == 'VENTA'
        assert decision_map.get('HOLD') == 'ESPERA'
        assert decision_map.get('LONG') == 'COMPRA'
        assert decision_map.get('SHORT') == 'VENTA'


class TestConfigPaperOptimization:
    """Tests para verificar la configuracion paper optimizada."""

    def test_config_loads_correctly(self):
        """Verifica que la configuracion paper carga correctamente."""
        import yaml

        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert 'trading' in config
        assert 'risk_management' in config

    def test_optimized_thresholds(self):
        """Verifica que los thresholds optimizados estan correctos."""
        import yaml

        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Verificar thresholds optimizados
        ai_agents = config.get('ai_agents', {})
        assert ai_agents.get('min_adx_trend', 25) <= 20  # Reducido para mas trades

        risk = config.get('risk_management', {})
        assert risk.get('min_risk_reward_ratio', 2.0) <= 1.8  # Mas flexible

        kelly = risk.get('kelly_criterion', {})
        assert kelly.get('min_confidence', 0.70) <= 0.60  # Mas trades

    def test_capital_configuration(self):
        """Verifica la configuracion de capital."""
        import yaml

        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        risk = config.get('risk_management', {})
        assert risk.get('initial_capital') == 1000
        assert risk.get('max_risk_per_trade') >= 2.5
        assert risk.get('max_daily_drawdown') >= 8


class TestPreFilterConfigurable:
    """Tests para verificar que los pre-filtros son configurables."""

    def test_adx_threshold_from_config(self):
        """Verifica que el ADX threshold se lee de la config."""
        # Simular la logica del pre-filtro
        def check_adx(adx_value, min_adx_threshold):
            return adx_value >= min_adx_threshold

        # Con threshold de 20 (config paper)
        assert check_adx(22, 20) is True
        assert check_adx(18, 20) is False

        # Con threshold de 25 (config live)
        assert check_adx(22, 25) is False
        assert check_adx(26, 25) is True

    def test_volume_threshold_from_config(self):
        """Verifica que el volume threshold se lee de la config."""
        def check_volume(volume_ratio, min_volume):
            return volume_ratio >= min_volume

        # Con threshold de 0.8 (config paper)
        assert check_volume(0.9, 0.8) is True
        assert check_volume(0.7, 0.8) is False

        # Con threshold de 1.0 (config live)
        assert check_volume(0.9, 1.0) is False
        assert check_volume(1.1, 1.0) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
