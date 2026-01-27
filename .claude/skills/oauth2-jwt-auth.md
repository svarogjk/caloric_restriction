# OAuth2 JWT Authentication Skill

Full-stack authentication skill for both **backend** (FastAPI/Python) and **frontend** (React/TypeScript). Use this skill when implementing user authentication, registration, login, or protecting routes.

## Project Structure

### Backend (FastAPI)
```
backend/app/
├── api/
│   ├── auth_routes.py       # Authentication endpoints
│   ├── dependencies.py      # Auth dependencies (get_current_user)
│   └── chat_routes.py       # Protected routes example
├── models/
│   └── database.py          # User SQLAlchemy model
├── schemas/
│   └── auth.py              # Pydantic auth models
├── services/
│   └── auth_service.py      # Auth business logic
└── config/
    └── settings.py          # JWT configuration
```

### Frontend (React)
```
frontend/src/
├── components/auth/
│   ├── index.ts             # Exports all auth components
│   ├── Login.tsx            # Login form component
│   ├── Register.tsx         # Registration form component
│   ├── AuthGuard.tsx        # Protected route wrapper
│   └── UserMenu.tsx         # User dropdown with logout
├── services/
│   └── authApi.ts           # Auth API calls & token storage
└── store/
    └── authSlice.ts         # Redux auth state management
```

## Dependencies

```bash
cd backend && uv add pyjwt "pwdlib[argon2]"
```

## Environment Variables

Add to `backend/.env`:
```bash
# Generate with: openssl rand -hex 32
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Pydantic Schemas

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    """Request to register a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    """User data response (excludes password)."""
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
    """Data encoded in JWT payload."""
    username: Optional[str] = None
```

## SQLAlchemy User Model

```python
# Add to backend/app/models/database.py
class User(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # User owns conversations
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
```

Update Conversation model:
```python
# Add to Conversation model
user_id: Mapped[Optional[str]] = mapped_column(
    String(36), ForeignKey("users.id"), nullable=True
)
user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
```

## Settings Configuration

```python
# backend/app/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./chat.db"

    # JWT
    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # Existing settings...
    mistral_key: str = ""
    email: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

## Auth Service

```python
# backend/app/services/auth_service.py
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

# Use Argon2 - recommended password hashing
password_hash = PasswordHash.recommended()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return password_hash.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password using Argon2."""
        return password_hash.hash(password)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Fetch user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> Optional[User]:
        """Authenticate user with username and password."""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with hashed password."""
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

## Auth Dependencies

```python
# backend/app/api/dependencies.py
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

# Points to the token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(session=db)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency to get current authenticated user from JWT."""
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
    """Dependency to get current active (non-disabled) user."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

## Auth Routes

```python
# backend/app/api/auth_routes.py
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

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
    """
    Register a new user account.

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (8-100 characters)
    - **full_name**: Optional display name
    """
    # Check username uniqueness
    if await auth_service.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check email uniqueness
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
    """
    OAuth2 compatible token login.

    Send username and password as form data to get JWT token.
    """
    user = await auth_service.authenticate_user(
        form_data.username,
        form_data.password,
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
    """Get current authenticated user's information."""
    return current_user
```

## Protecting Routes

```python
# Example: Protected chat routes
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
        user_id=current_user.id,  # Link conversation to user
    )
    return CreateConversationResponse(...)


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    chat_service: ChatService = Depends(get_chat_service),
    limit: int = 20,
    offset: int = 0,
):
    """List conversations for the authenticated user only."""
    conversations = await chat_service.list_conversations(
        user_id=current_user.id,  # Filter by user
        limit=limit,
        offset=offset,
    )
    return [...]
```

## Register Routes in Main App

```python
# backend/app/main.py
from fastapi import FastAPI
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router

app = FastAPI(title="GEO Survival Analysis")

app.include_router(auth_router)
app.include_router(chat_router)
```

## Testing Authentication

```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepass123",
    "full_name": "Test User"
  }'

# Login and get token (note: form data, not JSON)
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=securepass123"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# Access protected route with token
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ..."

