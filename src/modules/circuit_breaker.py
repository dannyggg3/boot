"""
Circuit Breaker - Patrón de resiliencia para operaciones críticas
=================================================================
Previene cascadas de fallos cerrando temporalmente operaciones
cuando se detectan errores repetidos.

Autor: Trading Bot System
Versión: 1.6
"""

import time
import logging
from typing import Callable, Any, Optional, Dict
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados del circuit breaker."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Blocking calls
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitStats:
    """Estadísticas del circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Implementación del patrón Circuit Breaker.

    Estados:
    - CLOSED: Operación normal, permite todas las llamadas
    - OPEN: Bloquea llamadas después de X fallos consecutivos
    - HALF_OPEN: Permite una llamada de prueba después del timeout

    Usage:
        breaker = CircuitBreaker(name="exchange_api", failure_threshold=5)

        @breaker
        def call_exchange():
            return exchange.fetch_ticker("BTC/USDT")
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        expected_exceptions: tuple = (Exception,)
    ):
        """
        Inicializa el circuit breaker.

        Args:
            name: Nombre identificador del breaker
            failure_threshold: Fallos consecutivos para abrir el circuito
            recovery_timeout: Segundos antes de intentar half-open
            half_open_max_calls: Llamadas exitosas para cerrar el circuito
            expected_exceptions: Excepciones que cuentan como fallo
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = Lock()
        self._last_state_change = time.time()
        self._half_open_successes = 0

        logger.info(f"CircuitBreaker '{name}' inicializado (threshold={failure_threshold})")

    @property
    def state(self) -> CircuitState:
        """Estado actual del breaker."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Estadísticas del breaker."""
        return self._stats

    def _should_allow_call(self) -> bool:
        """Determina si se debe permitir una llamada."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Verificar si pasó el timeout de recuperación
            if time.time() - self._last_state_change >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            return True

        return False

    def _transition_to(self, new_state: CircuitState):
        """Transiciona a un nuevo estado."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._last_state_change = time.time()
            self._stats.state_changes += 1

            if new_state == CircuitState.HALF_OPEN:
                self._half_open_successes = 0

            logger.warning(f"CircuitBreaker '{self.name}': {old_state.value} -> {new_state.value}")

    def _record_success(self):
        """Registra una llamada exitosa."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.successful_calls += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_max_calls:
                    self._transition_to(CircuitState.CLOSED)
                    logger.info(f"CircuitBreaker '{self.name}' recuperado y cerrado")

    def _record_failure(self, exception: Exception):
        """Registra una llamada fallida."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Fallo en half-open, volver a abrir
                self._transition_to(CircuitState.OPEN)
                logger.warning(f"CircuitBreaker '{self.name}' reabierto por fallo en half-open")

            elif self._stats.consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
                logger.error(f"CircuitBreaker '{self.name}' ABIERTO después de {self.failure_threshold} fallos")

    def __call__(self, func: Callable) -> Callable:
        """Decorator para proteger funciones con el circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función protegida por el circuit breaker.

        Raises:
            CircuitOpenError: Si el circuito está abierto
        """
        if not self._should_allow_call():
            raise CircuitOpenError(
                f"CircuitBreaker '{self.name}' está ABIERTO. "
                f"Esperando {self.recovery_timeout}s para recuperación."
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exceptions as e:
            self._record_failure(e)
            raise

    def reset(self):
        """Resetea el circuit breaker a estado inicial."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._stats = CircuitStats()
            self._last_state_change = time.time()
            self._half_open_successes = 0
        logger.info(f"CircuitBreaker '{self.name}' reseteado")

    def force_open(self):
        """Fuerza la apertura del circuito (para emergencias)."""
        with self._lock:
            self._transition_to(CircuitState.OPEN)
        logger.warning(f"CircuitBreaker '{self.name}' forzado a OPEN")

    def get_status(self) -> Dict[str, Any]:
        """Retorna estado completo del breaker."""
        return {
            "name": self.name,
            "state": self._state.value,
            "total_calls": self._stats.total_calls,
            "successful_calls": self._stats.successful_calls,
            "failed_calls": self._stats.failed_calls,
            "consecutive_failures": self._stats.consecutive_failures,
            "failure_rate": (
                self._stats.failed_calls / self._stats.total_calls * 100
                if self._stats.total_calls > 0 else 0
            ),
            "last_failure": self._stats.last_failure_time,
            "last_success": self._stats.last_success_time,
            "state_changes": self._stats.state_changes
        }


class CircuitOpenError(Exception):
    """Excepción cuando el circuito está abierto."""
    pass


# =============================================================================
# CIRCUIT BREAKER REGISTRY
# =============================================================================

class CircuitBreakerRegistry:
    """
    Registro global de circuit breakers.
    Permite monitorear todos los breakers del sistema.
    """

    _instance = None
    _breakers: Dict[str, CircuitBreaker] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._breakers = {}
        return cls._instance

    def register(self, breaker: CircuitBreaker):
        """Registra un circuit breaker."""
        self._breakers[breaker.name] = breaker

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Obtiene un breaker por nombre."""
        return self._breakers.get(name)

    def get_all_status(self) -> Dict[str, Dict]:
        """Obtiene estado de todos los breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }

    def any_open(self) -> bool:
        """Verifica si algún breaker está abierto."""
        return any(
            b.state == CircuitState.OPEN
            for b in self._breakers.values()
        )

    def reset_all(self):
        """Resetea todos los breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Singleton global
circuit_registry = CircuitBreakerRegistry()


def create_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """
    Factory para crear y registrar circuit breakers.

    Usage:
        exchange_breaker = create_breaker("exchange", failure_threshold=3)

        @exchange_breaker
        def fetch_price():
            ...
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    circuit_registry.register(breaker)
    return breaker
