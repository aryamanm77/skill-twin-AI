# SkillTwin AI

> **"We don't replace the expert. We capture the expert's skill and make it teachable, measurable and repeatable."**

AI-Powered Practical Skill Training & Assessment Platform

---

## ⚠ Honest Product Statement

SkillTwin AI is an **AI-assisted assembly training and skill-transfer prototype** for controlled workstation procedures.

**This system does NOT claim:**
- Universal procedure understanding
- Perfect human action recognition  
- Perfect 3D reconstruction from a single webcam
- Industrial safety certification
- Automatic understanding of every profession

**This system DOES provide:**
- Zone-based, FSM-driven step recognition (explicit and debuggable)
- Real YOLO object detection + ByteTrack object tracking
- Measurable skill scores from actual observation data
- 3D digital twin (approximate spatial representation, not true 3D)
- Privacy-first local processing

---

## 🏗 Architecture

```
Camera (Real/Test/Video)
    ↓
OpenCV frame capture
    ↓
Ultralytics YOLO v8 (object detection)
    ↓
ByteTrack (object tracking)
    ↓
Zone Checker (workspace zone membership)
    ↓
Procedure FSM (step recognition — zone + motion based)
    ↓
Expert/Trainee Comparator (sequence, object, position, timing, movement)
    ↓
Skill Scorer (weighted, transparent, measurement-based)
    ↓
FastAPI + WebSocket
    ↓
React Dashboard (Live feed | 3D Twin | Analytics)
```

---

## 📁 Project Structure

```
skilltwin-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes + WebSocket
│   │   ├── vision/       # Camera + YOLO detector + pipeline
│   │   ├── tracking/     # Object tracker
│   │   ├── calibration/  # Homography + zone system
│   │   ├── procedure_engine/ # FSM + loader + comparator
│   │   ├── scoring/      # Skill score computation
│   │   ├── database/     # SQLAlchemy models + CRUD
│   │   ├── hardware/     # ESP32 serial integration
│   │   └── core/         # Config + security
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/   # UI components
│       ├── pages/        # Dashboard, Training, History
│       ├── three/        # Three.js digital twin
│       ├── hooks/        # WebSocket hook
│       ├── services/     # API service layer
│       ├── store/        # Zustand state stores
│       └── types/        # TypeScript types
├── config/
│   ├── domains.json
│   └── procedures/
│       └── basic_assembly.json
├── data/                 # SQLite DB + expert profiles
├── models/               # YOLO weights (auto-downloaded)
├── tests/                # pytest test suite
└── scripts/              # Start scripts
```

---

## 🚀 Installation

### Prerequisites

- Python 3.11+ (tested on 3.15.0b4)
- Node.js 18+ (tested on v24.19.0)
- Git

### Backend Setup

```powershell
# Navigate to project
cd d:\QRFileTransfer\skilltwin-ai\backend

# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend Setup

```powershell
cd d:\QRFileTransfer\skilltwin-ai\frontend
npm install
```

---

## 🏃 Running the Application

### Start Backend

```powershell
cd d:\QRFileTransfer\skilltwin-ai\backend
.\venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the script:
```
scripts\start_backend.bat
```

Backend will be available at: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

### Start Frontend

```powershell
cd d:\QRFileTransfer\skilltwin-ai\frontend
npm run dev
```

Or use the script:
```
scripts\start_frontend.bat
```

Frontend: `http://localhost:5173`

---

## 🔑 Demo Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Expert | `expert` | `expert123` |
| Trainee | `trainee` | `trainee123` |

---

## 📷 Camera Modes

### TEST MODE (Default — No Camera Required)

The application starts in TEST MODE by default:
- Generates synthetic animated frames
- Produces synthetic YOLO-like detections
- Clearly labeled: `⚠ SIMULATION / TEST MODE`
- Full pipeline runs — FSM, scoring, 3D twin all work
- Safe for development without any physical hardware

### REAL MODE — Laptop Webcam

1. On the Training page, select **"Real Camera"**
2. Click **Start Session**
3. Allow browser webcam access if prompted
4. YOLO model auto-downloads (~6MB) on first use

### VIDEO FILE MODE

1. Select **"Video File"** camera mode
2. Provide path to an MP4/AVI file in the camera_source field

---

## 🎯 YOLO Model Setup

The system uses `yolov8n.pt` (COCO-class, nano model).

**Auto-download**: The model downloads automatically on first real-mode run.

**Manual download**:
```python
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
```

**COCO classes used** (mapped to procedure objects):
- Component A → `bottle`, `cup`, `bowl`  
- Component B → `remote`, `mouse`, `cell phone`
- Component C → `book`, `laptop`, `keyboard`
- Tool → `scissors`, `knife`, `fork`

