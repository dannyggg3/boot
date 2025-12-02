"""
Router de autenticación.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional

from core.database import fetchrow, execute
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

router = APIRouter()

# Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

# Endpoints
@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Registra un nuevo usuario."""
    # Verificar si el email ya existe
    existing = await fetchrow(
        "SELECT id FROM users WHERE email = $1",
        user_data.email
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Crear usuario
    password_hash = get_password_hash(user_data.password)
    user_id = await fetchrow(
        """
        INSERT INTO users (email, password_hash, name)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        user_data.email,
        password_hash,
        user_data.name
    )

    user_id = str(user_id["id"])

    # Crear suscripción Free por defecto
    await execute(
        """
        INSERT INTO subscriptions (user_id, plan_id, status)
        SELECT $1, id, 'active'
        FROM plans WHERE name = 'Free'
        """,
        user_id
    )

    # Generar tokens
    token_data = {"sub": user_id, "email": user_data.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Inicia sesión y retorna tokens JWT."""
    # Buscar usuario
    user = await fetchrow(
        "SELECT id, email, password_hash FROM users WHERE email = $1 AND is_active = TRUE",
        credentials.email
    )

    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Generar tokens
    token_data = {"sub": str(user["id"]), "email": user["email"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Renueva el access token usando el refresh token."""
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Verificar que el usuario aún existe
    user = await fetchrow(
        "SELECT id, email FROM users WHERE id = $1 AND is_active = TRUE",
        payload["sub"]
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Generar nuevos tokens
    token_data = {"sub": str(user["id"]), "email": user["email"]}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )

@router.post("/logout")
async def logout():
    """Cierra la sesión (client-side debe eliminar tokens)."""
    return {"message": "Logged out successfully"}
