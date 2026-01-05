from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import pytz

db = SQLAlchemy()
WIB = pytz.timezone('Asia/Jakarta')

def get_current_time():
    return datetime.now(WIB)

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    work_start_time = db.Column(db.String(5), default="08:00")
    work_end_time = db.Column(db.String(5), default="17:00")
    late_tolerance = db.Column(db.Integer, default=15)
    created_at = db.Column(db.DateTime, default=get_current_time)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10))

class OfficeLocation(db.Model):
    __tablename__ = 'office_locations'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    radius_meters = db.Column(db.Integer, default=100)
    is_active = db.Column(db.Boolean, default=True)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    nik = db.Column(db.String(20), unique=True, nullable=False)
    nip = db.Column(db.String(30), unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    position = db.Column(db.String(100))
    role = db.Column(db.String(20), default='employee')
    is_active = db.Column(db.Boolean, default=True)
    is_wfh_allowed = db.Column(db.Boolean, default=False)
    photo_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=get_current_time)
    
    company = db.relationship('Company', backref='employees')
    department = db.relationship('Department', backref='employees')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nik': self.nik,
            'nip': self.nip,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'position': self.position,
            'department': self.department.name if self.department else None,
            'role': self.role,
            'is_active': self.is_active,
            'is_wfh_allowed': self.is_wfh_allowed
        }

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    clock_in_method = db.Column(db.String(20))
    clock_out_method = db.Column(db.String(20))
    clock_in_latitude = db.Column(db.Float)
    clock_in_longitude = db.Column(db.Float)
    clock_in_location_name = db.Column(db.String(200))
    clock_out_latitude = db.Column(db.Float)
    clock_out_longitude = db.Column(db.Float)
    status = db.Column(db.String(20), default='present')
    late_minutes = db.Column(db.Integer, default=0)
    overtime_minutes = db.Column(db.Integer, default=0)
    work_type = db.Column(db.String(10), default='wfo')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_current_time)
    
    employee = db.relationship('Employee', backref='attendances')
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'date': self.date.isoformat() if self.date else None,
            'clock_in': self.clock_in.isoformat() if self.clock_in else None,
            'clock_out': self.clock_out.isoformat() if self.clock_out else None,
            'status': self.status,
            'late_minutes': self.late_minutes,
            'work_type': self.work_type,
            'clock_in_location': self.clock_in_location_name
        }

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(30), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_current_time)
    
    employee = db.relationship('Employee', foreign_keys=[employee_id], backref='leave_requests')
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'leave_type': self.leave_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'total_days': self.total_days,
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    annual_quota = db.Column(db.Integer, default=12)
    annual_used = db.Column(db.Integer, default=0)
    annual_remaining = db.Column(db.Integer, default=12)
    sick_used = db.Column(db.Integer, default=0)
