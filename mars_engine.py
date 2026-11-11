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

        # Thermal and Radiation Environmental Modeling
        thermal = self.get_temperature_and_thermal(lat, lon_leaflet, elevation)

        return {
            "elevation_m": round(elevation, 1),
            "slope_deg": round(slope, 2),
            "pressure_pa": round(pressure, 1),
            "pressure_mbar": round(pressure / 100.0, 2),
            "temperature_c": thermal["temp_c"],
            "temperature_k": thermal["temp_k"],
            "thermal_zone": thermal["thermal_zone"],
            "radiation_msv_day": thermal["radiation_msv_day"],
            "suit_heating_watts": thermal["suit_heating_watts"]
        }

    def get_temperature_and_thermal(self, lat, lon_leaflet, elevation_m=0.0, is_night=False):
        """
        Martian thermodynamic and thermal environment model:
        - Latitudinal insolation gradient (Warmest at equator, cryogenic at poles)
        - Altitude lapse rate (~ -4.5 K per 1,000 meters elevation)
        - Diurnal Day/Night cycle swing (~60°C to 80°C delta)
        - Cosmic and solar particle radiation dose vs. atmospheric shielding depth
        """
        lat_rad = np.radians(lat)
        
        # 1. Base insolation temperature
        # Equator solar noon: ~ +15°C to +20°C in summer, drops to -130°C at poles
        if not is_night:
            base_temp_c = 18.0 * np.cos(lat_rad) - 75.0 * (np.sin(lat_rad)**2)
        else:
            # Nighttime radiative cooling through thin CO2 atmosphere
            base_temp_c = -72.0 * np.cos(lat_rad) - 65.0 * (np.sin(lat_rad)**2)

        # 2. Martian Atmospheric Lapse Rate: -4.5 K per 1,000 m (relative to datum)
        lapse_rate_k_per_m = 0.0045
        elevation_temp_delta = -elevation_m * lapse_rate_k_per_m
        temp_c = round(float(base_temp_c + elevation_temp_delta), 1)

        # Hard physical floor: CO2 sublimation/freezing point on Mars is ~ -125°C (148 K)
        temp_c = max(-138.0, min(24.0, temp_c))
        temp_k = round(temp_c + 273.15, 1)

        # Thermal classification
        if temp_c > 0.0:
            thermal_zone = "Temperate Daytime (Liquid Water Possible Brief)"
        elif temp_c > -40.0:
            thermal_zone = "Moderate Sub-Zero (Nominal Rover Operation)"
        elif temp_c > -80.0:
            thermal_zone = "Severe Cold (Battery Pre-Heating Required)"
        else:
            thermal_zone = "Cryogenic Extreme (Dry Ice CO2 Frost Zone)"

        # 3. Radiation Exposure Model
        # Base Mars surface radiation: ~0.65 mSv/day (GCR + Solar particles)
        # Thicker atmosphere at low elevations provides shielding (e.g. Hellas Basin)
        # Thin air at Olympus Mons leaves astronaut unprotected
        density_shielding_factor = np.exp(-elevation_m / 11100.0)
        surface_rad = 0.65 * (2.0 - min(1.3, density_shielding_factor))
        surface_rad = max(0.45, min(0.98, surface_rad))

        # 4. Thermal Suit Heating Power
        # Standard astronaut EVA suit delta-T heating: Q = U * A * (T_suit - T_ambient)
        suit_watts = int(max(80, (20.0 - temp_c) * 3.8))

        return {
            "temp_c": temp_c,
            "temp_k": temp_k,
            "thermal_zone": thermal_zone,
            "radiation_msv_day": round(float(surface_rad), 3),
            "suit_heating_watts": suit_watts
        }

    def generate_global_thermal_grid(self, is_night=False):
        """Generates a coarse global grid of Martian surface temperatures for Leaflet thermal heatmap."""
        grid = []
        for lat in range(-80, 85, 10):
            for lon_leaflet in range(-180, 185, 15):
                lon_east = lon_leaflet % 360.0
                elev = 0.0
                if self.mola_grid is not None:
                    r = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
                    c = int(np.clip(lon_east * 16.0, 0, 5759))
                    elev = float(self.mola_grid[r, c])
                
                t = self.get_temperature_and_thermal(lat, lon_leaflet, elev, is_night)
                grid.append({
                    "lat": lat,
                    "lon": lon_leaflet,
                    "elev": round(elev, 0),
                    "temp_c": t["temp_c"],
                    "rad": t["radiation_msv_day"]
                })
        return grid

    def get_subsurface_ice_sheets(self):
        """
        NASA SHARAD (Shallow Radar) & MRO soundings of massive subsurface water ice deposits.
        Crucial for in-situ resource utilization (ISRU) drinking water and rocket propellant synthesis.
        """
        return [
            {
                "name": "Arcadia Planitia Subsurface Glaciers",
                "code": "ICE-01",
                "lat": 39.30,
                "lon": 189.70,
                "lon_leaflet": 189.70 if 189.70 <= 180 else 189.70 - 360,
                "depth_below_surface_m": 1.5,
                "estimated_thickness_m": 120,
                "purity_pct": 96,
                "volume_km3": 14500,
                "accessibility": "Very High (Accessible by shallow automated scrape drill)",
                "mission_value": "Primary candidate site for human base water supply and LOX/Methane propellant"
            },
            {
                "name": "Utopia Planitia Subsurface Ice Sheet",
                "code": "ICE-02",
                "lat": 45.00,
                "lon": 110.00,
                "lon_leaflet": 110.00 if 110.00 <= 180 else 110.00 - 360,
                "depth_below_surface_m": 2.5,
                "estimated_thickness_m": 170,
                "purity_pct": 92,
                "volume_km3": 14300,
                "accessibility": "High (Covered by 1-2.5m dust-regolith mantle)",
                "mission_value": "Contains more water than Lake Superior on Earth; shielded from cosmic radiation"
            },
            {
                "name": "Korolev Crater Permanent Ice Dome",
                "code": "ICE-03",
                "lat": 73.00,
                "lon": 165.00,
                "lon_leaflet": 165.00 if 165.00 <= 180 else 165.00 - 360,
                "depth_below_surface_m": 0.0,
                "estimated_thickness_m": 1800,
                "purity_pct": 99,
                "volume_km3": 2200,
                "accessibility": "Direct Surface Access (Cryogenic cold trap reservoir)",
                "mission_value": "1.8 km thick pure water ice layer kept frozen by cold air trap year-round"
            },
            {
                "name": "Deuteronilus Mensae Lobate Apron",
                "code": "ICE-04",
                "lat": 43.80,
                "lon": 23.50,
                "lon_leaflet": 23.50,
                "depth_below_surface_m": 4.0,
                "estimated_thickness_m": 350,
                "purity_pct": 88,
                "volume_km3": 8700,
                "accessibility": "Moderate (Debris-covered rock glacier)",
                "mission_value": "Ancient glacier flows preserved under rocky insulating landslide blanket"
            }
        ]

    def get_astronaut_eva_tasks(self):
        """Active operational EVA task dispatch board for Martian surface crew."""
        return [
            {
                "id": "EVA-101",
                "title": "Subsurface Ice Core Drill & Purity Assay",
                "site": "Arcadia Glacial Base",
                "crew": "Dr. Sarah Lin, Specialist Cole",
                "priority": "HIGH",
                "status": "In Progress (68%)",
                "duration_hrs": 4.5,
                "suit_power_wh": 1420,
                "tool_assigned": "Cryo-Drill Rig & Heated Vacuum Sieve"
            },
            {
                "id": "EVA-102",
                "title": "Antigravity Magnetic Guide-Track Alignment",
                "site": "Valles Marineris Lift Corridor",
                "crew": "Cmdr. Elena Rostova",
                "priority": "CRITICAL",
                "status": "Active (Nominal)",
                "duration_hrs": 3.0,
                "suit_power_wh": 950,
                "tool_assigned": "Superconducting Vector Field Calibrator"
            },
            {
                "id": "EVA-103",
                "title": "Microwave Sintering of Regolith Radiation Shield",
                "site": "Jezero Delta Habitat Alpha",
                "crew": "Dr. Aris Thorne",
                "priority": "HIGH",
                "status": "Scheduled (Next Sol)",
                "duration_hrs": 6.0,
                "suit_power_wh": 1890,
                "tool_assigned": "Thermal Microwave Sintering Rover"
            },
            {
                "id": "EVA-104",
                "title": "Lava Tube Structural Sensor Deployment",
                "site": "Olympus Mons High Caldera Base",
                "crew": "Specialist Wei Chen",
                "priority": "MEDIUM",
                "status": "Completed (Logged)",
                "duration_hrs": 5.2,
                "suit_power_wh": 1640,
                "tool_assigned": "Seismic Sensor Node Array"
            }
        ]

    def simulate_dust_storm(self, severity="normal"):
        """
        Martian dust storm impact simulation on operations, optical depth, solar power, and rover range.
        """
        scenarios = {
            "clear": {
                "label": "Clear Atmosphere (Nominal)",
                "tau": 0.35,
                "solar_power_pct": 100,
                "visibility_km": 45.0,
                "wheeled_rover_status": "100% OPERATIONAL",
                "antigrav_status": "OPTIMAL (Cruise 18 km/h)",
                "alert_level": "GREEN (Nominal)",
                "color": "#10b981"
            },
            "regional": {
                "label": "Regional Dust Storm (Active)",
                "tau": 1.75,
                "solar_power_pct": 38,
                "visibility_km": 4.2,
                "wheeled_rover_status": "CAUTION: Speed reduced to 0.08 km/h. Solar arrays blocked by 62%.",
                "antigrav_status": "NOMINAL: Micro-fusion driven. Operating at 14 km/h.",
                "alert_level": "AMBER (Regional Warning)",
                "color": "#f59e0b"
            },
            "global": {
                "label": "Global Planet-Encircling Storm (Severe)",
                "tau": 4.60,
                "solar_power_pct": 8,
                "visibility_km": 0.3,
                "wheeled_rover_status": "GROUNDED: Solar depletion imminent. Emergency sleep mode engaged.",
                "antigrav_status": "MISSION ESSENTIAL: Sole operational transport. Radio-beacon radar active.",
                "alert_level": "RED (Planetary Emergency)",
                "color": "#ef4444"
            }
        }
        return scenarios.get(severity, scenarios["clear"])

    def get_cross_sections(self):
        """Topographic cross-section profiles for major Martian geological monuments."""
        return {
            "olympus": {
                "name": "Olympus Mons (Shield Volcano & 6-km Basal Scarp)",
                "relief_m": 23287,
                "highest_point_m": 21287,
                "lowest_point_m": -2000,
                "labels": ["Plains (0km)", "Outer Apron (50km)", "Basal Scarp (100km)", "Lower Flank (200km)", "Caldera Rim (300km)", "Caldera Floor (350km)", "East Flank (450km)", "Tharsis (600km)"],
                "elevations": [-2000, 500, 6000, 12500, 21287, 18500, 11000, -1800],
                "antigrav_altitude": [2000, 3000, 7500, 14000, 22500, 22500, 13000, 1000],
                "hazards": ["6,000m sheer vertical basal cliff", "Near-vacuum atmospheric boundary", "Unclimbable for wheeled rovers"]
            },
            "valles": {
                "name": "Valles Marineris (Coprates & Melas Chasma Abyss)",
                "relief_m": 11300,
                "highest_point_m": 4200,
                "lowest_point_m": -7100,
                "labels": ["North Rim (0km)", "Upper Step (40km)", "Debris Fan (70km)", "Abyss Floor (120km)", "Interior Mound (180km)", "Fault Scarp (240km)", "South Terraces (290km)", "South Rim (320km)"],
                "elevations": [4200, 3100, -1200, -7100, -6800, -2500, 2800, 3950],
                "antigrav_altitude": [4500, 4200, 3500, 2000, 2200, 3500, 4200, 4500],
                "hazards": ["7,000m vertical drop", "Massive landslide boulder fields", "40° cliff slopes"]
            },
            "gale": {
                "name": "Gale Crater & Mount Sharp (Aeolis Mons Sediment)",
                "relief_m": 10000,
                "highest_point_m": 5500,
                "lowest_point_m": -4500,
                "labels": ["North Rim (0km)", "Bradbury Landing (30km)", "Yellowknife (65km)", "Lower Mound (95km)", "Peak (120km)", "South Moat (150km)"],
                "elevations": [-1200, -4450, -3800, 500, 5500, -2100],
                "antigrav_altitude": [-800, -3500, -2800, 1500, 6200, -1000],
                "hazards": ["Loose sand dunes (Bagnold)", "Steep clay-sulfate transition", "Sharp ventifact rocks"]
            }
        }

    def query_ode_products(self, lat, lon, limit=4):
        """Queries live Washington University Mars ODE API for PDS satellite elevation and radar records."""
        url = "https://oderest.rsl.wustl.edu/live2/"
        params = {
            "target": "mars",
            "query": "product",
            "results": "fp",
            "output": "JSON",
            "ihid": "MGS",
            "iid": "MOLA",
            "pt": "MEGDR",
            "minlat": max(-90.0, lat - 8.0),
            "maxlat": min(90.0, lat + 8.0),
            "westlon": (lon - 8.0) % 360.0,
            "eastlon": (lon + 8.0) % 360.0,
            "limit": limit
        }
        import urllib.parse
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(full_url, headers={"User-Agent": "MartianMapPlatform/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                products = data.get("ODEResults", {}).get("Products", {}).get("Product", [])
                if isinstance(products, dict):
                    products = [products]
                return [{
                    "pds_id": p.get("pdsid"),
                    "title": f"MOLA Topography: {p.get('pdsid', 'MEGDR')}",
                    "instrument": "Mars Global Surveyor / MOLA",
                    "type": p.get("Product_type", "Elevation Grid"),
                    "center_lat": p.get("Center_latitude"),
                    "center_lon": p.get("Center_longitude"),
                    "pds_url": f"https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/{p.get('pdsid', 'megt90n000cb').lower()}.img"
                } for p in products]
        except Exception:
            # Clean offline fallback
            return [
                {
                    "pds_id": "MEGT90N000EB",
                    "title": "MOLA Global Topographic Elevation Grid (16 pix/deg)",
                    "instrument": "MGS / MOLA (NASA PDS)",
                    "type": "MEGDR Topography",
                    "center_lat": round(lat, 2),
                    "center_lon": round(lon, 2),
                    "pds_url": "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/"
                },
                {
                    "pds_id": "MEGA90N000EB",
                    "title": "MOLA Areoid Planetary Radius Elevation Reference",
                    "instrument": "MGS / MOLA (NASA PDS)",
                    "type": "Shapefile & DTM",
                    "center_lat": round(lat, 2),
                    "center_lon": round(lon, 2),
                    "pds_url": "https://oderest.rsl.wustl.edu/"
                }
            ]
        grid = []
        for lat in range(-80, 85, 10):
            for lon_leaflet in range(-180, 185, 15):
                # Sample elevation
                lon_east = lon_leaflet % 360.0
                elev = 0.0
                if self.mola_grid is not None:
                    r = int(np.clip((90.0 - lat) * 16.0, 0, 2879))
                    c = int(np.clip(lon_east * 16.0, 0, 5759))
                    elev = float(self.mola_grid[r, c])
                
                t = self.get_temperature_and_thermal(lat, lon_leaflet, elev, is_night)
                grid.append({
                    "lat": lat,
                    "lon": lon_leaflet,
                    "elev": round(elev, 0),
                    "temp_c": t["temp_c"],
                    "rad": t["radiation_msv_day"]
                })
        return grid

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
