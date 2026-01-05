from flask import request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import datetime
from models import db, Employee, LeaveBalance
from routes import auth_bp

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if Employee.query.filter_by(email=data.get('email')).first():
            return jsonify({'success': False, 'message': 'Email sudah terdaftar'}), 400
        
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
        db.session.add(employee)
        db.session.commit()
        
        lb = LeaveBalance(employee_id=employee.id, year=datetime.now().year)
        db.session.add(lb)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registrasi berhasil', 'data': employee.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        employee = Employee.query.filter_by(email=data.get('email')).first()
        
        if not employee or not employee.check_password(data.get('password')):
            return jsonify({'success': False, 'message': 'Email atau password salah'}), 401
        
        if not employee.is_active:
            return jsonify({'success': False, 'message': 'Akun tidak aktif'}), 403
        
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
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({'success': False, 'message': 'Tidak ditemukan'}), 404
        
        balance = LeaveBalance.query.filter_by(employee_id=employee_id, year=datetime.now().year).first()
        
        data = employee.to_dict()
        data['leave_balance'] = {
            'annual_quota': balance.annual_quota if balance else 12,
            'annual_used': balance.annual_used if balance else 0,
            'annual_remaining': balance.annual_remaining if balance else 12
        }
        
        return jsonify({'success': True, 'data': data}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    employee_id = get_jwt_identity()
    access_token = create_access_token(identity=employee_id)
    return jsonify({'success': True, 'access_token': access_token}), 200
