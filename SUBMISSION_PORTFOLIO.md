# 🚀 NASA Space Apps Challenge Submission Kit
## Project: Interplanetary Survival Guide: Martian Map

---

## 📋 Executive Overview

* **Project Title:** Interplanetary Survival Guide: Martian Map
* **Category / Challenge:** Planetary Exploration, Interactive Web Mapping, and STEM Space Education
* **Tech Stack:** Python 3, Flask, Leaflet.js, Tailwind CSS, Chart.js, SQLite, NumPy
* **NASA Datasets Used:**
  * **NASA MOLA (Mars Orbiter Laser Altimeter):** 16 pixels/degree global elevation grid (`mola_elevation_megt90n000eb.img`) for real-time elevation, slope hazard gradients ($>15^\circ$ danger zones), and barometric pressure calculations.
  * **NASA HiRISE (High Resolution Imaging Science Experiment):** 4.2 GB dataset featuring 2,182 high-resolution (50 cm/pixel) surface images with exact Martian coordinates and official planetary science captions.
  * **Mars Reconnaissance Orbiter (MRO) CTX Imagery:** Context orbital strip and surface crop data.

---

## 💡 The Pitch (Copy-Paste for Submission Form)

### High-Level Summary (Short Description)
> **"Interplanetary Survival Guide: Martian Map"** is a dual-purpose web platform designed to solve extraterrestrial surface logistics. For astronauts, it provides operational task mapping and theoretical antigravity routing to bypass hazardous Martian terrain. For students, it provides an interactive space research lab simulating gravity physics, payload transport, and planetary survival challenges.

### Full Project Description
> Landing humans on Mars is only half the battle; surviving and building permanent infrastructure across rugged, hostile terrain is the true challenge. Conventional rovers are limited to speeds under $0.2\text{ km/h}$ and slopes under $15^\circ$, making geographic features like the 7,000-meter cliffs of Valles Marineris or crater rims insurmountable obstacles.
>
> Our platform bridges cutting-edge mission operations with public STEM engagement:
> 1. **Astronaut Operational Mapping:** Integrates real NASA MOLA topography and a theoretical antigravity routing engine. By modeling next-generation diamagnetic levitation vehicles operating at an effective gravity of $0.05g$, astronauts can calculate frictionless direct glide corridors, saving over **88% to 93% of transit energy** and reducing multi-week journeys to mere hours.
> 2. **Gravity-Manipulation Zones (GMZs):** Visualizes localized construction fields where multi-ton habitat domes (e.g., 42,000 kg) are reduced to an effective weight of 2,100 kg, enabling rapid regolith berm construction without tipping cranes.
> 3. **Student Space Research Lab:** An educational physics sandbox where students toggle between Earth ($1.0g$), Mars ($0.38g$), and Antigravity ($0.05g$) to calculate work done ($W = m \cdot g \cdot h$), test human jump heights (up to 8 meters!), and explore real 50 cm/pixel HiRISE surface photos.

---

## 🎬 2-Minute Demo Video Script (For Your Recording)

| Timestamp | Visual on Screen | Voiceover / Narration |
| :--- | :--- | :--- |
| **0:00 - 0:20** | Fullscreen view of the Martian Map showing glowing GMZ circles and landing sites | *"Welcome to the Interplanetary Survival Guide: Martian Map. Our mission solves the critical challenges of Martian surface logistics and education by combining real NASA planetary datasets with theoretical antigravity mechanics."* |
| **0:20 - 0:50** | Zoom in on the **Antigravity Traversal Planner**; select *Valles Marineris Crossing* | *"In our Astronaut Operations center, mission planners face the 7,000-meter vertical abyss of Valles Marineris. A conventional rover must detour 1,240 km around the canyon rim, taking over 800 hours. With our Antigravity Glide Corridor, the craft glides directly across the 185 km chasm in just 12 hours—saving 93% of energy."* |
| **0:50 - 1:15** | Click on **GMZ-Alpha** at Jezero Crater, then click a green **HiRISE camera icon** | *"We highlight Gravity-Manipulation Zones where heavy lifting fields reduce a 42-ton habitat dome to just 2,100 kg. Clicking on any camera pin instantly streams a real 50 cm/pixel NASA HiRISE orbital photograph and scientific explanation directly from our 4.2 GB archive."* |
| **1:15 - 1:45** | Click the **Student Research Lab** button in the header; drag the Payload Slider | *"For students, the platform transforms into an interactive physics laboratory. Students can adjust payload mass and instantly compare the weight in Newtons between Earth, Mars, and Antigravity fields. Under 0.05g assistance, an astronaut can leap 8 meters high with an 11-second hang time."* |
| **1:45 - 2:00** | Pan out to the global view of Mars showing the telemetry bar | *"By bridging deep-space operational logistics with interactive STEM education, the Interplanetary Survival Guide equips the next generation of space explorers. Thank you."* |

---

## ❓ Judge Q&A Preparation

**Q: Why incorporate theoretical antigravity into a NASA Space Apps project?**  
*A: "NASA's mission has always been to push the frontiers of physics and conceptual engineering. Theoretical concepts like diamagnetic levitation and negative energy spacetime metric modifications are actively explored in advanced physics literature. Integrating them into a real MOLA elevation model grounds theoretical science into actionable engineering scenarios, demonstrating how future physics could revolutionize planetary logistics while inspiring students in STEM."*

**Q: How is the 4.2 GB HiRISE dataset handled efficiently?**  
*A: "Rather than decompressing gigabytes of data, our Flask backend uses high-speed streaming directly out of the raw archive on-demand, indexing 2,182 observations into SQLite by Martian latitude and longitude. For cloud deployments, we included an automated lightweight fallback cache so the web app runs anywhere in milliseconds."*

---

## 🌐 How to Push to GitHub & Deploy

### 1. Push to GitHub
1. Create a new repository on your GitHub account named: `interplanetary-survival-guide-martian-map`
2. Run in terminal:
   ```powershell
   git remote add origin https://github.com/<YOUR_USERNAME>/interplanetary-survival-guide-martian-map.git
   git branch -M main
   git push -u origin main
   ```

### 2. Deploy to Render / Railway / Vercel
* **On Render / Railway:** Connect your GitHub repository. The included [`Procfile`](file:///f:/nasa.data/Procfile) (`web: gunicorn wsgi:app`) and [`requirements.txt`](file:///f:/nasa.data/requirements.txt) will automatically build and deploy your app live with a public URL!
* **On Vercel:** The included [`vercel.json`](file:///f:/nasa.data/vercel.json) configures `@vercel/python` serverless routing out-of-the-box.
