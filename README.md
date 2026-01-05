# 🇮🇩 Sistem Absensi Karyawan 2025

Sistem absensi modern untuk perusahaan Indonesia, mendukung absensi via GPS, QR Code, dan Face Recognition.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-green.svg)
![Flask](https://img.shields.io/badge/flask-3.0-orange.svg)

## ✨ Fitur Utama

- 📍 **Absensi GPS** - Validasi lokasi dengan radius kantor
- 📱 **Absensi QR Code** - Generate & scan QR untuk absen
- 👤 **Face Recognition** - Verifikasi wajah dengan liveness detection
- 📅 **Manajemen Cuti** - Sesuai UU Ketenagakerjaan Indonesia
- 📊 **Laporan & Export** - Export ke Excel/PDF
- 🏢 **Multi-Cabang** - Support banyak lokasi kantor
- 📱 **Responsive** - Mobile-first design
- 🔐 **Keamanan** - JWT authentication, role-based access

## 🛠️ Tech Stack

### Backend
- Python 3.11
- Flask 3.0
- PostgreSQL 15
- SQLAlchemy 2.0
- JWT Authentication

### Frontend
- HTML5 / CSS3 / JavaScript
- TensorFlow.js (Face Detection)
- Geolocation API
- Responsive Design

### Deployment
- Docker
- Render.com
- GitHub Actions CI/CD

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (atau SQLite untuk development)
- Git

### Local Development

1. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/absensi-karyawan-2025.git
   cd absensi-karyawan-2025
