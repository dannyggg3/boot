"""
Position Engine - Motor de gestión de posiciones
================================================
Coordinador central del ciclo de vida de posiciones:
- Creación de posiciones después de orden ejecutada
- Colocación de órdenes de protección (OCO/SL/TP)
- Monitoreo continuo de posiciones
- Trailing stop inteligente
- Cierre de posiciones y registro de resultados

Autor: Trading Bot System
Versión: 1.5
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

        # Trailing stop config
        ts_config = pm_config.get('trailing_stop', {})
        self.trailing_enabled = ts_config.get('enabled', True)
        self.trailing_activation = ts_config.get('activation_profit_percent', 1.0)
        self.trailing_distance = ts_config.get('trail_distance_percent', 2.0)

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
        """Activa trailing stop para una posición."""
        position_id = position['id']
        side = position['side']

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

        # Activar
        self.store.activate_trailing_stop(position_id, self.trailing_distance)
        position['trailing_stop_active'] = True
        position['trailing_stop_distance'] = self.trailing_distance

        # Actualizar SL
        self._update_stop_loss(position, new_sl, "trailing_activation")

        logger.info(f"📈 Trailing Stop ACTIVADO: {position['symbol']}")
        logger.info(f"   Nuevo SL: ${new_sl:.2f} (distancia: {self.trailing_distance}%)")

    def _update_trailing_stop_if_needed(self, position: Dict, current_price: float):
        """Actualiza trailing stop si el precio se movió favorablemente."""
        side = position['side']
        current_sl = position['stop_loss']
        distance = position.get('trailing_stop_distance', self.trailing_distance)

        if side == 'long':
            # Long: mover SL arriba si precio sube
            new_sl = current_price * (1 - distance / 100)
            if new_sl > current_sl:
                self._update_stop_loss(position, new_sl, "trailing_update")
        else:
            # Short: mover SL abajo si precio baja
            new_sl = current_price * (1 + distance / 100)
            if new_sl < current_sl:
                self._update_stop_loss(position, new_sl, "trailing_update")

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

        Returns:
            Número de posiciones recuperadas
        """
        try:
            open_positions = self.store.get_open_positions()

            if not open_positions:
                logger.info("No hay posiciones abiertas para recuperar")
                return 0

            logger.info(f"🔄 Recuperando {len(open_positions)} posiciones abiertas...")

            for pos in open_positions:
                self.positions[pos['id']] = pos
                logger.info(f"   {pos['symbol']} {pos['side']} @ ${pos['entry_price']:.2f}")

                # Verificar si las órdenes de protección siguen activas
                if pos.get('oco_order_id') and self.protection_mode == 'oco':
                    status = self.order_manager.check_oco_status(pos['id'], pos['symbol'])
                    if status.get('status') not in ['active', 'unknown']:
                        logger.warning(f"   OCO no activa, re-colocando...")
                        self._place_protection_orders(pos)

            logger.info("✅ Posiciones recuperadas")
            return len(open_positions)

        except Exception as e:
            logger.error(f"Error recuperando posiciones: {e}")
            return 0

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
