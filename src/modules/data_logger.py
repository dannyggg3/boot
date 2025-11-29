"""
Data Logger - Almacenamiento de Decisiones en InfluxDB
=======================================================
Guarda cada decisión del bot con contexto completo para
análisis posterior y optimización de estrategias.

Autor: Trading Bot System
Versión: 1.3
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv
import json

load_dotenv()
logger = logging.getLogger(__name__)


class DataLogger:
    """
    Logger de datos que almacena decisiones y métricas en InfluxDB.
    Permite análisis posterior para optimización de estrategias.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el data logger.

        Args:
            config: Configuración del bot
        """
        self.config = config
        self.enabled = config.get('data_logging', {}).get('enabled', True)

        # Configuración de InfluxDB
        self.url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
        self.token = os.getenv('INFLUXDB_TOKEN', '')
        self.org = os.getenv('INFLUXDB_ORG', 'trading_bot')
        self.bucket = os.getenv('INFLUXDB_BUCKET', 'trading_decisions')

        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api = None

        if self.enabled and self.token:
            self._connect()
        else:
            logger.warning("DataLogger deshabilitado o sin token de InfluxDB")

    def _connect(self):
        """Conecta con InfluxDB."""
        try:
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()

            # Verificar conexión
            health = self.client.health()
            if health.status == "pass":
                logger.info(f"Conectado a InfluxDB: {self.url}")
            else:
                logger.warning(f"InfluxDB health check: {health.status}")

        except Exception as e:
            logger.error(f"Error conectando a InfluxDB: {e}")
            self.enabled = False

    def log_decision(
        self,
        symbol: str,
        decision: str,
        confidence: float,
        agent_type: str,
        analysis_type: str,
        market_data: Dict[str, Any],
        advanced_data: Optional[Dict[str, Any]] = None,
        reasoning: str = ""
    ):
        """
        Registra una decisión de trading.

        Args:
            symbol: Par de trading
            decision: COMPRA, VENTA, ESPERA
            confidence: Nivel de confianza (0-1)
            agent_type: Tipo de agente (trend, reversal, hybrid)
            analysis_type: Tipo de análisis
            market_data: Datos técnicos del mercado
            advanced_data: Datos avanzados (order book, funding, etc.)
            reasoning: Razonamiento de la IA
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("trading_decision") \
                .tag("symbol", symbol) \
                .tag("decision", decision) \
                .tag("agent_type", agent_type) \
                .tag("analysis_type", analysis_type) \
                .field("confidence", float(confidence)) \
                .field("price", float(market_data.get('current_price', 0))) \
                .field("rsi", float(market_data.get('rsi', 0))) \
                .field("ema_50", float(market_data.get('ema_50', 0))) \
                .field("ema_200", float(market_data.get('ema_200', 0))) \
                .field("atr_percent", float(market_data.get('atr_percent', 0))) \
                .field("macd", float(market_data.get('macd', 0))) \
                .field("reasoning", reasoning[:500])  # Limitar tamaño

            # Datos avanzados si están disponibles
            if advanced_data:
                if 'order_book' in advanced_data:
                    ob = advanced_data['order_book']
                    point = point.field("ob_imbalance", float(ob.get('imbalance', 0)))
                    point = point.field("ob_spread", float(ob.get('spread_percent', 0)))

                if 'funding_rate' in advanced_data:
                    point = point.field("funding_rate", float(advanced_data['funding_rate']))

                if 'open_interest' in advanced_data:
                    oi = advanced_data['open_interest']
                    if isinstance(oi, dict):
                        point = point.field("oi_change", float(oi.get('change_24h', 0)))

            point = point.time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Decisión registrada: {symbol} -> {decision}")

        except Exception as e:
            logger.error(f"Error guardando decisión: {e}")

    def log_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        size: float,
        stop_loss: float,
        take_profit: float,
        agent_type: str,
        confidence: float
    ):
        """
        Registra la ejecución de un trade.

        Args:
            symbol: Par de trading
            side: BUY o SELL
            entry_price: Precio de entrada
            size: Tamaño de la posición
            stop_loss: Nivel de stop loss
            take_profit: Nivel de take profit
            agent_type: Tipo de agente
            confidence: Confianza de la decisión
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("trade_execution") \
                .tag("symbol", symbol) \
                .tag("side", side) \
                .tag("agent_type", agent_type) \
                .field("entry_price", float(entry_price)) \
                .field("size", float(size)) \
                .field("stop_loss", float(stop_loss)) \
                .field("take_profit", float(take_profit)) \
                .field("confidence", float(confidence)) \
                .field("risk_reward", abs((take_profit - entry_price) / (entry_price - stop_loss)) if stop_loss != entry_price else 0) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(f"Trade registrado: {side} {symbol} @ {entry_price}")

        except Exception as e:
            logger.error(f"Error guardando trade: {e}")

    def log_trade_result(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_percent: float,
        result: str,  # WIN, LOSS, BREAKEVEN
        agent_type: str,
        hold_time_minutes: int
    ):
        """
        Registra el resultado de un trade cerrado.

        Args:
            symbol: Par de trading
            side: BUY o SELL
            entry_price: Precio de entrada
            exit_price: Precio de salida
            pnl: Ganancia/pérdida en USD
            pnl_percent: Ganancia/pérdida en porcentaje
            result: WIN, LOSS, BREAKEVEN
            agent_type: Tipo de agente
            hold_time_minutes: Tiempo en posición
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("trade_result") \
                .tag("symbol", symbol) \
                .tag("side", side) \
                .tag("result", result) \
                .tag("agent_type", agent_type) \
                .field("entry_price", float(entry_price)) \
                .field("exit_price", float(exit_price)) \
                .field("pnl", float(pnl)) \
                .field("pnl_percent", float(pnl_percent)) \
                .field("hold_time_minutes", int(hold_time_minutes)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(f"Resultado registrado: {symbol} {result} {pnl_percent:+.2f}%")

        except Exception as e:
            logger.error(f"Error guardando resultado: {e}")

    def log_market_snapshot(
        self,
        symbol: str,
        price: float,
        volume_24h: float,
        rsi: float,
        volatility: float
    ):
        """
        Registra un snapshot del mercado para análisis histórico.
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("market_snapshot") \
                .tag("symbol", symbol) \
                .field("price", float(price)) \
                .field("volume_24h", float(volume_24h)) \
                .field("rsi", float(rsi)) \
                .field("volatility", float(volatility)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

        except Exception as e:
            logger.error(f"Error guardando snapshot: {e}")

    # ==================== CONSULTAS PARA ANÁLISIS ====================

    def get_agent_performance(self, agent_type: str, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene el rendimiento de un agente específico.

        Args:
            agent_type: Tipo de agente
            days: Días a analizar

        Returns:
            Métricas de rendimiento
        """
        if not self.enabled or not self.query_api:
            return {}

        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => r._measurement == "trade_result")
                |> filter(fn: (r) => r.agent_type == "{agent_type}")
            '''

            tables = self.query_api.query(query, org=self.org)

            wins = 0
            losses = 0
            total_pnl = 0.0

            for table in tables:
                for record in table.records:
                    if record.get_field() == "pnl":
                        total_pnl += record.get_value()
                    if record.values.get("result") == "WIN":
                        wins += 1
                    elif record.values.get("result") == "LOSS":
                        losses += 1

            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

            return {
                'agent_type': agent_type,
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'period_days': days
            }

        except Exception as e:
            logger.error(f"Error consultando rendimiento: {e}")
            return {}

    def get_symbol_statistics(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un símbolo específico.

        Args:
            symbol: Par de trading
            days: Días a analizar

        Returns:
            Estadísticas del símbolo
        """
        if not self.enabled or not self.query_api:
            return {}

        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{days}d)
                |> filter(fn: (r) => r._measurement == "trade_result")
                |> filter(fn: (r) => r.symbol == "{symbol}")
            '''

            tables = self.query_api.query(query, org=self.org)

            results = {'wins': 0, 'losses': 0, 'total_pnl': 0.0}

            for table in tables:
                for record in table.records:
                    if record.get_field() == "pnl":
                        results['total_pnl'] += record.get_value()
                    if record.values.get("result") == "WIN":
                        results['wins'] += 1
                    elif record.values.get("result") == "LOSS":
                        results['losses'] += 1

            total = results['wins'] + results['losses']
            results['total_trades'] = total
            results['win_rate'] = round((results['wins'] / total * 100) if total > 0 else 0, 2)
            results['symbol'] = symbol

            return results

        except Exception as e:
            logger.error(f"Error consultando estadísticas: {e}")
            return {}

    def get_decisions_by_condition(
        self,
        condition_field: str,
        condition_value: Any,
        days: int = 30
    ) -> List[Dict]:
        """
        Obtiene decisiones filtradas por una condición específica.
        Útil para analizar patrones.

        Args:
            condition_field: Campo a filtrar (ej: rsi, ob_imbalance)
            condition_value: Valor de referencia
            days: Días a analizar

        Returns:
            Lista de decisiones que cumplen la condición
        """
        # Esta es una consulta más compleja que requiere
        # personalización según el caso de uso
        if not self.enabled:
            return []

        logger.info(f"Consulta por condición: {condition_field} = {condition_value}")
        return []

    def close(self):
        """Cierra la conexión con InfluxDB."""
        if self.client:
            self.client.close()
            logger.info("Conexión InfluxDB cerrada")


# ==================== EJEMPLO DE USO ====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Configuración de prueba
    config = {
        'data_logging': {'enabled': True}
    }

    logger_instance = DataLogger(config)

    # Registrar una decisión de ejemplo
    logger_instance.log_decision(
        symbol="BTC/USDT",
        decision="COMPRA",
        confidence=0.85,
        agent_type="trend_agent",
        analysis_type="specialized_agent",
        market_data={
            'current_price': 95000,
            'rsi': 45,
            'ema_50': 94500,
            'ema_200': 92000,
            'atr_percent': 1.5,
            'macd': 150
        },
        advanced_data={
            'order_book': {'imbalance': 25.5, 'spread_percent': 0.02},
            'funding_rate': 0.0001
        },
        reasoning="Tendencia alcista confirmada con retroceso a EMA 50"
    )

    print("Decisión registrada correctamente")
