# 08 - Segurança & Multi-Tenancy

## Arquitetura de Segurança

```
┌──────────────────────────────────────────────────────────────┐
│                      CAMADAS DE SEGURANÇA                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. NETWORK          HTTPS (TLS 1.3) + HSTS                │
│     ↓                CloudFront + WAF                        │
│  2. API GATEWAY      Rate Limiting por tier                  │
│     ↓                Input validation (Pydantic)             │
│  3. AUTH             JWT (RS256) + Refresh tokens            │
│     ↓                Session management                      │
│  4. AUTHORIZATION    RBAC (Role-Based Access Control)        │
│     ↓                Endpoint-level permissions               │
│  5. DATA ISOLATION   PostgreSQL RLS (Row-Level Security)     │
│     ↓                S3 prefix isolation                     │
│  6. ML ISOLATION     Global models, per-org results          │
│     ↓                Feature store scoped by org_id          │
│  7. AUDIT            Full audit log of all data access       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 1. Autenticação (JWT)

### Estrutura do Token

```python
# Access Token (vida curta: 1 hora)
{
    "sub": "user-uuid",
    "org_id": "org-uuid",
    "role": "coach",
    "team_ids": ["team-uuid-1", "team-uuid-2"],
    "email": "coach@team.com",
    "iat": 1710000000,
    "exp": 1710003600,  # +1 hora
    "iss": "cs2-analytics"
}

# Refresh Token (vida longa: 30 dias)
# Armazenado como hash em PostgreSQL
# Rotação: novo refresh token emitido a cada refresh
```

### Implementação FastAPI

```python
# packages/backend/src/middleware/auth.py

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta

security = HTTPBearer()

# RS256 (asymmetric) — private key no backend, public key para validação
ALGORITHM = "RS256"
PRIVATE_KEY = load_from_secrets_manager("jwt-private-key")
PUBLIC_KEY = load_from_secrets_manager("jwt-public-key")

def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "org_id": str(user.org_id),
        "role": user.role,
        "team_ids": [str(t.id) for t in user.teams],
        "email": user.email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iss": "cs2-analytics"
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenPayload:
    try:
        payload = jwt.decode(
            credentials.credentials,
            PUBLIC_KEY,
            algorithms=[ALGORITHM],
            issuer="cs2-analytics"
        )
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Password hashing
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### Requisitos de Password

```
Mínimo 10 caracteres
Pelo menos 1 maiúscula, 1 minúscula, 1 número
Não pode conter email ou nome do utilizador
Bcrypt com cost factor 12
Rate limit: 5 tentativas falhadas → bloqueio 15 min
```

---

## 2. RBAC (Role-Based Access Control)

### Permissões por Função

| Ação | admin | coach | analyst | player | viewer |
|------|-------|-------|---------|--------|--------|
| Gerir organização | Sim | - | - | - | - |
| Gerir faturação | Sim | - | - | - | - |
| Convidar utilizadores | Sim | Sim | - | - | - |
| Gerir roster | Sim | Sim | - | - | - |
| Upload de demos | Sim | Sim | Sim | - | - |
| Apagar demos | Sim | Sim | - | - | - |
| Ver matches da equipa | Sim | Sim | Sim | Sim | Sim |
| Ver deteção de erros | Sim | Sim | Sim | Sim* | Sim* |
| Ver análise tática | Sim | Sim | Sim | Sim* | - |
| Gerar scout reports | Sim | Sim | Sim | - | - |
| Ver scout reports | Sim | Sim | Sim | - | - |
| Ver plano de treino | Sim | Sim | Sim | Próprio | - |
| Dar feedback em erros | Sim | Sim | Sim | - | - |
| Exportar PDF | Sim | Sim | Sim | - | - |
| Acesso API | Sim | Sim | Sim | - | - |

*player vê dados filtrados para o próprio jogador preferencialmente

### Implementação do RBAC

