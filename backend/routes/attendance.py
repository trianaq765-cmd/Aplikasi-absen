"""
Updated Attendance Routes with Face Recognition & Advanced Geolocation
"""

# Tambahkan import di bagian atas file attendance.py yang sudah ada
from utils.face_recognition import face_service
from utils.geolocation import geo_service

# Update fungsi clock_in dengan face recognition

@attendance_bp.route('/clock-in', methods=['POST'])
@jwt_required()
@active_employee_required()
def clock_in():
    """
    Absen Masuk dengan Face Recognition & GPS Validation
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
        
        method = data.get('method', 'manual')
        work_type = data.get('work_type', 'wfo')
        
        location_name = None
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        photo_data = data.get('photo')
        
        # ============================================
        # FACE RECOGNITION VALIDATION
        # ============================================
        if method == 'face' and photo_data:
            # Get stored face encoding
            stored_encoding = employee.face_encoding
            
            # Process face
            face_result = face_service.process_attendance_photo(
                photo_data, 
                stored_encoding
            )
            
            if not face_result['success']:
                return jsonify({
                    'success': False,
                    'message': face_result['message'],
                    'face_detected': face_result['face_detected']
                }), 400
            
            # If no stored encoding, save the new one
            if stored_encoding is None and face_result['new_encoding']:
                employee.face_encoding = face_result['new_encoding']
                db.session.commit()
        
        # ============================================
        # GPS VALIDATION
        # ============================================
        if work_type == 'wfo' and method in ['gps', 'face']:
            if not latitude or not longitude:
                return jsonify({
                    'success': False,
                    'message': 'Lokasi GPS diperlukan untuk absen WFO'
                }), 400
            
            # Validate location
            location_result = geo_service.validate_location(
                latitude, longitude, accuracy
            )
            
            if not location_result.is_valid:
                return jsonify({
                    'success': False,
                    'message': location_result.message,
                    'distance': location_result.distance_meters,
                    'nearest_office': location_result.nearest_office
                }), 400
            
            location_name = location_result.nearest_office
        
        # ============================================
        # WFH VALIDATION
        # ============================================
        if work_type == 'wfh':
            if not employee.is_wfh_allowed:
                return jsonify({
                    'success': False,
                    'message': 'Anda tidak memiliki izin untuk WFH. Hubungi HR.'
                }), 403
            
            # Optional: Validate WFH location
            if latitude and longitude:
                wfh_result = geo_service.validate_wfh_location(
                    latitude, longitude
                )
                if not wfh_result.is_valid:
                    return jsonify({
                        'success': False,
                        'message': wfh_result.message
                    }), 400
        
        # ============================================
        # CALCULATE LATE
        # ============================================
        office_start = employee.company.work_start_time if employee.company else "08:00"
        late_tolerance = employee.company.late_tolerance if employee.company else 15
        late_minutes = calculate_late_minutes(now, office_start, late_tolerance)
        
        status = 'late' if late_minutes > 0 else 'present'
        if work_type == 'wfh':
            status = 'wfh'
        
        # ============================================
        # CREATE/UPDATE ATTENDANCE
        # ============================================
        if existing:
            existing.clock_in = now
            existing.clock_in_method = method
            existing.clock_in_latitude = latitude
            existing.clock_in_longitude = longitude
            existing.clock_in_location_name = location_name
            existing.clock_in_photo = photo_data[:100] if photo_data else None  # Store reference only
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
                clock_in_location_name=location_name,
                clock_in_photo=photo_data[:100] if photo_data else None,
                late_minutes=late_minutes,
                status=status,
                work_type=work_type,
                notes=data.get('notes')
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        # Build response message
        message = f'Absen masuk berhasil pada {now.strftime("%H:%M")} WIB'
        if late_minutes > 0:
            message += f'. Anda terlambat {late_minutes} menit.'
        if method == 'face':
            message += ' (Verifikasi wajah berhasil)'
        
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


@attendance_bp.route('/register-face', methods=['POST'])
@jwt_required()
def register_face():
    """
    Register/Update face encoding untuk karyawan
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        data = request.get_json()
        
        photo_data = data.get('photo')
        if not photo_data:
            return jsonify({
                'success': False,
                'message': 'Foto wajah diperlukan'
            }), 400
        
        # Process face without verification (new registration)
        face_result = face_service.process_attendance_photo(photo_data, None)
        
        if not face_result['success']:
            return jsonify({
                'success': False,
                'message': face_result['message']
            }), 400
        
        # Save encoding
        employee.face_encoding = face_result['new_encoding']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Wajah berhasil didaftarkan'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@attendance_bp.route('/validate-location', methods=['POST'])
@jwt_required()
def validate_location():
    """
    Validate location before attendance (preview)
    """
    try:
        data = request.get_json()
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        
        if not latitude or not longitude:
            return jsonify({
                'success': False,
                'message': 'Koordinat diperlukan'
            }), 400
        
        # Get location summary
        summary = geo_service.get_location_summary(latitude, longitude)
        
        # Validate for WFO
        validation = geo_service.validate_location(latitude, longitude, accuracy)
        
        return jsonify({
            'success': True,
            'data': {
                'is_valid': validation.is_valid,
                'message': validation.message,
                'distance_meters': validation.distance_meters,
                'nearest_office': validation.nearest_office,
                'accuracy_warning': validation.accuracy_warning,
                'summary': summary
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
