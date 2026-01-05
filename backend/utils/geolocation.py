"""
Advanced Geolocation Module
Validasi lokasi untuk absensi WFO/WFH
"""

import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class OfficeLocation:
    """Data class for office location"""
    id: int
    name: str
    latitude: float
    longitude: float
    radius_meters: int
    address: str = ""
    is_active: bool = True


@dataclass
class LocationValidationResult:
    """Result of location validation"""
    is_valid: bool
    distance_meters: float
    nearest_office: Optional[str]
    message: str
    accuracy_warning: bool = False


class GeolocationService:
    """
    Service untuk validasi geolokasi
    Features:
    - Validasi radius kantor
    - Support multi-lokasi kantor
    - Deteksi GPS spoofing (basic)
    - Perhitungan jarak akurat (Haversine)
    """
    
    # Earth's radius in meters
    EARTH_RADIUS = 6371000
    
    # Maximum acceptable GPS accuracy (meters)
    MAX_ACCEPTABLE_ACCURACY = 100
    
    # Minimum accuracy for reliable check (meters)
    MIN_RELIABLE_ACCURACY = 50
    
    def __init__(self):
        self.office_locations: List[OfficeLocation] = []
    
    def set_office_locations(self, locations: List[Dict]):
        """
        Set daftar lokasi kantor
        
        Args:
            locations: List of location dicts with keys:
                       id, name, latitude, longitude, radius_meters, address
        """
        self.office_locations = [
            OfficeLocation(**loc) for loc in locations
        ]
    
    def add_office_location(self, location: Dict):
        """Add single office location"""
        self.office_locations.append(OfficeLocation(**location))
    
    def haversine_distance(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
        
        Returns:
            Distance in meters
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return self.EARTH_RADIUS * c
    
    def validate_location(
        self,
        user_lat: float,
        user_lon: float,
        accuracy: Optional[float] = None,
        allowed_office_ids: Optional[List[int]] = None
    ) -> LocationValidationResult:
        """
        Validate user location against office locations
        
        Args:
            user_lat: User's latitude
            user_lon: User's longitude
            accuracy: GPS accuracy in meters (optional)
            allowed_office_ids: List of office IDs user is allowed to check in
        
        Returns:
            LocationValidationResult
        """
        # Check if we have office locations
        if not self.office_locations:
            return LocationValidationResult(
                is_valid=False,
                distance_meters=0,
                nearest_office=None,
                message="Tidak ada lokasi kantor yang dikonfigurasi"
            )
        
        # Check GPS accuracy
        accuracy_warning = False
        if accuracy is not None:
            if accuracy > self.MAX_ACCEPTABLE_ACCURACY:
                return LocationValidationResult(
                    is_valid=False,
                    distance_meters=0,
                    nearest_office=None,
                    message=f"Akurasi GPS terlalu rendah ({accuracy:.0f}m). "
                           f"Maksimal {self.MAX_ACCEPTABLE_ACCURACY}m. "
                           "Coba di tempat terbuka."
                )
            elif accuracy > self.MIN_RELIABLE_ACCURACY:
                accuracy_warning = True
        
        # Filter allowed offices
        offices_to_check = self.office_locations
        if allowed_office_ids:
            offices_to_check = [
                o for o in self.office_locations 
                if o.id in allowed_office_ids and o.is_active
            ]
        else:
            offices_to_check = [o for o in self.office_locations if o.is_active]
        
        if not offices_to_check:
            return LocationValidationResult(
                is_valid=False,
                distance_meters=0,
                nearest_office=None,
                message="Tidak ada lokasi kantor yang tersedia untuk Anda"
            )
        
        # Find nearest office and check if within radius
        nearest_office = None
        min_distance = float('inf')
        valid_office = None
        
        for office in offices_to_check:
            distance = self.haversine_distance(
                user_lat, user_lon,
                office.latitude, office.longitude
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest_office = office
            
            # Check if within radius (with accuracy buffer)
            effective_radius = office.radius_meters
            if accuracy:
                effective_radius += accuracy  # Add accuracy as buffer
            
            if distance <= effective_radius:
                valid_office = office
                break  # Found valid location
        
        if valid_office:
            message = f"Lokasi valid: {valid_office.name} ({min_distance:.0f}m)"
            if accuracy_warning:
                message += f" (Akurasi GPS: {accuracy:.0f}m - disarankan di tempat terbuka)"
            
            return LocationValidationResult(
                is_valid=True,
                distance_meters=min_distance,
                nearest_office=valid_office.name,
                message=message,
                accuracy_warning=accuracy_warning
            )
        else:
            return LocationValidationResult(
                is_valid=False,
                distance_meters=min_distance,
                nearest_office=nearest_office.name if nearest_office else None,
                message=f"Anda berada {min_distance:.0f}m dari {nearest_office.name}. "
                       f"Maksimal {nearest_office.radius_meters}m untuk absen WFO."
            )
    
    def detect_spoofing(
        self,
        current_location: Tuple[float, float],
        previous_location: Optional[Tuple[float, float]],
        time_diff_seconds: float
    ) -> Tuple[bool, str]:
        """
        Basic GPS spoofing detection
        Checks if movement is physically possible
        
        Args:
            current_location: (lat, lon) of current position
            previous_location: (lat, lon) of previous position
            time_diff_seconds: Time difference between readings
        
        Returns:
            Tuple: (is_suspicious, reason)
        """
        if previous_location is None:
            return False, ""
        
        # Calculate distance moved
        distance = self.haversine_distance(
            previous_location[0], previous_location[1],
            current_location[0], current_location[1]
        )
        
        # Calculate speed (meters per second)
        if time_diff_seconds <= 0:
            time_diff_seconds = 1
        
        speed_mps = distance / time_diff_seconds
        speed_kmph = speed_mps * 3.6
        
        # Check for impossible speeds
        # Max reasonable speed: 200 km/h (high-speed train/car)
        MAX_SPEED_KMPH = 200
        
        if speed_kmph > MAX_SPEED_KMPH:
            return True, (
                f"Perpindahan lokasi mencurigakan: "
                f"{distance:.0f}m dalam {time_diff_seconds:.0f} detik "
                f"({speed_kmph:.0f} km/jam)"
            )
        
        # Check for exact same coordinates (too precise)
        if (current_location[0] == previous_location[0] and 
            current_location[1] == previous_location[1]):
            return True, "Koordinat identik dengan sebelumnya (kemungkinan fake GPS)"
        
        return False, ""
    
    def get_location_summary(
        self,
        lat: float,
        lon: float
    ) -> Dict:
        """
        Get summary of location relative to all offices
        
        Returns:
            Dict with distances to all offices
        """
        summary = {
            'user_location': {'latitude': lat, 'longitude': lon},
            'offices': [],
            'nearest': None,
            'in_range': []
        }
        
        min_distance = float('inf')
        
        for office in self.office_locations:
            if not office.is_active:
                continue
                
            distance = self.haversine_distance(
                lat, lon,
                office.latitude, office.longitude
            )
            
            office_info = {
                'id': office.id,
                'name': office.name,
                'distance_meters': round(distance, 2),
                'is_in_range': distance <= office.radius_meters,
                'radius_meters': office.radius_meters
            }
            
            summary['offices'].append(office_info)
            
            if office_info['is_in_range']:
                summary['in_range'].append(office.name)
            
            if distance < min_distance:
                min_distance = distance
                summary['nearest'] = office.name
        
        return summary
    
    def validate_wfh_location(
        self,
        user_lat: float,
        user_lon: float,
        registered_home_lat: Optional[float] = None,
        registered_home_lon: Optional[float] = None,
        home_radius: int = 500
    ) -> LocationValidationResult:
        """
        Validate WFH location
        If registered home location exists, check against it
        Otherwise, just ensure not at office
        
        Args:
            user_lat, user_lon: User's current location
            registered_home_lat, registered_home_lon: Registered home location
            home_radius: Allowed radius from home (default 500m)
        
        Returns:
            LocationValidationResult
        """
        # First check if at office (should not be for WFH)
        office_check = self.validate_location(user_lat, user_lon)
        
        if office_check.is_valid:
            return LocationValidationResult(
                is_valid=False,
                distance_meters=office_check.distance_meters,
                nearest_office=office_check.nearest_office,
                message="Anda terdeteksi di kantor. Gunakan mode WFO untuk absen."
            )
        
        # If registered home location exists, validate against it
        if registered_home_lat is not None and registered_home_lon is not None:
            distance_from_home = self.haversine_distance(
                user_lat, user_lon,
                registered_home_lat, registered_home_lon
            )
            
            if distance_from_home <= home_radius:
                return LocationValidationResult(
                    is_valid=True,
                    distance_meters=distance_from_home,
                    nearest_office=None,
                    message=f"Lokasi WFH valid ({distance_from_home:.0f}m dari alamat terdaftar)"
                )
            else:
                return LocationValidationResult(
                    is_valid=False,
                    distance_meters=distance_from_home,
                    nearest_office=None,
                    message=f"Anda {distance_from_home:.0f}m dari alamat WFH terdaftar. "
                           f"Maksimal {home_radius}m."
                )
        
        # No registered home, just allow WFH from anywhere not at office
        return LocationValidationResult(
            is_valid=True,
            distance_meters=office_check.distance_meters,
            nearest_office=office_check.nearest_office,
            message="Lokasi WFH tercatat"
        )


# Singleton instance
geo_service = GeolocationService()


def init_office_locations_from_db(app):
    """
    Initialize office locations from database
    Call this after app context is ready
    """
    from models import OfficeLocation as OfficeLocationModel
    
    with app.app_context():
        locations = OfficeLocationModel.query.filter_by(is_active=True).all()
        
        geo_service.set_office_locations([
            {
                'id': loc.id,
                'name': loc.name,
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'radius_meters': loc.radius_meters,
                'address': loc.address or ""
            }
            for loc in locations
        ])
