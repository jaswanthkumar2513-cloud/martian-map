/**
 * Interplanetary Survival Guide: Martian Map
 * Operational Task Mapping & Student Research Platform
 * NASA Space Apps Challenge
 */

let map;
let layerGroups = {
    outposts: L.layerGroup(),
    gmz: L.layerGroup(),
    routes: L.layerGroup(),
    hirise: L.layerGroup(),
    thermal: L.layerGroup(),
    ice: L.layerGroup()
};

let cachedRoutes = [];
let cachedGMZs = [];
let currentRouteIndex = 0;
let gravityChart = null;
let isNightMode = false;
let audioEnabled = true;
let audioCtx = null;
let simInterval = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    loadOutposts();
    loadGMZs();
    loadPresetRoutes();
    loadHiRISEData();
    loadThermalMap();
    loadIceSheets();
    loadEvaTasks();
    initPhysicsSimulator();
    initCrossSectionChart();
});

// ==============================================================
// 1. LEAFLET MAP INITIALIZATION & TILE LAYERS
// ==============================================================
function initMap() {
    // Mars coordinates: center on Jezero Crater (18.38, 77.58)
    map = L.map("marsMap", {
        center: [15.0, 75.0],
        zoom: 3,
        minZoom: 2,
        maxZoom: 9,
        attributionControl: false
    });

    // Custom dark Mars / OpenPlanetary tile layer
    const openPlanetaryMars = L.tileLayer(
        "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png",
        {
            maxZoom: 9,
            tms: false
        }
    );

    // NASA Trek MOLA Color Hillshade Tile Layer (Alternative/Fallback)
    const nasaMolaShade = L.tileLayer(
        "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
        {
            maxZoom: 8,
            tms: false
        }
    );

    // Fallback CartoDB Dark Matter
    const darkFallback = L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        {
            subdomains: "abcd",
            maxZoom: 9
        }
    );

    // Add default layer with graceful fallback
    openPlanetaryMars.addTo(map);
    openPlanetaryMars.on("tileerror", () => {
        if (!map.hasLayer(darkFallback) && !map.hasLayer(nasaMolaShade)) {
            darkFallback.addTo(map);
        }
    });

    // Add layer groups to map
    Object.values(layerGroups).forEach(lg => lg.addTo(map));

    // Dynamic Real-time Cursor Elevation Inspector
    let throttleTimeout;
    map.on("mousemove", (e) => {
        if (throttleTimeout) return;
        throttleTimeout = setTimeout(() => {
            throttleTimeout = null;
            const lat = e.latlng.lat.toFixed(2);
            const lon = e.latlng.lng.toFixed(2);
            document.getElementById("inspLat").innerText = `${lat}°`;
            document.getElementById("inspLon").innerText = `${lon >= 0 ? lon : (360 + parseFloat(lon)).toFixed(2)}°E`;

            // Query MOLA elevation, slope, thermal and radiation at cursor
            fetch(`/api/elevation/query?lat=${lat}&lon=${lon}&is_night=${isNightMode}`)
                .then(res => res.json())
                .then(data => {
                    document.getElementById("inspElev").innerText = `${data.elevation_m.toLocaleString()} m`;
                    const slope = data.slope_deg;
                    let slopeStatus = "Safe";
                    let slopeColor = "text-emerald-400";
                    if (slope > 15.0) {
                        slopeStatus = "Extreme Hazard (>15°)";
                        slopeColor = "text-red-400";
                    } else if (slope > 8.0) {
                        slopeStatus = "Caution (Steep)";
                        slopeColor = "text-amber-400";
                    }
                    const el = document.getElementById("inspSlope");
                    el.className = `${slopeColor} font-bold`;
                    el.innerText = `${slope}° (${slopeStatus})`;

                    // Update Thermal and Radiation in HUD
                    if (data.temperature_c !== undefined) {
                        const tempEl = document.getElementById("inspTemp");
                        if (tempEl) {
                            tempEl.innerText = `${data.temperature_c}°C`;
                            tempEl.className = data.temperature_c > -30 ? "text-amber-400 font-bold" : (data.temperature_c > -70 ? "text-rose-400 font-bold" : "text-cyan-300 font-bold");
                        }
                        const radEl = document.getElementById("inspRad");
                        if (radEl) radEl.innerText = `${data.radiation_msv_day} mSv/d`;

                        // Update Astronaut Operations Console
                        const opsTemp = document.getElementById("opsTempDisplay");
                        if (opsTemp) opsTemp.innerText = `${data.temperature_c}°C (${data.temperature_k} K)`;
                        const opsSuit = document.getElementById("opsSuitWatts");
                        if (opsSuit) opsSuit.innerText = `${data.suit_heating_watts} Watts`;
                        const opsRad = document.getElementById("opsRadLevel");
                        if (opsRad) opsRad.innerText = `${data.radiation_msv_day} mSv / day`;
                        const badgeZone = document.getElementById("badgeThermalZone");
                        if (badgeZone && data.thermal_zone) badgeZone.innerText = data.thermal_zone.toUpperCase();
                    }
                })
                .catch(() => {});
        }, 120);
    });
}

// Layer visibility toggles
function toggleMapLayer(layerName) {
    const isChecked = document.getElementById(`layer${layerName.charAt(0).toUpperCase() + layerName.slice(1)}`).checked;
    if (isChecked) {
        map.addLayer(layerGroups[layerName]);
        if (layerName === "thermal" && layerGroups.thermal.getLayers().length === 0) {
            loadThermalMap();
        }
    } else {
        map.removeLayer(layerGroups[layerName]);
    }
}

// Global Thermal Map Loader
function loadThermalMap() {
    fetch(`/api/thermal/grid?is_night=${isNightMode}`)
        .then(res => res.json())
        .then(data => {
            layerGroups.thermal.clearLayers();
            data.grid_points.forEach(pt => {
                const t = pt.temp_c;
                let color = "#38bdf8"; // Arctic ice blue
                if (t > 0) color = "#ef4444"; // Warm red
                else if (t > -30) color = "#f97316"; // Orange
                else if (t > -60) color = "#c084fc"; // Violet
                else if (t > -90) color = "#06b6d4"; // Cyan

                const circle = L.circle([pt.lat, pt.lon], {
                    radius: 380000,
                    color: "transparent",
                    fillColor: color,
                    fillOpacity: isNightMode ? 0.35 : 0.28,
                    interactive: true
                }).addTo(layerGroups.thermal);

                circle.bindTooltip(`
                    <div class="font-mono text-xs p-1 bg-space-950 text-slate-100 rounded border border-space-700">
                        <span class="font-bold block" style="color:${color}">Surface Temp: ${t}°C (${(t + 273.15).toFixed(1)} K)</span>
                        <span class="text-slate-300 text-[10px]">Elevation: ${pt.elev.toLocaleString()} m</span><br>
                        <span class="text-purple-300 text-[10px]">Cosmic Rad: ${pt.rad} mSv/day</span>
                    </div>
                `, { sticky: true });
            });
        })
        .catch(err => console.log("Thermal grid error:", err));
}

// Diurnal Day/Night Cycle Switcher
function toggleDiurnalCycle() {
    isNightMode = !isNightMode;
    const lbl = document.getElementById("lblDiurnal");
    const icon = document.getElementById("iconDiurnal");
    const btn = document.getElementById("btnDiurnal");
    if (isNightMode) {
        lbl.innerText = "Polar Night";
        icon.className = "fa-solid fa-moon text-cyan-400 text-[10px]";
        btn.className = "px-2 py-0.5 rounded bg-space-800 border border-cyan-500/50 text-[10px] text-cyan-300 font-mono flex items-center space-x-1 hover:bg-space-700";
    } else {
        lbl.innerText = "Solar Noon";
        icon.className = "fa-solid fa-sun text-amber-400 text-[10px]";
        btn.className = "px-2 py-0.5 rounded bg-space-800 border border-amber-500/50 text-[10px] text-amber-300 font-mono flex items-center space-x-1 hover:bg-space-700";
    }
    loadThermalMap();
}

// ==============================================================
// 2. DATA LOADERS (OUTPOSTS, GMZ, HIRISE, ROUTES)
// ==============================================================

function loadOutposts() {
    fetch("/api/outposts")
        .then(res => res.json())
        .then(outposts => {
            layerGroups.outposts.clearLayers();
            outposts.forEach(p => {
                const icon = L.divIcon({
                    className: "custom-outpost-icon",
                    html: `
                        <div class="relative group cursor-pointer">
                            <div class="w-7 h-7 rounded-full bg-space-950 border-2 border-amber-400 flex items-center justify-center shadow-lg shadow-amber-500/30 hover:scale-125 transition-transform">
                                <i class="fa-solid fa-flag text-amber-400 text-xs"></i>
                            </div>
                        </div>
                    `,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14]
                });

                const marker = L.marker([p.lat, p.lon_leaflet], { icon }).addTo(layerGroups.outposts);
                marker.bindPopup(`
                    <div class="bg-space-900 text-slate-100 p-2 font-mono text-xs max-w-xs">
                        <div class="font-bold text-amber-400 border-b border-space-700 pb-1 mb-1 uppercase tracking-wider">${p.name}</div>
                        <div class="text-[11px] text-slate-300 mb-1">${p.description}</div>
                        <div class="text-[10px] text-slate-400">Elevation: <span class="text-cyan-300 font-bold">${p.elevation.toLocaleString()} m</span></div>
                        <div class="text-[10px] text-slate-400">Status: <span class="text-emerald-400 font-bold">${p.status}</span></div>
                    </div>
                `);
            });
        });
}

