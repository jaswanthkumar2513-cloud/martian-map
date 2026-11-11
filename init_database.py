import os
import json
import sqlite3
import zipfile
import numpy as np

DB_FILE = "mars_data.db"
ZIP_PATH = r"F:\mars details for building website\archive mars surface images.zip"
MOLA_FILE = "mola_elevation_megt90n000eb.img"

def lon_to_leaflet(lon_east):
    lon = float(lon_east) % 360.0
    if lon > 180.0:
        return lon - 360.0
    return lon

def load_mola_grid():
    if os.path.exists(MOLA_FILE):
        return np.fromfile(MOLA_FILE, dtype='>i2').reshape((2880, 5760)).astype(np.float32)
    return None

def get_elevation_from_grid(grid, lat, lon_east):
    if grid is None:
        return 0.0
    r = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
    c = int(np.clip((float(lon_east) % 360.0) * 16.0, 0, 5759))
    return float(grid[r, c])

def setup_database():
    print("Setting up mars_data.db for Interplanetary Survival Guide...")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # 1. HiRISE Captioned Observations Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS hirise_observations (
            obs_id TEXT PRIMARY KEY,
            title TEXT,
            lat REAL,
            lon_east REAL,
            lon_leaflet REAL,
            elevation REAL,
            caption TEXT,
            acquisition_date TEXT,
            spacecraft_altitude TEXT,
            scale TEXT
        )
    ''')

    # 2. Gravity-Manipulation Zones (GMZ) Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS gravity_zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            code TEXT,
            lat REAL,
            lon_east REAL,
            lon_leaflet REAL,
            elevation REAL,
            radius_km REAL,
            field_strength_g REAL,
            status TEXT,
            purpose TEXT,
            power_mw REAL,
            active_payload TEXT,
            mitigation TEXT
        )
    ''')

    # 3. Mars Outposts & Exploration Bases Table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS mars_outposts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            lat REAL,
            lon_east REAL,
            lon_leaflet REAL,
            elevation REAL,
            status TEXT,
            description TEXT
        )
    ''')

    # 4. Antigravity vs Wheeled Routing Corridors
    cur.execute('''
        CREATE TABLE IF NOT EXISTS antigravity_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT,
            origin_name TEXT,
            destination_name TEXT,
            origin_lat REAL,
            origin_lon REAL,
            dest_lat REAL,
            dest_lon REAL,
            wheeled_dist_km REAL,
            antigrav_dist_km REAL,
            wheeled_time_hrs REAL,
            antigrav_time_hrs REAL,
            energy_savings_pct REAL,
            obstacle_description TEXT,
            route_geometry_json TEXT
        )
    ''')

    mola_grid = load_mola_grid()

    # Populate HiRISE data if not already populated
    cur.execute("SELECT COUNT(*) FROM hirise_observations")
    hirise_count = cur.fetchone()[0]
    if hirise_count == 0 and os.path.exists(ZIP_PATH):
        print(f"Reading {ZIP_PATH} for captioned HiRISE images...")
        with zipfile.ZipFile(ZIP_PATH, 'r') as z:
            with z.open('captioned/meta_clean.json') as f:
                data = json.load(f)
                rows = []
                for obs_id, meta in data.items():
                    try:
                        lat = float(meta.get('Latitude (centered)', 0))
                        lon_e = float(meta.get('Longitude (East)', 0))
                        lon_l = lon_to_leaflet(lon_e)
                        title = meta.get('title', 'Martian Surface Observation')
                        caption = meta.get('caption', '')
                        date = meta.get('Acquisition date', 'Unknown')
                        alt = meta.get('Spacecraft altitude', '250 km')
                        scale = meta.get('Map projected scale', '50 cm/pixel')
                        elev = get_elevation_from_grid(mola_grid, lat, lon_e)
                        rows.append((obs_id, title, lat, lon_e, lon_l, elev, caption, date, alt, scale))
                    except Exception:
                        continue
                cur.executemany('''
                    INSERT OR REPLACE INTO hirise_observations 
                    (obs_id, title, lat, lon_east, lon_leaflet, elevation, caption, acquisition_date, spacecraft_altitude, scale)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', rows)
        print(f"Imported {len(rows)} HiRISE scientific images into database!")
    else:
        print(f"HiRISE observations already present ({hirise_count} records).")

    # Populate Gravity-Manipulation Zones (GMZs)
    cur.execute("DELETE FROM gravity_zones")
    gmz_records = [
        (
            "GMZ-Alpha: Jezero Delta Habitat Core", "GMZ-01",
            18.38, 77.58, lon_to_leaflet(77.58), get_elevation_from_grid(mola_grid, 18.38, 77.58),
            12.5, 0.05, "Operational (Active Levitation)",
            "Heavy-lift modular habitat construction and regolith radiation berm positioning.",
            1.85, "Primary Pressurized Dome #4 (Mass: 42,000 kg -> Effective: 2,100 kg)",
            "Cancels 95% of gravitational load; eliminates crane tip-over risks on loose delta sand."
        ),
        (
            "GMZ-Beta: Valles Marineris Canyon Lift Corridor", "GMZ-02",
            -14.00, 301.00, lon_to_leaflet(301.00), get_elevation_from_grid(mola_grid, -14.00, 301.00),
            25.0, 0.08, "Operational (Continuous Transport)",
            "Vertical cargo transit across the 7,000-meter canyon escarpment wall.",
            3.40, "Deep Subsurface Mineral Extractor Unit (Mass: 68,000 kg -> Effective: 5,440 kg)",
            "Bypasses 45° vertical rock walls without winding zigzag roads."
        ),
        (
            "GMZ-Gamma: Olympus Caldera High-Altitude Lab", "GMZ-03",
            18.65, 226.20, lon_to_leaflet(226.20), get_elevation_from_grid(mola_grid, 18.65, 226.20),
            18.0, 0.04, "Operational (Stationary Levitation)",
            "Stabilizing deep atmospheric observatory modules in near-vacuum volcanic rim.",
            1.20, "Cryogenic Solar Flare Tracking Array (Mass: 15,000 kg -> Effective: 600 kg)",
            "Allows delicate optical sensor alignment without seismic ground settling."
        ),
        (
            "GMZ-Delta: Arcadia Glacial Water Harvesting Base", "GMZ-04",
            39.30, 189.70, lon_to_leaflet(189.70), get_elevation_from_grid(mola_grid, 39.30, 189.70),
            15.0, 0.06, "Operational (Trench Levitation)",
            "Subsurface ice sheet thermal extraction and massive ice ingot hauling.",
            2.10, "Automated Subsurface Ice Slicer (Mass: 30,000 kg -> Effective: 1,800 kg)",
            "Prevents heavy machinery from sinking into thawing permafrost mud."
        ),
        (
            "GMZ-Epsilon: Hellas Basin Deep Atmospheric Outpost", "GMZ-05",
            -42.70, 70.00, lon_to_leaflet(70.00), get_elevation_from_grid(mola_grid, -42.70, 70.00),
            20.0, 0.05, "Operational (Regolith Shielding)",
            "Atmospheric shielding field and heavy bunker assembly in maximum pressure zone.",
            2.80, "Tungsten-Composite Radiation Bunker Ceiling (Mass: 90,000 kg -> Effective: 4,500 kg)",
            "Enables rapid placement of thick cosmic ray shielding blocks."
        )
    ]
    cur.executemany('''
        INSERT INTO gravity_zones 
        (name, code, lat, lon_east, lon_leaflet, elevation, radius_km, field_strength_g, status, purpose, power_mw, active_payload, mitigation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', gmz_records)
    print(f"Populated {len(gmz_records)} Gravity-Manipulation Zones.")

    # Populate Mars Outposts & Historic Landing Sites
    cur.execute("DELETE FROM mars_outposts")
    outposts = [
        ("Jezero Base Alpha (Perseverance Site)", "Human Outpost & Science Hub", 18.38, 77.58, lon_to_leaflet(77.58), get_elevation_from_grid(mola_grid, 18.38, 77.58), "Active Colony", "Primary astrobiology river delta exploration center."),
        ("Gale Crater Station (Curiosity Site)", "Geology & Mineral Analysis Base", -4.59, 137.44, lon_to_leaflet(137.44), get_elevation_from_grid(mola_grid, -4.59, 137.44), "Active Science Station", "Mount Sharp sedimentary layer research."),
        ("Olympus Mons Summit Observatory", "Deep Space & High-Altitude Research", 18.65, 226.20, lon_to_leaflet(226.20), get_elevation_from_grid(mola_grid, 18.65, 226.20), "Active High-Altitude Base", "Highest elevation research station in the Solar System (21,000 m)."),
        ("Valles Marineris Chasma Depot", "Deep Canyon Logistics Terminal", -14.00, 301.00, lon_to_leaflet(301.00), get_elevation_from_grid(mola_grid, -14.00, 301.00), "Active Logistics Depot", "Canyon floor sheltered habitat beneath giant cliffs."),
        ("Arcadia Planitia Ice Extraction Camp", "Resource Mining Hub", 39.30, 189.70, lon_to_leaflet(189.70), get_elevation_from_grid(mola_grid, 39.30, 189.70), "Active Industrial Base", "Glacial ice deposits for life support and rocket propellant."),
        ("Hellas Planitia Deep Station", "Dense Atmosphere Research Center", -42.70, 70.00, lon_to_leaflet(70.00), get_elevation_from_grid(mola_grid, -42.70, 70.00), "Active Science Base", "Lowest point on Mars (-7,000 m), providing maximal natural atmospheric radiation shielding."),
        ("Viking 1 Memorial Station (Chryse Planitia)", "Historic Landing Site", 22.48, 312.05, lon_to_leaflet(312.05), get_elevation_from_grid(mola_grid, 22.48, 312.05), "Historic Landmark", "First successful landing and long-duration mission on Mars (1976).")
    ]
    cur.executemany('''
        INSERT INTO mars_outposts 
        (name, category, lat, lon_east, lon_leaflet, elevation, status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', outposts)
    print(f"Populated {len(outposts)} Mars Outposts.")

    # Populate Antigravity vs Wheeled Routing Corridors
    cur.execute("DELETE FROM antigravity_routes")
    routes = [
        (
            "Jezero Delta to Isidis Lowland Rim",
            "Jezero Base Alpha", "Isidis Logistics Depository",
            18.38, lon_to_leaflet(77.58),
            12.80, lon_to_leaflet(88.20),
            785.4, 280.2,
            523.6, 18.6,
            88.4,
            "Crater rim escarpment with 22° slopes and treacherous boulder fields. Wheeled rovers must navigate a 785 km zigzag detour. Antigravity Glider flies direct 280 km glide corridor over crater lip in 18 hours.",
            json.dumps({
                "wheeled": [
                    [18.38, lon_to_leaflet(77.58)],
                    [19.10, lon_to_leaflet(79.00)],
                    [17.50, lon_to_leaflet(82.40)],
                    [15.80, lon_to_leaflet(84.50)],
                    [14.20, lon_to_leaflet(86.10)],
                    [12.80, lon_to_leaflet(88.20)]
                ],
                "antigrav": [
                    [18.38, lon_to_leaflet(77.58)],
                    [15.60, lon_to_leaflet(82.90)],
                    [12.80, lon_to_leaflet(88.20)]
                ]
            })
        ),
        (
            "Valles Marineris North-to-South Wall Crossing",
            "Coprates Chasma North Rim", "Melas Chasma South Depot",
            -11.50, lon_to_leaflet(295.00),
            -15.80, lon_to_leaflet(297.20),
            1240.0, 185.0,
            826.0, 12.3,
            93.2,
            "7,000-meter near-vertical canyon abyss. Wheeled rover is physically blocked and must travel 1,240 km around the eastern canyon mouth. Antigravity craft glides effortlessly across the 185 km chasm at 15 km/h.",
            json.dumps({
                "wheeled": [
                    [-11.50, lon_to_leaflet(295.00)],
                    [-10.20, lon_to_leaflet(305.00)],
                    [-12.00, lon_to_leaflet(315.00)],
                    [-18.00, lon_to_leaflet(312.00)],
                    [-17.00, lon_to_leaflet(302.00)],
                    [-15.80, lon_to_leaflet(297.20)]
                ],
                "antigrav": [
                    [-11.50, lon_to_leaflet(295.00)],
                    [-13.65, lon_to_leaflet(296.10)],
                    [-15.80, lon_to_leaflet(297.20)]
                ]
            })
        ),
        (
            "Olympus Mons Basal Scarp Summit Ascent",
            "Western Volcanic Plains Base", "Caldera Scientific Station",
            17.20, lon_to_leaflet(221.00),
            18.65, lon_to_leaflet(226.20),
            460.0, 145.0,
            306.0, 9.6,
            86.5,
            "Sheer 6-km cliff (basal scarp) encircling the volcano. Impassable for conventional wheeled vehicles. Antigravity propulsion neutralizes 95% of gravity, ascending the vertical scarp in under 10 hours.",
            json.dumps({
                "wheeled": [
                    [17.20, lon_to_leaflet(221.00)],
                    [15.80, lon_to_leaflet(223.50)],
                    [16.40, lon_to_leaflet(228.00)],
                    [17.90, lon_to_leaflet(227.50)],
                    [18.65, lon_to_leaflet(226.20)]
                ],
                "antigrav": [
                    [17.20, lon_to_leaflet(221.00)],
                    [18.65, lon_to_leaflet(226.20)]
                ]
            })
        )
    ]
    cur.executemany('''
        INSERT INTO antigravity_routes 
        (route_name, origin_name, destination_name, origin_lat, origin_lon, dest_lat, dest_lon, wheeled_dist_km, antigrav_dist_km, wheeled_time_hrs, antigrav_time_hrs, energy_savings_pct, obstacle_description, route_geometry_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', routes)
    print(f"Populated {len(routes)} Antigravity vs Wheeled Routing Corridors.")

    conn.commit()
    conn.close()
    print("Database initialization complete!\n")

if __name__ == "__main__":
    setup_database()
