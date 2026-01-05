"""
Sistem Absensi Karyawan 2025
Main Application Entry Point - Production Ready

Features:
- Absensi via GPS, QR Code, Face Recognition
- Manajemen Cuti sesuai UU Ketenagakerjaan
- Laporan & Export Excel
- Multi-tenant & Multi-cabang

Author: AI Assistant
Version: 1.0.0
"""

import os
import logging
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import config and models
from config import config
from models import db, Company, Department, Employee, OfficeLocation, LeaveBalance

# Import routes
from routes import auth_bp, attendance_bp, leave_bp, reports_bp, employee_bp
from routes.auth import *
from routes.attendance import *
from routes.leave import *
from routes.reports import *
from routes.employee import *

# Initialize extensions
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')
    
    # Determine static folder path
    # In production, frontend is served from same directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, 'frontend')
    
    app = Flask(__name__, 
                static_folder=static_folder, 
                static_url_path='')
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # Configure CORS
    CORS(app, 
         origins=["*"],
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(employee_bp)
    
    # ============================================
    # JWT Error Handlers
    # ============================================
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'message': 'Token sudah kadaluarsa. Silakan login kembali.'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'message': 'Token tidak valid.'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'message': 'Token diperlukan untuk mengakses resource ini.'
        }), 401
    
    # ============================================
    # Error Handlers
    # ============================================
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            'success': False,
            'message': 'Request tidak valid'
        }), 400
    
    @app.errorhandler(404)
    def not_found(e):
        # Check if request is for API
        if request.path.startswith('/api'):
            return jsonify({
                'success': False,
                'message': 'Endpoint tidak ditemukan'
            }), 404
        # For frontend routes, serve index.html
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.errorhandler(500)
    def server_error(e):
        logger.error(f'Server error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan server. Silakan coba lagi.'
        }), 500
    
    # ============================================
    # Health Check & Info Endpoints
    # ============================================
    @app.route('/api/health')
    def health_check():
        """Health check endpoint for Render/monitoring"""
        try:
            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'database': db_status,
            'environment': config_name
        }), 200
    
    @app.route('/api/info')
    def app_info():
        """Application info"""
        return jsonify({
            'name': 'Sistem Absensi Karyawan',
            'version': '1.0.0',
            'year': 2025,
            'description': 'Sistem Absensi Modern untuk Perusahaan Indonesia',
            'features': [
                'Absensi GPS',
                'Absensi QR Code',
                'Absensi Face Recognition',
                'Manajemen Cuti (UU Ketenagakerjaan)',
                'Laporan & Export Excel',
                'Multi-cabang'
            ]
        }), 200
    
    # ============================================
    # Frontend Routes
    # ============================================
    @app.route('/')
    def serve_index():
        """Serve main frontend page"""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files or fallback to index.html for SPA"""
        static_file = os.path.join(app.static_folder, path)
        if os.path.exists(static_file):
            return send_from_directory(app.static_folder, path)
        # Fallback to index.html for client-side routing
        return send_from_directory(app.static_folder, 'index.html')
    
    # ============================================
    # Request Logging (Production)
    # ============================================
    @app.before_request
    def log_request():
        if config_name == 'production' and request.path.startswith('/api'):
            logger.info(f'{request.method} {request.path} - {request.remote_addr}')
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    return app


def init_database(app):
    """Initialize database with tables and sample data"""
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if already initialized
        if Company.query.first():
            logger.info("Database sudah diinisialisasi sebelumnya")
            return
        
        logger.info("Menginisialisasi database...")
        
        try:
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
            db.session.flush()  # Get company.id
            
            # Create departments
            departments = [
                Department(company_id=company.id, name="IT", code="IT"),
                Department(company_id=company.id, name="Human Resources", code="HR"),
                Department(company_id=company.id, name="Finance", code="FIN"),
                Department(company_id=company.id, name="Marketing", code="MKT"),
                Department(company_id=company.id, name="Operations", code="OPS")
            ]
            db.session.add_all(departments)
            db.session.flush()
            
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
            db.session.flush()
            
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
                db.session.flush()
                
                # Create leave balance
                lb = LeaveBalance(
                    employee_id=emp.id,
                    year=datetime.now().year,
                    annual_quota=12,
                    annual_remaining=12
                )
                db.session.add(lb)
            
            db.session.commit()
            
            logger.info("=" * 50)
            logger.info("Database berhasil diinisialisasi!")
            logger.info("=" * 50)
            logger.info("AKUN DEFAULT:")
            logger.info("Admin   : admin@contoh.co.id / admin123")
            logger.info("Employee: budi@contoh.co.id / password123")
            logger.info("Manager : ahmad@contoh.co.id / password123")
            logger.info("=" * 50)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing database: {str(e)}")
            raise


# Create application instance
app = create_app()


# Initialize database on first run
with app.app_context():
    try:
        init_database(app)
    except Exception as e:
        logger.warning(f"Database init skipped: {str(e)}")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
