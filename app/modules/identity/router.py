from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.models import UserRole
from app.modules.identity.schemas import UserCreate, UserLogin, UserResponse, Token, TokenRefresh
from app.modules.identity.service import AuthService
from app.modules.identity.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Password (minimum 8 characters)

    Returns the created user object with their assigned role (default: customer).
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token, summary="Authenticate user and get tokens")
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Authenticate a user with email and password.

    - **email**: User's registered email
    - **password**: User's password

    Returns access and refresh tokens for authenticated requests.
    """
    auth_service = AuthService(db)
    token = await auth_service.authenticate(credentials.email, credentials.password)
    return token


@router.post("/refresh", response_model=Token, summary="Refresh access token")
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Refresh the access token using a valid refresh token.

    - **refresh_token**: Valid refresh token from previous login

    Returns new access and refresh tokens.
    """
    auth_service = AuthService(db)
    token = await auth_service.refresh_access_token(token_data.refresh_token)
    return token


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get the currently authenticated user's profile.

    Requires a valid access token in the Authorization header.
    """
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(current_user["user_id"])
    return UserResponse.model_validate(user)