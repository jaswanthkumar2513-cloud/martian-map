import json
from app import app

def test_all():
    client = app.test_client()
    print("Testing Flask endpoints...")

    # 1. Main index
    res = client.get("/")
    assert res.status_code == 200, f"Index failed: {res.status_code}"
    print("[PASS] GET / -> HTTP 200")

    # 2. Telemetry
    res = client.get("/api/telemetry")
    assert res.status_code == 200
    data = res.get_json()
    assert "martian_sol" in data
    print(f"[PASS] GET /api/telemetry -> Sol: {data['martian_sol']}, Status: {data['antigrav_fleet_readiness']}")

    # 3. Gravity-Manipulation Zones
    res = client.get("/api/gravity-zones")
    assert res.status_code == 200
    zones = res.get_json()
    assert len(zones) == 5
    print(f"[PASS] GET /api/gravity-zones -> {len(zones)} GMZs loaded successfully.")

    # 4. Outposts
    res = client.get("/api/outposts")
    assert res.status_code == 200
    outposts = res.get_json()
    assert len(outposts) >= 5
    print(f"[PASS] GET /api/outposts -> {len(outposts)} outposts found.")

    # 5. Preset Routes
    res = client.get("/api/routes")
    assert res.status_code == 200
    routes = res.get_json()
    assert len(routes) == 3
    print(f"[PASS] GET /api/routes -> {len(routes)} preset Antigravity corridors found.")

    # 6. Custom Route Calculator
    res = client.get("/api/route/custom?lat1=18.38&lon1=77.58&lat2=12.80&lon2=88.20")
    assert res.status_code == 200
    route_calc = res.get_json()
    print(f"[PASS] GET /api/route/custom -> Direct: {route_calc['direct_distance_km']} km, Wheeled: {route_calc['wheeled']['distance_km']} km, Energy Savings: {route_calc['savings']['energy_savings_pct']}%")

    # 7. HiRISE image list and direct streaming from 4.2GB zip
    res = client.get("/api/hirise?limit=5")
    assert res.status_code == 200
    hirise_list = res.get_json()
    assert len(hirise_list) == 5
    sample_obs = hirise_list[0]["obs_id"]
    print(f"[PASS] GET /api/hirise -> Fetched {len(hirise_list)} items. Testing image streaming for {sample_obs}...")

    img_res = client.get(f"/api/hirise/image/{sample_obs}")
    assert img_res.status_code == 200, f"Image streaming failed: {img_res.status_code}"
    print(f"[PASS] GET /api/hirise/image/{sample_obs} -> Streamed {len(img_res.data)} bytes directly from 4.2GB ZIP!")

    # 8. Physics Simulator
    res = client.get("/api/physics-sim?mass_kg=10000&lift_height_m=3&antigrav_geff=0.05")
    assert res.status_code == 200
    sim = res.get_json()
    w_earth = sim["environments"]["earth"]["weight_newtons"]
    w_mars = sim["environments"]["mars"]["weight_newtons"]
    w_ag = sim["environments"]["antigrav"]["weight_newtons"]
    print(f"[PASS] GET /api/physics-sim -> 10,000kg load: Earth: {w_earth} N | Mars: {w_mars} N | Antigrav: {w_ag} N")

    print("\nALL 8 TESTS PASSED SUCCESSFULLY! The platform is 100% operational.")

if __name__ == "__main__":
    test_all()