function loadGMZs() {
    fetch("/api/gravity-zones")
        .then(res => res.json())
        .then(zones => {
            cachedGMZs = zones;
            layerGroups.gmz.clearLayers();
            const container = document.getElementById("gmzListContainer");
            container.innerHTML = "";

            zones.forEach((z, index) => {
                // Circle representing the gravity field radius
                const circle = L.circle([z.lat, z.lon_leaflet], {
                    radius: z.radius_km * 1000,
                    color: "#c084fc",
                    weight: 2,
                    opacity: 0.85,
                    fillColor: "#9333ea",
                    fillOpacity: 0.18,
                    dashArray: "4, 6"
                }).addTo(layerGroups.gmz);

                // Center Pulsating GMZ Marker
                const gmzIcon = L.divIcon({
                    className: "pulse-gmz",
                    html: `
                        <div class="w-6 h-6 rounded-full bg-purple-600/80 border-2 border-purple-300 flex items-center justify-center shadow-lg shadow-purple-500/50">
                            <i class="fa-solid fa-atom text-white text-[10px]"></i>
                        </div>
                    `,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });

                const marker = L.marker([z.lat, z.lon_leaflet], { icon: gmzIcon }).addTo(layerGroups.gmz);
                
                const popupContent = `
                    <div class="bg-space-950 text-slate-100 p-2.5 font-mono text-xs max-w-sm rounded border border-purple-500/40">
                        <div class="flex items-center justify-between border-b border-purple-800 pb-1 mb-2">
                            <span class="font-bold text-purple-300 uppercase">${z.code}: ${z.name}</span>
                            <span class="text-[10px] bg-purple-900 text-purple-200 px-1.5 py-0.5 rounded">${z.field_strength_g} g</span>
                        </div>
                        <p class="text-[11px] text-slate-300 mb-2">${z.purpose}</p>
                        <div class="bg-space-900 p-1.5 rounded mb-2 border border-space-700">
                            <span class="text-[10px] text-slate-400 block">ACTIVE HEAVY-LIFT TASK:</span>
                            <span class="text-cyan-300 font-bold text-[11px]">${z.active_payload}</span>
                        </div>
                        <div class="text-[10px] text-slate-400">Power: <span class="text-amber-400 font-bold">${z.power_mw} MW</span> • Radius: <span class="text-white">${z.radius_km} km</span></div>
                        <div class="text-[10px] text-emerald-400 mt-1 italic">${z.mitigation}</div>
                    </div>
                `;

                circle.bindPopup(popupContent);
                marker.bindPopup(popupContent);

                // Add to Side HUD Card
                const card = document.createElement("div");
                card.className = "bg-space-900/90 border border-space-700 hover:border-purple-500/70 p-2.5 rounded cursor-pointer transition-all";
                card.onclick = () => {
                    map.flyTo([z.lat, z.lon_leaflet], 6, { duration: 1.5 });
                    marker.openPopup();
                };
                card.innerHTML = `
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-bold text-purple-300 font-mono">${z.code}</span>
                        <span class="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-1.5 py-0.5 rounded">g_eff = ${z.field_strength_g}g</span>
                    </div>
                    <div class="text-[11px] text-slate-200 font-medium mt-0.5">${z.name}</div>
                    <div class="text-[10px] text-slate-400 mt-1 truncate">Payload: ${z.active_payload}</div>
                `;
                container.appendChild(card);
            });
        });
}

function loadPresetRoutes() {
    fetch("/api/routes")
        .then(res => res.json())
        .then(routes => {
            cachedRoutes = routes;
            displayRoute(0);
        });
}

function displayRoute(index) {
    if (!cachedRoutes || cachedRoutes.length === 0) return;
    const r = cachedRoutes[index];
    currentRouteIndex = index;

    // Update HUD Scorecards
    document.getElementById("routeWheeledDist").innerText = `${r.wheeled_dist_km.toLocaleString()} km`;
    document.getElementById("routeWheeledTime").innerText = `${r.wheeled_time_hrs.toLocaleString()} hrs (${(r.wheeled_time_hrs / 24.66).toFixed(1)} Sols)`;
    document.getElementById("routeAgDist").innerText = `${r.antigrav_dist_km.toLocaleString()} km`;
    document.getElementById("routeAgTime").innerText = `${r.antigrav_time_hrs.toLocaleString()} hrs`;
    document.getElementById("routeSavingsEnergy").innerText = `${r.energy_savings_pct}%`;
    document.getElementById("routeSavingsTime").innerText = `${(((r.wheeled_time_hrs - r.antigrav_time_hrs) / r.wheeled_time_hrs) * 100).toFixed(1)}% Faster`;
    document.getElementById("routeObstacleNote").innerText = r.obstacle_description;

    // Render Routes on Leaflet
    layerGroups.routes.clearLayers();

    // 1. Wheeled Route (Dashed Mars Red/Orange)
    const wheeledPoly = L.polyline(r.route_geometry.wheeled, {
        color: "#f97316",
        weight: 3.5,
        opacity: 0.85,
        dashArray: "6, 8"
    }).addTo(layerGroups.routes);
    wheeledPoly.bindPopup(`
        <div class="font-mono text-xs text-slate-200 bg-space-950 p-2">
            <span class="text-mars font-bold block mb-1">CONVENTIONAL WHEELED ROVER PATH</span>
            <span>Distance: ${r.wheeled_dist_km} km</span><br>
            <span>Time: ${r.wheeled_time_hrs} hours</span><br>
            <span class="text-amber-400 text-[10px] block mt-1">Forced to take switchbacks around crater rims and boulder fields.</span>
        </div>
    `);

    // 2. Antigravity Glide Corridor (Neon Cyan Glow)
    // Outer glow
    L.polyline(r.route_geometry.antigrav, {
        color: "#00f0ff",
        weight: 8,
        opacity: 0.25
    }).addTo(layerGroups.routes);

    // Inner bright core
    const agPoly = L.polyline(r.route_geometry.antigrav, {
        color: "#00f0ff",
        weight: 3.5,
        opacity: 0.95
    }).addTo(layerGroups.routes);

    agPoly.bindPopup(`
        <div class="font-mono text-xs text-slate-200 bg-space-950 p-2">
            <span class="text-cyan-400 font-bold block mb-1">ANTIGRAVITY GLIDE CORRIDOR</span>
            <span>Distance: ${r.antigrav_dist_km} km (Direct Geodesic)</span><br>
            <span>Time: ${r.antigrav_time_hrs} hours (16.5 km/h)</span><br>
            <span class="text-emerald-400 text-[10px] block mt-1">Zero terrain friction • Bypasses cliffs, dunes, and boulders effortlessly.</span>
        </div>
    `);

    // Fit map bounds to view the route
    const allCoords = r.route_geometry.wheeled.concat(r.route_geometry.antigrav);
    map.fitBounds(L.latLngBounds(allCoords), { padding: [50, 50], maxZoom: 6 });
}

function onRouteSelected() {
    const idx = parseInt(document.getElementById("routeSelect").value);
    displayRoute(idx);
}

