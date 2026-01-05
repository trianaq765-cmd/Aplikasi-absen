/**
 * Face Detection Module
 * Menggunakan TensorFlow.js untuk deteksi wajah di browser
 * Sistem Absensi Karyawan 2025
 */

// ============================================
// CONFIGURATION
// ============================================
const FaceConfig = {
    // Model URLs (using face-landmarks-detection from TensorFlow.js)
    MODEL_URL: 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh',
    
    // Detection settings
    MIN_FACE_SIZE: 100,        // Minimum face size in pixels
    MAX_FACES: 1,               // Maximum faces to detect
    SCORE_THRESHOLD: 0.5,       // Confidence threshold
    
    // UI settings
    FACE_GUIDE_COLOR: '#10b981',
    FACE_GUIDE_COLOR_INVALID: '#ef4444',
    
    // Capture settings
    IMAGE_QUALITY: 0.8,
    IMAGE_TYPE: 'image/jpeg'
};

// ============================================
// STATE
// ============================================
let faceDetector = null;
let isModelLoaded = false;
let isDetecting = false;
let lastDetectionResult = null;
let detectionInterval = null;

// ============================================
// MODEL LOADING
// ============================================
async function loadFaceDetectionModel() {
    try {
        // Check if TensorFlow.js is available
        if (typeof tf === 'undefined') {
            console.log('TensorFlow.js not loaded, using fallback mode');
            return false;
        }
        
        // Load BlazeFace model (lightweight face detection)
        faceDetector = await blazeface.load();
        isModelLoaded = true;
        console.log('Face detection model loaded');
        return true;
        
    } catch (error) {
        console.error('Failed to load face detection model:', error);
        return false;
    }
}

// ============================================
// FACE DETECTION
// ============================================
async function detectFace(videoElement) {
    if (!isModelLoaded || !faceDetector) {
        return { detected: false, message: 'Model belum dimuat' };
    }
    
    try {
        const predictions = await faceDetector.estimateFaces(videoElement, false);
        
        if (predictions.length === 0) {
            return { 
                detected: false, 
                message: 'Wajah tidak terdeteksi. Posisikan wajah di tengah kamera.' 
            };
        }
        
        if (predictions.length > 1) {
            return { 
                detected: false, 
                message: 'Terdeteksi lebih dari satu wajah.' 
            };
        }
        
        const face = predictions[0];
        const probability = face.probability[0];
        
        // Check confidence
        if (probability < FaceConfig.SCORE_THRESHOLD) {
            return { 
                detected: false, 
                message: 'Wajah tidak jelas. Pastikan pencahayaan cukup.' 
            };
        }
        
        // Check face size
        const width = face.bottomRight[0] - face.topLeft[0];
        const height = face.bottomRight[1] - face.topLeft[1];
        
        if (width < FaceConfig.MIN_FACE_SIZE || height < FaceConfig.MIN_FACE_SIZE) {
            return { 
                detected: false, 
                message: 'Wajah terlalu jauh. Dekatkan ke kamera.' 
            };
        }
        
        // All checks passed
        return {
            detected: true,
            message: 'Wajah terdeteksi',
            confidence: probability,
            bounds: {
                x: face.topLeft[0],
                y: face.topLeft[1],
                width: width,
                height: height
            },
            landmarks: face.landmarks
        };
        
    } catch (error) {
        console.error('Face detection error:', error);
        return { 
            detected: false, 
            message: 'Error saat mendeteksi wajah' 
        };
    }
}

// ============================================
// CONTINUOUS DETECTION
// ============================================
function startContinuousDetection(videoElement, callback, interval = 500) {
    if (detectionInterval) {
        clearInterval(detectionInterval);
    }
    
    isDetecting = true;
    
    detectionInterval = setInterval(async () => {
        if (!isDetecting) return;
        
        const result = await detectFace(videoElement);
        lastDetectionResult = result;
        
        if (callback) {
            callback(result);
        }
    }, interval);
}

function stopContinuousDetection() {
    isDetecting = false;
    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
}

