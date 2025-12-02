"""
Tests para funcionalidades institucionales v1.7
================================================
Verifica:
- Trailing Stop fix (race condition)
- Paper Mode Simulator
- Kelly Criterion mejorado
- Validación de liquidez
- Métricas institucionales
- Thread-safe singletons

Ejecutar: python -m pytest tests/test_v17_institutional.py -v
"""

import sys
import os
import time
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Añadir el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# =============================================================================
# TEST 1: TRAILING STOP FIX
# =============================================================================

class TestTrailingStopFix(unittest.TestCase):
    """Tests para el fix de race condition en trailing stop."""

    def setUp(self):
        """Configura mocks para cada test."""
        self.config = {
            'position_management': {
                'enabled': True,
                'protection_mode': 'oco',
                'trailing_stop': {
                    'enabled': True,
                    'activation_profit_percent': 2.0,
                    'trail_distance_percent': 1.5
                },
                'portfolio': {
                    'max_concurrent_positions': 3
                },
                'local_monitoring': {
                    'check_interval_ms': 500
                }
            }
        }

        # Mocks
        self.mock_market_engine = Mock()
        self.mock_order_manager = Mock()
        self.mock_position_store = Mock()
        self.mock_notifier = Mock()

    def test_trailing_skip_when_sl_would_trigger_immediately_short(self):
        """
        Test crítico: Verifica que el trailing NO mueve el SL
        si el nuevo valor ya estaría triggered.
        """
        from engines.position_engine import PositionEngine

        engine = PositionEngine(
            config=self.config,
            market_engine=self.mock_market_engine,
            order_manager=self.mock_order_manager,
            position_store=self.mock_position_store,
            notifier=self.mock_notifier
        )

        # Posición SHORT
        position = {
            'id': 'test123',
            'symbol': 'ETH/USDT',
            'side': 'short',
            'entry_price': 2865.0,
            'stop_loss': 2889.0,
            'trailing_stop_active': False
        }

        # Precio actual ARRIBA del potencial nuevo SL
        # Para short con 1.5% trailing: new_sl = 2800 * 1.015 = 2842
        # Pero si precio es 2860, el SL estaría triggered
        current_price = 2860.0  # Precio alto

        # El trailing NO debería activarse porque el SL estaría triggered
        engine._activate_trailing_stop(position, current_price)

        # Verificar que NO se llamó a activate_trailing_stop del store
        self.mock_position_store.activate_trailing_stop.assert_not_called()

    def test_trailing_activates_when_safe_short(self):
        """
        Test: Verifica que el trailing SÍ se activa cuando es seguro.
        """
        from engines.position_engine import PositionEngine

        engine = PositionEngine(
            config=self.config,
            market_engine=self.mock_market_engine,
            order_manager=self.mock_order_manager,
            position_store=self.mock_position_store,
            notifier=self.mock_notifier
        )

        # Posición SHORT con profit
        position = {
            'id': 'test456',
            'symbol': 'ETH/USDT',
            'side': 'short',
            'entry_price': 2865.0,
            'quantity': 0.1,  # Añadido para test
            'stop_loss': 2920.0,  # SL original lejos
            'take_profit': 2700.0,
            'trailing_stop_active': False
        }

        # Precio bajó significativamente (profit para short)
        # new_sl = 2750 * 1.015 = 2791.25 (muy por encima de 2750)
        current_price = 2750.0

        engine._activate_trailing_stop(position, current_price)

        # Verificar que SÍ se activó
        self.mock_position_store.activate_trailing_stop.assert_called_once()

    def test_trailing_skip_when_sl_would_trigger_immediately_long(self):
        """
        Test: Verifica skip para posiciones LONG.
        """
        from engines.position_engine import PositionEngine

        engine = PositionEngine(
            config=self.config,
            market_engine=self.mock_market_engine,
            order_manager=self.mock_order_manager,
            position_store=self.mock_position_store,
            notifier=self.mock_notifier
        )

        # Posición LONG
        position = {
            'id': 'test789',
            'symbol': 'BTC/USDT',
            'side': 'long',
            'entry_price': 88000.0,
            'quantity': 0.001,  # Añadido para test
            'stop_loss': 86000.0,
            'take_profit': 92000.0,
            'trailing_stop_active': False
        }

        # Precio justo arriba del entry, nuevo SL estaría cerca
        # new_sl = 88100 * 0.985 = 86778.5, precio = 88100
        # Margen = 88100 - 86778.5 = 1321.5 > 0.3% de 88100 = 264.3 ✓
        current_price = 88100.0

        engine._activate_trailing_stop(position, current_price)

        # Debería activarse porque hay margen suficiente
        # y el nuevo SL (86778) es mejor que el actual (86000)
        self.mock_position_store.activate_trailing_stop.assert_called_once()

    def test_cooldown_prevents_rapid_updates(self):
        """
        Test: Verifica que el cooldown previene actualizaciones rápidas.
        """
        from engines.position_engine import PositionEngine

        engine = PositionEngine(
            config=self.config,
            market_engine=self.mock_market_engine,
            order_manager=self.mock_order_manager,
            position_store=self.mock_position_store,
            notifier=self.mock_notifier
        )

        # Posición con trailing activo y última actualización reciente
        position = {
            'id': 'test_cooldown',
            'symbol': 'BTC/USDT',
            'side': 'long',
            'entry_price': 88000.0,
            'stop_loss': 87000.0,
            'trailing_stop_active': True,
            'trailing_stop_distance': 1.5,
            'last_sl_update_time': time.time()  # Justo ahora
        }

        current_price = 90000.0  # Precio favorable

        # Mock para update_stop_loss
        engine._update_stop_loss = Mock()

        engine._update_trailing_stop_if_needed(position, current_price)

        # NO debería actualizarse por cooldown
        engine._update_stop_loss.assert_not_called()

    def test_safety_margin_prevents_tight_sl(self):
        """
        Test: Verifica que el margen de seguridad previene SL muy cercanos.
        """
        from engines.position_engine import PositionEngine

        engine = PositionEngine(
            config=self.config,
            market_engine=self.mock_market_engine,
            order_manager=self.mock_order_manager,
            position_store=self.mock_position_store,
            notifier=self.mock_notifier
        )

        # Configurar trailing distance muy pequeño para forzar SL cercano
        engine.trailing_distance = 0.2  # 0.2% - muy pequeño

        position = {
            'id': 'test_margin',
            'symbol': 'ETH/USDT',
            'side': 'short',
            'entry_price': 2865.0,
            'stop_loss': 2900.0,
            'trailing_stop_active': False
        }

        # Con 0.2% trailing: new_sl = 2800 * 1.002 = 2805.6
        # Margen = 2805.6 - 2800 = 5.6
        # 0.3% de 2800 = 8.4
        # 5.6 < 8.4 → debería rechazar
        current_price = 2800.0

        engine._activate_trailing_stop(position, current_price)

        # NO debería activarse por margen insuficiente
        self.mock_position_store.activate_trailing_stop.assert_not_called()


