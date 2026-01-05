"""
Authentication Routes
Login, Register, Profile Management
"""

from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from datetime import datetime
from models import db, Employee, Company, Department, LeaveBalance
from routes import auth_bp
from utils.helpers import get_wib_now


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register karyawan baru (biasanya oleh Admin/HR)
    """
    try:
        data = request.get_json()
        
        # Validasi input wajib
        required_fields = ['nik', 'name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Field {field} wajib diisi'
                }), 400
        
        # Cek email sudah terdaftar
        if Employee.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'message': 'Email sudah terdaftar'
            }), 400
        
        # Cek NIK sudah terdaftar
        if Employee.query.filter_by(nik=data['nik']).first():
            return jsonify({
                'success': False,
                'message': 'NIK sudah terdaftar'
            }), 400
        
        # Buat karyawan baru
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
            employment_type=data.get('employment_type', 'permanent'),
            join_date=datetime.strptime(data['join_date'], '%Y-%m-%d').date() if data.get('join_date') else datetime.now().date(),
            is_wfh_allowed=data.get('is_wfh_allowed', False)
        )
        employee.set_password(data['password'])
        
        db.session.add(employee)
        db.session.commit()
        
        # Buat saldo cuti untuk tahun ini
        current_year = datetime.now().year
        leave_balance = LeaveBalance(
            employee_id=employee.id,
            year=current_year,
            annual_quota=12,
            annual_remaining=12
        )
        db.session.add(leave_balance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Registrasi berhasil',
            'data': employee.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login karyawan
    """
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'success': False,
                'message': 'Email dan password wajib diisi'
            }), 400
        
        # Cari karyawan
        employee = Employee.query.filter_by(email=data['email']).first()
        
        if not employee or not employee.check_password(data['password']):
            return jsonify({
                'success': False,
                'message': 'Email atau password salah'
            }), 401
        
        if not employee.is_active:
            return jsonify({
                'success': False,
                'message': 'Akun tidak aktif. Hubungi HR.'
            }), 403
        
        # Buat token
        access_token = create_access_token(identity=employee.id)
        refresh_token = create_refresh_token(identity=employee.id)
        
        return jsonify({
            'success': True,
            'message': 'Login berhasil',
            'data': {
                'employee': employee.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token
    """
    try:
        employee_id = get_jwt_identity()
        access_token = create_access_token(identity=employee_id)
        
        return jsonify({
            'success': True,
            'access_token': access_token
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get profil karyawan yang sedang login
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Karyawan tidak ditemukan'
            }), 404
        
        # Ambil saldo cuti
        current_year = datetime.now().year
        leave_balance = LeaveBalance.query.filter_by(
            employee_id=employee_id,
            year=current_year
        ).first()
        
        profile_data = employee.to_dict()
        profile_data['leave_balance'] = {
            'annual_quota': leave_balance.annual_quota if leave_balance else 12,
            'annual_used': leave_balance.annual_used if leave_balance else 0,
            'annual_remaining': leave_balance.annual_remaining if leave_balance else 12
        }
        
        return jsonify({
            'success': True,
            'data': profile_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update profil karyawan
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Karyawan tidak ditemukan'
            }), 404
        
        data = request.get_json()
        
        # Field yang boleh diupdate sendiri
        allowed_fields = ['phone', 'photo_url']
        
        for field in allowed_fields:
            if field in data:
                setattr(employee, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profil berhasil diupdate',
            'data': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Ganti password
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        
        data = request.get_json()
        
        if not data.get('old_password') or not data.get('new_password'):
            return jsonify({
                'success': False,
                'message': 'Password lama dan baru wajib diisi'
            }), 400
        
        if not employee.check_password(data['old_password']):
            return jsonify({
                'success': False,
                'message': 'Password lama salah'
            }), 400
        
        if len(data['new_password']) < 6:
            return jsonify({
                'success': False,
                'message': 'Password baru minimal 6 karakter'
            }), 400
        
        employee.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password berhasil diubah'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
