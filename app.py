import io
import json
import sqlite3
from flask import Flask, render_template, request, jsonify, send_file, Response
from mars_engine import MarsEngine, DB_FILE

app = Flask(__name__)
engine = MarsEngine()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/telemetry")
def get_telemetry():
    """Returns dynamic Martian operational telemetry."""
    return jsonify({
        "mission_name": "Ares Operational Vanguard",
        "martian_sol": 842,
        "solar_longitude_ls": 142.6,
        "season": "Northern Autumn / Southern Spring",
        "avg_surface_temp_c": -63.5,
        "dust_optical_depth_tau": 0.42,
        "active_gmz_count": 5,
        "antigrav_fleet_readiness": "100% NOMINAL",
        "atmospheric_datum_p0_pa": 610.0
    })

@app.route("/api/gravity-zones")
def get_gravity_zones():
    """Fetches Gravity-Manipulation Zones (GMZs) for operational mapping."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM gravity_zones")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/outposts")
def get_outposts():
    """Fetches Mars human outposts and historical landing sites."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM mars_outposts")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/hirise")
def get_hirise_list():
    """
    Returns captioned HiRISE surface observations.
    Supports ?limit=100 and ?search=term.
    """
    limit = min(200, int(request.args.get("limit", 60)))
    search = request.args.get("search", "").strip()
    
    conn = get_db()
    cur = conn.cursor()
    if search:
        cur.execute('''
            SELECT obs_id, title, lat, lon_east, lon_leaflet, elevation, caption, acquisition_date, spacecraft_altitude, scale
            FROM hirise_observations
            WHERE title LIKE ? OR caption LIKE ?
            LIMIT ?
        ''', (f"%{search}%", f"%{search}%", limit))
    else:
        # Return a diverse sample
        cur.execute('''
            SELECT obs_id, title, lat, lon_east, lon_leaflet, elevation, caption, acquisition_date, spacecraft_altitude, scale
            FROM hirise_observations
            ORDER BY RANDOM()
            LIMIT ?
        ''', (limit,))
        
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d["real_image_path"] = f"F:\\mars details for building website\\archive mars surface images\\captioned\\images\\{d['obs_id']}.jpg"
        rows.append(d)
    conn.close()
    return jsonify(rows)

@app.route("/api/hirise/nearest")
def get_nearest_hirise():
    """Finds the nearest real NASA HiRISE observation and its real image path for any (lat, lon)."""
    try:
        lat = float(request.args.get("lat", 18.38))
        lon = float(request.args.get("lon", 77.58))
    except (ValueError, TypeError):
        lat, lon = 18.38, 77.58

    result = engine.find_nearest_hirise(lat, lon)
    return jsonify(result)

@app.route("/api/hirise/image/<obs_id>")
def get_hirise_image(obs_id):
    """Streams a 50 cm/pixel HiRISE image directly out of the local disk archive or 4.4 GB zip file."""
    img_data = engine.get_hirise_image_bytes(obs_id)
    if img_data is None:
        return Response("Image not found in archive", status=404, mimetype="text/plain")
    return send_file(io.BytesIO(img_data), mimetype="image/jpeg")

