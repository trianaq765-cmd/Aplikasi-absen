/**
 * Advanced Geolocation Module
 * GPS validation, accuracy monitoring, mock detection
 * Sistem Absensi Karyawan 2025
 */

// ============================================
// CONFIGURATION
// ============================================
const GeoConfig = {
    // Accuracy settings
    HIGH_ACCURACY: true,
    MAX_AGE: 30000,           // 30 seconds
    TIMEOUT: 15000,           // 15 seconds
    
    // Validation
    MAX_ACCEPTABLE_ACCURACY: 100,  // meters
    MIN_ACCURACY_WARNING: 50,      // meters
    
    // Update intervals
    WATCH_INTERVAL: 5000,     // 5 seconds
    
    // Mock detection
    ENABLE_MOCK_DETECTION: true,
    SPEED_THRESHOLD_KMPH: 200  // Max realistic speed
};

// ============================================
// STATE
// ============================================
let watchId = null;
let locationHistory = [];
let lastValidLocation = null;
let mockDetected = false;

// ============================================
// ENHANCED LOCATION GETTER
// ============================================
async function getEnhancedLocation(options = {}) {
    const config = {
        enableHighAccuracy: options.highAccuracy ?? GeoConfig.HIGH_ACCURACY,
        maximumAge: options.maxAge ?? GeoConfig.MAX_AGE,
        timeout: options.timeout ?? GeoConfig.TIMEOUT
    };
    
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject({
                code: 0,
                message: 'Geolocation tidak didukung browser ini'
            });
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    altitude: position.coords.altitude,
                    altitudeAccuracy: position.coords.altitudeAccuracy,
                    heading: position.coords.heading,
                    speed: position.coords.speed,
                    timestamp: position.timestamp
                };
                
                // Check for mock location
                if (GeoConfig.ENABLE_MOCK_DETECTION) {
                    const mockCheck = detectMockLocation(location);
                    if (mockCheck.isMock) {
                        reject({
                            code: -1,
                            message: mockCheck.reason,
                            isMock: true
                        });
                        return;
                    }
                }
                
                // Add to history
                addLocationToHistory(location);
                
                // Get address
                try {
                    location.address = await reverseGeocode(
                        location.latitude, 
                        location.longitude
                    );
                } catch {
                    location.address = null;
                }
                
                lastValidLocation = location;
                resolve(location);
            },
            (error) => {
                let message = 'Gagal mendapatkan lokasi';
                
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        message = 'Izin lokasi ditolak. Aktifkan GPS dan izinkan akses lokasi di pengaturan browser.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        message = 'Informasi lokasi tidak tersedia. Pastikan GPS aktif.';
                        break;
                    case error.TIMEOUT:
                        message = 'Waktu permintaan lokasi habis. Coba di tempat terbuka.';
                        break;
                }
                
                reject({
                    code: error.code,
                    message: message
                });
            },
            config
        );
    });
}

// ============================================
// LOCATION WATCHING
// ============================================
function startWatchingLocation(callback) {
    if (watchId !== null) {
        stopWatchingLocation();
    }
    
    watchId = navigator.geolocation.watchPosition(
        (position) => {
            const location = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy,
                timestamp: position.timestamp
            };
            
            // Check for suspicious movement
            if (locationHistory.length > 0) {
                const lastLoc = locationHistory[locationHistory.length - 1];
                const timeDiff = (location.timestamp - lastLoc.timestamp) / 1000;
                const distance = haversineDistance(
                    lastLoc.latitude, lastLoc.longitude,
                    location.latitude, location.longitude
                );
                
                const speedKmph = (distance / 1000) / (timeDiff / 3600);
                
                if (speedKmph > GeoConfig.SPEED_THRESHOLD_KMPH) {
                    location.suspicious = true;
                    location.suspiciousReason = `Kecepatan tidak wajar: ${speedKmph.toFixed(0)} km/jam`;
                }
            }
            
            addLocationToHistory(location);
            lastValidLocation = location;
            
            if (callback) {
                callback(location);
            }
        },
        (error) => {
            console.error('Watch location error:', error);
            if (callback) {
                callback(null, error);
            }
        },
        {
            enableHighAccuracy: GeoConfig.HIGH_ACCURACY,
            maximumAge: GeoConfig.MAX_AGE,
            timeout: GeoConfig.TIMEOUT
        }
    );
    
    return watchId;
}

function stopWatchingLocation() {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }
}

