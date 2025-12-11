"""Neighborhood operations for solution modification."""

import copy
import random
import logging
from typing import Dict, List, Tuple, Optional

from src.models import Vehicle, Shipment, Network

logger = logging.getLogger("cvrp.optimization")


def generate_neighbor(
    solution: Dict[Vehicle, List[Shipment]],
    network: Network
) -> Dict[Vehicle, List[Shipment]]:
    """
    Generate a neighbor solution using a random move.
    
    Args:
        solution: Current solution
        network: The transportation network
    
    Returns:
        Modified neighbor solution
    """
    # Create deep copy
    neighbor = copy.deepcopy(solution)
    
    # Choose move type with weights
    moves = [
        ("swap", 0.4),
        ("transfer", 0.3),
        ("relocate", 0.2),
        ("reverse", 0.1)
    ]
    
    move_type = random.choices(
        [m[0] for m in moves],
        weights=[m[1] for m in moves]
    )[0]
    
    if move_type == "swap":
        neighbor = swap_between_vehicles(neighbor, network)
    elif move_type == "transfer":
        neighbor = transfer_shipment(neighbor, network)
    elif move_type == "relocate":
        neighbor = relocate_within_vehicle(neighbor)
    elif move_type == "reverse":
        neighbor = reverse_subroute(neighbor)
    
    return neighbor


def swap_between_vehicles(
    solution: Dict[Vehicle, List[Shipment]],
    network: Network
) -> Dict[Vehicle, List[Shipment]]:
    """
    Swap shipments between two vehicles.
    
    Args:
        solution: Current solution
        network: The transportation network
    
    Returns:
        Modified solution
    """
    vehicles = list(solution.keys())
    if len(vehicles) < 2:
        return solution
    
    # Select two random vehicles
    v1, v2 = random.sample(vehicles, 2)
    
    # If either is empty, try transfer instead
    if not solution[v1] or not solution[v2]:
        return transfer_shipment(solution, network)
    
    # Try different swap strategies
    strategies = [
        single_swap,
        destination_swap,
        proximity_swap,
    ]
    random.shuffle(strategies)
    
    for strategy in strategies:
        result = strategy(solution, v1, v2, network)
        if result is not solution:  # Strategy succeeded
            return result
    
    return solution


def single_swap(
    solution: Dict[Vehicle, List[Shipment]],
    v1: Vehicle,
    v2: Vehicle,
    network: Network
) -> Dict[Vehicle, List[Shipment]]:
    """Swap single shipments between two vehicles."""
    if not solution[v1] or not solution[v2]:
        return solution
    
    s1 = random.choice(solution[v1])
    s2 = random.choice(solution[v2])
    
    # Calculate new loads
    v1_new_cbm = sum(s.total_cbm for s in solution[v1] if s != s1) + s2.total_cbm
    v1_new_weight = sum(s.weight for s in solution[v1] if s != s1) + s2.weight
    v2_new_cbm = sum(s.total_cbm for s in solution[v2] if s != s2) + s1.total_cbm
    v2_new_weight = sum(s.weight for s in solution[v2] if s != s2) + s1.weight
    
    # Check capacity constraints
    if (v1_new_cbm <= v1.max_cbm and v1_new_weight <= v1.max_weight and
        v2_new_cbm <= v2.max_cbm and v2_new_weight <= v2.max_weight):
        
        solution[v1].remove(s1)
        solution[v2].remove(s2)
        solution[v1].append(s2)
        solution[v2].append(s1)
        
        logger.debug(f"Swapped {s1.shipment_id} <-> {s2.shipment_id}")
        return solution
    
    return solution


