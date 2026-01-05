"""
Auth Routes - FIXED with DB Error Handling
"""

from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from datetime import datetime
from sqlalchemy.exc import OperationalError
from models import db, Employee, LeaveBalance
from routes import auth_bp
import logging
import time

logger = logging.getLogger(__name__)


def safe_db_operation(operation, max_retries=2):
    """Execute database operation with retry on connection errors"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return operation()
        except OperationalError as e:
            last_error = e
            error_str = str(e).lower()
            if 'ssl' in error_str or 'connection' in error_str or 'eof' in error_str:
                logger.warning(f"DB connection error (attempt {attempt + 1}): {e}")
                try:
                    db.session.rollback()
                    db.session.remove()
                except:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
            raise
    raise last_error


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['nik', 'name', 'email', 'password']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} wajib diisi'}), 400
        
        # Check existing email
        def check_email():
            return Employee.query.filter_by(email=data['email']).first()
        
        existing = safe_db_operation(check_email)
        if existing:
            return jsonify({'success': False, 'message': 'Email sudah terdaftar'}), 400
        
        # Create employee
        employee = Employee(
            company_id=data.get('company_id', 1),
            department_id=data.get('department_id'),
            nik=data['nik'],
            nip=data.get('nip'),
            name=data['name'],
            email=data['email'],
            phone=data.get('phone'),
            position=data.get('position', 'Staff'),
            role=data.get('role', 'employee'),
            is_wfh_allowed=data.get('is_wfh_allowed', False)
        )
        employee.set_password(data['password'])
        
        def save_employee():
            db.session.add(employee)
            db.session.commit()
            return employee
        
        safe_db_operation(save_employee)
        
        # Create leave balance
        def create_leave_balance():
            lb = LeaveBalance(
                employee_id=employee.id,
                year=datetime.now().year,
                annual_quota=12,
                annual_remaining=12
            )
            db.session.add(lb)
            db.session.commit()
        
        safe_db_operation(create_leave_balance)
        
        return jsonify({
            'success': True,
            'message': 'Registrasi berhasil',
            'data': employee.to_dict()
        }), 201
        
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"DB error in register: {e}")
        return jsonify({
            'success': False,
            'message': 'Koneksi database bermasalah. Silakan coba lagi.'
        }), 503
    except Exception as e:
        db.session.rollback()
        logger.error(f"Register error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email dan password harus diisi'}), 400
        
        logger.info(f"Login attempt for: {email}")
        
        # Find employee with retry
        def find_employee():
            return Employee.query.filter_by(email=email).first()
        
        employee = safe_db_operation(find_employee)
        
        if not employee:
            logger.warning(f"Login failed - email not found: {email}")
            return jsonify({'success': False, 'message': 'Email atau password salah'}), 401
        
        if not employee.check_password(password):
            logger.warning(f"Login failed - wrong password for: {email}")
            return jsonify({'success': False, 'message': 'Email atau password salah'}), 401
        
        if not employee.is_active:
            return jsonify({'success': False, 'message': 'Akun tidak aktif. Hubungi HR.'}), 403
        
        # Create tokens
        access_token = create_access_token(identity=employee.id)
        refresh_token = create_refresh_token(identity=employee.id)
        
        logger.info(f"Login successful for: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Login berhasil',
            'data': {
                'employee': employee.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 200
        
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"DB error in login: {e}")
        return jsonify({
            'success': False,
            'message': 'Koneksi database bermasalah. Silakan coba lagi.',
            'retry': True
        }), 503
    except Exception as e:
        db.session.rollback()
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        employee_id = get_jwt_identity()
        
        def get_employee():
            return Employee.query.get(employee_id)
        
        employee = safe_db_operation(get_employee)
        
        if not employee:
            return jsonify({'success': False, 'message': 'Karyawan tidak ditemukan'}), 404
        
        # Get leave balance
        def get_balance():
            return LeaveBalance.query.filter_by(
                employee_id=employee_id,
                year=datetime.now().year
            ).first()
        
        balance = safe_db_operation(get_balance)
        
        data = employee.to_dict()
        data['leave_balance'] = {
            'annual_quota': balance.annual_quota if balance else 12,
            'annual_used': balance.annual_used if balance else 0,
            'annual_remaining': balance.annual_remaining if balance else 12
        }
        
        return jsonify({'success': True, 'data': data}), 200
        
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"DB error in profile: {e}")
        return jsonify({
            'success': False,
            'message': 'Koneksi database bermasalah.'
        }), 503
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        employee_id = get_jwt_identity()
        access_token = create_access_token(identity=employee_id)
        return jsonify({'success': True, 'access_token': access_token}), 200
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
