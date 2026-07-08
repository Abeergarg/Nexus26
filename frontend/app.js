const BACKEND_URL = "http://127.0.0.1:8000";

let topologyData = null;
let startNodeId = null;
let endNodeId = null;
let cacheHitHistory = [];

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    // 1. Fetch Topology & Render SVG Map
    fetchTopology();

    // 2. Poll Operations Forecast & Cache Metrics
    pollOperationsForecast();
    setInterval(pollOperationsForecast, 4000);
    setInterval(pollCacheStats, 4000);

    // 3. Setup Clock
    setupClock();

    // 4. Setup Form Event Listeners
    document.getElementById("wayfinding-form").addEventListener("submit", handleWayfindingSubmit);
    document.getElementById("btn-replenish").addEventListener("click", handleReplenish);

    // 5. Select dropdown change listener
    document.getElementById("select-start").addEventListener("change", (e) => {
        setStartNode(e.target.value, false);
    });
    document.getElementById("select-end").addEventListener("change", (e) => {
        setEndNode(e.target.value, false);
    });
});

// --- UI Clock Helper ---
function setupClock() {
    const clock = document.getElementById("live-clock");
    setInterval(() => {
        const now = new Date();
        clock.textContent = now.toISOString().replace("T", " ").substring(0, 19) + " UTC";
    }, 1000);
}

// --- Fetch Topology ---
async function fetchTopology() {
    appendTelemetryLog("Fetching stadium topology from FastAPI core...", "system");
    try {
        const response = await fetch(`${BACKEND_URL}/api/telemetry/topology`);
        if (!response.ok) throw new Error("Failed to load topology");
        
        topologyData = await response.json();
        
        populateDropdowns(topologyData.nodes);
        renderStadiumMap(topologyData);
        appendTelemetryLog("Stadium density graph rendered successfully.", "system");
    } catch (err) {
        console.error(err);
        appendTelemetryLog(`ERROR loading topology. Is backend running? ${err.message}`, "system");
    }
}

// --- Populate Location Dropdowns ---
function populateDropdowns(nodes) {
    const selectStart = document.getElementById("select-start");
    const selectEnd = document.getElementById("select-end");
    
    // Clear previous
    selectStart.innerHTML = '<option value="">Select Start Point</option>';
    selectEnd.innerHTML = '<option value="">Select Destination</option>';

    // Sort nodes alphabetically by type then label
    const sortedNodes = [...nodes].sort((a, b) => a.label.localeCompare(b.label));

    sortedNodes.forEach(node => {
        const opt = document.createElement("option");
        opt.value = node.id;
        opt.textContent = `${node.label} (${node.id})`;
        
        selectStart.appendChild(opt.cloneNode(true));
        selectEnd.appendChild(opt.cloneNode(true));
    });
}

