"""
Router de API Keys.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional

from core.database import fetchrow, execute, fetch
from core.security import key_encryption
from .users import get_current_user

router = APIRouter()

# Schemas
class ExchangeKeyCreate(BaseModel):
    exchange: str = "binance"
    api_key: str
    api_secret: str
    is_testnet: bool = True

class AIKeyCreate(BaseModel):
    provider: str = "deepseek"
    api_key: str

class KeyInfo(BaseModel):
    id: str
    exchange: Optional[str] = None
    provider: Optional[str] = None
    is_testnet: Optional[bool] = None
    created_at: str
    is_valid: bool = True

# Endpoints - Exchange Keys
@router.post("/exchange")
async def save_exchange_key(
    key_data: ExchangeKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Guarda las API keys de un exchange (encriptadas)."""
    user_id = str(current_user["id"])

    # Encriptar keys
    encrypted_key = key_encryption.encrypt(key_data.api_key)
    encrypted_secret = key_encryption.encrypt(key_data.api_secret)

    # Guardar o actualizar
    await execute(
        """
        INSERT INTO api_keys (user_id, exchange, api_key_encrypted, api_secret_encrypted, is_testnet)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, exchange, is_testnet)
        DO UPDATE SET api_key_encrypted = $3, api_secret_encrypted = $4
        """,
        user_id,
        key_data.exchange,
        encrypted_key,
        encrypted_secret,
        key_data.is_testnet
    )

    return {
        "message": f"Exchange keys for {key_data.exchange} saved successfully",
        "is_testnet": key_data.is_testnet
    }

@router.get("/exchange", response_model=List[KeyInfo])
async def list_exchange_keys(current_user: dict = Depends(get_current_user)):
    """Lista los exchanges configurados (sin mostrar las keys)."""
    user_id = str(current_user["id"])

    rows = await fetch(
        """
        SELECT id, exchange, is_testnet, created_at
        FROM api_keys
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id
    )

    return [
        KeyInfo(
            id=str(row["id"]),
            exchange=row["exchange"],
            is_testnet=row["is_testnet"],
            created_at=row["created_at"].isoformat()
        )
        for row in rows
    ]

@router.delete("/exchange/{key_id}")
async def delete_exchange_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Elimina una API key de exchange."""
    user_id = str(current_user["id"])

    result = await execute(
        "DELETE FROM api_keys WHERE id = $1 AND user_id = $2",
        key_id, user_id
    )

    return {"message": "Exchange key deleted"}

# Endpoints - AI Keys
@router.post("/ai")
async def save_ai_key(
    key_data: AIKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Guarda la API key de un proveedor de IA (encriptada)."""
    user_id = str(current_user["id"])

    encrypted_key = key_encryption.encrypt(key_data.api_key)

    await execute(
        """
        INSERT INTO ai_keys (user_id, provider, api_key_encrypted)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, provider)
        DO UPDATE SET api_key_encrypted = $3
        """,
        user_id,
        key_data.provider,
        encrypted_key
    )

    return {"message": f"AI key for {key_data.provider} saved successfully"}

@router.get("/ai", response_model=List[KeyInfo])
async def list_ai_keys(current_user: dict = Depends(get_current_user)):
    """Lista los proveedores de IA configurados."""
    user_id = str(current_user["id"])

    rows = await fetch(
        """
        SELECT id, provider, created_at
        FROM ai_keys
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id
    )

    return [
        KeyInfo(
            id=str(row["id"]),
            provider=row["provider"],
            created_at=row["created_at"].isoformat()
        )
        for row in rows
    ]

@router.delete("/ai/{key_id}")
async def delete_ai_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Elimina una API key de IA."""
    user_id = str(current_user["id"])

    await execute(
        "DELETE FROM ai_keys WHERE id = $1 AND user_id = $2",
        key_id, user_id
    )

    return {"message": "AI key deleted"}

# Test connection
@router.post("/test")
async def test_connection(
    key_type: str,  # "exchange" or "ai"
    current_user: dict = Depends(get_current_user)
):
    """Prueba la conexión con las API keys configuradas."""
    user_id = str(current_user["id"])

    if key_type == "exchange":
        # TODO: Implementar test de conexión a Binance
        return {"status": "ok", "message": "Exchange connection test not implemented"}

    elif key_type == "ai":
        # TODO: Implementar test de conexión a DeepSeek
        return {"status": "ok", "message": "AI connection test not implemented"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid key_type. Use 'exchange' or 'ai'"
    )