// ============================================
// FACE GUIDE OVERLAY
// ============================================
function drawFaceGuide(canvasElement, videoElement, detectionResult) {
    const ctx = canvasElement.getContext('2d');
    const width = videoElement.videoWidth;
    const height = videoElement.videoHeight;
    
    // Set canvas size to match video
    canvasElement.width = width;
    canvasElement.height = height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw oval face guide
    const centerX = width / 2;
    const centerY = height / 2;
    const guideWidth = width * 0.4;
    const guideHeight = height * 0.6;
    
    ctx.strokeStyle = detectionResult?.detected 
        ? FaceConfig.FACE_GUIDE_COLOR 
        : FaceConfig.FACE_GUIDE_COLOR_INVALID;
    ctx.lineWidth = 3;
    ctx.setLineDash([10, 5]);
    
    ctx.beginPath();
    ctx.ellipse(centerX, centerY, guideWidth / 2, guideHeight / 2, 0, 0, 2 * Math.PI);
    ctx.stroke();
    
    // Draw detected face bounds if available
    if (detectionResult?.detected && detectionResult.bounds) {
        const bounds = detectionResult.bounds;
        
        ctx.strokeStyle = FaceConfig.FACE_GUIDE_COLOR;
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        
        ctx.strokeRect(bounds.x, bounds.y, bounds.width, bounds.height);
        
        // Draw landmarks
        if (detectionResult.landmarks) {
            ctx.fillStyle = FaceConfig.FACE_GUIDE_COLOR;
            detectionResult.landmarks.forEach(point => {
                ctx.beginPath();
                ctx.arc(point[0], point[1], 3, 0, 2 * Math.PI);
                ctx.fill();
            });
        }
    }
    
    // Draw status text
    ctx.font = '16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = detectionResult?.detected ? '#10b981' : '#ef4444';
    ctx.fillText(
        detectionResult?.message || 'Memuat...',
        centerX,
        height - 20
    );
}

// ============================================
// LIVENESS CHECK (Basic)
// ============================================
async function performLivenessCheck(videoElement, duration = 3000) {
    return new Promise((resolve) => {
        const samples = [];
        const sampleInterval = 200;
        let elapsed = 0;
        
        const updateStatus = (message) => {
            const statusEl = document.getElementById('livenessStatus');
            if (statusEl) statusEl.textContent = message;
        };
        
        updateStatus('Menganalisis... Tetap diam');
        
        const collectSample = async () => {
            const result = await detectFace(videoElement);
            
            if (result.detected) {
                samples.push({
                    time: elapsed,
                    bounds: result.bounds,
                    confidence: result.confidence
                });
            }
            
            elapsed += sampleInterval;
            
            if (elapsed < duration) {
                setTimeout(collectSample, sampleInterval);
            } else {
                // Analyze samples
                const analysis = analyzeLivenessSamples(samples);
                resolve(analysis);
            }
        };
        
        collectSample();
    });
}

function analyzeLivenessSamples(samples) {
    if (samples.length < 5) {
        return {
            isLive: false,
            confidence: 0,
            message: 'Tidak cukup data. Wajah tidak terdeteksi dengan konsisten.'
        };
    }
    
    // Check for natural micro-movements
    let totalMovement = 0;
    for (let i = 1; i < samples.length; i++) {
        const prev = samples[i - 1].bounds;
        const curr = samples[i].bounds;
        
        const dx = Math.abs(curr.x - prev.x);
        const dy = Math.abs(curr.y - prev.y);
        const dw = Math.abs(curr.width - prev.width);
        const dh = Math.abs(curr.height - prev.height);
        
        totalMovement += dx + dy + dw + dh;
    }
    
    const avgMovement = totalMovement / (samples.length - 1);
    
    // Too still (might be photo)
    if (avgMovement < 0.5) {
        return {
            isLive: false,
            confidence: 0.3,
            message: 'Terdeteksi tidak ada gerakan. Mungkin foto.'
        };
    }
    
    // Too much movement (might be video or shaky)
    if (avgMovement > 50) {
        return {
            isLive: false,
            confidence: 0.3,
            message: 'Terlalu banyak gerakan. Tetap stabil.'
        };
    }
    
    // Check confidence consistency
    const avgConfidence = samples.reduce((sum, s) => sum + s.confidence, 0) / samples.length;
    
    if (avgConfidence < 0.7) {
        return {
            isLive: false,
            confidence: avgConfidence,
            message: 'Kualitas deteksi rendah. Perbaiki pencahayaan.'
        };
    }
    
    // Passed all checks
    return {
        isLive: true,
        confidence: avgConfidence,
        message: 'Verifikasi liveness berhasil'
    };
}

// ============================================
// CAPTURE PHOTO
// ============================================
function capturePhoto(videoElement, canvasElement) {
    const ctx = canvasElement.getContext('2d');
    
    // Set canvas size
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    
    // Draw video frame
    ctx.drawImage(videoElement, 0, 0);
    
    // Convert to base64
    return canvasElement.toDataURL(FaceConfig.IMAGE_TYPE, FaceConfig.IMAGE_QUALITY);
}

// ============================================
// ENHANCED CAMERA FUNCTIONS
// ============================================
async function initFaceCamera() {
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('faceCanvas');
    const statusEl = document.getElementById('faceStatus');
    
    if (!video) return false;
    
    try {
        // Update status
        if (statusEl) statusEl.textContent = 'Memuat model deteksi wajah...';
        
        // Load model
        await loadFaceDetectionModel();
        
        // Start camera
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { 
                facingMode: 'user', 
                width: { ideal: 640 }, 
                height: { ideal: 480 } 
            }
        });
        
        video.srcObject = stream;
        cameraStream = stream;
        
        // Wait for video to be ready
        await new Promise(resolve => {
            video.onloadedmetadata = () => {
                video.play();
                resolve();
            };
        });
        
        // Start continuous detection with visual feedback
        if (canvas && isModelLoaded) {
            startContinuousDetection(video, (result) => {
                drawFaceGuide(canvas, video, result);
                if (statusEl) {
                    statusEl.textContent = result.message;
                    statusEl.className = result.detected ? 'status-success' : 'status-warning';
                }
            }, 300);
        }
        
        return true;
        
    } catch (error) {
        console.error('Camera init error:', error);
        if (statusEl) statusEl.textContent = 'Gagal mengakses kamera: ' + error.message;
        return false;
    }
}