// --- Render SVG Stadium Map ---
function renderStadiumMap(topology) {
    const container = document.getElementById("map-viewport");
    container.innerHTML = ""; // Clear loader

    // Create SVG Viewbox 800x800
    const svgNamespace = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNamespace, "svg");
    svg.setAttribute("viewBox", "0 0 800 800");

    // 1. Draw Field / Pitch markings in the center
    const pitchGroup = document.createElementNS(svgNamespace, "g");
    
    const pitchBg = document.createElementNS(svgNamespace, "rect");
    pitchBg.setAttribute("x", "280");
    pitchBg.setAttribute("y", "320");
    pitchBg.setAttribute("width", "240");
    pitchBg.setAttribute("height", "160");
    pitchBg.setAttribute("rx", "15");
    pitchBg.setAttribute("ry", "15");
    pitchBg.setAttribute("class", "stadium-pitch");
    pitchGroup.appendChild(pitchBg);

    const pitchOutline = document.createElementNS(svgNamespace, "rect");
    pitchOutline.setAttribute("x", "295");
    pitchOutline.setAttribute("y", "335");
    pitchOutline.setAttribute("width", "210");
    pitchOutline.setAttribute("height", "130");
    pitchOutline.setAttribute("class", "stadium-pitch-lines");
    pitchGroup.appendChild(pitchOutline);

    const pitchCircle = document.createElementNS(svgNamespace, "circle");
    pitchCircle.setAttribute("cx", "400");
    pitchCircle.setAttribute("cy", "400");
    pitchCircle.setAttribute("r", "30");
    pitchCircle.setAttribute("class", "stadium-pitch-lines");
    pitchGroup.appendChild(pitchCircle);

    svg.appendChild(pitchGroup);

    // 2. Draw Edges (Graph Paths)
    const edgeGroup = document.createElementNS(svgNamespace, "g");
    edgeGroup.setAttribute("id", "svg-edges-group");
    
    const nodeMap = {};
    topology.nodes.forEach(n => { nodeMap[n.id] = n; });

    topology.edges.forEach((edge, index) => {
        const u = nodeMap[edge.source];
        const v = nodeMap[edge.target];
        if (!u || !v) return;

        // Base Line
        const line = document.createElementNS(svgNamespace, "line");
        line.setAttribute("x1", u.x);
        line.setAttribute("y1", u.y);
        line.setAttribute("x2", v.x);
        line.setAttribute("y2", v.y);
        line.setAttribute("id", `edge-${edge.source}-${edge.target}`);
        
        // Edge styling by density
        let strokeColor = "rgba(0, 230, 118, 0.2)"; // Low
        if (edge.density >= 0.7) {
            strokeColor = "rgba(255, 23, 68, 0.75)"; // Heavy
        } else if (edge.density >= 0.3) {
            strokeColor = "rgba(255, 214, 0, 0.5)"; // Medium
        }

        line.setAttribute("stroke", strokeColor);
        line.setAttribute("stroke-width", edge.density >= 0.7 ? "4" : "2.5");
        if (edge.stairs) {
            line.classList.add("stairs");
        }
        line.classList.add("svg-edge");
        
        edgeGroup.appendChild(line);
    });
    svg.appendChild(edgeGroup);

    // 3. Draw Route overlay path container (will be updated dynamically)
    const routeGroup = document.createElementNS(svgNamespace, "g");
    routeGroup.setAttribute("id", "svg-route-group");
    svg.appendChild(routeGroup);

    // 4. Draw Nodes (Sections, Gates, Ramps)
    const nodeGroup = document.createElementNS(svgNamespace, "g");
    nodeGroup.setAttribute("id", "svg-nodes-group");

    topology.nodes.forEach(node => {
        const group = document.createElementNS(svgNamespace, "g");
        group.setAttribute("cursor", "pointer");
        group.addEventListener("click", () => handleNodeClick(node.id));

        const circle = document.createElementNS(svgNamespace, "circle");
        circle.setAttribute("cx", node.x);
        circle.setAttribute("cy", node.y);
        
        // Node Type Radii
        let radius = 10;
        let color = "#1e1e1e";
        let stroke = "#555555";
        
        if (node.type === "gate") {
            radius = 12;
            color = "#0055ff";
            stroke = "#4ba0ff";
        } else if (node.type === "section") {
            radius = 11;
            color = "#202020";
            stroke = "#999999";
        } else if (node.type === "transit") {
            radius = 13;
            color = "#008800";
            stroke = "#00ff00";
        } else if (node.type === "first_aid") {
            radius = 11;
            color = "#aa0000";
            stroke = "#ff4444";
        } else if (node.type === "food") {
            radius = 11;
            color = "#d57a00";
            stroke = "#ffb04c";
        }

        circle.setAttribute("r", radius);
        circle.setAttribute("fill", color);
        circle.setAttribute("stroke", stroke);
        circle.setAttribute("stroke-width", "2");
        circle.setAttribute("id", `node-${node.id}`);
        circle.classList.add("svg-node");

        group.appendChild(circle);

        // Add small textual identifier labels below nodes
        const label = document.createElementNS(svgNamespace, "text");
        label.setAttribute("x", node.x);
        label.setAttribute("y", node.y + radius + 10);
        label.setAttribute("class", "svg-label");
        
        // Short labels to avoid overcrowding
        let displayLabel = node.id.replace("_", " ");
        label.textContent = displayLabel;
        group.appendChild(label);

        nodeGroup.appendChild(group);
    });
    
    svg.appendChild(nodeGroup);
    container.appendChild(svg);
}

