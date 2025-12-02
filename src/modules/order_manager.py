"""
Order Manager - Gestión de órdenes protectoras OCO/SL/TP
========================================================
Maneja la creación y monitoreo de órdenes de protección:
- OCO (One-Cancels-Other): SL + TP combinados
- Stop Loss Limit
- Take Profit Limit
- Actualización de Trailing Stop

v1.7: Añadida simulación de latencia y slippage para paper mode

Autor: Trading Bot System
Versión: 1.7
"""

import logging
import time
import random
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# v1.7: SIMULACIÓN DE CONDICIONES REALES PARA PAPER MODE
# ============================================================================

class PaperModeSimulator:
    """
    Simula condiciones reales de mercado para paper trading.
    Incluye latencia, slippage y fallos ocasionales.
    """

    def __init__(self, config: Dict[str, Any] = None):
        sim_config = (config or {}).get('paper_simulation', {})

        # Latencia de red (ms)
        self.min_latency_ms = sim_config.get('min_latency_ms', 50)
        self.max_latency_ms = sim_config.get('max_latency_ms', 200)

        # Slippage (%)
        self.base_slippage_percent = sim_config.get('base_slippage_percent', 0.05)
        self.max_slippage_percent = sim_config.get('max_slippage_percent', 0.15)

        # Probabilidad de fallos
        self.failure_rate = sim_config.get('failure_rate', 0.02)  # 2% de fallos

        # Estadísticas
        self.stats = {
            'total_orders': 0,
            'total_latency_ms': 0,
            'total_slippage_usd': 0,
            'failures': 0
        }

    def simulate_latency(self):
        """Simula latencia de red."""
        latency_ms = random.uniform(self.min_latency_ms, self.max_latency_ms)
        time.sleep(latency_ms / 1000)
        self.stats['total_latency_ms'] += latency_ms
        return latency_ms

    def calculate_slippage(self, price: float, side: str, volatility: float = 1.0) -> float:
        """
        Calcula slippage basado en condiciones de mercado.

        Args:
            price: Precio objetivo
            side: 'buy' o 'sell'
            volatility: Factor de volatilidad (1.0 = normal)

        Returns:
            Precio ajustado con slippage
        """
        # Slippage base + componente aleatorio
        slippage_percent = self.base_slippage_percent + random.uniform(0, self.max_slippage_percent - self.base_slippage_percent)

        # Ajustar por volatilidad
        slippage_percent *= volatility

        # Dirección del slippage (siempre desfavorable)
        if side == 'buy':
            adjusted_price = price * (1 + slippage_percent / 100)
        else:
            adjusted_price = price * (1 - slippage_percent / 100)

        slippage_usd = abs(adjusted_price - price)
        self.stats['total_slippage_usd'] += slippage_usd

        return adjusted_price

    def should_fail(self) -> bool:
        """Determina si la orden debe fallar (simula problemas de red)."""
        if random.random() < self.failure_rate:
            self.stats['failures'] += 1
            return True
        return False

    def process_order(self, price: float, side: str, order_type: str = 'market') -> Dict[str, Any]:
        """
        Procesa una orden simulando condiciones reales.

        Returns:
            Dict con precio ajustado, latencia y estado
        """
        self.stats['total_orders'] += 1

        # Simular latencia
        latency = self.simulate_latency()

        # Verificar fallo
        if self.should_fail():
            return {
                'success': False,
                'error': 'Simulated network timeout',
                'latency_ms': latency
            }

        # Calcular slippage (solo para market orders)
        if order_type == 'market':
            adjusted_price = self.calculate_slippage(price, side)
        else:
            adjusted_price = price

        return {
            'success': True,
            'original_price': price,
            'executed_price': adjusted_price,
            'slippage_percent': abs(adjusted_price - price) / price * 100,
            'latency_ms': latency
        }

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de simulación."""
        total = self.stats['total_orders']
        return {
            'total_orders': total,
            'avg_latency_ms': self.stats['total_latency_ms'] / total if total > 0 else 0,
            'total_slippage_usd': round(self.stats['total_slippage_usd'], 4),
            'failure_rate_actual': self.stats['failures'] / total * 100 if total > 0 else 0
        }


# Instancia global del simulador
_paper_simulator: Optional[PaperModeSimulator] = None


def get_paper_simulator(config: Dict = None) -> PaperModeSimulator:
    """Obtiene o crea el simulador de paper mode."""
    global _paper_simulator
    if _paper_simulator is None:
        _paper_simulator = PaperModeSimulator(config)
    return _paper_simulator


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

        # v1.7: Simulador para paper mode
        self.paper_simulator = None
        if mode == 'paper':
            self.paper_simulator = get_paper_simulator(config)
            logger.info(f"  Paper Mode Simulator: ACTIVO (slippage: {self.paper_simulator.base_slippage_percent}-{self.paper_simulator.max_slippage_percent}%)")

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
        reason: str = "manual",
        current_price: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cierra una posición con orden de mercado.

        Args:
            symbol: Par de trading
            side: 'sell' para cerrar long, 'buy' para cerrar short
            quantity: Cantidad a cerrar
            reason: Razón del cierre
            current_price: v1.7 - Precio actual para simulación de slippage

        Returns:
            Información de la orden o None
        """
        if self.mode == 'paper':
            # v1.7: Simulación realista con latencia y slippage
            if self.paper_simulator and current_price:
                sim_result = self.paper_simulator.process_order(current_price, side, 'market')

                if not sim_result['success']:
                    logger.warning(f"[PAPER] Market Close FAILED (simulated): {sim_result['error']}")
                    # Reintentar una vez
                    time.sleep(0.5)
                    sim_result = self.paper_simulator.process_order(current_price, side, 'market')

                executed_price = sim_result.get('executed_price', current_price)
                slippage = sim_result.get('slippage_percent', 0)
                latency = sim_result.get('latency_ms', 0)

                logger.info(f"[PAPER] Market Close: {symbol} {side} {quantity} ({reason})")
                logger.info(f"  Precio: ${current_price:.2f} → ${executed_price:.2f} (slippage: {slippage:.3f}%)")
                logger.info(f"  Latencia: {latency:.0f}ms")

                return {
                    'id': f'paper_close_{int(time.time())}',
                    'status': 'closed',
                    'reason': reason,
                    'average': executed_price,
                    'price': executed_price,
                    'slippage_percent': slippage,
                    'latency_ms': latency
                }
            else:
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

    def get_simulation_stats(self) -> Optional[Dict[str, Any]]:
        """v1.7: Obtiene estadísticas de simulación de paper mode."""
        if self.paper_simulator:
            return self.paper_simulator.get_stats()
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
