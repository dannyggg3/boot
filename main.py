#!/usr/bin/env python3
"""
Sistema Autónomo de Trading Híbrido (SATH)
==========================================
Bot de trading profesional que combina análisis técnico cuantitativo
con razonamiento de IA para trading autónomo en crypto y mercados tradicionales.

Autor: Trading Bot System
Versión: 2.2.2 INSTITUCIONAL PROFESIONAL

================================================================================
Changelog v2.2.0 (INSTITUCIONAL PROFESIONAL - SQLite Atómico):
================================================================================
- CRÍTICO: Persistencia SQLite atómica (elimina corrupción de datos)
- NUEVO: Migración automática de JSON a SQLite
- NUEVO: Fallback parser robusto para respuestas IA
- NUEVO: Mapeo de sinónimos de decisiones (BUY=COMPRA, SELL=VENTA)
- NUEVO: Pre-filtros configurables desde YAML
- NUEVO: Script de verificación del sistema (verify_system.py)
- OPTIMIZADO: Config paper para generar más trades
- OPTIMIZADO: ADX threshold reducido a 20 para paper (más oportunidades)
- OPTIMIZADO: Latencia IA reducida (usa chat en lugar de reasoner)
- FIX: Thread-safe locks en Risk Manager
- FIX: Validación de confidence normalizada (0-1)
- Tests: 12 nuevos tests para v2.2 (todos pasados)

Changelog v2.1.0 (INSTITUCIONAL PROFESIONAL):
- Trailing Math corregido (activation > distance)
- PROFIT LOCK - Trailing nunca convierte ganador en perdedor
- Range Agent para mercados laterales
- ADX >= 25 para tendencias, RSI 35-65 para entradas
- Session Filter y volumen >= 1.0x

Changelog v1.9.0 (Institucional Pro Max):
- Validación precio post-IA
- Filtro ADX pre-IA
- Backtester y CI/CD Pipeline

Changelog v1.8.1 (Institucional Pro):
- ATR-Based Stop Loss y Take Profit dinámicos
- Session Filter para horarios óptimos
- API Retries configurables
- Trailing Stop mejorado con cooldown

Changelog v1.7+ (Nivel Institucional Superior):
- Multi-Timeframe Analysis (4H → 1H → 15m)
- Correlation Filter
- Adaptive Parameters
- Performance Attribution
- Kelly Criterion automático

Ver README.md para historial completo.
"""

import sys
import os
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml
import signal
from typing import Dict, Any, List

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Importar módulos del bot
from engines.ai_engine import AIEngine
from engines.market_engine import MarketEngine
from modules.technical_analysis import TechnicalAnalyzer
from modules.risk_manager import RiskManager
from modules.data_logger import DataLogger  # v1.3: Logging de decisiones en InfluxDB
from modules.notifications import NotificationManager  # v1.4: Alertas Telegram

# v1.5: Sistema de gestión de posiciones
try:
    from engines.position_engine import PositionEngine
    from modules.position_supervisor import PositionSupervisor
    from modules.order_manager import OrderManager
    from modules.position_store import PositionStore
    from schemas.position_schemas import PositionSide, ExitReason
    POSITION_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    POSITION_MANAGEMENT_AVAILABLE = False
    PositionEngine = None
    PositionSupervisor = None
    OrderManager = None
    PositionStore = None
    print(f"Warning: Position management not available: {e}")

# v1.3: WebSocket Engine para datos en tiempo real
try:
    from engines.websocket_engine import WebSocketEngine
    WEBSOCKET_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_AVAILABLE = False
    WebSocketEngine = None

# v1.6: Módulos de robustez y escalabilidad
try:
    from modules.circuit_breaker import create_breaker
    from modules.health_monitor import HealthMonitor, create_exchange_check, create_database_check
    from modules.ai_ensemble import AIEnsemble
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    ADVANCED_FEATURES_AVAILABLE = False
    create_breaker = None
    HealthMonitor = None
    AIEnsemble = None
    create_exchange_check = None
    create_database_check = None
    print(f"Warning: Advanced features not available: {e}")

# v1.7: Métricas institucionales
try:
    from modules.institutional_metrics import get_institutional_metrics, InstitutionalMetrics
    INSTITUTIONAL_METRICS_AVAILABLE = True
except ImportError as e:
    INSTITUTIONAL_METRICS_AVAILABLE = False
    get_institutional_metrics = None
    InstitutionalMetrics = None
    print(f"Warning: Institutional metrics not available: {e}")

# v1.7+: Módulos de nivel institucional superior
try:
    from modules.multi_timeframe import MTFAnalyzer, get_mtf_analyzer
    MTF_AVAILABLE = True
except ImportError as e:
    MTF_AVAILABLE = False
    MTFAnalyzer = None
    get_mtf_analyzer = None
    print(f"Warning: Multi-timeframe analysis not available: {e}")

try:
    from modules.correlation_filter import CorrelationFilter, get_correlation_filter
    CORRELATION_FILTER_AVAILABLE = True
except ImportError as e:
    CORRELATION_FILTER_AVAILABLE = False
    CorrelationFilter = None
    get_correlation_filter = None
    print(f"Warning: Correlation filter not available: {e}")

try:
    from modules.adaptive_parameters import AdaptiveParameterManager, get_adaptive_manager
    ADAPTIVE_PARAMS_AVAILABLE = True
except ImportError as e:
    ADAPTIVE_PARAMS_AVAILABLE = False
    AdaptiveParameterManager = None
    get_adaptive_manager = None
    print(f"Warning: Adaptive parameters not available: {e}")

try:
    from modules.performance_attribution import PerformanceAttributor, get_performance_attributor
    PERFORMANCE_ATTRIBUTION_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_ATTRIBUTION_AVAILABLE = False
    PerformanceAttributor = None
    get_performance_attributor = None
    print(f"Warning: Performance attribution not available: {e}")


