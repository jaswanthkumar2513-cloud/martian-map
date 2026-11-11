import os
import tempfile
# Use a writable temporary folder for matplotlib cache
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'matplotlib'))

import numpy as np
import matplotlib.pyplot as plt

# Point to the downloaded MOLA file
mola_file = "mola_elevation_megt90n000eb.img"

if not os.path.exists(mola_file):
    print(f"File not found: {mola_file}. Please run mola.py first to download it.")
    exit(1)

print(f"Loading MOLA elevation data from: {mola_file}...")

# MOLA 16 pix/deg MEGDR specification:
# - Global coverage: 90°N to 90°S (180°), 0°E to 360°E (360°)
# - Rows (Height): 180 deg * 16 = 2880 pixels
# - Columns (Width): 360 deg * 16 = 5760 pixels
# - Data type: 16-bit signed big-endian integer (meters relative to Mars datum)
try:
    # Read raw planetary binary data using NumPy
    elevation_data = np.fromfile(mola_file, dtype='>i2').reshape((2880, 5760))
    
    print("Successfully loaded MOLA elevation dataset!")
    print(f"Dimensions: {elevation_data.shape[1]} x {elevation_data.shape[0]} (Width x Height)")
    print(f"Mars Elevation Range: {elevation_data.min()} m to {elevation_data.max()} m")
    
    # Create the planetary topography plot
    plt.figure(figsize=(14, 7))
    
    # 'terrain' colormap displays low basins (Hellas, Argyre) in blues/greens 
    # and giant volcanoes (Olympus Mons, Tharsis) in browns/whites
    img = plt.imshow(
        elevation_data,
        cmap='terrain',
        extent=[0, 360, -90, 90],  # Longitude 0-360°E, Latitude -90 to 90°
        aspect='auto'
    )
    
    cbar = plt.colorbar(img, label='Elevation (meters relative to Mars Datum)', pad=0.02)
    plt.title('Mars Global MOLA Topography (MGS MOLA MEGDR 16 pix/deg)', fontsize=14, pad=12)
    plt.xlabel('Longitude (Degrees East)', fontsize=11)
    plt.ylabel('Latitude (Degrees)', fontsize=11)
    
    # Save a high-resolution PNG image
    output_png = "mars_mola_topography.png"
    plt.savefig(output_png, dpi=200, bbox_inches='tight')
    print(f"Map image successfully saved locally to: {output_png}")
    
    # Open interactive window
    plt.show()

except Exception as e:
    print(f"An error occurred: {e}")