// --- Handle Map Interactive Clicking ---
function handleNodeClick(nodeId) {
    if (!startNodeId) {
        setStartNode(nodeId, true);
    } else if (!endNodeId && nodeId !== startNodeId) {
        setEndNode(nodeId, true);
        // Automatically request routing when end node is clicked
        document.getElementById("wayfinding-form").dispatchEvent(new Event("submit"));
    } else {
        // Reset and assign clicked node as new start
        setStartNode(nodeId, true);
        setEndNode(null, true);
    }
}

function setStartNode(nodeId, updateDropdown) {
    // Remove previous active outline
    if (startNodeId) {
        const prev = document.getElementById(`node-${startNodeId}`);
        if (prev) prev.classList.remove("active-start");
    }
    
    startNodeId = nodeId;
    
    if (startNodeId) {
        const next = document.getElementById(`node-${startNodeId}`);
        if (next) next.classList.add("active-start");
    }
    
    if (updateDropdown) {
        document.getElementById("select-start").value = nodeId || "";
    }
}

function setEndNode(nodeId, updateDropdown) {
    // Remove previous active outline
    if (endNodeId) {
        const prev = document.getElementById(`node-${endNodeId}`);
        if (prev) prev.classList.remove("active-end");
    }
    
    endNodeId = nodeId;
    
    if (endNodeId) {
        const next = document.getElementById(`node-${endNodeId}`);
        if (next) next.classList.add("active-end");
    }
    
    if (updateDropdown) {
        document.getElementById("select-end").value = nodeId || "";
    }
}

// --- Draw Path Route Overlay on SVG Map ---
function drawRouteOverlay(path) {
    const routeGroup = document.getElementById("svg-route-group");
    routeGroup.innerHTML = ""; // Clear previous

    if (!path || path.length < 2 || !topologyData) return;

    const nodeMap = {};
    topologyData.nodes.forEach(n => { nodeMap[n.id] = n; });

    const svgNamespace = "http://www.w3.org/2000/svg";

    // 1. Draw glowing path line strings
    let pathD = "";
    path.forEach((nodeId, idx) => {
        const node = nodeMap[nodeId];
        if (!node) return;
        if (idx === 0) {
            pathD += `M ${node.x} ${node.y}`;
        } else {
            pathD += ` L ${node.x} ${node.y}`;
        }
    });

    // Draw background thick blur line
    const glowPath = document.createElementNS(svgNamespace, "path");
    glowPath.setAttribute("d", pathD);
    glowPath.setAttribute("fill", "none");
    glowPath.setAttribute("class", "svg-edge-glow");
    glowPath.setAttribute("stroke", "var(--primary-color)");
    routeGroup.appendChild(glowPath);

    // Draw primary route line path
    const routePath = document.createElementNS(svgNamespace, "path");
    routePath.setAttribute("d", pathD);
    routePath.setAttribute("fill", "none");
    routePath.setAttribute("class", "svg-route-path");
    routeGroup.appendChild(routePath);
}

