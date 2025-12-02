"""
Order Manager - Gestión de órdenes protectoras OCO/SL/TP
========================================================
Maneja la creación y monitoreo de órdenes de protección:
- OCO (One-Cancels-Other): SL + TP combinados
- Stop Loss Limit
- Take Profit Limit
- Actualización de Trailing Stop

Autor: Trading Bot System
Versión: 1.5
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Gestor de órdenes protectoras para posiciones abiertas.
    Soporta modo OCO (exchange) y modo local (bot monitorea).
    """

    def __init__(
        self,
        exchange_connection,
        config: Dict[str, Any],
        mode: str = "live"
    ):
        """
        Inicializa el Order Manager.

        Args:
            exchange_connection: Conexión CCXT al exchange
            config: Configuración del bot
            mode: 'live', 'paper', 'backtest'
        """
        self.exchange = exchange_connection
        self.config = config
        self.mode = mode

        # Configuración de position management
        pm_config = config.get('position_management', {})
        self.protection_mode = pm_config.get('protection_mode', 'oco')

        # OCO settings
        oco_config = pm_config.get('oco_settings', {})
        self.sl_limit_buffer = oco_config.get('sl_limit_buffer_percent', 0.2) / 100

        # Estado interno
        self.active_oco_orders: Dict[str, Dict] = {}  # position_id -> oco_info

        logger.info(f"OrderManager inicializado (modo: {self.protection_mode})")

    # =========================================================================
    # ÓRDENES OCO (One-Cancels-Other)
    # =========================================================================

    def place_oco_order(
        self,
        position_id: str,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Coloca una orden OCO que combina Take Profit y Stop Loss.
        Cuando una se ejecuta, la otra se cancela automáticamente.

        Args:
            position_id: ID de la posición a proteger
            symbol: Par de trading
            side: 'sell' para cerrar long, 'buy' para cerrar short
            quantity: Cantidad a vender/comprar
            take_profit_price: Precio límite del TP
            stop_loss_price: Precio trigger del SL

        Returns:
            Dict con IDs de órdenes o None si falla
        """
        if self.mode == 'backtest':
            return self._simulate_oco_order(position_id, symbol, side, quantity,
                                           take_profit_price, stop_loss_price)

        if self.mode == 'paper':
            logger.info(f"[PAPER] OCO Order: {symbol} {side} {quantity} | TP=${take_profit_price} SL=${stop_loss_price}")
            return {
                'position_id': position_id,
                'oco_id': f"paper_oco_{position_id}",
                'tp_order_id': f"paper_tp_{position_id}",
                'sl_order_id': f"paper_sl_{position_id}",
                'status': 'active',
                'mode': 'paper'
            }

        try:
            # Calcular precio límite del SL (ligeramente peor que trigger)
            if side == 'sell':
                # Para venta (cerrar long), SL limit es menor que trigger
                sl_limit_price = stop_loss_price * (1 - self.sl_limit_buffer)
            else:
                # Para compra (cerrar short), SL limit es mayor que trigger
                sl_limit_price = stop_loss_price * (1 + self.sl_limit_buffer)

            logger.info(f"Colocando OCO Order para {symbol}...")
            logger.info(f"  TP: ${take_profit_price:.2f}")
            logger.info(f"  SL Trigger: ${stop_loss_price:.2f}")
            logger.info(f"  SL Limit: ${sl_limit_price:.2f}")

            # Binance OCO order via CCXT
            # Nota: CCXT maneja esto internamente para Binance
            oco_result = self.exchange.create_oco_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=quantity,
                price=take_profit_price,
                stopPrice=stop_loss_price,
                stopLimitPrice=sl_limit_price,
                params={
                    'stopLimitTimeInForce': 'GTC',
                    'listClientOrderId': f'oco_{position_id}'
                }
            )

            # Extraer IDs de las órdenes
            oco_id = oco_result.get('orderListId') or oco_result.get('id')
            orders = oco_result.get('orders', [])

            tp_order_id = None
            sl_order_id = None

            for order in orders:
                order_type = order.get('type', '').upper()
                if 'LIMIT' in order_type and 'STOP' not in order_type:
                    tp_order_id = order.get('orderId') or order.get('id')
                elif 'STOP' in order_type:
                    sl_order_id = order.get('orderId') or order.get('id')

            result = {
                'position_id': position_id,
                'oco_id': str(oco_id),
                'tp_order_id': str(tp_order_id) if tp_order_id else None,
                'sl_order_id': str(sl_order_id) if sl_order_id else None,
                'status': 'active',
                'take_profit_price': take_profit_price,
                'stop_loss_price': stop_loss_price,
                'created_at': datetime.now().isoformat()
            }

            # Guardar referencia
            self.active_oco_orders[position_id] = result

            logger.info(f"✅ OCO Order creada: {oco_id}")
            logger.info(f"   TP Order: {tp_order_id}")
            logger.info(f"   SL Order: {sl_order_id}")

            return result

        except Exception as e:
            logger.error(f"Error creando OCO order: {e}")

            # Intentar método alternativo: órdenes separadas
            logger.info("Intentando colocar órdenes SL y TP por separado...")
            return self._place_separate_sl_tp(
                position_id, symbol, side, quantity,
                take_profit_price, stop_loss_price
            )

    def _place_separate_sl_tp(
        self,
        position_id: str,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback: Coloca SL y TP como órdenes separadas.
        Menos ideal que OCO pero funciona si OCO no está disponible.
        """
        try:
            # Calcular SL limit
            if side == 'sell':
                sl_limit_price = stop_loss_price * (1 - self.sl_limit_buffer)
            else:
                sl_limit_price = stop_loss_price * (1 + self.sl_limit_buffer)

            # Stop Loss Order
            sl_order = self.exchange.create_order(
                symbol=symbol,
                type='STOP_LOSS_LIMIT',
                side=side,
                amount=quantity,
                price=sl_limit_price,
                params={
                    'stopPrice': stop_loss_price,
                    'timeInForce': 'GTC'
                }
            )
            sl_order_id = sl_order.get('id')
            logger.info(f"SL Order creada: {sl_order_id}")

            # Take Profit Order (limit normal)
            tp_order = self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=quantity,
                price=take_profit_price,
                params={'timeInForce': 'GTC'}
            )
            tp_order_id = tp_order.get('id')
            logger.info(f"TP Order creada: {tp_order_id}")

            result = {
                'position_id': position_id,
                'oco_id': None,  # No es OCO real
                'tp_order_id': str(tp_order_id),
                'sl_order_id': str(sl_order_id),
                'status': 'active',
                'is_separate': True,  # Flag para saber que no es OCO real
                'take_profit_price': take_profit_price,
                'stop_loss_price': stop_loss_price,
                'created_at': datetime.now().isoformat()
            }

            self.active_oco_orders[position_id] = result
            return result

        except Exception as e:
            logger.error(f"Error creando órdenes separadas: {e}")
            return None

    def cancel_oco_order(self, position_id: str, symbol: str) -> bool:
        """
        Cancela una orden OCO o sus órdenes componentes.

        Args:
            position_id: ID de la posición
            symbol: Par de trading

        Returns:
            True si se canceló correctamente
        """
        if self.mode in ['paper', 'backtest']:
            logger.info(f"[{self.mode.upper()}] OCO cancelada para {position_id}")
            self.active_oco_orders.pop(position_id, None)
            return True

        oco_info = self.active_oco_orders.get(position_id)
        if not oco_info:
            logger.warning(f"No hay OCO activa para posición {position_id}")
            return False

        try:
            if oco_info.get('oco_id') and not oco_info.get('is_separate'):
                # Cancelar OCO completa
                self.exchange.cancel_order(
                    oco_info['oco_id'],
                    symbol,
                    params={'type': 'oco'}
                )
                logger.info(f"OCO {oco_info['oco_id']} cancelada")
            else:
                # Cancelar órdenes separadas
                if oco_info.get('tp_order_id'):
                    try:
                        self.exchange.cancel_order(oco_info['tp_order_id'], symbol)
                        logger.info(f"TP Order {oco_info['tp_order_id']} cancelada")
                    except Exception as e:
                        logger.warning(f"Error cancelando TP: {e}")

                if oco_info.get('sl_order_id'):
                    try:
                        self.exchange.cancel_order(oco_info['sl_order_id'], symbol)
                        logger.info(f"SL Order {oco_info['sl_order_id']} cancelada")
                    except Exception as e:
                        logger.warning(f"Error cancelando SL: {e}")

            self.active_oco_orders.pop(position_id, None)
            return True

        except Exception as e:
            logger.error(f"Error cancelando OCO: {e}")
            return False

    def update_stop_loss(
        self,
        position_id: str,
        symbol: str,
        side: str,
        quantity: float,
        new_stop_loss: float,
        take_profit_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza el stop loss de una posición.
        Cancela la OCO existente y crea una nueva con el SL actualizado.

        Args:
            position_id: ID de la posición
            symbol: Par de trading
            side: Lado de la orden de cierre
            quantity: Cantidad
            new_stop_loss: Nuevo precio de stop loss
            take_profit_price: Precio de TP (si no se pasa, usa el existente)

        Returns:
            Nueva información de OCO o None si falla
        """
        oco_info = self.active_oco_orders.get(position_id)

        # Obtener TP existente si no se proporciona
        if take_profit_price is None and oco_info:
            take_profit_price = oco_info.get('take_profit_price')

        if not take_profit_price:
            logger.error(f"No se puede actualizar SL: falta take_profit_price")
            return None

        # Cancelar OCO existente
        if oco_info:
            self.cancel_oco_order(position_id, symbol)

        # Crear nueva OCO con SL actualizado
        return self.place_oco_order(
            position_id=position_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            take_profit_price=take_profit_price,
            stop_loss_price=new_stop_loss
        )

    def update_take_profit(
        self,
        position_id: str,
        symbol: str,
        side: str,
        quantity: float,
        new_take_profit: float,
        stop_loss_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza el take profit de una posición.
        """
        oco_info = self.active_oco_orders.get(position_id)

        if stop_loss_price is None and oco_info:
            stop_loss_price = oco_info.get('stop_loss_price')

        if not stop_loss_price:
            logger.error(f"No se puede actualizar TP: falta stop_loss_price")
            return None

        if oco_info:
            self.cancel_oco_order(position_id, symbol)

        return self.place_oco_order(
            position_id=position_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            take_profit_price=new_take_profit,
            stop_loss_price=stop_loss_price
        )

    # =========================================================================
    # MONITOREO DE ÓRDENES
    # =========================================================================

    def check_oco_status(self, position_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Verifica el estado de una OCO order.

        Returns:
            Dict con estado: 'active', 'tp_filled', 'sl_filled', 'cancelled', 'unknown'
        """
        if self.mode in ['paper', 'backtest']:
            return {'status': 'active', 'mode': self.mode}

        oco_info = self.active_oco_orders.get(position_id)
        if not oco_info:
            return {'status': 'unknown', 'error': 'OCO not found'}

        try:
            result = {'status': 'active'}

            # Verificar TP order
            if oco_info.get('tp_order_id'):
                tp_order = self.exchange.fetch_order(oco_info['tp_order_id'], symbol)
                tp_status = tp_order.get('status', 'unknown')

                if tp_status == 'closed':
                    result['status'] = 'tp_filled'
                    result['fill_price'] = tp_order.get('average') or tp_order.get('price')
                    result['filled_at'] = tp_order.get('datetime')
                    return result
                elif tp_status == 'canceled':
                    # Si TP fue cancelada, verificar si SL se ejecutó
                    pass

            # Verificar SL order
            if oco_info.get('sl_order_id'):
                sl_order = self.exchange.fetch_order(oco_info['sl_order_id'], symbol)
                sl_status = sl_order.get('status', 'unknown')

                if sl_status == 'closed':
                    result['status'] = 'sl_filled'
                    result['fill_price'] = sl_order.get('average') or sl_order.get('price')
                    result['filled_at'] = sl_order.get('datetime')
                    return result
                elif sl_status == 'canceled':
                    # Ambas canceladas
                    if result.get('status') != 'tp_filled':
                        result['status'] = 'cancelled'

            return result

        except Exception as e:
            logger.error(f"Error verificando OCO status: {e}")
            return {'status': 'error', 'error': str(e)}

    def get_active_orders_for_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de órdenes activas para una posición."""
        return self.active_oco_orders.get(position_id)

    # =========================================================================
    # ÓRDENES INDIVIDUALES (para modo local o actualizaciones)
    # =========================================================================

    def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Coloca una orden de Stop Loss individual.

        Args:
            symbol: Par de trading
            side: 'sell' o 'buy'
            quantity: Cantidad
            stop_price: Precio de activación
            limit_price: Precio límite (si None, usa stop_price con buffer)

        Returns:
            Información de la orden o None
        """
        if self.mode == 'paper':
            logger.info(f"[PAPER] SL Order: {symbol} {side} {quantity} @ ${stop_price}")
            return {'id': f'paper_sl_{int(time.time())}', 'status': 'open'}

        try:
            if limit_price is None:
                if side == 'sell':
                    limit_price = stop_price * (1 - self.sl_limit_buffer)
                else:
                    limit_price = stop_price * (1 + self.sl_limit_buffer)

            order = self.exchange.create_order(
                symbol=symbol,
                type='STOP_LOSS_LIMIT',
                side=side,
                amount=quantity,
                price=limit_price,
                params={
                    'stopPrice': stop_price,
                    'timeInForce': 'GTC'
                }
            )

            logger.info(f"SL Order creada: {order.get('id')} @ ${stop_price}")
            return order

        except Exception as e:
            logger.error(f"Error creando SL order: {e}")
            return None

    def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Coloca una orden de Take Profit (limit).

        Args:
            symbol: Par de trading
            side: 'sell' o 'buy'
            quantity: Cantidad
            price: Precio de TP

        Returns:
            Información de la orden o None
        """
        if self.mode == 'paper':
            logger.info(f"[PAPER] TP Order: {symbol} {side} {quantity} @ ${price}")
            return {'id': f'paper_tp_{int(time.time())}', 'status': 'open'}

        try:
            order = self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=quantity,
                price=price,
                params={'timeInForce': 'GTC'}
            )

            logger.info(f"TP Order creada: {order.get('id')} @ ${price}")
            return order

        except Exception as e:
            logger.error(f"Error creando TP order: {e}")
            return None

    def place_market_close(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reason: str = "manual"
    ) -> Optional[Dict[str, Any]]:
        """
        Cierra una posición con orden de mercado.

        Args:
            symbol: Par de trading
            side: 'sell' para cerrar long, 'buy' para cerrar short
            quantity: Cantidad a cerrar
            reason: Razón del cierre

        Returns:
            Información de la orden o None
        """
        if self.mode == 'paper':
            logger.info(f"[PAPER] Market Close: {symbol} {side} {quantity} ({reason})")
            return {'id': f'paper_close_{int(time.time())}', 'status': 'closed', 'reason': reason}

        try:
            if side == 'sell':
                order = self.exchange.create_market_sell_order(symbol, quantity)
            else:
                order = self.exchange.create_market_buy_order(symbol, quantity)

            logger.info(f"Market Close ejecutada: {order.get('id')} ({reason})")
            return order

        except Exception as e:
            logger.error(f"Error en market close: {e}")
            return None

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _simulate_oco_order(
        self,
        position_id: str,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> Dict[str, Any]:
        """Simula OCO order para backtest."""
        return {
            'position_id': position_id,
            'oco_id': f"sim_oco_{position_id}",
            'tp_order_id': f"sim_tp_{position_id}",
            'sl_order_id': f"sim_sl_{position_id}",
            'status': 'active',
            'take_profit_price': take_profit_price,
            'stop_loss_price': stop_loss_price,
            'mode': 'backtest'
        }

    def get_all_active_orders(self) -> Dict[str, Dict]:
        """Retorna todas las órdenes OCO activas."""
        return self.active_oco_orders.copy()

    def cleanup_completed_orders(self):
        """Limpia órdenes completadas del tracking interno."""
        to_remove = []
        for pos_id, oco_info in self.active_oco_orders.items():
            if oco_info.get('status') in ['tp_filled', 'sl_filled', 'cancelled']:
                to_remove.append(pos_id)

        for pos_id in to_remove:
            del self.active_oco_orders[pos_id]

        if to_remove:
            logger.debug(f"Limpiadas {len(to_remove)} órdenes completadas")
