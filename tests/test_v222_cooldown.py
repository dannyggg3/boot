#!/usr/bin/env python3
"""
Tests para las mejoras de SATH v2.2.2
=====================================
- Cooldown post-cierre por simbolo
- Filtros actualizados en config
"""

import sys
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import yaml


class TestSymbolCooldown:
    """Tests para el cooldown post-cierre de posicion."""

    def test_cooldown_blocks_immediate_reentry(self):
        """Verifica que el cooldown bloquea re-entrada inmediata."""
        from engines.position_engine import PositionEngine

        # Mock de dependencias
        config = {
            'position_management': {
                'enabled': True,
                'protection_mode': 'oco',
                'symbol_cooldown_minutes': 15,
                'trailing_stop': {'enabled': False},
                'portfolio': {'max_concurrent_positions': 3},
                'local_monitoring': {'check_interval_ms': 500}
            }
        }

        # Crear mocks
        market_engine = MagicMock()
        order_manager = MagicMock()
        position_store = MagicMock()
        position_store.get_open_positions.return_value = []
        notifier = MagicMock()

        engine = PositionEngine(
            config=config,
            market_engine=market_engine,
            order_manager=order_manager,
            position_store=position_store,
            notifier=notifier
        )

        # Simular cierre de posicion
        engine.symbol_last_close['ETH/USDT'] = datetime.now()

        # Intentar abrir nueva posicion inmediatamente
        can_open = engine.can_open_position('ETH/USDT')

        # Debe bloquear
        assert can_open is False

    def test_cooldown_allows_after_expiry(self):
        """Verifica que permite re-entrada despues del cooldown."""
        from engines.position_engine import PositionEngine

        config = {
            'position_management': {
                'enabled': True,
                'protection_mode': 'oco',
                'symbol_cooldown_minutes': 15,
                'trailing_stop': {'enabled': False},
                'portfolio': {'max_concurrent_positions': 3},
                'local_monitoring': {'check_interval_ms': 500}
            }
        }

        market_engine = MagicMock()
        order_manager = MagicMock()
        position_store = MagicMock()
        position_store.get_open_positions.return_value = []
        notifier = MagicMock()

        engine = PositionEngine(
            config=config,
            market_engine=market_engine,
            order_manager=order_manager,
            position_store=position_store,
            notifier=notifier
        )

        # Simular cierre hace 20 minutos (cooldown expirado)
        engine.symbol_last_close['ETH/USDT'] = datetime.now() - timedelta(minutes=20)

        # Intentar abrir nueva posicion
        can_open = engine.can_open_position('ETH/USDT')

        # Debe permitir
        assert can_open is True
        # Debe limpiar el registro
        assert 'ETH/USDT' not in engine.symbol_last_close

    def test_cooldown_different_symbols(self):
        """Verifica que cooldown es por simbolo, no global."""
        from engines.position_engine import PositionEngine

        config = {
            'position_management': {
                'enabled': True,
                'protection_mode': 'oco',
                'symbol_cooldown_minutes': 15,
                'trailing_stop': {'enabled': False},
                'portfolio': {'max_concurrent_positions': 3},
                'local_monitoring': {'check_interval_ms': 500}
            }
        }

        market_engine = MagicMock()
        order_manager = MagicMock()
        position_store = MagicMock()
        position_store.get_open_positions.return_value = []
        notifier = MagicMock()

        engine = PositionEngine(
            config=config,
            market_engine=market_engine,
            order_manager=order_manager,
            position_store=position_store,
            notifier=notifier
        )

        # Simular cierre de ETH (en cooldown)
        engine.symbol_last_close['ETH/USDT'] = datetime.now()

        # ETH bloqueado
        assert engine.can_open_position('ETH/USDT') is False

        # BTC debe estar permitido
        assert engine.can_open_position('BTC/USDT') is True

    def test_cooldown_default_value(self):
        """Verifica el valor por defecto del cooldown."""
        from engines.position_engine import PositionEngine

        # Config sin cooldown especificado
        config = {
            'position_management': {
                'enabled': True,
                'protection_mode': 'oco',
                'trailing_stop': {'enabled': False},
                'portfolio': {'max_concurrent_positions': 3},
                'local_monitoring': {'check_interval_ms': 500}
            }
        }

        market_engine = MagicMock()
        order_manager = MagicMock()
        position_store = MagicMock()
        notifier = MagicMock()

        engine = PositionEngine(
            config=config,
            market_engine=market_engine,
            order_manager=order_manager,
            position_store=position_store,
            notifier=notifier
        )

        # Debe usar 15 minutos por defecto
        assert engine.symbol_cooldown_minutes == 15


class TestConfigV222:
    """Tests para la configuracion actualizada v2.2.2."""

    def test_config_paper_loads(self):
        """Verifica que config_paper.yaml carga correctamente."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        assert config is not None
        assert 'ai_agents' in config
        assert 'position_management' in config

    def test_cooldown_in_config(self):
        """Verifica que symbol_cooldown_minutes esta en config."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        pm = config.get('position_management', {})
        cooldown = pm.get('symbol_cooldown_minutes')

        assert cooldown is not None
        assert cooldown == 15

    def test_volatility_threshold_updated(self):
        """Verifica min_volatility_percent actualizado a 0.5."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        agents = config.get('ai_agents', {})
        vol = agents.get('min_volatility_percent')

        assert vol == 0.5

    def test_adx_threshold_updated(self):
        """Verifica min_adx_trend actualizado a 22."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        agents = config.get('ai_agents', {})
        adx = agents.get('min_adx_trend')

        assert adx == 22

    def test_mtf_alignment_updated(self):
        """Verifica MTF min_alignment_score actualizado a 0.60."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        mtf = config.get('multi_timeframe', {})
        alignment = mtf.get('min_alignment_score')

        assert alignment == 0.60

    def test_confidence_threshold_updated(self):
        """Verifica default_min_confidence actualizado a 0.60."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'config_paper.yaml'
        )

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        adaptive = config.get('adaptive_parameters', {})
        confidence = adaptive.get('default_min_confidence')

        assert confidence == 0.60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
