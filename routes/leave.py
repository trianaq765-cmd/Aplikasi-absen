"""
Leave Management Routes
Pengajuan Cuti, Izin, Approval
Sesuai UU Ketenagakerjaan Indonesia
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from models import db, Employee, LeaveRequest, LeaveBalance, Attendance
from routes import leave_bp
from utils.helpers import get_wib_now, get_wib_today
from utils.decorators import manager_required, hr_required


# Jenis cuti sesuai UU Ketenagakerjaan Indonesia
LEAVE_TYPES = {
    'annual': {
        'name': 'Cuti Tahunan',
        'max_days': 12,
        'requires_approval': True,
        'deduct_balance': True
    },
    'sick': {
        'name': 'Sakit',
        'max_days': 14,  # Lebih dari ini perlu surat dokter
        'requires_approval': False,
        'deduct_balance': False
    },
    'maternity': {
        'name': 'Cuti Melahirkan',
        'max_days': 90,  # 3 bulan
        'requires_approval': True,
        'deduct_balance': False
    },
    'paternity': {
        'name': 'Cuti Ayah',
        'max_days': 2,
        'requires_approval': True,
        'deduct_balance': False
    },
    'marriage': {
        'name': 'Cuti Menikah',
        'max_days': 3,
        'requires_approval': True,
        'deduct_balance': False
    },
    'marriage_child': {
        'name': 'Cuti Menikahkan Anak',
        'max_days': 2,
        'requires_approval': True,
        'deduct_balance': False
    },
    'circumcision': {
        'name': 'Cuti Khitanan Anak',
        'max_days': 2,
        'requires_approval': True,
        'deduct_balance': False
    },
    'baptism': {
        'name': 'Cuti Pembaptisan Anak',
        'max_days': 2,
        'requires_approval': True,
        'deduct_balance': False
    },
    'bereavement_spouse': {
        'name': 'Duka Suami/Istri/Anak/Ortu',
        'max_days': 2,
        'requires_approval': False,
        'deduct_balance': False
    },
    'bereavement_family': {
        'name': 'Duka Anggota Keluarga',
        'max_days': 1,
        'requires_approval': False,
        'deduct_balance': False
    },
    'hajj': {
        'name': 'Ibadah Haji',
        'max_days': 50,  # Sekali selama bekerja
        'requires_approval': True,
        'deduct_balance': False
    },
    'unpaid': {
        'name': 'Cuti Tanpa Gaji',
        'max_days': 30,
        'requires_approval': True,
        'deduct_balance': False
    },
    'other': {
        'name': 'Izin Lainnya',
        'max_days': 1,
        'requires_approval': True,
        'deduct_balance': True
    }
}


@leave_bp.route('/types', methods=['GET'])
@jwt_required()
def get_leave_types():
    """
    Get daftar jenis cuti yang tersedia
    """
    return jsonify({
        'success': True,
        'data': LEAVE_TYPES
    }), 200


@leave_bp.route('/balance', methods=['GET'])
@jwt_required()
def get_leave_balance():
    """
    Get saldo cuti karyawan
    """
    try:
        employee_id = get_jwt_identity()
        year = request.args.get('year', datetime.now().year, type=int)
        
        balance = LeaveBalance.query.filter_by(
            employee_id=employee_id,
            year=year
        ).first()
        
        if not balance:
            # Buat saldo baru jika belum ada
            balance = LeaveBalance(
                employee_id=employee_id,
                year=year,
                annual_quota=12,
                annual_remaining=12
            )
            db.session.add(balance)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'year': balance.year,
                'annual_quota': balance.annual_quota,
                'annual_used': balance.annual_used,
                'annual_remaining': balance.annual_remaining,
                'sick_used': balance.sick_used
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@leave_bp.route('/request', methods=['POST'])
@jwt_required()
def create_leave_request():
    """
    Buat pengajuan cuti/izin baru
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        data = request.get_json()
        
        # Validasi input
        required = ['leave_type', 'start_date', 'end_date', 'reason']
        for field in required:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Field {field} wajib diisi'
                }), 400
        
        leave_type = data['leave_type']
        if leave_type not in LEAVE_TYPES:
            return jsonify({
                'success': False,
                'message': 'Jenis cuti tidak valid'
            }), 400
        
        # Parse tanggal
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        if start_date > end_date:
            return jsonify({
                'success': False,
                'message': 'Tanggal mulai harus sebelum tanggal selesai'
            }), 400
        
        if start_date < get_wib_today():
            return jsonify({
                'success': False,
                'message': 'Tidak bisa mengajukan cuti untuk tanggal yang sudah lewat'
            }), 400
        
        # Hitung total hari (exclude weekend)
        total_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Senin-Jumat
                total_days += 1
            current += timedelta(days=1)
        
        # Validasi max days
        leave_info = LEAVE_TYPES[leave_type]
        if total_days > leave_info['max_days']:
            return jsonify({
                'success': False,
                'message': f"Maksimal {leave_info['name']} adalah {leave_info['max_days']} hari"
            }), 400
        
        # Cek saldo cuti tahunan
        if leave_info['deduct_balance']:
            year = start_date.year
            balance = LeaveBalance.query.filter_by(
                employee_id=employee_id,
                year=year
            ).first()
            
            if not balance or balance.annual_remaining < total_days:
                remaining = balance.annual_remaining if balance else 0
                return jsonify({
                    'success': False,
                    'message': f'Saldo cuti tidak cukup. Tersisa: {remaining} hari'
                }), 400
        
        # Cek overlap dengan cuti yang sudah ada
        existing = LeaveRequest.query.filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(['pending', 'approved']),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'Tanggal bentrok dengan pengajuan cuti yang sudah ada'
            }), 400
        
        # Buat pengajuan
        leave_request = LeaveRequest(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=data['reason'],
            attachment=data.get('attachment'),
            status='pending' if leave_info['requires_approval'] else 'approved'
        )
        
        db.session.add(leave_request)
        
        # Auto-approve untuk cuti sakit/duka
        if not leave_info['requires_approval']:
            leave_request.approved_at = get_wib_now()
            
            # Update attendance untuk tanggal cuti
            current = start_date
            while current <= end_date:
                if current.weekday() < 5:
                    attendance = Attendance.query.filter_by(
                        employee_id=employee_id,
                        date=current
                    ).first()
                    
                    if not attendance:
                        attendance = Attendance(
                            employee_id=employee_id,
                            date=current,
                            status='sick' if leave_type == 'sick' else 'leave'
                        )
                        db.session.add(attendance)
                    else:
                        attendance.status = 'sick' if leave_type == 'sick' else 'leave'
                
                current += timedelta(days=1)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pengajuan cuti berhasil dibuat',
            'data': leave_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@leave_bp.route('/my-requests', methods=['GET'])
