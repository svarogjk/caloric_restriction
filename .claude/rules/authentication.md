# Authentication Rules

Rules for implementing and maintaining OAuth2 JWT authentication.

## Security Requirements

| Rule | Enforcement |
|------|-------------|
| Never store plaintext passwords | Required |
| Use Argon2 for password hashing (pwdlib) | Required |
| JWT secret from environment variable only | Required |
| Token expiration must be enforced | Required |
| HTTPS in production | Required |

## Password Rules

```python
# CORRECT - Use pwdlib with Argon2
from pwdlib import PasswordHash
password_hash = PasswordHash.recommended()
hashed = password_hash.hash(plain_password)

# WRONG - Never store plain passwords
user.password = request.password  # NEVER DO THIS
```

## JWT Token Rules

1. **Always include expiration**
   ```python
   to_encode.update({"exp": datetime.now(timezone.utc) + expires_delta})
   ```

2. **Use "sub" claim for username**
   ```python
   data={"sub": user.username}
   ```

3. **Validate token on every protected request**
   ```python
   payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
   ```

## API Endpoint Patterns

### Registration
```python
@router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, ...):
    # Check username exists
    # Check email exists
    # Hash password
    # Create user
```

### Login
```python
@router.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm, ...):
    # Authenticate user
    # Create JWT token
    # Return token
```

### Protected Routes
```python
@router.get("/protected")
async def protected_route(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    # User is authenticated
```

## Dependency Injection

```python
# Auth service dependency
async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(session=db)

# Current user dependency
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    # Decode and validate token
    # Fetch user from database
```

## Error Handling

| Scenario | Status Code | Response |
|----------|-------------|----------|
| Invalid credentials | 401 | `{"detail": "Incorrect username or password"}` |
| Invalid token | 401 | `{"detail": "Could not validate credentials"}` |
| User disabled | 400 | `{"detail": "Inactive user"}` |
| Username taken | 400 | `{"detail": "Username already registered"}` |
| Email taken | 400 | `{"detail": "Email already registered"}` |

Always include `WWW-Authenticate: Bearer` header on 401 responses.

## Environment Variables

Required in `backend/.env`:
```
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Database Model

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[str]  # UUID
    username: Mapped[str]  # Unique
    email: Mapped[str]  # Unique
    hashed_password: Mapped[str]  # Argon2 hash
    disabled: Mapped[bool]  # For soft-disable
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

## Testing Authentication

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "test@example.com", "password": "secure123"}'

# Login (note: x-www-form-urlencoded for OAuth2)
curl -X POST http://localhost:8000/auth/token \
  -d "username=test&password=secure123"

# Protected request
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```
