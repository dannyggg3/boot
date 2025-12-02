"""
Health Monitor - Sistema de monitoreo de salud del bot
======================================================
Monitorea métricas críticas y emite alertas cuando hay problemas.
Incluye auto-recovery y diagnósticos.

Autor: Trading Bot System
Versión: 1.6
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Estados de salud del sistema."""
    HEALTHY = "healthy"           # Todo funcionando
    DEGRADED = "degraded"         # Funcionando con problemas
    UNHEALTHY = "unhealthy"       # Problemas serios
    CRITICAL = "critical"         # Sistema en peligro


@dataclass
class HealthCheck:
    """Resultado de un health check."""
    name: str
    status: HealthStatus
    message: str
    last_check: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """Métricas del sistema."""
    uptime_seconds: float = 0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_api_calls: int = 0
    failed_api_calls: int = 0
    avg_response_time_ms: float = 0
    memory_usage_mb: float = 0
    active_positions: int = 0
    last_trade_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None


class HealthMonitor:
    """
    Monitor de salud del sistema de trading.

    Características:
    - Health checks periódicos
    - Métricas de performance
    - Alertas automáticas
    - Auto-recovery básico
    """

    def __init__(
        self,
        config: Dict[str, Any],
        notifier=None,
        check_interval: int = 60
    ):
        """
        Inicializa el monitor de salud.

        Args:
            config: Configuración del bot
            notifier: Sistema de notificaciones (opcional)
            check_interval: Intervalo entre checks en segundos
        """
        self.config = config
        self.notifier = notifier
        self.check_interval = check_interval

        self.metrics = SystemMetrics()
        self.health_checks: Dict[str, HealthCheck] = {}
        self.registered_checks: Dict[str, Callable] = {}

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time = time.time()
        self._lock = threading.Lock()

        # Callbacks para alertas
        self._alert_callbacks: List[Callable] = []

        # Umbrales de alerta
        self._thresholds = {
            'max_api_failure_rate': 0.1,      # 10% de fallos
            'max_response_time_ms': 5000,     # 5 segundos
            'max_consecutive_failures': 3,
            'min_heartbeat_interval': 120     # 2 minutos sin heartbeat
        }

        logger.info(f"HealthMonitor inicializado (interval={check_interval}s)")

    def start(self):
        """Inicia el monitoreo en background."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="HealthMonitor"
        )
        self._thread.start()
        logger.info("HealthMonitor iniciado")

    def stop(self):
        """Detiene el monitoreo."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("HealthMonitor detenido")

    def register_check(self, name: str, check_fn: Callable[[], HealthCheck]):
        """
        Registra un health check personalizado.

        Args:
            name: Nombre del check
            check_fn: Función que retorna HealthCheck
        """
        self.registered_checks[name] = check_fn
        logger.debug(f"Health check registrado: {name}")

    def register_alert_callback(self, callback: Callable[[str, HealthStatus], None]):
        """Registra callback para alertas."""
        self._alert_callbacks.append(callback)

    def _monitoring_loop(self):
        """Loop principal de monitoreo."""
        while self._running:
            try:
                self._run_all_checks()
                self._update_metrics()
                self._check_alerts()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error en health monitoring: {e}")
                time.sleep(5)

    def _run_all_checks(self):
        """Ejecuta todos los health checks registrados."""
        for name, check_fn in self.registered_checks.items():
            try:
                start_time = time.time()
                result = check_fn()
                result.response_time_ms = (time.time() - start_time) * 1000
                result.last_check = datetime.now()

                with self._lock:
                    self.health_checks[name] = result

                if result.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    logger.warning(f"Health check '{name}' falló: {result.message}")

            except Exception as e:
                logger.error(f"Error ejecutando health check '{name}': {e}")
                with self._lock:
                    self.health_checks[name] = HealthCheck(
                        name=name,
                        status=HealthStatus.CRITICAL,
                        message=f"Error: {str(e)}"
                    )

    def _update_metrics(self):
        """Actualiza métricas del sistema."""
        with self._lock:
            self.metrics.uptime_seconds = time.time() - self._start_time
            self.metrics.last_heartbeat = datetime.now()

            # Calcular tasa de fallos API
            if self.metrics.total_api_calls > 0:
                pass  # Ya calculado en record_api_call

    def _check_alerts(self):
        """Verifica condiciones de alerta."""
        overall_status = self.get_overall_status()

        if overall_status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
            self._trigger_alert(f"Sistema en estado {overall_status.value}", overall_status)

        # Verificar tasa de fallos API
        if self.metrics.total_api_calls > 10:
            failure_rate = self.metrics.failed_api_calls / self.metrics.total_api_calls
            if failure_rate > self._thresholds['max_api_failure_rate']:
                self._trigger_alert(
                    f"Alta tasa de fallos API: {failure_rate*100:.1f}%",
                    HealthStatus.DEGRADED
                )

    def _trigger_alert(self, message: str, status: HealthStatus):
        """Dispara una alerta."""
        logger.warning(f"ALERTA: {message}")

        # Notificar via Telegram si disponible
        if self.notifier:
            try:
                emoji = "🔴" if status == HealthStatus.CRITICAL else "🟡"
                self.notifier.send_message(
                    f"{emoji} *Health Alert*\n"
                    f"Estado: {status.value}\n"
                    f"Mensaje: {message}"
                )
            except Exception as e:
                logger.error(f"Error enviando alerta: {e}")

        # Ejecutar callbacks
        for callback in self._alert_callbacks:
            try:
                callback(message, status)
            except Exception as e:
                logger.error(f"Error en alert callback: {e}")

    # =========================================================================
    # MÉTRICAS RECORDING
    # =========================================================================

    def record_trade(self, success: bool, pnl: float = 0):
        """Registra un trade."""
        with self._lock:
            self.metrics.total_trades += 1
            if success:
                self.metrics.successful_trades += 1
            else:
                self.metrics.failed_trades += 1
            self.metrics.last_trade_time = datetime.now()

    def record_api_call(self, success: bool, response_time_ms: float = 0):
        """Registra una llamada API."""
        with self._lock:
            self.metrics.total_api_calls += 1
            if not success:
                self.metrics.failed_api_calls += 1

            # Actualizar promedio de tiempo de respuesta
            n = self.metrics.total_api_calls
            old_avg = self.metrics.avg_response_time_ms
            self.metrics.avg_response_time_ms = (
                (old_avg * (n - 1) + response_time_ms) / n
            )

    def record_heartbeat(self):
        """Registra un heartbeat."""
        with self._lock:
            self.metrics.last_heartbeat = datetime.now()

    def update_active_positions(self, count: int):
        """Actualiza contador de posiciones activas."""
        with self._lock:
            self.metrics.active_positions = count

    # =========================================================================
    # STATUS QUERIES
    # =========================================================================

    def get_overall_status(self) -> HealthStatus:
        """Obtiene el estado general del sistema."""
        with self._lock:
            if not self.health_checks:
                return HealthStatus.HEALTHY

            statuses = [hc.status for hc in self.health_checks.values()]

            if HealthStatus.CRITICAL in statuses:
                return HealthStatus.CRITICAL
            if HealthStatus.UNHEALTHY in statuses:
                return HealthStatus.UNHEALTHY
            if HealthStatus.DEGRADED in statuses:
                return HealthStatus.DEGRADED
            return HealthStatus.HEALTHY

    def get_health_report(self) -> Dict[str, Any]:
        """Genera reporte completo de salud."""
        with self._lock:
            return {
                'status': self.get_overall_status().value,
                'timestamp': datetime.now().isoformat(),
                'uptime_hours': round(self.metrics.uptime_seconds / 3600, 2),
                'metrics': {
                    'total_trades': self.metrics.total_trades,
                    'successful_trades': self.metrics.successful_trades,
                    'failed_trades': self.metrics.failed_trades,
                    'win_rate': (
                        self.metrics.successful_trades / self.metrics.total_trades * 100
                        if self.metrics.total_trades > 0 else 0
                    ),
                    'total_api_calls': self.metrics.total_api_calls,
                    'api_failure_rate': (
                        self.metrics.failed_api_calls / self.metrics.total_api_calls * 100
                        if self.metrics.total_api_calls > 0 else 0
                    ),
                    'avg_response_time_ms': round(self.metrics.avg_response_time_ms, 2),
                    'active_positions': self.metrics.active_positions,
                    'last_trade': (
                        self.metrics.last_trade_time.isoformat()
                        if self.metrics.last_trade_time else None
                    ),
                    'last_heartbeat': (
                        self.metrics.last_heartbeat.isoformat()
                        if self.metrics.last_heartbeat else None
                    )
                },
                'checks': {
                    name: {
                        'status': hc.status.value,
                        'message': hc.message,
                        'response_time_ms': round(hc.response_time_ms, 2),
                        'last_check': hc.last_check.isoformat()
                    }
                    for name, hc in self.health_checks.items()
                }
            }

    def is_healthy(self) -> bool:
        """Verifica si el sistema está saludable."""
        return self.get_overall_status() in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


