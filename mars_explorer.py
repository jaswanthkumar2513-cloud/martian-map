import os
import sqlite3
import numpy as np

MOLA_FILE = "mola_elevation_megt90n000eb.img"
DB_FILE = "mars_data.db"

# Mars Physical Constants
P0 = 610.0          # Mars surface reference pressure at datum (Pascals)
SCALE_HEIGHT = 11100.0  # Atmospheric scale height (meters)
KM_PER_DEG_LAT = 59.3   # Ground distance per degree of latitude on Mars (~3,390 km radius)
PIXEL_SIZE_M = 3710.0   # MOLA 16 pix/deg resolution (~3.71 km/pixel)

class MarsDataSystem:
    def __init__(self):
        if not os.path.exists(MOLA_FILE):
            raise FileNotFoundError(f"Missing {MOLA_FILE}. Run mola.py first to download it.")
        
        print("Loading global MOLA elevation grid (2880 x 5760)...", end=" ", flush=True)
        self.elev = np.fromfile(MOLA_FILE, dtype='>i2').reshape((2880, 5760)).astype(np.float32)
        print("Done!")
        
        # Precompute gradient for slopes
        print("Computing global slope gradients...", end=" ", flush=True)
        dy, dx = np.gradient(self.elev, PIXEL_SIZE_M)
        self.slope_deg = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
        print("Done!\n")

    def coord_to_indices(self, lat, lon):
        row = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
        col = int(np.clip((lon % 360.0) * 16.0, 0, 5759))
        return row, col

    def analyze_point(self, lat, lon):
        r, c = self.coord_to_indices(lat, lon)
        elevation = float(self.elev[r, c])
        slope = float(self.slope_deg[r, c])
        
        # Barometric scale height atmospheric pressure: P = P0 * exp(-h / H)
        pressure_pa = P0 * np.exp(-elevation / SCALE_HEIGHT)
        pressure_mbar = pressure_pa / 100.0
        
        # Hazard and landing rating
        if slope < 3.0:
            slope_rating = "Flat Plains (Very Safe)"
        elif slope < 8.0:
            slope_rating = "Moderate Undulation (Safe for Rovers)"
        elif slope < 15.0:
            slope_rating = "Rugged / Rolling Hills (Caution)"
        else:
            slope_rating = "Steep Cliff / Scarp (HAZARDOUS > 15°)"

        if elevation < -2500 and slope < 5.0 and abs(lat) <= 35:
            parachute_status = "OPTIMAL (Deep basin, thick atmosphere, safe slope)"
        elif elevation < -1400 and slope < 10.0 and abs(lat) <= 35:
            parachute_status = "VIABLE (Acceptable parachute braking margin)"
        elif elevation < 1000:
            parachute_status = "CHALLENGING (Requires advanced retrorockets / Sky Crane)"
        else:
            parachute_status = "CRITICAL (Atmosphere too thin for parachute landing)"

        return {
            "lat": lat,
            "lon": lon % 360.0,
            "elevation_m": elevation,
            "elevation_km": elevation / 1000.0,
            "slope_deg": slope,
            "slope_rating": slope_rating,
            "pressure_pa": pressure_pa,
            "pressure_mbar": pressure_mbar,
            "parachute_status": parachute_status
        }

    def print_analysis(self, name, data):
        print("=" * 65)
        print(f"  MARS PLANETARY ANALYSIS: {name}")
        print("=" * 65)
        print(f"• Coordinates:           {data['lat']:.2f}° {'N' if data['lat']>=0 else 'S'}, {data['lon']:.2f}° E")
        print(f"• MOLA Elevation:        {data['elevation_m']:+,.0f} meters ({data['elevation_km']:+.2f} km)")
        print(f"• Local Surface Slope:   {data['slope_deg']:.2f}° ({data['slope_rating']})")
        print(f"• Surface Air Pressure:  {data['pressure_pa']:.0f} Pa ({data['pressure_mbar']:.1f} mbar)")
        print(f"• Landing Feasibility:   {data['parachute_status']}")
        print("=" * 65 + "\n")

    def save_to_database(self, name, data):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO elevation_data (feature_name, latitude, longitude, elevation)
            VALUES (?, ?, ?, ?)
        ''', (name, data['lat'], data['lon'], data['elevation_m']))
        conn.commit()
        conn.close()
        print(f"Saved '{name}' to {DB_FILE} successfully!")

def run_demo():
    system = MarsDataSystem()
    
    # Test major landmarks
    test_points = [
        ("Olympus Mons Summit", 18.65, 226.20),
        ("Jezero Crater Floor (Perseverance)", 18.38, 77.58),
        ("Valles Marineris Abyss", -14.00, 301.00),
        ("Hellas Planitia Depths", -42.70, 70.00),
    ]

    for name, lat, lon in test_points:
        analysis = system.analyze_point(lat, lon)
        system.print_analysis(name, analysis)
        system.save_to_database(name, analysis)

if __name__ == "__main__":
    run_demo()
