# 🌕 CHANDRA DRISHTI

**AI-Based Super-Resolution Hazard Mapping for Safe Lunar Landing**

> *"Vision Beyond the Lunar Horizon"*

**CHANDRA DRISHTI** is a lunar terrain-analysis system that uses advanced algorithmic super-resolution to transform 5m TMC lunar imagery into a 1m grid-spacing representation and generate a multi-hazard map for autonomous landing-site selection. 

TMC provides broad lunar coverage, while high-resolution OHRC data has limited coverage. Our approach aims to reduce this limitation by deriving high-resolution hazard information from widely available TMC data.

---

## ✨ Key Features

- **5m → 1m Super-Resolution:** Algorithmic upscaling (Lanczos4 + Unsharp Masking) for crisp hazard edge detection.
- **Slope Hazard Detection:** Identifies steep inclines >10° using DEM gradient processing.
- **Crater & Boulder Detection:** Detects craters >1m using PyTorch Faster R-CNN with MobileNetV3-FPN backbone.
- **Shadow Hazard Detection:** Dynamic thresholding to flag permanently shadowed regions.
- **Master Hazard Map:** Fuses all data layers into a single risk assessment map.
- **Strict 75% Safety Rule:** Automatically aborts missions if overall terrain safety drops below 75%.
- **Automatic Safe Landing-Zone Detection:** Pinpoints exact coordinates (X, Y) and calculates a safe radius using Euclidean Distance Transform (EDT).
- **Rover Path Planning:** Autonomously plots a straight-line post-landing exploration path to the nearest water-ice crater.

---

## ⚙️ How It Works (Pipeline)

```text
TMC 5m Ortho + DEM
        |
        v
 Super-Resolution
    5m → 1m
        |
        v
 +------+------+------+
 |      |      |      |
 v      v      v      v
Slope  Crater Shadow Pathfinding
 |      |      |      |
 +------+------+------+
        |
        v
 Master Hazard Map
        |
        v
 Terrain Safety %
        |
   +----+----+
   |         |
   v         v
  ≥75%      <75%
   |         |
   v         v
 Accept    Abort
 Landing   Mission
   |
   v
Safe Zone + Radius
```

*The 75% Safety Rule accepts a landing zone only when overall terrain safety is at least 75%; otherwise, the primary landing zone is rejected and contingency zones are evaluated.*

---

## 🛠️ Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python** | Core backend processing |
| **PyTorch** | Deep Learning object detection |
| **Faster R-CNN & MobileNetV3-FPN** | Fast, lightweight crater/boulder detection backbone |
| **OpenCV** | Advanced algorithmic super-resolution (Lanczos4) and image processing |
| **Rasterio / NumPy** | Geo-raster and numerical mathematical matrix processing |
| **Flask / REST API** | Decoupled backend communication |
| **Vanilla JavaScript / CSS / HTML** | Zero-dependency, high-performance tactical frontend |
| **Euclidean Distance Transform (EDT)**| Safe-Zone Search algorithm |

---

## 📁 Repository Structure

```text
CHANDRA-DRISHTI/
│
├── CODE_SIH1519_ORION SPACE SYSTEM/
│   ├── backend/
│   │   ├── server.py             # Flask API, ML Inference, Image Processing
│   │   └── models/               # PyTorch Weights (if applicable)
│   ├── frontend/
│   │   ├── index.html            # Tactical UI
│   │   ├── style.css             # Sci-Fi / Cyber CSS Styles
│   │   └── script.js             # API communication and DOM manipulation
│   ├── demo_safe/                # Test datasets
│   └── demo_abort/               # Test datasets for failure scenarios
│
├── README.md
└── requirements.txt
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/asthagupta0211/CHANDRA-DRISHTI.git
cd CHANDRA-DRISHTI
```

### 2. Create Environment
```bash
python -m venv venv
```
**Windows:**
```bash
venv\Scripts\activate
```
**Linux/macOS:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Backend Server
```bash
python "CODE_SIH1519_ORION SPACE SYSTEM/backend/server.py"
```

### 5. Launch the UI
You must host the frontend to avoid browser CORS issues. Open a new terminal and run:
```bash
cd "CODE_SIH1519_ORION SPACE SYSTEM/frontend"
python -m http.server 8000
```
Then navigate to `http://localhost:8000` in your web browser.

---

## 🎯 Expected Output

The system targets near-real-time processing, generating a multi-layered response:

1. **1m Terrain Map**
2. **Slope Map** (Binarized gradient hazards)
3. **Crater/Boulder Map** (Bounding boxes and confidence intervals)
4. **Shadow Map** (Illumination hazards)
5. **Master Hazard Map** (Fused data)
6. **Safety Score** (%)
7. **Safe Landing Zone** (X, Y, Radius)
8. **Rover Post-Landing Path** (Trajectory and distance to nearest crater)

---

## 🛰️ Data Sources

- **Chandrayaan-2 TMC-2** — 5m DEM & Ortho imagery
- **Chandrayaan-2 OHRC** — 25cm benchmark data
- **NASA LROC NAC** — High-resolution validation data

---

## 👥 Team — CHANDRA DRISHTI

**Smart India Hackathon 2026**

- **Deepanshu Kumar** — Team Leader
- Astha Gupta
- Sheetal R Odedra
- Darshan Bhawsar
- Gajendra Sharma
- Prabhash Kumar Yadav

---

## 🔮 Future Scope

- Real-time onboard deployment hardware integration.
- Extension of super-resolution using advanced Generative Adversarial Networks (GANs).
- Multi-modal terrain fusion incorporating thermal and spectral data.
- Autonomous descent optimization based on real-time LIDAR.
- Rover navigation integration utilizing live landing zone telemetry.
- Extension to Mars and asteroid landing missions.
