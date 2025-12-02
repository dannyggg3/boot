"""
Risk Manager - Gestor de Riesgo
================================
Este módulo es el "policía" del bot. Valida todas las operaciones
antes de ejecutarlas para proteger el capital y evitar pérdidas catastróficas.

v1.6: Incluye validación de comisiones para asegurar rentabilidad.
v1.7: Kelly Criterion mejorado para ser más conservador con historial limitado.
      - Requiere mínimo 50 trades para confiar en Kelly
      - Tracking de rachas perdedoras
      - Factor de seguridad dinámico

Autor: Trading Bot System
Versión: 1.7
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
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

        # Kelly Criterion para sizing dinámico (v1.3)
        kelly_config = self.config.get('kelly_criterion', {})
        self.use_kelly_criterion = kelly_config.get('enabled', True)
        self.kelly_fraction = kelly_config.get('fraction', 0.25)  # Fracción de Kelly (conservador)
        self.min_confidence_to_trade = kelly_config.get('min_confidence', 0.5)
        self.max_kelly_risk = kelly_config.get('max_risk_cap', 3.0)  # Riesgo máximo con Kelly

        # v1.6: Configuración de comisiones y tamaños mínimos
        fees_config = self.config.get('fees', {})
        self.maker_fee_percent = fees_config.get('maker_fee_percent', 0.10)
        self.taker_fee_percent = fees_config.get('taker_fee_percent', 0.10)
        self.round_trip_fee_percent = self.maker_fee_percent + self.taker_fee_percent

        sizing_config = self.config.get('position_sizing', {})
        self.min_position_usd = sizing_config.get('min_position_usd', 15.0)
        self.min_profit_after_fees = sizing_config.get('min_profit_after_fees_usd', 0.50)
        self.profit_to_fees_ratio = sizing_config.get('profit_to_fees_ratio', 5.0)

        # Mínimos del exchange
        self.exchange_minimums = self.config.get('exchange_minimums', {
            'BTC_USDT': 5.0,
            'ETH_USDT': 5.0,
            'SOL_USDT': 5.0,
            'default': 10.0
        })

        logger.info(f"v1.6: Fees configuradas - Round-trip: {self.round_trip_fee_percent}%")

        # Historial para cálculo de Kelly
        self.trade_history = {
            'wins': 0,
            'losses': 0,
            'total_win_amount': 0.0,
            'total_loss_amount': 0.0
        }

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
        market_data: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5,
        available_balance: Optional[float] = None
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
            confidence: Nivel de confianza de la IA (0-1) para Kelly Criterion
            available_balance: v1.5 - Balance real disponible (USDT para compra, activo para venta)

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

        # 3. Calcular tamaño de posición (Kelly Criterion si está habilitado)
        # v1.5: Usar balance real si se proporciona
        effective_capital = available_balance if available_balance is not None else self.current_capital

        # v1.5: Para VENTA, el balance es en unidades del activo, convertir a USD para Kelly
        if decision == 'VENTA' and available_balance is not None:
            effective_capital_usd = available_balance * current_price
            logger.info(f"v1.5: VENTA - Balance activo: {available_balance:.6f} = ${effective_capital_usd:.2f}")
        else:
            effective_capital_usd = effective_capital
            if available_balance is not None:
                logger.info(f"v1.5: COMPRA - Balance USDT: ${effective_capital_usd:.2f}")

        if self.use_kelly_criterion and confidence >= self.min_confidence_to_trade:
            position_size = self.calculate_kelly_position_size(
                confidence=confidence,
                current_price=current_price,
                stop_loss=suggested_stop_loss,
                capital_override=effective_capital_usd  # v1.5: Usar capital real
            )
            logger.info(f"Kelly Sizing: confianza={confidence:.2f}, risk={self.get_dynamic_risk_percentage(confidence):.1f}%")
        else:
            position_size = self._calculate_position_size(
                current_price,
                suggested_stop_loss,
                capital_override=effective_capital_usd  # v1.5: Usar capital real
            )

        # v1.5: Para VENTA, limitar al balance disponible del activo
        if decision == 'VENTA' and available_balance is not None:
            if position_size > available_balance:
                logger.info(f"v1.5: Ajustando position_size de {position_size:.6f} a {available_balance:.6f} (balance máximo)")
                position_size = available_balance

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
                # v1.7 FIX CRÍTICO: RECHAZAR trades con mal R/R (antes solo warning)
                # Un trade con R/R < 1.5 tiene expectativa matemática negativa a largo plazo
                logger.warning(
                    f"Ratio R/R bajo ({risk_reward:.2f}) para {symbol}. "
                    f"Mínimo requerido: {self.min_risk_reward_ratio}"
                )
                return self._reject_trade(
                    f"Ratio R/R insuficiente ({risk_reward:.2f} < {self.min_risk_reward_ratio})",
                    symbol
                )

        # 6. Verificar volatilidad extrema
        if market_data and 'volatility_level' in market_data:
            if market_data['volatility_level'] == 'alta':
                # Reducir tamaño de posición en mercados volátiles
                position_size *= 0.5
                logger.info(f"Posición reducida 50% por alta volatilidad en {symbol}")

        # 7. v1.6: Validar rentabilidad después de comisiones
        if suggested_take_profit and current_price > 0:
            position_value_usd = position_size * current_price
            expected_profit_percent = abs(suggested_take_profit - current_price) / current_price * 100

            profitability_check = self.validate_trade_profitability(
                symbol=symbol,
                position_value_usd=position_value_usd,
                expected_profit_percent=expected_profit_percent
            )

            if not profitability_check['valid']:
                return self._reject_trade(
                    f"v1.6 Fee Check: {profitability_check['reason']}",
                    symbol
                )

            logger.info(f"v1.6 Fee Check OK: Ganancia neta ${profitability_check['net_profit_usd']:.2f} "
                       f"(después de ${profitability_check['total_fees_usd']:.2f} en fees)")

        # Operación aprobada
        return {
            'approved': True,
            'symbol': symbol,
            'decision': decision,
            'position_size': round(position_size, 8),
            'stop_loss': round(suggested_stop_loss, 2),
            'take_profit': round(suggested_take_profit, 2) if suggested_take_profit else None,
            'risk_percentage': self.max_risk_per_trade,
            'confidence': confidence,  # v1.5: Para notificaciones
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
        stop_loss: Optional[float],
        capital_override: Optional[float] = None
    ) -> float:
        """
        Calcula el tamaño óptimo de la posición basado en el riesgo permitido.

        Fórmula: Position Size = (Capital * Risk%) / (Entry Price - Stop Loss)

        Args:
            current_price: Precio de entrada
            stop_loss: Precio de stop loss
            capital_override: v1.5 - Capital real a usar (en lugar de self.current_capital)

        Returns:
            Cantidad de activo a operar
        """
        # v1.5: Usar capital real si se proporciona
        capital = capital_override if capital_override is not None else self.current_capital

        if not stop_loss:
            # Si no hay stop loss, usar un porcentaje fijo del capital
            return (capital * (self.max_risk_per_trade / 100)) / current_price

        # Calcular riesgo por unidad
        risk_per_unit = abs(current_price - stop_loss)

        # Capital a arriesgar
        capital_at_risk = capital * (self.max_risk_per_trade / 100)

        # Tamaño de posición
        position_size = capital_at_risk / risk_per_unit

        logger.debug(f"Position size calculado: {position_size:.8f} (capital: ${capital:.2f})")
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

        # v1.4: Enviar notificación de emergencia
        try:
            from modules.notifications import get_notification_manager
            notifier = get_notification_manager()
            if notifier:
                loss_percent = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
                notifier.notify_kill_switch(
                    reason=reason,
                    capital=self.current_capital,
                    loss_percent=abs(loss_percent)
                )
        except Exception as e:
            logger.error(f"Error enviando notificación kill switch: {e}")

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
            'open_trades': self.open_trades,
            'trade_history': self.trade_history  # v1.4: Persistir historial para Kelly
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
            # v1.4: Cargar historial para Kelly Criterion
            self.trade_history = state.get('trade_history', {
                'wins': 0,
                'losses': 0,
                'total_win_amount': 0.0,
                'total_loss_amount': 0.0
            })

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
            'max_daily_drawdown': self.max_daily_drawdown,
            'kelly_criterion': self.use_kelly_criterion,
            'win_rate': self._get_win_rate()
        }

    # ==================== KELLY CRITERION ====================

    def calculate_kelly_position_size(
        self,
        confidence: float,
        current_price: float,
        stop_loss: Optional[float] = None,
        expected_rr: float = 2.0,
        capital_override: Optional[float] = None
    ) -> float:
        """
        Calcula el tamaño de posición usando Kelly Criterion ajustado por confianza.

        Kelly Formula: f* = (bp - q) / b
        Donde:
            f* = fracción óptima del capital a apostar
            b = ratio ganancia/pérdida (odds)
            p = probabilidad de ganar
            q = probabilidad de perder (1-p)

        Args:
            confidence: Confianza de la IA (0-1), usado como proxy de probabilidad
            current_price: Precio actual
            stop_loss: Precio de stop loss
            expected_rr: Ratio riesgo/recompensa esperado
            capital_override: v1.5 - Capital real a usar (en lugar de self.current_capital)

        Returns:
            Tamaño de posición óptimo
        """
        # v1.7.1 FIX: Verificar confianza ORIGINAL antes del ajuste
        # La confianza ajustada solo se usa para el cálculo de Kelly, no para el filtro
        if confidence < self.min_confidence_to_trade:
            logger.info(f"Confianza original {confidence:.2f} menor al mínimo {self.min_confidence_to_trade}")
            return 0.0

        # Usar confianza como probabilidad de éxito (ajustada por historial)
        win_probability = self._adjust_confidence_to_probability(confidence)

        # Calcular Kelly
        b = expected_rr  # Ratio ganancia/pérdida
        p = win_probability
        q = 1 - p

        # Fórmula de Kelly
        kelly_fraction_raw = (b * p - q) / b

        # Si Kelly es negativo, no apostar
        if kelly_fraction_raw <= 0:
            logger.info(f"Kelly negativo ({kelly_fraction_raw:.4f}) - No operar")
            return 0.0

        # Aplicar fracción de Kelly (conservador - típicamente 1/4 o 1/2)
        kelly_adjusted = kelly_fraction_raw * self.kelly_fraction

        # Limitar al máximo permitido
        kelly_capped = min(kelly_adjusted, self.max_risk_per_trade / 100)

        # v1.5: Usar capital real si se proporciona
        capital = capital_override if capital_override is not None else self.current_capital

        # Calcular tamaño de posición
        capital_to_risk = capital * kelly_capped

        if stop_loss and stop_loss != current_price:
            risk_per_unit = abs(current_price - stop_loss)
            position_size = capital_to_risk / risk_per_unit
        else:
            position_size = capital_to_risk / current_price

        logger.info(
            f"Kelly Sizing: confianza={confidence:.2f}, win_prob={win_probability:.2f}, "
            f"kelly_raw={kelly_fraction_raw:.4f}, kelly_adj={kelly_adjusted:.4f}, "
            f"position_size={position_size:.8f}"
        )

        return position_size

    def _adjust_confidence_to_probability(self, confidence: float) -> float:
        """
        Ajusta la confianza de la IA a una probabilidad realista.

        v1.7: Mejorado para ser más conservador con historial limitado.
        La confianza de la IA tiende a ser optimista, así que la ajustamos
        basándonos en el historial real de operaciones.

        Args:
            confidence: Confianza reportada por la IA (0-1)

        Returns:
            Probabilidad ajustada
        """
        # Obtener win rate histórico
        historical_win_rate = self._get_win_rate()
        total_trades = self.trade_history['wins'] + self.trade_history['losses']

        # v1.7.1: Ajustado para permitir operaciones iniciales
        # Ser conservador pero no tan restrictivo que impida operar
        if total_trades < 10:
            # Menos de 10 trades: usar probabilidad conservadora pero viable
            # 0.50 permite operaciones con Kelly positivo cuando R/R >= 2
            logger.info(f"Kelly: Solo {total_trades} trades - usando probabilidad base 0.50")
            return 0.50  # Neutral - permite operar si R/R es bueno

        elif total_trades < 30:
            # Entre 10-30 trades: blend conservador
            base_probability = 0.48
            weight = (total_trades - 10) / 20  # 0 a 1 entre 10 y 30 trades
            blended = base_probability * (1 - weight) + historical_win_rate * weight
            logger.debug(f"Kelly: {total_trades} trades - blend probability {blended:.2f}")
            return max(0.35, min(blended, 0.65))  # Limitar más estrictamente

        elif total_trades < 50:
            # Entre 30-50 trades: blend moderado
            base_probability = 0.50
            weight = (total_trades - 30) / 20
            blended = base_probability * (1 - weight) + historical_win_rate * weight
            logger.debug(f"Kelly: {total_trades} trades - moderate blend {blended:.2f}")
            return max(0.30, min(blended, 0.70))

        # 50+ trades: confiar más en historial real
        # Ajustar confianza usando historial
        historical_factor = historical_win_rate / 0.50  # Normalizado a 50%
        historical_factor = max(0.6, min(historical_factor, 1.4))  # v1.7: Rango más estrecho

        adjusted_probability = confidence * historical_factor

        # v1.7: Aplicar factor de seguridad adicional basado en drawdown reciente
        recent_losses = self._get_recent_loss_streak()
        if recent_losses >= 3:
            # Reducir probabilidad si hay racha perdedora
            safety_factor = max(0.7, 1 - (recent_losses - 2) * 0.1)
            adjusted_probability *= safety_factor
            logger.info(f"Kelly: {recent_losses} pérdidas recientes - factor seguridad {safety_factor:.2f}")

        # Limitar entre 0.25 y 0.80 (nunca demasiado extremo)
        return max(0.25, min(adjusted_probability, 0.80))

    def _get_recent_loss_streak(self) -> int:
        """
        v1.7: Calcula la racha de pérdidas recientes.
        Útil para ajustar Kelly dinámicamente.

        Returns:
            Número de pérdidas consecutivas recientes
        """
        # Si no hay suficiente historial, asumir 0
        if not hasattr(self, 'recent_results'):
            self.recent_results = []

        # Contar pérdidas consecutivas desde el final
        streak = 0
        for result in reversed(self.recent_results[-10:]):  # Últimos 10 trades
            if result == 'loss':
                streak += 1
            else:
                break

        return streak

    def record_trade_result(self, is_win: bool):
        """
        v1.7: Registra resultado de trade para tracking de rachas.

        Args:
            is_win: True si el trade fue ganador
        """
        if not hasattr(self, 'recent_results'):
            self.recent_results = []

        self.recent_results.append('win' if is_win else 'loss')

        # Mantener solo los últimos 20 resultados
        if len(self.recent_results) > 20:
            self.recent_results = self.recent_results[-20:]

    def _get_win_rate(self) -> float:
        """Calcula el win rate histórico."""
        total = self.trade_history['wins'] + self.trade_history['losses']
        if total == 0:
            return 0.50  # Sin historial, asumir 50%
        return self.trade_history['wins'] / total

    def get_dynamic_risk_percentage(self, confidence: float) -> float:
        """
        Obtiene el porcentaje de riesgo dinámico basado en confianza.
        Método simplificado para integración con el sistema existente.

        Args:
            confidence: Confianza de la IA (0-1)

        Returns:
            Porcentaje de riesgo recomendado
        """
        if not self.use_kelly_criterion:
            return self.max_risk_per_trade

        # Mapeo de confianza a riesgo
        if confidence >= 0.85:
            risk = min(self.max_risk_per_trade * 1.25, 3.0)  # Hasta 3%
        elif confidence >= 0.70:
            risk = self.max_risk_per_trade  # Normal (2%)
        elif confidence >= 0.55:
            risk = self.max_risk_per_trade * 0.75  # Reducido (1.5%)
        elif confidence >= 0.40:
            risk = self.max_risk_per_trade * 0.5  # Mínimo (1%)
        else:
            risk = 0  # No operar

        logger.debug(f"Riesgo dinámico: confianza={confidence:.2f} -> riesgo={risk:.2f}%")
        return risk

    def update_trade_history(self, is_win: bool, amount: float):
        """
        Actualiza el historial de trades para cálculos de Kelly.

        Args:
            is_win: True si el trade fue ganador
            amount: Monto absoluto ganado/perdido
        """
        if is_win:
            self.trade_history['wins'] += 1
            self.trade_history['total_win_amount'] += abs(amount)
        else:
            self.trade_history['losses'] += 1
            self.trade_history['total_loss_amount'] += abs(amount)

        logger.info(
            f"Historial actualizado: {self.trade_history['wins']}W / "
            f"{self.trade_history['losses']}L = {self._get_win_rate()*100:.1f}%"
        )

        self._save_state()

    # ==================== v1.6: VALIDACIÓN DE FEES ====================

    def validate_trade_profitability(
        self,
        symbol: str,
        position_value_usd: float,
        expected_profit_percent: float
    ) -> Dict[str, Any]:
        """
        v1.6: Valida que un trade sea rentable después de comisiones.

        Args:
            symbol: Par de trading (ej: 'BTC/USDT')
            position_value_usd: Valor de la posición en USD
            expected_profit_percent: Ganancia esperada en porcentaje

        Returns:
            Dict con validación y detalles
        """
        # Obtener mínimo del exchange para este símbolo
        symbol_key = symbol.replace('/', '_')
        min_notional = self.exchange_minimums.get(
            symbol_key,
            self.exchange_minimums.get('default', 10.0)
        )

        # 1. Verificar tamaño mínimo del exchange
        if position_value_usd < min_notional:
            return {
                'valid': False,
                'reason': f'Posición ${position_value_usd:.2f} menor al mínimo del exchange ${min_notional}',
                'min_required': min_notional
            }

        # 2. Verificar tamaño mínimo para rentabilidad
        if position_value_usd < self.min_position_usd:
            return {
                'valid': False,
                'reason': f'Posición ${position_value_usd:.2f} menor al mínimo rentable ${self.min_position_usd}',
                'min_required': self.min_position_usd
            }

        # 3. Calcular fees
        fees_usd = position_value_usd * (self.round_trip_fee_percent / 100)

        # 4. Calcular ganancia esperada
        expected_profit_usd = position_value_usd * (expected_profit_percent / 100)

        # 5. Verificar ganancia neta
        net_profit_usd = expected_profit_usd - fees_usd

        if net_profit_usd < self.min_profit_after_fees:
            return {
                'valid': False,
                'reason': f'Ganancia neta ${net_profit_usd:.2f} menor al mínimo ${self.min_profit_after_fees}',
                'fees': fees_usd,
                'expected_profit': expected_profit_usd,
                'net_profit': net_profit_usd
            }

        # 6. Verificar ratio ganancia/fees
        if fees_usd > 0 and (expected_profit_usd / fees_usd) < self.profit_to_fees_ratio:
            return {
                'valid': False,
                'reason': f'Ratio ganancia/fees {expected_profit_usd/fees_usd:.1f}x menor al mínimo {self.profit_to_fees_ratio}x',
                'ratio': expected_profit_usd / fees_usd,
                'min_ratio': self.profit_to_fees_ratio
            }

        # Trade es rentable
        return {
            'valid': True,
            'position_value_usd': position_value_usd,
            'total_fees_usd': round(fees_usd, 4),
            'expected_profit_usd': round(expected_profit_usd, 2),
            'net_profit_usd': round(net_profit_usd, 2),
            'profit_to_fees_ratio': round(expected_profit_usd / fees_usd, 1) if fees_usd > 0 else float('inf'),
            'message': f'Trade rentable: ganancia neta ${net_profit_usd:.2f} después de fees ${fees_usd:.4f}'
        }

    def calculate_min_profitable_position(
        self,
        symbol: str,
        target_profit_percent: float = 4.0
    ) -> float:
        """
        v1.6: Calcula el tamaño mínimo de posición para ser rentable.

        Args:
            symbol: Par de trading
            target_profit_percent: % de ganancia objetivo (default 4% = 2:1 R/R con 2% SL)

        Returns:
            Tamaño mínimo en USD
        """
        # Necesitamos: ganancia_esperada > fees * profit_to_fees_ratio
        # ganancia = position * target_profit_percent / 100
        # fees = position * round_trip_fee_percent / 100
        # position * target_profit_percent > position * round_trip_fee_percent * ratio
        # Ya que position se cancela, siempre es rentable si target_profit > fees * ratio

        # Pero también necesitamos min_profit_after_fees
        # net_profit = position * (target_profit - round_trip_fee) / 100 >= min_profit_after_fees
        # position >= min_profit_after_fees * 100 / (target_profit - round_trip_fee)

        net_profit_percent = target_profit_percent - self.round_trip_fee_percent
        if net_profit_percent <= 0:
            logger.warning("El target profit no cubre las comisiones")
            return float('inf')

        min_for_profit = (self.min_profit_after_fees * 100) / net_profit_percent

        # También considerar mínimo del exchange
        symbol_key = symbol.replace('/', '_')
        exchange_min = self.exchange_minimums.get(
            symbol_key,
            self.exchange_minimums.get('default', 10.0)
        )

        # Retornar el mayor de los mínimos
        return max(min_for_profit, exchange_min, self.min_position_usd)

    def get_fee_summary(self) -> Dict[str, Any]:
        """v1.6: Obtiene resumen de configuración de fees."""
        return {
            'maker_fee_percent': self.maker_fee_percent,
            'taker_fee_percent': self.taker_fee_percent,
            'round_trip_fee_percent': self.round_trip_fee_percent,
            'min_position_usd': self.min_position_usd,
            'min_profit_after_fees': self.min_profit_after_fees,
            'profit_to_fees_ratio': self.profit_to_fees_ratio,
            'exchange_minimums': self.exchange_minimums
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
