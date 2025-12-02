"""
Adaptive Parameters - Parámetros Adaptativos
==============================================
Sistema que ajusta automáticamente los parámetros del bot basándose
en el rendimiento y condiciones de mercado.

Principio: Los mercados cambian, los parámetros deben adaptarse.

Parámetros que se adaptan:
- min_confidence: Sube si hay muchas pérdidas, baja si hay ganancias consistentes
- trailing_activation: Ajusta según volatilidad del mercado
- max_risk_per_trade: Reduce después de rachas perdedoras
- scan_interval: Reduce en alta volatilidad, aumenta en baja

Autor: Trading Bot System
Versión: 1.7
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveState:
    """Estado actual de los parámetros adaptativos."""
    min_confidence: float = 0.65
    trailing_activation: float = 2.0
    max_risk_per_trade: float = 1.0
    scan_interval: int = 180

    # Métricas de rendimiento
    recent_win_rate: float = 0.50
    recent_avg_pnl: float = 0.0
    current_volatility: str = "medium"
    loss_streak: int = 0
    win_streak: int = 0

    # Timestamps
    last_update: str = ""
    last_trade_result: str = ""  # "win" or "loss"
    last_volatility_change: str = ""  # Timestamp del último cambio de volatilidad


class AdaptiveParameterManager:
    """
    Gestor de parámetros adaptativos.

    Ajusta parámetros del bot basándose en:
    1. Win rate reciente (últimos 20 trades)
    2. Volatilidad actual del mercado
    3. Rachas de ganancias/pérdidas
    4. Drawdown actual
    """

    # Rangos permitidos para cada parámetro
    PARAMETER_RANGES = {
        'min_confidence': {'min': 0.50, 'max': 0.80, 'default': 0.65},
        'trailing_activation': {'min': 1.0, 'max': 4.0, 'default': 2.0},
        'max_risk_per_trade': {'min': 0.5, 'max': 2.0, 'default': 1.0},
        'scan_interval': {'min': 60, 'max': 300, 'default': 180}
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el gestor de parámetros adaptativos.

        Args:
            config: Configuración del bot
        """
        self.config = config
        self._lock = threading.Lock()

        # Configuración adaptativa
        adaptive_config = config.get('adaptive_parameters', {})
        self.enabled = adaptive_config.get('enabled', True)

        # Número de trades para calcular métricas
        self.lookback_trades = adaptive_config.get('lookback_trades', 20)

        # Sensibilidad de ajustes (0.1 = conservador, 0.5 = agresivo)
        self.adjustment_sensitivity = adaptive_config.get('sensitivity', 0.25)

        # Historial de trades recientes
        self.trade_history: List[Dict[str, Any]] = []

        # Estado actual
        self.state = AdaptiveState()

        # Cargar estado persistido
        self._load_state()

        logger.info(f"Adaptive Parameters: enabled={self.enabled}")
        logger.info(f"  Lookback: {self.lookback_trades} trades")
        logger.info(f"  Sensitivity: {self.adjustment_sensitivity}")

    def record_trade_result(
        self,
        symbol: str,
        pnl: float,
        pnl_percent: float,
        hold_time_minutes: int,
        regime: str = "unknown"
    ):
        """
        Registra resultado de un trade y ajusta parámetros.

        Args:
            symbol: Símbolo operado
            pnl: P&L en USD
            pnl_percent: P&L en porcentaje
            hold_time_minutes: Tiempo que estuvo abierta la posición
            regime: Régimen de mercado (trend, reversal, etc.)
        """
        with self._lock:
            is_win = pnl > 0

            # Registrar en historial
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'hold_time_minutes': hold_time_minutes,
                'regime': regime,
                'is_win': is_win
            }
            self.trade_history.append(trade_record)

            # Mantener solo últimos N trades
            if len(self.trade_history) > self.lookback_trades * 2:
                self.trade_history = self.trade_history[-self.lookback_trades:]

            # Actualizar rachas
            if is_win:
                self.state.win_streak += 1
                self.state.loss_streak = 0
                self.state.last_trade_result = "win"
            else:
                self.state.loss_streak += 1
                self.state.win_streak = 0
                self.state.last_trade_result = "loss"

            # Recalcular métricas
            self._update_metrics()

            # Ajustar parámetros
            if self.enabled:
                self._adjust_parameters()

            # Guardar estado
            self._save_state()

            logger.info(f"📊 Adaptive: Trade recorded {'✅ WIN' if is_win else '❌ LOSS'}")
            logger.info(f"   Win streak: {self.state.win_streak} | Loss streak: {self.state.loss_streak}")

    def update_market_volatility(self, volatility_level: str):
        """
        Actualiza la volatilidad actual del mercado con hysteresis para evitar flip-flop.

        Args:
            volatility_level: "low", "medium", "high", "baja", "media", "alta"
        """
        # Normalizar nombres de volatilidad (español → inglés)
        vol_map = {"baja": "low", "media": "medium", "alta": "high"}
        volatility_level = vol_map.get(volatility_level, volatility_level)

        with self._lock:
            old_vol = self.state.current_volatility

            # Hysteresis: No cambiar si el último cambio fue hace menos de 5 minutos
            if self.state.last_volatility_change:
                try:
                    last_change = datetime.fromisoformat(self.state.last_volatility_change)
                    cooldown = timedelta(minutes=5)
                    if datetime.now() - last_change < cooldown:
                        # Silenciosamente ignorar cambios durante el cooldown
                        return
                except ValueError:
                    pass

            # Solo actualizar si hay un cambio real
            if old_vol != volatility_level:
                self.state.current_volatility = volatility_level
                self.state.last_volatility_change = datetime.now().isoformat()

                logger.info(f"📈 Volatilidad cambió: {old_vol} → {volatility_level}")

                if self.enabled:
                    self._adjust_for_volatility()
                    self._save_state()

    def _update_metrics(self):
        """Actualiza métricas basadas en historial reciente."""
        recent_trades = self.trade_history[-self.lookback_trades:]

        if not recent_trades:
            return

        # Win rate
        wins = sum(1 for t in recent_trades if t['is_win'])
        self.state.recent_win_rate = wins / len(recent_trades)

        # Average P&L
        pnls = [t['pnl_percent'] for t in recent_trades]
        self.state.recent_avg_pnl = sum(pnls) / len(pnls)

        self.state.last_update = datetime.now().isoformat()

    def _adjust_parameters(self):
        """Ajusta parámetros basándose en rendimiento."""
        # 1. Ajustar min_confidence basado en win rate
        self._adjust_confidence()

        # 2. Ajustar risk basado en rachas
        self._adjust_risk()

        # 3. Ajustar trailing basado en volatilidad
        self._adjust_for_volatility()

        logger.info(f"🔧 Parámetros ajustados:")
        logger.info(f"   min_confidence: {self.state.min_confidence:.2f}")
        logger.info(f"   max_risk: {self.state.max_risk_per_trade:.2f}%")
        logger.info(f"   trailing_activation: {self.state.trailing_activation:.1f}%")

    def _adjust_confidence(self):
        """Ajusta min_confidence basado en win rate."""
        win_rate = self.state.recent_win_rate
        ranges = self.PARAMETER_RANGES['min_confidence']

        # Si win rate es bajo, aumentar confidence requerida (ser más selectivo)
        # Si win rate es alto, podemos ser menos restrictivos
        if win_rate < 0.40:
            # Win rate muy bajo: ser MUY selectivo
            adjustment = 0.10
        elif win_rate < 0.50:
            # Win rate bajo: ser más selectivo
            adjustment = 0.05
        elif win_rate > 0.60:
            # Win rate alto: podemos relajar un poco
            adjustment = -0.05
        elif win_rate > 0.70:
            # Win rate muy alto: relajar más
            adjustment = -0.08
        else:
            adjustment = 0

        # Aplicar con sensibilidad
        adjustment *= self.adjustment_sensitivity

        new_value = self.state.min_confidence + adjustment
        self.state.min_confidence = max(ranges['min'], min(ranges['max'], new_value))

    def _adjust_risk(self):
        """Ajusta max_risk_per_trade basado en rachas."""
        ranges = self.PARAMETER_RANGES['max_risk_per_trade']

        # Reducir riesgo después de rachas perdedoras
        if self.state.loss_streak >= 3:
            # 3+ pérdidas seguidas: reducir riesgo significativamente
            reduction = 0.3 * self.adjustment_sensitivity
            new_risk = self.state.max_risk_per_trade - reduction
        elif self.state.loss_streak >= 2:
            # 2 pérdidas seguidas: reducir riesgo ligeramente
            reduction = 0.15 * self.adjustment_sensitivity
            new_risk = self.state.max_risk_per_trade - reduction
        elif self.state.win_streak >= 3:
            # 3+ ganancias seguidas: podemos aumentar riesgo gradualmente
            increase = 0.1 * self.adjustment_sensitivity
            new_risk = self.state.max_risk_per_trade + increase
        else:
            # Tender hacia el default
            default = ranges['default']
            current = self.state.max_risk_per_trade
            new_risk = current + (default - current) * 0.1

        self.state.max_risk_per_trade = max(ranges['min'], min(ranges['max'], new_risk))

    def _adjust_for_volatility(self):
        """Ajusta parámetros basados en volatilidad."""
        volatility = self.state.current_volatility
        trailing_ranges = self.PARAMETER_RANGES['trailing_activation']
        scan_ranges = self.PARAMETER_RANGES['scan_interval']

        if volatility == "high":
            # Alta volatilidad: trailing más amplio, escaneo más frecuente
            self.state.trailing_activation = min(
                trailing_ranges['max'],
                trailing_ranges['default'] * 1.5
            )
            self.state.scan_interval = scan_ranges['min']  # Más frecuente

        elif volatility == "low":
            # Baja volatilidad: trailing más ajustado, escaneo menos frecuente
            self.state.trailing_activation = max(
                trailing_ranges['min'],
                trailing_ranges['default'] * 0.75
            )
            self.state.scan_interval = scan_ranges['max']  # Menos frecuente

        else:  # medium
            # Volatilidad normal: usar defaults
            self.state.trailing_activation = trailing_ranges['default']
            self.state.scan_interval = scan_ranges['default']

    def get_current_parameters(self) -> Dict[str, Any]:
        """
        Obtiene los parámetros actuales ajustados.

        Returns:
            Dict con parámetros actuales
        """
        with self._lock:
            return {
                'min_confidence': self.state.min_confidence,
                'trailing_activation': self.state.trailing_activation,
                'max_risk_per_trade': self.state.max_risk_per_trade,
                'scan_interval': self.state.scan_interval,
                'metrics': {
                    'recent_win_rate': self.state.recent_win_rate,
                    'recent_avg_pnl': self.state.recent_avg_pnl,
                    'current_volatility': self.state.current_volatility,
                    'loss_streak': self.state.loss_streak,
                    'win_streak': self.state.win_streak
                },
                'last_update': self.state.last_update
            }

    def get_adjusted_confidence(self) -> float:
        """Obtiene min_confidence ajustado."""
        return self.state.min_confidence

    def get_adjusted_risk(self) -> float:
        """Obtiene max_risk ajustado."""
        return self.state.max_risk_per_trade

    def get_adjusted_trailing(self) -> float:
        """Obtiene trailing_activation ajustado."""
        return self.state.trailing_activation

    def get_adjusted_scan_interval(self) -> int:
        """Obtiene scan_interval ajustado."""
        return self.state.scan_interval

    def _save_state(self):
        """Guarda estado en archivo."""
        state_file = 'data/adaptive_state.json'
        os.makedirs('data', exist_ok=True)

        try:
            data = {
                'state': asdict(self.state),
                'trade_history': self.trade_history[-self.lookback_trades:]
            }
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando estado adaptativo: {e}")

    def _load_state(self):
        """Carga estado desde archivo."""
        state_file = 'data/adaptive_state.json'

        if not os.path.exists(state_file):
            return

        try:
            with open(state_file, 'r') as f:
                data = json.load(f)

            # Restaurar estado
            state_dict = data.get('state', {})
            for key, value in state_dict.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)

            # Restaurar historial
            self.trade_history = data.get('trade_history', [])

            logger.info(f"Estado adaptativo restaurado: {len(self.trade_history)} trades en historial")

        except Exception as e:
            logger.error(f"Error cargando estado adaptativo: {e}")

    def get_status_report(self) -> str:
        """Genera reporte de estado para logs."""
        params = self.get_current_parameters()
        metrics = params['metrics']

        return (
            f"📊 ADAPTIVE STATUS\n"
            f"├─ Win Rate: {metrics['recent_win_rate']:.1%}\n"
            f"├─ Avg P&L: {metrics['recent_avg_pnl']:+.2f}%\n"
            f"├─ Volatility: {metrics['current_volatility']}\n"
            f"├─ Streaks: W{metrics['win_streak']}/L{metrics['loss_streak']}\n"
            f"└─ Params:\n"
            f"   ├─ min_confidence: {params['min_confidence']:.2f}\n"
            f"   ├─ max_risk: {params['max_risk_per_trade']:.2f}%\n"
            f"   └─ trailing: {params['trailing_activation']:.1f}%"
        )


