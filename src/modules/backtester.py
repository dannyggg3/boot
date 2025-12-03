"""
Backtester Module - Backtesting para decisiones de trading
============================================================
v1.9 INSTITUCIONAL: Módulo de backtesting para validar estrategias.

Este módulo permite:
- Cargar datos históricos OHLCV
- Simular decisiones de trading basadas en indicadores técnicos
- Calcular métricas de rendimiento (Sharpe, Sortino, Max DD)
- Validar parámetros antes de trading real

NOTA: El backtesting de decisiones IA es limitado porque:
1. Los modelos tienen fecha de corte de entrenamiento (look-ahead bias)
2. Las llamadas reales a API son costosas para datos históricos

Por eso este módulo se enfoca en:
- Backtesting de reglas técnicas (indicadores)
- Validación de parámetros de riesgo
- Simulación de costos y slippage

Autor: Trading Bot System
Versión: 1.9
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import os

logger = logging.getLogger(__name__)


class BacktestMode(Enum):
    """Modos de backtesting disponibles."""
    TECHNICAL_ONLY = "technical"    # Solo indicadores técnicos
    RULE_BASED = "rule_based"       # Reglas definidas por usuario
    REPLAY = "replay"               # Replay de decisiones históricas


@dataclass
class BacktestTrade:
    """Representa un trade en el backtest."""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = ""
    side: str = ""  # 'long' or 'short'
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    exit_reason: str = ""
    fees: float = 0.0
    slippage: float = 0.0


@dataclass
class BacktestResult:
    """Resultados del backtest."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_duration_minutes: float = 0.0
    total_fees: float = 0.0
    net_pnl: float = 0.0
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class Backtester:
    """
    Motor de backtesting para validar estrategias de trading.

    Uso típico:
    ```python
    backtester = Backtester(config)
    result = backtester.run(
        data=ohlcv_data,
        strategy='ema_cross',
        initial_capital=10000
    )
    print(result.sharpe_ratio)
    ```
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializa el backtester.

        Args:
            config: Configuración del backtester
        """
        self.config = config or {}

        # Parámetros de simulación
        self.fee_rate = self.config.get('fee_rate', 0.001)  # 0.1% por trade
        self.slippage_rate = self.config.get('slippage_rate', 0.0005)  # 0.05%
        self.risk_free_rate = self.config.get('risk_free_rate', 0.05)  # 5% anual

        # Parámetros de riesgo
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 0.02)  # 2%
        self.default_stop_loss_pct = self.config.get('default_stop_loss_pct', 0.02)  # 2%
        self.default_take_profit_pct = self.config.get('default_take_profit_pct', 0.04)  # 4%

        logger.info("Backtester v1.9 inicializado")

    def run(
        self,
        data: List[List],
        strategy: str = 'ema_cross',
        initial_capital: float = 10000,
        symbol: str = "BTC/USDT"
    ) -> BacktestResult:
        """
        Ejecuta el backtest con los datos y estrategia especificados.

        Args:
            data: Datos OHLCV [[timestamp, open, high, low, close, volume], ...]
            strategy: Nombre de la estrategia a usar
            initial_capital: Capital inicial
            symbol: Símbolo del activo

        Returns:
            BacktestResult con métricas y trades
        """
        if not data or len(data) < 200:
            logger.warning("Datos insuficientes para backtest (mínimo 200 velas)")
            return BacktestResult()

        logger.info(f"Iniciando backtest: {strategy} con {len(data)} velas")

        # Seleccionar estrategia
        strategy_func = self._get_strategy(strategy)
        if not strategy_func:
            logger.error(f"Estrategia no encontrada: {strategy}")
            return BacktestResult()

        # Ejecutar simulación
        trades = self._simulate(data, strategy_func, initial_capital, symbol)

        # Calcular métricas
        result = self._calculate_metrics(trades, initial_capital)

        logger.info(f"Backtest completado: {result.total_trades} trades, "
                   f"Win Rate: {result.win_rate:.1f}%, "
                   f"Sharpe: {result.sharpe_ratio:.2f}")

        return result

    def _get_strategy(self, name: str):
        """Obtiene la función de estrategia por nombre."""
        strategies = {
            'ema_cross': self._strategy_ema_cross,
            'rsi_reversal': self._strategy_rsi_reversal,
            'macd_momentum': self._strategy_macd_momentum,
            'adx_trend': self._strategy_adx_trend,
            'combined': self._strategy_combined,
        }
        return strategies.get(name)

    def _simulate(
        self,
        data: List[List],
        strategy_func,
        initial_capital: float,
        symbol: str
    ) -> List[BacktestTrade]:
        """Ejecuta la simulación del backtest."""
        import pandas as pd
        import numpy as np

        # Convertir a DataFrame
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Calcular indicadores
        df = self._calculate_indicators(df)

        trades = []
        capital = initial_capital
        position = None

        # Iterar desde la vela 200 (para tener suficientes datos)
        for i in range(200, len(df)):
            current_bar = df.iloc[i]
            lookback = df.iloc[i-200:i]

            if position is None:
                # Buscar entrada
                signal = strategy_func(lookback, current_bar)

                if signal in ['COMPRA', 'VENTA']:
                    entry_price = float(current_bar['close'])

                    # Aplicar slippage
                    if signal == 'COMPRA':
                        entry_price *= (1 + self.slippage_rate)
                    else:
                        entry_price *= (1 - self.slippage_rate)

                    # Calcular tamaño de posición
                    risk_amount = capital * self.max_risk_per_trade
                    stop_distance = entry_price * self.default_stop_loss_pct
                    quantity = risk_amount / stop_distance

                    # Fees
                    fees = entry_price * quantity * self.fee_rate

                    # Crear posición
                    if signal == 'COMPRA':
                        sl = entry_price * (1 - self.default_stop_loss_pct)
                        tp = entry_price * (1 + self.default_take_profit_pct)
                        side = 'long'
                    else:
                        sl = entry_price * (1 + self.default_stop_loss_pct)
                        tp = entry_price * (1 - self.default_take_profit_pct)
                        side = 'short'

                    position = BacktestTrade(
                        entry_time=current_bar['timestamp'],
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        quantity=quantity,
                        stop_loss=sl,
                        take_profit=tp,
                        fees=fees
                    )

            else:
                # Verificar salida
                high = float(current_bar['high'])
                low = float(current_bar['low'])
                close = float(current_bar['close'])

                exit_price = None
                exit_reason = None

                if position.side == 'long':
                    if low <= position.stop_loss:
                        exit_price = position.stop_loss
                        exit_reason = 'stop_loss'
                    elif high >= position.take_profit:
                        exit_price = position.take_profit
                        exit_reason = 'take_profit'
                else:  # short
                    if high >= position.stop_loss:
                        exit_price = position.stop_loss
                        exit_reason = 'stop_loss'
                    elif low <= position.take_profit:
                        exit_price = position.take_profit
                        exit_reason = 'take_profit'

                if exit_price:
                    # Aplicar slippage a la salida
                    if position.side == 'long':
                        exit_price *= (1 - self.slippage_rate)
                    else:
                        exit_price *= (1 + self.slippage_rate)

                    # Calcular P&L
                    if position.side == 'long':
                        pnl = (exit_price - position.entry_price) * position.quantity
                    else:
                        pnl = (position.entry_price - exit_price) * position.quantity

                    # Fees de salida
                    exit_fees = exit_price * position.quantity * self.fee_rate
                    total_fees = position.fees + exit_fees
                    net_pnl = pnl - total_fees

                    # Actualizar posición
                    position.exit_time = current_bar['timestamp']
                    position.exit_price = exit_price
                    position.exit_reason = exit_reason
                    position.pnl = net_pnl
                    position.pnl_percent = (net_pnl / (position.entry_price * position.quantity)) * 100
                    position.fees = total_fees
                    position.slippage = self.slippage_rate * 2 * 100  # Round trip en %

                    trades.append(position)
                    capital += net_pnl
                    position = None

        return trades

    def _calculate_indicators(self, df) -> 'pd.DataFrame':
        """Calcula indicadores técnicos para el backtest."""
        import pandas as pd

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # EMAs
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        df['atr_pct'] = (df['atr'] / df['close']) * 100

        # ADX
        df = self._calculate_adx(df)

        return df

    def _calculate_adx(self, df, period: int = 14) -> 'pd.DataFrame':
        """Calcula el ADX para el backtest."""
        import pandas as pd

        # True Range
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # Smoothed averages
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=period).mean()
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di

        return df

    # =========================================================================
    # ESTRATEGIAS DE BACKTEST
    # =========================================================================

    def _strategy_ema_cross(self, lookback, current_bar) -> str:
        """Estrategia de cruce de EMAs."""
        ema_50 = float(current_bar['ema_50'])
        ema_200 = float(current_bar['ema_200'])
        prev_ema_50 = float(lookback['ema_50'].iloc[-2])
        prev_ema_200 = float(lookback['ema_200'].iloc[-2])

        # Golden Cross
        if prev_ema_50 <= prev_ema_200 and ema_50 > ema_200:
            return 'COMPRA'

        # Death Cross
        if prev_ema_50 >= prev_ema_200 and ema_50 < ema_200:
            return 'VENTA'

        return 'ESPERA'

    def _strategy_rsi_reversal(self, lookback, current_bar) -> str:
        """Estrategia de reversión por RSI extremo."""
        rsi = float(current_bar['rsi'])
        prev_rsi = float(lookback['rsi'].iloc[-2])

        # Sobreventa -> Rebote
        if prev_rsi < 30 and rsi > 30:
            return 'COMPRA'

        # Sobrecompra -> Caída
        if prev_rsi > 70 and rsi < 70:
            return 'VENTA'

        return 'ESPERA'

    def _strategy_macd_momentum(self, lookback, current_bar) -> str:
        """Estrategia de momentum MACD."""
        macd = float(current_bar['macd'])
        signal = float(current_bar['macd_signal'])
        prev_macd = float(lookback['macd'].iloc[-2])
        prev_signal = float(lookback['macd_signal'].iloc[-2])

        # Cruce alcista
        if prev_macd <= prev_signal and macd > signal:
            return 'COMPRA'

        # Cruce bajista
        if prev_macd >= prev_signal and macd < signal:
            return 'VENTA'

        return 'ESPERA'

    def _strategy_adx_trend(self, lookback, current_bar) -> str:
        """Estrategia de tendencia con ADX."""
        adx = float(current_bar['adx']) if not pd.isna(current_bar['adx']) else 0
        plus_di = float(current_bar['plus_di']) if not pd.isna(current_bar['plus_di']) else 0
        minus_di = float(current_bar['minus_di']) if not pd.isna(current_bar['minus_di']) else 0

        # Solo operar si hay tendencia fuerte (ADX > 25)
        if adx < 25:
            return 'ESPERA'

        # Tendencia alcista
        if plus_di > minus_di and plus_di > 25:
            return 'COMPRA'

        # Tendencia bajista
        if minus_di > plus_di and minus_di > 25:
            return 'VENTA'

        return 'ESPERA'

    def _strategy_combined(self, lookback, current_bar) -> str:
        """Estrategia combinada (similar al bot real)."""
        import pandas as pd

        # Indicadores
        rsi = float(current_bar['rsi'])
        ema_50 = float(current_bar['ema_50'])
        ema_200 = float(current_bar['ema_200'])
        macd = float(current_bar['macd'])
        macd_signal = float(current_bar['macd_signal'])
        adx = float(current_bar['adx']) if not pd.isna(current_bar['adx']) else 0
        price = float(current_bar['close'])

        # Puntuación de señal
        score = 0

        # 1. ADX - Solo operar si hay tendencia (filtro v1.9)
        if adx < 20:
            return 'ESPERA'

        # 2. Tendencia EMA
        if price > ema_200 and ema_50 > ema_200:
            score += 2  # Tendencia alcista
        elif price < ema_200 and ema_50 < ema_200:
            score -= 2  # Tendencia bajista

        # 3. RSI
        if rsi < 40:
            score += 1  # Potencial sobreventa
        elif rsi > 60:
            score -= 1  # Potencial sobrecompra

        # 4. MACD
        if macd > macd_signal:
            score += 1
        else:
            score -= 1

        # 5. ADX fuerte amplifica señal
        if adx > 40:
            score = int(score * 1.5)

        # Decisión
        if score >= 3:
            return 'COMPRA'
        elif score <= -3:
            return 'VENTA'

        return 'ESPERA'

    def _calculate_metrics(
        self,
        trades: List[BacktestTrade],
        initial_capital: float
    ) -> BacktestResult:
        """Calcula métricas de rendimiento del backtest."""
        import numpy as np

        result = BacktestResult()
        result.trades = trades

        if not trades:
            return result

        # Métricas básicas
        result.total_trades = len(trades)
        result.winning_trades = sum(1 for t in trades if t.pnl > 0)
        result.losing_trades = sum(1 for t in trades if t.pnl < 0)
        result.win_rate = (result.winning_trades / result.total_trades) * 100

        # P&L
        pnls = [t.pnl for t in trades]
        result.total_pnl = sum(pnls)
        result.total_fees = sum(t.fees for t in trades)
        result.net_pnl = result.total_pnl  # Ya incluye fees
        result.total_pnl_percent = (result.net_pnl / initial_capital) * 100

        # Avg Win/Loss
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl < 0]
        result.avg_win = np.mean(wins) if wins else 0
        result.avg_loss = np.mean(losses) if losses else 0

        # Profit Factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 1
        result.profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Equity Curve y Drawdown
        equity = initial_capital
        peak = initial_capital
        max_dd = 0
        equity_curve = [initial_capital]

        for trade in trades:
            equity += trade.pnl
            equity_curve.append(equity)

            if equity > peak:
                peak = equity

            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd

        result.equity_curve = equity_curve
        result.max_drawdown_percent = max_dd
        result.max_drawdown = peak - min(equity_curve)

        # Duración promedio
        durations = []
        for t in trades:
            if t.exit_time and t.entry_time:
                duration = (t.exit_time - t.entry_time).total_seconds() / 60
                durations.append(duration)
        result.avg_trade_duration_minutes = np.mean(durations) if durations else 0

        # Sharpe Ratio (simplificado)
        if len(pnls) > 1:
            returns = np.array(pnls) / initial_capital
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                # Anualizado asumiendo ~1000 trades/año
                result.sharpe_ratio = (avg_return * np.sqrt(365)) / std_return

        # Sortino Ratio
        negative_returns = [r for r in pnls if r < 0]
        if negative_returns:
            downside_std = np.std(negative_returns) / initial_capital
            if downside_std > 0:
                avg_return = np.mean(pnls) / initial_capital
                result.sortino_ratio = (avg_return * np.sqrt(365)) / downside_std

        return result

    def generate_report(self, result: BacktestResult) -> str:
        """Genera un reporte legible del backtest."""
        report = []
        report.append("=" * 60)
        report.append("REPORTE DE BACKTEST v1.9")
        report.append("=" * 60)
        report.append("")
        report.append("RESUMEN DE RENDIMIENTO")
        report.append("-" * 40)
        report.append(f"Total Trades:          {result.total_trades}")
        report.append(f"Trades Ganadores:      {result.winning_trades}")
        report.append(f"Trades Perdedores:     {result.losing_trades}")
        report.append(f"Win Rate:              {result.win_rate:.1f}%")
        report.append("")
        report.append(f"P&L Total:             ${result.total_pnl:,.2f}")
        report.append(f"P&L Neto (- fees):     ${result.net_pnl:,.2f}")
        report.append(f"P&L %:                 {result.total_pnl_percent:.2f}%")
        report.append(f"Total Fees:            ${result.total_fees:,.2f}")
        report.append("")
        report.append("MÉTRICAS DE RIESGO")
        report.append("-" * 40)
        report.append(f"Max Drawdown:          {result.max_drawdown_percent:.2f}%")
        report.append(f"Sharpe Ratio:          {result.sharpe_ratio:.2f}")
        report.append(f"Sortino Ratio:         {result.sortino_ratio:.2f}")
        report.append(f"Profit Factor:         {result.profit_factor:.2f}")
        report.append("")
        report.append("ESTADÍSTICAS DE TRADES")
        report.append("-" * 40)
        report.append(f"Ganancia Promedio:     ${result.avg_win:,.2f}")
        report.append(f"Pérdida Promedio:      ${result.avg_loss:,.2f}")
        report.append(f"Duración Promedio:     {result.avg_trade_duration_minutes:.0f} min")
        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


# Importar pandas para type hints
try:
    import pandas as pd
except ImportError:
    pd = None


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)

    # Generar datos de prueba
    import random

    test_data = []
    base_price = 50000

    for i in range(500):
        timestamp = 1700000000000 + (i * 3600000)  # 1 hora entre velas
        open_price = base_price + random.uniform(-100, 100)
        high_price = open_price + random.uniform(0, 300)
        low_price = open_price - random.uniform(0, 300)
        close_price = (high_price + low_price) / 2 + random.uniform(-50, 50)
        volume = random.uniform(100, 500)

        test_data.append([timestamp, open_price, high_price, low_price, close_price, volume])
        base_price = close_price * (1 + random.uniform(-0.01, 0.01))

    # Ejecutar backtest
    bt = Backtester()
    result = bt.run(test_data, strategy='combined', initial_capital=10000)

    print(bt.generate_report(result))