// --- Handle Wayfinding Form Submission ---
async function handleWayfindingSubmit(e) {
    e.preventDefault();

    const start = document.getElementById("select-start").value;
    const end = document.getElementById("select-end").value;
    const profile = document.getElementById("select-profile").value;
    const lang = document.getElementById("select-lang").value;
    const query = document.getElementById("input-query").value.trim() || `Route from ${start} to ${end}`;

    if (!start || !end) return;

    try {
        const response = await fetch(`${BACKEND_URL}/api/navigation/route`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                start: start,
                end: end,
                profile: profile,
                query_text: query,
                language: lang
            })
        });

        if (!response.ok) {
            const errBody = await response.json();
            throw new Error(errBody.detail || "Routing request failed");
        }

        const data = await response.json();
        
        // Render Output Panel
        document.getElementById("output-placeholder").style.display = "none";
        const outputPanel = document.getElementById("wayfinding-output");
        outputPanel.style.display = "flex";

        // 1. Populate PII Scrubbing Layer Logs
        document.getElementById("scrubbed-text").textContent = `"${data.scrubbed_query}"`;
        document.getElementById("scrub-names").textContent = `${data.scrub_stats.names} Names`;
        document.getElementById("scrub-emails").textContent = `${data.scrub_stats.emails} Emails`;
        document.getElementById("scrub-phones").textContent = `${data.scrub_stats.phones} Phones`;

        // 2. Cache Match Stats
        const cacheBadge = document.getElementById("cache-badge");
        if (data.cache_hit) {
            cacheBadge.textContent = "SEMANTIC CACHE HIT";
            cacheBadge.className = "cache-badge hit";
        } else {
            cacheBadge.textContent = "CACHE MISS / LLM CALC";
            cacheBadge.className = "cache-badge";
        }
        document.getElementById("cache-similarity").textContent = `${(data.similarity_score * 100).toFixed(1)}%`;
        document.getElementById("cache-latency").textContent = data.latency_ms.toFixed(1);

        // 3. Navigation summary metrics
        document.getElementById("route-profile").textContent = data.profile_label;
        document.getElementById("route-carbon").textContent = `${data.estimated_carbon_grams}g CO2`;
        document.getElementById("route-dist").textContent = `${data.total_distance_meters}m`;
        document.getElementById("route-time").textContent = `${data.total_time_minutes} mins`;

        // 4. Instructions
        const stepsList = document.getElementById("route-steps-list");
        stepsList.innerHTML = "";
        data.steps.forEach(step => {
            const li = document.createElement("li");
            li.textContent = step;
            stepsList.appendChild(li);
        });

        // 5. Draw path layout on stadium map
        drawRouteOverlay(data.path);
        
        appendTelemetryLog(`Routed ${start} to ${end} via '${profile}' [CacheHit: ${data.cache_hit}]`, "system");

    } catch (err) {
        console.error(err);
        alert(`Routing failed: ${err.message}`);
    }
}