# Create conversation (protected)
curl -X POST http://localhost:8000/chat/conversations \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"title": "My Chat", "context_type": "general"}'
```

## Error Responses

| Scenario | Status | Response |
|----------|--------|----------|
| Invalid credentials | 401 | `{"detail": "Incorrect username or password"}` |
| Invalid/expired token | 401 | `{"detail": "Could not validate credentials"}` |
| Missing token | 401 | `{"detail": "Not authenticated"}` |
| Disabled user | 400 | `{"detail": "Inactive user"}` |
| Username taken | 400 | `{"detail": "Username already registered"}` |
| Email taken | 400 | `{"detail": "Email already registered"}` |

## Security Best Practices

1. **Generate secure secret**: `openssl rand -hex 32`
2. **Never commit `.env`** with real secrets
3. **Use HTTPS** in production
4. **Set reasonable token expiration** (30 min default)
5. **Rate limit login endpoint** to prevent brute force
6. **Validate password strength** (min 8 chars enforced)
7. **Hash passwords with Argon2** (industry standard)

## Optional: Refresh Tokens

For longer sessions without re-login:

```python
class RefreshToken(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_data: RefreshToken,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get new access token using refresh token."""
    # Validate refresh token (stored in DB with longer expiry)
    # Return new access token
    pass
```

## Frontend Implementation (React/TypeScript)

### Auth API Service (`frontend/src/services/authApi.ts`)

```typescript
import axios from 'axios'

const API_BASE_URL = '/api'
const TOKEN_KEY = 'auth_token'

export interface User {
    id: string
    username: string
    email: string
    full_name: string | null
    disabled: boolean
}

export interface Token {
    access_token: string
    token_type: string
}

export const getStoredToken = (): string | null => {
    return localStorage.getItem(TOKEN_KEY)
}

export const setStoredToken = (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token)
}

export const removeStoredToken = (): void => {
    localStorage.removeItem(TOKEN_KEY)
}

export const login = async (username: string, password: string): Promise<Token> => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const response = await axios.post<Token>('/api/auth/token', formData.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return response.data
}

export const register = async (userData: UserCreate): Promise<User> => {
    const response = await axios.post<User>('/api/auth/register', userData)
    return response.data
}

export const getCurrentUser = async (token: string): Promise<User> => {
    const response = await axios.get<User>('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
}
```

### Auth Redux Slice (`frontend/src/store/authSlice.ts`)

```typescript
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import {
    login as loginApi,
    getCurrentUser,
    getStoredToken,
    setStoredToken,
    removeStoredToken,
} from '../services/authApi'

interface AuthState {
    user: User | null
    token: string | null
    isAuthenticated: boolean
    loading: boolean
    error: string | null
}

export const loginUser = createAsyncThunk(
    'auth/login',
    async ({ username, password }, { rejectWithValue }) => {
        try {
            const tokenResponse = await loginApi(username, password)
            setStoredToken(tokenResponse.access_token)
            const user = await getCurrentUser(tokenResponse.access_token)
            return { user, token: tokenResponse.access_token }
        } catch (error) {
            removeStoredToken()
            return rejectWithValue(error.response?.data?.detail || 'Login failed')
        }
    }
)

export const checkAuth = createAsyncThunk(
    'auth/check',
    async (_, { rejectWithValue }) => {
        const token = getStoredToken()
        if (!token) return rejectWithValue('No token')
        try {
            return await getCurrentUser(token)
        } catch {
            removeStoredToken()
            return rejectWithValue('Invalid token')
        }
    }
)

const authSlice = createSlice({
    name: 'auth',
    initialState: {
        user: null,
        token: getStoredToken(),
        isAuthenticated: false,
        loading: false,
        error: null,
    },
    reducers: {
        logout: (state) => {
            removeStoredToken()
            state.user = null
            state.token = null
            state.isAuthenticated = false
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(loginUser.fulfilled, (state, action) => {
                state.user = action.payload.user
                state.token = action.payload.token
                state.isAuthenticated = true
            })
            .addCase(checkAuth.fulfilled, (state, action) => {
                state.user = action.payload
                state.isAuthenticated = true
            })
    },
})
```

### API Client with Interceptors (`frontend/src/services/api.ts`)

```typescript
import axios from 'axios'
import { getStoredToken, removeStoredToken } from './authApi'

const apiClient = axios.create({
    baseURL: '/api',
    headers: { 'Content-Type': 'application/json' },
})

// Add token to all requests
apiClient.interceptors.request.use((config) => {
    const token = getStoredToken()
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Handle 401 errors globally
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            removeStoredToken()
            window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        }
        return Promise.reject(error)
    }
)
```

### Auth Guard Component (`frontend/src/components/auth/AuthGuard.tsx`)

```typescript
import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { checkAuth, logout } from '../../store/authSlice'
import { Login } from './Login'
import { Register } from './Register'

export const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const dispatch = useDispatch()
    const { isAuthenticated, loading, token } = useSelector((state) => state.auth)
    const [authView, setAuthView] = useState<'login' | 'register'>('login')

    useEffect(() => {
        if (token && !isAuthenticated) {
            dispatch(checkAuth())
        }
    }, [dispatch, token, isAuthenticated])

    useEffect(() => {
        const handleUnauthorized = () => dispatch(logout())
        window.addEventListener('auth:unauthorized', handleUnauthorized)
        return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }, [dispatch])

    if (loading) return <LoadingSpinner />

    if (!isAuthenticated) {
        return authView === 'login'
            ? <Login onSwitchToRegister={() => setAuthView('register')} />
            : <Register onSwitchToLogin={() => setAuthView('login')} />
    }

    return <>{children}</>
}
```

### Usage in App.tsx

```typescript
import { AuthGuard, UserMenu } from './components/auth'

const App = () => (
    <AuthGuard>
        <nav>
            <h1>App Title</h1>
            <UserMenu />
        </nav>
        <main>
            {/* Protected content */}
        </main>
    </AuthGuard>
)
```