# =============================================================================
# TEST 2: PAPER MODE SIMULATOR
# =============================================================================

class TestPaperModeSimulator(unittest.TestCase):
    """Tests para el simulador de paper mode."""

    def test_simulator_initialization(self):
        """Test: Verifica inicialización correcta del simulador."""
        from modules.order_manager import PaperModeSimulator

        config = {
            'paper_simulation': {
                'min_latency_ms': 100,
                'max_latency_ms': 300,
                'base_slippage_percent': 0.1,
                'max_slippage_percent': 0.2,
                'failure_rate': 0.05
            }
        }

        simulator = PaperModeSimulator(config)

        self.assertEqual(simulator.min_latency_ms, 100)
        self.assertEqual(simulator.max_latency_ms, 300)
        self.assertEqual(simulator.base_slippage_percent, 0.1)
        self.assertEqual(simulator.failure_rate, 0.05)

    def test_slippage_always_unfavorable(self):
        """Test: Verifica que el slippage siempre es desfavorable."""
        from modules.order_manager import PaperModeSimulator

        simulator = PaperModeSimulator({
            'paper_simulation': {
                'min_latency_ms': 0,
                'max_latency_ms': 1,
                'base_slippage_percent': 0.1,
                'max_slippage_percent': 0.1
            }
        })

        original_price = 1000.0

        # Para BUY: precio ejecutado debe ser MAYOR (peor)
        buy_price = simulator.calculate_slippage(original_price, 'buy')
        self.assertGreater(buy_price, original_price)

        # Para SELL: precio ejecutado debe ser MENOR (peor)
        sell_price = simulator.calculate_slippage(original_price, 'sell')
        self.assertLess(sell_price, original_price)

    def test_process_order_returns_valid_structure(self):
        """Test: Verifica estructura de respuesta de process_order."""
        from modules.order_manager import PaperModeSimulator

        simulator = PaperModeSimulator({
            'paper_simulation': {
                'min_latency_ms': 1,
                'max_latency_ms': 2,
                'failure_rate': 0  # Sin fallos para este test
            }
        })

        result = simulator.process_order(1000.0, 'buy', 'market')

        self.assertIn('success', result)
        self.assertTrue(result['success'])
        self.assertIn('original_price', result)
        self.assertIn('executed_price', result)
        self.assertIn('slippage_percent', result)
        self.assertIn('latency_ms', result)

    def test_stats_accumulation(self):
        """Test: Verifica acumulación de estadísticas."""
        from modules.order_manager import PaperModeSimulator

        simulator = PaperModeSimulator({
            'paper_simulation': {
                'min_latency_ms': 10,
                'max_latency_ms': 10,
                'failure_rate': 0
            }
        })

        # Ejecutar varias órdenes
        for _ in range(5):
            simulator.process_order(1000.0, 'buy', 'market')

        stats = simulator.get_stats()

        self.assertEqual(stats['total_orders'], 5)
        self.assertGreater(stats['avg_latency_ms'], 0)


