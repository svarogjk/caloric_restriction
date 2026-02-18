---
name: oauth2-jwt-auth
description: Full-stack OAuth2 JWT authentication patterns for FastAPI backend and React frontend. Use when implementing user registration, login, token management, route protection, or auth components.
---

# OAuth2 JWT Authentication

Full-stack auth using FastAPI + pyjwt + pwdlib (backend) and React + Redux + Axios interceptors (frontend).

## Project Structure

### Backend
```
backend/app/
├── api/auth_routes.py       # POST /auth/register, /auth/token, GET /auth/me
├── api/dependencies.py      # get_current_user, get_current_active_user
├── models/database.py       # User SQLAlchemy model
├── schemas/auth.py          # UserCreate, UserResponse, Token, TokenData
├── services/auth_service.py # Password hashing (Argon2), JWT creation, user CRUD
└── config/settings.py       # JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
```

### Frontend
```
frontend/src/
├── components/auth/
│   ├── Login.tsx, Register.tsx, AuthGuard.tsx, UserMenu.tsx
├── services/authApi.ts      # Token storage, login/register API calls
└── store/authSlice.ts       # Redux auth state, async thunks
```

## Key Patterns

### Password Hashing (Argon2)
```python
from pwdlib import PasswordHash
password_hash = PasswordHash.recommended()
hashed = password_hash.hash(plain_password)
is_valid = password_hash.verify(plain_password, hashed)
```

### JWT Token Creation
```python
import jwt
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=30))
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
```

### Route Protection (FastAPI Dependency)
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           auth_service: AuthService = Depends(get_auth_service)) -> User:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    user = await auth_service.get_user_by_username(payload.get("sub"))
    if not user: raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
```

### Frontend Token Management
```typescript
// Axios interceptor adds token to all requests
apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('auth_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// Handle 401 globally
apiClient.interceptors.response.use(r => r, (error) => {
    if (error.response?.status === 401) {
        localStorage.removeItem('auth_token');
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    return Promise.reject(error);
});
```

## Environment Variables

```bash
# backend/.env - generate secret with: openssl rand -hex 32
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Error Responses

| Scenario | Status | Response |
|----------|--------|----------|
| Invalid credentials | 401 | `{"detail": "Incorrect username or password"}` |
| Invalid/expired token | 401 | `{"detail": "Could not validate credentials"}` |
| Missing token | 401 | `{"detail": "Not authenticated"}` |
| Username taken | 400 | `{"detail": "Username already registered"}` |

## Testing

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "securepass123"}'

# Login (form data)
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=securepass123"

# Protected route
curl http://localhost:8000/auth/me -H "Authorization: Bearer <token>"
```

For detailed implementation code, see:
- [Backend implementation](references/backend.md)
- [Frontend implementation](references/frontend.md)
