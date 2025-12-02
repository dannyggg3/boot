"""
Configuración de base de datos PostgreSQL.
"""

import asyncpg
from typing import Optional
from .config import settings

# Pool de conexiones global
pool: Optional[asyncpg.Pool] = None

async def init_db():
    """Inicializa el pool de conexiones."""
    global pool
    pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=5,
        max_size=20
    )
    print("Database pool initialized")

async def close_db():
    """Cierra el pool de conexiones."""
    global pool
    if pool:
        await pool.close()
        print("Database pool closed")

async def get_db():
    """Obtiene una conexión del pool."""
    async with pool.acquire() as connection:
        yield connection

# Funciones de utilidad
async def execute(query: str, *args):
    """Ejecuta una query sin retorno."""
    async with pool.acquire() as conn:
        await conn.execute(query, *args)

async def fetch(query: str, *args):
    """Ejecuta una query y retorna múltiples filas."""
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def fetchrow(query: str, *args):
    """Ejecuta una query y retorna una fila."""
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def fetchval(query: str, *args):
    """Ejecuta una query y retorna un valor."""
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)