def destination_swap(
    solution: Dict[Vehicle, List[Shipment]],
    v1: Vehicle,
    v2: Vehicle,
    network: Network
) -> Dict[Vehicle, List[Shipment]]:
    """Swap shipments going to the same destination."""
    if not solution[v1] or not solution[v2]:
        return solution
    
    # Find common destinations
    v1_dests = {s.delivery_location_id for s in solution[v1]}
    v2_dests = {s.delivery_location_id for s in solution[v2]}
    common = v1_dests & v2_dests
    
    if not common:
        return solution
    
    # Pick a random common destination
    dest = random.choice(list(common))
    
    # Get shipments to that destination
    s1_candidates = [s for s in solution[v1] if s.delivery_location_id == dest]
    s2_candidates = [s for s in solution[v2] if s.delivery_location_id == dest]
    
    if not s1_candidates or not s2_candidates:
        return solution
    
    s1 = random.choice(s1_candidates)
    s2 = random.choice(s2_candidates)
    
    # Check capacity
    v1_new_cbm = sum(s.total_cbm for s in solution[v1] if s != s1) + s2.total_cbm
    v1_new_weight = sum(s.weight for s in solution[v1] if s != s1) + s2.weight
    v2_new_cbm = sum(s.total_cbm for s in solution[v2] if s != s2) + s1.total_cbm
    v2_new_weight = sum(s.weight for s in solution[v2] if s != s2) + s1.weight
    
    if (v1_new_cbm <= v1.max_cbm and v1_new_weight <= v1.max_weight and
        v2_new_cbm <= v2.max_cbm and v2_new_weight <= v2.max_weight):
        
        solution[v1].remove(s1)
        solution[v2].remove(s2)
        solution[v1].append(s2)
        solution[v2].append(s1)
        
        logger.debug(f"Destination swap: {s1.shipment_id} <-> {s2.shipment_id}")
        return solution
    
    return solution


def proximity_swap(
    solution: Dict[Vehicle, List[Shipment]],
    v1: Vehicle,
    v2: Vehicle,
    network: Network
) -> Dict[Vehicle, List[Shipment]]:
    """Swap shipments going to nearby destinations."""
    if not solution[v1] or not solution[v2]:
        return solution
    
    # Find pairs of shipments with nearby destinations
    for s1 in solution[v1]:
        for s2 in solution[v2]:
            distance = network.shortest_path_length(
                s1.delivery_location_id,
                s2.delivery_location_id
            )
            
            # If destinations are close (< 500km)
            if distance < 500:
                # Check capacity
                v1_new_cbm = sum(s.total_cbm for s in solution[v1] if s != s1) + s2.total_cbm
                v2_new_cbm = sum(s.total_cbm for s in solution[v2] if s != s2) + s1.total_cbm
                
                if v1_new_cbm <= v1.max_cbm and v2_new_cbm <= v2.max_cbm:
                    solution[v1].remove(s1)
                    solution[v2].remove(s2)
                    solution[v1].append(s2)
                    solution[v2].append(s1)
                    
                    logger.debug(f"Proximity swap: {s1.shipment_id} <-> {s2.shipment_id}")
                    return solution
    
    return solution


def transfer_shipment(
    solution: Dict[Vehicle, List[Shipment]],
    network: Network
) -> Dict[Vehicle, List[Shipment]]:
    """
    Transfer shipment(s) from one vehicle to another.
    
    Args:
        solution: Current solution
        network: The transportation network
    
    Returns:
        Modified solution
    """
    vehicles = list(solution.keys())
    
    # Get vehicles with shipments
    active = [v for v in vehicles if solution[v]]
    if not active:
        return solution
    
    # Choose source vehicle
    source = random.choice(active)
    
    # Choose target vehicle (can be empty)
    targets = [v for v in vehicles if v != source]
    if not targets:
        return solution
    
    target = random.choice(targets)
    
    # Choose shipment(s) to transfer
    num_to_transfer = random.randint(1, min(3, len(solution[source])))
    shipments_to_move = random.sample(solution[source], num_to_transfer)
    
    # Check if target can accommodate
    transfer_cbm = sum(s.total_cbm for s in shipments_to_move)
    transfer_weight = sum(s.weight for s in shipments_to_move)
    target_cbm = sum(s.total_cbm for s in solution[target])
    target_weight = sum(s.weight for s in solution[target])
    
    if (target_cbm + transfer_cbm <= target.max_cbm and
        target_weight + transfer_weight <= target.max_weight):
        
        for shipment in shipments_to_move:
            solution[source].remove(shipment)
            solution[target].append(shipment)
        
        logger.debug(
            f"Transferred {len(shipments_to_move)} shipments: "
            f"{source.vehicle_id} -> {target.vehicle_id}"
        )
    
    return solution


