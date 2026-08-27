# ATHENA Database Migration: SQLite → Supabase

This guide walks you through migrating your Django backend from SQLite to Supabase (managed PostgreSQL).

---

## Prerequisites

1. **Supabase account** (free tier available at https://supabase.com)
2. **Python 3.9+** (you already have this)
3. **pip package manager**
4. **PostgreSQL client tools** (optional, for direct SQL inspection)

---

## Step 1: Create Supabase Project

### 1.1 Create Account & Project

1. Go to https://supabase.com → **Sign up** (use email or OAuth)
2. Create new project:
   - Click **"New Project"**
   - **Name:** `athena-trading` (or your choice)
   - **Database Password:** Generate strong password (save this!)
   - **Region:** Choose region closest to your location or trading server
   - Click **"Create New Project"** (takes ~2 min)

### 1.2 Get Connection Details

1. Navigate to **Settings** → **Database** (left sidebar)
2. Copy the following (you'll need these):
   - **Host:** `db.xxxxx.supabase.co` (under Connection string, find host)
   - **Database:** `postgres`
   - **User:** `postgres`
   - **Password:** The one you just set
   - **Port:** `5432`

**Alternative: Get full connection string**
- In Settings → Database → Connection String
- Select **Postgres** tab
- Copy URI: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`

---

## Step 2: Update Django Dependencies

### 2.1 Create requirements.txt

Create file `backend/requirements.txt`:

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

**Note:** Adjust versions to match your actual dependencies. The key addition is `psycopg2-binary` (PostgreSQL adapter).

### 2.2 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**If psycopg2 fails to install:**
```bash
# macOS
pip install psycopg2-binary

# Ubuntu/Debian
sudo apt-get install postgresql-client libpq-dev
pip install psycopg2-binary

# Windows
pip install psycopg2-binary
```

---

## Step 3: Update Django Settings

### 3.1 Create .env File

Create `backend/.env`:

```env
# Supabase Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_supabase_password_here
DB_HOST=db.xxxxx.supabase.co
DB_PORT=5432

# Django Settings
DEBUG=True
SECRET_KEY=django-insecure-your-existing-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
```

**Replace:**
- `DB_PASSWORD` → Your Supabase password
- `DB_HOST` → Your Supabase host
- `SECRET_KEY` → Keep your existing secret key

### 3.2 Update settings.py

Modify `backend/settings.py`:

**Find this section:**
```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
```

**Add this after the import:**
```python
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR.parent / '.env')
```

**Find the DATABASES section:**
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

**Save the file.**

---

## Step 4: Test Database Connection

### 4.1 Verify Django Can Connect

```bash
cd backend
python manage.py dbshell
```

You should see a PostgreSQL prompt:
```
postgres=> 
```

Type `\q` to exit.

If you get an error:
- ❌ "could not connect to server" → Check HOST/PORT in .env
- ❌ "password authentication failed" → Check DB_PASSWORD
- ❌ "database does not exist" → DB_NAME should be `postgres` (default)

---

## Step 5: Migrate Data (Backup SQLite First)

### 5.1 Back Up Local SQLite Database

```bash
# In the backend directory
cp db.sqlite3 db.sqlite3.backup
```

**This is your safety net. Keep this file.**

### 5.2 Export Data from SQLite (Optional but Recommended)

If you have data you want to keep, export it:

```bash
cd backend

# Dump all data as JSON
python manage.py dumpdata > data_backup.json
```

This creates `data_backup.json` with all your database records.

### 5.3 Run Migrations on Supabase

```bash
cd backend

# Apply all Django migrations to Supabase
python manage.py migrate
```

Expected output:
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, ...
  
Running migrations:
  Applying accounts.0001_initial... OK
  Applying accounts.0002_account_user_many... OK
  ...
```

**If migrations fail:**
```bash
# Check migration status
python manage.py showmigrations

# Manually inspect what happened
python manage.py dbshell
```

---

## Step 6: Load Data (If You Have Existing Data)

### 6.1 Load JSON Backup into Supabase

If you exported data in Step 5.2:

```bash
cd backend

# Load the JSON dump into Supabase
python manage.py loaddata data_backup.json
```

**This works only if the Supabase schema exactly matches the SQLite schema.**

### 6.2 If loaddata Fails

**Option A: Start Fresh**
```bash
# Just delete the backup files
rm db.sqlite3.backup data_backup.json

# Your Supabase DB is now clean and ready
```

**Option B: Manual Sync (Advanced)**
- Export specific tables from SQLite using DB management tool
- Use Supabase Studio (web UI) to import CSV files
- Or write a Python script to copy records manually

For a new trading system, starting fresh is usually fine.

---

## Step 7: Create Superuser

```bash
cd backend

python manage.py createsuperuser
```

Prompts:
```
Username: admin
Email: your@email.com
Password: 
Password (again):
Superuser created successfully.
```

---

## Step 8: Test Django Admin

```bash
cd backend

# Start development server
python manage.py runserver
```

Visit: http://localhost:8000/admin

**Login with superuser credentials.** You should see all your models connected to Supabase.

---

## Step 9: Environment Configuration for Production

### 9.1 Update .env for Production

```env
# Production Supabase
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_supabase_password_here
DB_HOST=db.xxxxx.supabase.co
DB_PORT=5432

# Django Security
DEBUG=False
SECRET_KEY=your-super-secret-key-generate-new-one
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# Security Headers
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 9.2 Generate New Secret Key (Production Only)

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy output → update SECRET_KEY in .env

### 9.3 Don't Commit .env to Git

Add to `.gitignore`:
```
.env
db.sqlite3
db.sqlite3.backup
*.pyc
__pycache__/
```

---

## Step 10: Enable Supabase Features (Optional)

### 10.1 Real-Time Subscriptions (For WebSocket Updates)

Your ATHENA system uses Django Channels for WebSocket. You can optionally enable Supabase real-time:

1. Go to Supabase project → **Realtime** (left sidebar)
2. Enable tables for real-time: 
   - execution_liveexecutionattempt
   - execution_executionlifecycleevent
   - backtesting_replaysession
3. Django Channels will continue to work as-is (no changes needed)

### 10.2 Enable Row Level Security (RLS)

For production security:

1. Go to **Authentication** → **Policies**
2. Create policies to restrict data access per user
3. Update Django `ALLOWED_HOSTS` with your production domain

---

## Step 11: Monitor & Optimize

### 11.1 Check Connection Pool

In Supabase Dashboard → **Database** → **Connections:**
- View active connections
- Monitor query logs

### 11.2 Enable Query Logging (Optional)

In Supabase → **Logs** → **PostgreSQL Logs:**
- Monitor slow queries
- Debug connection issues

### 11.3 Set Up Backups

Supabase automatically backs up daily (free tier). To increase frequency:

1. Go to **Settings** → **Backups**
2. Upgrade to Pro for hourly backups (if needed)

---

## Step 12: Troubleshooting

### Connection Issues

**Problem:** `could not translate host name "db.xxxxx.supabase.co" to address`

**Solution:**
- Check HOST spelling in .env
- Verify internet connection
- Try direct PostgreSQL connection:
```bash
psql -h db.xxxxx.supabase.co -U postgres -d postgres
```

### Migration Issues

**Problem:** `django.db.utils.ProgrammingError: relation "auth_user" already exists`

**Solution:**
```bash
# Fake the initial migration (data already in DB)
python manage.py migrate --fake-initial
```

### Slow Queries

**Problem:** Queries running slowly compared to SQLite

**Solution:**
1. Check if tables are properly indexed:
```bash
python manage.py dbshell
SELECT * FROM pg_indexes WHERE tablename = 'execution_liveexecutionattempt';
```

2. Django auto-creates indexes for foreign keys, but you can optimize manually:
```sql
CREATE INDEX idx_execution_account ON execution_liveexecutionattempt(account_id);
CREATE INDEX idx_execution_created ON execution_liveexecutionattempt(created_at);
```

### Permission Issues

**Problem:** `permission denied for schema public`

**Solution:**
```bash
# Re-run migrations with superuser:
python manage.py migrate --verbosity 2
```

---

## Step 13: Migrate Channels Layer to Supabase (Optional)

If you want to persist WebSocket messages to Supabase instead of in-memory:

### Update settings.py

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

Install dependency:
```bash
pip install channels-postgres
```

---

## Step 14: Verify Data Integrity

### 14.1 Quick Sanity Check

```bash
cd backend

python manage.py shell
```

In the Python shell:

```python
from accounts.models import Account
from execution.models import LiveExecutionAttempt

# Count records
print(f"Accounts: {Account.objects.count()}")
print(f"Executions: {LiveExecutionAttempt.objects.count()}")

# Check recent execution
last_exec = LiveExecutionAttempt.objects.latest('created_at')
print(f"Latest execution: {last_exec}")

# Exit
exit()
```

### 14.2 Compare with SQLite Backup

```bash
# Open SQLite backup
cd backend

python manage.py shell --database sqlite_bak
```

Wait, Django doesn't alias databases that way. Instead, **manually compare:**

```bash
# In SQLite
sqlite3 db.sqlite3.backup

sqlite> SELECT COUNT(*) FROM execution_liveexecutionattempt;

# Then check Supabase:
python manage.py dbshell
postgres=> SELECT COUNT(*) FROM execution_liveexecutionattempt;
```

---

## Rollback Plan (If Something Goes Wrong)

### Revert to SQLite

```bash
# 1. Update settings.py back to SQLite
# Change DATABASES to:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 2. Restore backup
cp db.sqlite3.backup db.sqlite3

# 3. Restart Django
python manage.py runserver
```

**Your Supabase data stays in Supabase (doesn't affect the rollback).**

---

## Final Checklist

- [ ] Supabase project created
- [ ] Connection credentials saved securely
- [ ] `.env` file created with Supabase credentials
- [ ] `requirements.txt` created with `psycopg2-binary`
- [ ] `settings.py` updated to use environment variables
- [ ] Connection tested with `python manage.py dbshell`
- [ ] `db.sqlite3` backed up
- [ ] Migrations run: `python manage.py migrate`
- [ ] Superuser created: `python manage.py createsuperuser`
- [ ] Django admin tested at http://localhost:8000/admin
- [ ] `.env` added to `.gitignore`
- [ ] `.env.example` created (without passwords) for team reference

---

## Example .env.example (For Team/Repo)

Create `backend/.env.example`:

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

**This file goes in the repo. The actual `.env` stays private.**

---

## Next Steps

1. **Test in development** for 1 week (all systems running against Supabase)
2. **Monitor logs** at Supabase Dashboard
3. **Verify backtest engine** still works (uses DB queries for historical data)
4. **Verify execution engine** (reads/writes to DB during paper trading)
5. **Deploy to production** when confident

---

## Production Deployment Considerations

### Environment Variables in Production

**Heroku/Railway/Render:**
```bash
# Set environment variables via dashboard or CLI
heroku config:set DB_HOST=db.xxxxx.supabase.co
heroku config:set DB_PASSWORD=xxxxx
# ... etc
```

**Docker/Kubernetes:**
```yaml
# k8s secret
apiVersion: v1
kind: Secret
metadata:
  name: athena-db
type: Opaque
stringData:
  DB_HOST: db.xxxxx.supabase.co
  DB_PASSWORD: xxxxx
```

### Connection Pooling

For production with many concurrent requests, enable connection pooling in Supabase:

1. Go **Settings** → **Database** → **Connection Pooling**
2. Set **Pool Mode** to `Transaction`
3. Update Django settings:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ... other settings ...
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',
        },
        'CONN_MAX_AGE': 600,
    }
}
```

---

## Summary

| Step | Duration | Key Action |
|------|----------|-----------|
| 1. Create Supabase | 5 min | Project + credentials |
| 2. Install deps | 2 min | `pip install psycopg2-binary` |
| 3. Update settings | 5 min | Edit settings.py, create .env |
| 4. Test connection | 2 min | `python manage.py dbshell` |
| 5. Backup SQLite | 1 min | Copy db.sqlite3 |
| 6. Run migrations | 5 min | `python manage.py migrate` |
| 7. Create superuser | 2 min | `python manage.py createsuperuser` |
| 8. Test admin | 2 min | Visit /admin |
| **TOTAL** | **~25 min** | Complete migration |

---

**You're done!** Your ATHENA system now runs on Supabase PostgreSQL instead of local SQLite. 

---

**Questions?**
- Check Supabase docs: https://supabase.com/docs
- Django + PostgreSQL: https://docs.djangoproject.com/en/6.0/ref/databases/#postgresql-notes
- Troubleshoot connection: Use `psql` CLI or Supabase Studio UI

