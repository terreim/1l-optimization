"""Data loading and parsing utilities."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

from src.models import Node, Edge, Vehicle, Shipment, Network

logger = logging.getLogger("cvrp.utils")


def load_json(filepath: str | Path) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        filepath: Path to the JSON file
    
    Returns:
        Parsed JSON data
    
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_nodes(nodes_data: Dict[str, Any]) -> Dict[str, Node]:
    """
    Parse nodes from JSON data.
    
    Args:
        nodes_data: JSON data containing locations
    
    Returns:
        Dictionary of Node objects keyed by node_id
    """
    if "locations" not in nodes_data:
        raise ValueError("Invalid nodes data: 'locations' key missing")
    
    locations = nodes_data["locations"]
    nodes = {}
    
    # Parse depots
    for depot in locations.get("depots", []):
        node = Node.from_dict(depot, node_type="depot")
        nodes[node.node_id] = node
    
    # Parse border crossings
    for border in locations.get("border_crossings", []):
        node = Node.from_dict(border, node_type="border_crossing")
        nodes[node.node_id] = node
    
    logger.debug(f"Parsed {len(nodes)} nodes")
    return nodes


def parse_edges(edges_data: Dict[str, Any]) -> Dict[str, Edge]:
    """
    Parse edges from JSON data.
    
    Args:
        edges_data: JSON data containing routes by country
    
    Returns:
        Dictionary of Edge objects keyed by edge_id
    """
    if "countries" not in edges_data:
        raise ValueError("Invalid edges data: 'countries' key missing")
    
    edges = {}
    
    for country, data in edges_data["countries"].items():
        time_windows = data.get("time_windows", [])
        
        for route_name, route_info in data.get("routes", {}).items():
            try:
                edge = Edge.from_route_data(route_name, route_info, time_windows)
                edges[edge.edge_id] = edge
            except ValueError as e:
                logger.warning(f"Skipping malformed route '{route_name}': {e}")
    
    logger.debug(f"Parsed {len(edges)} edges")
    return edges


def parse_vehicles(
    vehicles_data: Dict[str, Any], 
    packing_data: Dict[str, Any] | None = None
) -> List[Vehicle]:
    """
    Parse vehicles from JSON data and optionally load their shipments.
    
    Args:
        vehicles_data: JSON data containing fleet information
        packing_data: Optional JSON data containing packing plans
    
    Returns:
        List of Vehicle objects
    """
    if "fleet" not in vehicles_data:
        raise ValueError("Invalid vehicles data: 'fleet' key missing")
    
    vehicles = [Vehicle.from_dict(v) for v in vehicles_data["fleet"]]
    
    # Load shipments if packing data provided
    if packing_data:
        if "vehicles" not in packing_data:
            raise ValueError("Invalid packing data: 'vehicles' key missing")
        
        vehicle_map = {v.vehicle_id: v for v in vehicles}
        
        for veh_data in packing_data["vehicles"]:
            vehicle = vehicle_map.get(veh_data["id"])
            if vehicle:
                for shipment_data in veh_data.get("shipments", []):
                    shipment = Shipment.from_dict(shipment_data)
                    vehicle.add_shipment(shipment)
    
    logger.debug(f"Parsed {len(vehicles)} vehicles")
    return vehicles


def parse_shipments(packing_data: Dict[str, Any]) -> List[Shipment]:
    """
    Parse all shipments from packing plan data.
    
    Args:
        packing_data: JSON data containing packing plans
    
    Returns:
        List of all Shipment objects
    """
    if "vehicles" not in packing_data:
        raise ValueError("Invalid packing data: 'vehicles' key missing")
    
    shipments = []
    for vehicle_data in packing_data["vehicles"]:
        for shipment_data in vehicle_data.get("shipments", []):
            shipments.append(Shipment.from_dict(shipment_data))
    
    logger.debug(f"Parsed {len(shipments)} shipments")
    return shipments


def load_historical_costs(cost_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Process historical cost data to extract total costs per vehicle.
    
    Args:
        cost_data: Raw cost breakdown data
    
    Returns:
        Dictionary mapping vehicle IDs to total historical costs
    """
    costs = {}
    for vehicle_id, data in cost_data.items():
        if "total" in data and "total_cost" in data["total"]:
            costs[vehicle_id] = float(data["total"]["total_cost"])
    
    logger.debug(f"Loaded historical costs for {len(costs)} vehicles")
    return costs


def build_network(
    nodes: Dict[str, Node], 
    edges: Dict[str, Edge]
) -> Network:
    """
    Build a transportation network from nodes and edges.
    
    Args:
        nodes: Dictionary of nodes
        edges: Dictionary of edges
    
    Returns:
        Constructed Network instance
    """
    return Network.build_from_data(nodes, edges)


def save_json(data: Any, filepath: str | Path) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save (must be JSON-serializable)
        filepath: Path to save to
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    logger.debug(f"Saved data to {filepath}")