// ============================================
// MOCK LOCATION DETECTION
// ============================================
function detectMockLocation(location) {
    // Check 1: Accuracy too perfect (mock apps often give 0 or very low accuracy)
    if (location.accuracy === 0) {
        return {
            isMock: true,
            reason: 'Akurasi GPS mencurigakan (0m)'
        };
    }
    
    // Check 2: Coordinates too precise (more than 7 decimal places is suspicious)
    const latDecimals = (location.latitude.toString().split('.')[1] || '').length;
    const lonDecimals = (location.longitude.toString().split('.')[1] || '').length;
    
    if (latDecimals > 10 || lonDecimals > 10) {
        return {
            isMock: true,
            reason: 'Koordinat terlalu presisi (kemungkinan fake GPS)'
        };
    }
    
    // Check 3: Speed movement check against history
    if (locationHistory.length >= 2) {
        const prev = locationHistory[locationHistory.length - 1];
        const timeDiff = (location.timestamp - prev.timestamp) / 1000;
        
        if (timeDiff > 0) {
            const distance = haversineDistance(
                prev.latitude, prev.longitude,
                location.latitude, location.longitude
            );
            
            const speedKmph = (distance / 1000) / (timeDiff / 3600);
            
            if (speedKmph > GeoConfig.SPEED_THRESHOLD_KMPH) {
                mockDetected = true;
                return {
                    isMock: true,
                    reason: `Perpindahan tidak wajar: ${distance.toFixed(0)}m dalam ${timeDiff.toFixed(0)} detik`
                };
            }
        }
    }
    
    // Check 4: Altitude check (if available)
    if (location.altitude !== null && location.altitudeAccuracy !== null) {
        // Extreme altitudes for Indonesia (Mt. Jaya is 4,884m)
        if (location.altitude < -100 || location.altitude > 5000) {
            return {
                isMock: true,
                reason: `Altitude tidak valid: ${location.altitude}m`
            };
        }
    }
    
    return { isMock: false };
}

// ============================================
// LOCATION VALIDATION
// ============================================
async function validateLocationForAttendance(workType = 'wfo') {
    const statusEl = document.getElementById('locationStatus');
    
    const updateStatus = (message, type = 'info') => {
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `location-status ${type}`;
        }
    };
    
    updateStatus('Mendapatkan lokasi GPS...', 'loading');
    
    try {
        // Get current location
        const location = await getEnhancedLocation();
        
        // Check accuracy
        if (location.accuracy > GeoConfig.MAX_ACCEPTABLE_ACCURACY) {
            updateStatus(
                `Akurasi GPS rendah (${location.accuracy.toFixed(0)}m). Coba di tempat terbuka.`,
                'warning'
            );
            return {
                valid: false,
                location: location,
                message: `Akurasi GPS terlalu rendah: ${location.accuracy.toFixed(0)}m`
            };
        }
        
        // Validate with server
        const validationResult = await api.post('/attendance/validate-location', {
            latitude: location.latitude,
            longitude: location.longitude,
            accuracy: location.accuracy,
            work_type: workType
        });
        
        if (validationResult.success) {
            const data = validationResult.data;
            
            if (data.is_valid) {
                updateStatus(data.message, 'valid');
                return {
                    valid: true,
                    location: location,
                    message: data.message,
                    office: data.nearest_office
                };
            } else {
                updateStatus(data.message, 'invalid');
                return {
                    valid: false,
                    location: location,
                    message: data.message,
                    distance: data.distance_meters
                };
            }
        }
        
        return {
            valid: false,
            location: location,
            message: 'Gagal memvalidasi lokasi'
        };
        
    } catch (error) {
        const message = error.message || 'Gagal mendapatkan lokasi';
        updateStatus(message, 'error');
        
        return {
            valid: false,
            location: null,
            message: message,
            isMock: error.isMock || false
        };
    }
}

// ============================================
// HELPER FUNCTIONS
// ============================================
function haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Earth's radius in meters
    
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c;
}

function toRad(deg) {
    return deg * (Math.PI / 180);
}

