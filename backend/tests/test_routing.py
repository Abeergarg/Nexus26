import sys
import os

# Ensure backend folder is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.features.wayfinding.service import routing_service


def test_accessible_routing_stairs_avoidance():
    # Save original densities and set to 0.0 to ensure shortest path choice
    original_densities = {}
    for node_id, edges in routing_service.adj.items():
        for edge in edges:
            key = (edge["source"], edge["target"])
            original_densities[key] = edge.get("density", 0.0)
            edge["density"] = 0.0

    try:
        route_std = routing_service.calculate_route(
            "Section_101", "Section_201", profile="standard"
        )
        route_acc = routing_service.calculate_route(
            "Section_101", "Section_201", profile="mobility_impaired"
        )

        assert route_std["success"] is True
        assert route_acc["success"] is True

        # Standard route selects Stairs_North
        assert "Stairs_North" in route_std["path"]

        # Accessible route avoids Stairs_North, routing through Elevator_West instead
        assert "Stairs_North" not in route_acc["path"]
        assert "Elevator_West" in route_acc["path"]

    finally:
        # Restore original densities
        for node_id, edges in routing_service.adj.items():
            for edge in edges:
                key = (edge["source"], edge["target"])
                if key in original_densities:
                    edge["density"] = original_densities[key]


def test_green_transit_routing():
    # Gate_D to Eco_Bike_Share (high green_factor)
    route = routing_service.calculate_route("Gate_D", "Eco_Bike_Share", profile="green")
    assert route["success"] is True
    # Carbon calculations: 50m * (1 - 0.95) * 100 = 250g
    assert route["estimated_carbon_grams"] == 250.0
