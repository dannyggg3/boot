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

        self._initialize_connection()
        logger.info(f"Market Engine inicializado: {self.market_type} - Modo: {self.mode}")

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
        price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta una orden en el mercado.

        Args:
            symbol: Símbolo del activo
            side: 'buy' o 'sell'
            amount: Cantidad a operar
            order_type: 'market' o 'limit'
            price: Precio límite (solo para órdenes limit)

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

        try:
            if self.market_type == 'crypto':
                return self._execute_crypto_order(symbol, side, amount, order_type, price)
            elif self.market_type == 'forex_stocks':
                return self._execute_ib_order(symbol, side, amount, order_type, price)

        except Exception as e:
            logger.error(f"Error ejecutando orden: {e}")
            return None

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
