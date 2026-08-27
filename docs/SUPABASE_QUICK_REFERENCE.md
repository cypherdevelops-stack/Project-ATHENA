# Supabase Migration: Quick Copy-Paste Guide

Use this file for fast reference. Copy-paste code directly.

---

## 1. Create requirements.txt

**File:** `backend/requirements.txt`

```txt
Django==6.0.3
daphne==4.1.2
djangorestframework==3.14.0
channels==4.0.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
xgboost==2.0.3
numpy==1.24.3
pandas==2.0.3
```

**Install:**
```bash
cd backend
pip install -r requirements.txt
```

---

## 2. Create .env File

**File:** `backend/.env`

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=YOUR_SUPABASE_PASSWORD
DB_HOST=db.xxxxx.supabase.co
DB_PORT=5432

DEBUG=True
SECRET_KEY=django-insecure-r&p_tx8s-q=5sbizkagr#qj(=92&xi2+5j9y3u+ov)fby*410f
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
```

**Replace:**
- `YOUR_SUPABASE_PASSWORD` → Your actual Supabase password
- `db.xxxxx.supabase.co` → Your actual Supabase host
- `SECRET_KEY` → Keep your existing key (or generate new one)

---

## 3. Update settings.py

### 3.1 Add imports at top

**After:** `from pathlib import Path`

**Add:**
```python
import os
from dotenv import load_dotenv
```

### 3.2 Load .env after BASE_DIR

**After:** `BASE_DIR = Path(__file__).resolve().parent.parent`

**Add:**
```python
# Load environment variables
load_dotenv(BASE_DIR.parent / '.env')
```

### 3.3 Replace DATABASES section

**Find:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

**Replace with:**
```python
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'postgres'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c default_transaction_isolation=read_committed',
        },
    }
}
```

---

## 4. Test Connection

```bash
cd backend
python manage.py dbshell
```

Type `\q` to exit. Should connect without errors.

---

## 5. Backup & Migrate

```bash
cd backend

# Backup SQLite
cp db.sqlite3 db.sqlite3.backup

# Export data (optional)
python manage.py dumpdata > data_backup.json

# Run migrations on Supabase
python manage.py migrate
```

---

## 6. Create Superuser

```bash
cd backend
python manage.py createsuperuser
```

Follow prompts.

---

## 7. Test Admin

```bash
cd backend
python manage.py runserver
```

Visit: http://localhost:8000/admin

Login with superuser credentials.

---

## 8. Create .gitignore Entry

**File:** `.gitignore`

**Add:**
```
.env
db.sqlite3
db.sqlite3.backup
*.pyc
__pycache__/
data_backup.json
```

---

## 9. Create .env.example (For Team)

**File:** `backend/.env.example`

```env
# Database (use Supabase credentials)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=db.xxxxx.supabase.co
DB_PORT=5432

# Django
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Troubleshooting Commands

### Test PostgreSQL Connection Directly

```bash
psql -h db.xxxxx.supabase.co -U postgres -d postgres -c "SELECT 1;"
```

Should return:
```
 ?column?
----------
        1
```

### Check Django Migrations Status

```bash
cd backend
python manage.py showmigrations
```

### Re-run Migrations (If Failed)

```bash
cd backend
python manage.py migrate --verbosity 2
```

### Fake Initial Migration (If Already Migrated)

```bash
cd backend
python manage.py migrate --fake-initial
```

### Drop All Tables & Start Fresh (DANGEROUS)

```bash
cd backend
python manage.py migrate zero
python manage.py migrate
```

### Export Data from SQLite to JSON

```bash
cd backend
python manage.py dumpdata --database sqlite_bak > backup.json
```

Wait, Django doesn't alias that. Use instead:

```bash
sqlite3 db.sqlite3.backup ".dump" > sqlite_dump.sql
```

---

## Rollback to SQLite

If something goes wrong:

1. **Update settings.py:**

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

2. **Restore backup:**

```bash
cp db.sqlite3.backup db.sqlite3
```

3. **Restart:**

```bash
python manage.py runserver
```

---

## Quick Stats

```bash
cd backend
python manage.py shell
```

```python
from accounts.models import Account
from execution.models import LiveExecutionAttempt
from backtesting.models import ReplaySession

print(f"Accounts: {Account.objects.count()}")
print(f"Executions: {LiveExecutionAttempt.objects.count()}")
print(f"Backtests: {ReplaySession.objects.count()}")

# Show latest execution
exec = LiveExecutionAttempt.objects.latest('created_at')
print(f"\nLatest execution: {exec.broker_symbol} {exec.direction} @ {exec.created_at}")

exit()
```

---

## Production Environment Variables

**Heroku:**
```bash
heroku config:set DB_ENGINE=django.db.backends.postgresql
heroku config:set DB_HOST=db.xxxxx.supabase.co
heroku config:set DB_USER=postgres
heroku config:set DB_PASSWORD=xxxxx
heroku config:set DB_NAME=postgres
heroku config:set DB_PORT=5432
heroku config:set SECRET_KEY=your-new-secret-key
heroku config:set DEBUG=False
```

**Railway/Render:** Use dashboard to set env vars

**Docker:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV DB_ENGINE=django.db.backends.postgresql
ENV DEBUG=False

CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## Common Errors & Fixes

### `psycopg2.OperationalError: could not connect to server`

**Fix:** Check HOST and PORT in .env

```bash
# Test directly
psql -h db.xxxxx.supabase.co -U postgres -d postgres
```

### `django.db.utils.IntegrityError: duplicate key value violates unique constraint`

**Fix:** Fake the initial migration

```bash
python manage.py migrate --fake-initial
```

### `ProgrammingError: relation "auth_user" already exists`

**Fix:** Same as above

```bash
python manage.py migrate --fake-initial
```

### `permission denied for schema public`

**Fix:** Supabase PostgreSQL permissions might be restricted. Re-run migrations:

```bash
python manage.py migrate --verbosity 2
```

If still failing, go to Supabase → SQL Editor → run:

```sql
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
```

---

## Monitoring Supabase

### Check Active Connections

**Supabase Dashboard** → **Database** → **Connections**

### View Logs

**Supabase Dashboard** → **Logs** → **Postgres Logs**

### Query Performance

```sql
-- In Supabase SQL Editor
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

### Table Sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Enable Real-Time (Optional)

```bash
# Install real-time client (for frontend)
cd frontend
npm install @supabase/realtime-js
```

**In Django (settings.py):**

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_postgres.core.PostgresChannelLayer',
        'CONFIG': {
            'hosts': [
                (os.getenv('DB_HOST'), int(os.getenv('DB_PORT', 5432))),
            ],
            'db_name': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
        },
    }
}
```

**Install:**
```bash
pip install channels-postgres
```

---

## One-Liner Summary

```bash
# 1. Install
pip install psycopg2-binary python-dotenv

# 2. Add .env with Supabase credentials

# 3. Update settings.py (see Section 3)

# 4. Test
python manage.py dbshell

# 5. Backup & Migrate
cp db.sqlite3 db.sqlite3.backup && python manage.py migrate

# 6. Create user & test
python manage.py createsuperuser && python manage.py runserver
```

Done in 5 steps! 🚀

