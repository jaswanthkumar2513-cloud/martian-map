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
    hirise: L.layerGroup()
};

let cachedRoutes = [];
let cachedGMZs = [];
let currentRouteIndex = 0;
let gravityChart = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    loadOutposts();
    loadGMZs();
    loadPresetRoutes();
    loadHiRISEData();
    initPhysicsSimulator();
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

            // Query MOLA elevation at cursor
            fetch(`/api/elevation/query?lat=${lat}&lon=${lon}`)
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
    } else {
        map.removeLayer(layerGroups[layerName]);
    }
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
    document.getElementById("modalCoords").innerText = `${img.lat.toFixed(3)}°, ${img.lon_east.toFixed(3)}°E`;
    document.getElementById("modalDate").innerText = img.acquisition_date;
    document.getElementById("modalAltitude").innerText = img.spacecraft_altitude;
    document.getElementById("modalCaption").innerText = img.caption;

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
