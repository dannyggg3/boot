"""
Router de usuarios.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from core.database import fetchrow, execute
from core.security import decode_token

router = APIRouter()

# Dependency para obtener usuario actual
async def get_current_user(authorization: str = Header(...)):
    """Obtiene el usuario actual del token JWT."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user = await fetchrow(
        """
        SELECT u.id, u.email, u.name, u.created_at, u.is_active, u.role,
               s.status as subscription_status, p.name as plan_name
        FROM users u
        LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active'
        LEFT JOIN plans p ON s.plan_id = p.id
        WHERE u.id = $1 AND u.is_active = TRUE
        """,
        payload["sub"]
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return dict(user)

# Schemas
class UserProfile(BaseModel):
    id: str
    email: str
    name: Optional[str]
    plan: str
    created_at: datetime

class UserUpdate(BaseModel):
    name: Optional[str] = None

# Endpoints
@router.get("/me", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Obtiene el perfil del usuario actual."""
    return UserProfile(
        id=str(current_user["id"]),
        email=current_user["email"],
        name=current_user["name"],
        plan=current_user["plan_name"] or "Free",
        created_at=current_user["created_at"]
    )

@router.put("/me")
async def update_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualiza el perfil del usuario."""
    if update_data.name:
        await execute(
            "UPDATE users SET name = $1, updated_at = NOW() WHERE id = $2",
            update_data.name,
            current_user["id"]
        )

    return {"message": "Profile updated successfully"}

@router.delete("/me")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """Desactiva la cuenta del usuario."""
    # Soft delete
    await execute(
        "UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
        current_user["id"]
    )

    # TODO: Detener bot si está corriendo

    return {"message": "Account deleted successfully"}