async function captureFaceAndAttend() {
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    const btn = document.getElementById('btnCapture');
    
    if (!video || !canvas) return;
    
    // Check if face is detected
    if (!lastDetectionResult?.detected) {
        showToast('Wajah tidak terdeteksi. Posisikan wajah dengan benar.', 'error');
        return;
    }
    
    // Disable button
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memverifikasi...';
    }
    
    try {
        // Perform liveness check
        const livenessResult = await performLivenessCheck(video, 2000);
        
        if (!livenessResult.isLive) {
            showToast(livenessResult.message, 'error');
            resetCaptureButton();
            return;
        }
        
        // Capture photo
        const photoData = capturePhoto(video, canvas);
        
        // Get location
        let locationData = {};
        if (currentLocation) {
            locationData = {
                latitude: currentLocation.latitude,
                longitude: currentLocation.longitude,
                accuracy: currentLocation.accuracy
            };
        }
        
        // Determine action (clock in or out)
        const workType = document.querySelector('input[name="workType"]:checked')?.value || 'wfo';
        
        if (todayAttendance?.clock_in && !todayAttendance?.clock_out) {
            // Clock out
            await performClockOut('face', photoData, locationData);
        } else if (!todayAttendance?.clock_in) {
            // Clock in
            await performClockIn('face', workType, photoData, locationData);
        } else {
            showToast('Absensi hari ini sudah lengkap', 'info');
        }
        
    } catch (error) {
        console.error('Capture error:', error);
        showToast('Terjadi kesalahan saat memproses', 'error');
    } finally {
        resetCaptureButton();
    }
}

async function performClockIn(method, workType, photoData, locationData) {
    const data = {
        method: method,
        work_type: workType,
        photo: photoData,
        ...locationData
    };
    
    const result = await api.post('/attendance/clock-in', data);
    
    if (result.success) {
        showToast(result.message, 'success');
        todayAttendance = result.data;
        updateAttendanceDisplay();
        stopFaceCamera();
    } else {
        showToast(result.message || 'Gagal absen masuk', 'error');
    }
}

async function performClockOut(method, photoData, locationData) {
    const data = {
        method: method,
        photo: photoData,
        ...locationData
    };
    
    const result = await api.post('/attendance/clock-out', data);
    
    if (result.success) {
        showToast(result.message, 'success');
        todayAttendance = result.data;
        updateAttendanceDisplay();
        stopFaceCamera();
    } else {
        showToast(result.message || 'Gagal absen pulang', 'error');
    }
}

function stopFaceCamera() {
    stopContinuousDetection();
    
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    const video = document.getElementById('cameraFeed');
    if (video) video.srcObject = null;
    
    // Reset UI
    const btnStart = document.getElementById('btnStartCamera');
    const btnCapture = document.getElementById('btnCapture');
    const btnStop = document.getElementById('btnStopCamera');
    
    if (btnStart) btnStart.style.display = '';
    if (btnCapture) btnCapture.style.display = 'none';
    if (btnStop) btnStop.style.display = 'none';
}

function resetCaptureButton() {
    const btn = document.getElementById('btnCapture');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-camera"></i> Ambil Foto & Absen';
    }
}

// ============================================
// FACE REGISTRATION
// ============================================
async function registerFace() {
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    
    if (!video || !canvas) {
        showToast('Kamera tidak tersedia', 'error');
        return;
    }
    
    if (!lastDetectionResult?.detected) {
        showToast('Wajah tidak terdeteksi', 'error');
        return;
    }
    
    try {
        showToast('Mendaftarkan wajah...', 'info');
        
        // Capture photo
        const photoData = capturePhoto(video, canvas);
        
        // Send to server
        const result = await api.post('/attendance/register-face', {
            photo: photoData
        });
        
        if (result.success) {
            showToast('Wajah berhasil didaftarkan!', 'success');
        } else {
            showToast(result.message || 'Gagal mendaftarkan wajah', 'error');
        }
        
    } catch (error) {
        console.error('Face registration error:', error);
        showToast('Terjadi kesalahan', 'error');
    }
}

// ============================================
// EXPORT
// ============================================
window.loadFaceDetectionModel = loadFaceDetectionModel;
window.detectFace = detectFace;
window.initFaceCamera = initFaceCamera;
window.captureFaceAndAttend = captureFaceAndAttend;
window.stopFaceCamera = stopFaceCamera;
window.registerFace = registerFace;
