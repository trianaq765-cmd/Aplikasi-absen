from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from models import db, Employee, LeaveRequest, LeaveBalance
from routes import leave_bp
from utils.helpers import get_wib_now, get_wib_today

LEAVE_TYPES = {
    'annual': {'name': 'Cuti Tahunan', 'max_days': 12},
    'sick': {'name': 'Sakit', 'max_days': 14},
    'marriage': {'name': 'Cuti Menikah', 'max_days': 3},
    'maternity': {'name': 'Cuti Melahirkan', 'max_days': 90},
    'paternity': {'name': 'Cuti Ayah', 'max_days': 2},
    'bereavement': {'name': 'Duka Cita', 'max_days': 2},
    'unpaid': {'name': 'Tanpa Gaji', 'max_days': 30},
}

@leave_bp.route('/types', methods=['GET'])
@jwt_required()
def get_types():
    return jsonify({'success': True, 'data': LEAVE_TYPES}), 200

@leave_bp.route('/balance', methods=['GET'])
@jwt_required()
def get_balance():
    try:
        employee_id = get_jwt_identity()
        year = request.args.get('year', datetime.now().year, type=int)
        
        balance = LeaveBalance.query.filter_by(employee_id=employee_id, year=year).first()
        if not balance:
            balance = LeaveBalance(employee_id=employee_id, year=year)
            db.session.add(balance)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'year': balance.year,
                'annual_quota': balance.annual_quota,
                'annual_used': balance.annual_used,
                'annual_remaining': balance.annual_remaining
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@leave_bp.route('/request', methods=['POST'])
@jwt_required()
def create_request():
    try:
        employee_id = get_jwt_identity()
        data = request.get_json()
        
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        total_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                total_days += 1
            current += timedelta(days=1)
        
        leave_request = LeaveRequest(
            employee_id=employee_id,
            leave_type=data['leave_type'],
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=data['reason'],
            status='pending'
        )
        db.session.add(leave_request)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Pengajuan berhasil', 'data': leave_request.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@leave_bp.route('/my-requests', methods=['GET'])
@jwt_required()
def get_my_requests():
    try:
        employee_id = get_jwt_identity()
        requests = LeaveRequest.query.filter_by(employee_id=employee_id).order_by(LeaveRequest.created_at.desc()).all()
        return jsonify({'success': True, 'data': [r.to_dict() for r in requests]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@leave_bp.route('/cancel/<int:leave_id>', methods=['POST'])
@jwt_required()
def cancel_request(leave_id):
    try:
        employee_id = get_jwt_identity()
        leave = LeaveRequest.query.filter_by(id=leave_id, employee_id=employee_id).first()
        
        if not leave:
            return jsonify({'success': False, 'message': 'Tidak ditemukan'}), 404
        
        if leave.status != 'pending':
            return jsonify({'success': False, 'message': 'Hanya pending yang bisa dibatalkan'}), 400
        
        leave.status = 'cancelled'
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Dibatalkan'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
