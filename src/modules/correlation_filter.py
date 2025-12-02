"""
Correlation Filter - Filtro de Correlación
============================================
Evita sobreexposición a activos altamente correlacionados.

Problema: Si tienes LONG en BTC y LONG en ETH (correlación 0.85),
tu riesgo real es casi el doble del percibido.

Solución: No abrir posiciones en activos con correlación > 0.70
si ya tienes posición en un activo correlacionado.

Autor: Trading Bot System
Versión: 1.7
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class CorrelationFilter:
    """
    Filtro de correlación para gestión de riesgo de portfolio.

    Evita que el bot abra posiciones en activos altamente correlacionados,
    lo que reduciría la diversificación efectiva.
    """

    # Correlaciones históricas típicas en crypto (actualizables)
    # Fuente: Datos históricos 2023-2024
    DEFAULT_CORRELATIONS = {
        ('BTC/USDT', 'ETH/USDT'): 0.85,
        ('BTC/USDT', 'SOL/USDT'): 0.78,
        ('BTC/USDT', 'XRP/USDT'): 0.72,
        ('BTC/USDT', 'BNB/USDT'): 0.80,
        ('ETH/USDT', 'SOL/USDT'): 0.82,
        ('ETH/USDT', 'XRP/USDT'): 0.68,
        ('ETH/USDT', 'BNB/USDT'): 0.75,
        ('SOL/USDT', 'XRP/USDT'): 0.65,
        ('SOL/USDT', 'BNB/USDT'): 0.70,
    }

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el filtro de correlación.

        Args:
            config: Configuración del bot
        """
        self.config = config

        # Configuración de correlación
        corr_config = config.get('correlation_filter', {})
        self.enabled = corr_config.get('enabled', True)

        # Umbral de correlación para bloquear
        self.max_correlation = corr_config.get('max_correlation', 0.70)

        # Correlaciones personalizadas (pueden sobrescribir defaults)
        custom_correlations = corr_config.get('correlations', {})
        self.correlations = self.DEFAULT_CORRELATIONS.copy()

        # Agregar correlaciones personalizadas
        for pair_str, corr_value in custom_correlations.items():
            # Formato esperado: "BTC/USDT,ETH/USDT": 0.85
            if ',' in pair_str:
                symbols = tuple(pair_str.split(','))
                self.correlations[symbols] = corr_value

        # Cache de correlaciones calculadas dinámicamente
        self._dynamic_correlations: Dict[tuple, float] = {}
        self._cache_expiry: Optional[datetime] = None
        self._cache_duration = timedelta(hours=4)

        logger.info(f"Correlation Filter: enabled={self.enabled}, max_corr={self.max_correlation}")

    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Obtiene la correlación entre dos símbolos.

        Args:
            symbol1: Primer símbolo
            symbol2: Segundo símbolo

        Returns:
            Coeficiente de correlación (0-1)
        """
        if symbol1 == symbol2:
            return 1.0

        # Normalizar orden para búsqueda consistente
        pair = tuple(sorted([symbol1, symbol2]))

        # Buscar en correlaciones dinámicas primero
        if pair in self._dynamic_correlations:
            return self._dynamic_correlations[pair]

        # Buscar en correlaciones default/configuradas
        if pair in self.correlations:
            return self.correlations[pair]

        # Buscar en orden inverso
        pair_reversed = (pair[1], pair[0])
        if pair_reversed in self.correlations:
            return self.correlations[pair_reversed]

        # Default: asumir correlación moderada si no se conoce
        return 0.50

    def calculate_dynamic_correlation(
        self,
        returns1: List[float],
        returns2: List[float]
    ) -> float:
        """
        Calcula correlación dinámica basada en retornos recientes.

        Args:
            returns1: Lista de retornos del activo 1
            returns2: Lista de retornos del activo 2

        Returns:
            Coeficiente de correlación de Pearson
        """
        if len(returns1) < 20 or len(returns2) < 20:
            return 0.50  # Default si no hay suficientes datos

        # Asegurar misma longitud
        min_len = min(len(returns1), len(returns2))
        r1 = np.array(returns1[-min_len:])
        r2 = np.array(returns2[-min_len:])

        # Calcular correlación de Pearson
        correlation = np.corrcoef(r1, r2)[0, 1]

        return abs(correlation) if not np.isnan(correlation) else 0.50

    def update_dynamic_correlation(
        self,
        symbol1: str,
        symbol2: str,
        returns1: List[float],
        returns2: List[float]
    ):
        """
        Actualiza la correlación dinámica entre dos símbolos.

        Args:
            symbol1: Primer símbolo
            symbol2: Segundo símbolo
            returns1: Retornos del activo 1
            returns2: Retornos del activo 2
        """
        pair = tuple(sorted([symbol1, symbol2]))
        correlation = self.calculate_dynamic_correlation(returns1, returns2)
        self._dynamic_correlations[pair] = correlation
        self._cache_expiry = datetime.now() + self._cache_duration

        logger.debug(f"Correlación dinámica actualizada: {pair} = {correlation:.3f}")

    def can_open_position(
        self,
        symbol: str,
        open_positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verifica si se puede abrir posición sin violar límites de correlación.

        Args:
            symbol: Símbolo a evaluar
            open_positions: Lista de posiciones abiertas actuales

        Returns:
            Dict con 'allowed' (bool) y 'reason' (str)
        """
        if not self.enabled:
            return {'allowed': True, 'reason': 'Correlation filter disabled'}

        if not open_positions:
            return {'allowed': True, 'reason': 'No open positions'}

        # Revisar correlación con cada posición abierta
        high_correlations = []

        for pos in open_positions:
            pos_symbol = pos.get('symbol', '')
            if pos_symbol == symbol:
                continue  # Ya se maneja por límite de posición por símbolo

            correlation = self.get_correlation(symbol, pos_symbol)

            if correlation >= self.max_correlation:
                high_correlations.append({
                    'symbol': pos_symbol,
                    'correlation': correlation
                })

        if high_correlations:
            # Bloquear por alta correlación
            blocking_symbols = [hc['symbol'] for hc in high_correlations]
            max_corr = max(hc['correlation'] for hc in high_correlations)

            reason = (
                f"Alta correlación ({max_corr:.0%}) con posiciones abiertas: "
                f"{', '.join(blocking_symbols)}. "
                f"Umbral: {self.max_correlation:.0%}"
            )

            logger.warning(f"🚫 Correlación bloqueando {symbol}: {reason}")

            return {
                'allowed': False,
                'reason': reason,
                'blocking_positions': high_correlations,
                'max_correlation_found': max_corr
            }

        return {
            'allowed': True,
            'reason': 'Correlation check passed',
            'correlations_checked': len(open_positions)
        }

    def get_portfolio_correlation_matrix(
        self,
        symbols: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """
        Genera matriz de correlación para un conjunto de símbolos.

        Args:
            symbols: Lista de símbolos

        Returns:
            Matriz de correlación como dict de dicts
        """
        matrix = {}

        for s1 in symbols:
            matrix[s1] = {}
            for s2 in symbols:
                matrix[s1][s2] = self.get_correlation(s1, s2)

        return matrix

    def calculate_effective_positions(
        self,
        open_positions: List[Dict[str, Any]]
    ) -> float:
        """
        Calcula el número efectivo de posiciones considerando correlación.

        Si tienes 2 posiciones con 100% correlación, efectivamente tienes 1.
        Si tienes 2 posiciones con 0% correlación, efectivamente tienes 2.

        Fórmula: N_eff = N^2 / sum(correlations^2)

        Args:
            open_positions: Lista de posiciones abiertas

        Returns:
            Número efectivo de posiciones (puede ser decimal)
        """
        n = len(open_positions)

        if n <= 1:
            return float(n)

        # Calcular suma de correlaciones al cuadrado
        total_corr_sq = 0

        for i, pos1 in enumerate(open_positions):
            for j, pos2 in enumerate(open_positions):
                if i <= j:  # Solo triángulo superior + diagonal
                    corr = self.get_correlation(
                        pos1.get('symbol', ''),
                        pos2.get('symbol', '')
                    )
                    if i == j:
                        total_corr_sq += 1  # Diagonal = 1
                    else:
                        total_corr_sq += 2 * (corr ** 2)  # Simetría

        # Fórmula de posiciones efectivas
        if total_corr_sq > 0:
            n_effective = (n ** 2) / total_corr_sq
        else:
            n_effective = float(n)

        return round(n_effective, 2)

    def get_diversification_score(
        self,
        open_positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calcula score de diversificación del portfolio.

        Returns:
            Dict con métricas de diversificación
        """
        n = len(open_positions)

        if n <= 1:
            return {
                'score': 1.0,
                'effective_positions': float(n),
                'actual_positions': n,
                'diversification_ratio': 1.0,
                'status': 'N/A' if n == 0 else 'Single position'
            }

        n_effective = self.calculate_effective_positions(open_positions)
        diversification_ratio = n_effective / n

        # Score de 0 a 1 (1 = perfectamente diversificado)
        score = diversification_ratio

        # Determinar status
        if score >= 0.8:
            status = "Excellent diversification"
        elif score >= 0.6:
            status = "Good diversification"
        elif score >= 0.4:
            status = "Moderate diversification"
        else:
            status = "Poor diversification - High correlation risk"

        return {
            'score': round(score, 3),
            'effective_positions': n_effective,
            'actual_positions': n,
            'diversification_ratio': round(diversification_ratio, 3),
            'status': status
        }


# Singleton
_correlation_filter = None


def get_correlation_filter(config: Dict[str, Any] = None) -> Optional[CorrelationFilter]:
    """Obtiene singleton del filtro de correlación."""
    global _correlation_filter
    if _correlation_filter is None and config:
        _correlation_filter = CorrelationFilter(config)
    return _correlation_filter


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = {
        'correlation_filter': {
            'enabled': True,
            'max_correlation': 0.70
        }
    }

    cf = CorrelationFilter(config)

    # Test: Verificar si puede abrir ETH teniendo BTC abierto
    open_positions = [
        {'symbol': 'BTC/USDT', 'side': 'long', 'entry_price': 50000}
    ]

    result = cf.can_open_position('ETH/USDT', open_positions)
    print(f"\n¿Puede abrir ETH con BTC abierto? {result['allowed']}")
    print(f"Razón: {result['reason']}")

    # Test: Verificar diversificación
    open_positions = [
        {'symbol': 'BTC/USDT'},
        {'symbol': 'ETH/USDT'},
        {'symbol': 'SOL/USDT'}
    ]

    diversification = cf.get_diversification_score(open_positions)
    print(f"\n=== DIVERSIFICATION SCORE ===")
    print(f"Score: {diversification['score']:.1%}")
    print(f"Effective positions: {diversification['effective_positions']}")
    print(f"Actual positions: {diversification['actual_positions']}")
    print(f"Status: {diversification['status']}")
