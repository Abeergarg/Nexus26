import json
import os
import heapq
from typing import List, Dict, Any, Tuple

from app.core.exceptions import RouteCalculationError

TOPOLOGY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "stadium_topology.json",
)

TRANSLATIONS = {
    "es": {
        "start_at": "Comience en {label}.",
        "head_to": "Diríjase hacia {label} ({dist}m, congestión: {density}%).",
        "take_stairs": "Suba por {label} ({dist}m, congestión: {density}%). [Advertencia: Contiene escaleras]",
        "take_ramp": "Avance por la rampa {label} ({dist}m, congestión: {density}%). [Acceso Accesible]",
        "take_elevator": "Suba en el ascensor {label} ({dist}m, congestión: {density}%). [Acceso Accesible]",
        "arrive_at": "Llegue a su destino en {label}.",
        "standard": "Ruta Estándar Optimizado",
        "mobility_impaired": "Ruta Accesible (Sin Escaleras)",
        "green": "Ruta de Tránsito Ecológico",
        "carbon_saved": "Emisiones de carbono estimadas: {carbon}g CO2 equivalent.",
    },
    "fr": {
        "start_at": "Commencez à {label}.",
        "head_to": "Dirigez-vous vers {label} ({dist}m, affluence: {density}%).",
        "take_stairs": "Prenez les escaliers via {label} ({dist}m, affluence: {density}%). [Attention: Escaliers]",
        "take_ramp": "Suivez la rampe d'accès {label} ({dist}m, affluence: {density}%). [Accessible PMR]",
        "take_elevator": "Prenez l'ascenseur {label} ({dist}m, affluence: {density}%). [Accessible PMR]",
        "arrive_at": "Arrivez à votre destination à {label}.",
        "standard": "Itinéraire Standard Optimisé",
        "mobility_impaired": "Itinéraire Accessible (Évite les Escaliers)",
        "green": "Itinéraire Éco-Responsable",
        "carbon_saved": "Émissions de carbone estimées: {carbon}g équivalent CO2.",
    },
    "ar": {
        "start_at": "ابدأ من {label}.",
        "head_to": "توجه نحو {label} ({dist} متر، الازدحام: {density}%).",
        "take_stairs": "اسلك السلالم عبر {label} ({dist} متر، الازدحام: {density}%). [تحذير: درج]",
        "take_ramp": "اسلك المنحدر {label} ({dist} متر، الازدحام: {density}%). [مسار مهيأ للكراسي]",
        "take_elevator": "استخدم المصعد {label} ({dist} متر، الازدحام: {density}%). [مسار مهيأ للكراسي]",
        "arrive_at": "الوصول إلى الوجهة في {label}.",
        "standard": "مسار قياسي محسن",
        "mobility_impaired": "مسار يسهل الوصول إليه (تجنب السلالم)",
        "green": "مسار صديق للبيئة",
        "carbon_saved": "انبعاثات الكربون المقدرة: {carbon} غرام مكافئ لثاني أكسيد الكربون.",
    },
    "en": {
        "start_at": "Start at {label}.",
        "head_to": "Head toward {label} ({dist}m, crowd density: {density}%).",
        "take_stairs": "Go via stairs at {label} ({dist}m, crowd density: {density}%). [Warning: Contains Stairs]",
        "take_ramp": "Go via accessibility ramp at {label} ({dist}m, crowd density: {density}%). [Wheelchair Friendly]",
        "take_elevator": "Take elevator at {label} ({dist}m, crowd density: {density}%). [Wheelchair Friendly]",
        "arrive_at": "Arrive at your destination {label}.",
        "standard": "Standard Optimized Route",
        "mobility_impaired": "Accessible Route (Stairs-Free)",
        "green": "Green Transit Route",
        "carbon_saved": "Estimated carbon footprint: {carbon}g CO2 equivalent.",
    },
}