```python
# packages/backend/src/middleware/authorization.py

from enum import Enum
from functools import wraps

class Permission(Enum):
    MANAGE_ORG = "manage_org"
    MANAGE_BILLING = "manage_billing"
    INVITE_USERS = "invite_users"
    MANAGE_ROSTER = "manage_roster"
    UPLOAD_DEMOS = "upload_demos"
    DELETE_DEMOS = "delete_demos"
    VIEW_MATCHES = "view_matches"
    VIEW_ERRORS = "view_errors"
    VIEW_TACTICS = "view_tactics"
    GENERATE_SCOUT = "generate_scout"
    VIEW_SCOUT = "view_scout"
    VIEW_TRAINING = "view_training"
    SUBMIT_FEEDBACK = "submit_feedback"
    EXPORT_DATA = "export_data"
    API_ACCESS = "api_access"

ROLE_PERMISSIONS = {
    "admin": set(Permission),  # Todas
    "coach": {
        Permission.INVITE_USERS, Permission.MANAGE_ROSTER,
        Permission.UPLOAD_DEMOS, Permission.DELETE_DEMOS,
        Permission.VIEW_MATCHES, Permission.VIEW_ERRORS,
        Permission.VIEW_TACTICS, Permission.GENERATE_SCOUT,
        Permission.VIEW_SCOUT, Permission.VIEW_TRAINING,
        Permission.SUBMIT_FEEDBACK, Permission.EXPORT_DATA,
        Permission.API_ACCESS,
    },
    "analyst": {
        Permission.UPLOAD_DEMOS, Permission.VIEW_MATCHES,
        Permission.VIEW_ERRORS, Permission.VIEW_TACTICS,
        Permission.GENERATE_SCOUT, Permission.VIEW_SCOUT,
        Permission.VIEW_TRAINING, Permission.SUBMIT_FEEDBACK,
        Permission.EXPORT_DATA, Permission.API_ACCESS,
    },
    "player": {
        Permission.VIEW_MATCHES, Permission.VIEW_ERRORS,
        Permission.VIEW_TACTICS, Permission.VIEW_TRAINING,
    },
    "viewer": {
        Permission.VIEW_MATCHES, Permission.VIEW_ERRORS,
    },
}

def require_permission(permission: Permission):
    """Dependency para verificar permissão."""
    async def check(user: TokenPayload = Depends(get_current_user)):
        if permission not in ROLE_PERMISSIONS.get(user.role, set()):
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check

# Uso nos endpoints:
@app.post("/api/v1/demos/upload")
async def upload_demo(
    file: UploadFile,
    user: TokenPayload = Depends(require_permission(Permission.UPLOAD_DEMOS))
):
    ...
```

---

## 3. Multi-Tenancy (Row-Level Security)

### Estratégia: Base de Dados Partilhada, Isolamento a Nível de Linha

```
Todas as tabelas com dados de cliente têm coluna org_id.
PostgreSQL RLS garante que queries só retornam dados da org do user.
Mesmo que haja bug no código, RLS é a última linha de defesa.
```

### Middleware de Inquilino (Tenant)

```python
# packages/backend/src/middleware/tenant.py

from sqlalchemy.ext.asyncio import AsyncSession

class TenantMiddleware:
    """
    Middleware que define o org_id no contexto do PostgreSQL
    para que RLS policies filtrem automaticamente.
    """

    async def __call__(self, request: Request, call_next):
        user = request.state.user  # Set by auth middleware

        if user:
            # Definir variável de sessão PostgreSQL
            async with get_db_session() as session:
                await session.execute(
                    text(f"SET app.current_org_id = '{user.org_id}'")
                )
                request.state.db = session

        response = await call_next(request)
        return response
```

### Políticas RLS

```sql
-- Ativar RLS
ALTER TABLE demos ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE detected_errors ENABLE ROW LEVEL SECURITY;
ALTER TABLE tactical_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_weakness_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE scout_reports ENABLE ROW LEVEL SECURITY;

-- Policy: users só veem dados da sua org
CREATE POLICY org_isolation_demos ON demos
    FOR ALL
    USING (org_id = current_setting('app.current_org_id')::UUID)
    WITH CHECK (org_id = current_setting('app.current_org_id')::UUID);

-- Repetir para todas as tabelas...
-- FOR ALL = SELECT, INSERT, UPDATE, DELETE

-- Role do application user (não é superuser)
CREATE ROLE app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- app_user NÃO tem BYPASSRLS
```

### Isolamento S3

```
Estrutura S3:
  s3://cs2-analytics-demos/
    ├── {org_id_1}/
    │   ├── demos/
    │   │   ├── {demo_id_1}.dem
    │   │   └── {demo_id_2}.dem
    │   └── exports/
    ├── {org_id_2}/
    │   ├── demos/
    │   └── exports/
    └── training/          # Dados anónimos para treino ML
        └── pro_demos/

Pre-signed URLs:
  - Gerados apenas para demos da org do user
  - Expiram em 1 hora
  - Validação no backend antes de gerar URL
```

### Isolamento ClickHouse

```python
# ClickHouse não suporta RLS nativo
# Isolamento feito na camada de aplicação

class ClickHouseClient:
    async def query(self, sql: str, org_id: UUID, **params):
        """Todas as queries ClickHouse DEVEM passar por este client
        que injeta o filtro org_id."""

        # Garantir que org_id está nos filtros
        if 'WHERE' in sql.upper():
            sql = sql.replace('WHERE', f'WHERE org_id = %(org_id)s AND')
        else:
            sql += f' WHERE org_id = %(org_id)s'

        params['org_id'] = str(org_id)
        return await self._execute(sql, params)
```

---

## 4. Validação & Sanitização de Input

### Validação de Ficheiros Demo

```python
# packages/backend/src/services/demo_service.py

DEMO_MAGIC_BYTES = b'PBDEMS2'  # CS2 demo magic bytes
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

async def validate_demo_file(file: UploadFile) -> bool:
    # 1. Verificar extensão
    if not file.filename.endswith('.dem'):
        raise HTTPException(400, "File must be a .dem file")

    # 2. Verificar tamanho
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    if size < 1024:
        raise HTTPException(400, "File too small to be a valid demo")

    # 3. Verificar magic bytes
    header = await file.read(7)
    await file.seek(0)
    if header != DEMO_MAGIC_BYTES:
        raise HTTPException(400, "Invalid demo file format")

    # 4. Virus scan (ClamAV ou similar)
    # await scan_file(file)

    return True
```