# Singleton
_adaptive_manager = None


def get_adaptive_manager(config: Dict[str, Any] = None) -> Optional[AdaptiveParameterManager]:
    """Obtiene singleton del gestor adaptativo."""
    global _adaptive_manager
    if _adaptive_manager is None and config:
        _adaptive_manager = AdaptiveParameterManager(config)
    return _adaptive_manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = {
        'adaptive_parameters': {
            'enabled': True,
            'lookback_trades': 20,
            'sensitivity': 0.25
        }
    }

    manager = AdaptiveParameterManager(config)

    # Simular trades
    print("\n=== Simulando trades ===\n")

    # 3 pérdidas seguidas
    for i in range(3):
        manager.record_trade_result('BTC/USDT', -10, -1.5, 30, 'trend')
        print(f"Trade {i+1}: LOSS")

    print(f"\nDespués de 3 pérdidas:")
    print(manager.get_status_report())

    # 2 ganancias
    for i in range(2):
        manager.record_trade_result('ETH/USDT', 25, 2.5, 45, 'trend')
        print(f"Trade {4+i}: WIN")

    print(f"\nDespués de recuperación:")
    print(manager.get_status_report())

    # Cambio de volatilidad
    manager.update_market_volatility("high")
    print(f"\nDespués de alta volatilidad:")
    print(manager.get_status_report())
