import os
import json
import sqlite3
import zipfile
import numpy as np

MOLA_FILE = "mola_elevation_megt90n000eb.img"
DB_FILE = "mars_data.db"
ZIP_PATH = r"F:\mars details for building website\archive mars surface images.zip"

# Mars Physical Constants
MARS_RADIUS_KM = 3389.5
G_EARTH = 9.80665   # m/s^2
G_MARS = 3.72076    # m/s^2 (~0.379g)
P0 = 610.0          # Pascals at datum
SCALE_HEIGHT = 11100.0  # meters

class MarsEngine:
    def __init__(self):
        self.mola_grid = None
        self.slope_grid = None
        self._load_mola()

    def _load_mola(self):
        if os.path.exists(MOLA_FILE):
            print("Loading MOLA elevation data into memory...")
            self.mola_grid = np.fromfile(MOLA_FILE, dtype='>i2').reshape((2880, 5760)).astype(np.float32)
            # Precompute rough slope gradient
            dy, dx = np.gradient(self.mola_grid, 3710.0)
            self.slope_grid = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
            print("MOLA grid and slope gradients loaded successfully.")
        else:
            print("Warning: MOLA file not found. Topography features will use estimates.")

    def get_elevation_and_slope(self, lat, lon_leaflet):
        # lon_leaflet is -180 to +180. Convert to Mars East longitude (0 to 360)
        lon_east = lon_leaflet % 360.0
        if lon_east < 0:
            lon_east += 360.0

        if self.mola_grid is None:
            return {"elevation_m": 0.0, "slope_deg": 1.5, "pressure_pa": P0}

        r = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
        c = int(np.clip(lon_east * 16.0, 0, 5759))

        elevation = float(self.mola_grid[r, c])
        slope = float(self.slope_grid[r, c])
        pressure = float(P0 * np.exp(-elevation / SCALE_HEIGHT))

        return {
            "elevation_m": round(elevation, 1),
            "slope_deg": round(slope, 2),
            "pressure_pa": round(pressure, 1),
            "pressure_mbar": round(pressure / 100.0, 2)
        }

    def compute_great_circle_distance(self, lat1, lon1, lat2, lon2):
        """Haversine distance on Mars sphere in kilometers."""
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return float(MARS_RADIUS_KM * c)

    def calculate_custom_route(self, lat1, lon1, lat2, lon2):
        """
        Calculates comparative traversal metrics between Conventional Wheeled Rover
        and Antigravity Glider along the path.
        """
        direct_dist_km = self.compute_great_circle_distance(lat1, lon1, lat2, lon2)
        
        # Sample points along the line
        num_samples = max(10, min(50, int(direct_dist_km / 15.0)))
        lats = np.linspace(lat1, lat2, num_samples)
        lons = np.linspace(lon1, lon2, num_samples)

        elevations = []
        slopes = []
        waypoints_antigrav = []
        
        for la, lo in zip(lats, lons):
            geo = self.get_elevation_and_slope(la, lo)
            elevations.append(geo["elevation_m"])
            slopes.append(geo["slope_deg"])
            waypoints_antigrav.append([round(float(la), 4), round(float(lo), 4)])

        max_slope = max(slopes) if slopes else 2.0
        avg_slope = sum(slopes) / len(slopes) if slopes else 1.5

        # Conventional Wheeled Rover Constraints:
        # Cannot climb slopes > 15 deg easily. Must take winding detour paths.
        detour_factor = 1.0 + (avg_slope / 8.0) * 0.75 + (max_slope > 12.0) * 0.8
        detour_factor = max(1.2, min(3.8, detour_factor))
        wheeled_dist_km = round(direct_dist_km * detour_factor, 1)

        # Wheeled rover speed is slow (~0.12 to 0.18 km/h like Curiosity/Perseverance)
        wheeled_speed_kmh = max(0.08, 0.16 - (avg_slope * 0.005))
        wheeled_time_hrs = round(wheeled_dist_km / wheeled_speed_kmh, 1)

        # Energy: Wheeled rover encounters heavy rolling resistance, slippage in Martian dust,
        # and steep climbing work against full gravity.
        # Average wheeled energy: ~4.5 kWh per km under rough terrain
        wheeled_energy_kwh = round(wheeled_dist_km * (3.8 + avg_slope * 0.4), 1)

        # Generate realistic winding route for wheeled rover (sinusoidal lateral deviation)
        waypoints_wheeled = []
        for i, (la, lo) in enumerate(zip(lats, lons)):
            if i == 0 or i == len(lats) - 1:
                waypoints_wheeled.append([round(float(la), 4), round(float(lo), 4)])
            else:
                # Add zig-zag switchbacks around terrain hazards
                offset = np.sin(i * 1.5) * (avg_slope / 15.0) * 0.4
                waypoints_wheeled.append([round(float(la + offset), 4), round(float(lo - offset * 0.5), 4)])

        # Antigravity Glider Constraints:
        # Operates at geff = 0.05g. Zero rolling resistance. Direct flight corridor.
        # Glider speed: 18.0 km/h cruising speed.
        antigrav_dist_km = round(direct_dist_km, 1)
        antigrav_speed_kmh = 16.5
        antigrav_time_hrs = round(antigrav_dist_km / antigrav_speed_kmh, 1)
        
        # Antigravity energy: Field sustained at 0.05g + low atmospheric drag in Mars thin air
        # Energy reduction is ~85-92%
        antigrav_energy_kwh = round(antigrav_dist_km * 0.55, 1)
        energy_savings_pct = round(((wheeled_energy_kwh - antigrav_energy_kwh) / max(1.0, wheeled_energy_kwh)) * 100, 1)
        time_savings_pct = round(((wheeled_time_hrs - antigrav_time_hrs) / max(0.1, wheeled_time_hrs)) * 100, 1)

        return {
            "direct_distance_km": round(direct_dist_km, 1),
            "max_slope_deg": round(max_slope, 1),
            "avg_slope_deg": round(avg_slope, 1),
            "wheeled": {
                "distance_km": wheeled_dist_km,
                "duration_hours": wheeled_time_hrs,
                "duration_days": round(wheeled_time_hrs / 24.66, 1), # Martian Sols
                "energy_kwh": wheeled_energy_kwh,
                "avg_speed_kmh": round(wheeled_speed_kmh, 2),
                "waypoints": waypoints_wheeled
            },
            "antigrav": {
                "distance_km": antigrav_dist_km,
                "duration_hours": antigrav_time_hrs,
                "duration_days": round(antigrav_time_hrs / 24.66, 2),
                "energy_kwh": antigrav_energy_kwh,
                "avg_speed_kmh": antigrav_speed_kmh,
                "waypoints": waypoints_antigrav
            },
            "savings": {
                "distance_saved_km": round(wheeled_dist_km - antigrav_dist_km, 1),
                "time_saved_hours": round(wheeled_time_hrs - antigrav_time_hrs, 1),
                "energy_savings_pct": max(0.0, energy_savings_pct),
                "time_savings_pct": max(0.0, time_savings_pct)
            },
            "elevation_profile": [
                {"step": i, "elevation": elev, "slope": slp}
                for i, (elev, slp) in enumerate(zip(elevations, slopes))
            ]
        }

    def simulate_physics(self, mass_kg=1000.0, lift_height_m=3.0, transport_dist_km=5.0, antigrav_geff=0.05):
        """
        Physics simulation comparing Earth, Mars, and Antigravity Field:
        - Weight: W = m * g
        - Work to lift vertically: E = m * g * h
        - Human payload capacity (Assumes typical athletic astronaut can press ~40 kg in 1g):
          human_lift_capacity_kg = 40.0 * (G_EARTH / g)
          astronauts_needed = ceil(mass_kg / human_lift_capacity_kg)
        - Jump height: h = v^2 / (2 * g) for takeoff velocity v = 2.8 m/s (~0.4m jump on Earth)
        """
        v_takeoff = 2.8 # m/s
        g_ag = G_EARTH * antigrav_geff

        environments = {
            "earth": {
                "name": "Earth Surface",
                "gravity_ms2": G_EARTH,
                "g_ratio": 1.0,
                "weight_newtons": round(mass_kg * G_EARTH, 1),
                "effective_mass_feeling_kg": round(mass_kg, 1),
                "lift_work_joules": round(mass_kg * G_EARTH * lift_height_m, 1),
                "lift_work_kwh": round((mass_kg * G_EARTH * lift_height_m) / 3.6e6, 4),
                "horizontal_transport_kwh": round(mass_kg * G_EARTH * 0.05 * (transport_dist_km * 1000) / 3.6e6, 2),
                "jump_height_meters": round((v_takeoff**2) / (2 * G_EARTH), 2),
                "hang_time_seconds": round((2 * v_takeoff) / G_EARTH, 2),
                "astronauts_to_lift": int(np.ceil(mass_kg / 40.0))
            },
            "mars": {
                "name": "Mars Natural Surface",
                "gravity_ms2": G_MARS,
                "g_ratio": round(G_MARS / G_EARTH, 3),
                "weight_newtons": round(mass_kg * G_MARS, 1),
                "effective_mass_feeling_kg": round(mass_kg * (G_MARS / G_EARTH), 1),
                "lift_work_joules": round(mass_kg * G_MARS * lift_height_m, 1),
                "lift_work_kwh": round((mass_kg * G_MARS * lift_height_m) / 3.6e6, 4),
                "horizontal_transport_kwh": round(mass_kg * G_MARS * 0.05 * (transport_dist_km * 1000) / 3.6e6, 2),
                "jump_height_meters": round((v_takeoff**2) / (2 * G_MARS), 2),
                "hang_time_seconds": round((2 * v_takeoff) / G_MARS, 2),
                "astronauts_to_lift": int(np.ceil(mass_kg / (40.0 * (G_EARTH / G_MARS))))
            },
            "antigrav": {
                "name": f"Antigravity Field (g_eff = {antigrav_geff}g)",
                "gravity_ms2": round(g_ag, 3),
                "g_ratio": round(antigrav_geff, 3),
                "weight_newtons": round(mass_kg * g_ag, 1),
                "effective_mass_feeling_kg": round(mass_kg * antigrav_geff, 1),
                "lift_work_joules": round(mass_kg * g_ag * lift_height_m, 1),
                "lift_work_kwh": round((mass_kg * g_ag * lift_height_m) / 3.6e6, 4),
                "horizontal_transport_kwh": round(mass_kg * g_ag * 0.01 * (transport_dist_km * 1000) / 3.6e6, 3),
                "jump_height_meters": round((v_takeoff**2) / (2 * max(0.1, g_ag)), 2),
                "hang_time_seconds": round((2 * v_takeoff) / max(0.1, g_ag), 2),
                "astronauts_to_lift": max(1, int(np.ceil(mass_kg / (40.0 / antigrav_geff))))
            }
        }

        # Energy savings comparing Mars natural vs Antigravity
        lift_savings = ((environments["mars"]["lift_work_joules"] - environments["antigrav"]["lift_work_joules"]) / 
                        max(1.0, environments["mars"]["lift_work_joules"])) * 100.0

        return {
            "mass_kg": mass_kg,
            "lift_height_m": lift_height_m,
            "transport_dist_km": transport_dist_km,
            "antigrav_geff": antigrav_geff,
            "environments": environments,
            "energy_savings_percentage": round(lift_savings, 1),
            "payload_reduction_factor": round(1.0 / antigrav_geff, 1)
        }

    def get_hirise_image_bytes(self, obs_id):
        """Fetches raw image bytes from the 4.2 GB zip file, or local static samples as fallback."""
        # 1. Primary: 4.2 GB local archive
        if os.path.exists(ZIP_PATH):
            target_name = f"captioned/images/{obs_id}.jpg"
            try:
                with zipfile.ZipFile(ZIP_PATH, 'r') as z:
                    with z.open(target_name) as f:
                        return f.read()
            except Exception:
                pass

        # 2. Fallback: local static sample directory (for cloud/Vercel deployment)
        sample_path = os.path.join("static", "sample_images", f"{obs_id}.jpg")
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                return f.read()

        # 3. Default fallback to first sample available
        sample_dir = os.path.join("static", "sample_images")
        if os.path.exists(sample_dir):
            files = [f for f in os.listdir(sample_dir) if f.endswith(".jpg")]
            if files:
                with open(os.path.join(sample_dir, files[0]), "rb") as f:
                    return f.read()

        return None