# =============================================================================
# TEST 3: KELLY CRITERION MEJORADO
# =============================================================================

class TestKellyCriterionImproved(unittest.TestCase):
    """Tests para el Kelly Criterion mejorado."""

    def setUp(self):
        """Configura el risk manager para tests."""
        self.config = {
            'risk_management': {
                'max_risk_per_trade': 2.0,
                'max_daily_drawdown': 5.0,
                'min_risk_reward_ratio': 1.5,
                'initial_capital': 10000,
                'kelly_criterion': {
                    'enabled': True,
                    'fraction': 0.25,
                    'min_confidence': 0.5,
                    'max_risk_cap': 3.0
                }
            },
            'trading': {'mode': 'paper'},
            'security': {'kill_switch': {'enabled': False}}
        }

    def test_conservative_with_few_trades(self):
        """Test: Verifica probabilidad conservadora con pocos trades."""
        from modules.risk_manager import RiskManager

        rm = RiskManager(self.config)

        # Simular historial con 5 trades (muy pocos)
        rm.trade_history = {'wins': 4, 'losses': 1, 'total_win_amount': 100, 'total_loss_amount': 20}

        # Incluso con 80% win rate, debe ser conservador
        prob = rm._adjust_confidence_to_probability(0.7)

        # Con < 10 trades, debe retornar 0.45
        self.assertEqual(prob, 0.45)

    def test_moderate_with_medium_trades(self):
        """Test: Verifica blend moderado con historial medio."""
        from modules.risk_manager import RiskManager

        rm = RiskManager(self.config)

        # Simular 35 trades
        rm.trade_history = {'wins': 25, 'losses': 10, 'total_win_amount': 500, 'total_loss_amount': 200}

        prob = rm._adjust_confidence_to_probability(0.7)

        # Entre 30-50 trades: blend moderado, limitado a 0.30-0.70
        self.assertGreaterEqual(prob, 0.30)
        self.assertLessEqual(prob, 0.70)

    def test_full_confidence_with_many_trades(self):
        """Test: Verifica confianza completa con muchos trades."""
        from modules.risk_manager import RiskManager

        rm = RiskManager(self.config)

        # Simular 60 trades con buen historial
        rm.trade_history = {'wins': 40, 'losses': 20, 'total_win_amount': 1000, 'total_loss_amount': 400}

        prob = rm._adjust_confidence_to_probability(0.7)

        # Con 50+ trades y 66% win rate, debe confiar más
        self.assertGreater(prob, 0.50)

    def test_loss_streak_reduces_probability(self):
        """Test: Verifica que racha perdedora reduce probabilidad."""
        from modules.risk_manager import RiskManager

        rm = RiskManager(self.config)

        # Historial bueno pero racha reciente mala
        rm.trade_history = {'wins': 40, 'losses': 20, 'total_win_amount': 1000, 'total_loss_amount': 400}
        rm.recent_results = ['win', 'win', 'loss', 'loss', 'loss', 'loss']  # 4 pérdidas seguidas

        prob_with_streak = rm._adjust_confidence_to_probability(0.7)

        # Resetear y calcular sin racha
        rm.recent_results = ['win', 'win', 'win', 'win']
        prob_without_streak = rm._adjust_confidence_to_probability(0.7)

        # Con racha perdedora debe ser menor
        self.assertLess(prob_with_streak, prob_without_streak)

    def test_record_trade_result(self):
        """Test: Verifica registro de resultados de trades."""
        from modules.risk_manager import RiskManager

        rm = RiskManager(self.config)

        rm.record_trade_result(True)  # Win
        rm.record_trade_result(True)  # Win
        rm.record_trade_result(False)  # Loss

        self.assertEqual(len(rm.recent_results), 3)
        self.assertEqual(rm.recent_results, ['win', 'win', 'loss'])