function loadHiRISEData() {
    fetch("/api/hirise?limit=65")
        .then(res => res.json())
        .then(images => {
            layerGroups.hirise.clearLayers();
            images.forEach(img => {
                const icon = L.divIcon({
                    className: "custom-hirise-icon",
                    html: `
                        <div class="w-5 h-5 rounded-full bg-space-950 border border-emerald-400 flex items-center justify-center hover:scale-150 transition-all cursor-pointer shadow-md shadow-emerald-500/20">
                            <i class="fa-solid fa-camera text-emerald-400 text-[9px]"></i>
                        </div>
                    `,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                const marker = L.marker([img.lat, img.lon_leaflet], { icon }).addTo(layerGroups.hirise);
                marker.on("click", () => {
                    openHiRISEViewer(img);
                });
            });
        });
}

function openHiRISEViewer(img) {
    // Update Side HUD Card
    const card = document.getElementById("hiriseInspectorCard");
    card.innerHTML = `
        <div class="border border-emerald-500/40 bg-space-900 p-2.5 rounded space-y-2">
            <div class="flex items-center justify-between">
                <span class="text-[11px] font-bold text-emerald-400 font-mono">${img.obs_id}</span>
                <span class="text-[10px] text-slate-400">${img.acquisition_date}</span>
            </div>
            <div class="font-semibold text-slate-100 text-xs">${img.title}</div>
            <div class="relative rounded overflow-hidden cursor-pointer group" onclick='openModalDirect(${JSON.stringify(JSON.stringify(img))})'>
                <img src="/api/hirise/image/${img.obs_id}" alt="${img.title}" class="w-full h-32 object-cover rounded group-hover:scale-105 transition-transform duration-300">
                <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-cyan-300 text-xs font-mono">
                    <i class="fa-solid fa-expand mr-1.5"></i> Click to Enlarge (50cm/px)
                </div>
            </div>
            <p class="text-[11px] text-slate-300 leading-snug line-clamp-3">${img.caption}</p>
            <div class="text-[10px] text-emerald-300 font-mono break-all bg-space-950 p-1.5 rounded border border-emerald-500/30 select-all">
                <span class="text-emerald-400 font-bold block mb-0.5"><i class="fa-solid fa-folder-open mr-1"></i>Real Image Path:</span>
                ${img.real_image_path || `F:\\mars details for building website\\archive mars surface images\\captioned\\images\\${img.obs_id}.jpg`}
            </div>
            <div class="text-[10px] text-slate-400 font-mono flex items-center justify-between pt-1 border-t border-space-700">
                <span>Elev: <strong class="text-cyan-300">${img.elevation}m</strong></span>
                <span>Altitude: <strong class="text-amber-400">${img.spacecraft_altitude}</strong></span>
            </div>
        </div>
    `;

    // Also open modal
    openModal(img);
}

function openModal(img) {
    document.getElementById("modalTitle").innerText = `${img.obs_id}: ${img.title}`;
    document.getElementById("modalCoords").innerText = `${img.lat.toFixed(3)}°, ${img.lon_east ? img.lon_east.toFixed(3) : ''}°E`;
    document.getElementById("modalDate").innerText = img.acquisition_date || "NASA PDS Archive";
    document.getElementById("modalAltitude").innerText = img.spacecraft_altitude || "250.0 km";
    document.getElementById("modalCaption").innerText = img.caption || "HiRISE orbital observation.";

    const realPath = img.real_image_path || `F:\\mars details for building website\\archive mars surface images\\captioned\\images\\${img.obs_id}.jpg`;
    const realPathEl = document.getElementById("modalRealPath");
    if (realPathEl) realPathEl.innerText = realPath;

    const imgEl = document.getElementById("modalImage");
    const loadingEl = document.getElementById("modalLoading");
    loadingEl.classList.remove("hidden");
    imgEl.src = `/api/hirise/image/${img.obs_id}`;
    imgEl.onload = () => loadingEl.classList.add("hidden");

    document.getElementById("hiriseModal").classList.remove("hidden");
}

function openModalDirect(imgJsonStr) {
    const img = JSON.parse(imgJsonStr);
    openModal(img);
}

function closeModal() {
    document.getElementById("hiriseModal").classList.add("hidden");
}

// ==============================================================
// 3. DUAL-MODE CONTROLLER
// ==============================================================
function switchMode(mode) {
    const panelOps = document.getElementById("panelOps");
    const panelEdu = document.getElementById("panelEdu");
    const btnOps = document.getElementById("btnModeOps");
    const btnEdu = document.getElementById("btnModeEdu");

    if (mode === "ops") {
        panelOps.classList.remove("hidden");
        panelEdu.classList.add("hidden");
        btnOps.className = "flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm shadow-cyan-500/20";
        btnEdu.className = "flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all text-slate-400 hover:text-slate-200";
    } else {
        panelOps.classList.add("hidden");
        panelEdu.classList.remove("hidden");
        btnEdu.className = "flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all bg-purple-600/30 text-purple-300 border border-purple-500/50 shadow-sm shadow-purple-500/20";
        btnOps.className = "flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-semibold transition-all text-slate-400 hover:text-slate-200";
        
        // Trigger Chart.js refresh for student simulator
        setTimeout(() => {
            if (gravityChart) gravityChart.resize();
        }, 150);
    }
}

// ==============================================================
// 4. STUDENT RESEARCH LAB: GRAVITY & PHYSICS SIMULATOR
// ==============================================================

function initPhysicsSimulator() {
    const ctx = document.getElementById("chartGravityWeight").getContext("2d");
    gravityChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Earth (1.0g)", "Mars (0.38g)", "Antigravity (0.05g)"],
            datasets: [{
                label: "Payload Weight (Newtons)",
                data: [49033, 18604, 2451],
                backgroundColor: ["#3b82f6", "#f97316", "#c084fc"],
                borderColor: ["#60a5fa", "#fb923c", "#e9d5ff"],
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: "#1e293b" },
                    ticks: { color: "#94a3b8", font: { family: "monospace", size: 9 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#cbd5e1", font: { family: "monospace", size: 10 } }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });

    onPhysicsChanged();
}

function setMass(kg) {
    document.getElementById("sliderMass").value = kg;
    onPhysicsChanged();
}

function onPhysicsChanged() {
    const mass = parseFloat(document.getElementById("sliderMass").value);
    document.getElementById("sliderMassDisplay").innerText = `${mass.toLocaleString()} kg`;

    fetch(`/api/physics-sim?mass_kg=${mass}&lift_height_m=3.0&transport_dist_km=5.0&antigrav_geff=0.05`)
        .then(res => res.json())
        .then(sim => {
            const e = sim.environments;

            // Earth
            document.getElementById("weightEarth").innerText = `${e.earth.weight_newtons.toLocaleString()} N`;
            document.getElementById("feelEarth").innerText = `${e.earth.effective_mass_feeling_kg.toLocaleString()} kg`;

            // Mars
            document.getElementById("weightMars").innerText = `${e.mars.weight_newtons.toLocaleString()} N`;
            document.getElementById("feelMars").innerText = `${e.mars.effective_mass_feeling_kg.toLocaleString()} kg`;

            // Antigravity Field
            document.getElementById("weightAg").innerText = `${e.antigrav.weight_newtons.toLocaleString()} N`;
            document.getElementById("feelAg").innerText = `${e.antigrav.effective_mass_feeling_kg.toLocaleString()} kg`;

            // Astronaut capabilities
            document.getElementById("crewNeeded").innerText = `${e.antigrav.astronauts_to_lift} Astronaut${e.antigrav.astronauts_to_lift > 1 ? 's' : ''} (vs ${e.mars.astronauts_to_lift} on Mars)`;
            document.getElementById("jumpHeight").innerText = `${e.antigrav.jump_height_meters.toFixed(2)} m (vs ${e.mars.jump_height_meters.toFixed(2)}m Mars)`;
            document.getElementById("hangTime").innerText = `${e.antigrav.hang_time_seconds.toFixed(1)}s (vs ${e.mars.hang_time_seconds.toFixed(1)}s Mars)`;
            document.getElementById("simSavings").innerText = `${sim.energy_savings_percentage}% Less Lift Work`;

            // Update Chart
            if (gravityChart) {
                gravityChart.data.datasets[0].data = [
                    e.earth.weight_newtons,
                    e.mars.weight_newtons,
                    e.antigrav.weight_newtons
                ];
                gravityChart.update();
            }
        });
}

function checkAnswer(isCorrect) {
    const fb = document.getElementById("quizFeedback");
    fb.classList.remove("hidden");
    if (isCorrect) {
        fb.className = "text-xs p-2 rounded font-mono bg-emerald-950 border border-emerald-500/50 text-emerald-300";
        fb.innerHTML = "<strong>CORRECT!</strong> Valles Marineris drops up to 7,000 meters with 40° slopes, stopping conventional rovers cold. An Antigravity glider bypasses this barrier effortlessly!";
    } else {
        fb.className = "text-xs p-2 rounded font-mono bg-red-950 border border-red-500/50 text-red-300";
        fb.innerHTML = "<strong>INCORRECT:</strong> Try again! Think about the physical slope and depth of the Martian canyon system.";
    }
}

// ==============================================================
// 5. TOPOGRAPHIC CROSS-SECTION SLICER & ODE SEARCH
// ==============================================================
let crossSectionChart = null;
let cachedCrossSections = null;

function initCrossSectionChart() {
    const ctx = document.getElementById("chartElevationCrossSection");
    if (!ctx) return;

    fetch("/api/topography/cross-sections")
        .then(res => res.json())
        .then(data => {
            cachedCrossSections = data;
            const initial = data.olympus;

            crossSectionChart = new Chart(ctx.getContext("2d"), {
                type: "line",
                data: {
                    labels: initial.labels,
                    datasets: [
                        {
                            label: "Antigravity Flight Corridor",
                            data: initial.antigrav_altitude,
                            borderColor: "#00f0ff",
                            borderWidth: 2,
                            borderDash: [4, 4],
                            pointRadius: 2,
                            tension: 0.3,
                            fill: false
                        },
                        {
                            label: "MOLA Surface Topography",
                            data: initial.elevations,
                            borderColor: "#ea580c",
                            backgroundColor: "rgba(234, 88, 12, 0.25)",
                            borderWidth: 2,
                            pointRadius: 3,
                            pointBackgroundColor: "#fb923c",
                            fill: true,
                            tension: 0.2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            grid: { color: "#1e293b" },
                            ticks: {
                                color: "#94a3b8",
                                font: { family: "monospace", size: 8 },
                                callback: val => `${(val / 1000).toFixed(1)}k m`
                            }
                        },
                        x: {
                            grid: { display: false },
                            ticks: {
                                color: "#64748b",
                                font: { family: "monospace", size: 7 },
                                maxRotation: 30
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: "#cbd5e1",
                                font: { family: "monospace", size: 9 },
                                boxWidth: 10
                            }
                        }
                    }
                }
            });

            selectProfile("olympus");
        });
}

function selectProfile(profileKey) {
    if (!cachedCrossSections || !crossSectionChart) return;
    const p = cachedCrossSections[profileKey];
    if (!p) return;

    // Update stats
    document.getElementById("csRelief").innerText = `${p.relief_m.toLocaleString()} m`;
    document.getElementById("csPeak").innerText = `${p.highest_point_m.toLocaleString()} m`;
    document.getElementById("csBase").innerText = `${p.lowest_point_m.toLocaleString()} m`;

    // Update chart
    crossSectionChart.data.labels = p.labels;
    crossSectionChart.data.datasets[0].data = p.antigrav_altitude;
    crossSectionChart.data.datasets[1].data = p.elevations;
    crossSectionChart.update();
}

function queryCurrentSectorODE() {
    const lat = parseFloat(document.getElementById("inspLat").innerText) || 18.65;
    const lon = parseFloat(document.getElementById("inspLon").innerText) || 226.20;
    const container = document.getElementById("odeResultsContainer");
    container.classList.remove("hidden");
    container.innerHTML = `<div class="text-cyan-400 text-[11px]"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Querying Washington Univ Mars ODE Satellite Catalog...</div>`;

    fetch(`/api/ode/search?lat=${lat}&lon=${lon}&limit=3`)
        .then(res => res.json())
        .then(data => {
            if (!data.products || data.products.length === 0) {
                container.innerHTML = `<div class="text-amber-400">No matching PDS products in this exact sector.</div>`;
                return;
            }
            let html = `<div class="text-[10px] text-slate-400 border-b border-space-700 pb-1 mb-1 font-bold">NASA PDS SATELLITE PRODUCTS (Sector ${lat}°, ${lon}°E):</div>`;
            data.products.forEach(p => {
                html += `
                    <div class="bg-space-950 p-1.5 rounded border border-space-800 text-[10px]">
                        <div class="flex items-center justify-between">
                            <span class="text-cyan-300 font-bold">${p.pds_id}</span>
                            <span class="text-slate-400">${p.type}</span>
                        </div>
                        <div class="text-slate-300 text-[10px]">${p.instrument}</div>
                        <a href="${p.pds_url}" target="_blank" class="text-amber-400 hover:underline text-[9px] block mt-0.5">
                            <i class="fa-solid fa-arrow-up-right-from-square mr-1"></i> Open in NASA PDS Geosciences Archive
                        </a>
                    </div>
                `;
            });
            container.innerHTML = html;
        })
        .catch(err => {
            container.innerHTML = `<div class="text-rose-400">ODE query timed out. Showing cached MOLA MEGDR data.</div>`;
        });
}

// ==============================================================
// 6. SUBSURFACE WATER ICE, DUST STORM, EVA TASKS & SFX
// ==============================================================

function loadIceSheets() {
    fetch("/api/ice-deposits")
        .then(res => res.json())
        .then(deposits => {
            layerGroups.ice.clearLayers();
            deposits.forEach(ice => {
                const circle = L.circle([ice.lat, ice.lon_leaflet], {
                    radius: 260000,
                    color: "#38bdf8",
                    weight: 2,
                    fillColor: "#0284c7",
                    fillOpacity: 0.28,
                    dashArray: "3, 5"
                }).addTo(layerGroups.ice);

                const icon = L.divIcon({
                    className: "ice-sheet-icon",
                    html: `
                        <div class="w-5 h-5 rounded-full bg-cyan-950 border-2 border-cyan-300 flex items-center justify-center shadow-lg shadow-cyan-400/50 hover:scale-125 transition-transform cursor-pointer">
                            <i class="fa-solid fa-icicles text-cyan-300 text-[10px]"></i>
                        </div>
                    `,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                const marker = L.marker([ice.lat, ice.lon_leaflet], { icon }).addTo(layerGroups.ice);
                
                const popup = `
                    <div class="bg-space-950 p-2.5 rounded border border-cyan-400/50 text-xs font-mono text-slate-100 max-w-xs">
                        <div class="flex items-center justify-between border-b border-cyan-800 pb-1 mb-1.5">
                            <span class="font-bold text-cyan-300">${ice.code}: ${ice.name}</span>
                            <span class="text-[10px] bg-cyan-900 text-cyan-200 px-1.5 py-0.5 rounded">${ice.purity_pct}% Purity</span>
                        </div>
                        <div class="text-[11px] text-slate-300 mb-1.5">${ice.mission_value}</div>
                        <div class="text-[10px] text-slate-400 space-y-0.5">
                            <div>Depth below surface: <strong class="text-white">${ice.depth_below_surface_m} meters</strong></div>
                            <div>Glacier Thickness: <strong class="text-amber-400">${ice.estimated_thickness_m} meters</strong></div>
                            <div>Water Volume: <strong class="text-cyan-300">${ice.volume_km3.toLocaleString()} km³</strong></div>
                        </div>
                    </div>
                `;
                circle.bindPopup(popup);
                marker.bindPopup(popup);
            });
        });
}

function loadEvaTasks() {
    fetch("/api/eva-tasks")
        .then(res => res.json())
        .then(tasks => {
            const container = document.getElementById("evaTaskContainer");
            if (!container) return;
            container.innerHTML = "";

            tasks.forEach(t => {
                const card = document.createElement("div");
                card.className = "bg-space-900/90 border border-space-700 hover:border-cyan-500/50 p-2.5 rounded text-xs font-mono space-y-1.5 transition-all";
                let priorityColor = t.priority === "CRITICAL" ? "text-rose-400 bg-rose-950 border-rose-500/40" : (t.priority === "HIGH" ? "text-amber-400 bg-amber-950 border-amber-500/40" : "text-cyan-300 bg-cyan-950 border-cyan-500/40");
                
                card.innerHTML = `
                    <div class="flex items-center justify-between">
                        <span class="font-bold text-slate-200">${t.id}: ${t.title}</span>
                        <span class="text-[9px] px-1.5 py-0.5 rounded border ${priorityColor}">${t.priority}</span>
                    </div>
                    <div class="text-[10px] text-slate-400">Assigned: <strong class="text-slate-300">${t.crew}</strong> • Site: <span class="text-cyan-400">${t.site}</span></div>
                    <div class="flex items-center justify-between text-[10px] pt-1 border-t border-space-800">
                        <span class="text-emerald-400 font-semibold">${t.status}</span>
                        <button onclick="playSfx('click'); alert('Telemetry dispatched to suit HUD for ${t.id}')" class="px-2 py-0.5 rounded bg-space-800 hover:bg-cyan-900 text-cyan-300 text-[9px] border border-space-600">Dispatch</button>
                    </div>
                `;
                container.appendChild(card);
            });
        });
}

function setDustStormSeverity(severity) {
    playSfx('alert');
    fetch(`/api/dust-storm?severity=${severity}`)
        .then(res => res.json())
        .then(d => {
            document.getElementById("badgeDustStorm").innerText = d.alert_level;
            document.getElementById("badgeDustStorm").style.color = d.color;
            document.getElementById("stormSolarPower").innerText = `${d.solar_power_pct}% (Tau ${d.tau})`;
            document.getElementById("stormVisibility").innerText = `${d.visibility_km} km`;
            document.getElementById("stormRoverImpact").innerHTML = `
                <div class="text-[10px] space-y-0.5">
                    <div><strong class="text-mars">Wheeled Rover:</strong> ${d.wheeled_rover_status}</div>
                    <div><strong class="text-cyan-400">Antigravity Glider:</strong> ${d.antigrav_status}</div>
                </div>
            `;
        });
}

function startTraversalSimulation() {
    playSfx('warp');
    const ticker = document.getElementById("simTicker");
    const bar = document.getElementById("simProgressBar");
    const pct = document.getElementById("simProgress");
    const btn = document.getElementById("btnSimulateRoute");

    if (simInterval) clearInterval(simInterval);

    ticker.classList.remove("hidden");
    btn.disabled = true;
    btn.classList.add("opacity-50");

    let progress = 0;
    const simMarker = L.marker([0, 0], {
        icon: L.divIcon({
            className: "flight-sim-vehicle",
            html: `<div class="w-6 h-6 rounded-full bg-cyan-400 border-2 border-white flex items-center justify-center shadow-lg shadow-cyan-400/80 animate-bounce"><i class="fa-solid fa-shuttle-space text-space-950 text-xs"></i></div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        })
    }).addTo(layerGroups.routes);

    const r = cachedRoutes[currentRouteIndex];
    const waypoints = (r && r.route_geometry.antigrav) || [[18.38, 77.58], [12.80, 88.20]];

    simInterval = setInterval(() => {
        progress += 4;
        if (progress > 100) progress = 100;

        pct.innerText = `${progress}%`;
        bar.style.width = `${progress}%`;

        // Interpolate position along waypoints
        const idx = Math.min(waypoints.length - 1, Math.floor((progress / 100) * (waypoints.length - 1)));
        simMarker.setLatLng(waypoints[idx]);

        // Dynamic battery drain simulation
        const batt = Math.max(88, 100 - Math.floor(progress * 0.08));
        document.getElementById("simBattery").innerText = `${batt}%`;

        if (progress >= 100) {
            clearInterval(simInterval);
            simInterval = null;
            playSfx('click');
            setTimeout(() => {
                map.removeLayer(simMarker);
                ticker.classList.add("hidden");
                btn.disabled = false;
                btn.classList.remove("opacity-50");
                alert(`Mission Flight Simulation Complete!\nDestination reached in record time with 93% energy efficiency!`);
            }, 600);
        }
    }, 180);
}

// Procedural Web Audio API sound synthesizer
function initAudio() {
    if (!audioCtx && (window.AudioContext || window.webkitAudioContext)) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function toggleAudio() {
    initAudio();
    audioEnabled = !audioEnabled;
    const lbl = document.getElementById("lblAudio");
    const icon = document.getElementById("iconAudio");
    if (audioEnabled) {
        lbl.innerText = "SFX ON";
        icon.className = "fa-solid fa-volume-high text-cyan-400 text-xs";
        playSfx('click');
    } else {
        lbl.innerText = "SFX MUTED";
        icon.className = "fa-solid fa-volume-xmark text-slate-500 text-xs";
    }
}

function playSfx(type) {
    if (!audioEnabled) return;
    try {
        initAudio();
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        const now = audioCtx.currentTime;
        if (type === 'click') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(800, now);
            osc.frequency.exponentialRampToValueAtTime(1200, now + 0.05);
            gain.gain.setValueAtTime(0.08, now);
            gain.gain.linearRampToValueAtTime(0.001, now + 0.05);
            osc.start(now);
            osc.stop(now + 0.05);
        } else if (type === 'warp') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(220, now);
            osc.frequency.exponentialRampToValueAtTime(880, now + 0.35);
            gain.gain.setValueAtTime(0.06, now);
            gain.gain.linearRampToValueAtTime(0.001, now + 0.35);
            osc.start(now);
            osc.stop(now + 0.35);
        } else if (type === 'alert') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(550, now);
            osc.frequency.setValueAtTime(440, now + 0.12);
            gain.gain.setValueAtTime(0.09, now);
            gain.gain.linearRampToValueAtTime(0.001, now + 0.25);
            osc.start(now);
            osc.stop(now + 0.25);
        } else if (type === 'rover_drive') {
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(140, now);
            osc.frequency.exponentialRampToValueAtTime(220, now + 0.08);
            osc.frequency.exponentialRampToValueAtTime(110, now + 0.22);
            gain.gain.setValueAtTime(0.07, now);
            gain.gain.linearRampToValueAtTime(0.001, now + 0.22);
            osc.start(now);
            osc.stop(now + 0.22);
        } else if (type === 'rover_turn') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(380, now);
            osc.frequency.linearRampToValueAtTime(280, now + 0.12);
            gain.gain.setValueAtTime(0.05, now);
            gain.gain.linearRampToValueAtTime(0.001, now + 0.12);
            osc.start(now);
            osc.stop(now + 0.12);
        }
    } catch (e) {}
}

// ==============================================================
// 14. GOOGLE MAPS STYLE MARS ROVER STREET VIEW CONTROLLER
// Split screen: Top 50% 3D ground perspective, Bottom 50% 2D Leaflet
// ==============================================================
let svMap = null;
let svRoverMarker = null;
let svHeadingConeEl = null;
let svRoutePolyline = null;
let svRouteHaloPolyline = null;
let svWaypointMarkers = [];
let svWaypoints = [];
let svCurrentIndex = 0;
let svHeading = 38; // degrees from North (0 - 360)
let svPitch = 0; // vertical camera pitch
let svIsAutoDriving = false;
let svAutoDriveTimer = null;
let svCanvas = null;
let svCtx = null;
let svAnimFrame = null;
let svIsDragging = false;
let svDragStartX = 0;
let svDragStartY = 0;
let svHeadingAtDragStart = 0;
let svStepBump = 0; // visual camera lurch when stepping
let svActiveCorridor = 0; // 0: Jezero, 1: Valles Marineris, 2: Olympus Mons
let svIsFullscreen = false;
let svMode = 'real'; // 'real' (real NASA HiRISE photo) or 'synthetic' (3D procedural canvas)
let currentRealObs = null; // cached HiRISE metadata

function loadNearestRealImage(lat, lon) {
    fetch(`/api/hirise/nearest?lat=${lat}&lon=${lon}`)
        .then(res => res.json())
        .then(data => {
            currentRealObs = data;
            
            // 1. Update real image background
            const imgEl = document.getElementById("roverRealImage");
            if (imgEl && data.image_url) {
                imgEl.src = data.image_url;
            }

            // 2. Update real image path banner
            const pathEl = document.getElementById("svRealPathText");
            if (pathEl) {
                pathEl.innerText = data.real_image_path || "Archive";
                pathEl.title = data.real_image_path || "";
            }

            const obsIdBadge = document.getElementById("svObsIdBadge");
            if (obsIdBadge) {
                obsIdBadge.innerText = data.obs_id;
            }

            // 3. Update drawer details
            const drawerTitle = document.getElementById("drawerObsTitle");
            if (drawerTitle) drawerTitle.innerText = `${data.obs_id}: ${data.title}`;

            const drawerDist = document.getElementById("drawerDistanceBadge");
            if (drawerDist) drawerDist.innerText = `Nearest Real Observation: ${data.distance_km} km away`;

            const drawerPath = document.getElementById("drawerRealPath");
            if (drawerPath) drawerPath.innerText = data.real_image_path || "";

            const drawerCoords = document.getElementById("drawerCoords");
            if (drawerCoords) drawerCoords.innerText = `${Math.abs(data.lat).toFixed(2)}°${data.lat >= 0 ? 'N' : 'S'} ${data.lon_east ? data.lon_east.toFixed(2) : ''}°E`;

            const drawerScale = document.getElementById("drawerScale");
            if (drawerScale) drawerScale.innerText = data.scale || "50 cm/px";

            const drawerDate = document.getElementById("drawerDate");
            if (drawerDate) drawerDate.innerText = data.acquisition_date || "NASA Archive";

            const drawerCaption = document.getElementById("drawerCaption");
            if (drawerCaption) drawerCaption.innerText = data.caption || "HiRISE orbital observation.";
        })
        .catch(err => console.warn("Error fetching nearest HiRISE real image:", err));
}

function toggleStreetViewMode() {
    const canvas = document.getElementById("roverNavcamCanvas");
    const realContainer = document.getElementById("roverRealImageContainer");
    const btn = document.getElementById("btnToggleImageMode");
    const icon = document.getElementById("iconImageMode");
    const lbl = document.getElementById("lblImageMode");

    if (svMode === 'real') {
        svMode = 'synthetic';
        if (realContainer) realContainer.classList.add("hidden");
        if (canvas) canvas.classList.remove("hidden");
        if (btn) {
            btn.className = "bg-cyan-600/90 hover:bg-cyan-500 text-white px-3 py-1.5 rounded-full text-xs font-mono font-bold flex items-center space-x-1.5 shadow-xl border border-cyan-400/40 cursor-pointer transition-all";
        }
        if (icon) icon.className = "fa-solid fa-satellite text-[10px]";
        if (lbl) lbl.innerText = "3D Canvas";
    } else {
        svMode = 'real';
        if (canvas) canvas.classList.add("hidden");
        if (realContainer) realContainer.classList.remove("hidden");
        if (btn) {
            btn.className = "bg-emerald-600/90 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-full text-xs font-mono font-bold flex items-center space-x-1.5 shadow-xl border border-emerald-400/40 cursor-pointer transition-all";
        }
        if (icon) icon.className = "fa-solid fa-camera text-[10px]";
        if (lbl) lbl.innerText = "Real Image";
    }
    playSfx('click');
}

function toggleRealImageDrawer() {
    const drawer = document.getElementById("svRealImageDrawer");
    if (drawer) {
        drawer.classList.toggle("hidden");
        playSfx('click');
    }
}

function copyRealPath() {
    const path = currentRealObs ? currentRealObs.real_image_path : document.getElementById("svRealPathText").innerText;
    if (path) {
        navigator.clipboard.writeText(path).then(() => {
            alert(`Real Image Path copied to clipboard:\n${path}`);
        }).catch(() => {
            prompt("Real Image Path on Host Disk:", path);
        });
    }
}

function openCurrentHiRISEInModal() {
    if (currentRealObs) {
        openModal(currentRealObs);
    }
}

function generateDenseWaypoints(coarseCoords, totalSteps = 28) {
    if (!coarseCoords || coarseCoords.length < 2) return coarseCoords || [];
    const result = [];
    const segmentCount = coarseCoords.length - 1;
    const stepsPerSeg = Math.max(2, Math.floor(totalSteps / segmentCount));
    for (let i = 0; i < segmentCount; i++) {
        const [lat1, lon1] = coarseCoords[i];
        const [lat2, lon2] = coarseCoords[i + 1];
        for (let s = 0; s < stepsPerSeg; s++) {
            const t = s / stepsPerSeg;
            result.push([
                parseFloat((lat1 + (lat2 - lat1) * t).toFixed(4)),
                parseFloat((lon1 + (lon2 - lon1) * t).toFixed(4))
            ]);
        }
    }
    result.push([
        parseFloat(coarseCoords[coarseCoords.length - 1][0].toFixed(4)),
        parseFloat(coarseCoords[coarseCoords.length - 1][1].toFixed(4))
    ]);
    return result;
}

function initStreetViewMap() {
    if (svMap) return;
    
    // Create Leaflet instance on #streetViewMap
    svMap = L.map("streetViewMap", {
        center: [18.38, 77.58],
        zoom: 7,
        minZoom: 2,
        maxZoom: 9,
        attributionControl: false,
        zoomControl: true
    });

    // Dark Martian tile layer
    const marsTiles = L.tileLayer(
        "https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-mars-basemap-v0-2/all/{z}/{x}/{y}.png",
        { maxZoom: 9 }
    );
    const darkFallback = L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        { subdomains: "abcd", maxZoom: 9 }
    );
    marsTiles.addTo(svMap);
    marsTiles.on("tileerror", () => {
        if (!svMap.hasLayer(darkFallback)) darkFallback.addTo(svMap);
    });

    // Clicking ANY point on the map traverses the rover directly there!
    svMap.on("click", (e) => {
        const clickedLat = parseFloat(e.latlng.lat.toFixed(4));
        const clickedLon = parseFloat(e.latlng.lng.toFixed(4));
        teleportRoverTo(clickedLat, clickedLon);
    });
}

function updateRoverMarkerOnMap(lat, lon, heading) {
    if (!svMap) return;

    if (!svRoverMarker) {
        const icon = L.divIcon({
            className: "custom-rover-street-icon",
            html: `
                <div class="rover-marker-container">
                    <div id="svHeadingCone" class="rover-heading-cone" style="transform: rotate(${heading}deg);"></div>
                    <div class="rover-pulse-ring"></div>
                    <div class="rover-center-dot"></div>
                </div>
            `,
            iconSize: [48, 48],
            iconAnchor: [24, 24]
        });
        svRoverMarker = L.marker([lat, lon], { icon, zIndexOffset: 1000 }).addTo(svMap);
        svHeadingConeEl = document.getElementById("svHeadingCone");
    } else {
        svRoverMarker.setLatLng([lat, lon]);
        svHeadingConeEl = document.getElementById("svHeadingCone");
        if (svHeadingConeEl) {
            svHeadingConeEl.style.transform = `rotate(${heading}deg)`;
        }
    }
}

function renderStreetViewRouteLines() {
    if (!svMap || !svWaypoints || svWaypoints.length < 2) return;

    if (svRouteHaloPolyline) svMap.removeLayer(svRouteHaloPolyline);
    if (svRoutePolyline) svMap.removeLayer(svRoutePolyline);

    // Outer casing / halo (dark blue)
    svRouteHaloPolyline = L.polyline(svWaypoints, {
        color: "#1e3a8a",
        weight: 9,
        opacity: 0.75,
        lineCap: "round",
        lineJoin: "round"
    }).addTo(svMap);

    // Inner bright blue Google Maps style line
    svRoutePolyline = L.polyline(svWaypoints, {
        color: "#2563eb",
        weight: 6,
        opacity: 0.95,
        lineCap: "round",
        lineJoin: "round"
    }).addTo(svMap);

    // Waypoint dots
    svWaypointMarkers.forEach(m => svMap.removeLayer(m));
    svWaypointMarkers = [];

    // Add small circles along route
    const stepInterval = Math.max(1, Math.floor(svWaypoints.length / 8));
    for (let i = 0; i < svWaypoints.length; i += stepInterval) {
        const wp = svWaypoints[i];
        const dot = L.circleMarker(wp, {
            radius: 4,
            fillColor: "#ffffff",
            color: "#1e3a8a",
            weight: 2,
            fillOpacity: 0.9
        }).addTo(svMap);

        const pointIndex = i;
        dot.on("click", () => {
            svCurrentIndex = pointIndex;
            const coord = svWaypoints[pointIndex];
            updateRoverMarkerOnMap(coord[0], coord[1], svHeading);
            fetchTelemetryForPoint(coord[0], coord[1]);
            updateStreetViewHUD();
            playSfx('rover_drive');
        });
        svWaypointMarkers.push(dot);
    }
}

function openRoverStreetView() {
    playSfx('warp');
    const container = document.getElementById("roverStreetViewContainer");
    if (!container) return;

    container.classList.remove("hidden");
    
    // Initialize map
    initStreetViewMap();

    // Start 3D canvas renderer
    startNavcamRenderer();

    // Set default route if none loaded
    if (!svWaypoints || svWaypoints.length === 0) {
        setStreetViewRoute(0);
    } else {
        renderStreetViewRouteLines();
        const cur = svWaypoints[svCurrentIndex];
        updateRoverMarkerOnMap(cur[0], cur[1], svHeading);
        loadNearestRealImage(cur[0], cur[1]);
    }

    // Force Leaflet to re-measure viewport
    setTimeout(() => {
        if (svMap) {
            svMap.invalidateSize();
            const cur = svWaypoints[svCurrentIndex];
            if (cur) svMap.panTo(cur);
        }
    }, 150);
}

function exitRoverStreetView() {
    playSfx('click');
    const container = document.getElementById("roverStreetViewContainer");
    if (container) {
        container.classList.add("hidden");
    }
    if (svIsAutoDriving) {
        toggleRoverAutoDrive();
    }
    if (svAnimFrame) {
        cancelAnimationFrame(svAnimFrame);
        svAnimFrame = null;
    }
    // Re-invalidate orbital map
    if (map) {
        setTimeout(() => map.invalidateSize(), 150);
    }
}

function stepRover(direction) {
    if (!svWaypoints || svWaypoints.length === 0) return;

    if (direction === 'forward') {
        if (svCurrentIndex < svWaypoints.length - 1) {
            svCurrentIndex++;
            playSfx('rover_drive');
        } else {
            // Reached end of corridor
            if (svIsAutoDriving) toggleRoverAutoDrive();
            playSfx('alert');
            return;
        }
    } else if (direction === 'backward') {
        if (svCurrentIndex > 0) {
            svCurrentIndex--;
            playSfx('rover_drive');
        } else {
            playSfx('alert');
            return;
        }
    }

    const currentCoord = svWaypoints[svCurrentIndex];
    
    // Calculate heading based on trajectory
    if (direction === 'forward' && svCurrentIndex < svWaypoints.length - 1) {
        const nextCoord = svWaypoints[svCurrentIndex + 1];
        const dLat = nextCoord[0] - currentCoord[0];
        const dLon = nextCoord[1] - currentCoord[1];
        let angle = Math.atan2(dLon, dLat) * 180 / Math.PI;
        svHeading = (Math.round(angle) + 360) % 360;
    } else if (direction === 'backward' && svCurrentIndex > 0) {
        const prevCoord = svWaypoints[svCurrentIndex - 1];
        const dLat = currentCoord[0] - prevCoord[0];
        const dLon = currentCoord[1] - prevCoord[1];
        let angle = Math.atan2(dLon, dLat) * 180 / Math.PI;
        svHeading = (Math.round(angle) + 360) % 360;
    }

    // Camera bump animation
    svStepBump = direction === 'forward' ? 18 : -14;

    // Update marker on map
    updateRoverMarkerOnMap(currentCoord[0], currentCoord[1], svHeading);
    if (svMap) {
        svMap.panTo([currentCoord[0], currentCoord[1]], { animate: true, duration: 0.4 });
    }

    // Fetch live elevation, slope, temp
    fetchTelemetryForPoint(currentCoord[0], currentCoord[1]);
    loadNearestRealImage(currentCoord[0], currentCoord[1]);
    updateStreetViewHUD();
}

function rotateRover(degDelta) {
    svHeading = (svHeading + degDelta + 360) % 360;
    playSfx('rover_turn');
    if (svHeadingConeEl) {
        svHeadingConeEl.style.transform = `rotate(${svHeading}deg)`;
    }
    updateStreetViewHUD();
}

function teleportRoverTo(lat, lon) {
    playSfx('rover_drive');
    const prevCoord = svWaypoints[svCurrentIndex] || [18.38, 77.58];
    
    // Calculate heading toward clicked point
    const dLat = lat - prevCoord[0];
    const dLon = lon - prevCoord[1];
    if (Math.abs(dLat) > 0.001 || Math.abs(dLon) > 0.001) {
        let angle = Math.atan2(dLon, dLat) * 180 / Math.PI;
        svHeading = (Math.round(angle) + 360) % 360;
    }

    // Insert new waypoint or jump
    svWaypoints.splice(svCurrentIndex + 1, 0, [lat, lon]);
    svCurrentIndex++;

    renderStreetViewRouteLines();
    updateRoverMarkerOnMap(lat, lon, svHeading);
    if (svMap) {
        svMap.panTo([lat, lon], { animate: true, duration: 0.5 });
    }

    // Camera bump animation
    svStepBump = 14;

    // Fetch telemetry for this exact point on Mars
    fetchTelemetryForPoint(lat, lon);
    loadNearestRealImage(lat, lon);
    updateStreetViewHUD();
}

function toggleStreetViewSplitFullscreen() {
    const topPane = document.getElementById("streetViewTopPane");
    const bottomPane = document.getElementById("streetViewBottomPane");
    const iconTop = document.getElementById("iconTopExpand");
    const iconBtm = document.getElementById("iconBottomRightExpand");

    svIsFullscreen = !svIsFullscreen;
    if (svIsFullscreen) {
        topPane.classList.remove("h-1/2");
        topPane.classList.add("h-full");
        bottomPane.classList.add("hidden");
        if (iconTop) iconTop.className = "fa-solid fa-compress text-xs";
        if (iconBtm) iconBtm.className = "fa-solid fa-down-left-and-up-right-to-center text-sm";
    } else {
        topPane.classList.remove("h-full");
        topPane.classList.add("h-1/2");
        bottomPane.classList.remove("hidden");
        if (iconTop) iconTop.className = "fa-solid fa-expand text-xs";
        if (iconBtm) iconBtm.className = "fa-solid fa-up-right-and-down-left-from-center text-sm";
        if (svMap) {
            setTimeout(() => svMap.invalidateSize(), 200);
        }
    }
    playSfx('click');
}

function toggleRoverAutoDrive() {
    svIsAutoDriving = !svIsAutoDriving;
    const btn = document.getElementById("btnAutoDrive");
    const icon = document.getElementById("iconAutoDrive");
    const lbl = document.getElementById("lblAutoDrive");

    if (svIsAutoDriving) {
        if (btn) {
            btn.classList.add("bg-amber-600/90", "border-amber-400");
            btn.classList.remove("bg-cyan-600/80");
        }
        if (icon) icon.className = "fa-solid fa-pause text-[10px]";
        if (lbl) lbl.innerText = "Pause";
        playSfx('warp');

        svAutoDriveTimer = setInterval(() => {
            if (svCurrentIndex < svWaypoints.length - 1) {
                stepRover('forward');
            } else {
                toggleRoverAutoDrive();
            }
        }, 1250);
    } else {
        if (svAutoDriveTimer) clearInterval(svAutoDriveTimer);
        svAutoDriveTimer = null;
        if (btn) {
            btn.classList.remove("bg-amber-600/90", "border-amber-400");
            btn.classList.add("bg-cyan-600/80");
        }
        if (icon) icon.className = "fa-solid fa-play text-[10px]";
        if (lbl) lbl.innerText = "Auto Drive";
        playSfx('click');
    }
}

function setStreetViewRoute(routeIdx) {
    svActiveCorridor = routeIdx;

    // Update buttons
    [0, 1, 2].forEach(i => {
        const b = document.getElementById(`svRouteBtn${i}`);
        if (!b) return;
        if (i === routeIdx) {
            b.className = "px-2.5 py-1 text-xs rounded font-mono bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 cursor-pointer";
        } else {
            b.className = "px-2.5 py-1 text-xs rounded font-mono bg-space-900 text-slate-400 hover:text-slate-200 border border-space-700 cursor-pointer";
        }
    });

    const badge = document.getElementById("svSectorBadge");
    const corridors = [
        {
            name: "Jezero Delta",
            coords: [[18.38, 77.58], [18.25, 78.10], [17.90, 78.90], [17.40, 79.80], [16.80, 80.70], [16.10, 81.60], [15.40, 82.50], [14.60, 83.60], [13.70, 85.00], [12.80, 88.20]]
        },
        {
            name: "Valles Marineris",
            coords: [[-8.50, -62.10], [-9.10, -62.30], [-9.80, -62.50], [-10.50, -62.70], [-11.20, -62.90], [-11.90, -63.10], [-12.60, -63.30], [-13.40, -63.60], [-14.10, -63.90], [-14.80, -64.20]]
        },
        {
            name: "Olympus Mons",
            coords: [[17.20, -135.50], [17.60, -134.80], [18.00, -134.10], [18.40, -133.40], [18.80, -132.70], [19.20, -132.00], [19.60, -131.20], [20.00, -130.50], [20.40, -129.80], [21.00, -129.00]]
        }
    ];

    const sel = corridors[routeIdx] || corridors[0];
    if (badge) badge.innerText = sel.name;

    svWaypoints = generateDenseWaypoints(sel.coords, 28);
    svCurrentIndex = 0;
    const startCoord = svWaypoints[0];

    // Compute initial heading
    if (svWaypoints.length > 1) {
        const nextCoord = svWaypoints[1];
        const dLat = nextCoord[0] - startCoord[0];
        const dLon = nextCoord[1] - startCoord[1];
        svHeading = (Math.round(Math.atan2(dLon, dLat) * 180 / Math.PI) + 360) % 360;
    }

    renderStreetViewRouteLines();
    updateRoverMarkerOnMap(startCoord[0], startCoord[1], svHeading);

    if (svMap) {
        svMap.fitBounds(L.latLngBounds(svWaypoints), { padding: [50, 50], maxZoom: 8 });
    }

    fetchTelemetryForPoint(startCoord[0], startCoord[1]);
    loadNearestRealImage(startCoord[0], startCoord[1]);
    updateStreetViewHUD();
    playSfx('warp');
}

function fetchTelemetryForPoint(lat, lon) {
    const lon360 = lon >= 0 ? lon : 360 + lon;
    fetch(`/api/telemetry?lat=${lat}&lon=${lon}`)
        .then(res => res.json())
        .then(data => {
            const elev = data.elevation ? Math.round(data.elevation.elevation_m) : 0;
            const slope = data.elevation ? data.elevation.slope_deg.toFixed(1) : "0.0";
            const temp = data.thermal ? data.thermal.temperature_c.toFixed(1) : "-62.5";

            const elElev = document.getElementById("svElev");
            const elSlope = document.getElementById("svSlope");
            const elTemp = document.getElementById("svTemp");
            const elLat = document.getElementById("svLat");
            const elLon = document.getElementById("svLon");

            if (elElev) elElev.innerText = `${elev.toLocaleString()} m`;
            if (elSlope) elSlope.innerText = `${slope}°`;
            if (elTemp) elTemp.innerText = `${temp}°C`;
            if (elLat) elLat.innerText = `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? 'N' : 'S'}`;
            if (elLon) elLon.innerText = `${lon360.toFixed(2)}°E`;
        })
        .catch(err => console.warn("Street view telemetry fetch error:", err));
}

function updateStreetViewHUD() {
    const elHeading = document.getElementById("svHeading");
    const elInfo = document.getElementById("svWaypointInfo");
    const elRoadLabel = document.getElementById("svRoadLabel");

    const cardinals = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
    const cardIdx = Math.round(svHeading / 22.5) % 16;
    const cardStr = cardinals[cardIdx];
    const degStr = String(Math.round(svHeading)).padStart(3, '0');

    if (elHeading) {
        elHeading.innerText = `${degStr}° ${cardStr}`;
    }

    const corridorNames = [
        "JEZERO DELTA HIGHWAY",
        "VALLES MARINERIS CHASMA ROUTE",
        "OLYMPUS MONS CALDERA TRAIL"
    ];
    const cName = corridorNames[svActiveCorridor] || "MARS TRAVERSAL CORRIDOR";

    const totalWp = svWaypoints.length;
    const curWp = svCurrentIndex + 1;
    if (elInfo) {
        elInfo.innerText = `WP ${curWp} OF ${totalWp} • HEADING ${degStr}° ${cardStr}`;
    }
    if (elRoadLabel) {
        elRoadLabel.innerText = `${cName} • WP ${curWp}`;
    }
}

function startNavcamRenderer() {
    svCanvas = document.getElementById("roverNavcamCanvas");
    if (!svCanvas) return;
    svCtx = svCanvas.getContext("2d");
    initNavcamEvents();

    function renderLoop() {
        drawNavcamScene();
        svAnimFrame = requestAnimationFrame(renderLoop);
    }
    if (svAnimFrame) cancelAnimationFrame(svAnimFrame);
    svAnimFrame = requestAnimationFrame(renderLoop);
}

function initNavcamEvents() {
    if (!svCanvas || svCanvas._eventsAttached) return;
    svCanvas._eventsAttached = true;

    svCanvas.addEventListener("mousedown", (e) => {
        svIsDragging = true;
        svDragStartX = e.clientX;
        svDragStartY = e.clientY;
        svHeadingAtDragStart = svHeading;
    });

    window.addEventListener("mousemove", (e) => {
        if (!svIsDragging) return;
        const dx = e.clientX - svDragStartX;
        const dy = e.clientY - svDragStartY;
        svHeading = (svHeadingAtDragStart - dx * 0.25 + 360) % 360;
        svPitch = Math.max(-50, Math.min(50, dy * 0.2));
        if (svHeadingConeEl) {
            svHeadingConeEl.style.transform = `rotate(${svHeading}deg)`;
        }
        updateStreetViewHUD();
    });

    window.addEventListener("mouseup", () => {
        if (svIsDragging) {
            svIsDragging = false;
        }
    });

    // Touch support for mobile / touchscreens
    svCanvas.addEventListener("touchstart", (e) => {
        if (e.touches.length === 1) {
            svIsDragging = true;
            svDragStartX = e.touches[0].clientX;
            svDragStartY = e.touches[0].clientY;
            svHeadingAtDragStart = svHeading;
        }
    }, { passive: true });

    window.addEventListener("touchmove", (e) => {
        if (!svIsDragging || e.touches.length === 0) return;
        const dx = e.touches[0].clientX - svDragStartX;
        const dy = e.touches[0].clientY - svDragStartY;
        svHeading = (svHeadingAtDragStart - dx * 0.35 + 360) % 360;
        svPitch = Math.max(-50, Math.min(50, dy * 0.25));
        if (svHeadingConeEl) {
            svHeadingConeEl.style.transform = `rotate(${svHeading}deg)`;
        }
        updateStreetViewHUD();
    }, { passive: true });

    window.addEventListener("touchend", () => {
        svIsDragging = false;
    });
}

function drawNavcamScene() {
    if (!svCanvas || !svCtx) return;
    const w = svCanvas.width = svCanvas.clientWidth;
    const h = svCanvas.height = svCanvas.clientHeight;
    if (w === 0 || h === 0) return;

    const ctx = svCtx;
    const horizonY = h * 0.46 + svPitch + svStepBump;

    // 1. Martian Sky Gradient
    const skyGrad = ctx.createLinearGradient(0, 0, 0, horizonY);
    skyGrad.addColorStop(0, "#2c130b"); // Dark amber space
    skyGrad.addColorStop(0.4, "#5a2717");
    skyGrad.addColorStop(0.75, "#b3532f");
    skyGrad.addColorStop(1, "#df8454"); // Salmon horizon dust
    ctx.fillStyle = skyGrad;
    ctx.fillRect(0, 0, w, Math.max(0, horizonY));

    // 2. High Altitude Pale Sun with Martian Blue-White Halo
    const sunAzimuth = 120;
    let sunAngleDiff = (sunAzimuth - svHeading + 540) % 360 - 180;
    if (Math.abs(sunAngleDiff) < 75) {
        const sunX = w / 2 + (sunAngleDiff / 75) * (w / 2);
        const sunY = horizonY - h * 0.22;
        
        const haloGrad = ctx.createRadialGradient(sunX, sunY, 4, sunX, sunY, 130);
        haloGrad.addColorStop(0, "rgba(255, 250, 240, 0.95)");
        haloGrad.addColorStop(0.25, "rgba(255, 215, 170, 0.45)");
        haloGrad.addColorStop(0.65, "rgba(215, 120, 70, 0.12)");
        haloGrad.addColorStop(1, "transparent");
        ctx.fillStyle = haloGrad;
        ctx.beginPath();
        ctx.arc(sunX, sunY, 130, 0, Math.PI * 2);
        ctx.fill();

        // Sun disc (pale bluish-white as observed by Curiosity/Perseverance)
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(sunX, sunY, 7, 0, Math.PI * 2);
        ctx.fill();
    }

    // 3. Distant Crater Rim Mountain Silhouette
    ctx.fillStyle = "#873b22";
    ctx.beginPath();
    ctx.moveTo(0, horizonY);
    for (let x = 0; x <= w; x += 15) {
        const angle = ((svHeading * 2.2) + (x / w) * 110) * (Math.PI / 180);
        const peak = Math.sin(angle * 1.5) * 22 + Math.cos(angle * 3.1) * 12 + Math.sin(angle * 0.7) * 32;
        ctx.lineTo(x, horizonY - Math.max(3, peak));
    }
    ctx.lineTo(w, horizonY);
    ctx.closePath();
    ctx.fill();

    // 4. Midground Rolling Terraces (Sedimentary Beds)
    ctx.fillStyle = "#ad4725";
    ctx.beginPath();
    ctx.moveTo(0, horizonY);
    for (let x = 0; x <= w; x += 20) {
        const angle = ((svHeading * 3.4) + (x / w) * 90) * (Math.PI / 180);
        const hill = Math.sin(angle * 2.0) * 14 + Math.cos(angle * 1.2) * 16;
        ctx.lineTo(x, horizonY - Math.max(0, hill));
    }
    ctx.lineTo(w, horizonY);
    ctx.closePath();
    ctx.fill();

    // 5. Martian Ground Plane
    const groundGrad = ctx.createLinearGradient(0, horizonY, 0, h);
    groundGrad.addColorStop(0, "#b85128");
    groundGrad.addColorStop(0.25, "#a1421e");
    groundGrad.addColorStop(0.65, "#823014");
    groundGrad.addColorStop(1, "#541b0a");
    ctx.fillStyle = groundGrad;
    ctx.fillRect(0, horizonY, w, Math.max(0, h - horizonY));

    // 6. Perspective Dune Ripples
    ctx.strokeStyle = "rgba(125, 42, 16, 0.45)";
    ctx.lineWidth = 1.5;
    for (let r = 0; r < 14; r++) {
        const t = Math.pow((r + 1) / 14, 2.2);
        const y = horizonY + (h - horizonY) * t;
        ctx.beginPath();
        for (let x = 0; x <= w; x += 25) {
            const wave = Math.sin((x / 65) + (svHeading * 0.05) + r) * (t * 6);
            if (x === 0) ctx.moveTo(x, y + wave);
            else ctx.lineTo(x, y + wave);
        }
        ctx.stroke();
    }

    // 7. Rover Tire Tracks
    ctx.strokeStyle = "rgba(35, 10, 4, 0.4)";
    ctx.lineWidth = 4;
    // Left wheel track
    ctx.beginPath();
    ctx.moveTo(w * 0.48, horizonY + 2);
    ctx.lineTo(w * 0.22, h);
    ctx.stroke();
    // Right wheel track
    ctx.beginPath();
    ctx.moveTo(w * 0.52, horizonY + 2);
    ctx.lineTo(w * 0.78, h);
    ctx.stroke();

    // 8. Basaltic Rocks / Boulders in 3D Perspective
    const rockSeeds = [
        { u: -0.35, v: 0.85, s: 22, color: "#3e1b12" },
        { u: 0.38, v: 0.75, s: 28, color: "#34150e" },
        { u: -0.15, v: 0.60, s: 16, color: "#481f15" },
        { u: 0.22, v: 0.50, s: 14, color: "#3a180f" },
        { u: -0.42, v: 0.40, s: 12, color: "#421b12" },
        { u: 0.45, v: 0.35, s: 10, color: "#37160f" },
        { u: -0.08, v: 0.30, s: 8, color: "#4d2217" },
        { u: 0.12, v: 0.22, s: 6, color: "#411b12" },
        { u: -0.28, v: 0.18, s: 5, color: "#522419" },
        { u: 0.30, v: 0.15, s: 4, color: "#3c1911" },
        { u: -0.05, v: 0.95, s: 34, color: "#2c110a" },
        { u: 0.52, v: 0.90, s: 30, color: "#391710" }
    ];

    rockSeeds.forEach((rock) => {
        const relU = rock.u + Math.sin((svHeading * Math.PI) / 180) * 0.25;
        const v = rock.v;
        const t = Math.pow(v, 2.0);
        const rx = w / 2 + relU * w * (0.3 + 0.7 * t);
        const ry = horizonY + (h - horizonY) * t;
        const size = rock.s * (0.2 + 0.8 * t);

        if (rx > -50 && rx < w + 50 && ry < h) {
            // Shadow
            ctx.fillStyle = "rgba(18, 5, 2, 0.5)";
            ctx.beginPath();
            ctx.ellipse(rx + size * 0.3, ry + size * 0.35, size * 0.8, size * 0.35, 0.2, 0, Math.PI * 2);
            ctx.fill();

            // Rock body
            ctx.fillStyle = rock.color;
            ctx.beginPath();
            ctx.moveTo(rx - size * 0.6, ry + size * 0.3);
            ctx.lineTo(rx - size * 0.4, ry - size * 0.5);
            ctx.lineTo(rx + size * 0.3, ry - size * 0.6);
            ctx.lineTo(rx + size * 0.7, ry - size * 0.1);
            ctx.lineTo(rx + size * 0.5, ry + size * 0.4);
            ctx.closePath();
            ctx.fill();

            // Sun highlight
            ctx.strokeStyle = "rgba(235, 155, 105, 0.35)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(rx - size * 0.4, ry - size * 0.5);
            ctx.lineTo(rx + size * 0.3, ry - size * 0.6);
            ctx.stroke();
        }
    });

    // 9. Rover Chassis / Solar Panel Corner Silhouette
    ctx.fillStyle = "#1e293b";
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(w * 0.15, h);
    ctx.lineTo(0, h - 50);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "#00f0ff";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.fillStyle = "#1e293b";
    ctx.beginPath();
    ctx.moveTo(w, h);
    ctx.lineTo(w - w * 0.15, h);
    ctx.lineTo(w, h - 50);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "#f97316";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // 10. Navcam Reticle Crosshairs in Center
    const cx = w / 2;
    const cy = horizonY;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx - 18, cy);
    ctx.lineTo(cx - 6, cy);
    ctx.moveTo(cx + 6, cy);
    ctx.lineTo(cx + 18, cy);
    ctx.moveTo(cx, cy - 18);
    ctx.lineTo(cx, cy - 6);
    ctx.moveTo(cx, cy + 6);
    ctx.lineTo(cx, cy + 18);
    ctx.stroke();

    // Decay step bump smoothly
    if (Math.abs(svStepBump) > 0.1) {
        svStepBump *= 0.82;
    } else {
        svStepBump = 0;
    }
}

// Global Keyboard Navigation for Mars Rover Street View
window.addEventListener("keydown", (e) => {
    const svContainer = document.getElementById("roverStreetViewContainer");
    if (!svContainer || svContainer.classList.contains("hidden")) return;

    if (e.key === "ArrowUp" || e.key === "w" || e.key === "W") {
        e.preventDefault();
        stepRover('forward');
    } else if (e.key === "ArrowDown" || e.key === "s" || e.key === "S") {
        e.preventDefault();
        stepRover('backward');
    } else if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") {
        e.preventDefault();
        rotateRover(-15);
    } else if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") {
        e.preventDefault();
        rotateRover(15);
    } else if (e.key === "Escape") {
        exitRoverStreetView();
    } else if (e.key === " ") {
        e.preventDefault();
        toggleRoverAutoDrive();
    }
});