class TradingBot:
    """
    Orquestador principal del sistema de trading.
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Inicializa el bot de trading.

        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config = self._load_config(config_path)
        self.running = False
        self.is_trading = False  # Flag para saber si hay operación en curso
        self.shutdown_requested = False  # Flag para apagado graceful

        # Configurar logging
        self._setup_logging()

        # Inicializar componentes
        try:
            logger.info("=" * 60)
            logger.info("Iniciando Sistema Autónomo de Trading Híbrido (SATH)")
            logger.info("=" * 60)

            self.ai_engine = AIEngine(config_path)
            self.market_engine = MarketEngine(config_path)
            self.technical_analyzer = TechnicalAnalyzer(self.config)
            self.risk_manager = RiskManager(self.config)
            self.data_logger = DataLogger(self.config)  # v1.3: InfluxDB logging
            self.notifier = NotificationManager(self.config)  # v1.4: Telegram alerts

            # v1.3: WebSocket Engine para datos en tiempo real
            self.websocket_engine = None
            self.use_websockets = self.config.get('websockets', {}).get('enabled', False)
            if self.use_websockets and WEBSOCKET_AVAILABLE:
                try:
                    self.websocket_engine = WebSocketEngine(self.config)
                    logger.info("WebSocket Engine inicializado")
                except Exception as e:
                    logger.warning(f"No se pudo inicializar WebSocket Engine: {e}")
                    self.use_websockets = False

            # Extraer modo de operación temprano (necesario para Position Management)
            self.mode = self.config['trading']['mode']

            # v1.5: Sistema de gestión de posiciones
            self.position_engine = None
            self.position_supervisor = None
            self.order_manager = None
            self.position_store = None
            self.use_position_management = self.config.get('position_management', {}).get('enabled', False)

            if self.use_position_management and POSITION_MANAGEMENT_AVAILABLE:
                try:
                    # Inicializar componentes de gestión de posiciones
                    pm_config = self.config.get('position_management', {})
                    db_path = pm_config.get('database', {}).get('path', 'data/positions.db')

                    # 1. Position Store (persistencia SQLite)
                    self.position_store = PositionStore(db_path)

                    # 2. Order Manager (órdenes OCO/SL/TP)
                    self.order_manager = OrderManager(
                        exchange_connection=self.market_engine.connection,
                        config=self.config,
                        mode=self.mode
                    )

                    # 3. Position Engine (coordinador central)
                    self.position_engine = PositionEngine(
                        config=self.config,
                        market_engine=self.market_engine,
                        order_manager=self.order_manager,
                        position_store=self.position_store,
                        notifier=self.notifier,
                        data_logger=self.data_logger if hasattr(self, 'data_logger') else None,
                        websocket_engine=self.websocket_engine
                    )

                    # 4. Position Supervisor (supervisión IA)
                    self.position_supervisor = PositionSupervisor(self.config)

                    logger.info("Position Management System inicializado correctamente")
                    logger.info(f"  - Database: {db_path}")
                    logger.info(f"  - Protection mode: {pm_config.get('protection_mode', 'oco')}")

                except Exception as e:
                    logger.error(f"Error inicializando Position Management: {e}", exc_info=True)
                    self.use_position_management = False
            else:
                if not POSITION_MANAGEMENT_AVAILABLE:
                    logger.info("Position Management no disponible (módulos no encontrados)")
                else:
                    logger.info("Position Management deshabilitado en configuración")

            # v1.6: Inicializar módulos de robustez y escalabilidad
            self.health_monitor = None
            self.ai_ensemble = None
            self.exchange_breaker = None

            if ADVANCED_FEATURES_AVAILABLE:
                try:
                    # Circuit Breaker para proteger llamadas al exchange
                    self.exchange_breaker = create_breaker(
                        name="exchange_api",
                        failure_threshold=5,
                        recovery_timeout=60
                    )

                    # Health Monitor para monitoreo de salud del sistema
                    self.health_monitor = HealthMonitor(
                        config=self.config,
                        notifier=self.notifier,
                        check_interval=60
                    )

                    # Registrar health checks
                    if self.market_engine and self.market_engine.connection:
                        self.health_monitor.register_check(
                            "exchange",
                            create_exchange_check(self.market_engine.connection)
                        )

                    if self.use_position_management:
                        pm_config = self.config.get('position_management', {})
                        db_path = pm_config.get('database', {}).get('path', 'data/positions.db')
                        self.health_monitor.register_check(
                            "database",
                            create_database_check(db_path)
                        )

                    # AI Ensemble para decisiones más robustas
                    self.ai_ensemble = AIEnsemble(
                        ai_engine=self.ai_engine,
                        config=self.config,
                        min_consensus=0.6,
                        min_models_agree=2
                    )

                    logger.info("Advanced Features v1.6 inicializados")
                    logger.info("  - Circuit Breaker: ACTIVO")
                    logger.info("  - Health Monitor: ACTIVO")
                    logger.info("  - AI Ensemble: ACTIVO")

                except Exception as e:
                    logger.warning(f"No se pudieron inicializar features avanzados: {e}")

            # v1.7: Métricas institucionales
            self.institutional_metrics = None
            self.use_liquidity_validation = self.config.get('liquidity_validation', {}).get('enabled', True)

            # v1.7: Tracking de capital para Sharpe Ratio y Drawdown
            self.last_recorded_capital = 0
            self.last_capital_record_date = None
            self.daily_starting_capital = 0

            if INSTITUTIONAL_METRICS_AVAILABLE:
                try:
                    self.institutional_metrics = get_institutional_metrics(self.config)
                    logger.info("v1.7 Institutional Metrics: ACTIVO")
                    logger.info(f"  - Liquidity Validation: {'ON' if self.use_liquidity_validation else 'OFF'}")
                except Exception as e:
                    logger.warning(f"No se pudieron inicializar métricas institucionales: {e}")

            # v1.7+: Módulos de nivel institucional superior
            self.mtf_analyzer = None
            self.correlation_filter = None
            self.adaptive_manager = None
            self.performance_attributor = None

            # Multi-Timeframe Analysis
            self.use_mtf = self.config.get('multi_timeframe', {}).get('enabled', False)
            if self.use_mtf and MTF_AVAILABLE:
                try:
                    self.mtf_analyzer = MTFAnalyzer(self.config)
                    logger.info("v1.7+ Multi-Timeframe Analysis: ACTIVO")
                    logger.info(f"  - Timeframes: {self.mtf_analyzer.higher_tf} → {self.mtf_analyzer.medium_tf} → {self.mtf_analyzer.lower_tf}")
                except Exception as e:
                    logger.warning(f"No se pudo inicializar MTF: {e}")
                    self.use_mtf = False

            # Correlation Filter
            self.use_correlation_filter = self.config.get('correlation_filter', {}).get('enabled', False)
            if self.use_correlation_filter and CORRELATION_FILTER_AVAILABLE:
                try:
                    self.correlation_filter = CorrelationFilter(self.config)
                    logger.info("v1.7+ Correlation Filter: ACTIVO")
                    logger.info(f"  - Max correlation: {self.correlation_filter.max_correlation:.0%}")
                except Exception as e:
                    logger.warning(f"No se pudo inicializar filtro de correlación: {e}")
                    self.use_correlation_filter = False

            # Adaptive Parameters
            self.use_adaptive_params = self.config.get('adaptive_parameters', {}).get('enabled', False)
            if self.use_adaptive_params and ADAPTIVE_PARAMS_AVAILABLE:
                try:
                    # v2.2.2: Usar singleton para que PositionEngine pueda acceder
                    self.adaptive_manager = get_adaptive_manager(self.config)
                    logger.info("v1.7+ Adaptive Parameters: ACTIVO")
                except Exception as e:
                    logger.warning(f"No se pudieron inicializar parámetros adaptativos: {e}")
                    self.use_adaptive_params = False

            # Performance Attribution
            self.use_performance_attribution = self.config.get('performance_attribution', {}).get('enabled', True)
            if self.use_performance_attribution and PERFORMANCE_ATTRIBUTION_AVAILABLE:
                try:
                    self.performance_attributor = PerformanceAttributor(self.config)
                    logger.info("v1.7+ Performance Attribution: ACTIVO")
                except Exception as e:
                    logger.warning(f"No se pudo inicializar atribución de rendimiento: {e}")
                    self.use_performance_attribution = False

            self.symbols = self.config['trading']['symbols']
            self.scan_interval = self.config['trading']['scan_interval']
            # self.mode ya se extrajo arriba (línea 119)

            # Configuración de análisis paralelo
            trading_config = self.config['trading']
            self.parallel_analysis = trading_config.get('parallel_analysis', True)
            self.max_workers = trading_config.get('max_parallel_workers', 4)

            # Configuración de datos avanzados (v1.2)
            advanced_data_config = trading_config.get('advanced_data', {})
            self.use_advanced_data = advanced_data_config.get('enabled', True)
            self.use_order_book = advanced_data_config.get('order_book', True)
            self.use_funding_rate = advanced_data_config.get('funding_rate', True)
            self.use_correlations = advanced_data_config.get('correlations', True)

            logger.info(f"Modo de operación: {self.mode.upper()}")
            logger.info(f"Símbolos a operar: {', '.join(self.symbols)}")
            logger.info(f"Intervalo de escaneo: {self.scan_interval}s")
            logger.info(f"Análisis paralelo: {'HABILITADO' if self.parallel_analysis else 'SECUENCIAL'}")
            logger.info(f"Datos avanzados: {'HABILITADO' if self.use_advanced_data else 'DESHABILITADO'}")
            logger.info(f"WebSockets: {'HABILITADO' if self.use_websockets else 'DESHABILITADO (polling HTTP)'}")
            logger.info(f"Position Management: {'HABILITADO' if self.use_position_management else 'DESHABILITADO'}")
            logger.info("=" * 60)

            # Configurar manejadores de señales para apagado limpio
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        except Exception as e:
            logger.critical(f"Error inicializando el bot: {e}")
            raise

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga la configuración desde el archivo YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f"ERROR: No se pudo cargar la configuración: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Configura el sistema de logging con rotación diaria."""
        from logging.handlers import TimedRotatingFileHandler

        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_file = log_config.get('file', 'logs/trading_bot.log')
        backup_count = log_config.get('backup_count', 30)  # Mantener 30 días por defecto

        # Crear directorio de logs si no existe
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Configurar formato
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

        # Handler de consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format, date_format))

        # Handler de archivo con rotación diaria a medianoche
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',      # Rotar a medianoche
            interval=1,           # Cada 1 día
            backupCount=backup_count,  # Días a mantener
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        file_handler.suffix = '%Y-%m-%d'  # Sufijo para archivos rotados: trading_bot.log.2024-11-30

        # Configurar handlers
        handlers = [console_handler, file_handler]

        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            datefmt=date_format,
            handlers=handlers
        )

        # Silenciar logs verbosos de librerías externas
        logging.getLogger('ccxt').setLevel(logging.WARNING)
        logging.getLogger('ib_insync').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    def _signal_handler(self, signum, frame):
        """Manejador de señales para apagado limpio con protección de trades."""
        if self.shutdown_requested:
            logger.warning("Segunda señal recibida. Forzando apagado...")
            self.running = False
            return

        self.shutdown_requested = True
        logger.info(f"\nSeñal {signum} recibida. Iniciando apagado seguro...")

        # Si hay un trade en progreso, esperar a que termine
        if self.is_trading:
            logger.warning("⚠️  Trade en progreso. Esperando a que termine (máx 30s)...")
            wait_time = 0
            while self.is_trading and wait_time < 30:
                time.sleep(1)
                wait_time += 1
                if wait_time % 5 == 0:
                    logger.info(f"Esperando trade... {wait_time}s")

            if self.is_trading:
                logger.warning("Timeout esperando trade. Procediendo con apagado.")

        self.running = False

    def run(self):
        """
        Ejecuta el loop principal del bot.
        """
        self.running = True
        logger.info("Bot iniciado. Presiona Ctrl+C para detener.")

        # v1.3: Iniciar WebSocket Engine si está habilitado
        if self.use_websockets and self.websocket_engine:
            self.websocket_engine.start()
            logger.info("🔌 WebSocket Stream ACTIVO - Datos en tiempo real")
            # Esperar a que se conecte
            import time as t
            t.sleep(3)  # Dar tiempo para conexión inicial

        # Verificar estado del risk manager
        risk_status = self.risk_manager.get_status()
        logger.info(f"Capital inicial: ${risk_status['initial_capital']}")
        logger.info(f"Capital actual: ${risk_status['current_capital']}")

        if risk_status['kill_switch_active']:
            logger.critical("⚠️  KILL SWITCH ACTIVO - Bot en modo seguro")
            logger.critical("El bot no ejecutará operaciones hasta que se resuelva el problema")
            self.running = False
            return

        # v1.4: Notificar inicio del bot
        self.notifier.notify_startup(
            mode=self.mode,
            symbols=self.symbols,
            capital=risk_status['current_capital']
        )

        # v1.6: Iniciar Health Monitor si está disponible
        if self.health_monitor:
            self.health_monitor.start()
            logger.info("🏥 Health Monitor ACTIVO - Monitoreo de salud del sistema")

        # v1.5: Recuperar posiciones abiertas y iniciar monitoreo
        if self.use_position_management and self.position_engine:
            try:
                recovered = self.position_engine.recover_positions_on_startup()
                if recovered > 0:
                    logger.info(f"✅ {recovered} posiciones recuperadas del almacenamiento")
                    self.notifier.send_message(
                        f"🔄 *Posiciones Recuperadas*\n"
                        f"Se encontraron {recovered} posiciones abiertas del almacenamiento"
                    )

                # Iniciar monitoreo de posiciones en background
                self.position_engine.start_monitoring()
                logger.info("🔄 Position Engine monitoring iniciado")

            except Exception as e:
                logger.error(f"Error recuperando posiciones: {e}")

        heartbeat_counter = 0
        last_metrics_report = time.time()
        metrics_report_interval = 3600  # 1 hora

        while self.running:
            try:
                heartbeat_counter += 1

                # Heartbeat cada minuto
                if heartbeat_counter % 60 == 0:
                    logger.info("💓 Heartbeat - Bot operando normalmente")
                    self._print_status()
                    # v1.7: Actualizar capital tracking para métricas
                    self._update_institutional_capital()

                # v1.7: Reporte de métricas institucionales cada hora (también envía a InfluxDB)
                if self.institutional_metrics and (time.time() - last_metrics_report) >= metrics_report_interval:
                    # Forzar registro de daily return antes del reporte
                    self._update_institutional_capital(force_daily_record=True)
                    self.institutional_metrics.log_periodic_report("HOURLY", data_logger=self.data_logger)
                    last_metrics_report = time.time()

                    # v1.7+: Registrar estado de adaptive params en InfluxDB
                    if self.use_adaptive_params and self.adaptive_manager:
                        params = self.adaptive_manager.get_current_parameters()
                        metrics = params.get('metrics', {})
                        self.data_logger.log_adaptive_params(
                            min_confidence=params.get('min_confidence', 0.65),
                            max_risk=params.get('max_risk_per_trade', 1.0),
                            trailing_activation=params.get('trailing_activation', 2.0),
                            scan_interval=params.get('scan_interval', 180),
                            win_rate=metrics.get('recent_win_rate', 0.5),
                            loss_streak=metrics.get('loss_streak', 0),
                            win_streak=metrics.get('win_streak', 0),
                            volatility=metrics.get('current_volatility', 'medium')
                        )

                    # v1.7+: Registrar performance attribution en InfluxDB
                    if self.use_performance_attribution and self.performance_attributor:
                        try:
                            agent_perf = self.performance_attributor.get_agent_performance()
                            for agent_type, perf in agent_perf.items():
                                self.data_logger.log_performance_attribution(
                                    agent_type=agent_type,
                                    regime='all',
                                    symbol='ALL',
                                    trades=perf.get('trades', 0),
                                    win_rate=perf.get('win_rate', 0),
                                    total_pnl=perf.get('total_pnl', 0),
                                    avg_pnl=perf.get('avg_pnl', 0)
                                )

                            regime_perf = self.performance_attributor.get_regime_performance()
                            for regime, perf in regime_perf.items():
                                self.data_logger.log_performance_attribution(
                                    agent_type='all',
                                    regime=regime,
                                    symbol='ALL',
                                    trades=perf.get('trades', 0),
                                    win_rate=perf.get('win_rate', 0),
                                    total_pnl=perf.get('total_pnl', 0),
                                    avg_pnl=perf.get('avg_pnl', 0)
                                )
                        except Exception as e:
                            logger.debug(f"Error registrando attribution: {e}")

                # v1.6: Monitoreo de posiciones abiertas y control de capacidad
                if self.position_engine:
                    positions = self.position_engine.store.get_open_positions()
                    max_positions = self.position_engine.max_positions

                    # SIEMPRE mostrar estado de posiciones si hay alguna abierta
                    if positions:
                        self._show_position_monitor(positions, max_positions)

                    # Verificar si hay capacidad para nuevas posiciones
                    can_open_any = any(
                        self.position_engine.can_open_position(symbol)
                        for symbol in self.symbols
                    )

                    if not can_open_any:
                        logger.info(f"⏸️ Sin capacidad ({len(positions)}/{max_positions}) - Ahorrando tokens de IA")
                        time.sleep(self.scan_interval)
                        continue

                # Escanear símbolos (paralelo o secuencial)
                if self.parallel_analysis and len(self.symbols) > 1:
                    self._analyze_symbols_parallel()
                else:
                    for symbol in self.symbols:
                        try:
                            self._analyze_and_trade(symbol)
                        except Exception as e:
                            logger.error(f"Error procesando {symbol}: {e}")
                            continue

                # Esperar hasta el siguiente ciclo
                # TODO v2.0: Migrar a asyncio.sleep() cuando se requiera HFT (<30s scans)
                # Ver CHANGELOG.md -> Roadmap v2.0.0 para detalles de la migración
                logger.debug(f"Esperando {self.scan_interval}s hasta el próximo escaneo...")
                time.sleep(self.scan_interval)

            except KeyboardInterrupt:
                logger.info("Interrupción de usuario detectada")
                break
            except Exception as e:
                logger.error(f"Error en el loop principal: {e}", exc_info=True)
                time.sleep(60)  # Esperar un minuto antes de reintentar

        # Apagado limpio
        self._shutdown()

    def _analyze_symbols_parallel(self):
        """
        Analiza todos los símbolos en paralelo usando ThreadPoolExecutor.
        Reduce significativamente el tiempo de análisis cuando hay múltiples símbolos.

        TODO v2.0: Migrar a asyncio.gather() cuando se implemente asyncio nativo.
        El ThreadPoolExecutor funciona bien para trading de frecuencia baja/media,
        pero asyncio sería más eficiente para HFT con WebSockets.
        Ver CHANGELOG.md -> Roadmap v2.0.0 para detalles.
        """
        logger.info(f"🔄 Iniciando análisis PARALELO de {len(self.symbols)} símbolos...")
        start_time = time.time()

        results = {}
        # TODO v2.0: Reemplazar con asyncio.gather() para mejor eficiencia
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(self.symbols))) as executor:
            # Enviar todos los análisis en paralelo
            future_to_symbol = {
                executor.submit(self._analyze_and_trade, symbol): symbol
                for symbol in self.symbols
            }

            # Recoger resultados a medida que terminan
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    future.result()  # Obtener resultado o excepción
                    results[symbol] = 'OK'
                except Exception as e:
                    logger.error(f"Error en análisis paralelo de {symbol}: {e}")
                    results[symbol] = f'ERROR: {e}'

        elapsed = time.time() - start_time
        logger.info(f"✅ Análisis paralelo completado en {elapsed:.2f}s")
        logger.info(f"   Resultados: {results}")

    def _analyze_and_trade(self, symbol: str):
        """
        Analiza un símbolo y ejecuta trading si las condiciones son favorables.

        Args:
            symbol: Símbolo del activo (ej. 'BTC/USDT')
        """
        # v1.4: Prefijo para identificar cada thread en logs paralelos
        tag = f"[{symbol}]"

        logger.info(f"\n{'=' * 60}")
        logger.info(f"{tag} 🔍 INICIANDO ANÁLISIS")
        logger.info(f"{'=' * 60}")

        # v1.3: Verificar si WebSocket tiene datos frescos
        ws_price = None
        if self.use_websockets and self.websocket_engine:
            if self.websocket_engine.is_data_fresh(symbol, max_age_seconds=10):
                ws_price = self.websocket_engine.get_current_price(symbol)
                logger.info(f"{tag} 📡 WebSocket: ${ws_price:.2f}")
            else:
                logger.debug(f"{tag} WebSocket: datos no frescos, usando HTTP")

        # 1. Obtener datos históricos (siempre necesarios para indicadores)
        timeframe = self.config['trading']['timeframe']
        ohlcv = self.market_engine.get_historical_data(symbol, timeframe=timeframe, limit=250)

        if not ohlcv:
            logger.warning(f"{tag} ⚠️ No se pudieron obtener datos OHLCV")
            return

        # 2. Calcular indicadores técnicos
        technical_data = self.technical_analyzer.analyze(ohlcv)

        if not technical_data:
            logger.warning(f"{tag} ⚠️ No se pudieron calcular indicadores")
            return

        # Agregar símbolo y tipo de mercado
        technical_data['symbol'] = symbol
        technical_data['market_type'] = self.market_engine.market_type

        # 2.4 v1.7+: Actualizar volatilidad en Adaptive Manager
        if self.use_adaptive_params and self.adaptive_manager:
            volatility_level = technical_data.get('volatility_level', 'medium')
            self.adaptive_manager.update_market_volatility(volatility_level)

        # 2.5 v1.7+: FILTRO DE CORRELACIÓN
        # Verificar ANTES de gastar tokens en IA si la correlación permite operar
        if self.use_correlation_filter and self.correlation_filter and self.position_engine:
            try:
                open_positions = self.position_engine.store.get_open_positions()
                correlation_check = self.correlation_filter.can_open_position(symbol, open_positions)

                # Calcular diversification score
                diversification = self.correlation_filter.get_diversification_score(open_positions)

                # Registrar en InfluxDB para análisis
                blocking_symbol = ""
                max_corr = 0.0
                if not correlation_check['allowed']:
                    blocking_positions = correlation_check.get('blocking_positions', [])
                    if blocking_positions:
                        blocking_symbol = blocking_positions[0].get('symbol', '')
                        max_corr = correlation_check.get('max_correlation_found', 0)

                self.data_logger.log_correlation_check(
                    symbol=symbol,
                    blocked=not correlation_check['allowed'],
                    blocking_symbol=blocking_symbol,
                    correlation=max_corr,
                    diversification_score=diversification.get('score', 1.0)
                )

                if not correlation_check['allowed']:
                    logger.info(f"{tag} 🔗 FILTRO CORRELACIÓN: {correlation_check['reason']}")
                    logger.info(f"{tag} ⏭️ Saltando análisis para evitar sobreexposición correlacionada")
                    return
            except Exception as e:
                logger.debug(f"{tag} Error verificando correlación: {e}")

        # 2.6 v1.7+: MULTI-TIMEFRAME ANALYSIS
        # Solo operar si múltiples timeframes están alineados
        if self.use_mtf and self.mtf_analyzer:
            try:
                # Obtener datos de múltiples timeframes
                higher_tf = self.mtf_analyzer.higher_tf
                medium_tf = self.mtf_analyzer.medium_tf

                # Obtener OHLCV de timeframes superiores
                ohlcv_higher = self.market_engine.get_historical_data(symbol, timeframe=higher_tf, limit=250)
                ohlcv_medium = self.market_engine.get_historical_data(symbol, timeframe=medium_tf, limit=250)

                # Debug: mostrar cuántas velas se obtuvieron (solo en primer análisis o si hay problema)
                candles_higher = len(ohlcv_higher) if ohlcv_higher else 0
                candles_medium = len(ohlcv_medium) if ohlcv_medium else 0

                if candles_higher < 50 or candles_medium < 50:
                    logger.warning(f"{tag} ⚠️ Velas insuficientes: {higher_tf}={candles_higher}, {medium_tf}={candles_medium}")

                if ohlcv_higher and ohlcv_medium:
                    # Calcular indicadores para cada timeframe
                    data_higher = self.technical_analyzer.analyze(ohlcv_higher)
                    data_medium = self.technical_analyzer.analyze(ohlcv_medium)

                    # Verificar si el análisis técnico tuvo éxito
                    if not data_higher or not data_medium:
                        logger.warning(f"{tag} ⚠️ Análisis técnico falló para MTF (data vacía)")
                        logger.debug(f"   {higher_tf}: {candles_higher} velas → {'OK' if data_higher else 'VACÍO'}")
                        logger.debug(f"   {medium_tf}: {candles_medium} velas → {'OK' if data_medium else 'VACÍO'}")

                    # Verificar alineación
                    mtf_result = self.mtf_analyzer.get_mtf_filter_result(
                        market_data_higher=data_higher,
                        market_data_medium=data_medium,
                        market_data_lower=technical_data
                    )

                    # Registrar MTF en InfluxDB para análisis
                    details = mtf_result.get('details', {})
                    self.data_logger.log_mtf_analysis(
                        symbol=symbol,
                        higher_tf=self.mtf_analyzer.higher_tf,
                        higher_direction=details.get('higher', {}).get('direction', 'neutral'),
                        medium_tf=self.mtf_analyzer.medium_tf,
                        medium_direction=details.get('medium', {}).get('direction', 'neutral'),
                        lower_tf=self.mtf_analyzer.lower_tf,
                        lower_direction=details.get('lower', {}).get('direction', 'neutral'),
                        alignment_score=mtf_result.get('alignment_score', 0),
                        signal=mtf_result['signal']
                    )

                    if mtf_result['signal'] == 'ESPERA':
                        logger.info(f"{tag} 📊 MTF NO ALINEADO: {mtf_result['reason']}")
                        logger.info(f"{tag} ⏭️ Saltando - Solo operar cuando TF están alineados")
                        return

                    # Agregar boost de confianza si hay alineación
                    confidence_boost = mtf_result.get('confidence_boost', 0)
                    if confidence_boost > 0:
                        technical_data['mtf_confidence_boost'] = confidence_boost
                        logger.info(f"{tag} ✅ MTF ALINEADO ({mtf_result['alignment_score']:.0%}) - Boost: +{confidence_boost:.0%}")

            except Exception as e:
                logger.debug(f"{tag} Error en análisis MTF: {e}")

        # 2.7 Obtener datos avanzados (Order Book, Funding Rate, etc.)
        advanced_data = None
        if self.use_advanced_data:
            # v1.3: Usar datos de WebSocket si están disponibles
            if self.use_websockets and self.websocket_engine and self.websocket_engine.is_data_fresh(symbol):
                ws_orderbook = self.websocket_engine.get_orderbook_imbalance(symbol)
                if ws_orderbook:
                    advanced_data = self.market_engine.get_advanced_market_data(symbol)
                    # Sobrescribir order book con datos en tiempo real
                    advanced_data['order_book'] = ws_orderbook
                    logger.info(f"{tag} 📡 Order Book: WebSocket RT")
                else:
                    advanced_data = self.market_engine.get_advanced_market_data(symbol)
            else:
                advanced_data = self.market_engine.get_advanced_market_data(symbol)

            # Log de datos avanzados relevantes
            if advanced_data:
                if 'order_book' in advanced_data:
                    ob = advanced_data['order_book']
                    logger.info(f"{tag} 📊 Order Book: {ob['imbalance']}% ({ob['pressure']})")

                if 'funding_rate' in advanced_data:
                    logger.info(f"{tag} 💰 Funding: {advanced_data['funding_rate']}%")
                    if advanced_data.get('funding_warning'):
                        logger.warning(f"{tag} ⚠️ {advanced_data['funding_warning']}")

                if 'correlations' in advanced_data:
                    corr = advanced_data['correlations']
                    if 'btc' in corr:
                        logger.info(f"{tag} 🔗 Corr BTC: {corr['btc']}")

        # 3. Consultar a la IA (Agentes Especializados v1.2 o Híbrido o Simple)
        if self.ai_engine.use_specialized_agents:
            logger.info(f"{tag} 🤖 Usando AGENTES ESPECIALIZADOS")
            ai_decision = self.ai_engine.analyze_market_v2(technical_data, advanced_data)
        elif self.ai_engine.use_hybrid:
            logger.info(f"{tag} 🤖 Usando análisis HÍBRIDO")
            ai_decision = self.ai_engine.analyze_market_hybrid(technical_data)
        else:
            logger.info(f"{tag} 🤖 Usando análisis SIMPLE")
            ai_decision = self.ai_engine.analyze_market(technical_data)

        if not ai_decision:
            logger.warning(f"{tag} ⚠️ La IA no pudo generar una decisión")
            return

        decision = ai_decision.get('decision', 'ESPERA')
        confidence = ai_decision.get('confidence', 0.0)
        reasoning = ai_decision.get('razonamiento', 'N/A')
        analysis_type = ai_decision.get('analysis_type', 'standard')

        # v1.7+: Aplicar boost de confianza de MTF si está disponible
        mtf_boost = technical_data.get('mtf_confidence_boost', 0)
        if mtf_boost > 0:
            original_confidence = confidence
            confidence = min(1.0, confidence + mtf_boost)
            logger.info(f"{tag} 📊 Confianza ajustada: {original_confidence:.2f} + {mtf_boost:.2f} = {confidence:.2f}")

        # v1.7+: Verificar confianza mínima adaptativa
        if self.use_adaptive_params and self.adaptive_manager:
            min_confidence = self.adaptive_manager.get_adjusted_confidence()
            if confidence < min_confidence:
                logger.info(f"{tag} ⏭️ Confianza {confidence:.2f} < mínima adaptativa {min_confidence:.2f}")
                return

        logger.info(f"{tag} 📋 Decisión: {decision} (Confianza: {confidence:.2f})")
        logger.info(f"{tag} 📝 Razonamiento: {reasoning}")

        # v1.3: Registrar decisión en InfluxDB para análisis posterior
        agent_type = ai_decision.get('agent_type', 'general')
        self.data_logger.log_decision(
            symbol=symbol,
            decision=decision,
            confidence=confidence,
            agent_type=agent_type,
            analysis_type=analysis_type,
            market_data=technical_data,
            advanced_data=advanced_data,
            reasoning=reasoning[:500] if reasoning else ""
        )

        # 4. Si la decisión es esperar, no hacer nada
        if decision == 'ESPERA':
            logger.info(f"{tag} ✋ ESPERAR - No hay oportunidad clara")
            return

        # 4.5 v1.4/v1.5: Validar balance y obtener capital disponible para cálculo correcto
        available_balance = None  # v1.5: Balance real para Kelly Criterion
        current_price = technical_data['current_price']

        if self.mode in ['live', 'paper']:
            try:
                balances = self.market_engine.get_balance()

                if decision == 'VENTA':
                    # Para VENTA: usar balance del activo LIMITADO al capital configurado
                    base_asset = symbol.split('/')[0]
                    asset_balance = balances.get(base_asset, 0)
                    asset_value_usd = asset_balance * current_price

                    if asset_value_usd < 5:
                        logger.info(f"{tag} ⏭️ VENTA ignorada - No tienes {base_asset} para vender (balance: {asset_balance:.6f} ≈ ${asset_value_usd:.2f})")
                        logger.info(f"{tag} 💡 En modo SPOT solo puedes vender activos que posees")
                        return
                    else:
                        # v1.6: Limitar VENTA al capital configurado
                        initial_capital = self.risk_manager.initial_capital
                        max_exposure = self.config.get('position_management', {}).get('portfolio', {}).get('max_exposure_percent', 50) / 100

                        # Máximo USD a vender = capital * max_exposure
                        max_sell_usd = initial_capital * max_exposure
                        # Convertir a unidades del activo
                        max_sell_units = max_sell_usd / current_price

                        # Usar el menor entre: balance disponible y límite de capital
                        limited_balance = min(asset_balance, max_sell_units)
                        limited_value_usd = limited_balance * current_price

                        logger.info(f"{tag} 💰 Balance {base_asset}: {asset_balance:.6f} (${asset_value_usd:.2f})")
                        logger.info(f"{tag} 💵 Capital límite: ${initial_capital} x {max_exposure*100:.0f}% = ${max_sell_usd:.2f}")
                        logger.info(f"{tag} 📊 Venta máxima permitida: {limited_balance:.6f} {base_asset} (${limited_value_usd:.2f})")
                        available_balance = limited_balance  # v1.6: Balance limitado al capital

                elif decision == 'COMPRA':
                    # Para COMPRA: usar balance de USDT LIMITADO al capital configurado
                    quote_asset = symbol.split('/')[1]  # USDT
                    usdt_balance = balances.get(quote_asset, 0)

                    if usdt_balance < 5:
                        logger.info(f"{tag} ⏭️ COMPRA ignorada - Balance {quote_asset} insuficiente: ${usdt_balance:.2f}")
                        return
                    else:
                        # v1.6: Limitar COMPRA al capital configurado
                        initial_capital = self.risk_manager.initial_capital
                        max_exposure = self.config.get('position_management', {}).get('portfolio', {}).get('max_exposure_percent', 50) / 100

                        # Máximo USD a comprar = capital * max_exposure
                        max_buy_usd = initial_capital * max_exposure

                        # Usar el menor entre: balance disponible y límite de capital
                        limited_balance = min(usdt_balance, max_buy_usd)

                        logger.info(f"{tag} 💵 Balance {quote_asset}: ${usdt_balance:.2f}")
                        logger.info(f"{tag} 💰 Capital límite: ${initial_capital} x {max_exposure*100:.0f}% = ${max_buy_usd:.2f}")
                        logger.info(f"{tag} 📊 Compra máxima permitida: ${limited_balance:.2f}")
                        available_balance = limited_balance  # v1.6: Balance limitado al capital

            except Exception as e:
                logger.warning(f"{tag} ⚠️ No se pudo verificar balance: {e}")
                # Continuar con capital de config, el error aparecerá en la ejecución si hay problema

        # 5. Validar con Risk Manager
        current_price = technical_data['current_price']
        suggested_sl = ai_decision.get('stop_loss_sugerido')
        suggested_tp = ai_decision.get('take_profit_sugerido')

        # Convertir strings a float si es necesario
        if isinstance(suggested_sl, str):
            try:
                suggested_sl = float(suggested_sl)
            except:
                suggested_sl = None

        if isinstance(suggested_tp, str):
            try:
                suggested_tp = float(suggested_tp)
            except:
                suggested_tp = None

        # v1.8 INSTITUCIONAL: Si no hay TP sugerido, calcular basado en ATR
        if suggested_tp is None and hasattr(self.risk_manager, 'calculate_atr_take_profit'):
            suggested_tp = self.risk_manager.calculate_atr_take_profit(
                current_price=current_price,
                decision=decision,
                market_data=technical_data
            )
            if suggested_tp:
                logger.info(f"{tag} 🎯 ATR-based TP calculado: ${suggested_tp:,.2f}")

        # v1.8 INSTITUCIONAL: Session Filter (verificar horario óptimo)
        if hasattr(self.risk_manager, 'is_optimal_session'):
            session_check = self.risk_manager.is_optimal_session()
            if not session_check.get('optimal', True):
                logger.info(f"{tag} ⏰ Session Filter: {session_check.get('reason', 'Fuera de horario')}")
                # No retornar, solo advertir - el usuario puede deshabilitar esto en config

        risk_validation = self.risk_manager.validate_trade(
            symbol=symbol,
            decision=decision,
            current_price=current_price,
            suggested_stop_loss=suggested_sl,
            suggested_take_profit=suggested_tp,
            market_data=technical_data,
            confidence=confidence,  # v1.3: Para Kelly Criterion
            available_balance=available_balance  # v1.5: Balance real para cálculo correcto
        )

        if not risk_validation['approved']:
            logger.warning(f"{tag} ❌ RECHAZADO por Risk Manager: {risk_validation.get('reason', 'N/A')}")
            return

        # 5.5 v1.6: Verificar límite de posiciones ANTES de ejecutar
        if self.position_engine and not self.position_engine.can_open_position(symbol):
            logger.warning(f"{tag} ⏭️ Límite de posiciones alcanzado - Orden no ejecutada")
            return

        # 6. Ejecutar operación
        logger.info(f"{tag} ✅ APROBADO por Risk Manager")
        self._execute_trade(symbol, decision, risk_validation, current_price, tag)

    def _execute_trade(
        self,
        symbol: str,
        decision: str,
        risk_params: Dict[str, Any],
        analysis_price: float,
        tag: str = None
    ):
        """
        v1.9 INSTITUCIONAL: Ejecuta operación con validación de precio post-IA.

        CRÍTICO: Verifica que el precio no haya cambiado significativamente
        desde que la IA tomó la decisión. Si el precio cambió > umbral,
        la operación se ABORTA porque el R/R ya no es válido.

        Args:
            symbol: Símbolo del activo
            decision: COMPRA o VENTA
            risk_params: Parámetros validados por el risk manager
            analysis_price: Precio al momento del análisis (para verificación pre-ejecución)
            tag: Prefijo para identificar el símbolo en logs paralelos
        """
        # v1.4: Tag para identificar símbolo en logs paralelos
        if tag is None:
            tag = f"[{symbol}]"

        side = 'buy' if decision == 'COMPRA' else 'sell'
        amount = risk_params['position_size']
        stop_loss = risk_params['stop_loss']
        take_profit = risk_params.get('take_profit')

        logger.info(f"\n{'=' * 60}")
        logger.info(f"{tag} 🚀 EJECUTANDO ORDEN: {decision} {amount}")
        logger.info(f"{tag} 💵 Precio de análisis: ${analysis_price}")
        logger.info(f"{tag} 🛑 Stop Loss: ${stop_loss}")
        logger.info(f"{tag} 🎯 Take Profit: ${take_profit}")
        logger.info(f"{'=' * 60}\n")

        if self.mode == 'backtest':
            logger.info(f"{tag} 🧪 BACKTEST MODE - Operación simulada")
            return

        # Verificar si se solicitó apagado
        if self.shutdown_requested:
            logger.warning(f"{tag} ⚠️ Apagado solicitado - operación cancelada")
            return

        try:
            # Marcar que hay un trade en progreso
            self.is_trading = True

            # ================================================================
            # v1.9 CRÍTICO: VALIDACIÓN DE PRECIO POST-IA
            # ================================================================
            # La IA analizó el mercado con un precio X, pero entre el análisis
            # y la ejecución pueden pasar 5-15 segundos. En crypto volátil,
            # el precio puede moverse significativamente, invalidando el R/R.
            #
            # Solución: Re-consultar precio y abortar si desvía > umbral
            # ================================================================

            price_deviation_threshold = self.config.get('risk_management', {}).get(
                'max_price_deviation_percent', 0.2  # Default 0.2%
            )

            try:
                current_price_now = self.market_engine.get_current_price(symbol)

                if current_price_now and current_price_now > 0:
                    # Calcular desviación
                    price_deviation_pct = abs(current_price_now - analysis_price) / analysis_price * 100

                    logger.info(f"{tag} 🔄 VALIDACIÓN POST-IA:")
                    logger.info(f"{tag}    Precio análisis: ${analysis_price:,.2f}")
                    logger.info(f"{tag}    Precio actual:   ${current_price_now:,.2f}")
                    logger.info(f"{tag}    Desviación:      {price_deviation_pct:.3f}%")
                    logger.info(f"{tag}    Umbral máximo:   {price_deviation_threshold:.2f}%")

                    if price_deviation_pct > price_deviation_threshold:
                        # ABORTAR - El precio cambió demasiado
                        direction = "subió" if current_price_now > analysis_price else "bajó"
                        logger.warning(f"{tag} ⚠️ ORDEN ABORTADA: Precio {direction} {price_deviation_pct:.2f}% desde análisis")
                        logger.warning(f"{tag}    La IA decidió sobre precio ${analysis_price:,.2f}")
                        logger.warning(f"{tag}    Precio actual ${current_price_now:,.2f} ya no garantiza R/R calculado")

                        # Notificar al usuario
                        self.notifier.send_message(
                            f"⚠️ *ORDEN ABORTADA* - {symbol}\n\n"
                            f"El precio {direction} {price_deviation_pct:.2f}% desde que la IA analizó:\n"
                            f"• Precio análisis: ${analysis_price:,.2f}\n"
                            f"• Precio actual: ${current_price_now:,.2f}\n"
                            f"• Umbral máximo: {price_deviation_threshold:.2f}%\n\n"
                            f"_El R/R calculado ya no es válido. Esperando nueva señal._",
                            priority='high'
                        )

                        # Registrar métrica
                        if self.institutional_metrics:
                            self.institutional_metrics.record_aborted_trade(
                                symbol=symbol,
                                reason='price_deviation_post_ai',
                                analysis_price=analysis_price,
                                current_price=current_price_now,
                                deviation_pct=price_deviation_pct
                            )

                        self.is_trading = False
                        return

                    # Precio OK - continuar
                    logger.info(f"{tag} ✅ Precio validado - desviación {price_deviation_pct:.3f}% dentro del umbral")

                    # Usar precio actual para la ejecución (más preciso)
                    # pero mantener SL/TP del análisis original
                    execution_price = current_price_now

                else:
                    logger.warning(f"{tag} ⚠️ No se pudo obtener precio actual - usando precio de análisis")
                    execution_price = analysis_price

            except Exception as e:
                logger.warning(f"{tag} ⚠️ Error en validación post-IA: {e} - continuando con precio de análisis")
                execution_price = analysis_price

            # v1.7: Validación de liquidez antes de ejecutar
            if self.use_liquidity_validation and hasattr(self.market_engine, 'validate_liquidity'):
                order_value_usd = amount * analysis_price
                liquidity_check = self.market_engine.validate_liquidity(
                    symbol=symbol,
                    order_size_usd=order_value_usd,
                    side=side,
                    max_slippage_percent=self.config.get('liquidity_validation', {}).get('max_slippage_percent', 0.5)
                )

                if not liquidity_check.get('valid', True):
                    logger.warning(f"{tag} ⚠️ LIQUIDEZ INSUFICIENTE: {liquidity_check.get('reason', 'Unknown')}")
                    self.is_trading = False
                    return

                if liquidity_check.get('estimated_slippage'):
                    logger.info(f"{tag} 📊 Liquidez OK - Slippage estimado: {liquidity_check['estimated_slippage']:.3f}%")

            # Ejecutar orden con verificación de precio y protección slippage
            order = self.market_engine.execute_order(
                symbol=symbol,
                side=side,
                amount=amount,
                order_type='market',  # Se convertirá a limit si está configurado
                analysis_price=analysis_price
            )

            if order:
                order_status = order.get('status', 'unknown')
                order_type = order.get('type', 'market')

                # v1.7: Track fill rate para órdenes limit
                if self.institutional_metrics and order_type == 'limit':
                    self.institutional_metrics.record_limit_order('placed', symbol, 'entry')

                if order_status == 'aborted':
                    # Orden abortada por verificación de precio
                    logger.warning(f"{tag} ⚠️ Orden ABORTADA: {order.get('reason', 'Precio cambió demasiado')}")
                    logger.warning(f"{tag} Desviación de precio: {order.get('price_deviation', 'N/A'):.2f}%")
                    if self.institutional_metrics and order_type == 'limit':
                        self.institutional_metrics.record_limit_order('cancelled', symbol, 'entry')
                    return

                if order_status in ['canceled', 'timeout']:
                    logger.warning(f"{tag} ⏱️ Orden no ejecutada: {order_status}")
                    if self.institutional_metrics and order_type == 'limit':
                        status = 'timeout' if order_status == 'timeout' else 'cancelled'
                        self.institutional_metrics.record_limit_order(status, symbol, 'entry')
                    return

                # v1.7: Orden ejecutada = filled
                if self.institutional_metrics and order_type == 'limit':
                    self.institutional_metrics.record_limit_order('filled', symbol, 'entry')

                logger.info(f"{tag} ✅ Orden ejecutada exitosamente")
                logger.info(f"{tag} Order ID: {order.get('id', 'N/A')}")
                logger.info(f"{tag} Estado: {order_status}")

                # v1.4: Notificar operación ejecutada
                self.notifier.notify_trade_executed(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=order.get('price', analysis_price),
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=risk_params.get('confidence', 0.0)
                )

                # v1.5: Crear posición con protección OCO/Local
                if self.use_position_management and self.position_engine:
                    try:
                        position = self.position_engine.create_position(
                            order_result=order,
                            trade_params={
                                'symbol': symbol,
                                'side': PositionSide.LONG if side == 'buy' else PositionSide.SHORT,
                                'entry_price': order.get('price', analysis_price),
                                'quantity': amount,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'confidence': risk_params.get('confidence', 0.0),
                                'agent_type': risk_params.get('agent_type', 'general'),
                                'entry_order_id': order.get('id'),
                                # v1.7: Datos para métricas institucionales
                                'analysis_price': analysis_price,  # Para calcular slippage real
                                'execution_latency_ms': order.get('latency_ms', 0)
                            }
                        )

                        if position:
                            pos_id = position.get('id', 'N/A') if isinstance(position, dict) else position.id
                            logger.info(f"{tag} 📊 Posición creada: {pos_id}")
                            logger.info(f"{tag} 🛡️ Protección activa - SL: ${stop_loss:,.2f} | TP: ${f'{take_profit:,.2f}' if take_profit else 'N/A'}")
                        else:
                            logger.warning(f"{tag} ⚠️ No se pudo crear la posición protegida")

                    except Exception as e:
                        logger.error(f"{tag} Error creando posición: {e}")
                else:
                    logger.info(f"{tag} ⚠️ Position Management deshabilitado - SL/TP son solo referencias")

            else:
                logger.error(f"{tag} ❌ Error ejecutando orden")

        except Exception as e:
            logger.error(f"{tag} Error ejecutando operación: {e}", exc_info=True)
        finally:
            # Siempre marcar que el trade terminó
            self.is_trading = False

    def _update_institutional_capital(self, force_daily_record: bool = False):
        """
        v1.7: Actualiza las métricas institucionales con el capital actual.
        Registra daily returns para cálculo de Sharpe Ratio.

        Args:
            force_daily_record: Forzar registro de retorno diario
        """
        if not self.institutional_metrics:
            return

        try:
            from datetime import date

            risk_status = self.risk_manager.get_status()
            current_capital = risk_status['current_capital']
            initial_capital = risk_status['initial_capital']

            # Inicializar capital de tracking si es primera vez
            if self.last_recorded_capital == 0:
                self.last_recorded_capital = initial_capital
                self.daily_starting_capital = initial_capital
                self.last_capital_record_date = date.today()

            today = date.today()

            # Registrar daily return si cambió el día o es forzado
            if self.last_capital_record_date != today or force_daily_record:
                # Calcular retorno del día anterior
                if self.daily_starting_capital > 0:
                    daily_return = ((current_capital - self.daily_starting_capital) /
                                   self.daily_starting_capital) * 100

                    # Registrar solo si hubo cambio real
                    if abs(daily_return) > 0.001 or force_daily_record:
                        self.institutional_metrics.record_daily_return(
                            return_percent=daily_return,
                            capital=current_capital
                        )
                        logger.debug(f"📊 Daily return registrado: {daily_return:+.3f}% (Capital: ${current_capital:.2f})")

                # Reiniciar para el nuevo día
                self.daily_starting_capital = current_capital
                self.last_capital_record_date = today

            # Actualizar capital tracking
            self.last_recorded_capital = current_capital

        except Exception as e:
            logger.error(f"Error actualizando métricas de capital: {e}")

    def _print_status(self):
        """Imprime el estado actual del bot."""
        risk_status = self.risk_manager.get_status()

        logger.info("\n" + "=" * 60)
        logger.info("ESTADO DEL SISTEMA")
        logger.info("=" * 60)
        logger.info(f"Capital inicial: ${risk_status['initial_capital']}")
        logger.info(f"Capital actual: ${risk_status['current_capital']}")
        logger.info(f"PnL Total: ${risk_status['total_pnl']} ({risk_status['total_pnl_percentage']}%)")
        logger.info(f"PnL Diario: ${risk_status['daily_pnl']}")
        logger.info(f"Operaciones abiertas: {risk_status['open_trades_count']}")
        logger.info(f"Kill Switch: {'🔴 ACTIVO' if risk_status['kill_switch_active'] else '🟢 Inactivo'}")

        # v1.5: Mostrar posiciones activas si Position Management está habilitado
        if self.use_position_management and self.position_engine:
            try:
                open_positions = self.position_engine.get_open_positions()
                logger.info(f"Posiciones con protección: {len(open_positions)}")
                for pos in open_positions:
                    current_price = self.market_engine.get_current_price(pos.symbol)
                    if current_price:
                        pnl = pos.calculate_pnl(current_price)
                        logger.info(f"   📊 {pos.symbol}: {pnl['pnl_percent']:+.2f}% (SL: ${pos.stop_loss:,.2f})")
            except Exception as e:
                logger.debug(f"Error obteniendo posiciones: {e}")

        logger.info("=" * 60 + "\n")

    def _show_position_monitor(self, positions: list, max_positions: int):
        """
        Muestra el estado detallado de las posiciones abiertas en tiempo real.
        Se llama en cada ciclo del loop principal si hay posiciones.
        """
        logger.info(f"📊 MONITOR DE POSICIONES ({len(positions)}/{max_positions})")
        logger.info("-" * 50)

        for pos in positions:
            try:
                symbol = pos['symbol']
                side = pos['side'].upper()
                entry = pos['entry_price']
                sl = pos['stop_loss']
                tp = pos.get('take_profit')
                qty = pos['quantity']
                opened_at = pos.get('opened_at')

                # Calcular tiempo transcurrido
                time_open = ""
                if opened_at:
                    try:
                        if isinstance(opened_at, str):
                            open_time = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                        else:
                            open_time = opened_at
                        delta = datetime.now(open_time.tzinfo) if open_time.tzinfo else datetime.now() - open_time.replace(tzinfo=None)
                        hours, remainder = divmod(int(delta.total_seconds()), 3600)
                        minutes, _ = divmod(remainder, 60)
                        if hours > 0:
                            time_open = f" | ⏱️ {hours}h {minutes}m"
                        else:
                            time_open = f" | ⏱️ {minutes}m"
                    except:
                        pass

                # Obtener precio actual
                current_price = None
                if self.websocket_engine and self.websocket_engine.is_data_fresh(symbol):
                    current_price = self.websocket_engine.get_current_price(symbol)
                if not current_price:
                    current_price = self.market_engine.get_current_price(symbol)

                if current_price:
                    # Calcular PnL no realizado
                    if side == 'LONG':
                        pnl = (current_price - entry) * qty
                        pnl_pct = ((current_price - entry) / entry) * 100
                        dist_sl = ((current_price - sl) / current_price) * 100
                        dist_tp = ((tp - current_price) / current_price) * 100 if tp else 0
                    else:  # SHORT
                        pnl = (entry - current_price) * qty
                        pnl_pct = ((entry - current_price) / entry) * 100
                        dist_sl = ((sl - current_price) / current_price) * 100
                        dist_tp = ((current_price - tp) / current_price) * 100 if tp else 0

                    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                    logger.info(f"   ┌─ {symbol} {side}{time_open}")
                    logger.info(f"   │  💰 Entrada: ${entry:.2f} → Actual: ${current_price:.2f}")
                    logger.info(f"   │  {pnl_emoji} PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
                    logger.info(f"   │  🛑 SL: ${sl:.2f} (a {abs(dist_sl):.2f}%)")
                    if tp:
                        logger.info(f"   └─ 🎯 TP: ${tp:.2f} (a {abs(dist_tp):.2f}%)")
                    else:
                        logger.info(f"   └─ 🎯 TP: N/A (trailing stop activo)")
                else:
                    logger.info(f"   ┌─ {symbol} {side}{time_open}")
                    logger.info(f"   └─ ⚠️ Sin precio actual disponible")

            except Exception as e:
                logger.debug(f"Error mostrando posición: {e}")

        logger.info("-" * 50)

    def _close_all_positions(self) -> bool:
        """
        Cierra todas las posiciones abiertas vendiendo los activos.

        Returns:
            True si se cerraron todas las posiciones correctamente
        """
        if self.mode != 'live':
            logger.info("Modo paper/backtest - no hay posiciones reales que cerrar")
            return True

        try:
            # Obtener balances actuales
            balances = self.market_engine.get_balance()
            logger.info(f"Balances actuales: {balances}")

            positions_closed = 0
            errors = 0

            for asset, amount in balances.items():
                # Ignorar stablecoins y cantidades muy pequeñas
                if asset in ['USDT', 'USDC', 'BUSD', 'USD'] or amount < 0.00001:
                    continue

                # Construir el par de trading
                symbol = f"{asset}/USDT"

                # Verificar si el símbolo es válido para este exchange
                try:
                    ticker = self.market_engine.get_current_price(symbol)
                    if ticker is None:
                        continue

                    # Calcular valor en USD
                    value_usd = amount * ticker
                    if value_usd < 1:  # Ignorar posiciones menores a $1
                        continue

                    logger.warning(f"🔴 Cerrando posición: {amount} {asset} (~${value_usd:.2f})")

                    # Ejecutar orden de venta
                    self.is_trading = True
                    order = self.market_engine.execute_order(
                        symbol=symbol,
                        side='sell',
                        amount=amount,
                        order_type='market'
                    )
                    self.is_trading = False

                    if order:
                        logger.info(f"✅ Posición cerrada: {symbol}")
                        positions_closed += 1

                        # Notificar por Telegram
                        self.notifier.send_message(
                            f"🔴 *POSICIÓN CERRADA (Shutdown)*\n"
                            f"Símbolo: {symbol}\n"
                            f"Cantidad: {amount}\n"
                            f"Valor: ~${value_usd:.2f}"
                        )
                    else:
                        logger.error(f"❌ Error cerrando {symbol}")
                        errors += 1

                except Exception as e:
                    logger.error(f"Error procesando {asset}: {e}")
                    errors += 1
                    self.is_trading = False

            logger.info(f"Posiciones cerradas: {positions_closed}, Errores: {errors}")
            return errors == 0

        except Exception as e:
            logger.error(f"Error cerrando posiciones: {e}")
            return False

    def _shutdown(self):
        """Apaga el bot de forma limpia cerrando todas las posiciones."""
        logger.info("\n" + "=" * 60)
        logger.info("Apagando bot...")
        logger.info("=" * 60)

        try:
            # v1.5: Detener Position Engine monitoring
            if self.position_engine:
                try:
                    self.position_engine.stop_monitoring()
                    logger.info("Position Engine monitoring detenido")

                    # Mostrar resumen de posiciones abiertas
                    open_positions = self.position_engine.get_open_positions()
                    if open_positions:
                        logger.warning(f"⚠️  {len(open_positions)} posiciones abiertas permanecen activas")
                        for pos in open_positions:
                            logger.warning(f"   - {pos.symbol}: {pos.quantity} @ ${pos.entry_price:,.2f}")
                except Exception as e:
                    logger.error(f"Error deteniendo Position Engine: {e}")

            # v1.5: Cerrar todas las posiciones abiertas ANTES de apagar
            logger.warning("🔴 Cerrando todas las posiciones abiertas...")
            positions_closed = self._close_all_positions()

            if positions_closed:
                logger.info("✅ Todas las posiciones cerradas correctamente")
                self.notifier.notify_shutdown(reason="Apagado normal - Posiciones cerradas")
            else:
                logger.warning("⚠️  Algunas posiciones no se pudieron cerrar")
                self.notifier.notify_shutdown(reason="Apagado con errores en cierre de posiciones")

            # v1.6: Detener Health Monitor
            if self.health_monitor:
                self.health_monitor.stop()
                logger.info("Health Monitor detenido")

            # v1.3: Cerrar WebSocket Engine
            if self.websocket_engine:
                self.websocket_engine.stop()
                logger.info("WebSocket Engine detenido")

            # Cerrar conexión con el mercado
            if self.market_engine:
                self.market_engine.close_connection()

            # Imprimir estado final
            self._print_status()

            logger.info("Bot apagado correctamente")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error durante el apagado: {e}")


def main():
    """Función principal."""
    # Determinar archivo de configuración
    config_path = os.environ.get('SATH_CONFIG', 'config/config.yaml')

    # Determinar modo de operación para el banner
    try:
        with open(config_path, 'r') as f:
            temp_config = yaml.safe_load(f)
            mode = temp_config.get('trading', {}).get('mode', 'paper').upper()
    except:
        mode = 'PAPER'

    print(f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     Sistema Autónomo de Trading Híbrido (SATH) v2.2.0        ║
    ║       ★★★★★ INSTITUCIONAL PROFESIONAL ★★★★★                  ║
    ║                                                               ║
    ║     ✓ SQLite Atómico (ACID)        ✓ Fallback Parser IA     ║
    ║     ✓ Pre-filtros Configurables    ✓ Migración Auto JSON    ║
    ║     ✓ Kelly Criterion + Trailing   ✓ ATR-Based Stops        ║
    ║     ✓ verify_system.py             ✓ 31 Tests Pasados       ║
    ║                                                               ║
    ║     MODO: {mode:^50}║
    ║     Config: {config_path:<47}║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    try:
        bot = TradingBot(config_path)
        bot.run()
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Obtener el logger global
    logger = logging.getLogger(__name__)
    main()
