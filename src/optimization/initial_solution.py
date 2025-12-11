"""Initial solution generation strategies."""

import random
import logging
from typing import Dict, List, Tuple

from src.models import Vehicle, Shipment, Network, CostCalculator
from src.optimization.route_optimizer import optimize_solution_routes

logger = logging.getLogger("cvrp.optimization")


class SolutionGenerator:
    """
    Generates initial solutions for the optimization.
    
    Supports multiple strategies:
    - Random assignment
    - First-Fit Decreasing (FFD)
    - Destination-grouped FFD
    """
    
    def __init__(
        self,
        vehicles: List[Vehicle],
        shipments: List[Shipment],
        network: Network,
        cost_calculator: CostCalculator
    ):
        self.vehicles = vehicles
        self.shipments = shipments
        self.network = network
        self.cost_calculator = cost_calculator
        
        # Calculate totals for info
        self.total_cbm = sum(s.total_cbm for s in shipments)
        self.total_weight = sum(s.weight for s in shipments)
    
    def generate(self, strategy: str = "ffd_grouped") -> Dict[Vehicle, List[Shipment]]:
        """
        Generate an initial solution using the specified strategy.
        
        Args:
            strategy: One of 'random', 'ffd', 'ffd_grouped'
        
        Returns:
            Initial solution mapping vehicles to shipments
        """
        # Reset all vehicles
        for vehicle in self.vehicles:
            vehicle.reset_state()
        
        if strategy == "random":
            solution = self._generate_random()
        elif strategy == "ffd":
            solution = self._generate_ffd()
        elif strategy == "ffd_grouped":
            solution = self._generate_ffd_grouped()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Optimize routes after initial assignment
        solution = optimize_solution_routes(solution, self.network)
        
        return solution
    
    def _generate_random(self) -> Dict[Vehicle, List[Shipment]]:
        """Generate solution using random assignment."""
        solution = {v: [] for v in self.vehicles}
        
        # Shuffle shipments
        shuffled = random.sample(self.shipments, len(self.shipments))
        
        for shipment in shuffled:
            assigned = False
            
            # Try each vehicle in random order
            for vehicle in random.sample(self.vehicles, len(self.vehicles)):
                if vehicle.can_add_shipment(shipment):
                    vehicle.add_shipment(shipment)
                    solution[vehicle].append(shipment)
                    assigned = True
                    break
            
            if not assigned:
                logger.warning(f"Could not assign shipment {shipment.shipment_id}")
        
        return solution
    
    def _generate_ffd(self) -> Dict[Vehicle, List[Shipment]]:
        """Generate solution using First-Fit Decreasing by volume."""
        solution = {v: [] for v in self.vehicles}
        
        # Sort shipments by volume (descending)
        sorted_shipments = sorted(
            self.shipments,
            key=lambda s: s.total_cbm,
            reverse=True
        )
        
        for shipment in sorted_shipments:
            assigned = False
            
            # Find first vehicle that fits
            for vehicle in self.vehicles:
                if vehicle.can_add_shipment(shipment):
                    vehicle.add_shipment(shipment)
                    solution[vehicle].append(shipment)
                    assigned = True
                    break
            
            if not assigned:
                logger.warning(f"Could not assign shipment {shipment.shipment_id}")
        
        return solution
    
    def _generate_ffd_grouped(self) -> Dict[Vehicle, List[Shipment]]:
        """
        Generate solution using FFD with destination grouping.
        
        Groups shipments by destination and tries to keep
        shipments to the same destination on the same vehicle.
        """
        solution = {v: [] for v in self.vehicles}
        
        # Group shipments by destination
        dest_groups: Dict[str, List[Shipment]] = {}
        for shipment in self.shipments:
            dest = shipment.delivery_location_id
            if dest not in dest_groups:
                dest_groups[dest] = []
            dest_groups[dest].append(shipment)
        
        # Sort destinations by total volume and distance from origin
        sorted_destinations = []
        for dest, group in dest_groups.items():
            total_volume = sum(s.total_cbm for s in group)
            distance = self.network.shortest_path_length(
                self.network.origin_code, dest
            )
            sorted_destinations.append((dest, group, total_volume, distance))
        
        # Sort by distance (ascending), then volume (descending)
        sorted_destinations.sort(key=lambda x: (x[3], -x[2]))
        
        # Assign groups to vehicles
        for dest, group, total_volume, _ in sorted_destinations:
            # Sort shipments within group by volume
            sorted_group = sorted(group, key=lambda s: s.total_cbm, reverse=True)
            
            # Try to find a vehicle that can fit the entire group
            best_vehicle = None
            best_remaining = float("inf")
            
            for vehicle in self.vehicles:
                current_cbm = sum(s.total_cbm for s in solution[vehicle])
                current_weight = sum(s.weight for s in solution[vehicle])
                group_cbm = sum(s.total_cbm for s in sorted_group)
                group_weight = sum(s.weight for s in sorted_group)
                
                if (current_cbm + group_cbm <= vehicle.max_cbm * 1.001 and
                    current_weight + group_weight <= vehicle.max_weight * 1.001):
                    remaining = vehicle.max_cbm - (current_cbm + group_cbm)
                    if remaining < best_remaining:
                        best_remaining = remaining
                        best_vehicle = vehicle
            
            if best_vehicle:
                # Assign entire group to best vehicle
                for shipment in sorted_group:
                    best_vehicle.add_shipment(shipment)
                    solution[best_vehicle].append(shipment)
                logger.debug(f"Assigned {len(sorted_group)} shipments to {dest} on {best_vehicle.vehicle_id}")
            else:
                # Can't keep group together - assign individually
                for shipment in sorted_group:
                    assigned = False
                    for vehicle in self.vehicles:
                        if vehicle.can_add_shipment(shipment):
                            vehicle.add_shipment(shipment)
                            solution[vehicle].append(shipment)
                            assigned = True
                            break
                    
                    if not assigned:
                        logger.warning(f"Could not assign shipment {shipment.shipment_id}")
        
        return solution
    
    def get_solution_stats(
        self, 
        solution: Dict[Vehicle, List[Shipment]]
    ) -> Dict:
        """Get statistics about a solution."""
        stats = {
            "vehicles_used": 0,
            "total_shipments": 0,
            "total_cbm": 0.0,
            "total_weight": 0.0,
            "avg_volume_utilization": 0.0,
            "avg_weight_utilization": 0.0,
            "vehicle_stats": {}
        }
        
        volume_utils = []
        weight_utils = []
        
        for vehicle, shipments in solution.items():
            if not shipments:
                continue
            
            stats["vehicles_used"] += 1
            stats["total_shipments"] += len(shipments)
            
            cbm = sum(s.total_cbm for s in shipments)
            weight = sum(s.weight for s in shipments)
            
            stats["total_cbm"] += cbm
            stats["total_weight"] += weight
            
            vol_util = (cbm / vehicle.max_cbm) * 100
            wgt_util = (weight / vehicle.max_weight) * 100
            
            volume_utils.append(vol_util)
            weight_utils.append(wgt_util)
            
            stats["vehicle_stats"][vehicle.vehicle_id] = {
                "shipments": len(shipments),
                "cbm": cbm,
                "weight": weight,
                "volume_utilization": vol_util,
                "weight_utilization": wgt_util
            }
        
        if volume_utils:
            stats["avg_volume_utilization"] = sum(volume_utils) / len(volume_utils)
            stats["avg_weight_utilization"] = sum(weight_utils) / len(weight_utils)
        
        return stats
