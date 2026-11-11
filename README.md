# 🪐 Interplanetary Survival Guide: Martian Map
> **NASA Space Apps Challenge Entry**  
> *A dual-purpose interactive mapping application bridging deep-space astronaut operational logistics with student STEM space research, enhanced with theoretical antigravity mechanics.*

---

## 🚀 Executive Summary
"**Interplanetary Survival Guide: Martian Map**" addresses one of the most fundamental hurdles of permanent human settlement on Mars: **terrain traversal hazards and heavy-payload logistics in extreme extraterrestrial geography.** 

By fusing real NASA datasets (**MOLA 16 pix/deg global elevation**, **4.2 GB HiRISE 50 cm/pixel surface photography**) with **theoretical antigravity and diamagnetic levitation mechanics**, the platform delivers:
1. **Operational Mission Control for Astronauts**: Traversal route planning comparing conventional wheeled rovers against frictionless antigravity glide corridors, monitoring active **Gravity-Manipulation Zones (GMZs)** for habitat construction, and inspecting real-time surface imagery.
2. **Interactive Student Research Lab**: A physics simulation sandbox enabling students to manipulate gravity fields ($1.0g$ Earth vs. $0.38g$ Mars vs. $0.05g$ Antigravity Field), calculate payload transport work ($W = m \cdot g \cdot h$), and explore Martian survival challenges.

---

## 🛠 Tech Stack & Architecture

- **Backend**: Python 3, Flask RESTful API, SQLite (`mars_data.db`), NumPy (MOLA raster gradient and slope analysis).
- **Frontend**: Leaflet.js (Mars web mapping & custom coordinate projections), Tailwind CSS (futuristic dark HUD UI), Chart.js (dynamic physics visualization).
- **NASA Datasets Integrated**:
  - **MOLA Global Topography Grid** (`mola_elevation_megt90n000eb.img`): High-precision elevation, slope hazard calculation ($>15^\circ$ danger zones), and barometric pressure scale height calculations.
  - **NASA HiRISE 4.2 GB Archive** (`archive mars surface images.zip`): 2,182 high-resolution captioned surface photographs with exact Mars coordinates, streamed dynamically on-demand without local storage overhead.

---

## ⚡ Antigravity Integration

### 1. Operational Traversal Routing (Wheeled Rover vs. Antigravity Glider)
Conventional Martian rovers (such as *Curiosity* or *Perseverance*) are physically restricted to slopes below $15^\circ$ and maximum speeds of $\sim 0.15\text{ km/h}$, forcing them to take tortuous detours around crater rims and boulder fields.
- **Antigravity Glide Corridors**: By operating at an effective gravitational acceleration of $g_{\text{eff}} = 0.05g$ with zero surface rolling resistance, next-generation vehicles traverse directly across impassable chasms (e.g., the 7,000-meter vertical cliffs of Valles Marineris) at $16.5\text{ km/h}$.
- **Diagnostic Metrics**: Distance reduced by up to **85%**, transit time reduced by **98%**, and propulsion energy expenditure cut by **88–93%**.

### 2. Gravity-Manipulation Zones (GMZs)
Strategic surface outposts equipped with high-gradient diamagnetic / metric field generators:
- **GMZ-Alpha (Jezero Delta)**: Modular habitat construction (relocating 42-ton domes with an effective felt weight of only 2,100 kg).
- **GMZ-Beta (Valles Marineris)**: Vertical cliff elevator corridor bypassing 7-km sheer rock walls.
- **GMZ-Gamma (Olympus Mons Caldera)**: High-altitude astronomical sensor stabilization in near-vacuum volcanic rim.
- **GMZ-Delta (Arcadia Planitia)**: Subsurface glacial ice sheet extraction preventing heavy equipment from sinking into thawing mud.
- **GMZ-Epsilon (Hellas Basin)**: Atmospheric cosmic-ray radiation bunker ceiling placement.

### 3. Student Physics Simulation Sandbox
Allows students to experiment with extraterrestrial physics:
$$\text{Weight } W = m \cdot g_{\text{eff}}$$
$$\text{Lifting Work } W = m \cdot g_{\text{eff}} \cdot h$$
$$\text{Vertical Jump Height } h_{\text{jump}} = \frac{v_0^2}{2 \cdot g_{\text{eff}}}$$
- Students discover that on Mars under a $0.05g$ antigravity field, a single human astronaut can lift a multi-ton habitat module and jump over 8 meters into the air with an 11-second hang time!

---

## 💻 Running the Platform Locally

1. **Activate Environment & Dependencies**:
   ```bash
   pip install flask numpy pillow
   ```

2. **Launch the Mission Platform**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000)

4. **Run Verification Test Suite**:
   ```bash
   python test_app.py
   ```

---

## 🛰 Project Verification Checklist
- [x] Dual-purpose mode switcher (Astronaut Operations vs. Student Lab).
- [x] Interactive Leaflet.js Martian coordinate system with MOLA elevation inspector.
- [x] On-demand streaming of 2,182 HiRISE images from the 4.2 GB archive.
- [x] Antigravity routing engine comparing Wheeled vs. Antigrav transit corridors.
- [x] Active GMZ infrastructure mapping with real-time heavy-lift queues.
- [x] Interactive Student Gravity Sandbox with Chart.js visualization.