@jwt_required()
def get_my_leave_requests():
    """
    Get daftar pengajuan cuti saya
    """
    try:
        employee_id = get_jwt_identity()
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        query = LeaveRequest.query.filter_by(employee_id=employee_id)
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.order_by(LeaveRequest.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [req.to_dict() for req in pagination.items],
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


@leave_bp.route('/cancel/<int:leave_id>', methods=['POST'])
@jwt_required()
def cancel_leave_request(leave_id):
    """
    Batalkan pengajuan cuti
    """
    try:
        employee_id = get_jwt_identity()
        
        leave_request = LeaveRequest.query.filter_by(
            id=leave_id,
            employee_id=employee_id
        ).first()
        
        if not leave_request:
            return jsonify({
                'success': False,
                'message': 'Pengajuan cuti tidak ditemukan'
            }), 404
        
        if leave_request.status not in ['pending']:
            return jsonify({
                'success': False,
                'message': 'Hanya pengajuan dengan status pending yang bisa dibatalkan'
            }), 400
        
        if leave_request.start_date <= get_wib_today():
            return jsonify({
                'success': False,
                'message': 'Tidak bisa membatalkan cuti yang sudah dimulai'
            }), 400
        
        leave_request.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pengajuan cuti berhasil dibatalkan'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@leave_bp.route('/pending', methods=['GET'])
@jwt_required()
@manager_required()
def get_pending_requests():
    """
    Get daftar pengajuan cuti yang menunggu approval
    Untuk Manager/HR
    """
    try:
        approver_id = get_jwt_identity()
        approver = Employee.query.get(approver_id)
        
        query = LeaveRequest.query.filter_by(status='pending')
        
        # Jika manager, hanya lihat tim sendiri
        if approver.role == 'manager':
            query = query.join(Employee).filter(
                Employee.department_id == approver.department_id
            )
        
        query = query.order_by(LeaveRequest.created_at.asc())
        requests = query.all()
        
        return jsonify({
            'success': True,
            'data': [req.to_dict() for req in requests]
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@leave_bp.route('/approve/<int:leave_id>', methods=['POST'])
@jwt_required()
@manager_required()
def approve_leave_request(leave_id):
    """
    Approve pengajuan cuti
    """
    try:
        approver_id = get_jwt_identity()
        
        leave_request = LeaveRequest.query.get(leave_id)
        
        if not leave_request:
            return jsonify({
                'success': False,
                'message': 'Pengajuan cuti tidak ditemukan'
            }), 404
        
        if leave_request.status != 'pending':
            return jsonify({
                'success': False,
                'message': 'Pengajuan ini sudah diproses'
            }), 400
        
        # Update status
        leave_request.status = 'approved'
        leave_request.approved_by = approver_id
        leave_request.approved_at = get_wib_now()
        
        # Kurangi saldo cuti jika perlu
        leave_info = LEAVE_TYPES.get(leave_request.leave_type, {})
        if leave_info.get('deduct_balance'):
            balance = LeaveBalance.query.filter_by(
                employee_id=leave_request.employee_id,
                year=leave_request.start_date.year
            ).first()
            
            if balance:
                balance.annual_used += leave_request.total_days
                balance.annual_remaining -= leave_request.total_days
        
        # Buat attendance untuk tanggal cuti
        current = leave_request.start_date
        while current <= leave_request.end_date:
            if current.weekday() < 5:
                attendance = Attendance.query.filter_by(
                    employee_id=leave_request.employee_id,
                    date=current
                ).first()
                
                if not attendance:
                    attendance = Attendance(
                        employee_id=leave_request.employee_id,
                        date=current,
                        status='leave'
                    )
                    db.session.add(attendance)
                else:
                    attendance.status = 'leave'
            
            current += timedelta(days=1)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pengajuan cuti disetujui'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@leave_bp.route('/reject/<int:leave_id>', methods=['POST'])
@jwt_required()
@manager_required()
def reject_leave_request(leave_id):
    """
    Tolak pengajuan cuti
    """
    try:
        approver_id = get_jwt_identity()
        data = request.get_json()
        
        leave_request = LeaveRequest.query.get(leave_id)
        
        if not leave_request:
            return jsonify({
                'success': False,
                'message': 'Pengajuan cuti tidak ditemukan'
            }), 404
        
        if leave_request.status != 'pending':
            return jsonify({
                'success': False,
                'message': 'Pengajuan ini sudah diproses'
            }), 400
        
        leave_request.status = 'rejected'
        leave_request.approved_by = approver_id
        leave_request.approved_at = get_wib_now()
        leave_request.rejection_reason = data.get('reason', 'Tidak disetujui')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Pengajuan cuti ditolak'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
