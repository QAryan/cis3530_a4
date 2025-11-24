# cis3530_a4
Assignment 4 for CIS*3530: Databases. The goal of this project is to build a small, data-driven web application using Flask and raw SQL.

# Setup

## 1. Setup environment
```
python3 -m venv .venv
MACOS/LINUX: source .venv/bin/activate
WINDOWS: .venv\Scripts\activate 
pip install -r requirements.txt
```

## 2. Setup database
```
createdb my_company
LINUX: export DATABASE_URL="postgresql://user:pass@localhost/my_company"
WINDOWS: $env:DATABASE_URL="postgresql://user:pass@localhost/my_company"
```
## 3. Load schema and your additions
```
% --> RECOMMENDATION 1 (continued): Update file version here too
LINUX:
psql -d $DATABASE_URL -f company_v3.02.sql
psql -d $DATABASE_URL -f team_setup.sql
WINDOWS:
psql -d $env:DATABASE_URL -f company_v3.02.sql
psql -d $env:DATABASE_URL -f team_setup.sql
```
## 4. Run the app
```
flask run
```