from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_token
from app.modules.identity.models import User, UserRole
from app.modules.identity.service import AuthService


async def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)

    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")

    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
    }


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    payload = verify_access_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        if not user.is_active:
            return None
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
        }
    except Exception:
        return None


def require_role(*allowed_roles: UserRole):
    def decorator(func):
        async def wrapper(*args, current_user: Dict[str, Any] = Depends(get_current_user), **kwargs):
            user_role = current_user.get("role")
            if user_role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, current_user=current_user, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_vendor_or_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    role = current_user.get("role")
    if role not in (UserRole.VENDOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Vendor or admin access required")
    return current_user