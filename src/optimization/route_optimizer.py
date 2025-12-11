"""Route optimization algorithms."""

import itertools
from typing import Dict, List, Callable, Optional

from src.models import Network, Vehicle, Shipment


def nearest_neighbor(
    origin: str,
    destinations: List[str],
    network: Network
) -> List[str]:
    """
    Construct a route using the nearest neighbor heuristic.
    
    Args:
        origin: Starting node code
        destinations: List of destination node codes
        network: The transportation network
    
    Returns:
        Ordered list of destinations (not including origin)
    """
    if not destinations:
        return []
    
    route = []
    unvisited = set(destinations)
    current = origin
    
    while unvisited:
        # Find nearest unvisited destination
        best_next = None
        best_distance = float("inf")
        
        for dest in unvisited:
            distance = network.shortest_path_length(current, dest)
            if distance < best_distance:
                best_distance = distance
                best_next = dest
        
        if best_next is None:
            # No reachable destinations - add remaining in original order
            route.extend([d for d in destinations if d in unvisited])
            break
        
        route.append(best_next)
        unvisited.remove(best_next)
        current = best_next
    
    return route


def two_opt_improvement(
    route: List[str],
    network: Network,
    origin: str = "NNG"
) -> List[str]:
    """
    Improve a route using 2-opt local search.
    
    Args:
        route: Current route (list of destination codes)
        network: The transportation network
        origin: Starting point
    
    Returns:
        Improved route
    """
    if len(route) < 3:
        return route
    
    improved = True
    current_route = route.copy()
    
    while improved:
        improved = False
        
        for i in range(len(current_route) - 1):
            for j in range(i + 2, len(current_route)):
                # Calculate current cost for edges being removed
                prev_i = origin if i == 0 else current_route[i - 1]
                curr_cost = (
                    network.shortest_path_length(prev_i, current_route[i]) +
                    network.shortest_path_length(current_route[j - 1], current_route[j])
                )
                
                # Calculate new cost if we reverse the segment
                new_cost = (
                    network.shortest_path_length(prev_i, current_route[j - 1]) +
                    network.shortest_path_length(current_route[i], current_route[j])
                )
                
                if new_cost < curr_cost:
                    # Reverse the segment
                    current_route[i:j] = reversed(current_route[i:j])
                    improved = True
    
    return current_route


def optimize_route(
    origin: str,
    destinations: List[str],
    network: Network
) -> List[str]:
    """
    Optimize a route using nearest neighbor + 2-opt.
    
    Args:
        origin: Starting node code
        destinations: List of destination node codes
        network: The transportation network
    
    Returns:
        Optimized route (list of destination codes)
    """
    # Start with nearest neighbor
    route = nearest_neighbor(origin, destinations, network)
    
    # Improve with 2-opt
    route = two_opt_improvement(route, network, origin)
    
    return route


def optimize_route_exact(
    origin: str,
    destinations: List[str],
    network: Network,
    max_exact_size: int = 5  # Reduced from 8 - 5! = 120 vs 8! = 40320
) -> List[str]:
    """
    Optimize route - exact for small instances, heuristic for large.
    
    Args:
        origin: Starting node code
        destinations: Unique destinations to visit
        network: The transportation network
        max_exact_size: Maximum size for exact enumeration (default 5)
    
    Returns:
        Optimized route
    """
    if not destinations:
        return []
    
    if len(destinations) <= max_exact_size:
        # Try all permutations for small instances
        best_route = list(destinations)
        best_cost = float("inf")
        
        for perm in itertools.permutations(destinations):
            route = list(perm)
            cost = calculate_route_distance(origin, route, network)
            if cost < best_cost:
                best_cost = cost
                best_route = route
        
        return best_route
    else:
        # Use heuristic for larger instances
        return optimize_route(origin, destinations, network)


def calculate_route_distance(
    origin: str,
    route: List[str],
    network: Network
) -> float:
    """
    Calculate total distance for a route.
    
    Args:
        origin: Starting node
        route: List of nodes to visit in order
        network: The transportation network
    
    Returns:
        Total distance
    """
    if not route:
        return 0.0
    
    total = network.shortest_path_length(origin, route[0])
    
    for i in range(len(route) - 1):
        total += network.shortest_path_length(route[i], route[i + 1])
    
    return total


