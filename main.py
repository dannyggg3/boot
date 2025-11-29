#!/usr/bin/env python3
"""
Sistema Autónomo de Trading Híbrido (SATH)
==========================================
Bot de trading profesional que combina análisis técnico cuantitativo
con razonamiento de IA para trading autónomo en crypto y mercados tradicionales.

Autor: Trading Bot System
Versión: 1.0
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

            self.symbols = self.config['trading']['symbols']
            self.scan_interval = self.config['trading']['scan_interval']
            self.mode = self.config['trading']['mode']

            # Configuración de análisis paralelo
            trading_config = self.config['trading']
            self.parallel_analysis = trading_config.get('parallel_analysis', True)
            self.max_workers = trading_config.get('max_parallel_workers', 4)

            logger.info(f"Modo de operación: {self.mode.upper()}")
            logger.info(f"Símbolos a operar: {', '.join(self.symbols)}")
            logger.info(f"Intervalo de escaneo: {self.scan_interval}s")
            logger.info(f"Análisis paralelo: {'HABILITADO' if self.parallel_analysis else 'SECUENCIAL'}")
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
        """Configura el sistema de logging."""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_file = log_config.get('file', 'logs/trading_bot.log')

        # Crear directorio de logs si no existe
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Configurar formato
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

        # Configurar handlers
        handlers = [
            logging.StreamHandler(),  # Consola
            logging.FileHandler(log_file)  # Archivo
        ]

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
        """Manejador de señales para apagado limpio."""
        logger.info(f"\nSeñal {signum} recibida. Apagando bot de forma segura...")
        self.running = False

    def run(self):
        """
        Ejecuta el loop principal del bot.
        """
        self.running = True
        logger.info("Bot iniciado. Presiona Ctrl+C para detener.")

        # Verificar estado del risk manager
        risk_status = self.risk_manager.get_status()
        logger.info(f"Capital inicial: ${risk_status['initial_capital']}")
        logger.info(f"Capital actual: ${risk_status['current_capital']}")

        if risk_status['kill_switch_active']:
            logger.critical("⚠️  KILL SWITCH ACTIVO - Bot en modo seguro")
            logger.critical("El bot no ejecutará operaciones hasta que se resuelva el problema")
            self.running = False
            return

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
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Analizando {symbol}")
        logger.info(f"{'=' * 60}")

        # 1. Obtener datos históricos
        timeframe = self.config['trading']['timeframe']
        ohlcv = self.market_engine.get_historical_data(symbol, timeframe=timeframe, limit=250)

        if not ohlcv:
            logger.warning(f"No se pudieron obtener datos para {symbol}")
            return

        # 2. Calcular indicadores técnicos
        technical_data = self.technical_analyzer.analyze(ohlcv)

        if not technical_data:
            logger.warning(f"No se pudieron calcular indicadores para {symbol}")
            return

        # Agregar símbolo y tipo de mercado
        technical_data['symbol'] = symbol
        technical_data['market_type'] = self.market_engine.market_type

        # 3. Consultar a la IA (Híbrido o Simple)
        if self.ai_engine.use_hybrid:
            logger.info("Usando análisis HÍBRIDO (2 niveles)")
            ai_decision = self.ai_engine.analyze_market_hybrid(technical_data)
        else:
            logger.info("Usando análisis SIMPLE (1 nivel)")
            ai_decision = self.ai_engine.analyze_market(technical_data)

        if not ai_decision:
            logger.warning("La IA no pudo generar una decisión")
            return

        decision = ai_decision.get('decision', 'ESPERA')
        confidence = ai_decision.get('confidence', 0.0)
        reasoning = ai_decision.get('razonamiento', 'N/A')
        analysis_type = ai_decision.get('analysis_type', 'standard')

        logger.info(f"Decisión IA: {decision} (Confianza: {confidence:.2f})")
        logger.info(f"Tipo de análisis: {analysis_type}")
        logger.info(f"Razonamiento: {reasoning}")

        # 4. Si la decisión es esperar, no hacer nada
        if decision == 'ESPERA':
            logger.info(f"✋ ESPERAR - No hay oportunidad clara en {symbol}")
            return

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
            market_data=technical_data
        )

        if not risk_validation['approved']:
            logger.warning(f"❌ Operación RECHAZADA por Risk Manager")
            logger.warning(f"Razón: {risk_validation.get('reason', 'N/A')}")
            return

        # 6. Ejecutar operación
        logger.info(f"✅ Operación APROBADA por Risk Manager")
        self._execute_trade(symbol, decision, risk_validation, current_price)

    def _execute_trade(
        self,
        symbol: str,
        decision: str,
        risk_params: Dict[str, Any],
        analysis_price: float
    ):
        """
        Ejecuta una operación de trading con protección contra slippage.

        Args:
            symbol: Símbolo del activo
            decision: COMPRA o VENTA
            risk_params: Parámetros validados por el risk manager
            analysis_price: Precio al momento del análisis (para verificación pre-ejecución)
        """
        side = 'buy' if decision == 'COMPRA' else 'sell'
        amount = risk_params['position_size']
        stop_loss = risk_params['stop_loss']
        take_profit = risk_params.get('take_profit')

        logger.info(f"\n{'=' * 60}")
        logger.info(f"EJECUTANDO ORDEN: {decision} {amount} {symbol}")
        logger.info(f"Precio de análisis: {analysis_price}")
        logger.info(f"Stop Loss: {stop_loss}")
        logger.info(f"Take Profit: {take_profit}")
        logger.info(f"{'=' * 60}\n")

        if self.mode == 'backtest':
            logger.info("🧪 BACKTEST MODE - Operación simulada")
            return

        try:
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
                    logger.warning(f"⚠️ Orden ABORTADA: {order.get('reason', 'Precio cambió demasiado')}")
                    logger.warning(f"Desviación de precio: {order.get('price_deviation', 'N/A'):.2f}%")
                    return

                if order_status in ['canceled', 'timeout']:
                    logger.warning(f"⏱️ Orden no ejecutada: {order_status}")
                    return

                logger.info(f"✅ Orden ejecutada exitosamente")
                logger.info(f"Order ID: {order.get('id', 'N/A')}")
                logger.info(f"Estado: {order_status}")

                # TODO: Implementar tracking de la orden
                # - Monitorear precio vs stop loss / take profit
                # - Actualizar trailing stop si está habilitado
                # - Cerrar posición cuando se alcance TP o SL
                # - Notificar al risk manager cuando se cierre

            else:
                logger.error("❌ Error ejecutando orden")

        except Exception as e:
            logger.error(f"Error ejecutando operación: {e}", exc_info=True)

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
        logger.info("=" * 60 + "\n")

    def _shutdown(self):
        """Apaga el bot de forma limpia."""
        logger.info("\n" + "=" * 60)
        logger.info("Apagando bot...")
        logger.info("=" * 60)

        try:
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
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     Sistema Autónomo de Trading Híbrido (SATH) v1.0         ║
    ║                                                               ║
    ║     Trading profesional con IA + Análisis Técnico            ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    try:
        bot = TradingBot()
        bot.run()
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Obtener el logger global
    logger = logging.getLogger(__name__)
    main()
