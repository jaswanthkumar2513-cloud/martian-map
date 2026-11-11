import os
import sqlite3
import numpy as np

# Path to MOLA topography data file
MOLA_FILE = "mola_elevation_megt90n000eb.img"
DB_NAME = "mars_data.db"

def load_mola_data():
    """Loads the 16 pix/deg MOLA elevation grid (2880 x 5760)."""
    if not os.path.exists(MOLA_FILE):
        raise FileNotFoundError(f"Missing {MOLA_FILE}. Run mola.py to download it first.")
    return np.fromfile(MOLA_FILE, dtype='>i2').reshape((2880, 5760))

def get_elevation(elev_grid, latitude, longitude):
    """
    Given latitude (-90 to +90) and longitude (0 to 360 East),
    returns elevation in meters relative to Mars datum.
    """
    row = int(np.clip((90.0 - latitude) * 16.0, 0, 2879))
    col = int(np.clip((longitude % 360.0) * 16.0, 0, 5759))
    return int(elev_grid[row, col])

def init_database():
    """Initializes or updates the SQLite database schema."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(elevation_data)")
    cols = [col[1] for col in cur.fetchall()]
    
    if not cols:
        cur.execute('''
            CREATE TABLE elevation_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_name TEXT,
                latitude REAL,
                longitude REAL,
                elevation REAL
            )
        ''')
    elif 'feature_name' not in cols:
        cur.execute("ALTER TABLE elevation_data ADD COLUMN feature_name TEXT")
        
    conn.commit()
    return conn

def populate_sample_landmarks(conn, elev_grid):
    """Inserts real elevation data for major Martian landmarks."""
    cur = conn.cursor()
    landmarks = [
        ("Olympus Mons Peak", 18.65, 226.2),
        ("Hellas Basin Floor", -42.70, 70.0),
        ("Jezero Crater (Perseverance Landing Site)", 18.38, 77.58),
        ("Gale Crater (Curiosity Landing Site)", -4.59, 137.44),
        ("Valles Marineris (Chasma Floor)", -14.00, 301.0),
        ("Elysium Mons Peak", 25.02, 147.21),
        ("Viking 1 Landing Site (Chryse Planitia)", 22.48, 312.05),
    ]

    print("\nExtracting elevations from MOLA dataset and storing to database...")
    for name, lat, lon in landmarks:
        elev = get_elevation(elev_grid, lat, lon)
        cur.execute(
            "INSERT INTO elevation_data (feature_name, latitude, longitude, elevation) VALUES (?, ?, ?, ?)",
            (name, lat, lon, elev),
        )
        print(f" -> {name}: Lat {lat}°, Lon {lon}°E => {elev:,} meters")

    conn.commit()

if __name__ == "__main__":
    print("=== Mars Scientific Elevation Database Pipeline ===")
    conn = init_database()
    
    # Load MOLA grid
    mola_grid = load_mola_data()
    print("Loaded MOLA elevation data grid successfully.")
    
    # Clear previous sample rows if re-running
    conn.cursor().execute("DELETE FROM elevation_data")
    
    # Populate landmarks with true MOLA measurements
    populate_sample_landmarks(conn, mola_grid)
    
    # Query and display database contents
    print("\n--- Current mars_data.db Records ---")
    cur = conn.cursor()
    cur.execute("SELECT id, feature_name, latitude, longitude, elevation FROM elevation_data")
    for row in cur.fetchall():
        print(f"ID {row[0]}: {row[1]} | Coord: ({row[2]}°, {row[3]}°E) | Elev: {row[4]:,} m")

    conn.close()
    print("\nDatabase updated successfully!")
