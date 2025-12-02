"""
Async Engine - Operaciones asíncronas para mayor escalabilidad
==============================================================
Proporciona versiones async de operaciones críticas para:
- Análisis paralelo de múltiples símbolos
- Llamadas concurrentes a la API del exchange
- Procesamiento de señales sin bloqueo

Autor: Trading Bot System
Versión: 1.6
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Coroutine
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import time

logger = logging.getLogger(__name__)


class AsyncMarketFetcher:
    """
    Fetcher asíncrono de datos de mercado.
    Permite obtener datos de múltiples símbolos concurrentemente.
    """

    def __init__(self, market_engine, max_concurrent: int = 10):
        """
        Inicializa el fetcher asíncrono.

        Args:
            market_engine: Motor de mercado existente
            max_concurrent: Máximo de operaciones concurrentes
        """
        self.market_engine = market_engine
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)

    async def fetch_price(self, symbol: str) -> Optional[float]:
        """Obtiene precio de forma asíncrona."""
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                self.market_engine.get_current_price,
                symbol
            )

    async def fetch_prices_batch(self, symbols: List[str]) -> Dict[str, float]:
        """
        Obtiene precios de múltiples símbolos concurrentemente.

        Args:
            symbols: Lista de símbolos

        Returns:
            Dict {symbol: price}
        """
        tasks = [self.fetch_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        prices = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {symbol}: {result}")
                continue
            if result:
                prices[symbol] = result

        return prices

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 250
    ) -> Optional[List]:
        """Obtiene datos OHLCV de forma asíncrona."""
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                partial(
                    self.market_engine.get_historical_data,
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit
                )
            )

    async def fetch_all_ohlcv(
        self,
        symbols: List[str],
        timeframe: str = "15m"
    ) -> Dict[str, List]:
        """
        Obtiene datos OHLCV de múltiples símbolos concurrentemente.
        """
        tasks = [
            self.fetch_ohlcv(symbol, timeframe)
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching OHLCV {symbol}: {result}")
                continue
            if result:
                data[symbol] = result

        return data

    async def close(self):
        """Cierra el executor."""
        self._executor.shutdown(wait=True)


class AsyncAnalyzer:
    """
    Analizador asíncrono que permite procesar múltiples símbolos
    en paralelo sin bloquear el event loop.
    """

    def __init__(
        self,
        market_fetcher: AsyncMarketFetcher,
        technical_analyzer,
        ai_engine,
        max_concurrent: int = 4
    ):
        """
        Inicializa el analizador asíncrono.

        Args:
            market_fetcher: Fetcher asíncrono de mercado
            technical_analyzer: Analizador técnico
            ai_engine: Motor de IA
            max_concurrent: Análisis concurrentes máximos
        """
        self.market_fetcher = market_fetcher
        self.technical_analyzer = technical_analyzer
        self.ai_engine = ai_engine
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)

    async def analyze_symbol(self, symbol: str, timeframe: str = "15m") -> Optional[Dict[str, Any]]:
        """
        Analiza un símbolo de forma asíncrona.

        Returns:
            Dict con análisis técnico y decisión IA
        """
        async with self._semaphore:
            try:
                start_time = time.time()

                # 1. Obtener datos OHLCV
                ohlcv = await self.market_fetcher.fetch_ohlcv(symbol, timeframe)
                if not ohlcv:
                    return None

                # 2. Calcular indicadores técnicos (CPU bound, usar executor)
                loop = asyncio.get_event_loop()
                technical_data = await loop.run_in_executor(
                    self._executor,
                    self.technical_analyzer.analyze,
                    ohlcv
                )

                if not technical_data:
                    return None

                technical_data['symbol'] = symbol

                # 3. Consultar IA (I/O bound)
                ai_decision = await loop.run_in_executor(
                    self._executor,
                    self._get_ai_decision,
                    technical_data
                )

                elapsed = time.time() - start_time

                return {
                    'symbol': symbol,
                    'technical': technical_data,
                    'decision': ai_decision,
                    'analysis_time_ms': elapsed * 1000
                }

            except Exception as e:
                logger.error(f"Error analizando {symbol}: {e}")
                return None

    def _get_ai_decision(self, technical_data: Dict) -> Optional[Dict]:
        """Obtiene decisión de IA (sync wrapper)."""
        try:
            if self.ai_engine.use_specialized_agents:
                return self.ai_engine.analyze_market_v2(technical_data, None)
            elif self.ai_engine.use_hybrid:
                return self.ai_engine.analyze_market_hybrid(technical_data)
            else:
                return self.ai_engine.analyze_market(technical_data)
        except Exception as e:
            logger.error(f"Error en AI analysis: {e}")
            return None

    async def analyze_all_symbols(
        self,
        symbols: List[str],
        timeframe: str = "15m"
    ) -> List[Dict[str, Any]]:
        """
        Analiza todos los símbolos concurrentemente.

        Returns:
            Lista de resultados de análisis
        """
        tasks = [
            self.analyze_symbol(symbol, timeframe)
            for symbol in symbols
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        valid_results = []
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Error en análisis de {symbol}: {result}")
                continue
            if result:
                valid_results.append(result)

        logger.info(
            f"Análisis async completado: {len(valid_results)}/{len(symbols)} "
            f"símbolos en {total_time:.2f}s"
        )

        return valid_results

    async def close(self):
        """Cierra recursos."""
        self._executor.shutdown(wait=True)


class AsyncTaskQueue:
    """
    Cola de tareas asíncronas con prioridad.
    Permite encolar operaciones de trading y ejecutarlas ordenadamente.
    """

    def __init__(self, max_workers: int = 3):
        """
        Inicializa la cola de tareas.

        Args:
            max_workers: Workers para procesar tareas
        """
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._workers: List[asyncio.Task] = []
        self._running = False
        self.max_workers = max_workers

    async def start(self):
        """Inicia los workers."""
        if self._running:
            return

        self._running = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(
                self._worker(f"worker-{i}")
            )
            self._workers.append(worker)

        logger.info(f"AsyncTaskQueue iniciada con {self.max_workers} workers")

    async def stop(self):
        """Detiene los workers."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("AsyncTaskQueue detenida")

    async def enqueue(
        self,
        priority: int,
        task_fn: Callable[[], Coroutine],
        task_id: str = None
    ):
        """
        Encola una tarea.

        Args:
            priority: Prioridad (menor = mayor prioridad)
            task_fn: Función async a ejecutar
            task_id: ID opcional para tracking
        """
        await self._queue.put((priority, time.time(), task_id, task_fn))

    async def _worker(self, name: str):
        """Worker que procesa tareas."""
        while self._running:
            try:
                priority, timestamp, task_id, task_fn = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                try:
                    await task_fn()
                    logger.debug(f"[{name}] Tarea {task_id} completada")
                except Exception as e:
                    logger.error(f"[{name}] Error en tarea {task_id}: {e}")
                finally:
                    self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    @property
    def pending_tasks(self) -> int:
        """Número de tareas pendientes."""
        return self._queue.qsize()


