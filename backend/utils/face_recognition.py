"""
Face Recognition Module
Menggunakan face_recognition library (dlib-based)
Untuk verifikasi identitas karyawan saat absensi
"""

import os
import io
import base64
import numpy as np
from PIL import Image
import logging

# Try to import face_recognition, with fallback
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logging.warning("face_recognition library not available. Using fallback mode.")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available.")


class FaceRecognitionService:
    """
    Service untuk Face Recognition
    Features:
    - Encode wajah dari foto
    - Simpan encoding ke database
    - Verifikasi wajah saat absensi
    - Deteksi liveness (anti-spoofing basic)
    """
    
    def __init__(self, tolerance=0.6):
        """
        Initialize face recognition service
        
        Args:
            tolerance: Face matching tolerance (lower = stricter)
                      0.6 is typical, 0.5 is more strict
        """
        self.tolerance = tolerance
        self.is_available = FACE_RECOGNITION_AVAILABLE
    
    def decode_base64_image(self, base64_string):
        """
        Decode base64 image string to numpy array
        
        Args:
            base64_string: Base64 encoded image (with or without data URL prefix)
        
        Returns:
            numpy array of image
        """
        try:
            # Remove data URL prefix if present
            if 'base64,' in base64_string:
                base64_string = base64_string.split('base64,')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_string)
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            return np.array(image)
            
        except Exception as e:
            logging.error(f"Error decoding image: {str(e)}")
            return None
    
    def detect_faces(self, image):
        """
        Detect faces in image
        
        Args:
            image: numpy array of image
        
        Returns:
            list of face locations [(top, right, bottom, left), ...]
        """
        if not self.is_available:
            return self._fallback_detect_faces(image)
        
        try:
            # Use HOG-based detection (faster) or CNN (more accurate)
            face_locations = face_recognition.face_locations(image, model="hog")
            return face_locations
        except Exception as e:
            logging.error(f"Error detecting faces: {str(e)}")
            return []
    
    def _fallback_detect_faces(self, image):
        """
        Fallback face detection using OpenCV Haar Cascade
        """
        if not CV2_AVAILABLE:
            # Ultimate fallback: assume there's a face
            return [(0, image.shape[1], image.shape[0], 0)]
        
        try:
            # Load Haar Cascade
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Convert to face_recognition format (top, right, bottom, left)
            locations = []
            for (x, y, w, h) in faces:
                locations.append((y, x + w, y + h, x))
            
            return locations
            
        except Exception as e:
            logging.error(f"Fallback detection error: {str(e)}")
            return []
    
    def encode_face(self, image, face_location=None):
        """
        Generate face encoding from image
        
        Args:
            image: numpy array of image
            face_location: optional specific face location
        
        Returns:
            numpy array of face encoding (128-dimensional) or None
        """
        if not self.is_available:
            return self._fallback_encode_face(image)
        
        try:
            if face_location:
                encodings = face_recognition.face_encodings(image, [face_location])
            else:
                encodings = face_recognition.face_encodings(image)
            
            if encodings:
                return encodings[0]
            return None
            
        except Exception as e:
            logging.error(f"Error encoding face: {str(e)}")
            return None
    
    def _fallback_encode_face(self, image):
        """
        Fallback encoding: generate a simple hash-based encoding
        Not as accurate but works without face_recognition library
        """
        try:
            # Resize image to standard size
            pil_image = Image.fromarray(image)
            pil_image = pil_image.resize((128, 128))
            
            # Convert to grayscale and flatten
            gray = pil_image.convert('L')
            pixels = np.array(gray).flatten()
            
            # Normalize to create a pseudo-encoding
            encoding = pixels.astype(np.float64) / 255.0
            
            # Reduce to 128 dimensions using simple averaging
            chunk_size = len(encoding) // 128
            reduced = np.array([
                encoding[i:i+chunk_size].mean() 
                for i in range(0, len(encoding), chunk_size)
            ])[:128]
            
            return reduced
            
        except Exception as e:
            logging.error(f"Fallback encoding error: {str(e)}")
            return None
    
    def compare_faces(self, known_encoding, unknown_encoding):
        """
        Compare two face encodings
        
        Args:
            known_encoding: stored face encoding
            unknown_encoding: new face encoding to compare
        
        Returns:
            tuple: (is_match: bool, distance: float)
        """
        if known_encoding is None or unknown_encoding is None:
            return False, 1.0
        
        try:
            if self.is_available:
                # Use face_recognition library
                distances = face_recognition.face_distance([known_encoding], unknown_encoding)
                distance = distances[0]
                is_match = distance <= self.tolerance
            else:
                # Fallback: use euclidean distance
                distance = np.linalg.norm(known_encoding - unknown_encoding)
                # Normalize distance (fallback encodings have different scale)
                distance = min(distance / 10, 1.0)
                is_match = distance <= self.tolerance
            
            return is_match, float(distance)
            
        except Exception as e:
            logging.error(f"Error comparing faces: {str(e)}")
            return False, 1.0
    
    def encoding_to_bytes(self, encoding):
        """Convert encoding numpy array to bytes for database storage"""
        if encoding is None:
            return None
        return encoding.tobytes()
    
    def bytes_to_encoding(self, encoding_bytes):
        """Convert bytes back to numpy array"""
        if encoding_bytes is None:
            return None
        return np.frombuffer(encoding_bytes, dtype=np.float64)
    
    def check_liveness(self, image):
        """
        Basic liveness detection (anti-spoofing)
        Checks if the image is likely from a real person vs a photo
        
        Note: This is a basic implementation. Production systems should use
        more sophisticated methods like 3D depth sensing or challenge-response.
        
        Args:
            image: numpy array of image
        
        Returns:
            tuple: (is_live: bool, confidence: float, reason: str)
        """
        try:
            # Check 1: Image quality and size
            height, width = image.shape[:2]
            if width < 200 or height < 200:
                return False, 0.0, "Resolusi gambar terlalu rendah"
            
            # Check 2: Brightness and contrast
            if len(image.shape) == 3:
                gray = np.mean(image, axis=2)
            else:
                gray = image
            
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            if brightness < 30 or brightness > 225:
                return False, 0.3, "Pencahayaan tidak optimal"
            
            if contrast < 20:
                return False, 0.3, "Kontras gambar terlalu rendah"
            
            # Check 3: Face detection confidence
            faces = self.detect_faces(image)
            if len(faces) == 0:
                return False, 0.0, "Wajah tidak terdeteksi"
            
            if len(faces) > 1:
                return False, 0.5, "Terdeteksi lebih dari satu wajah"
            
            # Check 4: Face size relative to image
            face = faces[0]
            face_height = face[2] - face[0]
            face_width = face[1] - face[3]
            face_area = face_height * face_width
            image_area = height * width
            face_ratio = face_area / image_area
            
            if face_ratio < 0.05:
                return False, 0.4, "Wajah terlalu jauh dari kamera"
            
            if face_ratio > 0.8:
                return False, 0.4, "Wajah terlalu dekat dengan kamera"
            
            # All checks passed
            confidence = 0.8  # Base confidence for basic checks
            return True, confidence, "Liveness check passed"
            
        except Exception as e:
            logging.error(f"Liveness check error: {str(e)}")
            return False, 0.0, f"Error: {str(e)}"
    
    def process_attendance_photo(self, base64_image, stored_encoding=None):
        """
        Complete processing for attendance photo
        
        Args:
            base64_image: Base64 encoded photo from frontend
            stored_encoding: Previously stored face encoding (bytes) for verification
        
        Returns:
            dict with results
        """
        result = {
            'success': False,
            'face_detected': False,
            'face_verified': False,
            'is_live': False,
            'new_encoding': None,
            'message': '',
            'confidence': 0.0
        }
        
        # Decode image
        image = self.decode_base64_image(base64_image)
        if image is None:
            result['message'] = 'Gagal memproses gambar'
            return result
        
        # Detect faces
        faces = self.detect_faces(image)
        if not faces:
            result['message'] = 'Wajah tidak terdeteksi. Pastikan wajah terlihat jelas.'
            return result
        
        result['face_detected'] = True
        
        # Check liveness
        is_live, live_confidence, live_message = self.check_liveness(image)
        result['is_live'] = is_live
        
        if not is_live:
            result['message'] = f'Verifikasi gagal: {live_message}'
            return result
        
        # Encode face
        encoding = self.encode_face(image, faces[0])
        if encoding is None:
            result['message'] = 'Gagal mengekstrak fitur wajah'
            return result
        
        result['new_encoding'] = self.encoding_to_bytes(encoding)
        
        # Verify against stored encoding if provided
        if stored_encoding is not None:
            known_encoding = self.bytes_to_encoding(stored_encoding)
            is_match, distance = self.compare_faces(known_encoding, encoding)
            
            result['face_verified'] = is_match
            result['confidence'] = 1.0 - distance
            
            if not is_match:
                result['message'] = 'Wajah tidak cocok dengan data terdaftar'
                return result
        else:
            # No stored encoding, this might be first-time registration
            result['face_verified'] = True
            result['confidence'] = live_confidence
        
        result['success'] = True
        result['message'] = 'Verifikasi wajah berhasil'
        
        return result


# Singleton instance
face_service = FaceRecognitionService()
