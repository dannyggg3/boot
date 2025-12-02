"""
Institutional Metrics - Métricas de nivel institucional
========================================================
Proporciona métricas avanzadas para trading profesional:
- Sharpe Ratio
- Sortino Ratio
- Max Drawdown
- Calmar Ratio
- Win Rate por régimen
- Tracking de latencia y slippage

Autor: Trading Bot System
Versión: 1.7
"""

import logging
import math
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque
import threading

logger = logging.getLogger(__name__)


class InstitutionalMetrics:
    """
    Calcula y mantiene métricas de nivel institucional.
    Thread-safe y persistente.
    """

    def __init__(self, config: Dict[str, Any] = None, data_path: str = "data/metrics.json"):
        self.config = config or {}
        self.data_path = data_path
        self._lock = threading.Lock()

        # Parámetros
        self.risk_free_rate = self.config.get('risk_free_rate', 0.05)  # 5% anual
        self.trading_days_per_year = self.config.get('trading_days_per_year', 365)  # Crypto = 365

        # Almacenamiento de datos
        self.daily_returns: deque = deque(maxlen=365)  # Últimos 365 días
        self.trades: List[Dict] = []
        self.latency_samples: deque = deque(maxlen=1000)
        self.slippage_samples: deque = deque(maxlen=1000)

        # Tracking por régimen
        self.regime_performance = {
            'trend': {'wins': 0, 'losses': 0, 'total_pnl': 0},
            'reversal': {'wins': 0, 'losses': 0, 'total_pnl': 0},
            'range': {'wins': 0, 'losses': 0, 'total_pnl': 0}
        }

        # v1.7: Fill Rate tracking
        self.limit_orders_placed = 0
        self.limit_orders_filled = 0
        self.limit_orders_cancelled = 0
        self.limit_orders_timeout = 0

        # v1.7: Umbrales de alerta
        self.slippage_alert_threshold = self.config.get('slippage_alert_threshold', 0.3)  # 0.3%

        # Peak para drawdown
        self.peak_capital = 0
        self.current_capital = 0
        self.max_drawdown = 0
        self.max_drawdown_duration_days = 0
        self.drawdown_start_date = None

        # Cargar datos persistidos
        self._load_data()

        logger.info("InstitutionalMetrics v1.7 inicializado")

    def record_trade(
        self,
        symbol: str,
        side: str,
        pnl: float,
        pnl_percent: float,
        entry_price: float,
        exit_price: float,
        regime: str = 'unknown',
        agent_type: str = 'general',
        hold_time_minutes: int = 0,
        latency_ms: float = 0,
        slippage_percent: float = 0
    ):
        """
        Registra un trade completado para cálculo de métricas.

        Args:
            symbol: Par de trading
            side: 'long' o 'short'
            pnl: P&L en USD
            pnl_percent: P&L en porcentaje
            entry_price: Precio de entrada
            exit_price: Precio de salida
            regime: Régimen de mercado ('trend', 'reversal', 'range')
            agent_type: Tipo de agente que tomó la decisión
            hold_time_minutes: Tiempo en posición
            latency_ms: Latencia de ejecución
            slippage_percent: Slippage experimentado
        """
        with self._lock:
            trade = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': side,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'regime': regime,
                'agent_type': agent_type,
                'hold_time_minutes': hold_time_minutes,
                'latency_ms': latency_ms,
                'slippage_percent': slippage_percent
            }
            self.trades.append(trade)

            # Actualizar tracking por régimen
            if regime in self.regime_performance:
                if pnl > 0:
                    self.regime_performance[regime]['wins'] += 1
                else:
                    self.regime_performance[regime]['losses'] += 1
                self.regime_performance[regime]['total_pnl'] += pnl

            # Registrar samples de latencia y slippage
            if latency_ms > 0:
                self.latency_samples.append(latency_ms)
            if slippage_percent > 0:
                self.slippage_samples.append(slippage_percent)
                # v1.7: Alerta si slippage excede umbral
                if slippage_percent > self.slippage_alert_threshold:
                    logger.warning(
                        f"⚠️ SLIPPAGE ALTO: {slippage_percent:.3f}% en {symbol} "
                        f"(umbral: {self.slippage_alert_threshold}%)"
                    )

            # Persistir
            self._save_data()

    def record_limit_order(self, status: str, symbol: str = "", order_type: str = ""):
        """
        Registra el resultado de una orden limit para cálculo de Fill Rate.

        Args:
            status: 'placed', 'filled', 'cancelled', 'timeout'
            symbol: Par de trading
            order_type: Tipo de orden ('entry', 'tp', 'sl')
        """
        with self._lock:
            if status == 'placed':
                self.limit_orders_placed += 1
            elif status == 'filled':
                self.limit_orders_filled += 1
            elif status == 'cancelled':
                self.limit_orders_cancelled += 1
            elif status == 'timeout':
                self.limit_orders_timeout += 1
                logger.info(f"📊 Limit order timeout: {symbol} ({order_type})")

            # Guardar cada 10 órdenes
            if self.limit_orders_placed % 10 == 0:
                self._save_data()

    def get_fill_rate_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de Fill Rate.

        Returns:
            Dict con métricas de fill rate
        """
        with self._lock:
            total = self.limit_orders_placed
            if total == 0:
                return {
                    'fill_rate_percent': 0,
                    'total_placed': 0,
                    'filled': 0,
                    'cancelled': 0,
                    'timeout': 0
                }

            return {
                'fill_rate_percent': round(self.limit_orders_filled / total * 100, 1),
                'total_placed': total,
                'filled': self.limit_orders_filled,
                'cancelled': self.limit_orders_cancelled,
                'timeout': self.limit_orders_timeout,
                'cancel_rate_percent': round(self.limit_orders_cancelled / total * 100, 1),
                'timeout_rate_percent': round(self.limit_orders_timeout / total * 100, 1)
            }

    def record_daily_return(self, return_percent: float, capital: float):
        """
        Registra el retorno diario para cálculo de Sharpe.

        Args:
            return_percent: Retorno del día en porcentaje
            capital: Capital al final del día
        """
        with self._lock:
            self.daily_returns.append({
                'date': datetime.now().date().isoformat(),
                'return_percent': return_percent,
                'capital': capital
            })

            # Actualizar peak y drawdown
            self.current_capital = capital
            if capital > self.peak_capital:
                self.peak_capital = capital
                self.drawdown_start_date = None
            else:
                # Calcular drawdown actual
                current_drawdown = (self.peak_capital - capital) / self.peak_capital * 100
                if current_drawdown > self.max_drawdown:
                    self.max_drawdown = current_drawdown

                # Tracking de duración
                if self.drawdown_start_date is None:
                    self.drawdown_start_date = datetime.now()
                else:
                    duration = (datetime.now() - self.drawdown_start_date).days
                    if duration > self.max_drawdown_duration_days:
                        self.max_drawdown_duration_days = duration

            self._save_data()

    def calculate_sharpe_ratio(self, period_days: int = 30) -> float:
        """
        Calcula el Sharpe Ratio.

        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns

        Args:
            period_days: Días a considerar

        Returns:
            Sharpe Ratio anualizado
        """
        with self._lock:
            if len(self.daily_returns) < 5:
                return 0.0

            # Obtener retornos del período
            returns = [r['return_percent'] for r in list(self.daily_returns)[-period_days:]]

            if len(returns) < 2:
                return 0.0

            # Calcular media y desviación estándar
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance) if variance > 0 else 0.001

            # Risk free rate diario
            daily_rf = self.risk_free_rate / self.trading_days_per_year

            # Sharpe diario
            daily_sharpe = (mean_return - daily_rf) / std_dev

            # Anualizar
            annualized_sharpe = daily_sharpe * math.sqrt(self.trading_days_per_year)

            return round(annualized_sharpe, 2)

    def calculate_sortino_ratio(self, period_days: int = 30) -> float:
        """
        Calcula el Sortino Ratio (solo considera downside volatility).

        Args:
            period_days: Días a considerar

        Returns:
            Sortino Ratio anualizado
        """
        with self._lock:
            if len(self.daily_returns) < 5:
                return 0.0

            returns = [r['return_percent'] for r in list(self.daily_returns)[-period_days:]]

            if len(returns) < 2:
                return 0.0

            mean_return = sum(returns) / len(returns)
            daily_rf = self.risk_free_rate / self.trading_days_per_year

            # Solo retornos negativos para downside deviation
            negative_returns = [r for r in returns if r < daily_rf]

            if len(negative_returns) < 2:
                return float('inf') if mean_return > daily_rf else 0.0

            downside_variance = sum((r - daily_rf) ** 2 for r in negative_returns) / len(negative_returns)
            downside_dev = math.sqrt(downside_variance) if downside_variance > 0 else 0.001

            daily_sortino = (mean_return - daily_rf) / downside_dev
            annualized_sortino = daily_sortino * math.sqrt(self.trading_days_per_year)

            return round(annualized_sortino, 2)

    def calculate_calmar_ratio(self) -> float:
        """
        Calcula el Calmar Ratio (CAGR / Max Drawdown).

        Returns:
            Calmar Ratio
        """
        with self._lock:
            if self.max_drawdown <= 0 or len(self.daily_returns) < 30:
                return 0.0

            # Calcular CAGR aproximado
            returns = [r['return_percent'] for r in self.daily_returns]
            total_return = sum(returns)
            days = len(returns)

            if days < 1:
                return 0.0

            # Anualizar retorno
            annual_return = (total_return / days) * self.trading_days_per_year

            calmar = annual_return / self.max_drawdown

            return round(calmar, 2)

    def get_regime_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas por régimen de mercado.

        Returns:
            Dict con stats por régimen
        """
        with self._lock:
            stats = {}
            for regime, data in self.regime_performance.items():
                total = data['wins'] + data['losses']
                stats[regime] = {
                    'total_trades': total,
                    'wins': data['wins'],
                    'losses': data['losses'],
                    'win_rate': round(data['wins'] / total * 100, 1) if total > 0 else 0,
                    'total_pnl': round(data['total_pnl'], 2),
                    'avg_pnl': round(data['total_pnl'] / total, 2) if total > 0 else 0
                }
            return stats

    def get_latency_stats(self) -> Dict[str, float]:
        """
        Obtiene estadísticas de latencia.

        Returns:
            Dict con P50, P95, P99 de latencia
        """
        with self._lock:
            if not self.latency_samples:
                return {'p50': 0, 'p95': 0, 'p99': 0, 'avg': 0}

            samples = sorted(self.latency_samples)
            n = len(samples)

            return {
                'p50': samples[int(n * 0.50)],
                'p95': samples[int(n * 0.95)] if n >= 20 else samples[-1],
                'p99': samples[int(n * 0.99)] if n >= 100 else samples[-1],
                'avg': round(sum(samples) / n, 2),
                'samples': n
            }

    def get_slippage_stats(self) -> Dict[str, float]:
        """
        Obtiene estadísticas de slippage.

        Returns:
            Dict con estadísticas de slippage
        """
        with self._lock:
            if not self.slippage_samples:
                return {'avg': 0, 'max': 0, 'total_cost_percent': 0}

            samples = list(self.slippage_samples)

            return {
                'avg': round(sum(samples) / len(samples), 4),
                'max': round(max(samples), 4),
                'min': round(min(samples), 4),
                'total_cost_percent': round(sum(samples), 4),
                'samples': len(samples)
            }

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """
        Genera reporte completo de métricas institucionales.

        Returns:
            Dict con todas las métricas
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'performance': {
                'sharpe_ratio_30d': self.calculate_sharpe_ratio(30),
                'sharpe_ratio_90d': self.calculate_sharpe_ratio(90),
                'sortino_ratio_30d': self.calculate_sortino_ratio(30),
                'calmar_ratio': self.calculate_calmar_ratio(),
                'max_drawdown_percent': round(self.max_drawdown, 2),
                'max_drawdown_duration_days': self.max_drawdown_duration_days,
                'current_capital': self.current_capital,
                'peak_capital': self.peak_capital
            },
            'regime_analysis': self.get_regime_stats(),
            'execution_quality': {
                'latency': self.get_latency_stats(),
                'slippage': self.get_slippage_stats(),
                'fill_rate': self.get_fill_rate_stats()
            },
            'trade_stats': {
                'total_trades': len(self.trades),
                'total_pnl': round(sum(t['pnl'] for t in self.trades), 2),
                'avg_hold_time_minutes': round(
                    sum(t['hold_time_minutes'] for t in self.trades) / len(self.trades), 1
                ) if self.trades else 0
            }
        }

    def log_periodic_report(self, interval_name: str = "", data_logger=None):
        """
        Imprime un reporte resumido de métricas en el log.
        Diseñado para ser llamado periódicamente (ej: cada hora).
        Opcionalmente envía las métricas a InfluxDB.

        Args:
            interval_name: Nombre del intervalo (ej: "1H", "4H", "Daily")
            data_logger: Instancia de DataLogger para enviar a InfluxDB
        """
        report = self.get_comprehensive_report()
        perf = report['performance']
        regime = report['regime_analysis']
        exec_q = report['execution_quality']

        # v1.7: Enviar a InfluxDB si está disponible
        if data_logger:
            try:
                # Métricas de performance
                data_logger.log_institutional_metrics(
                    sharpe_ratio=perf['sharpe_ratio_30d'],
                    sortino_ratio=perf['sortino_ratio_30d'],
                    calmar_ratio=perf['calmar_ratio'],
                    max_drawdown=perf['max_drawdown_percent'],
                    current_capital=perf['current_capital'],
                    peak_capital=perf['peak_capital']
                )

                # Métricas de ejecución
                latency = exec_q['latency']
                slippage = exec_q['slippage']
                fill_rate = exec_q['fill_rate']

                data_logger.log_execution_quality(
                    latency_p50=latency.get('p50', 0),
                    latency_p95=latency.get('p95', 0),
                    latency_p99=latency.get('p99', 0),
                    slippage_avg=slippage.get('avg', 0),
                    slippage_max=slippage.get('max', 0),
                    fill_rate=fill_rate.get('fill_rate_percent', 0)
                )

                # Performance por régimen
                for regime_name, stats in regime.items():
                    if stats['total_trades'] > 0:
                        data_logger.log_regime_performance(
                            regime=regime_name,
                            win_rate=stats['win_rate'],
                            total_trades=stats['total_trades'],
                            total_pnl=stats['total_pnl']
                        )

                logger.debug("Métricas enviadas a InfluxDB")

            except Exception as e:
                logger.error(f"Error enviando métricas a InfluxDB: {e}")

        # Header
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"📊 MÉTRICAS INSTITUCIONALES {interval_name}")
        logger.info(f"{'='*60}")

        # Performance
        logger.info(f"📈 Performance:")
        logger.info(f"   Sharpe (30d): {perf['sharpe_ratio_30d']:.2f} | Sortino: {perf['sortino_ratio_30d']:.2f}")
        logger.info(f"   Calmar: {perf['calmar_ratio']:.2f} | Max DD: {perf['max_drawdown_percent']:.1f}%")
        logger.info(f"   Capital: ${perf['current_capital']:.2f} (Peak: ${perf['peak_capital']:.2f})")

        # Win Rate por Régimen
        logger.info(f"📊 Win Rate por Régimen:")
        for reg_name, stats in regime.items():
            if stats['total_trades'] > 0:
                logger.info(f"   {reg_name.capitalize()}: {stats['win_rate']:.1f}% ({stats['wins']}/{stats['total_trades']}) | PnL: ${stats['total_pnl']:.2f}")

        # Calidad de Ejecución
        latency = exec_q['latency']
        slippage = exec_q['slippage']
        fill_rate = exec_q['fill_rate']

        logger.info(f"⚡ Ejecución:")
        if latency['samples'] > 0:
            logger.info(f"   Latencia: P50={latency['p50']:.0f}ms | P95={latency['p95']:.0f}ms | P99={latency['p99']:.0f}ms")
        if slippage['samples'] > 0:
            logger.info(f"   Slippage: Avg={slippage['avg']:.3f}% | Max={slippage['max']:.3f}%")
        if fill_rate['total_placed'] > 0:
            logger.info(f"   Fill Rate: {fill_rate['fill_rate_percent']:.1f}% ({fill_rate['filled']}/{fill_rate['total_placed']})")

        logger.info(f"{'='*60}")
        logger.info(f"")

    def _save_data(self):
        """Persiste los datos de métricas."""
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)

            data = {
                'daily_returns': list(self.daily_returns),
                'trades': self.trades[-1000:],  # Últimos 1000 trades
                'regime_performance': self.regime_performance,
                'peak_capital': self.peak_capital,
                'current_capital': self.current_capital,
                'max_drawdown': self.max_drawdown,
                'max_drawdown_duration_days': self.max_drawdown_duration_days,
                # v1.7: Fill rate data
                'limit_orders_placed': self.limit_orders_placed,
                'limit_orders_filled': self.limit_orders_filled,
                'limit_orders_cancelled': self.limit_orders_cancelled,
                'limit_orders_timeout': self.limit_orders_timeout
            }

            with open(self.data_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error guardando métricas: {e}")

    def _load_data(self):
        """Carga datos de métricas persistidos."""
        if not os.path.exists(self.data_path):
            return

        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)

            self.daily_returns = deque(data.get('daily_returns', []), maxlen=365)
            self.trades = data.get('trades', [])
            self.regime_performance = data.get('regime_performance', self.regime_performance)
            self.peak_capital = data.get('peak_capital', 0)
            self.current_capital = data.get('current_capital', 0)
            self.max_drawdown = data.get('max_drawdown', 0)
            self.max_drawdown_duration_days = data.get('max_drawdown_duration_days', 0)

            # v1.7: Fill rate data
            self.limit_orders_placed = data.get('limit_orders_placed', 0)
            self.limit_orders_filled = data.get('limit_orders_filled', 0)
            self.limit_orders_cancelled = data.get('limit_orders_cancelled', 0)
            self.limit_orders_timeout = data.get('limit_orders_timeout', 0)

            logger.info(f"Métricas cargadas: {len(self.trades)} trades, {len(self.daily_returns)} días")

        except Exception as e:
            logger.error(f"Error cargando métricas: {e}")


# =============================================================================
# SINGLETON
# =============================================================================

_metrics_instance: Optional[InstitutionalMetrics] = None
_metrics_lock = threading.Lock()


def get_institutional_metrics(config: Dict = None) -> InstitutionalMetrics:
    """Obtiene instancia singleton de métricas institucionales."""
    global _metrics_instance

    if _metrics_instance is not None:
        return _metrics_instance

    with _metrics_lock:
        if _metrics_instance is None:
            _metrics_instance = InstitutionalMetrics(config)

    return _metrics_instance
