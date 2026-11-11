import os
import tempfile
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'matplotlib'))

import numpy as np
import matplotlib.pyplot as plt

MOLA_FILE = "mola_elevation_megt90n000eb.img"

if not os.path.exists(MOLA_FILE):
    print(f"Missing {MOLA_FILE}. Run mola.py first.")
    exit(1)

print("Loading MOLA elevation data for advanced terrain analysis...")
elev_grid = np.fromfile(MOLA_FILE, dtype='>i2').reshape((2880, 5760)).astype(np.float32)

def coord_to_indices(lat, lon):
    row = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
    col = int(np.clip((lon % 360.0) * 16.0, 0, 5759))
    return row, col

# =====================================================================
# 1. SHADED RELIEF (HILLSHADE): Olympus Mons & Tharsis Volcanic Region
# =====================================================================
print("\n--- Generating Shaded Relief for Olympus Mons ---")
# Region bounds around Olympus Mons: Lat 10°N to 26°N, Lon 215°E to 238°E
r_top, c_left = coord_to_indices(26.0, 215.0)
r_bot, c_right = coord_to_indices(10.0, 238.0)

olympus_dem = elev_grid[r_top:r_bot, c_left:c_right]

# Compute gradient / slopes (16 pixels/degree ≈ 3,710 m/pixel at Mars equator)
cell_size = 3710.0
dy, dx = np.gradient(olympus_dem, cell_size)
slope = np.arctan(np.sqrt(dx**2 + dy**2))
aspect = np.arctan2(-dx, dy)

# Sun lighting parameters (Sun from North-West at 45° angle)
sun_azimuth = np.radians(315.0)
sun_altitude = np.radians(45.0)

hillshade = (
    np.sin(sun_altitude) * np.cos(slope) +
    np.cos(sun_altitude) * np.sin(slope) * np.cos(sun_azimuth - aspect)
)
hillshade = np.clip(hillshade, 0, 1)

# Composite figure: Colormapped elevation blended with shaded relief
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Shaded Relief
im1 = ax1.imshow(hillshade, cmap='gray', extent=[215, 238, 10, 26])
ax1.set_title("Olympus Mons: Analytical Hillshade (Sun Azimuth 315°, Alt 45°)", fontsize=11)
ax1.set_xlabel("Longitude (°E)")
ax1.set_ylabel("Latitude (°N)")

# Blended Topography
im2 = ax2.imshow(olympus_dem, cmap='magma', extent=[215, 238, 10, 26])
ax2.imshow(hillshade, cmap='gray', alpha=0.35, extent=[215, 238, 10, 26])
cbar = plt.colorbar(im2, ax=ax2, label="Elevation (meters)")
ax2.set_title("Olympus Mons: Shaded Topographic Relief (Peak ~21 km)", fontsize=11)
ax2.set_xlabel("Longitude (°E)")
ax2.set_ylabel("Latitude (°N)")

output_relief = "mars_olympus_mons_relief.png"
plt.savefig(output_relief, dpi=180, bbox_inches='tight')
plt.close(fig)
print(f"Olympus Mons shaded relief saved to: {output_relief}")

# =====================================================================
# 2. TOPOGRAPHICAL ELEVATION PROFILE: Cross-Section of Valles Marineris
# =====================================================================
print("\n--- Generating Canyon Cross-Section Profile for Valles Marineris ---")
# Valles Marineris (Coprates Chasma): North-South cross section across the canyon
# From 5°S, 292°E to 20°S, 292°E
lat_start, lat_end = -5.0, -22.0
lon_fixed = 292.0

num_samples = 400
lats = np.linspace(lat_start, lat_end, num_samples)
profile_elev = []
distances_km = []

# Circumference of Mars ~21,344 km => ~59.3 km per degree of latitude
km_per_deg_lat = 59.3

for i, lat in enumerate(lats):
    r, c = coord_to_indices(lat, lon_fixed)
    profile_elev.append(elev_grid[r, c])
    dist = abs(lat - lat_start) * km_per_deg_lat
    distances_km.append(dist)

profile_elev = np.array(profile_elev)
distances_km = np.array(distances_km)

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(distances_km, profile_elev / 1000.0, color='darkred', lw=2.2, label='Surface Profile')
ax.fill_between(distances_km, profile_elev / 1000.0, -6, color='coral', alpha=0.25)
ax.axhline(0, color='gray', linestyle='--', lw=1, label='Mars Datum (0 km)')

# Annotate canyon floor depth
min_idx = np.argmin(profile_elev)
ax.annotate(
    f"Canyon Floor: {profile_elev[min_idx]:.0f} m\nDepth: ~7.5 km below rims",
    xy=(distances_km[min_idx], profile_elev[min_idx] / 1000.0),
    xytext=(distances_km[min_idx] + 80, (profile_elev[min_idx] / 1000.0) + 2.5),
    arrowprops=dict(facecolor='black', shrink=0.08, width=1.5, headwidth=8),
    fontsize=10,
    bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.6)
)

ax.set_title("Valles Marineris (Coprates Chasma) Topographical Cross-Section", fontsize=13, pad=12)
ax.set_xlabel("Ground Distance (Kilometers from North Rim)", fontsize=11)
ax.set_ylabel("Elevation (Kilometers relative to Mars Datum)", fontsize=11)
ax.set_ylim(-6, 5)
ax.grid(True, linestyle=':', alpha=0.6)
ax.legend(loc='upper right')

output_profile = "mars_valles_marineris_profile.png"
plt.savefig(output_profile, dpi=180, bbox_inches='tight')
plt.close(fig)
print(f"Valles Marineris cross-section saved to: {output_profile}")
print("\nTerrain analysis complete!")
