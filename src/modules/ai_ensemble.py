"""
AI Ensemble - Sistema de consenso multi-modelo
==============================================
Combina múltiples análisis de IA para decisiones más robustas.
Implementa votación ponderada y calibración de confianza.

Autor: Trading Bot System
Versión: 1.6
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, stdev
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ModelVote:
    """Voto de un modelo individual."""
    model_name: str
    decision: str  # COMPRA, VENTA, ESPERA
    confidence: float
    reasoning: str
    response_time_ms: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class EnsembleDecision:
    """Decisión final del ensemble."""
    decision: str
    confidence: float
    consensus_strength: float  # 0-1, qué tan de acuerdo están los modelos
    votes: List[ModelVote] = field(default_factory=list)
    reasoning: str = ""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    analysis_type: str = "ensemble"


class ModelPerformanceTracker:
    """
    Rastrea el rendimiento de cada modelo para ajustar pesos.
    Implementa un sistema de aprendizaje simple basado en resultados.
    """

    def __init__(self):
        """Inicializa el tracker."""
        self._performance: Dict[str, Dict] = defaultdict(lambda: {
            'total_predictions': 0,
            'correct_predictions': 0,
            'total_pnl': 0.0,
            'avg_confidence': 0.0,
            'calibration_error': 0.0,  # Diferencia entre confianza predicha y real
            'weight': 1.0
        })

    def record_prediction(
        self,
        model_name: str,
        decision: str,
        confidence: float,
        actual_outcome: str = None,
        pnl: float = 0.0
    ):
        """
        Registra una predicción y su resultado.

        Args:
            model_name: Nombre del modelo
            decision: Decisión tomada
            confidence: Confianza reportada
            actual_outcome: Resultado real (win/loss/none)
            pnl: P&L del trade
        """
        perf = self._performance[model_name]
        perf['total_predictions'] += 1

        # Actualizar promedio de confianza
        n = perf['total_predictions']
        old_avg = perf['avg_confidence']
        perf['avg_confidence'] = (old_avg * (n - 1) + confidence) / n

        if actual_outcome:
            if actual_outcome == 'win':
                perf['correct_predictions'] += 1
            perf['total_pnl'] += pnl

            # Calcular error de calibración
            expected_win_rate = confidence
            actual_win_rate = perf['correct_predictions'] / n
            perf['calibration_error'] = abs(expected_win_rate - actual_win_rate)

            # Ajustar peso basado en rendimiento
            self._update_weight(model_name)

    def _update_weight(self, model_name: str):
        """Actualiza el peso del modelo basado en su rendimiento."""
        perf = self._performance[model_name]

        if perf['total_predictions'] < 10:
            return  # No ajustar hasta tener suficientes datos

        # Peso basado en win rate y calibración
        win_rate = perf['correct_predictions'] / perf['total_predictions']
        calibration_score = 1 - perf['calibration_error']

        # Peso = 50% win rate + 30% calibración + 20% baseline
        new_weight = (0.5 * win_rate + 0.3 * calibration_score + 0.2)

        # Suavizar cambios (exponential moving average)
        perf['weight'] = 0.8 * perf['weight'] + 0.2 * new_weight

    def get_weight(self, model_name: str) -> float:
        """Obtiene el peso actual de un modelo."""
        return self._performance[model_name]['weight']

    def get_model_stats(self, model_name: str) -> Dict[str, Any]:
        """Obtiene estadísticas de un modelo."""
        perf = self._performance[model_name]
        total = perf['total_predictions']

        return {
            'model': model_name,
            'total_predictions': total,
            'win_rate': (
                perf['correct_predictions'] / total * 100
                if total > 0 else 0
            ),
            'total_pnl': round(perf['total_pnl'], 2),
            'avg_confidence': round(perf['avg_confidence'], 2),
            'calibration_error': round(perf['calibration_error'], 3),
            'weight': round(perf['weight'], 3)
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        """Obtiene estadísticas de todos los modelos."""
        return {
            name: self.get_model_stats(name)
            for name in self._performance.keys()
        }


class AIEnsemble:
    """
    Sistema de ensemble que combina múltiples análisis de IA.

    Características:
    - Votación ponderada por rendimiento histórico
    - Calibración de confianza
    - Consenso requerido para trades
    - Diversificación de opiniones
    """

    def __init__(
        self,
        ai_engine,
        config: Dict[str, Any],
        min_consensus: float = 0.6,
        min_models_agree: int = 2
    ):
        """
        Inicializa el ensemble.

        Args:
            ai_engine: Motor de IA base
            config: Configuración del bot
            min_consensus: Consenso mínimo para trade (0-1)
            min_models_agree: Mínimo de modelos que deben estar de acuerdo
        """
        self.ai_engine = ai_engine
        self.config = config
        self.min_consensus = min_consensus
        self.min_models_agree = min_models_agree

        self.performance_tracker = ModelPerformanceTracker()

        # Configurar modelos disponibles
        self._setup_models()

        logger.info(f"AIEnsemble inicializado (consenso mínimo: {min_consensus*100}%)")

    def _setup_models(self):
        """Configura los modelos disponibles."""
        self.models = []

        # Modelo rápido para screening inicial
        if self.ai_engine.client:
            self.models.append({
                'name': 'fast_model',
                'type': 'fast',
                'model_id': self.config.get('ai_model_fast', 'deepseek-chat'),
                'weight_multiplier': 1.0
            })

        # Modelo profundo para análisis detallado
        if self.config.get('ai_use_hybrid_analysis'):
            self.models.append({
                'name': 'deep_model',
                'type': 'deep',
                'model_id': self.config.get('ai_model_deep', 'deepseek-reasoner'),
                'weight_multiplier': 1.2  # Más peso al modelo profundo
            })

        # Agentes especializados si están habilitados
        if self.config.get('ai_agents', {}).get('enabled'):
            self.models.append({
                'name': 'specialized_agents',
                'type': 'agents',
                'model_id': 'agents_v2',
                'weight_multiplier': 1.1
            })

        logger.info(f"Modelos configurados: {[m['name'] for m in self.models]}")

    def analyze(
        self,
        technical_data: Dict[str, Any],
        advanced_data: Optional[Dict[str, Any]] = None
    ) -> EnsembleDecision:
        """
        Realiza análisis ensemble de un símbolo.

        Args:
            technical_data: Datos técnicos
            advanced_data: Datos avanzados (order book, funding, etc.)

        Returns:
            EnsembleDecision con la decisión final
        """
        votes: List[ModelVote] = []
        symbol = technical_data.get('symbol', 'UNKNOWN')

        # Obtener votos de cada modelo
        for model_config in self.models:
            try:
                vote = self._get_model_vote(model_config, technical_data, advanced_data)
                if vote:
                    votes.append(vote)
            except Exception as e:
                logger.error(f"Error obteniendo voto de {model_config['name']}: {e}")

        if not votes:
            return EnsembleDecision(
                decision='ESPERA',
                confidence=0.0,
                consensus_strength=0.0,
                reasoning="No se pudieron obtener análisis"
            )

        # Calcular decisión final
        return self._aggregate_votes(votes, symbol)

    def _get_model_vote(
        self,
        model_config: Dict,
        technical_data: Dict,
        advanced_data: Optional[Dict]
    ) -> Optional[ModelVote]:
        """Obtiene el voto de un modelo específico."""
        start_time = time.time()
        model_name = model_config['name']
        model_type = model_config['type']

        try:
            # Ejecutar análisis según tipo de modelo
            if model_type == 'fast':
                result = self.ai_engine.analyze_market(technical_data)
            elif model_type == 'deep':
                result = self.ai_engine.analyze_market_hybrid(technical_data)
            elif model_type == 'agents':
                result = self.ai_engine.analyze_market_v2(technical_data, advanced_data)
            else:
                return None

            if not result:
                return None

            response_time = (time.time() - start_time) * 1000

            return ModelVote(
                model_name=model_name,
                decision=result.get('decision', 'ESPERA'),
                confidence=float(result.get('confidence', 0.0)),
                reasoning=result.get('razonamiento', ''),
                response_time_ms=response_time,
                stop_loss=result.get('stop_loss_sugerido'),
                take_profit=result.get('take_profit_sugerido')
            )

        except Exception as e:
            logger.error(f"Error en modelo {model_name}: {e}")
            return None

    def _aggregate_votes(self, votes: List[ModelVote], symbol: str) -> EnsembleDecision:
        """
        Agrega los votos para producir una decisión final.

        Implementa votación ponderada con ajuste por rendimiento histórico.
        """
        # Agrupar votos por decisión
        decision_weights: Dict[str, float] = defaultdict(float)
        decision_votes: Dict[str, List[ModelVote]] = defaultdict(list)

        for vote in votes:
            # Obtener peso del modelo basado en rendimiento
            base_weight = self.performance_tracker.get_weight(vote.model_name)

            # Aplicar multiplicador del modelo
            model_config = next(
                (m for m in self.models if m['name'] == vote.model_name),
                {'weight_multiplier': 1.0}
            )
            weight = base_weight * model_config['weight_multiplier']

            # Peso final = peso del modelo * confianza del voto
            final_weight = weight * vote.confidence

            decision_weights[vote.decision] += final_weight
            decision_votes[vote.decision].append(vote)

        # Determinar decisión ganadora
        if not decision_weights:
            return EnsembleDecision(
                decision='ESPERA',
                confidence=0.0,
                consensus_strength=0.0,
                votes=votes,
                reasoning="No hay votos válidos"
            )

        total_weight = sum(decision_weights.values())
        winning_decision = max(decision_weights, key=decision_weights.get)
        winning_weight = decision_weights[winning_decision]

        # Calcular fuerza de consenso
        consensus_strength = winning_weight / total_weight if total_weight > 0 else 0

        # Calcular confianza final (promedio ponderado de votos ganadores)
        winning_votes = decision_votes[winning_decision]
        if winning_votes:
            confidence = mean(v.confidence for v in winning_votes)
        else:
            confidence = 0.0

        # Verificar si hay suficiente consenso
        if consensus_strength < self.min_consensus:
            logger.info(f"[{symbol}] Consenso insuficiente: {consensus_strength:.2f} < {self.min_consensus}")
            return EnsembleDecision(
                decision='ESPERA',
                confidence=confidence,
                consensus_strength=consensus_strength,
                votes=votes,
                reasoning=f"Consenso insuficiente ({consensus_strength:.0%})"
            )

        if len(winning_votes) < self.min_models_agree:
            logger.info(f"[{symbol}] Pocos modelos de acuerdo: {len(winning_votes)} < {self.min_models_agree}")
            return EnsembleDecision(
                decision='ESPERA',
                confidence=confidence,
                consensus_strength=consensus_strength,
                votes=votes,
                reasoning=f"Solo {len(winning_votes)} modelos de acuerdo"
            )

        # Agregar SL/TP (usar mediana de los votos válidos)
        sl_values = [v.stop_loss for v in winning_votes if v.stop_loss]
        tp_values = [v.take_profit for v in winning_votes if v.take_profit]

        stop_loss = self._median(sl_values) if sl_values else None
        take_profit = self._median(tp_values) if tp_values else None

        # Construir razonamiento combinado
        reasoning = self._build_combined_reasoning(winning_votes, consensus_strength)

        logger.info(f"[{symbol}] Ensemble: {winning_decision} ({consensus_strength:.0%} consenso, {confidence:.0%} conf)")

        return EnsembleDecision(
            decision=winning_decision,
            confidence=confidence,
            consensus_strength=consensus_strength,
            votes=votes,
            reasoning=reasoning,
            stop_loss=stop_loss,
            take_profit=take_profit,
            analysis_type="ensemble"
        )

    def _build_combined_reasoning(
        self,
        votes: List[ModelVote],
        consensus: float
    ) -> str:
        """Construye razonamiento combinado de los votos."""
        parts = [f"Consenso: {consensus:.0%}"]

        for vote in votes[:3]:  # Máximo 3 razonamientos
            if vote.reasoning:
                short_reason = vote.reasoning[:100]
                parts.append(f"[{vote.model_name}]: {short_reason}")

        return " | ".join(parts)

    @staticmethod
    def _median(values: List[float]) -> float:
        """Calcula la mediana de una lista."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        return sorted_values[n//2]

    def record_outcome(
        self,
        votes: List[ModelVote],
        actual_outcome: str,
        pnl: float
    ):
        """
        Registra el resultado de un trade para ajustar pesos.

        Args:
            votes: Votos que se usaron para la decisión
            actual_outcome: 'win' o 'loss'
            pnl: P&L del trade
        """
        for vote in votes:
            self.performance_tracker.record_prediction(
                model_name=vote.model_name,
                decision=vote.decision,
                confidence=vote.confidence,
                actual_outcome=actual_outcome,
                pnl=pnl
            )

    def get_model_statistics(self) -> Dict[str, Dict]:
        """Obtiene estadísticas de rendimiento de todos los modelos."""
        return self.performance_tracker.get_all_stats()
