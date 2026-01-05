from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from models import db, Employee, Attendance, OfficeLocation
from routes import attendance_bp
from utils.helpers import get_wib_now, get_wib_today, calculate_late_minutes, generate_qr_code
import pytz

WIB = pytz.timezone('Asia/Jakarta')

@attendance_bp.route('/clock-in', methods=['POST'])
@jwt_required()
def clock_in():
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        data = request.get_json()
        
        today = get_wib_today()
        now = get_wib_now()
        
        existing = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
        if existing and existing.clock_in:
            return jsonify({'success': False, 'message': 'Sudah absen masuk hari ini'}), 400
        
        method = data.get('method', 'manual')
        work_type = data.get('work_type', 'wfo')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if work_type == 'wfh' and not employee.is_wfh_allowed:
            return jsonify({'success': False, 'message': 'Tidak diizinkan WFH'}), 403
        
        late_minutes = calculate_late_minutes(now, "08:00", 15)
        status = 'late' if late_minutes > 0 else 'present'
        
        if existing:
            existing.clock_in = now
            existing.clock_in_method = method
            existing.clock_in_latitude = latitude
            existing.clock_in_longitude = longitude
            existing.late_minutes = late_minutes
            existing.status = status
            existing.work_type = work_type
            attendance = existing
        else:
            attendance = Attendance(
                employee_id=employee_id,
                date=today,
                clock_in=now,
                clock_in_method=method,
                clock_in_latitude=latitude,
                clock_in_longitude=longitude,
                late_minutes=late_minutes,
                status=status,
                work_type=work_type
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        msg = f'Absen masuk berhasil {now.strftime("%H:%M")} WIB'
        if late_minutes > 0:
            msg += f'. Terlambat {late_minutes} menit.'
        
        return jsonify({'success': True, 'message': msg, 'data': attendance.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance_bp.route('/clock-out', methods=['POST'])
@jwt_required()
def clock_out():
    try:
        employee_id = get_jwt_identity()
        data = request.get_json()
        today = get_wib_today()
        now = get_wib_now()
        
        attendance = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
        
        if not attendance or not attendance.clock_in:
            return jsonify({'success': False, 'message': 'Belum absen masuk'}), 400
        
        if attendance.clock_out:
            return jsonify({'success': False, 'message': 'Sudah absen pulang'}), 400
        
        attendance.clock_out = now
        attendance.clock_out_method = data.get('method', 'manual')
        attendance.clock_out_latitude = data.get('latitude')
        attendance.clock_out_longitude = data.get('longitude')
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Absen pulang berhasil {now.strftime("%H:%M")} WIB', 'data': attendance.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today():
    try:
        employee_id = get_jwt_identity()
        today = get_wib_today()
        attendance = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
        return jsonify({
            'success': True,
            'data': attendance.to_dict() if attendance else None,
            'server_time': get_wib_now().strftime('%Y-%m-%d %H:%M:%S WIB')
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    try:
        employee_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        query = Attendance.query.filter_by(employee_id=employee_id).order_by(Attendance.date.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [a.to_dict() for a in pagination.items],
            'pagination': {'page': page, 'per_page': per_page, 'total': pagination.total}
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance_bp.route('/qr-code', methods=['GET'])
@jwt_required()
def get_qr():
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        today = get_wib_today()
        
        qr_data = f"ABSEN|{employee_id}|{employee.nip}|{today.isoformat()}"
        qr_base64 = generate_qr_code(qr_data)
        
        return jsonify({
            'success': True,
            'data': {
                'qr_image': f'data:image/png;base64,{qr_base64}',
                'valid_date': today.isoformat(),
                'employee_name': employee.name
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
