"""
Market Engine - Motor de Conexión con Mercados
===============================================
Este módulo gestiona la conexión con exchanges de crypto (Binance, Bybit)
y brokers tradicionales (Interactive Brokers) para ejecutar operaciones.

Autor: Trading Bot System
Versión: 1.0
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import ccxt
from ib_insync import IB, Stock, Forex, MarketOrder, LimitOrder, util
from dotenv import load_dotenv
import yaml

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)


class MarketEngine:
    """
    Motor de mercado que soporta múltiples exchanges y brokers.
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Inicializa el motor de mercado.

        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.config = self._load_config(config_path)
        self.market_type = self.config['market_type']
        self.connection = None
        self.mode = self.config['trading']['mode']  # live, paper, backtest

        # Estado del portfolio
        self.positions = {}
        self.balance = {}

        # Configuración de protección contra slippage
        trading_config = self.config.get('trading', {})

        # Verificación pre-ejecución
        price_verification = trading_config.get('price_verification', {})
        self.price_verification_enabled = price_verification.get('enabled', True)
        self.max_price_deviation = price_verification.get('max_deviation_percent', 0.5) / 100

        # Órdenes limit
        order_execution = trading_config.get('order_execution', {})
        self.use_limit_orders = order_execution.get('use_limit_orders', True)
        self.max_slippage = order_execution.get('max_slippage_percent', 0.3) / 100
        self.limit_order_timeout = order_execution.get('limit_order_timeout', 30)
        self.on_timeout = order_execution.get('on_timeout', 'cancel')

        self._initialize_connection()
        logger.info(f"Market Engine inicializado: {self.market_type} - Modo: {self.mode}")
        logger.info(f"Protección slippage: verificación={self.price_verification_enabled}, limit_orders={self.use_limit_orders}")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga la configuración desde el archivo YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            raise

    def _initialize_connection(self):
        """Inicializa la conexión con el exchange o broker correspondiente."""
        try:
            if self.market_type == 'crypto':
                self._initialize_crypto_exchange()
            elif self.market_type == 'forex_stocks':
                self._initialize_interactive_brokers()
            else:
                raise ValueError(f"Tipo de mercado no soportado: {self.market_type}")

        except Exception as e:
            logger.error(f"Error inicializando conexión de mercado: {e}")
            raise

    def _initialize_crypto_exchange(self):
        """Inicializa la conexión con exchanges de criptomonedas."""
        # Por defecto usamos Binance, pero es configurable
        exchange_config = self.config.get('exchanges', {})

        if exchange_config.get('binance', {}).get('enabled', True):
            exchange_name = 'binance'
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')

            if self.mode == 'paper':
                logger.info("Modo PAPER TRADING - Usando Binance Testnet")
                self.connection = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',  # spot, future, margin
                        'testnet': True if exchange_config.get('binance', {}).get('testnet') else False
                    }
                })
            else:
                self.connection = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'
                    }
                })

            # Verificar conexión
            self.connection.load_markets()
            logger.info(f"Conectado a {exchange_name.upper()} - {len(self.connection.markets)} mercados disponibles")

        elif exchange_config.get('bybit', {}).get('enabled', False):
            api_key = os.getenv('BYBIT_API_KEY')
            api_secret = os.getenv('BYBIT_API_SECRET')

            self.connection = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True
            })
            self.connection.load_markets()
            logger.info("Conectado a BYBIT")

        else:
            raise ValueError("No hay ningún exchange de crypto habilitado en la configuración")

    def _initialize_interactive_brokers(self):
        """Inicializa la conexión con Interactive Brokers."""
        ib_config = self.config.get('interactive_brokers', {})

        if not ib_config.get('enabled', False):
            raise ValueError("Interactive Brokers no está habilitado en la configuración")

        host = ib_config.get('host', '127.0.0.1')
        port = ib_config.get('port', 7497)
        client_id = ib_config.get('client_id', 1)

        self.connection = IB()

        try:
            self.connection.connect(host, port, clientId=client_id)
            logger.info(f"Conectado a Interactive Brokers en {host}:{port}")
            logger.info(f"Modo: {'PAPER' if port == 7497 else 'LIVE'}")

        except Exception as e:
            logger.error(f"Error conectando a IBKR: {e}")
            logger.error("Asegúrate de que TWS o IB Gateway esté ejecutándose")
            raise

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Obtiene el precio actual de un símbolo.

        Args:
            symbol: Símbolo del activo (ej. 'BTC/USDT' o 'AAPL')

        Returns:
            Precio actual o None si hay error
        """
        try:
            if self.market_type == 'crypto':
                ticker = self.connection.fetch_ticker(symbol)
                return ticker['last']

            elif self.market_type == 'forex_stocks':
                contract = self._create_ib_contract(symbol)
                ticker = self.connection.reqMktData(contract, '', False, False)
                self.connection.sleep(1)  # Esperar a que lleguen los datos
                price = ticker.marketPrice()
                return price if price > 0 else None

        except Exception as e:
            logger.error(f"Error obteniendo precio de {symbol}: {e}")
            return None

    def verify_price_for_execution(
        self,
        symbol: str,
        analysis_price: float,
        side: str
    ) -> Dict[str, Any]:
        """
        Verifica si el precio actual está dentro del rango aceptable para ejecutar.

        Args:
            symbol: Símbolo del activo
            analysis_price: Precio al momento del análisis
            side: 'buy' o 'sell'

        Returns:
            Dict con 'approved', 'current_price', 'deviation_percent', 'reason'
        """
        if not self.price_verification_enabled:
            return {
                'approved': True,
                'current_price': analysis_price,
                'deviation_percent': 0,
                'reason': 'Verificación deshabilitada'
            }

        current_price = self.get_current_price(symbol)

        if current_price is None:
            return {
                'approved': False,
                'current_price': None,
                'deviation_percent': None,
                'reason': 'No se pudo obtener precio actual'
            }

        # Calcular desviación
        deviation = (current_price - analysis_price) / analysis_price
        deviation_percent = abs(deviation) * 100

        # Para COMPRA: precio subió mucho = malo (comprarías más caro)
        # Para VENTA: precio bajó mucho = malo (venderías más barato)
        is_unfavorable = (side == 'buy' and deviation > 0) or (side == 'sell' and deviation < 0)

        if abs(deviation) > self.max_price_deviation:
            direction = "subió" if deviation > 0 else "bajó"
            return {
                'approved': False,
                'current_price': current_price,
                'deviation_percent': deviation_percent,
                'reason': f'Precio {direction} {deviation_percent:.2f}% (máx: {self.max_price_deviation*100:.2f}%)',
                'is_unfavorable': is_unfavorable
            }

        return {
            'approved': True,
            'current_price': current_price,
            'deviation_percent': deviation_percent,
            'reason': f'Desviación aceptable: {deviation_percent:.2f}%',
            'is_unfavorable': is_unfavorable
        }

    def calculate_limit_price(
        self,
        current_price: float,
        side: str
    ) -> float:
        """
        Calcula el precio límite con slippage para la orden.

        Args:
            current_price: Precio actual del mercado
            side: 'buy' o 'sell'

        Returns:
            Precio límite ajustado
        """
        if side == 'buy':
            # Para compra: dispuestos a pagar un poco más
            return current_price * (1 + self.max_slippage)
        else:
            # Para venta: dispuestos a recibir un poco menos
            return current_price * (1 - self.max_slippage)

    def get_historical_data(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100
    ) -> Optional[List[List]]:
        """
        Obtiene datos históricos (OHLCV).

        Args:
            symbol: Símbolo del activo
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Número de velas a obtener

        Returns:
            Lista de velas [timestamp, open, high, low, close, volume]
        """
        try:
            if self.market_type == 'crypto':
                ohlcv = self.connection.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    limit=limit
                )
                return ohlcv

            elif self.market_type == 'forex_stocks':
                contract = self._create_ib_contract(symbol)
                bars = self.connection.reqHistoricalData(
                    contract,
                    endDateTime='',
                    durationStr=f'{limit} D',
                    barSizeSetting=self._convert_timeframe_ib(timeframe),
                    whatToShow='MIDPOINT',
                    useRTH=True
                )

                # Convertir a formato compatible
                ohlcv = []
                for bar in bars:
                    ohlcv.append([
                        int(bar.date.timestamp() * 1000),
                        bar.open,
                        bar.high,
                        bar.low,
                        bar.close,
                        bar.volume
                    ])
                return ohlcv

        except Exception as e:
            logger.error(f"Error obteniendo datos históricos de {symbol}: {e}")
            return None

    def execute_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = 'market',
        price: Optional[float] = None,
        analysis_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta una orden en el mercado con protección contra slippage.

        Args:
            symbol: Símbolo del activo
            side: 'buy' o 'sell'
            amount: Cantidad a operar
            order_type: 'market' o 'limit' (se puede sobrescribir por config)
            price: Precio límite (solo para órdenes limit manuales)
            analysis_price: Precio al momento del análisis (para verificación)

        Returns:
            Información de la orden ejecutada
        """
        if self.mode == 'backtest':
            logger.info(f"BACKTEST MODE - Simulando orden: {side} {amount} {symbol}")
            return {
                'id': f'backtest_{datetime.now().timestamp()}',
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'status': 'simulated'
            }

        # Verificación pre-ejecución de precio
        if analysis_price and self.price_verification_enabled:
            verification = self.verify_price_for_execution(symbol, analysis_price, side)
            if not verification['approved']:
                logger.warning(f"⚠️ ORDEN ABORTADA: {verification['reason']}")
                logger.warning(f"Precio análisis: {analysis_price} | Precio actual: {verification['current_price']}")
                return {
                    'id': None,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'status': 'aborted',
                    'reason': verification['reason'],
                    'price_deviation': verification['deviation_percent']
                }
            logger.info(f"✅ Verificación de precio OK: {verification['reason']}")

        # Determinar tipo de orden final
        final_order_type = order_type
        limit_price = price

        # Si está configurado para usar limit orders y no se especificó precio
        if self.use_limit_orders and order_type == 'market' and price is None:
            final_order_type = 'limit'
            current_price = self.get_current_price(symbol)
            if current_price:
                limit_price = self.calculate_limit_price(current_price, side)
                logger.info(f"Convirtiendo a orden LIMIT: precio={limit_price:.8f} (slippage={self.max_slippage*100:.2f}%)")

        try:
            if self.market_type == 'crypto':
                result = self._execute_crypto_order(symbol, side, amount, final_order_type, limit_price)

                # Si es orden limit, monitorear hasta que se llene o timeout
                if final_order_type == 'limit' and result and result.get('id'):
                    result = self._monitor_limit_order(symbol, result['id'], side, amount)

                return result

            elif self.market_type == 'forex_stocks':
                return self._execute_ib_order(symbol, side, amount, final_order_type, limit_price)

        except Exception as e:
            logger.error(f"Error ejecutando orden: {e}")
            return None

    def _monitor_limit_order(
        self,
        symbol: str,
        order_id: str,
        side: str,
        amount: float
    ) -> Dict[str, Any]:
        """
        Monitorea una orden limit hasta que se llene o expire.

        Args:
            symbol: Símbolo del activo
            order_id: ID de la orden
            side: 'buy' o 'sell'
            amount: Cantidad ordenada

        Returns:
            Estado final de la orden
        """
        start_time = time.time()
        logger.info(f"Monitoreando orden limit {order_id} (timeout: {self.limit_order_timeout}s)")

        while time.time() - start_time < self.limit_order_timeout:
            try:
                order = self.connection.fetch_order(order_id, symbol)
                status = order.get('status', 'unknown')

                if status == 'closed':
                    logger.info(f"✅ Orden limit {order_id} ejecutada completamente")
                    return order

                if status == 'canceled':
                    logger.warning(f"❌ Orden limit {order_id} cancelada externamente")
                    return order

                # Orden parcialmente llena
                filled = order.get('filled', 0)
                if filled > 0:
                    logger.info(f"Orden {order_id}: {filled}/{amount} llenada...")

                time.sleep(2)  # Esperar 2 segundos antes de verificar de nuevo

            except Exception as e:
                logger.error(f"Error monitoreando orden: {e}")
                break

        # Timeout alcanzado
        logger.warning(f"⏱️ Timeout alcanzado para orden {order_id}")

        if self.on_timeout == 'cancel':
            try:
                self.connection.cancel_order(order_id, symbol)
                logger.info(f"Orden {order_id} cancelada por timeout")
                return {
                    'id': order_id,
                    'symbol': symbol,
                    'side': side,
                    'amount': amount,
                    'status': 'canceled',
                    'reason': 'timeout'
                }
            except Exception as e:
                logger.error(f"Error cancelando orden: {e}")

        elif self.on_timeout == 'market':
            logger.info(f"Convirtiendo orden {order_id} a MARKET")
            try:
                # Cancelar orden limit
                self.connection.cancel_order(order_id, symbol)
                # Ejecutar como market
                return self._execute_crypto_order(symbol, side, amount, 'market', None)
            except Exception as e:
                logger.error(f"Error convirtiendo a market: {e}")

        return {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'status': 'timeout'
        }

    def _execute_crypto_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str,
        price: Optional[float]
    ) -> Dict[str, Any]:
        """Ejecuta orden en exchange de crypto."""
        if order_type == 'market':
            if side == 'buy':
                order = self.connection.create_market_buy_order(symbol, amount)
            else:
                order = self.connection.create_market_sell_order(symbol, amount)
        elif order_type == 'limit':
            if not price:
                raise ValueError("Se requiere precio para órdenes limit")
            if side == 'buy':
                order = self.connection.create_limit_buy_order(symbol, amount, price)
            else:
                order = self.connection.create_limit_sell_order(symbol, amount, price)

        logger.info(f"Orden ejecutada: {order['id']} - {side} {amount} {symbol}")
        return order

    def _execute_ib_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str,
        price: Optional[float]
    ) -> Dict[str, Any]:
        """Ejecuta orden en Interactive Brokers."""
        contract = self._create_ib_contract(symbol)
        action = 'BUY' if side == 'buy' else 'SELL'

        if order_type == 'market':
            order = MarketOrder(action, amount)
        elif order_type == 'limit':
            if not price:
                raise ValueError("Se requiere precio para órdenes limit")
            order = LimitOrder(action, amount, price)

        trade = self.connection.placeOrder(contract, order)
        logger.info(f"Orden IB ejecutada: {trade.order.orderId} - {action} {amount} {symbol}")

        return {
            'id': trade.order.orderId,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'status': trade.orderStatus.status
        }

    def get_balance(self) -> Dict[str, float]:
        """
        Obtiene el balance de la cuenta.

        Returns:
            Diccionario con balances por activo
        """
        try:
            if self.market_type == 'crypto':
                balance = self.connection.fetch_balance()
                # Filtrar solo activos con balance > 0
                return {k: v['free'] for k, v in balance['total'].items() if v['free'] > 0}

            elif self.market_type == 'forex_stocks':
                account_values = self.connection.accountValues()
                balance = {}
                for item in account_values:
                    if item.tag == 'TotalCashValue':
                        balance[item.currency] = float(item.value)
                return balance

        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            return {}

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Obtiene las posiciones abiertas.

        Returns:
            Lista de posiciones abiertas
        """
        try:
            if self.market_type == 'crypto':
                # En spot trading de crypto no hay posiciones abiertas persistentes
                # Solo hay balances. Para futuros sería diferente.
                return []

            elif self.market_type == 'forex_stocks':
                positions = self.connection.positions()
                return [
                    {
                        'symbol': pos.contract.symbol,
                        'amount': pos.position,
                        'avg_cost': pos.avgCost,
                        'market_value': pos.marketValue
                    }
                    for pos in positions
                ]

        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []

    def _create_ib_contract(self, symbol: str):
        """
        Crea un contrato de IB basado en el símbolo.

        Args:
            symbol: Símbolo del activo

        Returns:
            Objeto Contract de IB
        """
        # Detectar si es Forex (6 caracteres) o Stock
        if len(symbol) == 6 and symbol.isalpha():
            # Forex: EURUSD -> EUR.USD
            return Forex(symbol[:3] + '.' + symbol[3:])
        else:
            # Stock
            return Stock(symbol, 'SMART', 'USD')

    def _convert_timeframe_ib(self, timeframe: str) -> str:
        """Convierte timeframe a formato de IB."""
        mapping = {
            '1m': '1 min',
            '5m': '5 mins',
            '15m': '15 mins',
            '30m': '30 mins',
            '1h': '1 hour',
            '4h': '4 hours',
            '1d': '1 day'
        }
        return mapping.get(timeframe, '1 hour')

    # ========================================================================
    # DATOS AVANZADOS DE MERCADO (v1.2)
    # ========================================================================

    def get_order_book(
        self,
        symbol: str,
        limit: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene el order book (libro de órdenes) del mercado.
        Detecta muros de compra/venta y desequilibrio.

        Args:
            symbol: Símbolo del activo
            limit: Profundidad del order book

        Returns:
            Diccionario con análisis del order book
        """
        try:
            if self.market_type != 'crypto':
                return None

            orderbook = self.connection.fetch_order_book(symbol, limit=limit)

            bids = orderbook.get('bids', [])  # Órdenes de compra
            asks = orderbook.get('asks', [])  # Órdenes de venta

            if not bids or not asks:
                return None

            # Calcular volumen total de cada lado
            bid_volume = sum([bid[1] for bid in bids])
            ask_volume = sum([ask[1] for ask in asks])

            # Detectar muros (órdenes grandes)
            avg_bid_size = bid_volume / len(bids) if bids else 0
            avg_ask_size = ask_volume / len(asks) if asks else 0

            # Muro = orden 3x más grande que el promedio
            bid_walls = [bid for bid in bids if bid[1] > avg_bid_size * 3]
            ask_walls = [ask for ask in asks if ask[1] > avg_ask_size * 3]

            # Imbalance: ratio entre bid y ask volume
            total_volume = bid_volume + ask_volume
            imbalance = ((bid_volume - ask_volume) / total_volume) * 100 if total_volume > 0 else 0

            # Spread
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else 0
            spread = ((best_ask - best_bid) / best_bid) * 100 if best_bid > 0 else 0

            result = {
                'bid_volume': round(bid_volume, 4),
                'ask_volume': round(ask_volume, 4),
                'imbalance': round(imbalance, 2),  # Positivo = más compradores
                'spread_percent': round(spread, 4),
                'bid_wall': bid_walls[0] if bid_walls else None,  # [precio, cantidad]
                'ask_wall': ask_walls[0] if ask_walls else None,
                'bid_wall_count': len(bid_walls),
                'ask_wall_count': len(ask_walls),
                'pressure': 'bullish' if imbalance > 10 else ('bearish' if imbalance < -10 else 'neutral')
            }

            logger.debug(f"Order Book {symbol}: Imbalance {imbalance:.1f}%, Spread {spread:.4f}%")
            return result

        except Exception as e:
            logger.error(f"Error obteniendo order book de {symbol}: {e}")
            return None

    def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el funding rate para contratos perpetuos.
        Solo disponible en mercados de futuros.

        Args:
            symbol: Símbolo del activo (ej: 'BTC/USDT')

        Returns:
            Diccionario con funding rate y análisis
        """
        try:
            if self.market_type != 'crypto':
                return None

            # Convertir a símbolo de futuros perpetuos si es necesario
            perp_symbol = symbol
            if not symbol.endswith(':USDT'):
                perp_symbol = symbol.replace('/USDT', '/USDT:USDT')

            # Intentar obtener funding rate
            try:
                funding = self.connection.fetch_funding_rate(perp_symbol)

                if funding:
                    rate = funding.get('fundingRate', 0) * 100  # Convertir a porcentaje

                    # Interpretar el funding rate
                    # Positivo = longs pagan a shorts (mercado alcista)
                    # Negativo = shorts pagan a longs (mercado bajista)
                    # Extremo (>0.1% o <-0.1%) = posible reversión
                    if rate > 0.1:
                        sentiment = 'extremely_bullish'
                        warning = 'Posible tope - demasiados longs'
                    elif rate > 0.03:
                        sentiment = 'bullish'
                        warning = None
                    elif rate < -0.1:
                        sentiment = 'extremely_bearish'
                        warning = 'Posible suelo - demasiados shorts'
                    elif rate < -0.03:
                        sentiment = 'bearish'
                        warning = None
                    else:
                        sentiment = 'neutral'
                        warning = None

                    return {
                        'funding_rate': round(rate, 4),
                        'sentiment': sentiment,
                        'warning': warning,
                        'next_funding_time': funding.get('fundingTimestamp')
                    }

            except Exception:
                # Exchange no soporta funding rate o símbolo no es perpetuo
                pass

            return None

        except Exception as e:
            logger.debug(f"Funding rate no disponible para {symbol}: {e}")
            return None

    def get_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el Open Interest (interés abierto) del mercado de futuros.
        Indica cuánto dinero nuevo está entrando al mercado.

        Args:
            symbol: Símbolo del activo

        Returns:
            Diccionario con open interest y cambio
        """
        try:
            if self.market_type != 'crypto':
                return None

            # Convertir a símbolo de futuros
            perp_symbol = symbol
            if not symbol.endswith(':USDT'):
                perp_symbol = symbol.replace('/USDT', '/USDT:USDT')

            try:
                # Intentar obtener open interest
                oi_data = self.connection.fetch_open_interest(perp_symbol)

                if oi_data:
                    oi_value = oi_data.get('openInterestAmount', 0)

                    # Obtener datos históricos para calcular cambio
                    oi_history = self.connection.fetch_open_interest_history(
                        perp_symbol,
                        timeframe='1h',
                        limit=24
                    )

                    change_24h = 0
                    if oi_history and len(oi_history) > 1:
                        oi_24h_ago = oi_history[0].get('openInterestAmount', oi_value)
                        if oi_24h_ago > 0:
                            change_24h = ((oi_value - oi_24h_ago) / oi_24h_ago) * 100

                    # Interpretar
                    # OI subiendo + precio subiendo = tendencia fuerte alcista
                    # OI subiendo + precio bajando = tendencia fuerte bajista
                    # OI bajando = posiciones cerrándose, posible reversión

                    return {
                        'value': oi_value,
                        'change_24h': round(change_24h, 2),
                        'trend': 'increasing' if change_24h > 5 else ('decreasing' if change_24h < -5 else 'stable')
                    }

            except Exception:
                # Exchange no soporta open interest
                pass

            return None

        except Exception as e:
            logger.debug(f"Open interest no disponible para {symbol}: {e}")
            return None

    def get_market_correlation(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Calcula correlación con BTC y mercados tradicionales.
        Útil para filtrar operaciones cuando hay divergencia con mercado general.

        Args:
            symbol: Símbolo del activo

        Returns:
            Diccionario con correlaciones
        """
        try:
            correlations = {}

            # 1. Correlación con BTC (si no es BTC)
            if 'BTC' not in symbol and self.market_type == 'crypto':
                try:
                    # Obtener datos de ambos activos
                    symbol_data = self.connection.fetch_ohlcv(symbol, timeframe='1h', limit=24)
                    btc_data = self.connection.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=24)

                    if symbol_data and btc_data and len(symbol_data) == len(btc_data):
                        # Calcular retornos
                        symbol_returns = [(symbol_data[i][4] - symbol_data[i-1][4]) / symbol_data[i-1][4]
                                         for i in range(1, len(symbol_data))]
                        btc_returns = [(btc_data[i][4] - btc_data[i-1][4]) / btc_data[i-1][4]
                                      for i in range(1, len(btc_data))]

                        # Correlación simple
                        if len(symbol_returns) > 0 and len(btc_returns) > 0:
                            import numpy as np
                            correlation = np.corrcoef(symbol_returns, btc_returns)[0, 1]
                            correlations['btc'] = round(correlation, 2)

                except Exception as e:
                    logger.debug(f"Error calculando correlación BTC: {e}")

            # 2. Obtener datos del S&P500 si IB está disponible
            # (Solo si tienes configurado Interactive Brokers)
            if hasattr(self, 'ib_connection') and self.ib_connection:
                try:
                    # Placeholder - requiere conexión IB activa
                    correlations['sp500'] = None
                except Exception:
                    pass

            if correlations:
                return correlations

            return None

        except Exception as e:
            logger.debug(f"Error calculando correlaciones: {e}")
            return None

    def get_advanced_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Obtiene todos los datos avanzados del mercado en una sola llamada.

        Args:
            symbol: Símbolo del activo

        Returns:
            Diccionario con todos los datos avanzados disponibles
        """
        logger.info(f"📊 Obteniendo datos avanzados para {symbol}...")

        advanced_data = {}

        # Order Book
        order_book = self.get_order_book(symbol)
        if order_book:
            advanced_data['order_book'] = order_book
            logger.debug(f"Order Book: Imbalance {order_book['imbalance']}%")

        # Funding Rate (solo futuros)
        funding = self.get_funding_rate(symbol)
        if funding:
            advanced_data['funding_rate'] = funding['funding_rate']
            advanced_data['funding_sentiment'] = funding['sentiment']
            if funding.get('warning'):
                advanced_data['funding_warning'] = funding['warning']
            logger.debug(f"Funding Rate: {funding['funding_rate']}%")

        # Open Interest (solo futuros)
        oi = self.get_open_interest(symbol)
        if oi:
            advanced_data['open_interest'] = oi
            logger.debug(f"Open Interest: {oi['change_24h']}% change")

        # Correlaciones
        correlations = self.get_market_correlation(symbol)
        if correlations:
            advanced_data['correlations'] = correlations
            logger.debug(f"Correlaciones: {correlations}")

        if advanced_data:
            logger.info(f"✅ Datos avanzados obtenidos: {list(advanced_data.keys())}")
        else:
            logger.debug("No hay datos avanzados disponibles para este símbolo")

        return advanced_data

    def close_connection(self):
        """Cierra la conexión con el mercado."""
        try:
            if self.market_type == 'forex_stocks' and self.connection:
                self.connection.disconnect()
                logger.info("Conexión con IB cerrada")
        except Exception as e:
            logger.error(f"Error cerrando conexión: {e}")


if __name__ == "__main__":
    # Prueba básica del módulo
    logging.basicConfig(level=logging.INFO)

    try:
        # Inicializar motor
        market = MarketEngine()

        # Obtener precio actual
        symbol = "BTC/USDT" if market.market_type == 'crypto' else "AAPL"
        price = market.get_current_price(symbol)
        print(f"\nPrecio actual de {symbol}: {price}")

        # Obtener balance
        balance = market.get_balance()
        print(f"\nBalance: {balance}")

        # Obtener datos históricos
        data = market.get_historical_data(symbol, timeframe='1h', limit=5)
        if data:
            print(f"\nÚltimas 5 velas de {symbol}:")
            for candle in data[-5:]:
                print(f"  {datetime.fromtimestamp(candle[0]/1000)} - Close: {candle[4]}")

    except Exception as e:
        logger.error(f"Error en prueba: {e}")
