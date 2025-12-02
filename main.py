#!/usr/bin/env python3
"""
Sistema Autónomo de Trading Híbrido (SATH)
==========================================
Bot de trading profesional que combina análisis técnico cuantitativo
con razonamiento de IA para trading autónomo en crypto y mercados tradicionales.

Autor: Trading Bot System
Versión: 1.6

Changelog v1.6:
- Circuit Breaker para protección contra fallos en cascada
- Health Monitor con alertas automáticas
- AI Ensemble para decisiones más robustas
- Arquitectura async/await para escalabilidad
- Documentación para roadmap institucional

Changelog v1.5:
- Sistema completo de gestión de posiciones con IA
- Órdenes OCO reales (Stop Loss + Take Profit) via CCXT
- Supervisión IA de posiciones abiertas (HOLD, TIGHTEN_SL, EXTEND_TP)
- Trailing Stop inteligente con activación configurable
- Persistencia de posiciones en SQLite (sobrevive reinicios)
- Monitoreo de riesgo a nivel portfolio
- Recuperación automática de posiciones al reiniciar

Changelog v1.4:
- Volumen promedio (SMA 20) y ratio para comparación
- Reglas de trading flexibles (volumen, EMA50, divergencia)
- Confianza mínima reducida (50%)
- Logging mejorado con tags [SYMBOL] para threads paralelos
- Notificaciones Telegram mejoradas
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
    from modules.circuit_breaker import CircuitBreaker, circuit_registry, create_breaker
    from modules.health_monitor import HealthMonitor, create_exchange_check, create_database_check
    from modules.ai_ensemble import AIEnsemble
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    ADVANCED_FEATURES_AVAILABLE = False
    CircuitBreaker = None
    HealthMonitor = None
    AIEnsemble = None
    print(f"Warning: Advanced features not available: {e}")


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

        while self.running:
            try:
                heartbeat_counter += 1

                # Heartbeat cada minuto
                if heartbeat_counter % 60 == 0:
                    logger.info("💓 Heartbeat - Bot operando normalmente")
                    self._print_status()

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
        """
        logger.info(f"🔄 Iniciando análisis PARALELO de {len(self.symbols)} símbolos...")
        start_time = time.time()

        results = {}
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

        # 2.5 Obtener datos avanzados (Order Book, Funding Rate, etc.)
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
                    # Para VENTA: usar balance del activo
                    base_asset = symbol.split('/')[0]
                    asset_balance = balances.get(base_asset, 0)
                    asset_value_usd = asset_balance * current_price

                    if asset_value_usd < 5:
                        logger.info(f"{tag} ⏭️ VENTA ignorada - No tienes {base_asset} para vender (balance: {asset_balance:.6f} ≈ ${asset_value_usd:.2f})")
                        logger.info(f"{tag} 💡 En modo SPOT solo puedes vender activos que posees")
                        return
                    else:
                        logger.info(f"{tag} 💰 Balance {base_asset}: {asset_balance:.6f} (${asset_value_usd:.2f}) - Venta permitida")
                        available_balance = asset_balance  # v1.5: Balance en unidades del activo

                elif decision == 'COMPRA':
                    # Para COMPRA: usar balance de USDT
                    quote_asset = symbol.split('/')[1]  # USDT
                    usdt_balance = balances.get(quote_asset, 0)

                    if usdt_balance < 5:
                        logger.info(f"{tag} ⏭️ COMPRA ignorada - Balance {quote_asset} insuficiente: ${usdt_balance:.2f}")
                        return
                    else:
                        logger.info(f"{tag} 💵 Balance {quote_asset}: ${usdt_balance:.2f} - Compra permitida")
                        available_balance = usdt_balance  # v1.5: Balance en USDT

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
        Ejecuta una operación de trading con protección contra slippage.

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

                if order_status == 'aborted':
                    # Orden abortada por verificación de precio
                    logger.warning(f"{tag} ⚠️ Orden ABORTADA: {order.get('reason', 'Precio cambió demasiado')}")
                    logger.warning(f"{tag} Desviación de precio: {order.get('price_deviation', 'N/A'):.2f}%")
                    return

                if order_status in ['canceled', 'timeout']:
                    logger.warning(f"{tag} ⏱️ Orden no ejecutada: {order_status}")
                    return

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
                                'entry_order_id': order.get('id')
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
    ║     Sistema Autónomo de Trading Híbrido (SATH) v1.6         ║
    ║                                                               ║
    ║     Trading profesional con IA + Análisis Técnico            ║
    ║     Circuit Breaker + Health Monitor + AI Ensemble           ║
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