class AsyncEventBus:
    """
    Bus de eventos asíncrono para comunicación entre componentes.
    Permite desacoplar el sistema y reaccionar a eventos.
    """

    def __init__(self):
        """Inicializa el bus de eventos."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, handler: Callable):
        """
        Suscribe un handler a un tipo de evento.

        Args:
            event_type: Tipo de evento (ej: "trade_executed", "sl_hit")
            handler: Función async a ejecutar
        """
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            logger.debug(f"Handler suscrito a '{event_type}'")

    async def unsubscribe(self, event_type: str, handler: Callable):
        """Desuscribe un handler."""
        async with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, data: Dict[str, Any] = None):
        """
        Publica un evento.

        Args:
            event_type: Tipo de evento
            data: Datos del evento
        """
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            return

        tasks = [handler(data) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(f"Error en handler de '{event_type}': {result}")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def run_with_timeout(
    coro: Coroutine,
    timeout: float,
    default: Any = None
) -> Any:
    """
    Ejecuta una coroutine con timeout.

    Args:
        coro: Coroutine a ejecutar
        timeout: Timeout en segundos
        default: Valor por defecto si hay timeout

    Returns:
        Resultado de la coroutine o default
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Timeout después de {timeout}s")
        return default


async def retry_async(
    coro_fn: Callable[[], Coroutine],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Any:
    """
    Ejecuta una coroutine con reintentos.

    Args:
        coro_fn: Función que crea la coroutine
        max_retries: Máximo de reintentos
        delay: Delay inicial entre reintentos
        backoff: Multiplicador de backoff

    Returns:
        Resultado de la coroutine

    Raises:
        Última excepción si se agotan los reintentos
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_retries + 1):
        try:
            return await coro_fn()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Intento {attempt + 1} fallido, reintentando en {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay *= backoff

    raise last_exception


def run_async(coro: Coroutine) -> Any:
    """
    Ejecuta una coroutine desde código síncrono.
    Útil para integrar con código existente.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si ya hay un loop corriendo, crear tarea
            return asyncio.ensure_future(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No hay loop, crear uno nuevo
        return asyncio.run(coro)
