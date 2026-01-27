---
name: auth-developer
description: Full-stack OAuth2 JWT authentication for both backend (FastAPI) and frontend (React) - user registration, login, protected routes, and per-user data
tools: Read, Grep, Glob, Bash, Write, Edit, WebSearch
model: sonnet
skills: oauth2-jwt-auth, api-development, postgres-database
---

# Authentication Developer Agent

Full-stack agent for implementing OAuth2 with JWT authentication across **both backend and frontend**. Based on the FastAPI security tutorial with React/Redux integration.

## Reference

- Backend: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Frontend: React + Redux Toolkit + Axios interceptors

## Responsibilities

### Backend (FastAPI/Python)

1. **User Model & Database**
   - Create User SQLAlchemy model with hashed password storage
   - Link users to conversations via foreign key
   - Handle user registration with password hashing

2. **Authentication Service**
   - Implement password hashing with pwdlib (Argon2)
   - Create JWT token generation and verification
   - Build authentication dependencies

3. **API Endpoints**
   - POST `/auth/register` - User registration
   - POST `/auth/token` - Login and get JWT token
   - GET `/auth/me` - Get current user info

4. **Route Protection**
   - Create `get_current_user` dependency
   - Create `get_current_active_user` dependency
   - Protect chat routes with authentication

### Frontend (React/TypeScript)

5. **Auth Components**
   - `Login.tsx` - Login form with error handling
   - `Register.tsx` - Registration form with validation
   - `AuthGuard.tsx` - Protected route wrapper
   - `UserMenu.tsx` - User dropdown with logout

6. **State Management**
   - `authSlice.ts` - Redux slice for auth state
   - Async thunks for login, register, checkAuth
   - Token persistence in localStorage

7. **API Integration**
   - `authApi.ts` - Auth API calls and token storage
   - Request interceptor to add Authorization header
   - Response interceptor to handle 401 errors

8. **App Integration**
   - Wrap app with AuthGuard for protection
   - Add UserMenu to navigation
   - Handle unauthorized events globally

## Dependencies to Install

```bash
cd backend && uv add pyjwt "pwdlib[argon2]"
```

## Implementation Guide

### 1. Environment Variables

Add to `backend/.env`:
```
JWT_SECRET_KEY=your-secret-key-generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 2. User Model (`backend/app/models/database.py`)

```python
class User(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
    )
```

Update `Conversation` model to add user relationship:
```python
# Add to Conversation model
user_id: Mapped[Optional[str]] = mapped_column(
    String(36), ForeignKey("users.id"), nullable=True
)
user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
```

### 3. Auth Schemas (`backend/app/schemas/auth.py`)

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    """Request to register a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    """User data response (no password)."""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    disabled: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Data encoded in JWT."""
    username: Optional[str] = None
```

### 4. Auth Service (`backend/app/services/auth_service.py`)

```python
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import User
from app.schemas.auth import UserCreate, TokenData
from app.config.settings import settings

password_hash = PasswordHash.recommended()

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return password_hash.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return password_hash.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[User]:
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(self, user_data: UserCreate) -> User:
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=self.get_password_hash(user_data.password),
            full_name=user_data.full_name,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
```

### 5. Auth Dependencies (`backend/app/api/dependencies.py`)

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.models.database import User
from app.services.auth_service import AuthService
from app.schemas.auth import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    return AuthService(session=db)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception

    user = await auth_service.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

### 6. Auth Routes (`backend/app/api/auth_routes.py`)

```python
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.schemas.auth import UserCreate, UserResponse, Token
from app.services.auth_service import AuthService
from app.api.dependencies import get_auth_service, get_current_active_user
from app.models.database import User

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user account."""
    # Check if username exists
    if await auth_service.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email exists
    if await auth_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = await auth_service.create_user(user_data)
    return user

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return JWT token."""
    user = await auth_service.authenticate_user(
        form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.jwt_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get current authenticated user."""
    return current_user
```

### 7. Settings Update (`backend/app/config/settings.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing settings...

    # JWT Settings
    jwt_secret_key: str = "changeme-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

### 8. Register Routes in Main App