> For real factory parts, train a custom YOLO model on your components and update `config/procedures/basic_assembly.json` → `objects[].yolo_classes`.

---

## 📐 Workspace Calibration

1. Start the backend
2. Navigate to Settings → Calibration (or use API)
3. Click 4 corners of your physical workstation in the live feed
4. Click "Save Calibration"
5. Workspace coordinates are now calibrated

**Without calibration**: The system uses normalized pixel coordinates (still fully functional).

**API**:
```http
POST /api/calibration
{
  "procedure_id": "basic_assembly",
  "points": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
  "frame_width": 1280,
  "frame_height": 720
}
```

---

## 👁 Recording an Expert Session

1. Log in as **expert** or **admin**
2. Go to **Training** page
3. Select procedure: `Basic Component Assembly`
4. Select mode: **Expert**
5. Click **Start Expert Session**
6. Perform the procedure in front of the camera:
   - Step 1: Pick up Component A from its source zone
   - Step 2: Move Component A toward assembly zone
   - Step 3: Place Component A in the assembly zone
   - Step 4: Pick up Component B
   - Step 5: Place Component B in the assembly zone
   - Step 6: Use the tool in the assembly zone
   - Step 7: Complete
7. Click **Stop Session**
8. Expert profile is saved automatically

---

## 🎯 Running Trainee Mode

1. Log in as **trainee**
2. Ensure expert profile exists (green indicator)
3. Select mode: **Trainee**
4. Click **Start Trainee Session**
5. Perform the procedure
6. System automatically:
   - Detects current step (no manual advancement)
   - Compares to expert profile
   - Shows live score
   - Detects deviations
7. Click **Stop Session** to see final report

---

## 🧪 Running Tests

```powershell
cd d:\QRFileTransfer\skilltwin-ai\backend
.\venv\Scripts\activate
python -m pytest ..\tests\ -v
```

Or:
```
scripts\run_tests.bat
```

### Test coverage:
- `test_procedure.py` — FSM transitions, step recognition
- `test_scoring.py` — Score computation, determinism
- `test_calibration.py` — Homography math, zone logic
- `test_comparator.py` — Wrong-object detection, timing, trajectory
- `test_database.py` — CRUD operations, session lifecycle

---

## 🔌 ESP32 Integration (Optional)

### Hardware

- ESP32 board with USB serial
- Green LED on GPIO pin (configurable)
- Red LED on GPIO pin (configurable)
- Optional buzzer

### Setup

1. Flash simple serial listener to ESP32:
```cpp
void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'G') { /* Green LED on */ }
    if (cmd == 'R') { /* Red LED on */ }
    if (cmd == 'B') { /* Buzzer */ }
    if (cmd == '0') { /* All off */ }
  }
}
```

2. Find serial port (e.g., `COM3`)

3. Update environment:
```
ESP32_PORT=COM3
ESP32_ENABLED=true
```

4. Restart backend

### Without ESP32

The system runs in **simulation mode** — serial commands are printed to console.

---

## 🔒 Privacy

- **No face recognition** — system uses object tracking only
- **No raw video stored** by default — only derived skill metrics
- **All processing is local** — no cloud API calls
- **Anonymous session IDs** — no facial identity stored
- Privacy indicator visible in sidebar

---

## ❗ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in venv |
| Camera won't open | Use TEST MODE; check camera index in `.env` |
| YOLO not loading | Run in TEST MODE; YOLO downloads on first REAL mode use |
| WebSocket disconnected | Check backend is running on port 8000 |
| Score is 0 | Make sure expert profile exists before trainee session |
| No detections in real mode | YOLO model may still be loading; wait 5-10 seconds |
| Frontend won't build | Run `npm install` again; check Node version ≥ 18 |

---

## 🚧 Known Limitations

1. **Action recognition accuracy** depends on object being visible to camera and YOLO confidence threshold
2. **Zone detection** is approximate — based on normalized pixel coordinates
3. **3D digital twin** is an approximate 2D-to-3D projection, NOT true 3D reconstruction
4. **One COCO model** used — custom factory objects need custom-trained YOLO
5. **No audio feedback** — ESP32 or screen only
6. **Single camera** — no multi-angle depth estimation

---

## 🔮 Future Improvements

- [ ] Custom YOLO model training interface
- [ ] Multi-camera support for better 3D estimation
- [ ] Advanced action recognition with pose estimation
- [ ] PostgreSQL migration (database layer is already designed for it)
- [ ] Mobile app for trainee recording
- [ ] Procedure Builder full UI
- [ ] Analytics charts page
- [ ] Video recording export (privacy-opt-in)
- [ ] Multi-language support
- [ ] Cloud sync (optional)