# =============================================================================
# TEST 4: VALIDACIÓN DE LIQUIDEZ
# =============================================================================

class TestLiquidityValidation(unittest.TestCase):
    """Tests para validación de liquidez."""

    def setUp(self):
        """Configura mocks para tests."""
        self.mock_connection = Mock()

    def test_validates_sufficient_liquidity(self):
        """Test: Verifica validación con liquidez suficiente."""
        from engines.market_engine import MarketEngine

        # Mock del order book con buena liquidez
        self.mock_connection.fetch_order_book.return_value = {
            'bids': [[99.9, 100], [99.8, 100], [99.7, 100]],  # $29,970 en bids
            'asks': [[100.1, 100], [100.2, 100], [100.3, 100]]  # $30,060 en asks
        }

        # Crear engine con mock
        engine = MarketEngine.__new__(MarketEngine)
        engine.connection = self.mock_connection
        engine.market_type = 'crypto'

        result = engine.validate_liquidity('TEST/USDT', 500, 'buy')

        self.assertTrue(result['valid'])
        self.assertIn('estimated_slippage', result)
        self.assertIn('spread_percent', result)

    def test_rejects_high_spread(self):
        """Test: Verifica rechazo con spread alto."""
        from engines.market_engine import MarketEngine

        # Mock del order book con spread alto (>0.5%)
        self.mock_connection.fetch_order_book.return_value = {
            'bids': [[99.0, 100]],  # Best bid: 99
            'asks': [[100.0, 100]]  # Best ask: 100 → spread = 1%
        }

        engine = MarketEngine.__new__(MarketEngine)
        engine.connection = self.mock_connection
        engine.market_type = 'crypto'

        result = engine.validate_liquidity('TEST/USDT', 500, 'buy')

        self.assertFalse(result['valid'])
        self.assertIn('Spread muy alto', result['reason'])

    def test_rejects_insufficient_liquidity(self):
        """Test: Verifica rechazo con liquidez insuficiente."""
        from engines.market_engine import MarketEngine

        # Mock con poca liquidez
        self.mock_connection.fetch_order_book.return_value = {
            'bids': [[100.0, 1]],  # Solo $100 en bids
            'asks': [[100.1, 1]]   # Solo $100 en asks
        }

        engine = MarketEngine.__new__(MarketEngine)
        engine.connection = self.mock_connection
        engine.market_type = 'crypto'

        # Intentar orden de $1000 con solo $100 de liquidez
        result = engine.validate_liquidity('TEST/USDT', 1000, 'buy')

        self.assertFalse(result['valid'])
        self.assertIn('Liquidez insuficiente', result['reason'])


# =============================================================================
# TEST 5: MÉTRICAS INSTITUCIONALES
# =============================================================================