def evaluate_route_efficiency(
    route: List[str],
    network: Network,
    origin: str = "NNG"
) -> float:
    """
    Evaluate route efficiency, returning a penalty score.
    
    Lower score = better route.
    
    Args:
        route: Route to evaluate (list of destination codes, NOT including origin)
        network: The transportation network
        origin: Starting point
    
    Returns:
        Penalty score (0 = perfect)
    """
    if len(route) <= 1:
        return 0.0
    
    penalty = 0.0
    
    # Penalty for repeated destinations (O(n))
    seen = set()
    for dest in route:
        if dest in seen:
            penalty += 2000
        seen.add(dest)
    
    # Calculate total distance (uses cached lookups - O(n))
    full_route = [origin] + list(route)
    total_distance = 0.0
    
    for i in range(len(full_route) - 1):
        dist = network.shortest_path_length(full_route[i], full_route[i + 1])
        if dist == float("inf"):
            return float("inf")
        total_distance += dist
    
    # Simplified backtracking penalty - only check every other triplet
    # This reduces complexity while still catching major issues
    for i in range(0, len(full_route) - 2, 2):  # Step by 2 instead of 1
        a, b, c = full_route[i], full_route[i + 1], full_route[i + 2]
        direct = network.shortest_path_length(a, c)
        through_b = (
            network.shortest_path_length(a, b) +
            network.shortest_path_length(b, c)
        )
        
        # Penalize if going through b is more than 30% longer
        if through_b > direct * 1.3:
            penalty += (through_b - direct) * 2
    
    return total_distance + penalty


def group_shipments_by_destination(
    shipments: List[Shipment]
) -> Dict[str, List[Shipment]]:
    """
    Group shipments by their delivery destination.
    
    Args:
        shipments: List of shipments
    
    Returns:
        Dictionary mapping destination codes to shipments
    """
    groups = {}
    for shipment in shipments:
        dest = shipment.delivery_location_id
        if dest not in groups:
            groups[dest] = []
        groups[dest].append(shipment)
    return groups


def group_shipments_by_region(
    shipments: List[Shipment],
    network: Network,
    origin: str = "NNG"
) -> Dict[str, List[Shipment]]:
    """
    Group shipments by geographical regions based on distance from origin.
    
    Args:
        shipments: List of shipments
        network: The transportation network
        origin: Origin node code
    
    Returns:
        Dictionary mapping region names to shipments
    """
    if not shipments:
        return {}
    
    # Calculate distances from origin
    distances = []
    for shipment in shipments:
        dist = network.shortest_path_length(origin, shipment.delivery_location_id)
        if dist < float("inf"):
            distances.append((shipment, dist))
    
    if not distances:
        return {"default": shipments}
    
    # Sort by distance
    distances.sort(key=lambda x: x[1])
    sorted_dists = [d[1] for d in distances]
    
    # Define quartile thresholds
    n = len(sorted_dists)
    q1 = sorted_dists[n // 4] if n > 3 else sorted_dists[0]
    q2 = sorted_dists[n // 2] if n > 1 else sorted_dists[0]
    q3 = sorted_dists[3 * n // 4] if n > 3 else sorted_dists[-1]
    
    # Assign to regions
    regions = {"near": [], "mid": [], "far": [], "very_far": []}
    
    for shipment, dist in distances:
        if dist <= q1:
            regions["near"].append(shipment)
        elif dist <= q2:
            regions["mid"].append(shipment)
        elif dist <= q3:
            regions["far"].append(shipment)
        else:
            regions["very_far"].append(shipment)
    
    # Remove empty regions
    return {k: v for k, v in regions.items() if v}


def optimize_solution_routes(
    solution: Dict[Vehicle, List[Shipment]],
    network: Network,
    origin: str = "NNG"
) -> Dict[Vehicle, List[Shipment]]:
    """
    Optimize routes for all vehicles in a solution.
    
    Reorders shipments to minimize travel distance while
    respecting delivery constraints.
    
    Args:
        solution: Current solution mapping vehicles to shipments
        network: The transportation network
        origin: Starting point
    
    Returns:
        Solution with optimized shipment ordering
    """
    optimized = {}
    
    for vehicle, shipments in solution.items():
        if not shipments:
            optimized[vehicle] = []
            continue
        
        # Get unique destinations
        destinations = list(set(s.delivery_location_id for s in shipments))
        
        # Optimize destination order
        optimized_order = optimize_route_exact(origin, destinations, network)
        
        # Create ordering map
        order_map = {dest: i for i, dest in enumerate(optimized_order)}
        
        # Sort shipments by optimized destination order
        ordered_shipments = sorted(
            shipments,
            key=lambda s: order_map.get(s.delivery_location_id, float("inf"))
        )
        
        optimized[vehicle] = ordered_shipments
    
    return optimized
