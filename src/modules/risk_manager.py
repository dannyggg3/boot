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

v1.8 INSTITUCIONAL:
      - ATR-based Stop Loss (en lugar de % fijo)
      - Kelly Criterion funcional con historial real
      - Session filter integrado
      - Volatility-adaptive sizing mejorado

Autor: Trading Bot System
Versión: 1.8
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
import sqlite3
from contextlib import contextmanager
import threading

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

        # v1.8 INSTITUCIONAL: Configuración ATR-based Stop Loss
        atr_config = self.config.get('atr_stops', {})
        self.use_atr_stops = atr_config.get('enabled', True)  # Activado por defecto
        self.atr_sl_multiplier = atr_config.get('sl_multiplier', 2.0)  # SL a 2x ATR
        self.atr_tp_multiplier = atr_config.get('tp_multiplier', 3.0)  # TP a 3x ATR (R/R 1.5:1)
        self.atr_min_distance_percent = atr_config.get('min_distance_percent', 0.5)  # Mínimo 0.5%
        self.atr_max_distance_percent = atr_config.get('max_distance_percent', 8.0)  # Máximo 8%

        # v1.8: Session filter para horarios óptimos
        session_config = self.config.get('session_filter', {})
        self.use_session_filter = session_config.get('enabled', False)
        self.optimal_hours_utc = session_config.get('optimal_hours_utc', [[7, 16], [13, 22]])  # Europa y USA

        # v2.2: Inicializar base de datos SQLite para persistencia atómica
        self.db_path = 'data/risk_manager.db'
        self._db_lock = threading.Lock()
        self._init_database()

        # Cargar estado si existe
        self._load_state()

        logger.info(f"Risk Manager v2.2 INSTITUCIONAL inicializado (SQLite atómico)")
        logger.info(f"  Capital: ${self.current_capital}")
        logger.info(f"  ATR Stops: {'ON' if self.use_atr_stops else 'OFF'} (SL: {self.atr_sl_multiplier}x ATR, TP: {self.atr_tp_multiplier}x ATR)")
        logger.info(f"  Kelly Criterion: {'ON' if self.use_kelly_criterion else 'OFF'} (fraction: {self.kelly_fraction})")
        logger.info(f"  Session Filter: {'ON' if self.use_session_filter else 'OFF'}")

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

        # 3. v2.1 FIX CRÍTICO: Calcular ATR-based SL/TP PRIMERO
        # El SL debe calcularse ANTES de Kelly para que el position sizing sea correcto
        # Bug anterior: Kelly recibía SL=None y dividía capital/precio (posiciones microscópicas)
        atr_stop_loss = suggested_stop_loss
        atr_take_profit = suggested_take_profit

        if self.use_atr_stops and market_data and 'atr' in market_data:
            # SIEMPRE usar ATR para calcular SL, ignorando sugerencia de IA
            atr_stop_loss = self._calculate_automatic_stop_loss(
                current_price,
                decision,
                market_data
            )

            # SIEMPRE usar ATR para calcular TP con el R/R mínimo requerido
            atr_take_profit = self.calculate_atr_take_profit(
                current_price,
                decision,
                market_data,
                risk_reward_ratio=self.min_risk_reward_ratio
            )

            sl_distance_percent = abs(current_price - atr_stop_loss) / current_price * 100
            tp_distance_percent = abs(atr_take_profit - current_price) / current_price * 100 if atr_take_profit else 0

            logger.info(f"🎯 v2.0 ATR FORZADO [{symbol}]: SL a {sl_distance_percent:.2f}%, TP a {tp_distance_percent:.2f}%")
            logger.info(f"   Precio: ${current_price:.2f} | SL: ${atr_stop_loss:.2f} | TP: ${atr_take_profit:.2f}")

        # Usar ATR SL para todos los cálculos siguientes
        suggested_stop_loss = atr_stop_loss
        suggested_take_profit = atr_take_profit

        # 4. Calcular capital efectivo
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

        # 5. Calcular tamaño de posición con Kelly (ahora con SL correcto de ATR)
        if self.use_kelly_criterion and confidence >= self.min_confidence_to_trade:
            position_size = self.calculate_kelly_position_size(
                confidence=confidence,
                current_price=current_price,
                stop_loss=suggested_stop_loss,  # v2.1: Ahora usa ATR SL correcto
                capital_override=effective_capital_usd
            )
            logger.info(f"Kelly Sizing: confianza={confidence:.2f}, risk={self.get_dynamic_risk_percentage(confidence):.1f}%")
        else:
            position_size = self._calculate_position_size(
                current_price,
                suggested_stop_loss,
                capital_override=effective_capital_usd
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

        # 6. Validar SL secundario si no usamos ATR (fallback)
        if not self.use_atr_stops:
            if suggested_stop_loss:
                sl_distance = abs(current_price - suggested_stop_loss) / current_price * 100
                # Stop loss muy cercano (< 1.5%) o muy lejano (> 10%) - ajustar
                if sl_distance < self.atr_min_distance_percent or sl_distance > 10:
                    suggested_stop_loss = self._adjust_stop_loss(
                        current_price,
                        decision,
                        market_data
                    )
                    logger.warning(f"Stop loss ajustado para {symbol} (estaba a {sl_distance:.2f}%)")
            else:
                # Crear stop loss automático como fallback
                suggested_stop_loss = self._calculate_automatic_stop_loss(
                    current_price,
                    decision,
                    market_data
                )

        # 7. Validar ratio riesgo/beneficio
        if suggested_take_profit:
            risk_reward = self._calculate_risk_reward(
                current_price,
                suggested_stop_loss,
                suggested_take_profit,
                decision
            )

            # v2.1 FIX: R/R debe ser ESTRICTAMENTE menor (con tolerancia para flotantes)
            # Un R/R de 2.0 es ACEPTABLE cuando el mínimo es 2.0
            if risk_reward < (self.min_risk_reward_ratio - 0.001):
                # v1.7 FIX CRÍTICO: RECHAZAR trades con mal R/R
                # Un trade con R/R < mínimo tiene expectativa matemática negativa a largo plazo
                logger.warning(
                    f"Ratio R/R bajo ({risk_reward:.2f}) para {symbol}. "
                    f"Mínimo requerido: {self.min_risk_reward_ratio}"
                )
                return self._reject_trade(
                    f"Ratio R/R insuficiente ({risk_reward:.2f} < {self.min_risk_reward_ratio})",
                    symbol
                )

        # 8. Verificar volatilidad extrema
        if market_data and 'volatility_level' in market_data:
            if market_data['volatility_level'] == 'alta':
                # Reducir tamaño de posición en mercados volátiles
                position_size *= 0.5
                logger.info(f"Posición reducida 50% por alta volatilidad en {symbol}")

        # 9. v1.6: Validar rentabilidad después de comisiones
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
        v1.8 INSTITUCIONAL: Calcula Stop Loss basado en ATR (Average True Range).

        Los institucionales NUNCA usan % fijo porque cada activo tiene volatilidad diferente.
        BTC con ATR 1% vs SOL con ATR 4% requieren SL muy diferentes.

        Fórmula: SL = Entry ± (ATR * multiplier)

        Args:
            current_price: Precio actual
            decision: COMPRA o VENTA
            market_data: Datos del mercado con ATR

        Returns:
            Precio de stop loss
        """
        # v1.8: Usar ATR si está disponible y habilitado
        if self.use_atr_stops and market_data and 'atr' in market_data:
            atr = market_data['atr']
            atr_percent = market_data.get('atr_percent', market_data.get('atr_percentage', 0))

            # Calcular distancia del SL usando ATR
            sl_distance = atr * self.atr_sl_multiplier
            sl_distance_percent = (sl_distance / current_price) * 100

            # v1.8: Aplicar límites mínimos y máximos
            if sl_distance_percent < self.atr_min_distance_percent:
                # ATR muy bajo (mercado muy tranquilo) - usar mínimo
                sl_distance = current_price * (self.atr_min_distance_percent / 100)
                logger.debug(f"SL ajustado al mínimo {self.atr_min_distance_percent}% (ATR muy bajo)")
            elif sl_distance_percent > self.atr_max_distance_percent:
                # ATR muy alto (mercado muy volátil) - usar máximo
                sl_distance = current_price * (self.atr_max_distance_percent / 100)
                logger.debug(f"SL ajustado al máximo {self.atr_max_distance_percent}% (ATR muy alto)")

            if decision == 'COMPRA':
                stop_loss = current_price - sl_distance
            else:  # VENTA
                stop_loss = current_price + sl_distance

            final_sl_percent = abs(stop_loss - current_price) / current_price * 100
            logger.info(f"📊 ATR-based SL: ATR={atr:.2f} ({atr_percent:.2f}%), "
                       f"Multiplier={self.atr_sl_multiplier}x, SL Distance={final_sl_percent:.2f}%")
        else:
            # Fallback: usar % fijo basado en max_risk_per_trade
            # Pero más conservador que antes
            fallback_percent = min(self.max_risk_per_trade * 1.5, 4.0)  # Máx 4%

            if decision == 'COMPRA':
                stop_loss = current_price * (1 - fallback_percent / 100)
            else:
                stop_loss = current_price * (1 + fallback_percent / 100)

            logger.warning(f"⚠️ Sin ATR disponible - usando SL fijo de {fallback_percent:.1f}%")

        return stop_loss

    def calculate_atr_take_profit(
        self,
        current_price: float,
        decision: str,
        market_data: Optional[Dict[str, Any]],
        risk_reward_ratio: Optional[float] = None
    ) -> Optional[float]:
        """
        v1.8 INSTITUCIONAL: Calcula Take Profit basado en ATR.

        TP = Entry ± (ATR * multiplier * R/R ratio)

        Args:
            current_price: Precio actual
            decision: COMPRA o VENTA
            market_data: Datos del mercado con ATR
            risk_reward_ratio: Ratio R/R deseado (si None, usa min_risk_reward_ratio)

        Returns:
            Precio de take profit o None si no se puede calcular
        """
        if not market_data or 'atr' not in market_data:
            return None

        atr = market_data['atr']
        rr_ratio = risk_reward_ratio or self.min_risk_reward_ratio

        # TP distance = ATR * SL_multiplier * R/R_ratio
        # Esto asegura que siempre tengamos el R/R deseado
        tp_distance = atr * self.atr_sl_multiplier * rr_ratio

        # Aplicar límites
        tp_distance_percent = (tp_distance / current_price) * 100
        min_tp = self.atr_min_distance_percent * rr_ratio
        max_tp = self.atr_max_distance_percent * rr_ratio

        if tp_distance_percent < min_tp:
            tp_distance = current_price * (min_tp / 100)
        elif tp_distance_percent > max_tp:
            tp_distance = current_price * (max_tp / 100)

        if decision == 'COMPRA':
            take_profit = current_price + tp_distance
        else:  # VENTA
            take_profit = current_price - tp_distance

        logger.info(f"🎯 ATR-based TP: Distance={tp_distance_percent:.2f}%, R/R={rr_ratio}:1")
        return take_profit

    def is_optimal_session(self) -> Dict[str, Any]:
        """
        v1.8 INSTITUCIONAL: Verifica si estamos en una sesión de trading óptima.

        Las mejores horas para crypto son cuando los mercados de USA y Europa están abiertos.
        Fuera de estas horas hay menos liquidez y más spreads.

        Returns:
            Dict con resultado y razón
        """
        if not self.use_session_filter:
            return {'optimal': True, 'reason': 'Session filter deshabilitado'}

        from datetime import datetime, timezone

        current_hour = datetime.now(timezone.utc).hour
        current_day = datetime.now(timezone.utc).weekday()  # 0=Monday, 6=Sunday

        # Fin de semana = menor liquidez
        if current_day >= 5:  # Sábado o domingo
            return {
                'optimal': False,
                'reason': f'Fin de semana (menor liquidez)',
                'hour_utc': current_hour,
                'day': current_day
            }

        # Verificar si estamos en horario óptimo
        for start_hour, end_hour in self.optimal_hours_utc:
            if start_hour <= current_hour < end_hour:
                return {
                    'optimal': True,
                    'reason': f'Sesión activa ({start_hour}:00-{end_hour}:00 UTC)',
                    'hour_utc': current_hour
                }

        return {
            'optimal': False,
            'reason': f'Fuera de horario óptimo ({current_hour}:00 UTC)',
            'hour_utc': current_hour,
            'optimal_hours': self.optimal_hours_utc
        }

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

    # ==================== v2.2: PERSISTENCIA SQLITE ATÓMICA ====================

    @contextmanager
    def _get_connection(self):
        """
        v2.2: Context manager para conexiones SQLite thread-safe.
        Garantiza transacciones atómicas - si algo falla, se hace rollback.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """
        v2.2: Inicializa la base de datos SQLite para persistencia atómica.
        Reemplaza el archivo JSON que era vulnerable a corrupción.
        """
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self._db_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Tabla principal de estado
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS risk_state (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        current_capital REAL NOT NULL,
                        initial_capital REAL NOT NULL,
                        daily_pnl REAL DEFAULT 0,
                        today TEXT NOT NULL,
                        kill_switch_active INTEGER DEFAULT 0,
                        high_water_mark REAL DEFAULT 0,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Tabla de historial para Kelly Criterion
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trade_history_kelly (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wins INTEGER DEFAULT 0,
                        losses INTEGER DEFAULT 0,
                        total_win_amount REAL DEFAULT 0,
                        total_loss_amount REAL DEFAULT 0,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Tabla de resultados recientes (para tracking de rachas)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recent_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        result TEXT NOT NULL,
                        pnl REAL DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Tabla de trades abiertos
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS open_trades (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        data TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Crear índice para resultados recientes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_recent_results_created
                    ON recent_results(created_at DESC)
                """)

                logger.debug("Base de datos SQLite para Risk Manager inicializada")

    def _save_state(self):
        """
        v2.2 INSTITUCIONAL: Guarda el estado en SQLite con transacción atómica.

        CRÍTICO: A diferencia del JSON, esto es ATÓMICO:
        - Si el bot crashea durante la escritura, el estado anterior se mantiene
        - No hay riesgo de corrupción de datos
        - El historial de Kelly se preserva siempre
        """
        with self._db_lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Upsert estado principal (INSERT OR REPLACE)
                    cursor.execute("""
                        INSERT OR REPLACE INTO risk_state
                        (id, current_capital, initial_capital, daily_pnl, today,
                         kill_switch_active, high_water_mark, updated_at)
                        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.current_capital,
                        self.initial_capital,
                        self.daily_pnl,
                        str(self.today),
                        1 if self.kill_switch_active else 0,
                        getattr(self, 'high_water_mark', self.current_capital),
                        datetime.now().isoformat()
                    ))

                    # Upsert historial de Kelly
                    cursor.execute("""
                        INSERT OR REPLACE INTO trade_history_kelly
                        (id, wins, losses, total_win_amount, total_loss_amount, updated_at)
                        VALUES (1, ?, ?, ?, ?, ?)
                    """, (
                        self.trade_history['wins'],
                        self.trade_history['losses'],
                        self.trade_history['total_win_amount'],
                        self.trade_history['total_loss_amount'],
                        datetime.now().isoformat()
                    ))

                logger.debug("Estado guardado en SQLite (atómico)")

            except Exception as e:
                logger.error(f"Error guardando estado en SQLite: {e}")

    def _load_state(self):
        """
        v2.2 INSTITUCIONAL: Carga el estado del risk manager desde SQLite.

        CRÍTICO para Kelly Criterion: El historial de trades debe persistir entre reinicios
        para que Kelly pueda calcular probabilidades reales basadas en rendimiento histórico.

        También intenta migrar datos del JSON antiguo si existe.
        """
        self.recent_results = []
        self.high_water_mark = self.initial_capital

        # Primero intentar migrar JSON antiguo si existe
        self._migrate_from_json()

        with self._db_lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Cargar estado principal
                    cursor.execute("SELECT * FROM risk_state WHERE id = 1")
                    state_row = cursor.fetchone()

                    if state_row:
                        self.current_capital = state_row['current_capital']
                        self.daily_pnl = state_row['daily_pnl']
                        self.kill_switch_active = bool(state_row['kill_switch_active'])
                        self.high_water_mark = state_row['high_water_mark'] or self.current_capital

                        # Verificar si es un nuevo día
                        saved_date = datetime.strptime(state_row['today'], '%Y-%m-%d').date()
                        if saved_date != self.today:
                            self.daily_pnl = 0.0
                            self.kill_switch_active = False
                    else:
                        logger.info("No se encontró estado previo - Usando valores por defecto")

                    # Cargar historial de Kelly
                    cursor.execute("SELECT * FROM trade_history_kelly WHERE id = 1")
                    kelly_row = cursor.fetchone()

                    if kelly_row:
                        self.trade_history = {
                            'wins': kelly_row['wins'],
                            'losses': kelly_row['losses'],
                            'total_win_amount': kelly_row['total_win_amount'],
                            'total_loss_amount': kelly_row['total_loss_amount']
                        }

                    # Cargar resultados recientes (últimos 20)
                    cursor.execute("""
                        SELECT result FROM recent_results
                        ORDER BY created_at DESC LIMIT 20
                    """)
                    self.recent_results = [row['result'] for row in cursor.fetchall()]
                    self.recent_results.reverse()  # Orden cronológico

                # Log del estado cargado
                total_trades = self.trade_history['wins'] + self.trade_history['losses']
                win_rate = self._get_win_rate()
                logger.info(f"📊 Estado cargado (SQLite) - Capital: ${self.current_capital:.2f}")
                logger.info(f"📊 Kelly Historial: {total_trades} trades ({self.trade_history['wins']}W/{self.trade_history['losses']}L = {win_rate*100:.1f}%)")

                if total_trades > 0:
                    avg_win = self.trade_history['total_win_amount'] / max(1, self.trade_history['wins'])
                    avg_loss = self.trade_history['total_loss_amount'] / max(1, self.trade_history['losses'])
                    if avg_loss > 0:
                        actual_rr = avg_win / avg_loss
                        logger.info(f"📊 Kelly Stats: Avg Win ${avg_win:.2f}, Avg Loss ${avg_loss:.2f}, R/R Real {actual_rr:.2f}")

            except Exception as e:
                logger.error(f"Error cargando estado desde SQLite: {e}")

    def _migrate_from_json(self):
        """
        v2.2: Migra datos del archivo JSON antiguo a SQLite (una sola vez).
        Preserva el historial de Kelly y capital existente.
        """
        json_file = 'data/risk_manager_state.json'
        migrated_flag = 'data/.risk_manager_migrated'

        # Si ya migramos, no hacer nada
        if os.path.exists(migrated_flag):
            return

        if not os.path.exists(json_file):
            return

        try:
            with open(json_file, 'r') as f:
                old_state = json.load(f)

            logger.info("🔄 Migrando datos de JSON a SQLite...")

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Migrar estado principal
                cursor.execute("""
                    INSERT OR REPLACE INTO risk_state
                    (id, current_capital, initial_capital, daily_pnl, today,
                     kill_switch_active, high_water_mark, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    old_state.get('current_capital', self.initial_capital),
                    self.initial_capital,
                    old_state.get('daily_pnl', 0),
                    old_state.get('today', str(self.today)),
                    1 if old_state.get('kill_switch_active') else 0,
                    old_state.get('current_capital', self.initial_capital),
                    datetime.now().isoformat()
                ))

                # Migrar historial de Kelly
                trade_hist = old_state.get('trade_history', {})
                cursor.execute("""
                    INSERT OR REPLACE INTO trade_history_kelly
                    (id, wins, losses, total_win_amount, total_loss_amount, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?)
                """, (
                    trade_hist.get('wins', 0),
                    trade_hist.get('losses', 0),
                    trade_hist.get('total_win_amount', 0),
                    trade_hist.get('total_loss_amount', 0),
                    datetime.now().isoformat()
                ))

                # Migrar resultados recientes
                recent = old_state.get('recent_results', [])
                for result in recent[-20:]:
                    cursor.execute("""
                        INSERT INTO recent_results (result) VALUES (?)
                    """, (result,))

            # Marcar como migrado
            with open(migrated_flag, 'w') as f:
                f.write(datetime.now().isoformat())

            # Renombrar JSON antiguo como backup
            backup_file = json_file + '.backup'
            os.rename(json_file, backup_file)

            logger.info(f"✅ Migración completada. JSON movido a {backup_file}")

        except Exception as e:
            logger.error(f"Error en migración JSON→SQLite: {e}")

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

    def record_trade_result(self, is_win: bool, pnl: float = 0):
        """
        v2.2: Registra resultado de trade en SQLite para tracking de rachas.

        Args:
            is_win: True si el trade fue ganador
            pnl: PnL del trade (opcional)
        """
        if not hasattr(self, 'recent_results'):
            self.recent_results = []

        result = 'win' if is_win else 'loss'
        self.recent_results.append(result)

        # Mantener solo los últimos 20 resultados en memoria
        if len(self.recent_results) > 20:
            self.recent_results = self.recent_results[-20:]

        # v2.2: Guardar en SQLite
        with self._db_lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO recent_results (result, pnl) VALUES (?, ?)
                    """, (result, pnl))

                    # Limpiar resultados antiguos (mantener solo últimos 50)
                    cursor.execute("""
                        DELETE FROM recent_results WHERE id NOT IN (
                            SELECT id FROM recent_results ORDER BY created_at DESC LIMIT 50
                        )
                    """)
            except Exception as e:
                logger.error(f"Error guardando resultado en SQLite: {e}")

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
