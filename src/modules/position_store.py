"""
Position Store - Persistencia SQLite para posiciones
====================================================
Almacena posiciones y órdenes en SQLite para:
- Sobrevivir reinicios del bot
- Historial de trades para análisis
- Tracking de rendimiento por agente

Autor: Trading Bot System
Versión: 1.5
"""

import sqlite3
import os
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PositionStore:
    """
    Almacén persistente de posiciones usando SQLite.
    Thread-safe con connection pooling.
    """

    def __init__(self, db_path: str = "data/positions.db"):
        """
        Inicializa el almacén de posiciones.

        Args:
            db_path: Ruta al archivo SQLite
        """
        self.db_path = db_path

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Inicializar base de datos
        self._init_database()
        logger.info(f"PositionStore inicializado: {db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones thread-safe."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """Crea las tablas si no existen."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabla de posiciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',

                    -- Entry details
                    entry_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    entry_order_id TEXT,
                    confidence REAL DEFAULT 0,
                    agent_type TEXT DEFAULT 'general',
                    entry_reasoning TEXT,

                    -- Protection levels
                    stop_loss REAL NOT NULL,
                    take_profit REAL,
                    initial_stop_loss REAL,
                    trailing_stop_active INTEGER DEFAULT 0,
                    trailing_stop_distance REAL,

                    -- OCO order tracking
                    oco_order_id TEXT,
                    sl_order_id TEXT,
                    tp_order_id TEXT,

                    -- Exit details
                    exit_price REAL,
                    exit_time TEXT,
                    exit_reason TEXT,
                    exit_order_id TEXT,

                    -- P&L
                    realized_pnl REAL,
                    realized_pnl_percent REAL,

                    -- Supervision
                    supervision_count INTEGER DEFAULT 0,
                    last_supervision TEXT,
                    supervision_history TEXT,  -- JSON array

                    -- Timestamps
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Índices para búsquedas rápidas
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)")

            # Tabla de órdenes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    position_id TEXT,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',

                    quantity REAL NOT NULL,
                    price REAL,
                    stop_price REAL,

                    filled_quantity REAL DEFAULT 0,
                    average_fill_price REAL,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    filled_at TEXT,

                    oco_id TEXT,
                    oco_pair_id TEXT,

                    exchange_response TEXT,  -- JSON

                    FOREIGN KEY (position_id) REFERENCES positions(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_position ON orders(position_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")

            # Tabla de historial de trades
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,

                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    quantity REAL NOT NULL,

                    pnl REAL NOT NULL,
                    pnl_percent REAL NOT NULL,
                    result TEXT NOT NULL,  -- 'win', 'loss', 'breakeven'

                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    hold_time_minutes INTEGER,

                    exit_reason TEXT NOT NULL,
                    agent_type TEXT,
                    confidence REAL,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (position_id) REFERENCES positions(id)
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_result ON trade_history(result)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_agent ON trade_history(agent_type)")

            logger.debug("Tablas de base de datos inicializadas")

    # =========================================================================
    # CRUD POSICIONES
    # =========================================================================

    def save_position(self, position: Dict[str, Any]) -> bool:
        """
        Guarda o actualiza una posición.

        Args:
            position: Diccionario con datos de la posición

        Returns:
            True si se guardó correctamente
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Verificar si existe
                cursor.execute("SELECT id FROM positions WHERE id = ?", (position['id'],))
                exists = cursor.fetchone()

                if exists:
                    # Update
                    self._update_position(cursor, position)
                else:
                    # Insert
                    self._insert_position(cursor, position)

                logger.debug(f"Posición guardada: {position['id']}")
                return True

        except Exception as e:
            logger.error(f"Error guardando posición: {e}")
            return False

    def _insert_position(self, cursor, position: Dict):
        """Inserta nueva posición."""
        cursor.execute("""
            INSERT INTO positions (
                id, symbol, side, status,
                entry_price, quantity, entry_time, entry_order_id,
                confidence, agent_type, entry_reasoning,
                stop_loss, take_profit, initial_stop_loss,
                trailing_stop_active, trailing_stop_distance,
                oco_order_id, sl_order_id, tp_order_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position['id'],
            position['symbol'],
            position['side'],
            position.get('status', 'open'),
            position['entry_price'],
            position['quantity'],
            position.get('entry_time', datetime.now().isoformat()),
            position.get('entry_order_id'),
            position.get('confidence', 0),
            position.get('agent_type', 'general'),
            position.get('entry_reasoning'),
            position['stop_loss'],
            position.get('take_profit'),
            position.get('initial_stop_loss', position['stop_loss']),
            1 if position.get('trailing_stop_active') else 0,
            position.get('trailing_stop_distance'),
            position.get('oco_order_id'),
            position.get('sl_order_id'),
            position.get('tp_order_id')
        ))

    def _update_position(self, cursor, position: Dict):
        """Actualiza posición existente."""
        cursor.execute("""
            UPDATE positions SET
                status = ?,
                stop_loss = ?,
                take_profit = ?,
                trailing_stop_active = ?,
                trailing_stop_distance = ?,
                oco_order_id = ?,
                sl_order_id = ?,
                tp_order_id = ?,
                exit_price = ?,
                exit_time = ?,
                exit_reason = ?,
                exit_order_id = ?,
                realized_pnl = ?,
                realized_pnl_percent = ?,
                supervision_count = ?,
                last_supervision = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            position.get('status', 'open'),
            position['stop_loss'],
            position.get('take_profit'),
            1 if position.get('trailing_stop_active') else 0,
            position.get('trailing_stop_distance'),
            position.get('oco_order_id'),
            position.get('sl_order_id'),
            position.get('tp_order_id'),
            position.get('exit_price'),
            position.get('exit_time'),
            position.get('exit_reason'),
            position.get('exit_order_id'),
            position.get('realized_pnl'),
            position.get('realized_pnl_percent'),
            position.get('supervision_count', 0),
            position.get('last_supervision'),
            datetime.now().isoformat(),
            position['id']
        ))

    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una posición por ID.

        Args:
            position_id: ID de la posición

        Returns:
            Diccionario con la posición o None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Error obteniendo posición {position_id}: {e}")
            return None

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las posiciones abiertas.

        Returns:
            Lista de posiciones abiertas
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM positions
                    WHERE status IN ('open', 'pending')
                    ORDER BY entry_time DESC
                """)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error obteniendo posiciones abiertas: {e}")
            return []

    def get_positions_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Obtiene posiciones abiertas para un símbolo.

        Args:
            symbol: Par de trading

        Returns:
            Lista de posiciones para ese símbolo
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM positions
                    WHERE symbol = ? AND status IN ('open', 'pending')
                """, (symbol,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error obteniendo posiciones de {symbol}: {e}")
            return []

    def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_reason: str,
        exit_order_id: Optional[str] = None
    ) -> bool:
        """
        Cierra una posición y registra en historial.

        Args:
            position_id: ID de la posición
            exit_price: Precio de salida
            exit_reason: Razón del cierre
            exit_order_id: ID de la orden de cierre

        Returns:
            True si se cerró correctamente
        """
        try:
            position = self.get_position(position_id)
            if not position:
                logger.warning(f"Posición no encontrada: {position_id}")
                return False

            # Calcular P&L
            entry_price = position['entry_price']
            quantity = position['quantity']
            side = position['side']

            if side == 'long':
                pnl = (exit_price - entry_price) * quantity
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl = (entry_price - exit_price) * quantity
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100

            # Determinar resultado
            if pnl > 0.01:
                result = 'win'
            elif pnl < -0.01:
                result = 'loss'
            else:
                result = 'breakeven'

            exit_time = datetime.now()

            # Calcular tiempo en posición
            entry_time = datetime.fromisoformat(position['entry_time'])
            hold_time = int((exit_time - entry_time).total_seconds() / 60)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Actualizar posición
                cursor.execute("""
                    UPDATE positions SET
                        status = 'closed',
                        exit_price = ?,
                        exit_time = ?,
                        exit_reason = ?,
                        exit_order_id = ?,
                        realized_pnl = ?,
                        realized_pnl_percent = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    exit_price,
                    exit_time.isoformat(),
                    exit_reason,
                    exit_order_id,
                    round(pnl, 4),
                    round(pnl_percent, 2),
                    exit_time.isoformat(),
                    position_id
                ))

                # Registrar en historial
                cursor.execute("""
                    INSERT INTO trade_history (
                        position_id, symbol, side,
                        entry_price, exit_price, quantity,
                        pnl, pnl_percent, result,
                        entry_time, exit_time, hold_time_minutes,
                        exit_reason, agent_type, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position_id,
                    position['symbol'],
                    side,
                    entry_price,
                    exit_price,
                    quantity,
                    round(pnl, 4),
                    round(pnl_percent, 2),
                    result,
                    position['entry_time'],
                    exit_time.isoformat(),
                    hold_time,
                    exit_reason,
                    position.get('agent_type', 'general'),
                    position.get('confidence', 0)
                ))

            logger.info(f"Posición cerrada: {position_id} | P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")
            return True

        except Exception as e:
            logger.error(f"Error cerrando posición {position_id}: {e}")
            return False

    def update_stop_loss(self, position_id: str, new_stop_loss: float) -> bool:
        """Actualiza el stop loss de una posición."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE positions SET
                        stop_loss = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (new_stop_loss, datetime.now().isoformat(), position_id))

            logger.debug(f"SL actualizado: {position_id} -> ${new_stop_loss}")
            return True

        except Exception as e:
            logger.error(f"Error actualizando SL: {e}")
            return False

    def update_take_profit(self, position_id: str, new_take_profit: float) -> bool:
        """Actualiza el take profit de una posición."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE positions SET
                        take_profit = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (new_take_profit, datetime.now().isoformat(), position_id))

            logger.debug(f"TP actualizado: {position_id} -> ${new_take_profit}")
            return True

        except Exception as e:
            logger.error(f"Error actualizando TP: {e}")
            return False

    def activate_trailing_stop(self, position_id: str, distance: float) -> bool:
        """Activa trailing stop para una posición."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE positions SET
                        trailing_stop_active = 1,
                        trailing_stop_distance = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (distance, datetime.now().isoformat(), position_id))

            logger.info(f"Trailing stop activado: {position_id} (distancia: {distance}%)")
            return True

        except Exception as e:
            logger.error(f"Error activando trailing stop: {e}")
            return False

    def update_supervision(self, position_id: str, decision: Dict) -> bool:
        """Registra una decisión del supervisor."""
        try:
            position = self.get_position(position_id)
            if not position:
                return False

            supervision_count = position.get('supervision_count', 0) + 1

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE positions SET
                        supervision_count = ?,
                        last_supervision = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    supervision_count,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    position_id
                ))

            return True

        except Exception as e:
            logger.error(f"Error actualizando supervisión: {e}")
            return False

    # =========================================================================
    # CRUD ÓRDENES
    # =========================================================================

    def save_order(self, order: Dict[str, Any]) -> bool:
        """Guarda una orden."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO orders (
                        id, position_id, symbol, type, side, status,
                        quantity, price, stop_price,
                        filled_quantity, average_fill_price,
                        oco_id, oco_pair_id, exchange_response
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order['id'],
                    order.get('position_id'),
                    order['symbol'],
                    order['type'],
                    order['side'],
                    order.get('status', 'pending'),
                    order['quantity'],
                    order.get('price'),
                    order.get('stop_price'),
                    order.get('filled_quantity', 0),
                    order.get('average_fill_price'),
                    order.get('oco_id'),
                    order.get('oco_pair_id'),
                    json.dumps(order.get('exchange_response', {}))
                ))
            return True

        except Exception as e:
            logger.error(f"Error guardando orden: {e}")
            return False

    def update_order_status(self, order_id: str, status: str, fill_price: Optional[float] = None) -> bool:
        """Actualiza estado de una orden."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if fill_price:
                    cursor.execute("""
                        UPDATE orders SET
                            status = ?,
                            average_fill_price = ?,
                            filled_at = ?
                        WHERE id = ?
                    """, (status, fill_price, datetime.now().isoformat(), order_id))
                else:
                    cursor.execute("""
                        UPDATE orders SET status = ? WHERE id = ?
                    """, (status, order_id))

            return True

        except Exception as e:
            logger.error(f"Error actualizando orden: {e}")
            return False

    # =========================================================================
    # ESTADÍSTICAS Y ANÁLISIS
    # =========================================================================

    def get_trade_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Obtiene estadísticas de trading.

        Args:
            days: Días a analizar

        Returns:
            Diccionario con estadísticas
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Total trades
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                           SUM(pnl) as total_pnl,
                           AVG(pnl_percent) as avg_pnl_percent,
                           AVG(hold_time_minutes) as avg_hold_time
                    FROM trade_history
                    WHERE datetime(exit_time) >= datetime('now', ?)
                """, (f'-{days} days',))

                row = cursor.fetchone()

                total = row['total'] or 0
                wins = row['wins'] or 0
                losses = row['losses'] or 0

                return {
                    'total_trades': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': (wins / total * 100) if total > 0 else 0,
                    'total_pnl': round(row['total_pnl'] or 0, 2),
                    'avg_pnl_percent': round(row['avg_pnl_percent'] or 0, 2),
                    'avg_hold_time_minutes': round(row['avg_hold_time'] or 0, 1),
                    'period_days': days
                }

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}

    def get_stats_by_agent(self, days: int = 30) -> Dict[str, Any]:
        """Estadísticas por tipo de agente."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT agent_type,
                           COUNT(*) as total,
                           SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                           SUM(pnl) as total_pnl
                    FROM trade_history
                    WHERE datetime(exit_time) >= datetime('now', ?)
                    GROUP BY agent_type
                """, (f'-{days} days',))

                results = {}
                for row in cursor.fetchall():
                    agent = row['agent_type'] or 'general'
                    total = row['total']
                    results[agent] = {
                        'total': total,
                        'wins': row['wins'],
                        'win_rate': (row['wins'] / total * 100) if total > 0 else 0,
                        'total_pnl': round(row['total_pnl'] or 0, 2)
                    }

                return results

        except Exception as e:
            logger.error(f"Error obteniendo stats por agente: {e}")
            return {}

    def get_portfolio_exposure(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        Calcula exposición actual del portfolio.

        Args:
            current_prices: Dict de precios actuales {symbol: price}

        Returns:
            Diccionario con exposición
        """
        positions = self.get_open_positions()

        total_exposure = 0
        max_single = 0
        symbols = []

        for pos in positions:
            symbol = pos['symbol']
            price = current_prices.get(symbol, pos['entry_price'])
            exposure = pos['quantity'] * price

            total_exposure += exposure
            max_single = max(max_single, exposure)
            symbols.append(symbol)

        return {
            'total_exposure_usd': round(total_exposure, 2),
            'position_count': len(positions),
            'max_single_exposure': round(max_single, 2),
            'symbols_held': symbols
        }


# =============================================================================
# SINGLETON - v1.7: Thread-safe implementation
# =============================================================================

import threading

_store_instance: Optional[PositionStore] = None
_store_lock = threading.Lock()


def get_position_store(db_path: str = "data/positions.db") -> PositionStore:
    """
    Obtiene instancia singleton del store.

    v1.7: Thread-safe con double-checked locking pattern.
    """
    global _store_instance

    # First check without lock (fast path)
    if _store_instance is not None:
        return _store_instance

    # Acquire lock for thread-safe initialization
    with _store_lock:
        # Double-check inside lock
        if _store_instance is None:
            _store_instance = PositionStore(db_path)
            logger.info("PositionStore singleton inicializado (thread-safe)")

    return _store_instance


def reset_position_store():
    """
    v1.7: Resetea el singleton (útil para tests).
    """
    global _store_instance
    with _store_lock:
        _store_instance = None