# =============================================================================
# HEALTH CHECK FACTORIES
# =============================================================================

def create_exchange_check(exchange) -> Callable[[], HealthCheck]:
    """Crea health check para conexión con exchange."""
    def check() -> HealthCheck:
        try:
            # Ping simple: fetch server time
            start = time.time()
            exchange.fetch_time()
            response_time = (time.time() - start) * 1000

            if response_time > 2000:
                return HealthCheck(
                    name="exchange",
                    status=HealthStatus.DEGRADED,
                    message=f"Respuesta lenta: {response_time:.0f}ms",
                    response_time_ms=response_time
                )

            return HealthCheck(
                name="exchange",
                status=HealthStatus.HEALTHY,
                message="Conexión OK",
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheck(
                name="exchange",
                status=HealthStatus.CRITICAL,
                message=f"Error de conexión: {str(e)}"
            )
    return check


def create_database_check(db_path: str) -> Callable[[], HealthCheck]:
    """Crea health check para base de datos."""
    import sqlite3
    import os

    def check() -> HealthCheck:
        try:
            if not os.path.exists(db_path):
                return HealthCheck(
                    name="database",
                    status=HealthStatus.CRITICAL,
                    message=f"Base de datos no existe: {db_path}"
                )

            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM positions")
            count = cursor.fetchone()[0]
            conn.close()

            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message=f"OK - {count} posiciones registradas"
            )
        except Exception as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Error: {str(e)}"
            )
    return check


def create_ai_check(ai_client, model: str) -> Callable[[], HealthCheck]:
    """Crea health check para servicio de IA."""
    def check() -> HealthCheck:
        try:
            start = time.time()
            response = ai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            response_time = (time.time() - start) * 1000

            if response_time > 5000:
                return HealthCheck(
                    name="ai_service",
                    status=HealthStatus.DEGRADED,
                    message=f"Respuesta lenta: {response_time:.0f}ms",
                    response_time_ms=response_time
                )

            return HealthCheck(
                name="ai_service",
                status=HealthStatus.HEALTHY,
                message="AI disponible",
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheck(
                name="ai_service",
                status=HealthStatus.UNHEALTHY,
                message=f"Error: {str(e)}"
            )
    return check
