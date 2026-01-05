-- Initial database setup script
-- This runs when PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Set timezone to WIB (Indonesia)
SET timezone = 'Asia/Jakarta';

-- Create indexes for performance (will be created after tables exist)
-- These are just comments for reference
-- CREATE INDEX idx_attendance_employee_date ON attendances(employee_id, date);
-- CREATE INDEX idx_attendance_date ON attendances(date);
-- CREATE INDEX idx_leave_request_status ON leave_requests(status);
-- CREATE INDEX idx_employee_email ON employees(email);
-- CREATE INDEX idx_employee_active ON employees(is_active);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE absensi_karyawan TO postgres;

-- Log
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully at %', NOW();
END $$;