### Validação Pydantic

```python
# packages/backend/src/schemas/team.py

from pydantic import BaseModel, Field, validator
import re

class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    tag: str | None = Field(None, max_length=10)
    game_team_name: str | None = Field(None, max_length=255)

    @validator('name')
    def sanitize_name(cls, v):
        # Remover caracteres perigosos
        v = v.strip()
        if re.search(r'[<>"\'/;(){}]', v):
            raise ValueError('Name contains invalid characters')
        return v

    @validator('tag')
    def sanitize_tag(cls, v):
        if v:
            v = re.sub(r'[^a-zA-Z0-9]', '', v)
        return v
```

---

## 5. Rate Limiting

```python
# packages/backend/src/middleware/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

TIER_LIMITS = {
    'free': {
        'demo_uploads_per_day': 2,
        'api_calls_per_minute': 30,
        'scout_reports_per_month': 1,
    },
    'basic': {
        'demo_uploads_per_day': 10,
        'api_calls_per_minute': 120,
        'scout_reports_per_month': 10,
    },
    'premium': {
        'demo_uploads_per_day': -1,   # Unlimited
        'api_calls_per_minute': 600,
        'scout_reports_per_month': -1,
    },
}

# Aplicar nos endpoints:
@app.post("/api/v1/demos/upload")
@limiter.limit(lambda: get_tier_limit('demo_uploads_per_day'))
async def upload_demo(...):
    ...
```

---

## 6. Segurança de Dados ML

```
PRINCÍPIO: Modelos são globais, resultados são isolados.

Training Data:
  - Modelos treinados em dados ANÓNIMOS (sem org_id, sem nomes)
  - Apenas features numéricas são usadas no treino
  - Dados pro (públicos) usados como baseline principal
  - Dados de utilizadores: opt-in, anonimizados antes de inclusão

Inference Results:
  - Cada resultado (erro, tática, rating) tem org_id
  - Armazenado nas tabelas com RLS
  - Isolamento total entre organizações

Feature Store (PostgreSQL + Redis):
  - Features keyed por (org_id, entity_id)
  - PostgreSQL offline store com RLS por org_id
  - Redis online store com key prefixes por org_id
  - Sem acesso cross-org

Model Artifacts:
  - Modelos armazenados no MLflow (acesso interno apenas)
  - Não contêm dados de utilizadores
  - Versionados e auditáveis
```

---

## 7. HTTPS & Cabeçalhos de Segurança

```python
# packages/backend/src/middleware/security_headers.py

from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response
```

---

## 8. Audit Log

```python
# packages/backend/src/services/audit_service.py

async def log_action(
    org_id: UUID,
    user_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
):
    await db.execute(
        insert(AuditLog).values(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            ip_address=ip_address,
        )
    )

# Ações auditadas:
# - login, logout, failed_login
# - upload_demo, delete_demo
# - view_match, view_errors, view_scout_report
# - generate_scout_report, export_pdf
# - invite_user, remove_user, change_role
# - change_billing, upgrade_tier
```

---

## 9. GDPR Compliance

```python
# Endpoint de data deletion (GDPR Art. 17)

@app.delete("/api/v1/privacy/player/{steam_id}")
async def delete_player_data(
    steam_id: str,
    user: TokenPayload = Depends(require_permission(Permission.MANAGE_ORG))
):
    """
    Apagar todos os dados associados a um steam_id.
    Requerido por GDPR right to erasure.
    """
    # 1. PostgreSQL: delete de todas as tabelas
    await delete_player_errors(steam_id, user.org_id)
    await delete_player_ratings(steam_id, user.org_id)
    await delete_player_weaknesses(steam_id, user.org_id)

    # 2. ClickHouse: anonymize (não delete, para integridade)
    await anonymize_player_ticks(steam_id, user.org_id)
    await anonymize_player_events(steam_id, user.org_id)

    # 3. Audit log
    await log_action(user.org_id, user.sub, "gdpr_deletion",
                     "player", metadata={"steam_id": steam_id})

    return {"message": f"All data for player {steam_id} has been deleted"}
```

---

## 10. Gestão de Secrets

```
Todos os secrets geridos via AWS Secrets Manager:

- jwt-private-key / jwt-public-key
- database-url (PostgreSQL)
- clickhouse-url
- redis-url
- s3-access-key / s3-secret-key
- mlflow-tracking-uri
- stripe-api-key
- hltv-api-key (se aplicável)

NUNCA em:
- Environment variables do container
- Ficheiros de configuração
- Código fonte
- Docker images

Rotação:
- JWT keys: a cada 90 dias
- Database passwords: a cada 90 dias
- API keys: a cada 180 dias
```
