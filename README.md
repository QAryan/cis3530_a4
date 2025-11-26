# cis3530_a4
Assignment 4 for CIS*3530: Databases. The goal of this project is to build a small, data-driven web application using Flask and raw SQL.
# Indexes
## idx_workson_pno ON Works_On (Pno)
This index on the project number in the works on table helps speed up the aggregation of the list of employees and hours on each of the project details pages.
## idx_employee_ssn ON Employee (Ssn)
this index on the employee ssn in the Employee table helps to speed up the insertion of new employees and for checking if a new employees manager ssn exists. this index allows for quickly checking if a ssn exist in the table instead of having to check every record everytime a new employee is trying to be inserted.
# Setup

## 1. Setup environment
```
python3 -m venv .venv
MACOS/LINUX: source .venv/bin/activate
WINDOWS: .venv\Scripts\activate 
pip install -r requirements.txt
```

## 2. Setup database and password
```
createdb my_company
LINUX: export DATABASE_URL="postgresql://user:pass@localhost/my_company"
WINDOWS: $env:DATABASE_URL="postgresql://user:pass@localhost/my_company"

LINUX: export PSQL_PASS="<your_password>"
WINDOWS: $env:PSQL_PASS="<your_password>"
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