"""
Position Engine - Motor de gestión de posiciones
================================================
Coordinador central del ciclo de vida de posiciones:
- Creación de posiciones después de orden ejecutada
- Colocación de órdenes de protección (OCO/SL/TP)
- Monitoreo continuo de posiciones
- Trailing stop inteligente
- Cierre de posiciones y registro de resultados

v1.7 Mejoras Institucionales:
- Fix race condition en trailing stop
- Validación pre-trigger para evitar SL inmediatos
- Cooldown de 3s entre actualizaciones de SL
- Margen de seguridad mínimo de 0.3%

Autor: Trading Bot System
Versión: 1.7
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class PositionEngine:
    """
    Motor de gestión de posiciones.
    Coordina el ciclo de vida completo desde entrada hasta salida.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        market_engine,
        order_manager,
        position_store,
        notifier,
        data_logger=None,
        websocket_engine=None
    ):
        """
        Inicializa el Position Engine.

        Args:
            config: Configuración del bot
            market_engine: Motor de mercado (para precios)
            order_manager: Gestor de órdenes OCO
            position_store: Almacén de posiciones (SQLite)
            notifier: Sistema de notificaciones
            data_logger: Logger de datos (InfluxDB)
            websocket_engine: Motor WebSocket para precios RT
        """
        self.config = config
        self.market_engine = market_engine
        self.order_manager = order_manager
        self.store = position_store
        self.notifier = notifier
        self.data_logger = data_logger
        self.websocket_engine = websocket_engine

        # Configuración de position management
        pm_config = config.get('position_management', {})
        self.enabled = pm_config.get('enabled', True)
        self.protection_mode = pm_config.get('protection_mode', 'oco')

        # Trailing stop config - v1.8.1 completo
        ts_config = pm_config.get('trailing_stop', {})
        self.trailing_enabled = ts_config.get('enabled', True)
        self.trailing_activation = ts_config.get('activation_profit_percent', 1.0)
        self.trailing_distance = ts_config.get('trail_distance_percent', 2.0)
        # v1.8.1: Nuevos parámetros de seguridad
        self.trailing_min_profit_lock = ts_config.get('min_profit_to_lock', 0.5)
        self.trailing_cooldown = ts_config.get('cooldown_seconds', 3.0)
        self.trailing_safety_margin = ts_config.get('min_safety_margin_percent', 0.3) / 100

        # Portfolio limits
        portfolio_config = pm_config.get('portfolio', {})
        self.max_positions = portfolio_config.get('max_concurrent_positions', 3)
        self.max_exposure_percent = portfolio_config.get('max_exposure_percent', 50)

        # Local monitoring config
        local_config = pm_config.get('local_monitoring', {})
        self.local_check_interval = local_config.get('check_interval_ms', 500) / 1000

        # Estado interno
        self.positions: Dict[str, Dict] = {}  # position_id -> position_data
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_position_closed: Optional[Callable] = None
        self.on_sl_triggered: Optional[Callable] = None
        self.on_tp_triggered: Optional[Callable] = None

        logger.info(f"PositionEngine inicializado")
        logger.info(f"  Modo protección: {self.protection_mode}")
        logger.info(f"  Trailing stop: {'ON' if self.trailing_enabled else 'OFF'}")
        logger.info(f"  Max posiciones: {self.max_positions}")

    # =========================================================================
    # CICLO DE VIDA DE POSICIONES
    # =========================================================================

    def create_position(
        self,
        order_result: Dict[str, Any],
        trade_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Crea una nueva posición después de que una orden de entrada se ejecuta.
        Coloca automáticamente las órdenes de protección (SL/TP).

        Args:
            order_result: Resultado de la orden de entrada
            trade_params: Parámetros del trade (symbol, stop_loss, take_profit, etc.)

        Returns:
            Diccionario con información de la posición o None si falla
        """
        if not self.enabled:
            logger.warning("Position management deshabilitado")
            return None

        try:
            symbol = trade_params['symbol']
            # Obtener side directamente o inferir de decision
            side = trade_params.get('side')
            if side is None:
                decision = trade_params.get('decision', 'COMPRA')
                side = 'long' if decision == 'COMPRA' else 'short'
            elif hasattr(side, 'value'):
                side = side.value  # Si es enum PositionSide

            # Verificar límites de portfolio
            if not self.can_open_position(symbol):
                logger.warning(f"No se puede abrir posición: límites de portfolio alcanzados")
                return None

            # Crear ID de posición
            position_id = str(uuid.uuid4())[:8]

            # Extraer datos de la orden
            entry_price = order_result.get('average') or order_result.get('price') or trade_params.get('entry_price')
            quantity = order_result.get('filled') or order_result.get('amount') or trade_params.get('quantity')

            if not entry_price or not quantity:
                logger.error(f"Datos de orden incompletos: price={entry_price}, qty={quantity}")
                return None

            # Datos de la posición
            position = {
                'id': position_id,
                'symbol': symbol,
                'side': side,
                'status': 'open',
                'entry_price': float(entry_price),
                'quantity': float(quantity),
                'entry_time': datetime.now().isoformat(),
                'entry_order_id': order_result.get('id'),
                'confidence': trade_params.get('confidence', 0.0),
                'agent_type': trade_params.get('agent_type', 'general'),
                'entry_reasoning': trade_params.get('reasoning', ''),
                'stop_loss': trade_params['stop_loss'],
                'take_profit': trade_params.get('take_profit'),
                'initial_stop_loss': trade_params['stop_loss'],
                'trailing_stop_active': False,
                'trailing_stop_distance': None,
                'oco_order_id': None,
                'sl_order_id': None,
                'tp_order_id': None
            }

            # Guardar en store
            self.store.save_position(position)
            logger.info(f"📊 Posición creada: {position_id} | {symbol} {side.upper()}")
            logger.info(f"   Entrada: ${entry_price:.2f} x {quantity}")
            logger.info(f"   SL: ${position['stop_loss']:.2f} | TP: ${position['take_profit']}")

            # Colocar órdenes de protección
            if self.protection_mode == 'oco' and position['take_profit']:
                oco_result = self._place_protection_orders(position)
                if oco_result:
                    position['oco_order_id'] = oco_result.get('oco_id')
                    position['sl_order_id'] = oco_result.get('sl_order_id')
                    position['tp_order_id'] = oco_result.get('tp_order_id')
                    self.store.save_position(position)
                else:
                    logger.warning(f"No se pudieron colocar órdenes de protección")

            # Guardar en memoria
            self.positions[position_id] = position

            # Notificar
            self._notify_position_created(position)

            return position

        except Exception as e:
            logger.error(f"Error creando posición: {e}", exc_info=True)
            return None

    def _place_protection_orders(self, position: Dict) -> Optional[Dict]:
        """Coloca órdenes de protección OCO para una posición."""
        try:
            # Determinar lado de cierre
            close_side = 'sell' if position['side'] == 'long' else 'buy'

            result = self.order_manager.place_oco_order(
                position_id=position['id'],
                symbol=position['symbol'],
                side=close_side,
                quantity=position['quantity'],
                take_profit_price=position['take_profit'],
                stop_loss_price=position['stop_loss']
            )

            return result

        except Exception as e:
            logger.error(f"Error colocando órdenes de protección: {e}")
            return None

    def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_reason: str,
        exit_order_id: Optional[str] = None
    ) -> bool:
        """
        Cierra una posición y registra el resultado.

        Args:
            position_id: ID de la posición
            exit_price: Precio de salida
            exit_reason: Razón del cierre
            exit_order_id: ID de la orden de cierre

        Returns:
            True si se cerró correctamente
        """
        try:
            position = self.positions.get(position_id) or self.store.get_position(position_id)
            if not position:
                logger.warning(f"Posición no encontrada: {position_id}")
                return False

            # Cancelar órdenes de protección pendientes
            self.order_manager.cancel_oco_order(position_id, position['symbol'])

            # Cerrar en store
            success = self.store.close_position(
                position_id=position_id,
                exit_price=exit_price,
                exit_reason=exit_reason,
                exit_order_id=exit_order_id
            )

            if success:
                # Calcular P&L para log
                entry = position['entry_price']
                qty = position['quantity']
                if position['side'] == 'long':
                    pnl = (exit_price - entry) * qty
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl = (entry - exit_price) * qty
                    pnl_pct = ((entry - exit_price) / entry) * 100

                logger.info(f"🏁 Posición cerrada: {position_id}")
                logger.info(f"   {position['symbol']} | {exit_reason}")
                logger.info(f"   P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")

                # v1.7: Registrar en métricas institucionales
                self._record_institutional_metrics(position, exit_price, exit_reason, pnl, pnl_pct)

                # Remover de memoria
                self.positions.pop(position_id, None)

                # Notificar
                self._notify_position_closed(position, exit_price, exit_reason, pnl, pnl_pct)

                # Callback
                if self.on_position_closed:
                    self.on_position_closed(position_id, exit_reason, pnl)

            return success

        except Exception as e:
            logger.error(f"Error cerrando posición: {e}", exc_info=True)
            return False

    # =========================================================================
    # MONITOREO DE POSICIONES
    # =========================================================================

    def start_monitoring(self):
        """Inicia el loop de monitoreo de posiciones en background."""
        if self.monitoring_active:
            logger.warning("Monitoreo ya está activo")
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PositionMonitor"
        )
        self.monitor_thread.start()
        logger.info("🔄 Monitoreo de posiciones iniciado")

    def stop_monitoring(self):
        """Detiene el loop de monitoreo."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitoreo de posiciones detenido")

    def _monitoring_loop(self):
        """Loop principal de monitoreo."""
        while self.monitoring_active:
            try:
                self._check_all_positions()
                time.sleep(self.local_check_interval)
            except Exception as e:
                logger.error(f"Error en monitoring loop: {e}")
                time.sleep(1)

    def _check_all_positions(self):
        """Verifica todas las posiciones abiertas."""
        open_positions = self.store.get_open_positions()

        for pos_data in open_positions:
            try:
                self._check_single_position(pos_data)
            except Exception as e:
                logger.error(f"Error verificando posición {pos_data['id']}: {e}")

    def _check_single_position(self, position: Dict):
        """Verifica una posición individual."""
        symbol = position['symbol']
        position_id = position['id']

        # Obtener precio actual
        current_price = self._get_current_price(symbol)
        if not current_price:
            return

        # Modo OCO: verificar si alguna orden se ejecutó
        if self.protection_mode == 'oco':
            oco_status = self.order_manager.check_oco_status(position_id, symbol)

            if oco_status.get('status') == 'tp_filled':
                self.close_position(
                    position_id=position_id,
                    exit_price=oco_status.get('fill_price', current_price),
                    exit_reason='take_profit'
                )
                return

            elif oco_status.get('status') == 'sl_filled':
                self.close_position(
                    position_id=position_id,
                    exit_price=oco_status.get('fill_price', current_price),
                    exit_reason='stop_loss'
                )
                return

            # En modo paper/backtest con OCO, también verificar triggers locales
            # porque las órdenes OCO no se ejecutan realmente en el exchange
            elif oco_status.get('mode') in ['paper', 'backtest']:
                triggered = self._check_sl_tp_triggers(position, current_price)
                if triggered:
                    return

        # Modo Local: verificar triggers manualmente
        elif self.protection_mode == 'local':
            triggered = self._check_sl_tp_triggers(position, current_price)
            if triggered:
                return

        # Verificar trailing stop
        if self.trailing_enabled:
            self._check_trailing_stop(position, current_price)

    def _check_sl_tp_triggers(self, position: Dict, current_price: float) -> bool:
        """
        Verifica si SL o TP fueron alcanzados (modo local).

        Returns:
            True si se triggereó algo
        """
        side = position['side']
        sl = position['stop_loss']
        tp = position.get('take_profit')

        if side == 'long':
            # Long: SL si precio baja, TP si precio sube
            if current_price <= sl:
                logger.info(f"🛑 SL Triggered: {position['symbol']} @ ${current_price}")
                self._execute_market_close(position, current_price, 'stop_loss')
                return True

            if tp and current_price >= tp:
                logger.info(f"🎯 TP Triggered: {position['symbol']} @ ${current_price}")
                self._execute_market_close(position, current_price, 'take_profit')
                return True

        else:  # short
            # Short: SL si precio sube, TP si precio baja
            if current_price >= sl:
                logger.info(f"🛑 SL Triggered: {position['symbol']} @ ${current_price}")
                self._execute_market_close(position, current_price, 'stop_loss')
                return True

            if tp and current_price <= tp:
                logger.info(f"🎯 TP Triggered: {position['symbol']} @ ${current_price}")
                self._execute_market_close(position, current_price, 'take_profit')
                return True

        return False

    def _execute_market_close(self, position: Dict, price: float, reason: str):
        """Ejecuta cierre de posición con orden de mercado."""
        close_side = 'sell' if position['side'] == 'long' else 'buy'

        order = self.order_manager.place_market_close(
            symbol=position['symbol'],
            side=close_side,
            quantity=position['quantity'],
            reason=reason
        )

        exit_price = price
        if order and order.get('average'):
            exit_price = order['average']

        self.close_position(
            position_id=position['id'],
            exit_price=exit_price,
            exit_reason=reason,
            exit_order_id=order.get('id') if order else None
        )

    # =========================================================================
    # TRAILING STOP
    # =========================================================================

    def _check_trailing_stop(self, position: Dict, current_price: float):
        """Verifica y actualiza trailing stop si corresponde."""
        if not position.get('trailing_stop_active'):
            # Verificar si debe activarse
            if self._should_activate_trailing(position, current_price):
                self._activate_trailing_stop(position, current_price)
        else:
            # Ya activo: verificar si debe actualizarse
            self._update_trailing_stop_if_needed(position, current_price)

    def _should_activate_trailing(self, position: Dict, current_price: float) -> bool:
        """Verifica si se debe activar el trailing stop."""
        entry = position['entry_price']
        side = position['side']

        if side == 'long':
            profit_pct = ((current_price - entry) / entry) * 100
        else:
            profit_pct = ((entry - current_price) / entry) * 100

        return profit_pct >= self.trailing_activation

    def _activate_trailing_stop(self, position: Dict, current_price: float):
        """
        Activa trailing stop para una posición.

        v1.7: Añadida validación pre-trigger para evitar race conditions.
        El SL nunca se moverá a una posición que ya esté triggered.
        """
        position_id = position['id']
        side = position['side']
        symbol = position['symbol']

        # Calcular nuevo SL basado en trailing distance
        if side == 'long':
            new_sl = current_price * (1 - self.trailing_distance / 100)
        else:
            new_sl = current_price * (1 + self.trailing_distance / 100)

        # Solo mover si es mejor que el SL actual
        if side == 'long' and new_sl <= position['stop_loss']:
            return
        if side != 'long' and new_sl >= position['stop_loss']:
            return

        # v1.7 FIX CRÍTICO: Validación pre-trigger
        # Verificar que el nuevo SL no esté en posición de trigger inmediato
        if side == 'long' and current_price <= new_sl:
            logger.warning(f"⚠️ Trailing skip {symbol}: new SL ${new_sl:.2f} >= price ${current_price:.2f}")
            return
        if side == 'short' and current_price >= new_sl:
            logger.warning(f"⚠️ Trailing skip {symbol}: new SL ${new_sl:.2f} <= price ${current_price:.2f}")
            return

        # v1.8.1: Verificar margen de seguridad mínimo (configurable)
        min_safety_margin = current_price * self.trailing_safety_margin
        if side == 'long' and (new_sl + min_safety_margin) >= current_price:
            logger.warning(f"⚠️ Trailing skip {symbol}: SL too close (margin < {self.trailing_safety_margin*100:.1f}%)")
            return
        if side == 'short' and (new_sl - min_safety_margin) <= current_price:
            logger.warning(f"⚠️ Trailing skip {symbol}: SL too close (margin < {self.trailing_safety_margin*100:.1f}%)")
            return

        # Activar
        self.store.activate_trailing_stop(position_id, self.trailing_distance)
        position['trailing_stop_active'] = True
        position['trailing_stop_distance'] = self.trailing_distance
        position['last_sl_update_time'] = time.time()  # v1.7: Para cooldown

        # Actualizar SL
        self._update_stop_loss(position, new_sl, "trailing_activation")

        logger.info(f"📈 Trailing Stop ACTIVADO: {symbol}")
        logger.info(f"   Precio actual: ${current_price:.2f}")
        logger.info(f"   Nuevo SL: ${new_sl:.2f} (distancia: {self.trailing_distance}%)")
        logger.info(f"   Margen de seguridad: ${abs(current_price - new_sl):.2f} ({abs(current_price - new_sl)/current_price*100:.2f}%)")

    def _update_trailing_stop_if_needed(self, position: Dict, current_price: float):
        """
        Actualiza trailing stop si el precio se movió favorablemente.

        v1.7: Añadido cooldown y validaciones de seguridad.
        """
        side = position['side']
        current_sl = position['stop_loss']
        symbol = position['symbol']
        distance = position.get('trailing_stop_distance', self.trailing_distance)

        # v1.8.1: Cooldown configurable después de cada actualización de SL
        last_update = position.get('last_sl_update_time', 0)
        if time.time() - last_update < self.trailing_cooldown:
            return  # Aún en cooldown

        if side == 'long':
            # Long: mover SL arriba si precio sube
            new_sl = current_price * (1 - distance / 100)

            # v1.7: Validación pre-trigger
            if current_price <= new_sl:
                logger.debug(f"Trailing update skip {symbol}: price ${current_price:.2f} <= new SL ${new_sl:.2f}")
                return

            # v1.8.1: Margen de seguridad mínimo configurable
            min_safety_margin = current_price * self.trailing_safety_margin
            if (new_sl + min_safety_margin) >= current_price:
                return

            if new_sl > current_sl:
                position['last_sl_update_time'] = time.time()
                self._update_stop_loss(position, new_sl, "trailing_update")
                logger.debug(f"📈 Trailing SL updated {symbol}: ${current_sl:.2f} → ${new_sl:.2f}")
        else:
            # Short: mover SL abajo si precio baja
            new_sl = current_price * (1 + distance / 100)

            # v1.7: Validación pre-trigger
            if current_price >= new_sl:
                logger.debug(f"Trailing update skip {symbol}: price ${current_price:.2f} >= new SL ${new_sl:.2f}")
                return

            # v1.8.1: Margen de seguridad mínimo configurable
            min_safety_margin = current_price * self.trailing_safety_margin
            if (new_sl - min_safety_margin) <= current_price:
                return

            if new_sl < current_sl:
                position['last_sl_update_time'] = time.time()
                self._update_stop_loss(position, new_sl, "trailing_update")
                logger.debug(f"📈 Trailing SL updated {symbol}: ${current_sl:.2f} → ${new_sl:.2f}")

    def _update_stop_loss(self, position: Dict, new_sl: float, reason: str):
        """Actualiza el stop loss de una posición."""
        position_id = position['id']
        old_sl = position['stop_loss']

        # Actualizar en store
        self.store.update_stop_loss(position_id, new_sl)
        position['stop_loss'] = new_sl

        # Actualizar OCO si está en modo OCO
        if self.protection_mode == 'oco':
            close_side = 'sell' if position['side'] == 'long' else 'buy'
            self.order_manager.update_stop_loss(
                position_id=position_id,
                symbol=position['symbol'],
                side=close_side,
                quantity=position['quantity'],
                new_stop_loss=new_sl,
                take_profit_price=position.get('take_profit')
            )

        logger.debug(f"SL actualizado: {position['symbol']} ${old_sl:.2f} -> ${new_sl:.2f} ({reason})")

    # =========================================================================
    # PORTFOLIO MANAGEMENT
    # =========================================================================

    def can_open_position(self, symbol: str) -> bool:
        """
        Verifica si se puede abrir una nueva posición.
        Método público para verificar ANTES de ejecutar órdenes.

        Args:
            symbol: Símbolo a verificar

        Returns:
            True si se puede abrir, False si no
        """
        open_positions = self.store.get_open_positions()

        # Verificar límite de posiciones
        if len(open_positions) >= self.max_positions:
            logger.warning(f"Límite de posiciones alcanzado: {len(open_positions)}/{self.max_positions}")
            return False

        # Verificar si ya hay posición en este símbolo
        for pos in open_positions:
            if pos['symbol'] == symbol:
                logger.warning(f"Ya existe posición abierta en {symbol}")
                return False

        return True

    def get_portfolio_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del portfolio."""
        open_positions = self.store.get_open_positions()

        # Obtener precios actuales
        current_prices = {}
        total_pnl = 0
        total_exposure = 0

        for pos in open_positions:
            symbol = pos['symbol']
            price = self._get_current_price(symbol) or pos['entry_price']
            current_prices[symbol] = price

            # Calcular P&L
            entry = pos['entry_price']
            qty = pos['quantity']
            if pos['side'] == 'long':
                pnl = (price - entry) * qty
            else:
                pnl = (entry - price) * qty
            total_pnl += pnl
            total_exposure += price * qty

        return {
            'position_count': len(open_positions),
            'max_positions': self.max_positions,
            'total_exposure_usd': round(total_exposure, 2),
            'total_unrealized_pnl': round(total_pnl, 2),
            'positions': [
                {
                    'id': p['id'],
                    'symbol': p['symbol'],
                    'side': p['side'],
                    'entry': p['entry_price'],
                    'current': current_prices.get(p['symbol']),
                    'sl': p['stop_loss'],
                    'tp': p.get('take_profit')
                }
                for p in open_positions
            ]
        }

    # =========================================================================
    # RECOVERY
    # =========================================================================

    def recover_positions_on_startup(self) -> int:
        """
        Recupera posiciones abiertas al iniciar el bot.
        Valida que las posiciones realmente existan en el exchange.

        Returns:
            Número de posiciones recuperadas
        """
        try:
            open_positions = self.store.get_open_positions()

            if not open_positions:
                logger.info("No hay posiciones abiertas para recuperar")
                return 0

            logger.info(f"🔄 Recuperando {len(open_positions)} posiciones abiertas...")

            recovered = 0
            for pos in open_positions:
                symbol = pos['symbol']
                side = pos['side']
                quantity = pos['quantity']
                position_id = pos['id']

                logger.info(f"   Verificando {symbol} {side} @ ${pos['entry_price']:.2f}...")

                # v1.6: Validar que la posición realmente existe en el exchange
                is_valid = self._validate_position_exists(pos)

                if not is_valid:
                    logger.warning(f"   ⚠️ Posición {position_id} no válida en exchange")
                    logger.warning(f"   Marcando como cerrada (posiblemente ejecutada durante downtime)")

                    # Obtener precio actual para estimar cierre
                    current_price = self._get_current_price(symbol)
                    if current_price:
                        self.close_position(
                            position_id=position_id,
                            exit_price=current_price,
                            exit_reason='recovered_closed'
                        )
                    continue

                # Posición válida - agregar a memoria
                self.positions[position_id] = pos
                logger.info(f"   ✅ {symbol} {side} @ ${pos['entry_price']:.2f}")

                # Verificar si las órdenes de protección siguen activas
                if pos.get('oco_order_id') and self.protection_mode == 'oco':
                    status = self.order_manager.check_oco_status(position_id, symbol)
                    oco_status = status.get('status', 'unknown')

                    if oco_status == 'filled':
                        # OCO ejecutada - posición cerrada
                        logger.warning(f"   🔔 OCO ejecutada durante downtime")
                        exit_price = status.get('executed_price') or self._get_current_price(symbol)
                        self.close_position(
                            position_id=position_id,
                            exit_price=exit_price,
                            exit_reason=status.get('executed_side', 'oco_executed')
                        )
                        continue
                    elif oco_status not in ['active', 'unknown']:
                        logger.warning(f"   OCO no activa ({oco_status}), re-colocando...")
                        self._place_protection_orders(pos)

                recovered += 1

            if recovered > 0:
                logger.info(f"✅ {recovered} posiciones recuperadas")
            else:
                logger.info("No hay posiciones válidas para recuperar")

            return recovered

        except Exception as e:
            logger.error(f"Error recuperando posiciones: {e}")
            return 0

    def _validate_position_exists(self, position: Dict) -> bool:
        """
        Valida que una posición realmente existe en el exchange.
        Verifica el balance del activo correspondiente.

        Args:
            position: Datos de la posición

        Returns:
            True si la posición parece válida
        """
        try:
            symbol = position['symbol']
            side = position['side']
            quantity = position['quantity']
            base_asset = symbol.split('/')[0]  # BTC, ETH, SOL

            # Obtener balance real del activo
            balances = self.market_engine.get_balance()
            if not balances:
                logger.warning(f"No se pudo obtener balance - asumiendo posición válida")
                return True

            actual_balance = balances.get(base_asset, 0)

            # Para SHORT: vendimos el activo, deberíamos tener MENOS del activo
            # Para LONG: compramos el activo, deberíamos tener MÁS del activo
            if side == 'short':
                # En un short, necesitamos que el balance sea menor que antes de abrir
                # Pero no podemos saber el balance anterior, así que solo verificamos
                # que no haya señales de cierre
                # Si el balance aumentó significativamente, probablemente se cerró
                logger.debug(f"   Balance {base_asset}: {actual_balance}")
                return True  # Difícil validar shorts sin historial

            elif side == 'long':
                # En un long, deberíamos tener al menos la cantidad de la posición
                if actual_balance >= quantity * 0.95:  # 5% margen por fees
                    return True
                else:
                    logger.warning(f"   Balance {base_asset}: {actual_balance} < {quantity} esperado")
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error validando posición: {e}")
            return True  # En caso de error, asumir válida

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Obtiene precio actual de un símbolo."""
        try:
            # Primero intentar WebSocket si está disponible
            if self.websocket_engine:
                ws_price = self.websocket_engine.get_current_price(symbol)
                if ws_price:
                    return ws_price

            # Fallback a REST API via market_engine
            price = self.market_engine.get_current_price(symbol)
            if price:
                return price

            return None

        except Exception as e:
            logger.error(f"Error obteniendo precio de {symbol}: {e}")
            return None

    def _notify_position_created(self, position: Dict):
        """Notifica creación de posición."""
        if not self.notifier:
            return

        try:
            # La notificación de trade ejecutado ya se hace en main.py
            # Aquí solo loggeamos
            pass
        except Exception as e:
            logger.error(f"Error notificando posición creada: {e}")

    def _record_institutional_metrics(
        self,
        position: Dict,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        pnl_pct: float
    ):
        """
        v1.7: Registra métricas institucionales al cerrar posición.

        Incluye:
        - Trade en métricas institucionales
        - Resultado para Kelly Criterion (CRÍTICO para position sizing)
        """
        try:
            # Importar métricas institucionales
            try:
                from modules.institutional_metrics import get_institutional_metrics
                metrics = get_institutional_metrics()
            except ImportError:
                metrics = None

            if metrics:
                # Calcular hold time
                created_at = position.get('created_at')
                if created_at:
                    from datetime import datetime
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    hold_time_minutes = (datetime.now() - created_at).total_seconds() / 60
                else:
                    hold_time_minutes = 0

                # v1.7: Derivar régimen del agent_type
                agent_type = position.get('agent_type', 'general')
                if 'trend' in agent_type.lower():
                    regime = 'trend'
                elif 'reversal' in agent_type.lower():
                    regime = 'reversal'
                elif 'range' in agent_type.lower():
                    regime = 'range'
                else:
                    regime = position.get('regime', 'trend')  # Default a trend

                # v1.7: Calcular slippage real si tenemos precio de análisis
                analysis_price = position.get('analysis_price', position['entry_price'])
                actual_entry = position['entry_price']
                if analysis_price > 0:
                    slippage_pct = abs(actual_entry - analysis_price) / analysis_price * 100
                else:
                    slippage_pct = position.get('slippage_percent', 0)

                # Registrar trade
                metrics.record_trade(
                    symbol=position['symbol'],
                    side=position['side'],
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    entry_price=position['entry_price'],
                    exit_price=exit_price,
                    regime=regime,
                    agent_type=agent_type,
                    hold_time_minutes=int(hold_time_minutes),
                    latency_ms=position.get('execution_latency_ms', 0),
                    slippage_percent=slippage_pct
                )

                logger.debug(f"📊 Métricas institucionales registradas para {position['symbol']}")

            # v1.7 FIX CRÍTICO: Actualizar historial para Kelly Criterion
            # Esto es ESENCIAL para que el position sizing mejore con el tiempo
            self._update_risk_manager_history(pnl)

            # v1.7+: Registrar en Performance Attribution
            self._record_performance_attribution(
                position=position,
                pnl=pnl,
                pnl_pct=pnl_pct,
                hold_time_minutes=int(hold_time_minutes),
                exit_reason=exit_reason,
                regime=regime,
                agent_type=agent_type
            )

            # v1.7+: Actualizar Adaptive Parameters
            self._update_adaptive_params(pnl, pnl_pct, regime)

        except Exception as e:
            logger.error(f"Error registrando métricas institucionales: {e}")

    def _update_risk_manager_history(self, pnl: float):
        """
        v1.7: Actualiza el historial del Risk Manager para Kelly Criterion.
        CRÍTICO: Sin esto, Kelly usa probabilidad base 0.45 forever.
        """
        try:
            # Intentar obtener el singleton de RiskManager
            # Método 1: Buscar en el config path estándar
            import os
            import json

            state_file = 'data/risk_manager_state.json'
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)

                trade_history = state.get('trade_history', {
                    'wins': 0,
                    'losses': 0,
                    'total_win_amount': 0.0,
                    'total_loss_amount': 0.0
                })

                # Actualizar historial
                is_win = pnl > 0
                if is_win:
                    trade_history['wins'] += 1
                    trade_history['total_win_amount'] += abs(pnl)
                else:
                    trade_history['losses'] += 1
                    trade_history['total_loss_amount'] += abs(pnl)

                state['trade_history'] = trade_history

                # Guardar estado actualizado
                with open(state_file, 'w') as f:
                    json.dump(state, f, indent=2)

                total_trades = trade_history['wins'] + trade_history['losses']
                win_rate = trade_history['wins'] / total_trades if total_trades > 0 else 0
                logger.info(f"📈 Kelly History Updated: {trade_history['wins']}W/{trade_history['losses']}L = {win_rate*100:.1f}%")

        except Exception as e:
            logger.debug(f"No se pudo actualizar historial de Kelly: {e}")

    def _record_performance_attribution(
        self,
        position: Dict,
        pnl: float,
        pnl_pct: float,
        hold_time_minutes: int,
        exit_reason: str,
        regime: str,
        agent_type: str
    ):
        """
        v1.7+: Registra trade en Performance Attribution para análisis.

        Permite saber qué agente/régimen/hora genera más alpha.
        """
        try:
            from modules.performance_attribution import get_performance_attributor
            attributor = get_performance_attributor()

            if attributor:
                attributor.record_trade(
                    symbol=position['symbol'],
                    side=position['side'],
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    agent_type=agent_type,
                    regime=regime,
                    hold_time_minutes=hold_time_minutes,
                    exit_reason=exit_reason
                )
                logger.debug(f"📊 Performance attribution registrado para {position['symbol']}")

        except ImportError:
            pass  # Módulo no disponible
        except Exception as e:
            logger.debug(f"No se pudo registrar attribution: {e}")

    def _update_adaptive_params(self, pnl: float, pnl_pct: float, regime: str):
        """
        v1.7+: Actualiza los parámetros adaptativos con el resultado del trade.

        Esto permite que el bot ajuste automáticamente:
        - min_confidence (más selectivo después de pérdidas)
        - max_risk (reduce después de rachas perdedoras)
        - trailing_activation (según volatilidad)
        """
        try:
            from modules.adaptive_parameters import get_adaptive_manager
            manager = get_adaptive_manager()

            if manager:
                manager.record_trade_result(
                    symbol="",  # Ya no es necesario el símbolo específico
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    hold_time_minutes=0,  # Ya registrado en otra llamada
                    regime=regime
                )
                logger.debug(f"📈 Adaptive parameters actualizados")

        except ImportError:
            pass  # Módulo no disponible
        except Exception as e:
            logger.debug(f"No se pudieron actualizar params adaptativos: {e}")

    def _notify_position_closed(
        self,
        position: Dict,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        pnl_pct: float
    ):
        """Notifica cierre de posición."""
        if not self.notifier:
            return

        try:
            if exit_reason == 'stop_loss':
                self.notifier.notify_sl_hit(
                    symbol=position['symbol'],
                    entry_price=position['entry_price'],
                    exit_price=exit_price,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    position_id=position['id']
                )
            elif exit_reason == 'take_profit':
                self.notifier.notify_tp_hit(
                    symbol=position['symbol'],
                    entry_price=position['entry_price'],
                    exit_price=exit_price,
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    position_id=position['id']
                )
            else:
                self.notifier.notify_trade_closed(
                    symbol=position['symbol'],
                    side=position['side'],
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    reason=exit_reason
                )
        except Exception as e:
            logger.error(f"Error notificando cierre: {e}")

    def _calculate_hold_time(self, position: Dict) -> str:
        """Calcula tiempo de hold de una posición."""
        try:
            entry_time = datetime.fromisoformat(position['entry_time'])
            hold_seconds = (datetime.now() - entry_time).total_seconds()

            if hold_seconds < 3600:
                return f"{int(hold_seconds / 60)} min"
            elif hold_seconds < 86400:
                return f"{hold_seconds / 3600:.1f} hrs"
            else:
                return f"{hold_seconds / 86400:.1f} días"
        except:
            return "N/A"

    def get_position(self, position_id: str) -> Optional[Dict]:
        """Obtiene una posición por ID."""
        return self.positions.get(position_id) or self.store.get_position(position_id)

    def get_open_positions(self) -> List[Dict]:
        """Obtiene todas las posiciones abiertas."""
        return self.store.get_open_positions()
