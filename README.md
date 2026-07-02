# 🛡️ AI Surveillance System — Human Violence & Harmful Object Detection

> **Real-time AI-powered surveillance system** that simultaneously detects **harmful objects (knives)** and **human violence** using dual **YOLOv11** models on a live webcam feed — with automated email alerts, evidence recording, and a full-featured admin dashboard.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![YOLOv11](https://img.shields.io/badge/YOLOv11-Ultralytics-purple?logo=yolo&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?logo=pytorch&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-5C3EE8?logo=opencv&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-Academic-orange)

---

## 📌 Table of Contents

- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [AI Models](#-ai-models)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [Usage](#-usage)
- [Screenshots](#-screenshots)
- [Testing](#-testing)
- [Contributors](#-contributors)

---

## 🎯 About the Project

The **Human Violence & Harmful Object Detection System** is an AI-powered real-time surveillance application developed as a **Final Year Project**. It addresses the critical need for automated threat detection in public spaces, institutions, and security-sensitive environments.

The system uses a **single webcam feed** and runs **two YOLOv11 models concurrently**:

| Model | File | Purpose |
|:---|:---|:---|
| **`best.pt`** | YOLOv11 | Detects harmful objects — **Knives, Blades, Weapons** |
| **`best2.pt`** | YOLOv11 | Detects **Human Violence** vs **Non-Violence** activity |

Both models run **simultaneously** on the same camera frame using a **multi-threaded pipeline**, and their bounding boxes are merged into a **single unified display** — providing real-time visual feedback with color-coded annotations.

When **both knife AND violence** are detected concurrently, the system triggers an **automated email alert** with attached snapshot evidence and a 5-second recorded video clip.

---

## ✨ Key Features

### 🔍 Dual AI Detection
- **Harmful Object (Knife) Detection** — YOLOv11 (`best.pt`) trained for real-time knife/blade/weapon detection
- **Human Violence Detection** — YOLOv11 (`best2.pt`) trained to classify violent vs non-violent human behavior
- Both models run **concurrently on the same webcam feed** with merged bounding box overlays

### 🚨 Intelligent Alerting System
- **Dual-detection trigger** — Email alerts fire only when **both** knife + violence are confirmed simultaneously
- **Hierarchical Reasoning Model (HRM)** — 5-stage validation pipeline to reduce false positives:
  1. Confidence threshold check
  2. Object class validation
  3. Multi-frame consecutive confirmation
  4. Temporal consistency (positive ratio over sliding window)
  5. Bounding box stability (IoU across frames)
- **Cooldown & rate limiting** — Prevents email spam (60-second cooldown per alert type, max 2 emails per type per session)

### 📧 Automated Email Alerts
- SMTP-based email with **TLS encryption** (Gmail compatible)
- Attachments include: knife snapshots, violence snapshots, and a **5-second evidence video clip**
- Role-based routing: Operator → receives alert + Admin also gets a copy

### 🎬 Evidence Recording
- Automatic **5-second video clip recording** when violence is detected
- Snapshots auto-saved to `alerts/` directory with timestamps
- All detections, recordings, and snapshots logged to SQLite database

### 🖥️ Full-Featured GUI (Tkinter)
- **Login System** — Admin + Operator roles with bcrypt-hashed passwords
- **Operator Registration** — Self-registration with email, mobile, full validation
- **Admin Dashboard** — Sidebar navigation with:
  - Start/Stop Detection
  - View Alerts (detection history)
  - View Recordings (video clips)
  - View Snapshots (image browser with click-to-open)
  - Object Detection Log & Violence Detection Log
  - **Live Speed Profiler** — Real-time per-stage timing (camera read, knife inference, violence inference, GUI render)
- **Dark theme UI** with accent colors and modern styling

### ⏱️ Performance Profiling
- Built-in **Speed Profiler** measuring avg/min/max/last timing per pipeline stage
- Live auto-refreshing profiler dashboard (updates every 2 seconds)

### 🧪 Comprehensive Test Suite
- **11 test modules** covering: Login, Registration, Camera, Knife Detection, Violence Detection, Email, Database, GUI, Recording, Profiler
- **Test Dashboard** — Tkinter-based UI with PASS/FAIL/SKIP results, GPU/RAM monitoring, exportable reports

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────┐
│                   WEBCAM (Single Feed)               │
└───────────────────────┬──────────────────────────────┘
                        │
              ┌─────────▼──────────┐
              │  Thread 1: Camera  │
              │    Capture Loop    │
              └─────────┬──────────┘
                        │ latest_raw_frame (shared)
               ┌────────┴────────┐
               │                 │
    ┌──────────▼──────┐   ┌─────▼───────────┐
    │ Thread 2: Knife │   │ Thread 3: Viol. │
    │  Model best.pt  │   │  Model best2.pt │
    │  (YOLOv11)      │   │  (YOLOv11)      │
    └──────────┬──────┘   └─────┬───────────┘
               │                │
               └────────┬───────┘
                        │ merged bounding boxes
              ┌─────────▼──────────┐
              │ Thread 4: GUI Poll │
              │ (Tkinter .after)   │
              │ Merges both results│
              │ onto single frame  │
              └─────────┬──────────┘
                        │
            ┌───────────▼────────────┐
            │   Alert Trigger Logic  │
            │  (Cooldown + Rate Cap) │
            └───────────┬────────────┘
                        │
          ┌─────────────┼──────────────┐
          │             │              │
   ┌──────▼──────┐ ┌───▼────┐ ┌──────▼──────┐
   │  Snapshot    │ │  Video │ │  Email      │
   │  Save + DB  │ │  Clip  │ │  Alert      │
   │  Logging    │ │  Record│ │  (SMTP/TLS) │
   └─────────────┘ └────────┘ └─────────────┘
```

---

## 🛠️ Tech Stack

| Category | Technology |
|:---|:---|
| **Language** | Python 3.10+ |
| **Object Detection** | YOLOv11 (Ultralytics) — `best.pt`, `best2.pt` |
| **Deep Learning Framework** | PyTorch 2.0+, TorchVision 0.15+ |
| **Computer Vision** | OpenCV 4.8+ |
| **GUI Framework** | Tkinter (built-in) + Pillow for image rendering |
| **Database** | SQLite3 (thread-safe with locking) |
| **Authentication** | bcrypt (password hashing) |
| **Email** | smtplib + MIME (SMTP with TLS) |
| **Concurrency** | Python `threading` — multi-threaded pipeline |
| **Profiling** | Custom `SpeedProfiler` with context manager API |

---

## 🤖 AI Models

### Model 1: `best.pt` — Harmful Object Detection (YOLOv11)
- **Architecture**: YOLOv11 (Ultralytics)
- **Task**: Detects knives, blades, and weapons in real-time
- **Confidence Threshold**: 0.55 (configurable)
- **Output**: Bounding boxes with class labels and confidence scores
- **Color**: 🟢 **Green** bounding boxes

### Model 2: `best2.pt` — Violence Detection (YOLOv11)
- **Architecture**: YOLOv11 (Ultralytics)
- **Task**: Classifies human activity as Violence or Non-Violence
- **Confidence Threshold**: 0.55 (configurable)
- **Output**: Bounding boxes distinguishing violent vs. non-violent behavior
- **Colors**: 🔴 **Red** = Violence, 🔵 **Blue** = Non-Violence

> **Note:** The project also includes a legacy **ResNet-18** violence classification model (`new_violence_model_finetuned_rwf.pth`) fine-tuned on the **RWF-2000** dataset, which performs frame-level temporal analysis using a rolling window buffer.

---

## 📁 Project Structure

```
Human Violence and Object Detection System/
│
├── main.py                        # 🚀 Entry point — launches Login → Dashboard
├── config.py                      # ⚙️ Central configuration (paths, thresholds, email, GUI)
├── requirements.txt               # 📦 Python dependencies
│
├── models/                        # 🤖 Trained AI model weights
│   ├── best.pt                    #    YOLOv11 — Knife/Object detection
│   ├── best2.pt                   #    YOLOv11 — Violence detection
│   └── new_violence_model_finetuned_rwf.pth  # ResNet-18 violence model (legacy)
│
├── ai_models/                     # 🧠 AI model wrappers & validation
│   ├── yolo_detector.py           #    YOLOv11 knife detection wrapper
│   ├── violence_detector.py       #    ResNet-18 violence detection wrapper
│   └── hrm_validator.py           #    Hierarchical Reasoning Model (false-positive reduction)
│
├── gui/                           # 🖥️ Tkinter GUI windows
│   ├── Integration.py             #    Single-webcam dual-YOLO live detection window
│   ├── admin_dashboard.py         #    Admin dashboard with sidebar navigation
│   ├── main_detection_window.py   #    Dual-panel detection window (webcam + video)
│   ├── login_window.py            #    Login form (Admin + Operator)
│   ├── register_window.py         #    Operator self-registration form
│   └── widgets.py                 #    Reusable styled UI components
│
├── services/                      # 🔧 Backend services
│   ├── alert_service.py           #    Alert coordination (dual-detection trigger)
│   ├── email_service.py           #    SMTP email with attachments
│   └── recording_service.py       #    5-second evidence video clip recorder
│
├── database/                      # 🗄️ Database layer
│   ├── db_manager.py              #    SQLite CRUD — users, operators, detections, alerts, recordings, snapshots
│   └── surveillance.db            #    SQLite database file
│
├── utils/                         # 🛠️ Utilities
│   ├── helpers.py                 #    Frame conversion, bounding box drawing, IoU, timestamps
│   ├── logger.py                  #    Logging setup with rotating file handlers
│   └── profiler.py                #    Speed profiler (context manager API)
│
├── alerts/                        # 📸 Auto-saved detection snapshots
├── recordings/                    # 🎬 Auto-recorded video clips
├── logs/                          # 📄 Application logs (app, object_detection, violence_detection)
│
├── tests/                         # 🧪 Test suite
│   ├── run_all_tests.py
│   ├── test_camera.py
│   ├── test_database.py
│   ├── test_email.py
│   ├── test_gui.py
│   ├── test_knife_detection.py
│   ├── test_login.py
│   ├── test_profiler.py
│   ├── test_recording.py
│   ├── test_registration.py
│   └── test_violence_detection.py
│
├── test_dashboard.py              # 🧪 Visual test runner dashboard (Tkinter)
└── webcam_violence_detect.py      # 🎥 Standalone webcam violence detection script
```

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.10+**
- **CUDA-enabled GPU** (recommended for real-time inference) or CPU
- **Webcam** connected to the system

### Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/<your-username>/Human-Violence-and-Object-Detection-System.git
   cd Human-Violence-and-Object-Detection-System
   ```

2. **Create a Virtual Environment (Recommended)**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Email Alerts** *(Optional)*
   
   Edit `config.py` and update the email settings:
   ```python
   EMAIL_SENDER   = "your_email@gmail.com"
   EMAIL_PASSWORD = "your_gmail_app_password"
   EMAIL_RECEIVER = "alert_recipient@gmail.com"
   ```
   > Use a [Gmail App Password](https://support.google.com/accounts/answer/185833) (not your regular password).

5. **Run the Application**
   ```bash
   python main.py
   ```

---

## 🖥️ Usage

### Login
- **Admin Login**: Username `admin`, Password `admin123` (default)
- **Operator Login**: Register first via the registration form, then log in with your credentials

### Detection Workflow
1. Log in as Admin or Operator
2. Click **▶ Start Detection** from the dashboard
3. The system opens the live detection window with your webcam
4. Both YOLOv11 models (`best.pt` + `best2.pt`) start processing the feed simultaneously
5. Detections appear as color-coded bounding boxes:
   - 🟢 **Green** — Knife/Object detected (`best.pt`)
   - 🔴 **Red** — Violence detected (`best2.pt`)
   - 🔵 **Blue** — Non-violence detected (`best2.pt`)
6. When threats are detected, **snapshots are auto-saved** and **email alerts are sent**

### Dashboard Features
- **View Alerts** — Browse detection history from the database
- **View Recordings** — Access recorded video clips
- **View Snapshots** — Image browser with double-click to open
- **Object/Violence Logs** — Detailed detection logs
- **Speed Profile** — Live per-stage performance timing

---

## 🧪 Testing

Run the visual **Test Dashboard** for comprehensive system testing:
```bash
python test_dashboard.py
```

Or run all tests from the command line:
```bash
python tests/run_all_tests.py
```

Test modules cover:
- Login & Authentication
- Camera access
- Knife Detection (YOLOv11)
- Violence Detection
- Email Service
- Database operations
- GUI components
- Recording Service
- Speed Profiler

---

## 👥 Contributors

| Name | Role |
|:---|:---|
| **Omkar** | Developer |

---

## 📜 License

This project was developed as an **academic Final Year Project**. All rights reserved by the contributors.

---

<p align="center">
  <b>Built with ❤️ using Python, YOLOv11, PyTorch & OpenCV</b>
</p>
