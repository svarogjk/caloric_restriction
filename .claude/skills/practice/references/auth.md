# Auth Exercises

JWT authentication exercises based on `backend/app/services/auth_service.py` and `frontend/src/services/authApi.ts`.

## Beginner

### Exercise 1: Password Hashing with Argon2
**Task**: Create functions to hash passwords with Argon2 and verify them. Use `pwdlib` with the argon2 backend. Never store plaintext passwords.
**Starter code**:
```python
from pwdlib import PasswordHash

# TODO: Create a PasswordHash instance with argon2 backend
# password_hash = PasswordHash(...)

def hash_password(password: str) -> str:
    # TODO: Hash the password and return the hash string
    return ""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # TODO: Verify the plain password against the hash
    # TODO: Return True if match, False otherwise
    return False
```
**Test criteria**:
- Hash is different from plaintext, hash format starts with "$argon2"
- Correct password verifies True, wrong password verifies False
- Same password produces different hashes (salt is random)
**Key concepts**: Argon2, password hashing, verification, salting

### Exercise 2: Create and Decode JWT Tokens
**Task**: Create a JWT token with custom claims (sub, exp, iat, role) and decode it back. Handle expired tokens by raising an appropriate error.
**Starter code**:
```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "test-secret-key"
ALGORITHM = "HS256"

def create_token(user_id: str, role: str = "user", expires_minutes: int = 30) -> str:
    # TODO: Build payload with sub, role, exp (now + expires_minutes), iat (now)
    # TODO: Encode with jwt.encode using SECRET_KEY and ALGORITHM
    return ""

def decode_token(token: str) -> dict:
    # TODO: Decode with jwt.decode, verify expiration
    # TODO: Return payload dict
    # TODO: Raise ValueError("Token expired") on jwt.ExpiredSignatureError
    # TODO: Raise ValueError("Invalid token") on jwt.InvalidTokenError
    return {}
```
**Test criteria**:
- Token encodes and decodes correctly, sub and role preserved
- Expired token raises ValueError, tampered token raises ValueError
**Key concepts**: JWT encode/decode, claims (sub, exp, iat), expiration

## Intermediate

### Exercise 3: FastAPI Auth Dependency
**Task**: Build a FastAPI dependency that extracts and validates JWT from the Authorization header. Use `OAuth2PasswordBearer` and return the current user. Include proper 401 responses.
**Starter code**:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    # TODO: Decode the JWT token
    # TODO: Extract user_id from "sub" claim
    # TODO: Look up user in database (simulated)
    # TODO: Raise HTTPException(401) if token invalid or user not found
    # TODO: Return user dict
    return {}

async def get_current_active_user(user: dict = Depends(get_current_user)) -> dict:
    # TODO: Check if user["disabled"] is True
    # TODO: Raise HTTPException(403) if disabled
    # TODO: Return active user
    return {}
```
**Test criteria**:
- Valid token returns user, invalid token returns 401
- Expired token returns 401, disabled user returns 403
- Dependency chain: oauth2_scheme → get_current_user → get_current_active_user
**Key concepts**: OAuth2PasswordBearer, Depends, HTTPException 401/403, dependency chain

### Exercise 4: Login and Register Endpoints
**Task**: Create `/auth/register` (POST) and `/auth/token` (POST) endpoints. Register validates unique username/email and hashes password. Login verifies credentials and returns access token.
**Starter code**:
```python
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

router = APIRouter(prefix="/api/auth")

# TODO: POST /register - create user with hashed password
#   Raise 400 if username or email already exists
# TODO: POST /token - verify credentials, return Token
#   Use OAuth2PasswordRequestForm for standard form login
#   Raise 401 if credentials invalid
```
**Test criteria**:
- Register creates user with hashed password, rejects duplicates
- Login returns valid JWT token, rejects wrong password
**Key concepts**: OAuth2PasswordRequestForm, password hashing, token creation, 400/401

## Advanced

### Exercise 5: Token Refresh Flow
**Task**: Implement access + refresh token pair. Access token expires in 30 min, refresh token in 7 days. Create `/auth/refresh` endpoint that accepts refresh token and returns new access token. Invalidate old refresh tokens.
**Starter code**:
```python
def create_token_pair(user_id: str) -> dict:
    # TODO: Create short-lived access token (30 min)
    # TODO: Create long-lived refresh token (7 days) with "type": "refresh" claim
    # TODO: Return {"access_token": ..., "refresh_token": ..., "token_type": "bearer"}
    return {}

# TODO: POST /auth/refresh endpoint
#   Accept refresh_token in request body
#   Validate it's a refresh type token (check "type" claim)
#   Verify it's not expired
#   Issue new access token (but NOT new refresh token)
#   Return Token response
```
**Test criteria**:
- Access and refresh tokens have different expiration times
- Refresh endpoint rejects access tokens (wrong type)
- Refresh endpoint rejects expired refresh tokens
- Returns new access token without changing refresh token
**Key concepts**: Token pairs, refresh flow, token types, expiration management

### Exercise 6: Axios Interceptors for Auth
**Task**: Create an Axios instance with request interceptor (inject Bearer token from localStorage) and response interceptor (catch 401, remove token, dispatch logout event). Include retry logic for token refresh.
**Starter code**:
```typescript
import axios from 'axios';

const apiClient = axios.create({ baseURL: '/api' });

// TODO: Request interceptor:
//   Read token from localStorage('auth_token')
//   If token exists, set Authorization header

// TODO: Response interceptor:
//   On 401 error: remove token from localStorage
//   Dispatch custom event 'auth:unauthorized'
//   Return Promise.reject(error)
//   On other errors: return Promise.reject(error)

// TODO: Export typed API methods:
//   login(username, password) → Token
//   register(userData) → User
//   getCurrentUser() → User
```
**Test criteria**:
- Request interceptor adds Bearer header when token exists
- Response interceptor catches 401 and cleans up
- Custom event dispatched on unauthorized
**Key concepts**: Axios interceptors, localStorage, custom events, token management
