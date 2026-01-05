"""
Database Models untuk Sistem Absensi Karyawan
Disesuaikan dengan kebutuhan perusahaan Indonesia 2025
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import pytz

db = SQLAlchemy()

# Timezone Indonesia
WIB = pytz.timezone('Asia/Jakarta')


def get_current_time():
    """Get current time in WIB"""
    return datetime.now(WIB)


class Company(db.Model):
    """Model Perusahaan - untuk multi-tenant"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    npwp = db.Column(db.String(30))  # NPWP Perusahaan
    
    # Settings
    work_start_time = db.Column(db.String(5), default="08:00")
    work_end_time = db.Column(db.String(5), default="17:00")
    late_tolerance = db.Column(db.Integer, default=15)  # menit
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, onupdate=get_current_time)
    
    # Relationships
    employees = db.relationship('Employee', backref='company', lazy='dynamic')
    departments = db.relationship('Department', backref='company', lazy='dynamic')
    office_locations = db.relationship('OfficeLocation', backref='company', lazy='dynamic')


class Department(db.Model):
    """Model Departemen"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10))
    
    # Relationships
    employees = db.relationship('Employee', backref='department', lazy='dynamic')


class OfficeLocation(db.Model):
    """Model Lokasi Kantor untuk Geolocation"""
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
    """Model Karyawan"""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    
    # Data Pribadi
    nik = db.Column(db.String(20), unique=True, nullable=False)  # NIK KTP
    nip = db.Column(db.String(30), unique=True)  # Nomor Induk Pegawai
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Data Pekerjaan
    position = db.Column(db.String(100))  # Jabatan
    role = db.Column(db.String(20), default='employee')  # admin, hr, manager, employee
    employment_type = db.Column(db.String(20), default='permanent')  # permanent, contract, intern
    join_date = db.Column(db.Date)
    
    # Face Recognition
    face_encoding = db.Column(db.LargeBinary)  # Encoded face data
    photo_url = db.Column(db.String(255))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_wfh_allowed = db.Column(db.Boolean, default=False)  # Boleh WFH
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, onupdate=get_current_time)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='employee', lazy='dynamic')
    leave_requests = db.relationship('LeaveRequest', backref='employee', lazy='dynamic')
    
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
            'is_wfh_allowed': self.is_wfh_allowed,
            'photo_url': self.photo_url
        }


class Attendance(db.Model):
    """Model Absensi"""
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Tanggal & Waktu
    date = db.Column(db.Date, nullable=False, default=date.today)
    clock_in = db.Column(db.DateTime)
    clock_out = db.Column(db.DateTime)
    
    # Metode Absensi
    clock_in_method = db.Column(db.String(20))  # face, qr, gps, manual
    clock_out_method = db.Column(db.String(20))
    
    # Lokasi (GPS)
    clock_in_latitude = db.Column(db.Float)
    clock_in_longitude = db.Column(db.Float)
    clock_in_location_name = db.Column(db.String(200))
    clock_out_latitude = db.Column(db.Float)
    clock_out_longitude = db.Column(db.Float)
    clock_out_location_name = db.Column(db.String(200))
    
    # Foto Selfie
    clock_in_photo = db.Column(db.String(255))
    clock_out_photo = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.String(20), default='present')
    # present, late, early_leave, absent, sick, leave, wfh
    
    late_minutes = db.Column(db.Integer, default=0)
    early_leave_minutes = db.Column(db.Integer, default=0)
    overtime_minutes = db.Column(db.Integer, default=0)
    
    # Work Type
    work_type = db.Column(db.String(10), default='wfo')  # wfo, wfh, wfa
    
    # Notes
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, onupdate=get_current_time)
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'date': self.date.isoformat() if self.date else None,
            'clock_in': self.clock_in.isoformat() if self.clock_in else None,
            'clock_out': self.clock_out.isoformat() if self.clock_out else None,
            'clock_in_method': self.clock_in_method,
            'clock_out_method': self.clock_out_method,
            'status': self.status,
            'late_minutes': self.late_minutes,
            'work_type': self.work_type,
            'clock_in_location': self.clock_in_location_name,
            'notes': self.notes
        }


class LeaveRequest(db.Model):
    """Model Pengajuan Cuti/Izin"""
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Jenis Cuti (sesuai UU Ketenagakerjaan Indonesia)
    leave_type = db.Column(db.String(30), nullable=False)
    # annual (cuti tahunan), sick (sakit), maternity (melahirkan), 
    # paternity (ayah), marriage (nikah), bereavement (duka),
    # hajj (haji), unpaid (tanpa gaji), other (lainnya)
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    
    reason = db.Column(db.Text, nullable=False)
    attachment = db.Column(db.String(255))  # Surat dokter, dll
    
    # Approval
    status = db.Column(db.String(20), default='pending')
    # pending, approved, rejected, cancelled
    
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, onupdate=get_current_time)
    
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
    """Model Saldo Cuti Karyawan"""
    __tablename__ = 'leave_balances'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # Tahun
    
    # Jatah Cuti (default sesuai UU: 12 hari/tahun setelah 1 tahun kerja)
    annual_quota = db.Column(db.Integer, default=12)
    annual_used = db.Column(db.Integer, default=0)
    annual_remaining = db.Column(db.Integer, default=12)
    
    # Cuti Sakit (umumnya tidak terbatas dengan surat dokter)
    sick_used = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, onupdate=get_current_time)


class AttendanceSummary(db.Model):
    """Model Ringkasan Absensi Bulanan (untuk laporan cepat)"""
    __tablename__ = 'attendance_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    
    # Statistik
    total_work_days = db.Column(db.Integer, default=0)
    present_days = db.Column(db.Integer, default=0)
    late_days = db.Column(db.Integer, default=0)
    absent_days = db.Column(db.Integer, default=0)
    leave_days = db.Column(db.Integer, default=0)
    sick_days = db.Column(db.Integer, default=0)
    wfh_days = db.Column(db.Integer, default=0)
    
    total_late_minutes = db.Column(db.Integer, default=0)
    total_overtime_minutes = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=get_current_time)
    updated_at = db.Column(db.DateTime, onupdate=get_current_time)