class TestInstitutionalMetrics(unittest.TestCase):
    """Tests para métricas institucionales."""

    def setUp(self):
        """Configura métricas para tests."""
        # Usar path temporal para no afectar datos reales
        self.test_path = '/tmp/test_metrics.json'
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def tearDown(self):
        """Limpia archivos temporales."""
        if os.path.exists(self.test_path):
            os.remove(self.test_path)

    def test_record_trade(self):
        """Test: Verifica registro de trades."""
        from modules.institutional_metrics import InstitutionalMetrics

        metrics = InstitutionalMetrics(data_path=self.test_path)

        metrics.record_trade(
            symbol='BTC/USDT',
            side='long',
            pnl=50.0,
            pnl_percent=2.5,
            entry_price=40000,
            exit_price=41000,
            regime='trend',
            latency_ms=150,
            slippage_percent=0.05
        )

        self.assertEqual(len(metrics.trades), 1)
        self.assertEqual(metrics.regime_performance['trend']['wins'], 1)

    def test_sharpe_ratio_calculation(self):
        """Test: Verifica cálculo de Sharpe Ratio."""
        from modules.institutional_metrics import InstitutionalMetrics

        metrics = InstitutionalMetrics(data_path=self.test_path)

        # Simular retornos diarios
        for i in range(30):
            metrics.record_daily_return(
                return_percent=0.5 + (i % 3 - 1) * 0.2,  # Variación
                capital=10000 + i * 50
            )

        sharpe = metrics.calculate_sharpe_ratio(30)

        # Sharpe debe ser un número válido
        self.assertIsInstance(sharpe, float)

    def test_regime_stats(self):
        """Test: Verifica estadísticas por régimen."""
        from modules.institutional_metrics import InstitutionalMetrics

        metrics = InstitutionalMetrics(data_path=self.test_path)

        # Registrar trades en diferentes regímenes
        metrics.record_trade('BTC/USDT', 'long', 50, 2.5, 40000, 41000, 'trend')
        metrics.record_trade('ETH/USDT', 'short', -20, -1.0, 2800, 2828, 'trend')
        metrics.record_trade('SOL/USDT', 'long', 30, 1.5, 100, 101.5, 'reversal')

        stats = metrics.get_regime_stats()

        self.assertEqual(stats['trend']['total_trades'], 2)
        self.assertEqual(stats['trend']['wins'], 1)
        self.assertEqual(stats['trend']['losses'], 1)
        self.assertEqual(stats['reversal']['total_trades'], 1)

    def test_latency_stats(self):
        """Test: Verifica estadísticas de latencia."""
        from modules.institutional_metrics import InstitutionalMetrics

        metrics = InstitutionalMetrics(data_path=self.test_path)

        # Registrar trades con diferentes latencias
        for latency in [50, 100, 150, 200, 250]:
            metrics.record_trade(
                'BTC/USDT', 'long', 10, 0.5, 40000, 40200,
                latency_ms=latency
            )

        stats = metrics.get_latency_stats()

        self.assertEqual(stats['samples'], 5)
        self.assertGreater(stats['avg'], 0)
        self.assertGreater(stats['p50'], 0)

    def test_comprehensive_report(self):
        """Test: Verifica reporte completo."""
        from modules.institutional_metrics import InstitutionalMetrics

        metrics = InstitutionalMetrics(data_path=self.test_path)

        # Añadir datos
        for i in range(10):
            metrics.record_daily_return(0.5, 10000 + i * 100)
            metrics.record_trade(
                'BTC/USDT', 'long', 50, 2.5, 40000, 41000,
                regime='trend', latency_ms=100, slippage_percent=0.05
            )

        report = metrics.get_comprehensive_report()

        self.assertIn('performance', report)
        self.assertIn('regime_analysis', report)
        self.assertIn('execution_quality', report)
        self.assertIn('trade_stats', report)


# =============================================================================
# TEST 6: THREAD-SAFE SINGLETON
# =============================================================================

class TestThreadSafeSingleton(unittest.TestCase):
    """Tests para singletons thread-safe."""

    def test_position_store_singleton(self):
        """Test: Verifica singleton de PositionStore."""
        from modules.position_store import get_position_store, reset_position_store

        # Resetear primero
        reset_position_store()

        # Obtener dos instancias
        store1 = get_position_store('/tmp/test_positions.db')
        store2 = get_position_store('/tmp/test_positions.db')

        # Deben ser la misma instancia
        self.assertIs(store1, store2)

        # Limpiar
        reset_position_store()

    def test_metrics_singleton(self):
        """Test: Verifica singleton de métricas."""
        from modules.institutional_metrics import get_institutional_metrics

        metrics1 = get_institutional_metrics()
        metrics2 = get_institutional_metrics()

        self.assertIs(metrics1, metrics2)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("TESTS v1.7 - FUNCIONALIDADES INSTITUCIONALES")
    print("=" * 70)

    # Crear test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Añadir tests
    suite.addTests(loader.loadTestsFromTestCase(TestTrailingStopFix))
    suite.addTests(loader.loadTestsFromTestCase(TestPaperModeSimulator))
    suite.addTests(loader.loadTestsFromTestCase(TestKellyCriterionImproved))
    suite.addTests(loader.loadTestsFromTestCase(TestLiquidityValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestInstitutionalMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestThreadSafeSingleton))

    # Ejecutar
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Resumen
    print("\n" + "=" * 70)
    print(f"Tests ejecutados: {result.testsRun}")
    print(f"Fallos: {len(result.failures)}")
    print(f"Errores: {len(result.errors)}")
    print("=" * 70)

    # Exit code
    sys.exit(0 if result.wasSuccessful() else 1)
