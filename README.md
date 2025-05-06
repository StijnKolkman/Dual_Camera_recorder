# Dual Camera Recorder

This repository provides a complete pipeline for synchronized dual-camera recording, object tracking, and 3D trajectory reconstruction.

## Table of Contents

* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Usage](#usage)

  * [Full pipeline (main.py)](#full-pipeline-mainpy)
  * [Generating motor velocity input](#generating-motor-velocity-input)
* [Modules](#modules)

  * [Recorder](#recorder)
  * [Tracker](#tracker)
  * [Trajectory Generator](#trajectory-generator)
* [Running Modules Separately](#running-modules-separately)
* [File Structure](#file-structure)
* [License](#license)

---

## Prerequisites

* **Git** (>=2.0)
* **Python** (>=3.8, <3.13) 

> All dependencies are listed in `requirements.txt` and can be installed in one step during setup.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/StijnKolkman/Dual_Camera_recorder.git
   cd Dual_Camera_recorder
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\Activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### Full pipeline (`main.py`)

This will launch the GUI recorder, then automatically run tracking and trajectory reconstruction when recording finishes.

```bash
python main.py
```

*(Ensure `main.py` is configured with your desired default file/folder names.)*

### Generating motor velocity input

Prepare and customize a motor velocity profile for your recorder.

```bash
python motorvelocityinput.py
```

* **Default settings** (maximum frequency, relative increase flag, motor connection, node/USB IDs, acceleration) are defined in the `__main__` instantiation at the bottom of `MotorVelocityInput.py`.
* To adjust behavior (e.g., change `maximumFrequency` or disable relative increases), edit the parameters passed to `MotorVelocityInput(...)` before running.

---

## Modules

### Recorder

* **Script:** `RecorderClassV2.py`
* **Description:** GUI application for simultaneous dual-camera capture.
* **How to run:**

  ```bash
  python RecorderClassV2.py
  ```
* **Outputs (in `<filename>/` folder):**

  * `<filename>_cam1.avi`  — left camera video
  * `<filename>_cam2.avi`  — right camera video
  * `<filename>_timestamps.csv`  — timestamps per frame

### Tracker

* **Script:** `TrackerClassV3.py`
* **Description:** Contour‑based ROI tracker with Otsu thresholding.
* **How to run:**

  ```bash
  python TrackerClassV3.py <path/to>/<filename>_cam1.avi
  ```

  *(It will prompt you to select the world‐scale box and the object ROI.)*
* **Outputs (in same folder):**

  * `<filename>_box.csv`  — box coordinates for scaling
  * `<filename>_locations.csv`  — frame‐by‐frame X,Y,angle
  * `<filename>_tracking.avi`  — annotated tracking video

### Trajectory Generator

* **Script:** `TrajectoryClassV5.py`
* **Description:** Converts dual‐view tracking CSVs into a 3D trajectory using pinhole‑camera geometry.
* **How to run:**

  ```bash
  python TrajectoryClassV5.py <path/to>/<filename>_cam1_locations.csv <path/to>/<filename>_cam2_locations.csv
  ```
* **Outputs (in same folder):**

  * `<filename>_Trajectory.csv`  — timestamped X,Y,Z in mm
  * Plots: 3D trajectory, 2D projections, and velocity over time

---

## Running Modules Separately

1. **Recorder only**

   ```bash
   python RecorderClassV2.py
   ```

2. **Tracker only**

   ```bash
   python TrackerClassV3.py data/Recording_cam1.avi
   ```

3. **Trajectory Generator only**

   ```bash
   python TrajectoryClassV5.py data/Recording_cam1_locations.csv data/Recording_cam2_locations.csv
   ```

---

## File Structure

```
Dual_Camera_recorder/
├── RecorderClassV2.py
├── TrackerClassV3.py
├── TrajectoryClassV5.py
├── main.py                # orchestrates recording → tracking → trajectory
├── motorvelocityinput.py  # generate motor velocity profiles
├── requirements.txt
├── .gitignore
└── LICENSE                # MIT License
```

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