class RoutingService:
    def __init__(self):
        self.nodes = {}
        self.adj = {}
        self.load_topology()

    def load_topology(self):
        if not os.path.exists(TOPOLOGY_PATH):
            raise FileNotFoundError(f"Topology file missing at {TOPOLOGY_PATH}")

        with open(TOPOLOGY_PATH, "r") as f:
            data = json.load(f)

        self.nodes = {n["id"]: n for n in data["nodes"]}
        self.adj = {n["id"]: [] for n in data["nodes"]}

        for edge in data["edges"]:
            src = edge["source"]
            tgt = edge["target"]
            self.adj[src].append(edge)
            rev_edge = edge.copy()
            rev_edge["source"] = tgt
            rev_edge["target"] = src
            self.adj[tgt].append(rev_edge)

    def update_edge_density(self, source: str, target: str, density: float) -> bool:
        updated = False
        for node in [source, target]:
            if node in self.adj:
                for edge in self.adj[node]:
                    if (edge["source"] == source and edge["target"] == target) or (
                        edge["source"] == target and edge["target"] == source
                    ):
                        edge["density"] = max(0.0, min(1.0, density))
                        updated = True
        return updated

    def calculate_route(
        self, start: str, end: str, profile: str = "standard", lang: str = "en"
    ) -> Dict[str, Any]:
        lang = lang.lower() if lang.lower() in TRANSLATIONS else "en"

        if start not in self.nodes:
            raise RouteCalculationError(
                f"Start node ID '{start}' is not represented in MetLife topology."
            )
        if end not in self.nodes:
            raise RouteCalculationError(
                f"Destination node ID '{end}' is not represented in MetLife topology."
            )

        queue: List[Tuple[float, str, List[str]]] = [(0.0, start, [start])]
        distances = {node_id: float("inf") for node_id in self.nodes}
        distances[start] = 0.0

        best_path: List[str] = []

        while queue:
            curr_cost, curr_node, path = heapq.heappop(queue)

            if curr_cost > distances[curr_node]:
                continue

            if curr_node == end:
                best_path = path
                break

            for edge in self.adj[curr_node]:
                neighbor = edge["target"]

                # Check accessibility
                if profile == "mobility_impaired":
                    if (
                        edge.get("stairs", False)
                        or self.nodes[curr_node]["type"] == "stairs"
                        or self.nodes[neighbor]["type"] == "stairs"
                    ):
                        continue

                dist = edge["distance"]
                density = edge.get("density", 0.0)
                green_factor = edge.get("green_factor", 1.0)

                # Weight formula calculations
                if profile == "mobility_impaired":
                    cost = dist * (1.0 + density * 4.0)
                elif profile == "green":
                    cost = dist * (2.0 - green_factor)
                else:
                    cost = dist * (1.0 + density * 9.0)

                new_cost = curr_cost + cost
                if new_cost < distances[neighbor]:
                    distances[neighbor] = new_cost
                    heapq.heappush(queue, (new_cost, neighbor, path + [neighbor]))

        if not best_path:
            raise RouteCalculationError(
                "No accessible routing paths connect the selected destinations."
            )

        total_distance = 0.0
        total_carbon = 0.0
        total_time_seconds = 0.0
        steps: List[str] = []
        t_dict = TRANSLATIONS[lang]

        steps.append(t_dict["start_at"].format(label=self.nodes[start]["label"]))

        for i in range(len(best_path) - 1):
            curr_n = best_path[i]
            next_n = best_path[i + 1]

            matching_edge = None
            for edge in self.adj[curr_n]:
                if edge["target"] == next_n:
                    matching_edge = edge
                    break

            if not matching_edge:
                continue

            dist = matching_edge["distance"]
            density = matching_edge.get("density", 0.0)
            green_factor = matching_edge.get("green_factor", 1.0)

            total_distance += dist
            edge_carbon = dist * (1.0 - green_factor) * 100.0
            total_carbon += edge_carbon

            speed = 1.4 * (1.0 - 0.7 * density)
            total_time_seconds += dist / speed

            label = self.nodes[next_n]["label"]
            pct_density = int(density * 100)

            if next_n == end:
                steps.append(t_dict["arrive_at"].format(label=label))
            else:
                n_type = self.nodes[next_n]["type"]
                if n_type == "stairs":
                    steps.append(
                        t_dict["take_stairs"].format(
                            label=label, dist=dist, density=pct_density
                        )
                    )
                elif n_type == "ramp":
                    steps.append(
                        t_dict["take_ramp"].format(
                            label=label, dist=dist, density=pct_density
                        )
                    )
                elif n_type == "elevator":
                    steps.append(
                        t_dict["take_elevator"].format(
                            label=label, dist=dist, density=pct_density
                        )
                    )
                else:
                    steps.append(
                        t_dict["head_to"].format(
                            label=label, dist=dist, density=pct_density
                        )
                    )

        return {
            "success": True,
            "profile": profile,
            "profile_label": t_dict[profile],
            "language": lang,
            "path": best_path,
            "total_distance_meters": round(total_distance, 1),
            "total_time_minutes": round(total_time_seconds / 60.0, 1),
            "estimated_carbon_grams": round(total_carbon, 1),
            "carbon_info": t_dict["carbon_saved"].format(carbon=round(total_carbon, 1)),
            "steps": steps,
        }


# Global service instance
routing_service = RoutingService()
