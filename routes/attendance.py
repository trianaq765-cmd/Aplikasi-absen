"""
Attendance Routes
Clock In, Clock Out, History, QR Code
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from models import db, Employee, Attendance, OfficeLocation
from routes import attendance_bp
from utils.helpers import (
    get_wib_now, get_wib_today, calculate_late_minutes,
    calculate_early_leave, calculate_overtime, check_location_in_radius,
    generate_qr_code, get_attendance_status
)
from utils.decorators import active_employee_required
import pytz

WIB = pytz.timezone('Asia/Jakarta')


@attendance_bp.route('/clock-in', methods=['POST'])
@jwt_required()
@active_employee_required()
def clock_in():
    """
    Absen Masuk
    Mendukung: GPS, QR, Face Recognition, Manual
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        data = request.get_json()
        
        today = get_wib_today()
        now = get_wib_now()
        
        # Cek apakah sudah absen hari ini
        existing = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        if existing and existing.clock_in:
            return jsonify({
                'success': False,
                'message': 'Anda sudah melakukan absen masuk hari ini',
                'data': existing.to_dict()
            }), 400
        
        # Validasi metode absensi
        method = data.get('method', 'manual')  # gps, qr, face, manual
        work_type = data.get('work_type', 'wfo')  # wfo, wfh, wfa
        
        location_name = None
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # Validasi GPS jika WFO
        if work_type == 'wfo' and method == 'gps':
            if not latitude or not longitude:
                return jsonify({
                    'success': False,
                    'message': 'Lokasi GPS diperlukan untuk absen WFO'
                }), 400
            
            # Cek apakah dalam radius kantor
            office_locations = OfficeLocation.query.filter_by(is_active=True).all()
            is_valid_location = False
            
            for office in office_locations:
                is_valid, distance = check_location_in_radius(
                    latitude, longitude,
                    office.latitude, office.longitude,
                    office.radius_meters
                )
                if is_valid:
                    is_valid_location = True
                    location_name = f"{office.name} ({distance}m)"
                    break
            
            if not is_valid_location:
                return jsonify({
                    'success': False,
                    'message': 'Anda berada di luar radius kantor. Gunakan mode WFH jika diizinkan.',
                    'distance': distance
                }), 400
        
        # Validasi WFH
        if work_type == 'wfh' and not employee.is_wfh_allowed:
            return jsonify({
                'success': False,
                'message': 'Anda tidak memiliki izin untuk WFH. Hubungi HR.'
            }), 403
        
        # Hitung keterlambatan
        office_start = employee.company.work_start_time if employee.company else "08:00"
        late_tolerance = employee.company.late_tolerance if employee.company else 15
        late_minutes = calculate_late_minutes(now, office_start, late_tolerance)
        
        # Tentukan status
        status = 'late' if late_minutes > 0 else 'present'
        if work_type == 'wfh':
            status = 'wfh'
        
        # Buat atau update attendance
        if existing:
            existing.clock_in = now
            existing.clock_in_method = method
            existing.clock_in_latitude = latitude
            existing.clock_in_longitude = longitude
            existing.clock_in_location_name = location_name or data.get('location_name')
            existing.clock_in_photo = data.get('photo')
            existing.late_minutes = late_minutes
            existing.status = status
            existing.work_type = work_type
            existing.notes = data.get('notes')
            attendance = existing
        else:
            attendance = Attendance(
                employee_id=employee_id,
                date=today,
                clock_in=now,
                clock_in_method=method,
                clock_in_latitude=latitude,
                clock_in_longitude=longitude,
                clock_in_location_name=location_name or data.get('location_name'),
                clock_in_photo=data.get('photo'),
                late_minutes=late_minutes,
                status=status,
                work_type=work_type,
                notes=data.get('notes')
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        # Response message
        message = f'Absen masuk berhasil pada {now.strftime("%H:%M")} WIB'
        if late_minutes > 0:
            message += f'. Anda terlambat {late_minutes} menit.'
        
        return jsonify({
            'success': True,
            'message': message,
            'data': attendance.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@attendance_bp.route('/clock-out', methods=['POST'])
@jwt_required()
@active_employee_required()
def clock_out():
    """
    Absen Pulang
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        data = request.get_json()
        
        today = get_wib_today()
        now = get_wib_now()
        
        # Cek apakah sudah absen masuk
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        if not attendance or not attendance.clock_in:
            return jsonify({
                'success': False,
                'message': 'Anda belum melakukan absen masuk hari ini'
            }), 400
        
        if attendance.clock_out:
            return jsonify({
                'success': False,
                'message': 'Anda sudah melakukan absen pulang hari ini',
                'data': attendance.to_dict()
            }), 400
        
        # Validasi metode
        method = data.get('method', 'manual')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        location_name = None
        
        # Validasi GPS jika WFO
        if attendance.work_type == 'wfo' and method == 'gps':
            if latitude and longitude:
                office_locations = OfficeLocation.query.filter_by(is_active=True).all()
                
                for office in office_locations:
                    is_valid, distance = check_location_in_radius(
                        latitude, longitude,
                        office.latitude, office.longitude,
                        office.radius_meters + 50  # Toleransi lebih untuk pulang
                    )
                    if is_valid:
                        location_name = f"{office.name} ({distance}m)"
                        break
        
        # Hitung pulang awal dan lembur
        office_end = employee.company.work_end_time if employee.company else "17:00"
        early_leave = calculate_early_leave(now, office_end)
        overtime = calculate_overtime(now, office_end)
        
        # Update attendance
        attendance.clock_out = now
        attendance.clock_out_method = method
        attendance.clock_out_latitude = latitude
        attendance.clock_out_longitude = longitude
        attendance.clock_out_location_name = location_name or data.get('location_name')
        attendance.clock_out_photo = data.get('photo')
        attendance.early_leave_minutes = early_leave
        attendance.overtime_minutes = overtime
        
        # Update status jika pulang awal
        if early_leave > 30 and attendance.status == 'present':
            attendance.status = 'early_leave'
        
        if data.get('notes'):
            attendance.notes = (attendance.notes or '') + f" | Pulang: {data['notes']}"
        
        db.session.commit()
        
        # Response message
        message = f'Absen pulang berhasil pada {now.strftime("%H:%M")} WIB'
        if overtime > 0:
            hours = overtime // 60
            mins = overtime % 60
            message += f'. Lembur: {hours} jam {mins} menit.'
        elif early_leave > 0:
            message += f'. Pulang {early_leave} menit lebih awal.'
        
        return jsonify({
            'success': True,
            'message': message,
            'data': attendance.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@attendance_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_attendance():
    """
    Get absensi hari ini
    """
    try:
        employee_id = get_jwt_identity()
        today = get_wib_today()
        
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        return jsonify({
            'success': True,
            'data': attendance.to_dict() if attendance else None,
            'server_time': get_wib_now().strftime('%Y-%m-%d %H:%M:%S WIB')
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@attendance_bp.route('/history', methods=['GET'])
@jwt_required()
def get_attendance_history():
    """
    Get riwayat absensi
    Query params: start_date, end_date, page, per_page
    """
    try:
        employee_id = get_jwt_identity()
        
        # Parse query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Build query
        query = Attendance.query.filter_by(employee_id=employee_id)
        
        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # Order by date descending
        query = query.order_by(Attendance.date.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [att.to_dict() for att in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@attendance_bp.route('/qr-code', methods=['GET'])
@jwt_required()
def get_qr_code():
    """
    Generate QR Code untuk absensi
    QR berisi token unik yang valid untuk hari ini
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        today = get_wib_today()
        
        # Generate unique QR data
        qr_data = f"ABSEN|{employee_id}|{employee.nip or employee.nik}|{today.isoformat()}"
        
        # Generate QR image as base64
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
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@attendance_bp.route('/scan-qr', methods=['POST'])
@jwt_required()
def scan_qr_attendance():
    """
    Absen via scan QR Code
    Biasanya di-scan oleh admin/security
    """
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        
        if not qr_data:
            return jsonify({
                'success': False,
                'message': 'QR Code tidak valid'
            }), 400
        
        # Parse QR data
        parts = qr_data.split('|')
        if len(parts) != 4 or parts[0] != 'ABSEN':
            return jsonify({
                'success': False,
                'message': 'Format QR Code tidak valid'
            }), 400
        
        employee_id = int(parts[1])
        qr_date = parts[3]
        today = get_wib_today()
        
        # Validasi tanggal
        if qr_date != today.isoformat():
            return jsonify({
                'success': False,
                'message': 'QR Code sudah kadaluarsa. Gunakan QR hari ini.'
            }), 400
        
        # Proses absensi
        employee = Employee.query.get(employee_id)
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Karyawan tidak ditemukan'
            }), 404
        
        now = get_wib_now()
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        action = 'clock_in'
        
        if attendance and attendance.clock_in and not attendance.clock_out:
            # Clock out
            attendance.clock_out = now
            attendance.clock_out_method = 'qr'
            action = 'clock_out'
        elif attendance and attendance.clock_out:
            return jsonify({
                'success': False,
                'message': f'{employee.name} sudah absen lengkap hari ini'
            }), 400
        else:
            # Clock in
            late_minutes = calculate_late_minutes(now, "08:00", 15)
            
            if attendance:
                attendance.clock_in = now
                attendance.clock_in_method = 'qr'
                attendance.late_minutes = late_minutes
                attendance.status = 'late' if late_minutes > 0 else 'present'
            else:
                attendance = Attendance(
                    employee_id=employee_id,
                    date=today,
                    clock_in=now,
                    clock_in_method='qr',
                    late_minutes=late_minutes,
                    status='late' if late_minutes > 0 else 'present',
                    work_type='wfo'
                )
                db.session.add(attendance)
        
        db.session.commit()
        
        action_text = 'masuk' if action == 'clock_in' else 'pulang'
        
        return jsonify({
            'success': True,
            'message': f'Absen {action_text} berhasil untuk {employee.name}',
            'data': {
                'employee_name': employee.name,
                'action': action,
                'time': now.strftime('%H:%M WIB'),
                'attendance': attendance.to_dict()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@attendance_bp.route('/summary/monthly', methods=['GET'])
@jwt_required()
def get_monthly_summary():
    """
    Get ringkasan absensi bulanan
    """
    try:
        employee_id = get_jwt_identity()
        
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Get all attendance for the month
        from calendar import monthrange
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        attendances = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()
        
        # Calculate summary
        summary = {
            'month': month,
            'year': year,
            'total_days': len(attendances),
            'present': sum(1 for a in attendances if a.status == 'present'),
            'late': sum(1 for a in attendances if a.status == 'late'),
            'early_leave': sum(1 for a in attendances if a.status == 'early_leave'),
            'wfh': sum(1 for a in attendances if a.work_type == 'wfh'),
            'absent': 0,  # Perlu dihitung dari working days - present
            'total_late_minutes': sum(a.late_minutes or 0 for a in attendances),
            'total_overtime_minutes': sum(a.overtime_minutes or 0 for a in attendances)
        }
        
        return jsonify({
            'success': True,
            'data': summary
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