async function reverseGeocode(lat, lon) {
    try {
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=id`
        );
        const data = await response.json();
        return data.display_name || null;
    } catch {
        return null;
    }
}

function addLocationToHistory(location) {
    locationHistory.push(location);
    
    // Keep only last 20 locations
    if (locationHistory.length > 20) {
        locationHistory.shift();
    }
}

function clearLocationHistory() {
    locationHistory = [];
    lastValidLocation = null;
    mockDetected = false;
}

// ============================================
// UI HELPERS
// ============================================
function displayLocationInfo(location, containerId = 'locationInfo') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let accuracyClass = 'good';
    let accuracyText = 'Baik';
    
    if (location.accuracy > GeoConfig.MAX_ACCEPTABLE_ACCURACY) {
        accuracyClass = 'bad';
        accuracyText = 'Rendah';
    } else if (location.accuracy > GeoConfig.MIN_ACCURACY_WARNING) {
        accuracyClass = 'moderate';
        accuracyText = 'Cukup';
    }
    
    container.innerHTML = `
        <div class="location-result">
            <i class="fas fa-map-marker-alt"></i>
            <div class="location-details">
                <h5>Lokasi Terdeteksi</h5>
                <p class="location-address">${location.address || 'Memuat alamat...'}</p>
                <div class="location-meta">
                    <span class="accuracy ${accuracyClass}">
                        <i class="fas fa-crosshairs"></i>
                        Akurasi: ${location.accuracy.toFixed(0)}m (${accuracyText})
                    </span>
                    <span class="coordinates">
                        <i class="fas fa-globe"></i>
                        ${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}
                    </span>
                </div>
                ${location.suspicious ? `
                    <div class="location-warning">
                        <i class="fas fa-exclamation-triangle"></i>
                        ${location.suspiciousReason}
                    </div>
                ` : ''}
            </div>
            <button class="btn btn-sm btn-outline" onclick="refreshLocation()">
                <i class="fas fa-sync-alt"></i>
            </button>
        </div>
    `;
}

async function refreshLocation() {
    const container = document.getElementById('locationInfo');
    if (container) {
        container.innerHTML = `
            <div class="location-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Memperbarui lokasi...</p>
            </div>
        `;
    }
    
    try {
        const location = await getEnhancedLocation();
        currentLocation = location;
        displayLocationInfo(location);
    } catch (error) {
        if (container) {
            container.innerHTML = `
                <div class="location-error">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>${error.message}</p>
                    <button class="btn btn-sm btn-outline" onclick="refreshLocation()">
                        <i class="fas fa-redo"></i> Coba Lagi
                    </button>
                </div>
            `;
        }
    }
}

// ============================================
// MAP DISPLAY (Optional - uses Leaflet)
// ============================================
let locationMap = null;
let userMarker = null;
let officeMarkers = [];

function initLocationMap(containerId = 'locationMap') {
    // Check if Leaflet is available
    if (typeof L === 'undefined') {
        console.log('Leaflet not loaded, skipping map initialization');
        return null;
    }
    
    const container = document.getElementById(containerId);
    if (!container) return null;
    
    // Initialize map centered on Jakarta
    locationMap = L.map(containerId).setView([-6.2088, 106.8456], 13);
    
    // Add tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(locationMap);
    
    return locationMap;
}

function updateMapLocation(location) {
    if (!locationMap) return;
    
    const latLng = [location.latitude, location.longitude];
    
    // Remove existing user marker
    if (userMarker) {
        locationMap.removeLayer(userMarker);
    }
    
    // Add new marker
    userMarker = L.marker(latLng, {
        icon: L.divIcon({
            className: 'user-location-marker',
            html: '<i class="fas fa-user"></i>',
            iconSize: [30, 30]
        })
    }).addTo(locationMap);
    
    // Add accuracy circle
    L.circle(latLng, {
        radius: location.accuracy,
        color: '#3b82f6',
        fillColor: '#3b82f6',
        fillOpacity: 0.2
    }).addTo(locationMap);
    
    // Center map on user
    locationMap.setView(latLng, 16);
}

function addOfficeMarkersToMap(offices) {
    if (!locationMap) return;
    
    // Remove existing office markers
    officeMarkers.forEach(marker => locationMap.removeLayer(marker));
    officeMarkers = [];
    
    // Add office markers
    offices.forEach(office => {
        const marker = L.marker([office.latitude, office.longitude], {
            icon: L.divIcon({
                className: 'office-location-marker',
                html: '<i class="fas fa-building"></i>',
                iconSize: [30, 30]
            })
        }).bindPopup(`
            <strong>${office.name}</strong><br>
            Radius: ${office.radius_meters}m
        `).addTo(locationMap);
        
        // Add radius circle
        L.circle([office.latitude, office.longitude], {
            radius: office.radius_meters,
            color: '#10b981',
            fillColor: '#10b981',
            fillOpacity: 0.1
        }).addTo(locationMap);
        
        officeMarkers.push(marker);
    });
}

// ============================================
// EXPORT
// ============================================
window.getEnhancedLocation = getEnhancedLocation;
window.startWatchingLocation = startWatchingLocation;
window.stopWatchingLocation = stopWatchingLocation;
window.validateLocationForAttendance = validateLocationForAttendance;
window.displayLocationInfo = displayLocationInfo;
window.refreshLocation = refreshLocation;
window.initLocationMap = initLocationMap;
window.updateMapLocation = updateMapLocation;
window.addOfficeMarkersToMap = addOfficeMarkersToMap;
window.clearLocationHistory = clearLocationHistory;
