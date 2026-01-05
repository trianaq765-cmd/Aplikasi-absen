"""
Helper Functions untuk Sistem Absensi
"""

from datetime import datetime, date, time
from geopy.distance import geodesic
import pytz
import qrcode
import io
import base64

WIB = pytz.timezone('Asia/Jakarta')


def get_wib_now():
    """Get current datetime in WIB"""
    return datetime.now(WIB)


def get_wib_today():
    """Get today's date in WIB"""
    return datetime.now(WIB).date()


def parse_time(time_str):
    """Parse time string (HH:MM) to time object"""
    return datetime.strptime(time_str, "%H:%M").time()


def calculate_late_minutes(clock_in_time, office_start="08:00", tolerance=15):
    """
    Hitung keterlambatan dalam menit
    
    Args:
        clock_in_time: datetime object
        office_start: string "HH:MM"
        tolerance: toleransi dalam menit
    
    Returns:
        int: menit keterlambatan (0 jika tidak telat)
    """
    start = parse_time(office_start)
    clock_in = clock_in_time.time()
    
    # Konversi ke menit dari midnight
    start_minutes = start.hour * 60 + start.minute + tolerance
    clock_in_minutes = clock_in.hour * 60 + clock_in.minute
    
    late = clock_in_minutes - start_minutes
    return max(0, late)


def calculate_early_leave(clock_out_time, office_end="17:00", tolerance=0):
    """
    Hitung pulang lebih awal dalam menit
    """
    end = parse_time(office_end)
    clock_out = clock_out_time.time()
    
    end_minutes = end.hour * 60 + end.minute - tolerance
    clock_out_minutes = clock_out.hour * 60 + clock_out.minute
    
    early = end_minutes - clock_out_minutes
    return max(0, early)


def calculate_overtime(clock_out_time, office_end="17:00", min_overtime=30):
    """
    Hitung lembur dalam menit (minimal 30 menit baru dihitung)
    """
    end = parse_time(office_end)
    clock_out = clock_out_time.time()
    
    end_minutes = end.hour * 60 + end.minute
    clock_out_minutes = clock_out.hour * 60 + clock_out.minute
    
    overtime = clock_out_minutes - end_minutes
    
    if overtime >= min_overtime:
        return overtime
    return 0


def check_location_in_radius(user_lat, user_lon, office_lat, office_lon, radius_meters):
    """
    Cek apakah lokasi user dalam radius kantor
    
    Returns:
        tuple: (is_valid, distance_meters)
    """
    user_location = (user_lat, user_lon)
    office_location = (office_lat, office_lon)
    
    distance = geodesic(user_location, office_location).meters
    is_valid = distance <= radius_meters
    
    return is_valid, round(distance, 2)


def generate_qr_code(data):
    """
    Generate QR Code sebagai base64 string
    
    Args:
        data: string to encode
    
    Returns:
        str: base64 encoded PNG image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()


def get_attendance_status(clock_in_time, clock_out_time, 
                          office_start="08:00", office_end="17:00",
                          late_tolerance=15):
    """
    Determine attendance status
    
    Returns:
        str: 'present', 'late', 'early_leave', 'incomplete'
    """
    if not clock_in_time:
        return 'absent'
    
    if not clock_out_time:
        return 'incomplete'
    
    late_mins = calculate_late_minutes(clock_in_time, office_start, late_tolerance)
    early_mins = calculate_early_leave(clock_out_time, office_end)
    
    if late_mins > 0 and early_mins > 0:
        return 'late_and_early'
    elif late_mins > 0:
        return 'late'
    elif early_mins > 0:
        return 'early_leave'
    
    return 'present'


def format_duration(minutes):
    """Format menit ke string jam:menit"""
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        return f"{hours} jam {mins} menit"
    return f"{mins} menit"


def get_working_days_in_month(year, month):
    """
    Hitung hari kerja dalam bulan (Senin-Jumat, exclude weekend)
    Catatan: Belum termasuk hari libur nasional
    """
    import calendar
    
    cal = calendar.Calendar()
    working_days = 0
    
    for day in cal.itermonthdays2(year, month):
        if day[0] != 0 and day[1] < 5:  # day[1]: 0=Monday, 6=Sunday
            working_days += 1
    
    return working_days


def is_indonesian_holiday(check_date):
    """
    Cek apakah tanggal adalah hari libur nasional Indonesia
    Catatan: Ini simplified, untuk production gunakan API atau database
    """
    # Hari libur tetap 2025 (contoh)
    fixed_holidays_2025 = [
        date(2025, 1, 1),   # Tahun Baru
        date(2025, 1, 29),  # Imlek
        date(2025, 3, 29),  # Nyepi
        date(2025, 3, 31),  # Wafat Isa Almasih
        date(2025, 4, 1),   # Idul Fitri
        date(2025, 4, 2),   # Idul Fitri
        date(2025, 5, 1),   # Hari Buruh
        date(2025, 5, 12),  # Waisak
        date(2025, 5, 29),  # Kenaikan Isa Almasih
        date(2025, 6, 1),   # Hari Lahir Pancasila
        date(2025, 6, 7),   # Idul Adha
        date(2025, 6, 27),  # Tahun Baru Islam
        date(2025, 8, 17),  # HUT RI
        date(2025, 9, 5),   # Maulid Nabi
        date(2025, 12, 25), # Natal
    ]
    
    return check_date in fixed_holidays_2025
