import os
import tempfile
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'matplotlib'))

import numpy as np
import matplotlib.pyplot as plt
import sqlite3

MOLA_FILE = "mola_elevation_megt90n000eb.img"
DB_FILE = "mars_data.db"

if not os.path.exists(MOLA_FILE):
    print(f"Error: {MOLA_FILE} not found. Run mola.py first.")
    exit(1)

print("Loading MOLA elevation data for Landing Site Selection Analysis...")
# MOLA grid: 2880 rows (-90 to +90 lat) x 5760 cols (0 to 360 lon)
elev = np.fromfile(MOLA_FILE, dtype='>i2').reshape((2880, 5760)).astype(np.float32)

# 1. Slope / Hazard Calculation
print("Calculating terrain slope hazards...")
dy, dx = np.gradient(elev)
slope = np.sqrt(dx**2 + dy**2)

# 2. Planetary Engineering Constraints for Safe Rover Landing:
# - Elevation constraint: Elevation < -1,400 m (sufficient atmospheric density for entry parachute)
# - Slope constraint: Low slope (below 60th percentile of slopes to avoid steep cliffs/boulders)
# - Latitude constraint: Equatorial / mid-latitude belt (-35° to +35°) for solar energy and thermal management
print("Applying planetary mission engineering constraints...")
slope_threshold = np.percentile(slope, 60)
elev_threshold = -1400.0  # meters relative to Mars datum

# Latitude grid (-90 to +90)
lats = np.linspace(90, -90, 2880)[:, None]
lat_mask = np.abs(lats) <= 35.0

# Boolean mask of candidate safe landing zones
safe_zones = (elev < elev_threshold) & (slope < slope_threshold) & lat_mask

# 3. Known Successful Robotic Landing Sites on Mars (Name, Lat, Lon_East, Agency, Year)
landing_missions = [
    ("Viking 1", 22.48, 312.05, "NASA", 1976),
    ("Pathfinder / Sojourner", 19.33, 326.45, "NASA", 1997),
    ("Opportunity", -1.95, 354.47, "NASA", 2004),
    ("Curiosity (Gale)", -4.59, 137.44, "NASA", 2012),
    ("InSight", 4.50, 135.62, "NASA", 2018),
    ("Perseverance (Jezero)", 18.38, 77.58, "NASA", 2021),
    ("Zhurong (Utopia)", 25.07, 109.93, "CNSA", 2021),
]

# 4. Generate Visualization Map
print("Generating Mission Landing Zone Map...")
fig, ax = plt.subplots(figsize=(15, 8))

# Background: semi-transparent MOLA topography
ax.imshow(elev, cmap='gray', extent=[0, 360, -90, 90], aspect='auto', alpha=0.55)

# Overlay Safe Landing Candidate Zones in Green
safe_display = np.ma.masked_where(~safe_zones, np.ones_like(safe_zones, dtype=float))
ax.imshow(safe_display, cmap='summer', extent=[0, 360, -90, 90], aspect='auto', alpha=0.45)

# Plot rover landing sites
for name, lat, lon, agency, yr in landing_missions:
    # Convert lon to 0-360
    lon_e = lon % 360.0
    r = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
    c = int(np.clip(lon_e * 16.0, 0, 5759))
    site_elev = elev[r, c]
    site_slope = slope[r, c]
    is_safe = safe_zones[r, c]

    ax.scatter(lon_e, lat, color='red', edgecolor='white', s=90, zorder=5)
    ax.annotate(
        f"{name} ({yr})\n{site_elev:.0f}m",
        xy=(lon_e, lat),
        xytext=(lon_e + 3, lat + 3),
        fontsize=8.5,
        fontweight='bold',
        color='yellow',
        bbox=dict(boxstyle="round,pad=0.2", fc="black", alpha=0.7, ec="white", lw=0.5),
        zorder=6
    )

ax.set_title("NASA / Planetary Science: Mars Rover Landing Sites & Safe Landing Corridor", fontsize=13, pad=12)
ax.set_xlabel("Longitude (Degrees East)", fontsize=11)
ax.set_ylabel("Latitude (Degrees)", fontsize=11)
ax.set_xlim(0, 360)
ax.set_ylim(-90, 90)
ax.axhline(35, color='cyan', linestyle=':', lw=1.2, label='Latitude Corridor (±35°)')
ax.axhline(-35, color='cyan', linestyle=':', lw=1.2)

# Custom legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='lightgreen', alpha=0.5, label='Safe Landing Corridor (Elev < -1.4km, Low Slope, |Lat| ≤ 35°)'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=9, label='Historical Landing Sites')
]
ax.legend(handles=legend_elements, loc='lower left', framealpha=0.9)

output_png = "mars_landing_zones_map.png"
plt.savefig(output_png, dpi=180, bbox_inches='tight')
plt.close(fig)
print(f"Landing site analysis map saved to: {output_png}")

# 5. Store mission landing evaluations to SQLite database
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute('''
    CREATE TABLE IF NOT EXISTS mission_landing_sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_name TEXT,
        agency TEXT,
        launch_year INTEGER,
        latitude REAL,
        longitude REAL,
        elevation_meters REAL,
        slope_index REAL,
        safe_corridor_candidate BOOLEAN
    )
''')
cur.execute("DELETE FROM mission_landing_sites")

for name, lat, lon, agency, yr in landing_missions:
    lon_e = lon % 360.0
    r = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
    c = int(np.clip(lon_e * 16.0, 0, 5759))
    site_elev = float(elev[r, c])
    site_slope = float(slope[r, c])
    is_safe = bool(safe_zones[r, c])
    
    cur.execute('''
        INSERT INTO mission_landing_sites 
        (mission_name, agency, launch_year, latitude, longitude, elevation_meters, slope_index, safe_corridor_candidate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, agency, yr, lat, lon_e, site_elev, round(site_slope, 2), is_safe))

conn.commit()
print("\n--- Evaluated Robotic Landing Sites in mars_data.db ---")
cur.execute("SELECT mission_name, launch_year, latitude, longitude, elevation_meters, safe_corridor_candidate FROM mission_landing_sites")
for row in cur.fetchall():
    status = "QUALIFIES (Safe Corridor)" if row[5] else "Challenging / Custom Terrain"
    print(f"• {row[0]} ({row[1]}): Lat {row[2]}°, Lon {row[3]:.1f}°E | Elev: {row[4]:,.0f} m => {status}")

conn.close()
print("\nMission analysis completed successfully!")
