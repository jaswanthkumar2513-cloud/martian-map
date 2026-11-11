import os
import tempfile
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'matplotlib'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

mola_file = "mola_elevation_megt90n000eb.img"

if not os.path.exists(mola_file):
    print(f"Error: {mola_file} not found. Run mola.py first to download it.")
    exit(1)

print(f"Loading {mola_file} for physical slope hazard calculation...")

# 1. Read binary elevation data using NumPy (2880 rows x 5760 cols)
elevation_data = np.fromfile(mola_file, dtype='>i2').reshape((2880, 5760)).astype(np.float32)

# 2. Slope Calculation with physical cell spacing (~3,710 m/pixel at Mars equator)
pixel_size_meters = 3710.0
dy, dx = np.gradient(elevation_data, pixel_size_meters)
slope_radians = np.sqrt(dx**2 + dy**2)
slope_degrees = np.degrees(np.arctan(slope_radians))

print(f"Mars Slope Range: {slope_degrees.min():.2f}° to {slope_degrees.max():.2f}° (Average: {slope_degrees.mean():.2f}°)")

# 3. Identify hazardous steep areas (> 15 degrees)
hazardous_slope = slope_degrees > 15.0
hazard_mask = np.ma.masked_where(~hazardous_slope, slope_degrees)

print(f"Detected {np.sum(hazardous_slope):,} hazardous pixels exceeding 15° slope.")

# 4. Plot Hazard Map
plt.figure(figsize=(14, 7))

# Safe / moderate slopes in terrain colors (0 to 15 degrees)
img = plt.imshow(
    slope_degrees, 
    cmap='terrain', 
    extent=[0, 360, -90, 90], 
    aspect='auto', 
    vmin=0, 
    vmax=15
)

# Overlay steep danger areas (>15°) in bright red/yellow
plt.imshow(
    hazard_mask, 
    cmap='autumn', 
    extent=[0, 360, -90, 90], 
    aspect='auto'
)

plt.colorbar(img, label='Slope Steepness (Degrees)', pad=0.02)
plt.title('Corrected Mars Hazard Map: Slope Steepness & Landing Hazards', fontsize=13, pad=12)
plt.xlabel('Longitude (Degrees East)', fontsize=11)
plt.ylabel('Latitude (Degrees)', fontsize=11)

legend_elements = [
    Patch(facecolor='yellow', edgecolor='red', label='Hazard Zone (Slope > 15°)')
]
plt.legend(handles=legend_elements, loc='upper right')

output_png = "mars_hazard_map.png"
plt.savefig(output_png, dpi=180, bbox_inches='tight')
print(f"Corrected hazard map successfully saved to: {output_png}")

# Display the interactive window
import sys
if sys.stdout.isatty():
    plt.show()
else:
    plt.show(block=False)
    plt.pause(1)