def relocate_within_vehicle(
    solution: Dict[Vehicle, List[Shipment]]
) -> Dict[Vehicle, List[Shipment]]:
    """
    Relocate a shipment to a different position within the same vehicle.
    
    Args:
        solution: Current solution
    
    Returns:
        Modified solution
    """
    # Get vehicles with multiple shipments
    candidates = [v for v in solution if len(solution[v]) >= 2]
    if not candidates:
        return solution
    
    vehicle = random.choice(candidates)
    shipments = solution[vehicle]
    
    # Pick a shipment and new position
    old_pos = random.randrange(len(shipments))
    new_pos = random.randrange(len(shipments))
    
    if old_pos != new_pos:
        shipment = shipments.pop(old_pos)
        shipments.insert(new_pos, shipment)
        logger.debug(f"Relocated shipment in {vehicle.vehicle_id}: {old_pos} -> {new_pos}")
    
    return solution


def reverse_subroute(
    solution: Dict[Vehicle, List[Shipment]]
) -> Dict[Vehicle, List[Shipment]]:
    """
    Reverse a segment of shipments within a vehicle's route.
    
    Args:
        solution: Current solution
    
    Returns:
        Modified solution
    """
    # Get vehicles with enough shipments to reverse
    candidates = [v for v in solution if len(solution[v]) >= 3]
    if not candidates:
        return solution
    
    vehicle = random.choice(candidates)
    shipments = solution[vehicle]
    
    # Pick segment to reverse
    start = random.randint(0, len(shipments) - 3)
    end = random.randint(start + 2, len(shipments))
    
    solution[vehicle][start:end] = list(reversed(solution[vehicle][start:end]))
    logger.debug(f"Reversed subroute in {vehicle.vehicle_id}: [{start}:{end}]")
    
    return solution


def consolidate_destinations(
    solution: Dict[Vehicle, List[Shipment]],
    network: Network
) -> Dict[Vehicle, List[Shipment]]:
    """
    Consolidate shipments to the same destination on the same vehicle.
    
    This is a repair operation that tries to group shipments
    going to the same place.
    
    Args:
        solution: Current solution
        network: The transportation network
    
    Returns:
        Consolidated solution
    """
    # Collect all shipments by destination
    dest_shipments: Dict[str, List[Tuple[Vehicle, Shipment]]] = {}
    
    for vehicle, shipments in solution.items():
        for shipment in shipments:
            dest = shipment.delivery_location_id
            if dest not in dest_shipments:
                dest_shipments[dest] = []
            dest_shipments[dest].append((vehicle, shipment))
    
    # For each destination with multiple vehicles, try to consolidate
    for dest, items in dest_shipments.items():
        if len(items) <= 1:
            continue
        
        # Get unique vehicles serving this destination
        vehicles_for_dest = list(set(v for v, _ in items))
        if len(vehicles_for_dest) <= 1:
            continue
        
        # Try to move all to the vehicle with most capacity
        best_vehicle = max(
            vehicles_for_dest,
            key=lambda v: v.max_cbm - sum(s.total_cbm for s in solution[v])
        )
        
        for vehicle, shipment in items:
            if vehicle == best_vehicle:
                continue
            
            # Check if we can move this shipment
            current_cbm = sum(s.total_cbm for s in solution[best_vehicle])
            if current_cbm + shipment.total_cbm <= best_vehicle.max_cbm:
                solution[vehicle].remove(shipment)
                solution[best_vehicle].append(shipment)
    
    return solution
