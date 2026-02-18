# OAuth2 JWT Backend Implementation

## Pydantic Schemas (`backend/app/schemas/auth.py`)

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    disabled: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
```

## User Model (`backend/app/models/database.py`)

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan",
    )
```

Update Conversation model:
```python
user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
```

## Auth Service (`backend/app/services/auth_service.py`)

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

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = await self.get_user_by_username(username)
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def create_user(self, user_data: UserCreate) -> User:
        user = User(
            username=user_data.username, email=user_data.email,
            hashed_password=self.get_password_hash(user_data.password),
            full_name=user_data.full_name,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
```

## Auth Dependencies (`backend/app/api/dependencies.py`)

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
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
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = await auth_service.get_user_by_username(username)
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

## Auth Routes (`backend/app/api/auth_routes.py`)

```python
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    if await auth_service.get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if await auth_service.get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return await auth_service.create_user(user_data)

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
):
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                          headers={"WWW-Authenticate": "Bearer"})
    access_token = auth_service.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    return Token(access_token=access_token)

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user
```

## Protecting Routes

```python
@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    chat_service: ChatService = Depends(get_chat_service),
):
    conversation = await chat_service.create_conversation(
        title=request.title, context_type=request.context_type, user_id=current_user.id,
    )
    return CreateConversationResponse(...)
```

## Register in Main App

```python
# backend/app/main.py
from app.api.auth_routes import router as auth_router
app.include_router(auth_router)
```
