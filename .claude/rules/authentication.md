---
paths:
  - "backend/app/**/*auth*"
  - "backend/app/schemas/auth*"
  - "frontend/src/**/*auth*"
  - "frontend/src/**/Auth*"
  - "frontend/src/**/*Login*"
  - "frontend/src/**/*Register*"
---

# Authentication Rules

OAuth2 JWT authentication with Argon2 password hashing.

## Security Requirements

- Never store plaintext passwords - use `pwdlib` with Argon2: `PasswordHash.recommended().hash(password)`
- JWT secret from environment variable only (`JWT_SECRET_KEY`)
- Always include token expiration: `{"exp": datetime.now(timezone.utc) + expires_delta}`
- Use `"sub"` claim for username
- Validate token on every protected request via `Depends(get_current_active_user)`
- HTTPS in production

## Error Responses

| Scenario | Status | Detail |
|----------|--------|--------|
| Invalid credentials | 401 | `Incorrect username or password` |
| Invalid/expired token | 401 | `Could not validate credentials` |
| User disabled | 400 | `Inactive user` |
| Username taken | 400 | `Username already registered` |
| Email taken | 400 | `Email already registered` |

Always include `WWW-Authenticate: Bearer` header on 401 responses.

## Environment Variables

Required in `backend/.env`:
```
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```
