from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.models import UserRole
from app.modules.identity.schemas import UserCreate, UserLogin, UserResponse, Token, TokenRefresh
from app.modules.identity.service import AuthService
from app.modules.identity.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    auth_service = AuthService(db)
    user = await auth_service.register_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    auth_service = AuthService(db)
    token = await auth_service.authenticate(credentials.email, credentials.password)
    return token


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> Token:
    auth_service = AuthService(db)
    token = await auth_service.refresh_access_token(token_data.refresh_token)
    return token


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(current_user["user_id"])
    return UserResponse.model_validate(user)