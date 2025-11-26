CREATE TABLE IF NOT EXISTS app_user (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workson_pno ON Works_On (Pno);
CREATE INDEX IF NOT EXISTS idx_employee_ssn ON Employee (Ssn);