@app.route("/api/routes")
def get_preset_routes():
    """Fetches pre-calculated Antigravity vs Wheeled traversal corridors."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM antigravity_routes")
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        d["route_geometry"] = json.loads(d["route_geometry_json"])
        del d["route_geometry_json"]
        rows.append(d)
    conn.close()
    return jsonify(rows)

@app.route("/api/route/custom", methods=["GET", "POST"])
def get_custom_route():
    """
    Calculates dynamic route metrics and waypoints between any two coordinates.
    """
    try:
        if request.method == "POST":
            data = request.get_json(force=True)
            lat1 = float(data.get("lat1"))
            lon1 = float(data.get("lon1"))
            lat2 = float(data.get("lat2"))
            lon2 = float(data.get("lon2"))
        else:
            lat1 = float(request.args.get("lat1", 18.38))
            lon1 = float(request.args.get("lon1", 77.58))
            lat2 = float(request.args.get("lat2", -14.00))
            lon2 = float(request.args.get("lon2", -59.00))

        result = engine.calculate_custom_route(lat1, lon1, lat2, lon2)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/elevation/query")
def query_elevation():
    """Queries MOLA topography, slope, atmospheric pressure, temperature, and radiation at given coordinate."""
    lat = float(request.args.get("lat", 0.0))
    lon = float(request.args.get("lon", 0.0))
    is_night = request.args.get("is_night", "false").lower() == "true"
    res = engine.get_elevation_and_slope(lat, lon)
    if is_night:
        thermal_night = engine.get_temperature_and_thermal(lat, lon, res["elevation_m"], is_night=True)
        res["temperature_c"] = thermal_night["temp_c"]
        res["temperature_k"] = thermal_night["temp_k"]
        res["thermal_zone"] = thermal_night["thermal_zone"]
        res["suit_heating_watts"] = thermal_night["suit_heating_watts"]
    return jsonify(res)

@app.route("/api/thermal/grid")
def get_thermal_grid():
    """Generates global Martian thermal temperature grid for heatmap overlay."""
    is_night = request.args.get("is_night", "false").lower() == "true"
    grid = engine.generate_global_thermal_grid(is_night=is_night)
    return jsonify({
        "diurnal_cycle": "Nighttime" if is_night else "Daytime (Solar Noon)",
        "grid_points": grid
    })

@app.route("/api/physics-sim", methods=["GET", "POST"])
def run_physics_sim():
    """Interactive gravity physics simulation comparing Earth, Mars, and Antigravity."""
    if request.method == "POST":
        data = request.get_json(force=True)
        mass = float(data.get("mass_kg", 5000.0))
        height = float(data.get("lift_height_m", 3.0))
        dist = float(data.get("transport_dist_km", 5.0))
        geff = float(data.get("antigrav_geff", 0.05))
    else:
        mass = float(request.args.get("mass_kg", 5000.0))
        height = float(request.args.get("lift_height_m", 3.0))
        dist = float(request.args.get("transport_dist_km", 5.0))
        geff = float(request.args.get("antigrav_geff", 0.05))

    sim = engine.simulate_physics(mass, height, dist, geff)
    return jsonify(sim)

@app.route("/api/ice-deposits")
def get_ice_deposits():
    """Returns NASA SHARAD radar data on subsurface water ice glaciers."""
    return jsonify(engine.get_subsurface_ice_sheets())

@app.route("/api/eva-tasks")
def get_eva_tasks():
    """Returns live Astronaut EVA operational task dispatch list."""
    return jsonify(engine.get_astronaut_eva_tasks())

@app.route("/api/dust-storm")
def get_dust_storm_simulation():
    """Simulates Martian dust storm severity and its impact on power, visibility, and rovers."""
    severity = request.args.get("severity", "clear").lower()
    return jsonify(engine.simulate_dust_storm(severity))

@app.route("/api/topography/cross-sections")
def get_topography_cross_sections():
    """Returns detailed elevation profile cross-sections for major Martian geological features."""
    return jsonify(engine.get_cross_sections())

@app.route("/api/ode/search")
def search_ode_satellite_products():
    """Queries live Washington University ODE API for NASA satellite elevation and radar records."""
    lat = float(request.args.get("lat", 18.65))
    lon = float(request.args.get("lon", 226.20))
    limit = int(request.args.get("limit", 4))
    products = engine.query_ode_products(lat, lon, limit)
    return jsonify({"sector_lat": lat, "sector_lon": lon, "products": products})

if __name__ == "__main__":
    print("\n=======================================================")
    print("  NASA Space Apps: Interplanetary Survival Guide Map   ")
    print("  Server running on http://127.0.0.1:5000              ")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
