"""
Risk Manager - Gestor de Riesgo
================================
Este módulo es el "policía" del bot. Valida todas las operaciones
antes de ejecutarlas para proteger el capital y evitar pérdidas catastróficas.

Autor: Trading Bot System
Versión: 1.0
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Gestor de riesgo que valida y controla todas las operaciones de trading.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el gestor de riesgo.

        Args:
            config: Configuración de gestión de riesgo
        """
        self.config = config.get('risk_management', {})
        self.trading_config = config.get('trading', {})

        # Parámetros de riesgo
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 2.0)
        self.max_daily_drawdown = self.config.get('max_daily_drawdown', 5.0)
        self.min_risk_reward_ratio = self.config.get('min_risk_reward_ratio', 1.5)
        self.use_trailing_stop = self.config.get('use_trailing_stop', True)
        self.trailing_stop_percentage = self.config.get('trailing_stop_percentage', 3.0)
        self.initial_capital = self.config.get('initial_capital', 10000)

        # Estado del sistema
        self.current_capital = self.initial_capital
        self.daily_pnl = 0.0
        self.today = datetime.now().date()
        self.open_trades = []
        self.kill_switch_active = False

        # Configuración de kill switch
        self.kill_switch_config = config.get('security', {}).get('kill_switch', {})
        self.kill_switch_enabled = self.kill_switch_config.get('enabled', True)
        self.max_loss_percentage = self.kill_switch_config.get('max_loss_percentage', 5.0)

        # Cargar estado si existe
        self._load_state()

        logger.info(f"Risk Manager inicializado - Capital: ${self.current_capital}")

    def validate_trade(
        self,
        symbol: str,
        decision: str,
        current_price: float,
        suggested_stop_loss: Optional[float] = None,
        suggested_take_profit: Optional[float] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Valida si una operación es segura y permitida.

        Args:
            symbol: Símbolo del activo
            decision: 'COMPRA' o 'VENTA'
            current_price: Precio actual del activo
            suggested_stop_loss: Stop loss sugerido por la IA
            suggested_take_profit: Take profit sugerido
            market_data: Datos adicionales del mercado (volatilidad, etc.)

        Returns:
            Diccionario con validación y parámetros ajustados
        """
        # Resetear daily PnL si es un nuevo día
        self._check_new_day()

        # 1. Verificar kill switch
        if self.kill_switch_active:
            return self._reject_trade(
                "Kill switch activado - Bot en modo seguro",
                symbol
            )

        # 2. Verificar drawdown diario
        if not self._check_daily_drawdown():
            return self._reject_trade(
                f"Drawdown diario excedido ({self.daily_pnl}%)",
                symbol
            )

        # 3. Calcular tamaño de posición
        position_size = self._calculate_position_size(
            current_price,
            suggested_stop_loss
        )

        if position_size <= 0:
            return self._reject_trade(
                "Tamaño de posición inválido",
                symbol
            )

        # 4. Validar stop loss y take profit
        if suggested_stop_loss:
            sl_distance = abs(current_price - suggested_stop_loss) / current_price * 100

            # Stop loss muy cercano (< 0.5%) o muy lejano (> 10%)
            if sl_distance < 0.5 or sl_distance > 10:
                suggested_stop_loss = self._adjust_stop_loss(
                    current_price,
                    decision,
                    market_data
                )
                logger.warning(f"Stop loss ajustado para {symbol}")

        else:
            # Crear stop loss automático
            suggested_stop_loss = self._calculate_automatic_stop_loss(
                current_price,
                decision,
                market_data
            )

        # 5. Validar ratio riesgo/beneficio
        if suggested_take_profit:
            risk_reward = self._calculate_risk_reward(
                current_price,
                suggested_stop_loss,
                suggested_take_profit,
                decision
            )

            if risk_reward < self.min_risk_reward_ratio:
                logger.warning(
                    f"Ratio R/R bajo ({risk_reward:.2f}) para {symbol}. "
                    f"Mínimo requerido: {self.min_risk_reward_ratio}"
                )
                # Opcionalmente rechazar o ajustar
                # return self._reject_trade("Ratio R/R insuficiente", symbol)

        # 6. Verificar volatilidad extrema
        if market_data and 'volatility_level' in market_data:
            if market_data['volatility_level'] == 'alta':
                # Reducir tamaño de posición en mercados volátiles
                position_size *= 0.5
                logger.info(f"Posición reducida 50% por alta volatilidad en {symbol}")

        # Operación aprobada
        return {
            'approved': True,
            'symbol': symbol,
            'decision': decision,
            'position_size': round(position_size, 8),
            'stop_loss': round(suggested_stop_loss, 2),
            'take_profit': round(suggested_take_profit, 2) if suggested_take_profit else None,
            'risk_percentage': self.max_risk_per_trade,
            'message': 'Operación aprobada por Risk Manager'
        }

    def _reject_trade(self, reason: str, symbol: str) -> Dict[str, Any]:
        """Rechaza una operación con una razón."""
        logger.warning(f"Operación RECHAZADA para {symbol}: {reason}")
        return {
            'approved': False,
            'reason': reason,
            'symbol': symbol
        }

    def _calculate_position_size(
        self,
        current_price: float,
        stop_loss: Optional[float]
    ) -> float:
        """
        Calcula el tamaño óptimo de la posición basado en el riesgo permitido.

        Fórmula: Position Size = (Capital * Risk%) / (Entry Price - Stop Loss)

        Args:
            current_price: Precio de entrada
            stop_loss: Precio de stop loss

        Returns:
            Cantidad de activo a operar
        """
        if not stop_loss:
            # Si no hay stop loss, usar un porcentaje fijo del capital
            return (self.current_capital * (self.max_risk_per_trade / 100)) / current_price

        # Calcular riesgo por unidad
        risk_per_unit = abs(current_price - stop_loss)

        # Capital a arriesgar
        capital_at_risk = self.current_capital * (self.max_risk_per_trade / 100)

        # Tamaño de posición
        position_size = capital_at_risk / risk_per_unit

        logger.debug(f"Position size calculado: {position_size:.8f}")
        return position_size

    def _calculate_automatic_stop_loss(
        self,
        current_price: float,
        decision: str,
        market_data: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calcula un stop loss automático basado en ATR o porcentaje fijo.

        Args:
            current_price: Precio actual
            decision: COMPRA o VENTA
            market_data: Datos del mercado con ATR

        Returns:
            Precio de stop loss
        """
        # Intentar usar ATR si está disponible
        if market_data and 'atr' in market_data:
            atr = market_data['atr']
            # Stop loss a 2x ATR
            if decision == 'COMPRA':
                stop_loss = current_price - (2 * atr)
            else:
                stop_loss = current_price + (2 * atr)
        else:
            # Usar porcentaje fijo (3%)
            if decision == 'COMPRA':
                stop_loss = current_price * 0.97
            else:
                stop_loss = current_price * 1.03

        return stop_loss

    def _adjust_stop_loss(
        self,
        current_price: float,
        decision: str,
        market_data: Optional[Dict[str, Any]]
    ) -> float:
        """Ajusta un stop loss que está fuera de rangos aceptables."""
        return self._calculate_automatic_stop_loss(current_price, decision, market_data)

    def _calculate_risk_reward(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        decision: str
    ) -> float:
        """
        Calcula el ratio riesgo/beneficio.

        Args:
            entry_price: Precio de entrada
            stop_loss: Precio de stop loss
            take_profit: Precio de take profit
            decision: COMPRA o VENTA

        Returns:
            Ratio R/R (mayor es mejor)
        """
        if decision == 'COMPRA':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:
            risk = stop_loss - entry_price
            reward = entry_price - take_profit

        if risk <= 0:
            return 0

        return reward / risk

    def _check_daily_drawdown(self) -> bool:
        """
        Verifica si el drawdown diario está dentro de límites.

        Returns:
            True si está dentro de límites, False si excede
        """
        daily_loss_percentage = (self.daily_pnl / self.initial_capital) * 100

        if abs(daily_loss_percentage) >= self.max_daily_drawdown:
            logger.critical(
                f"DRAWDOWN DIARIO EXCEDIDO: {daily_loss_percentage:.2f}% "
                f"(Máximo: {self.max_daily_drawdown}%)"
            )
            self._activate_kill_switch("Drawdown diario excedido")
            return False

        return True

    def _activate_kill_switch(self, reason: str):
        """
        Activa el kill switch - detiene todo trading.

        Args:
            reason: Razón de activación
        """
        self.kill_switch_active = True
        logger.critical(f"🚨 KILL SWITCH ACTIVADO: {reason}")

        # Guardar estado
        self._save_state()

        # TODO: Enviar notificación de emergencia al usuario
        # (Telegram, email, etc.)

    def update_trade_result(self, pnl: float):
        """
        Actualiza el resultado de una operación cerrada.

        Args:
            pnl: Profit and Loss de la operación
        """
        self.daily_pnl += pnl
        self.current_capital += pnl

        logger.info(f"Trade cerrado - PnL: ${pnl:.2f} | Capital actual: ${self.current_capital:.2f}")

        # Verificar si se debe activar kill switch
        total_loss_percentage = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100

        if self.kill_switch_enabled and total_loss_percentage <= -self.max_loss_percentage:
            self._activate_kill_switch(
                f"Pérdida total excede {self.max_loss_percentage}%"
            )

        self._save_state()

    def _check_new_day(self):
        """Resetea el PnL diario si es un nuevo día."""
        current_date = datetime.now().date()
        if current_date != self.today:
            logger.info(f"Nuevo día - PnL del día anterior: ${self.daily_pnl:.2f}")
            self.daily_pnl = 0.0
            self.today = current_date

            # Desactivar kill switch si ha pasado el período de cooldown
            if self.kill_switch_active:
                logger.info("Desactivando kill switch - Nuevo día")
                self.kill_switch_active = False

            self._save_state()

    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        decision: str,
        initial_stop_loss: float
    ) -> float:
        """
        Calcula el trailing stop dinámico.

        Args:
            entry_price: Precio de entrada
            current_price: Precio actual
            decision: COMPRA o VENTA
            initial_stop_loss: Stop loss inicial

        Returns:
            Nuevo precio de stop loss
        """
        if not self.use_trailing_stop:
            return initial_stop_loss

        if decision == 'COMPRA':
            # Si el precio ha subido, subir el stop loss
            if current_price > entry_price:
                new_stop = current_price * (1 - self.trailing_stop_percentage / 100)
                return max(new_stop, initial_stop_loss)
            return initial_stop_loss

        else:  # VENTA
            # Si el precio ha bajado, bajar el stop loss
            if current_price < entry_price:
                new_stop = current_price * (1 + self.trailing_stop_percentage / 100)
                return min(new_stop, initial_stop_loss)
            return initial_stop_loss

    def _save_state(self):
        """Guarda el estado del risk manager."""
        state = {
            'current_capital': self.current_capital,
            'daily_pnl': self.daily_pnl,
            'today': str(self.today),
            'kill_switch_active': self.kill_switch_active,
            'open_trades': self.open_trades
        }

        state_file = 'data/risk_manager_state.json'
        os.makedirs('data', exist_ok=True)

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.debug("Estado del risk manager guardado")
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")

    def _load_state(self):
        """Carga el estado del risk manager si existe."""
        state_file = 'data/risk_manager_state.json'

        if not os.path.exists(state_file):
            logger.info("No se encontró estado previo - Usando valores por defecto")
            return

        try:
            with open(state_file, 'r') as f:
                state = json.load(f)

            self.current_capital = state.get('current_capital', self.initial_capital)
            self.daily_pnl = state.get('daily_pnl', 0.0)
            self.kill_switch_active = state.get('kill_switch_active', False)
            self.open_trades = state.get('open_trades', [])

            # Verificar si es un nuevo día
            saved_date = datetime.strptime(state.get('today', str(self.today)), '%Y-%m-%d').date()
            if saved_date != self.today:
                self.daily_pnl = 0.0
                self.kill_switch_active = False

            logger.info(f"Estado cargado - Capital: ${self.current_capital:.2f}")

        except Exception as e:
            logger.error(f"Error cargando estado: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del risk manager.

        Returns:
            Diccionario con métricas de riesgo
        """
        total_pnl = self.current_capital - self.initial_capital
        total_pnl_percentage = (total_pnl / self.initial_capital) * 100

        return {
            'initial_capital': self.initial_capital,
            'current_capital': round(self.current_capital, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_percentage': round(total_pnl_percentage, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'kill_switch_active': self.kill_switch_active,
            'open_trades_count': len(self.open_trades),
            'risk_per_trade': self.max_risk_per_trade,
            'max_daily_drawdown': self.max_daily_drawdown
        }


if __name__ == "__main__":
    # Prueba básica del módulo
    logging.basicConfig(level=logging.INFO)

    test_config = {
        'risk_management': {
            'max_risk_per_trade': 2.0,
            'max_daily_drawdown': 5.0,
            'min_risk_reward_ratio': 1.5,
            'use_trailing_stop': True,
            'trailing_stop_percentage': 3.0,
            'initial_capital': 10000
        },
        'trading': {'mode': 'paper'},
        'security': {
            'kill_switch': {
                'enabled': True,
                'max_loss_percentage': 5.0
            }
        }
    }

    risk_manager = RiskManager(test_config)

    # Simular validación de operación
    validation = risk_manager.validate_trade(
        symbol='BTC/USDT',
        decision='COMPRA',
        current_price=45000,
        suggested_stop_loss=43500,
        suggested_take_profit=48000,
        market_data={'atr': 500, 'volatility_level': 'media'}
    )

    print("\n=== VALIDACIÓN DE OPERACIÓN ===")
    print(json.dumps(validation, indent=2))

    print("\n=== ESTADO DEL RISK MANAGER ===")
    print(json.dumps(risk_manager.get_status(), indent=2))
