"""
Sistem Absensi Karyawan 2025
Main Application Entry Point

Fitur:
- Absensi via GPS, QR Code, Face Recognition
- Manajemen Cuti sesuai UU Ketenagakerjaan
- Laporan & Export Excel
- Multi-tenant & Multi-cabang

Author: AI Assistant
Version: 1.0.0
"""

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from datetime import datetime

from config import config
from models import db, Company, Department, Employee, OfficeLocation, LeaveBalance

# Import routes
from routes import auth_bp, attendance_bp, leave_bp, reports_bp, employee_bp
from routes.auth import *
from routes.attendance import *
from routes.leave import *
from routes.reports import *
from routes.employee import *


def create_app(config_name=None):
    """Application factory"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=["*"], supports_credentials=True)
    JWTManager(app)
    Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(employee_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'success': False,
            'message': 'Endpoint tidak ditemukan'
        }), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan server'
        }), 500
    
    # Health check
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }), 200
    
    # Serve frontend
    @app.route('/')
    def serve_frontend():
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')
    
    return app


def init_database(app):
    """Initialize database with sample data"""
    
    with app.app_context():
        db.create_all()
        
        # Check if already initialized
        if Company.query.first():
            print("Database sudah diinisialisasi")
            return
        
        print("Menginisialisasi database...")
        
        # Create default company
        company = Company(
            name="PT Contoh Indonesia",
            address="Jl. Sudirman No. 123, Jakarta Pusat",
            phone="021-1234567",
            email="info@contoh.co.id",
            npwp="01.234.567.8-012.000",
            work_start_time="08:00",
            work_end_time="17:00",
            late_tolerance=15
        )
        db.session.add(company)
        db.session.commit()
        
        # Create departments
        departments = [
            Department(company_id=company.id, name="IT", code="IT"),
            Department(company_id=company.id, name="Human Resources", code="HR"),
            Department(company_id=company.id, name="Finance", code="FIN"),
            Department(company_id=company.id, name="Marketing", code="MKT"),
            Department(company_id=company.id, name="Operations", code="OPS")
        ]
        db.session.add_all(departments)
        db.session.commit()
        
        # Create office locations
        locations = [
            OfficeLocation(
                company_id=company.id,
                name="Kantor Pusat Jakarta",
                address="Jl. Sudirman No. 123, Jakarta Pusat",
                latitude=-6.2088,
                longitude=106.8456,
                radius_meters=100
            ),
            OfficeLocation(
                company_id=company.id,
                name="Kantor Cabang Surabaya",
                address="Jl. Pemuda No. 45, Surabaya",
                latitude=-7.2575,
                longitude=112.7521,
                radius_meters=100
            )
        ]
        db.session.add_all(locations)
        db.session.commit()
        
        # Create admin user
        admin = Employee(
            company_id=company.id,
            department_id=departments[1].id,  # HR
            nik="1234567890123456",
            nip="ADM001",
            name="Administrator",
            email="admin@contoh.co.id",
            phone="081234567890",
            position="HR Manager",
            role="admin",
            employment_type="permanent",
            join_date=datetime(2020, 1, 1).date(),
            is_wfh_allowed=True
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        
        # Create leave balance for admin
        leave_balance = LeaveBalance(
            employee_id=admin.id,
            year=datetime.now().year,
            annual_quota=12,
            annual_remaining=12
        )
        db.session.add(leave_balance)
        
        # Create sample employees
        sample_employees = [
            {
                "nik": "3201234567890001",
                "nip": "EMP001",
                "name": "Budi Santoso",
                "email": "budi@contoh.co.id",
                "position": "Software Developer",
                "department_id": departments[0].id,
                "role": "employee"
            },
            {
                "nik": "3201234567890002",
                "nip": "EMP002",
                "name": "Siti Rahayu",
                "email": "siti@contoh.co.id",
                "position": "UI/UX Designer",
                "department_id": departments[0].id,
                "role": "employee"
            },
            {
                "nik": "3201234567890003",
                "nip": "MGR001",
                "name": "Ahmad Wijaya",
                "email": "ahmad@contoh.co.id",
                "position": "IT Manager",
                "department_id": departments[0].id,
                "role": "manager"
            }
        ]
        
        for emp_data in sample_employees:
            emp = Employee(
                company_id=company.id,
                department_id=emp_data["department_id"],
                nik=emp_data["nik"],
                nip=emp_data["nip"],
                name=emp_data["name"],
                email=emp_data["email"],
                position=emp_data["position"],
                role=emp_data["role"],
                employment_type="permanent",
                join_date=datetime(2023, 1, 1).date(),
                is_wfh_allowed=True
            )
            emp.set_password("password123")
            db.session.add(emp)
            db.session.commit()
            
            # Create leave balance
            lb = LeaveBalance(
                employee_id=emp.id,
                year=datetime.now().year,
                annual_quota=12,
                annual_remaining=12
            )
            db.session.add(lb)
        
        db.session.commit()
        print("Database berhasil diinisialisasi!")
        print("\n=== AKUN DEFAULT ===")
        print("Admin: admin@contoh.co.id / admin123")
        print("Employee: budi@contoh.co.id / password123")
        print("Manager: ahmad@contoh.co.id / password123")


# Create application instance
app = create_app()


if __name__ == '__main__':
    # Initialize database
    init_database(app)
    
    # Run app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