// --- Poll Operations Dashboard ---
async function pollOperationsForecast() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/operations/forecast`);
        if (!response.ok) throw new Error("Forecast fetch failed");

        const data = await response.json();

        // 1. Update Conditions Cards
        document.getElementById("val-temp").textContent = `${data.inputs.temperature_celsius}°C`;
        document.getElementById("val-humidity").textContent = `${data.inputs.humidity_percentage}%`;
        
        const hiCard = document.getElementById("heat-index-card");
        const valHi = document.getElementById("val-heat-index");
        valHi.textContent = `${data.heat_index_celsius.toFixed(1)}°C`;

        const dangerAlert = document.getElementById("val-danger-level");
        dangerAlert.textContent = `Danger Level: ${data.danger_level}`;

        // Color card by heat index severity
        if (data.heat_index_celsius >= 35.0) {
            hiCard.className = "metric-card alert-card danger";
            dangerAlert.className = "danger-level-alert extreme";
        } else if (data.heat_index_celsius >= 27.0) {
            hiCard.className = "metric-card alert-card warn";
            dangerAlert.className = "danger-level-alert caution";
        } else {
            hiCard.className = "metric-card alert-card";
            dangerAlert.className = "danger-level-alert";
        }

        // 2. Update Resource Progress Bars
        updateProgressBar("water", data.depletion_percentages.water, data.remaining_time_hours.water);
        updateProgressBar("ice", data.depletion_percentages.ice, data.remaining_time_hours.ice);
        updateProgressBar("medical", data.depletion_percentages.medical, data.remaining_time_hours.medical);

        // 3. Render Logistics Dispatches
        const logContainer = document.getElementById("dispatch-logs-container");
        logContainer.innerHTML = "";
        
        if (data.dispatch_actions.length === 0) {
            logContainer.innerHTML = '<div class="empty-state">No active logistics dispatch schedules. Ambient temperature is safe.</div>';
        } else {
            data.dispatch_actions.forEach(act => {
                const card = document.createElement("div");
                card.className = "dispatch-card";
                if (act.action === "DISPATCH_WATER_TRUCK") {
                    card.className = "dispatch-card critical";
                }
                card.innerHTML = `
                    <div class="dispatch-title">${act.action.replace(/_/g, " ")}</div>
                    <div class="dispatch-meta">Target: ${act.target_zone} | Load: ${act.quantity} ${act.unit} | Team: ${act.volunteer_group}</div>
                `;
                logContainer.appendChild(card);
            });
        }

        // 4. Periodically reload SVG edge colors from live simulated densities
        refreshMapEdgeDensities();

    } catch (err) {
        console.error("Failed to poll operations forecast:", err);
    }
}

function updateProgressBar(key, depletionPct, hrsLeft) {
    const bar = document.getElementById(`bar-${key}`);
    const text = document.getElementById(`txt-${key}-depletion`);
    const timeText = document.getElementById(`time-${key}`);

    bar.style.width = `${100 - depletionPct}%`;
    text.textContent = `${depletionPct.toFixed(1)}% depleted`;
    timeText.textContent = hrsLeft < 999 ? `${hrsLeft.toFixed(1)} hrs` : "99+ hrs";

    // Set bar alerts
    if (depletionPct >= 80.0) {
        bar.className = "progress-fill danger";
    } else if (depletionPct >= 50.0) {
        bar.className = "progress-fill warning";
    } else {
        bar.className = "progress-fill";
    }
}

// --- Refresh SVG Map Colors Based on Oscillating Densities ---
async function refreshMapEdgeDensities() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/telemetry/topology`);
        if (!response.ok) return;
        const data = await response.json();
        
        topologyData = data; // Keep local cache updated

        data.edges.forEach(edge => {
            const line = document.getElementById(`edge-${edge.source}-${edge.target}`);
            if (line) {
                let strokeColor = "rgba(0, 230, 118, 0.22)"; // Low
                if (edge.density >= 0.7) {
                    strokeColor = "rgba(255, 23, 68, 0.75)"; // Heavy
                    line.setAttribute("stroke-width", "4.5");
                } else if (edge.density >= 0.3) {
                    strokeColor = "rgba(255, 214, 0, 0.55)"; // Medium
                    line.setAttribute("stroke-width", "3");
                } else {
                    line.setAttribute("stroke-width", "2");
                }
                line.setAttribute("stroke", strokeColor);
            }
        });
        
        // Log telemetry ticks
        appendTelemetryLog(`Ingested live telemetry: Occupancy flow ticks updated. Heat Index calculated.`, "ingested");
    } catch (err) {
        console.error("Map edge density refresh failed:", err);
    }
}

// --- Restock Action ---
async function handleReplenish() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/operations/replenish`, {
            method: "POST",
            headers: {
                "X-User-Role": "Administrator"
            }
        });
        const res = await response.json();
        appendTelemetryLog(`[SYSTEM] ${res.message}`, "system");
        pollOperationsForecast();
    } catch (err) {
        console.error(err);
    }
}

// --- Poll Cache stats ---
async function pollCacheStats() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/operations/cache/stats`);
        if (!response.ok) return;
        const data = await response.json();
        document.getElementById("val-cache-ratio").textContent = `${(data.hit_ratio * 100).toFixed(1)}% (${data.hits} / ${data.total_queries})`;
    } catch (err) {
        console.error("Failed cache telemetry:", err);
    }
}

// --- Append logs to Footer Telemetry ---
function appendTelemetryLog(msg, type = "system") {
    const container = document.getElementById("telemetry-logs");
    const line = document.createElement("div");
    line.className = `log-line ${type}`;
    
    const timestamp = new Date().toISOString().substring(11, 19);
    line.textContent = `[${timestamp}] ${msg}`;
    
    container.appendChild(line);
    
    // Auto-scroll
    container.scrollTop = container.scrollHeight;
    
    // Prune excess logs (keep last 18 lines)
    while (container.childNodes.length > 18) {
        container.removeChild(container.firstChild);
    }
}
