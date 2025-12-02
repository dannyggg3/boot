"""
Performance Attribution - Atribución de Rendimiento
=====================================================
Analiza qué estrategias, agentes y condiciones generan más alpha.

Permite responder preguntas como:
- ¿El trend_agent genera más ganancias que el reversal_agent?
- ¿En qué régimen de mercado ganamos más?
- ¿A qué hora del día tenemos mejor rendimiento?
- ¿Qué símbolos son más rentables?

Autor: Trading Bot System
Versión: 1.7
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os

logger = logging.getLogger(__name__)


class PerformanceAttributor:
    """
    Analizador de atribución de rendimiento.

    Descompone el rendimiento total en sus componentes para
    identificar qué está generando alpha y qué está destruyéndolo.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el atribuidor de rendimiento.

        Args:
            config: Configuración del bot
        """
        self.config = config

        # Historial de trades para análisis
        self.trade_history: List[Dict[str, Any]] = []

        # Métricas por dimensión
        self.by_agent: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'total_pnl_percent': 0.0
        })
        self.by_regime: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'total_pnl_percent': 0.0
        })
        self.by_symbol: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'total_pnl_percent': 0.0
        })
        self.by_hour: Dict[int, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'total_pnl_percent': 0.0
        })
        self.by_day: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'total_pnl': 0.0, 'total_pnl_percent': 0.0
        })

        # Cargar historial
        self._load_history()

        logger.info("Performance Attributor inicializado")

    def record_trade(
        self,
        symbol: str,
        side: str,
        pnl: float,
        pnl_percent: float,
        agent_type: str,
        regime: str,
        entry_time: Optional[datetime] = None,
        exit_time: Optional[datetime] = None,
        hold_time_minutes: int = 0,
        exit_reason: str = "unknown"
    ):
        """
        Registra un trade para análisis de atribución.

        Args:
            symbol: Símbolo operado
            side: 'long' o 'short'
            pnl: P&L en USD
            pnl_percent: P&L en porcentaje
            agent_type: Tipo de agente (trend_agent, reversal_agent, etc.)
            regime: Régimen de mercado
            entry_time: Hora de entrada
            exit_time: Hora de salida
            hold_time_minutes: Tiempo de holding
            exit_reason: Razón de salida (stop_loss, take_profit, etc.)
        """
        now = datetime.now()
        exit_time = exit_time or now
        entry_time = entry_time or (now - timedelta(minutes=hold_time_minutes))

        is_win = pnl > 0
        hour = entry_time.hour
        day_of_week = entry_time.strftime('%A')

        # Registrar en historial
        trade_record = {
            'timestamp': now.isoformat(),
            'symbol': symbol,
            'side': side,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'agent_type': agent_type,
            'regime': regime,
            'entry_hour': hour,
            'day_of_week': day_of_week,
            'hold_time_minutes': hold_time_minutes,
            'exit_reason': exit_reason,
            'is_win': is_win
        }
        self.trade_history.append(trade_record)

        # Actualizar métricas por agente
        self.by_agent[agent_type]['trades'] += 1
        self.by_agent[agent_type]['wins'] += 1 if is_win else 0
        self.by_agent[agent_type]['total_pnl'] += pnl
        self.by_agent[agent_type]['total_pnl_percent'] += pnl_percent

        # Por régimen
        self.by_regime[regime]['trades'] += 1
        self.by_regime[regime]['wins'] += 1 if is_win else 0
        self.by_regime[regime]['total_pnl'] += pnl
        self.by_regime[regime]['total_pnl_percent'] += pnl_percent

        # Por símbolo
        self.by_symbol[symbol]['trades'] += 1
        self.by_symbol[symbol]['wins'] += 1 if is_win else 0
        self.by_symbol[symbol]['total_pnl'] += pnl
        self.by_symbol[symbol]['total_pnl_percent'] += pnl_percent

        # Por hora
        self.by_hour[hour]['trades'] += 1
        self.by_hour[hour]['wins'] += 1 if is_win else 0
        self.by_hour[hour]['total_pnl'] += pnl
        self.by_hour[hour]['total_pnl_percent'] += pnl_percent

        # Por día
        self.by_day[day_of_week]['trades'] += 1
        self.by_day[day_of_week]['wins'] += 1 if is_win else 0
        self.by_day[day_of_week]['total_pnl'] += pnl
        self.by_day[day_of_week]['total_pnl_percent'] += pnl_percent

        # Guardar
        self._save_history()

    def get_agent_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene rendimiento por tipo de agente.

        Returns:
            Dict con métricas por agente
        """
        result = {}

        for agent, metrics in self.by_agent.items():
            trades = metrics['trades']
            if trades == 0:
                continue

            result[agent] = {
                'trades': trades,
                'wins': metrics['wins'],
                'win_rate': metrics['wins'] / trades,
                'total_pnl': round(metrics['total_pnl'], 2),
                'avg_pnl': round(metrics['total_pnl'] / trades, 2),
                'avg_pnl_percent': round(metrics['total_pnl_percent'] / trades, 2),
                'contribution_percent': 0  # Se calcula después
            }

        # Calcular contribución al P&L total
        total_pnl = sum(m['total_pnl'] for m in result.values())
        if total_pnl != 0:
            for agent in result:
                result[agent]['contribution_percent'] = round(
                    result[agent]['total_pnl'] / abs(total_pnl) * 100, 1
                )

        return result

    def get_regime_performance(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene rendimiento por régimen de mercado."""
        result = {}

        for regime, metrics in self.by_regime.items():
            trades = metrics['trades']
            if trades == 0:
                continue

            result[regime] = {
                'trades': trades,
                'wins': metrics['wins'],
                'win_rate': metrics['wins'] / trades,
                'total_pnl': round(metrics['total_pnl'], 2),
                'avg_pnl': round(metrics['total_pnl'] / trades, 2),
                'recommendation': self._get_regime_recommendation(
                    metrics['wins'] / trades,
                    metrics['total_pnl'] / trades
                )
            }

        return result

    def get_symbol_performance(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene rendimiento por símbolo."""
        result = {}

        for symbol, metrics in self.by_symbol.items():
            trades = metrics['trades']
            if trades == 0:
                continue

            result[symbol] = {
                'trades': trades,
                'wins': metrics['wins'],
                'win_rate': metrics['wins'] / trades,
                'total_pnl': round(metrics['total_pnl'], 2),
                'avg_pnl': round(metrics['total_pnl'] / trades, 2),
                'profitability': 'profitable' if metrics['total_pnl'] > 0 else 'unprofitable'
            }

        # Ordenar por P&L total
        return dict(sorted(result.items(), key=lambda x: x[1]['total_pnl'], reverse=True))

    def get_time_performance(self) -> Dict[str, Any]:
        """Obtiene rendimiento por hora y día."""
        # Por hora
        hourly = {}
        for hour, metrics in self.by_hour.items():
            trades = metrics['trades']
            if trades == 0:
                continue
            hourly[hour] = {
                'trades': trades,
                'win_rate': metrics['wins'] / trades,
                'avg_pnl': round(metrics['total_pnl'] / trades, 2)
            }

        # Por día
        daily = {}
        for day, metrics in self.by_day.items():
            trades = metrics['trades']
            if trades == 0:
                continue
            daily[day] = {
                'trades': trades,
                'win_rate': metrics['wins'] / trades,
                'avg_pnl': round(metrics['total_pnl'] / trades, 2)
            }

        # Encontrar mejores horas
        best_hours = sorted(hourly.items(), key=lambda x: x[1]['avg_pnl'], reverse=True)[:3]
        worst_hours = sorted(hourly.items(), key=lambda x: x[1]['avg_pnl'])[:3]

        # Encontrar mejores días
        best_days = sorted(daily.items(), key=lambda x: x[1]['avg_pnl'], reverse=True)[:2]

        return {
            'hourly': hourly,
            'daily': daily,
            'best_hours': [h[0] for h in best_hours] if best_hours else [],
            'worst_hours': [h[0] for h in worst_hours] if worst_hours else [],
            'best_days': [d[0] for d in best_days] if best_days else [],
            'recommendation': self._generate_time_recommendation(best_hours, worst_hours)
        }

    def _get_regime_recommendation(self, win_rate: float, avg_pnl: float) -> str:
        """Genera recomendación para un régimen."""
        if win_rate >= 0.60 and avg_pnl > 0:
            return "✅ Régimen favorable - Mantener o aumentar exposición"
        elif win_rate >= 0.50 and avg_pnl > 0:
            return "⚠️ Régimen neutral - Mantener exposición actual"
        elif win_rate < 0.45 or avg_pnl < 0:
            return "❌ Régimen desfavorable - Considerar reducir o evitar"
        return "📊 Datos insuficientes"

    def _generate_time_recommendation(
        self,
        best_hours: List,
        worst_hours: List
    ) -> str:
        """Genera recomendación basada en tiempo."""
        if not best_hours:
            return "Datos insuficientes para recomendación temporal"

        best = [str(h[0]) + ":00" for h in best_hours[:2]]
        worst = [str(h[0]) + ":00" for h in worst_hours[:2]]

        return (
            f"Mejores horas: {', '.join(best)}. "
            f"Evitar: {', '.join(worst)}."
        )

    def get_exit_reason_analysis(self) -> Dict[str, Dict[str, Any]]:
        """Analiza rendimiento por razón de salida."""
        by_exit = defaultdict(lambda: {'trades': 0, 'wins': 0, 'total_pnl': 0.0})

        for trade in self.trade_history:
            reason = trade.get('exit_reason', 'unknown')
            by_exit[reason]['trades'] += 1
            by_exit[reason]['wins'] += 1 if trade['is_win'] else 0
            by_exit[reason]['total_pnl'] += trade['pnl']

        result = {}
        for reason, metrics in by_exit.items():
            trades = metrics['trades']
            if trades == 0:
                continue
            result[reason] = {
                'trades': trades,
                'win_rate': metrics['wins'] / trades,
                'avg_pnl': round(metrics['total_pnl'] / trades, 2),
                'total_pnl': round(metrics['total_pnl'], 2)
            }

        return result

    def get_full_attribution_report(self) -> Dict[str, Any]:
        """
        Genera reporte completo de atribución de rendimiento.

        Returns:
            Dict con análisis completo
        """
        total_trades = len(self.trade_history)
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        total_wins = sum(1 for t in self.trade_history if t['is_win'])

        return {
            'summary': {
                'total_trades': total_trades,
                'total_wins': total_wins,
                'overall_win_rate': total_wins / total_trades if total_trades > 0 else 0,
                'total_pnl': round(total_pnl, 2),
                'avg_pnl_per_trade': round(total_pnl / total_trades, 2) if total_trades > 0 else 0
            },
            'by_agent': self.get_agent_performance(),
            'by_regime': self.get_regime_performance(),
            'by_symbol': self.get_symbol_performance(),
            'by_time': self.get_time_performance(),
            'by_exit_reason': self.get_exit_reason_analysis(),
            'recommendations': self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en el análisis."""
        recommendations = []

        # Analizar agentes
        agent_perf = self.get_agent_performance()
        if agent_perf:
            best_agent = max(agent_perf.items(), key=lambda x: x[1]['avg_pnl'])
            worst_agent = min(agent_perf.items(), key=lambda x: x[1]['avg_pnl'])

            if best_agent[1]['avg_pnl'] > 0 and worst_agent[1]['avg_pnl'] < 0:
                recommendations.append(
                    f"🔥 El {best_agent[0]} es más rentable (avg: ${best_agent[1]['avg_pnl']:.2f}). "
                    f"Considerar reducir uso de {worst_agent[0]} (avg: ${worst_agent[1]['avg_pnl']:.2f})."
                )

        # Analizar símbolos
        symbol_perf = self.get_symbol_performance()
        unprofitable = [s for s, m in symbol_perf.items() if m['total_pnl'] < 0]
        if unprofitable:
            recommendations.append(
                f"⚠️ Símbolos con pérdida neta: {', '.join(unprofitable)}. "
                f"Evaluar si deben seguir en el portfolio."
            )

        # Analizar regímenes
        regime_perf = self.get_regime_performance()
        for regime, metrics in regime_perf.items():
            if metrics['win_rate'] < 0.40:
                recommendations.append(
                    f"❌ Win rate bajo ({metrics['win_rate']:.0%}) en régimen '{regime}'. "
                    f"Considerar filtrar o ajustar estrategia."
                )

        if not recommendations:
            recommendations.append("✅ Rendimiento balanceado. Continuar monitoreando.")

        return recommendations

    def _save_history(self):
        """Guarda historial en archivo."""
        state_file = 'data/performance_attribution.json'
        os.makedirs('data', exist_ok=True)

        try:
            # Solo guardar últimos 200 trades
            data = {
                'trade_history': self.trade_history[-200:],
                'last_update': datetime.now().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando atribución: {e}")

    def _load_history(self):
        """Carga historial desde archivo."""
        state_file = 'data/performance_attribution.json'

        if not os.path.exists(state_file):
            return

        try:
            with open(state_file, 'r') as f:
                data = json.load(f)

            self.trade_history = data.get('trade_history', [])

            # Reconstruir métricas
            for trade in self.trade_history:
                is_win = trade.get('is_win', trade.get('pnl', 0) > 0)
                pnl = trade.get('pnl', 0)
                pnl_pct = trade.get('pnl_percent', 0)

                # Por agente
                agent = trade.get('agent_type', 'unknown')
                self.by_agent[agent]['trades'] += 1
                self.by_agent[agent]['wins'] += 1 if is_win else 0
                self.by_agent[agent]['total_pnl'] += pnl
                self.by_agent[agent]['total_pnl_percent'] += pnl_pct

                # Por régimen
                regime = trade.get('regime', 'unknown')
                self.by_regime[regime]['trades'] += 1
                self.by_regime[regime]['wins'] += 1 if is_win else 0
                self.by_regime[regime]['total_pnl'] += pnl

                # Por símbolo
                symbol = trade.get('symbol', 'unknown')
                self.by_symbol[symbol]['trades'] += 1
                self.by_symbol[symbol]['wins'] += 1 if is_win else 0
                self.by_symbol[symbol]['total_pnl'] += pnl

            logger.info(f"Historial de atribución cargado: {len(self.trade_history)} trades")

        except Exception as e:
            logger.error(f"Error cargando atribución: {e}")


# Singleton
_attributor = None


def get_performance_attributor(config: Dict[str, Any] = None) -> Optional[PerformanceAttributor]:
    """Obtiene singleton del atribuidor."""
    global _attributor
    if _attributor is None and config:
        _attributor = PerformanceAttributor(config)
    return _attributor
