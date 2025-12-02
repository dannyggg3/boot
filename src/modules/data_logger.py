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

    # ==================== MÉTRICAS DE SISTEMA v1.6 ====================

    def log_system_health(
        self,
        health_status: int,
        api_latency_ms: float,
        api_success_rate: float,
        memory_usage_mb: float = 0,
        cpu_usage_percent: float = 0
    ):
        """
        Registra estado de salud del sistema.

        Args:
            health_status: 0=HEALTHY, 1=DEGRADED, 2=UNHEALTHY
            api_latency_ms: Latencia promedio de API en ms
            api_success_rate: Tasa de éxito de API (0-100)
            memory_usage_mb: Uso de memoria en MB
            cpu_usage_percent: Uso de CPU en porcentaje
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("system_health") \
                .field("health_status", int(health_status)) \
                .field("api_latency_ms", float(api_latency_ms)) \
                .field("api_success_rate", float(api_success_rate)) \
                .field("memory_usage_mb", float(memory_usage_mb)) \
                .field("cpu_usage_percent", float(cpu_usage_percent)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"System health logged: status={health_status}")

        except Exception as e:
            logger.error(f"Error guardando system health: {e}")

    def log_circuit_breaker(
        self,
        state: str,
        failure_count: int = 0,
        last_failure_time: str = "",
        cooldown_remaining_seconds: int = 0
    ):
        """
        Registra estado del circuit breaker.

        Args:
            state: CLOSED, HALF_OPEN, OPEN
            failure_count: Número de fallos consecutivos
            last_failure_time: Timestamp del último fallo
            cooldown_remaining_seconds: Segundos restantes de cooldown
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("circuit_breaker") \
                .field("state", state) \
                .field("failure_count", int(failure_count)) \
                .field("last_failure_time", last_failure_time) \
                .field("cooldown_remaining_seconds", int(cooldown_remaining_seconds)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Circuit breaker logged: state={state}")

        except Exception as e:
            logger.error(f"Error guardando circuit breaker: {e}")

    def log_ai_ensemble(
        self,
        consensus_strength: float,
        models_agreed: int,
        total_models: int,
        final_decision: str,
        model_votes: Dict[str, str] = None
    ):
        """
        Registra decisión del ensemble de IA.

        Args:
            consensus_strength: Fuerza del consenso (0-1)
            models_agreed: Número de modelos de acuerdo
            total_models: Total de modelos consultados
            final_decision: Decisión final (COMPRA, VENTA, ESPERA)
            model_votes: Votos de cada modelo {model_name: decision}
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("ai_ensemble") \
                .tag("final_decision", final_decision) \
                .field("consensus_strength", float(consensus_strength)) \
                .field("models_agreed", int(models_agreed)) \
                .field("total_models", int(total_models)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)

            # Log individual votes if provided
            if model_votes:
                for model_name, vote in model_votes.items():
                    vote_point = Point("ai_ensemble") \
                        .tag("model_name", model_name) \
                        .tag("vote", vote) \
                        .field("votes", 1) \
                        .time(datetime.utcnow(), WritePrecision.NS)
                    self.write_api.write(bucket=self.bucket, org=self.org, record=vote_point)

            logger.debug(f"AI ensemble logged: consensus={consensus_strength:.0%}")

        except Exception as e:
            logger.error(f"Error guardando ai ensemble: {e}")

    # ==================== MÉTRICAS INSTITUCIONALES v1.7 ====================

    def log_institutional_metrics(
        self,
        sharpe_ratio: float,
        sortino_ratio: float,
        calmar_ratio: float,
        max_drawdown: float,
        current_capital: float,
        peak_capital: float
    ):
        """
        Registra métricas institucionales de performance.

        Args:
            sharpe_ratio: Sharpe Ratio (30 días)
            sortino_ratio: Sortino Ratio (30 días)
            calmar_ratio: Calmar Ratio
            max_drawdown: Maximum Drawdown en porcentaje
            current_capital: Capital actual
            peak_capital: Capital máximo histórico
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("institutional_metrics") \
                .field("sharpe_ratio", float(sharpe_ratio)) \
                .field("sortino_ratio", float(sortino_ratio)) \
                .field("calmar_ratio", float(calmar_ratio)) \
                .field("max_drawdown", float(max_drawdown)) \
                .field("current_capital", float(current_capital)) \
                .field("peak_capital", float(peak_capital)) \
                .field("drawdown_current", float((peak_capital - current_capital) / peak_capital * 100) if peak_capital > 0 else 0) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug("Métricas institucionales registradas en InfluxDB")

        except Exception as e:
            logger.error(f"Error guardando métricas institucionales: {e}")

    def log_execution_quality(
        self,
        latency_p50: float,
        latency_p95: float,
        latency_p99: float,
        slippage_avg: float,
        slippage_max: float,
        fill_rate: float
    ):
        """
        Registra métricas de calidad de ejecución.

        Args:
            latency_p50: Latencia P50 en ms
            latency_p95: Latencia P95 en ms
            latency_p99: Latencia P99 en ms
            slippage_avg: Slippage promedio en porcentaje
            slippage_max: Slippage máximo en porcentaje
            fill_rate: Fill rate de órdenes limit en porcentaje
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("execution_quality") \
                .field("latency_p50", float(latency_p50)) \
                .field("latency_p95", float(latency_p95)) \
                .field("latency_p99", float(latency_p99)) \
                .field("slippage_avg", float(slippage_avg)) \
                .field("slippage_max", float(slippage_max)) \
                .field("fill_rate", float(fill_rate)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug("Métricas de ejecución registradas en InfluxDB")

        except Exception as e:
            logger.error(f"Error guardando métricas de ejecución: {e}")

    def log_regime_performance(
        self,
        regime: str,
        win_rate: float,
        total_trades: int,
        total_pnl: float
    ):
        """
        Registra performance por régimen de mercado.

        Args:
            regime: Tipo de régimen (trend, reversal, range)
            win_rate: Win rate en porcentaje
            total_trades: Total de trades
            total_pnl: PnL total en USD
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("regime_performance") \
                .tag("regime", regime) \
                .field("win_rate", float(win_rate)) \
                .field("total_trades", int(total_trades)) \
                .field("total_pnl", float(total_pnl)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Performance de régimen {regime} registrada")

        except Exception as e:
            logger.error(f"Error guardando performance de régimen: {e}")

    def log_slippage_alert(
        self,
        symbol: str,
        expected_price: float,
        actual_price: float,
        slippage_percent: float
    ):
        """
        Registra alertas de slippage alto para análisis.

        Args:
            symbol: Par de trading
            expected_price: Precio esperado
            actual_price: Precio real de ejecución
            slippage_percent: Slippage en porcentaje
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("slippage_alert") \
                .tag("symbol", symbol) \
                .field("expected_price", float(expected_price)) \
                .field("actual_price", float(actual_price)) \
                .field("slippage_percent", float(slippage_percent)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.warning(f"⚠️ Slippage alert logged: {symbol} {slippage_percent:.3f}%")

        except Exception as e:
            logger.error(f"Error guardando alerta de slippage: {e}")

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

    # ==================== MÉTRICAS v1.7+ INSTITUCIONAL SUPERIOR ====================

    def log_mtf_analysis(
        self,
        symbol: str,
        higher_tf: str,
        higher_direction: str,
        medium_tf: str,
        medium_direction: str,
        lower_tf: str,
        lower_direction: str,
        alignment_score: float,
        signal: str
    ):
        """
        Registra análisis Multi-Timeframe.

        Args:
            symbol: Par de trading
            higher_tf: Timeframe superior (ej: 4h)
            higher_direction: Dirección del TF superior
            medium_tf: Timeframe medio (ej: 1h)
            medium_direction: Dirección del TF medio
            lower_tf: Timeframe inferior (ej: 15m)
            lower_direction: Dirección del TF inferior
            alignment_score: Score de alineación (0-1)
            signal: Señal resultante (COMPRA, VENTA, ESPERA)
        """
        if not self.enabled or not self.write_api:
            return

        try:
            # Determinar si está alineado (>= 70%)
            aligned = alignment_score >= 0.70
            # Calcular confidence boost (0% a 20% basado en alignment)
            confidence_boost = max(0, (alignment_score - 0.70) / 0.30 * 0.20) if aligned else 0

            point = Point("mtf_analysis") \
                .tag("symbol", symbol) \
                .tag("signal", signal) \
                .tag("higher_direction", higher_direction) \
                .tag("medium_direction", medium_direction) \
                .tag("lower_direction", lower_direction) \
                .field("alignment_score", float(alignment_score)) \
                .field("aligned", aligned) \
                .field("confidence_boost", float(confidence_boost)) \
                .field("higher_tf", higher_tf) \
                .field("medium_tf", medium_tf) \
                .field("lower_tf", lower_tf) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"MTF analysis logged: {symbol} alignment={alignment_score:.0%}")

        except Exception as e:
            logger.error(f"Error guardando MTF analysis: {e}")

    def log_correlation_check(
        self,
        symbol: str,
        blocked: bool,
        blocking_symbol: str = "",
        correlation: float = 0.0,
        diversification_score: float = 1.0
    ):
        """
        Registra verificación de correlación.

        Args:
            symbol: Par que intentó abrir
            blocked: Si fue bloqueado por correlación
            blocking_symbol: Símbolo que causó el bloqueo
            correlation: Correlación encontrada
            diversification_score: Score de diversificación actual
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("correlation_check") \
                .tag("symbol", symbol) \
                .tag("blocked", str(blocked)) \
                .tag("blocking_symbol", blocking_symbol or "none") \
                .field("correlation", float(correlation)) \
                .field("max_correlation", float(correlation)) \
                .field("diversification_score", float(diversification_score)) \
                .field("allowed", not blocked) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Correlation check logged: {symbol} blocked={blocked}")

        except Exception as e:
            logger.error(f"Error guardando correlation check: {e}")

    def log_adaptive_params(
        self,
        min_confidence: float,
        max_risk: float,
        trailing_activation: float,
        scan_interval: int,
        win_rate: float,
        loss_streak: int,
        win_streak: int,
        volatility: str
    ):
        """
        Registra estado de parámetros adaptativos.

        Args:
            min_confidence: Confianza mínima actual
            max_risk: Riesgo máximo actual
            trailing_activation: Activación de trailing actual
            scan_interval: Intervalo de escaneo actual
            win_rate: Win rate reciente
            loss_streak: Racha de pérdidas actual
            win_streak: Racha de ganancias actual
            volatility: Nivel de volatilidad actual
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("adaptive_params") \
                .tag("volatility", volatility) \
                .field("min_confidence", float(min_confidence)) \
                .field("max_risk", float(max_risk)) \
                .field("trailing_activation", float(trailing_activation)) \
                .field("scan_interval", int(scan_interval)) \
                .field("win_rate", float(win_rate)) \
                .field("loss_streak", int(loss_streak)) \
                .field("win_streak", int(win_streak)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Adaptive params logged: conf={min_confidence:.2f} risk={max_risk:.2f}")

        except Exception as e:
            logger.error(f"Error guardando adaptive params: {e}")

    def log_performance_attribution(
        self,
        agent_type: str,
        regime: str,
        symbol: str,
        trades: int,
        win_rate: float,
        total_pnl: float,
        avg_pnl: float
    ):
        """
        Registra atribución de rendimiento.

        Args:
            agent_type: Tipo de agente
            regime: Régimen de mercado
            symbol: Símbolo
            trades: Número de trades
            win_rate: Win rate
            total_pnl: P&L total
            avg_pnl: P&L promedio
        """
        if not self.enabled or not self.write_api:
            return

        try:
            point = Point("performance_attribution") \
                .tag("agent_type", agent_type) \
                .tag("regime", regime) \
                .tag("symbol", symbol) \
                .field("trades", int(trades)) \
                .field("win_rate", float(win_rate)) \
                .field("total_pnl", float(total_pnl)) \
                .field("avg_pnl", float(avg_pnl)) \
                .time(datetime.utcnow(), WritePrecision.NS)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Attribution logged: {agent_type}/{regime}/{symbol}")

        except Exception as e:
            logger.error(f"Error guardando attribution: {e}")

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
