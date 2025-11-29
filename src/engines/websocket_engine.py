"""
WebSocket Engine - Motor de Datos en Tiempo Real
=================================================
Mantiene conexiones WebSocket persistentes para recibir
datos de mercado en tiempo real sin polling HTTP.

Autor: Trading Bot System
Versión: 1.3
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import ccxt.pro as ccxtpro
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class WebSocketEngine:
    """
    Motor de WebSockets para datos de mercado en tiempo real.
    Mantiene Order Book, Ticker y Trades actualizados en memoria.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el motor de WebSockets.

        Args:
            config: Configuración del bot
        """
        self.config = config
        self.exchange_id = self._get_exchange_id()
        self.exchange: Optional[ccxtpro.Exchange] = None

        # Datos en memoria (actualizados en tiempo real)
        self._orderbooks: Dict[str, Dict] = {}
        self._tickers: Dict[str, Dict] = {}
        self._trades: Dict[str, List] = defaultdict(list)

        # Control de estado
        self._running = False
        self._connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        # Callbacks para notificar cambios
        self._on_ticker_update: Optional[Callable] = None
        self._on_orderbook_update: Optional[Callable] = None

        # Símbolos a monitorear
        self.symbols: List[str] = config.get('trading', {}).get('symbols', [])

        logger.info(f"WebSocket Engine inicializado para {self.exchange_id}")

    def _get_exchange_id(self) -> str:
        """Obtiene el ID del exchange desde la configuración."""
        exchanges = self.config.get('exchanges', {})
        for exchange_id, settings in exchanges.items():
            if settings.get('enabled', False):
                return exchange_id
        return 'binance'

    async def _initialize_exchange(self):
        """Inicializa la conexión async con el exchange."""
        try:
            exchange_class = getattr(ccxtpro, self.exchange_id)

            # Configuración del exchange
            exchange_config = {
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            }

            # Modo testnet si está configurado
            if self.config.get('exchanges', {}).get(self.exchange_id, {}).get('testnet', False):
                exchange_config['sandbox'] = True

            self.exchange = exchange_class(exchange_config)
            self._connected = True
            logger.info(f"WebSocket conectado a {self.exchange_id}")

        except Exception as e:
            logger.error(f"Error inicializando WebSocket: {e}")
            raise

    async def _watch_orderbook(self, symbol: str):
        """
        Mantiene el Order Book actualizado en tiempo real.

        Args:
            symbol: Par de trading (ej: BTC/USDT)
        """
        while self._running:
            try:
                orderbook = await self.exchange.watch_order_book(symbol, limit=20)

                # Actualizar en memoria
                self._orderbooks[symbol] = {
                    'bids': orderbook['bids'][:10],
                    'asks': orderbook['asks'][:10],
                    'timestamp': datetime.now(),
                    'nonce': orderbook.get('nonce', 0)
                }

                # Callback si está configurado
                if self._on_orderbook_update:
                    self._on_orderbook_update(symbol, self._orderbooks[symbol])

            except Exception as e:
                if self._running:
                    logger.warning(f"Error en orderbook {symbol}: {e}")
                    await asyncio.sleep(1)

    async def _watch_ticker(self, symbol: str):
        """
        Mantiene el Ticker actualizado en tiempo real.

        Args:
            symbol: Par de trading
        """
        while self._running:
            try:
                ticker = await self.exchange.watch_ticker(symbol)

                self._tickers[symbol] = {
                    'last': ticker['last'],
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'high': ticker['high'],
                    'low': ticker['low'],
                    'volume': ticker['baseVolume'],
                    'change': ticker['percentage'],
                    'timestamp': datetime.now()
                }

                if self._on_ticker_update:
                    self._on_ticker_update(symbol, self._tickers[symbol])

            except Exception as e:
                if self._running:
                    logger.warning(f"Error en ticker {symbol}: {e}")
                    await asyncio.sleep(1)

    async def _watch_trades(self, symbol: str):
        """
        Mantiene los últimos trades actualizados.

        Args:
            symbol: Par de trading
        """
        while self._running:
            try:
                trades = await self.exchange.watch_trades(symbol)

                # Guardar últimos 100 trades
                self._trades[symbol].extend(trades)
                self._trades[symbol] = self._trades[symbol][-100:]

            except Exception as e:
                if self._running:
                    logger.warning(f"Error en trades {symbol}: {e}")
                    await asyncio.sleep(1)

    async def _run_watchers(self):
        """Ejecuta todos los watchers en paralelo."""
        await self._initialize_exchange()

        tasks = []
        for symbol in self.symbols:
            # Crear tareas para cada tipo de dato por símbolo
            tasks.append(asyncio.create_task(self._watch_orderbook(symbol)))
            tasks.append(asyncio.create_task(self._watch_ticker(symbol)))
            # trades es opcional, consume más recursos
            # tasks.append(asyncio.create_task(self._watch_trades(symbol)))

        logger.info(f"WebSocket watchers iniciados para {len(self.symbols)} símbolos")

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("WebSocket watchers cancelados")

    def _run_event_loop(self):
        """Ejecuta el event loop en un thread separado."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._run_watchers())
        except Exception as e:
            logger.error(f"Error en event loop de WebSocket: {e}")
        finally:
            self._loop.close()

    def start(self):
        """Inicia el motor de WebSockets en un thread separado."""
        if self._running:
            logger.warning("WebSocket Engine ya está corriendo")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        logger.info("WebSocket Engine iniciado en thread separado")

    def stop(self):
        """Detiene el motor de WebSockets."""
        self._running = False

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=5)

        if self.exchange:
            asyncio.run(self.exchange.close())

        logger.info("WebSocket Engine detenido")

    # ==================== GETTERS DE DATOS EN TIEMPO REAL ====================

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Obtiene el precio actual desde memoria (sin HTTP).

        Args:
            symbol: Par de trading

        Returns:
            Precio actual o None si no hay datos
        """
        ticker = self._tickers.get(symbol)
        if ticker:
            return ticker['last']
        return None

    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene el Order Book desde memoria (sin HTTP).

        Args:
            symbol: Par de trading

        Returns:
            Order Book o None si no hay datos
        """
        return self._orderbooks.get(symbol)

    def get_orderbook_imbalance(self, symbol: str) -> Optional[Dict]:
        """
        Calcula el imbalance del Order Book en tiempo real.

        Args:
            symbol: Par de trading

        Returns:
            Diccionario con análisis de imbalance
        """
        ob = self._orderbooks.get(symbol)
        if not ob:
            return None

        bids = ob['bids']
        asks = ob['asks']

        if not bids or not asks:
            return None

        # Calcular volumen total en cada lado
        bid_volume = sum(bid[1] for bid in bids)
        ask_volume = sum(ask[1] for ask in asks)
        total_volume = bid_volume + ask_volume

        if total_volume == 0:
            return None

        imbalance = ((bid_volume - ask_volume) / total_volume) * 100

        # Detectar muros
        bid_wall = max(bids, key=lambda x: x[1]) if bids else None
        ask_wall = max(asks, key=lambda x: x[1]) if asks else None

        return {
            'imbalance': round(imbalance, 2),
            'pressure': 'bullish' if imbalance > 10 else 'bearish' if imbalance < -10 else 'neutral',
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'bid_wall': {'price': bid_wall[0], 'size': bid_wall[1]} if bid_wall else None,
            'ask_wall': {'price': ask_wall[0], 'size': ask_wall[1]} if ask_wall else None,
            'spread': asks[0][0] - bids[0][0] if bids and asks else 0,
            'spread_percent': ((asks[0][0] - bids[0][0]) / bids[0][0]) * 100 if bids and asks else 0,
            'timestamp': ob['timestamp']
        }

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene el ticker desde memoria.

        Args:
            symbol: Par de trading

        Returns:
            Ticker o None
        """
        return self._tickers.get(symbol)

    def get_price_change(self, symbol: str) -> Optional[float]:
        """
        Obtiene el cambio de precio en las últimas 24h.

        Args:
            symbol: Par de trading

        Returns:
            Cambio porcentual o None
        """
        ticker = self._tickers.get(symbol)
        if ticker:
            return ticker.get('change')
        return None

    def is_data_fresh(self, symbol: str, max_age_seconds: int = 5) -> bool:
        """
        Verifica si los datos son recientes.

        Args:
            symbol: Par de trading
            max_age_seconds: Edad máxima permitida en segundos

        Returns:
            True si los datos son frescos
        """
        ticker = self._tickers.get(symbol)
        if not ticker:
            return False

        age = (datetime.now() - ticker['timestamp']).total_seconds()
        return age < max_age_seconds

    def get_all_prices(self) -> Dict[str, float]:
        """
        Obtiene todos los precios actuales.

        Returns:
            Diccionario {symbol: price}
        """
        return {
            symbol: ticker['last']
            for symbol, ticker in self._tickers.items()
            if 'last' in ticker
        }

    # ==================== CALLBACKS ====================

    def on_ticker_update(self, callback: Callable):
        """Registra callback para actualizaciones de ticker."""
        self._on_ticker_update = callback

    def on_orderbook_update(self, callback: Callable):
        """Registra callback para actualizaciones de order book."""
        self._on_orderbook_update = callback

    # ==================== ESTADO ====================

    def is_connected(self) -> bool:
        """Verifica si está conectado."""
        return self._connected and self._running

    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado del motor."""
        return {
            'connected': self._connected,
            'running': self._running,
            'symbols': self.symbols,
            'tickers_loaded': len(self._tickers),
            'orderbooks_loaded': len(self._orderbooks),
            'exchange': self.exchange_id
        }


# ==================== EJEMPLO DE USO ====================

if __name__ == "__main__":
    import yaml

    logging.basicConfig(level=logging.INFO)

    # Cargar config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Crear engine
    ws_engine = WebSocketEngine(config)

    # Callback de ejemplo
    def on_price_update(symbol, ticker):
        print(f"{symbol}: ${ticker['last']:.2f} ({ticker['change']:+.2f}%)")

    ws_engine.on_ticker_update(on_price_update)

    # Iniciar
    ws_engine.start()

    try:
        # Mantener corriendo
        import time
        while True:
            time.sleep(5)
            print(f"\nPrecios actuales: {ws_engine.get_all_prices()}")
    except KeyboardInterrupt:
        ws_engine.stop()
        print("Detenido")