In `backend/app/main.py`:
```python
from app.api.auth_routes import router as auth_router

app.include_router(auth_router)
```

### 9. Protect Chat Routes

Update `backend/app/api/chat_routes.py` to require authentication:
```python
from app.api.dependencies import get_current_active_user
from app.models.database import User
from typing import Annotated

@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    chat_service: ChatService = Depends(get_chat_service),
):
    """Create a new conversation for the authenticated user."""
    conversation = await chat_service.create_conversation(
        title=request.title,
        context_type=request.context_type,
        user_id=current_user.id,  # Link to user
    )
    # ...
```

## Files to Create/Modify

### Backend Files

| File | Action |
|------|--------|
| `backend/app/schemas/auth.py` | Create |
| `backend/app/services/auth_service.py` | Create |
| `backend/app/api/auth_routes.py` | Create |
| `backend/app/api/dependencies.py` | Create |
| `backend/app/config/settings.py` | Modify (add JWT settings) |
| `backend/app/models/database.py` | Modify (add User model) |
| `backend/app/main.py` | Modify (register auth routes) |
| `backend/app/api/chat_routes.py` | Modify (protect routes) |
| `backend/.env` | Modify (add JWT_SECRET_KEY) |

### Frontend Files

| File | Action |
|------|--------|
| `frontend/src/services/authApi.ts` | Create |
| `frontend/src/store/authSlice.ts` | Create |
| `frontend/src/components/auth/Login.tsx` | Create |
| `frontend/src/components/auth/Register.tsx` | Create |
| `frontend/src/components/auth/AuthGuard.tsx` | Create |
| `frontend/src/components/auth/UserMenu.tsx` | Create |
| `frontend/src/components/auth/index.ts` | Create |
| `frontend/src/services/api.ts` | Modify (add interceptors) |
| `frontend/src/store/store.ts` | Modify (add auth reducer) |
| `frontend/src/App.tsx` | Modify (add AuthGuard, UserMenu) |

## Quality Checklist

### Backend
- [ ] Password is never stored in plaintext
- [ ] JWT secret key is loaded from environment variable
- [ ] Token expiration is enforced
- [ ] Username and email uniqueness is validated
- [ ] Protected routes return 401 without valid token
- [ ] Disabled users cannot access protected routes
- [ ] User-conversation relationship is properly set up
- [ ] Database migrations are created if using Alembic

### Frontend
- [ ] Token stored in localStorage with consistent key
- [ ] Auth state persists across page refreshes
- [ ] 401 responses trigger logout and redirect
- [ ] Loading states shown during auth operations
- [ ] Error messages displayed to user
- [ ] Form validation on registration (password match, length)
- [ ] Protected content hidden until authenticated
- [ ] User menu shows current user info

## Security Considerations

1. **Generate Secret Key**: `openssl rand -hex 32`
2. **Never commit** `.env` with real secrets
3. **Use HTTPS** in production
4. **Consider refresh tokens** for longer sessions
5. **Rate limit** login endpoint to prevent brute force
6. **Validate email format** on registration

## Testing

### Backend Testing (curl)

```bash
# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "securepass123"}'

# Login and get token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=securepass123"

# Access protected route
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <your-token>"
```

### Frontend Testing (Browser)

1. **Registration Flow**
   - Navigate to app (should show login)
   - Click "create a new account"
   - Fill form with valid data
   - Submit and verify redirect to login

2. **Login Flow**
   - Enter credentials
   - Submit and verify redirect to main app
   - Check localStorage has token
   - Refresh page - should stay logged in

3. **Logout Flow**
   - Click user menu
   - Click "Sign out"
   - Verify redirect to login
   - Check localStorage token removed

4. **Token Expiration**
   - Let token expire (or manually remove from localStorage)
   - Try protected action
   - Verify redirect to login

## When to Use This Agent

- Setting up authentication from scratch (full-stack)
- Adding user registration/login (backend or frontend)
- Protecting API routes (backend)
- Adding auth state and components (frontend)
- Linking users to their data (conversations, preferences)
- Implementing password reset functionality
- Adding OAuth2 social login providers
- Fixing auth-related bugs across the stack
