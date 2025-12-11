"""Solution validation utilities."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.models import Vehicle, Shipment, Network
from src.fuzzy import TriangularFuzzyNumber


@dataclass
class ValidationResult:
    """Results of solution validation."""
    is_valid: bool = True
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cost_comparisons: Dict[str, Dict] = field(default_factory=dict)
    improvements: List[str] = field(default_factory=list)
    
    def add_violation(self, message: str) -> None:
        """Add a validation violation."""
        self.violations.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a validation warning (non-fatal)."""
        self.warnings.append(message)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "violations": self.violations,
            "warnings": self.warnings,
            "cost_comparisons": self.cost_comparisons,
            "improvements": self.improvements
        }


class SolutionValidator:
    """
    Validates solutions against constraints and historical data.
    """
    
    def __init__(self, historical_costs: Optional[Dict[str, float]] = None):
        """
        Initialize validator with optional historical cost data.
        
        Args:
            historical_costs: Dictionary mapping vehicle IDs to historical costs
        """
        self.historical_costs = historical_costs or {}
    
    def validate_solution(
        self,
        solution: Dict[Vehicle, List[Shipment]],
        solution_costs: Optional[Dict[Vehicle, TriangularFuzzyNumber]] = None
    ) -> ValidationResult:
        """
        Validate a complete solution.
        
        Args:
            solution: Dictionary mapping vehicles to shipments
            solution_costs: Optional pre-calculated costs per vehicle
        
        Returns:
            ValidationResult with detailed validation information
        """
        result = ValidationResult()
        
        # Check capacity constraints
        self._validate_capacities(solution, result)
        
        # Check for unassigned shipments (if we had the full list)
        # This would require knowing all shipments that should be assigned
        
        # Compare with historical costs if available
        if solution_costs and self.historical_costs:
            self._compare_costs(solution, solution_costs, result)
        
        return result
    
    def _validate_capacities(
        self,
        solution: Dict[Vehicle, List[Shipment]],
        result: ValidationResult
    ) -> None:
        """Check that all vehicles are within capacity limits."""
        for vehicle, shipments in solution.items():
            total_cbm = sum(s.total_cbm for s in shipments)
            total_weight = sum(s.weight for s in shipments)
            
            # Check volume
            if total_cbm > vehicle.max_cbm * 1.001:  # Allow tiny tolerance
                result.add_violation(
                    f"Vehicle {vehicle.vehicle_id} exceeds volume capacity: "
                    f"{total_cbm:.2f}/{vehicle.max_cbm:.2f} CBM"
                )
            
            # Check weight
            if total_weight > vehicle.max_weight * 1.001:
                result.add_violation(
                    f"Vehicle {vehicle.vehicle_id} exceeds weight capacity: "
                    f"{total_weight:.2f}/{vehicle.max_weight:.2f} kg"
                )
    
    def _compare_costs(
        self,
        solution: Dict[Vehicle, List[Shipment]],
        solution_costs: Dict[Vehicle, TriangularFuzzyNumber],
        result: ValidationResult
    ) -> None:
        """
        Compare solution costs with historical data.
        
        NOTE: Per-vehicle comparison is shown for info only.
        The TRUE comparison is total optimized vs total historical,
        since the optimizer may reassign shipments between vehicles.
        """
        # Calculate totals for the TRUE comparison
        total_historical = sum(self.historical_costs.values())
        total_current = sum(
            cost.defuzzify() 
            for vehicle, cost in solution_costs.items() 
            if solution.get(vehicle)
        )
        
        # Per-vehicle breakdown (for information)
        for vehicle, shipments in solution.items():
            if not shipments:
                continue
            
            vehicle_id = vehicle.vehicle_id
            if vehicle not in solution_costs:
                continue
            
            current_cost = solution_costs[vehicle].defuzzify()
            
            # Get historical cost for this vehicle (if exists)
            # Note: This comparison is INFORMATIONAL ONLY since shipments differ
            historical_cost = self.historical_costs.get(vehicle_id, 0)
            difference = historical_cost - current_cost
            
            if historical_cost > 0:
                improvement_pct = (difference / historical_cost) * 100
            else:
                improvement_pct = 0
            
            result.cost_comparisons[vehicle_id] = {
                "historical_cost": historical_cost,
                "current_cost": current_cost,
                "difference": difference,
                "improvement_percentage": improvement_pct,
                "note": "Shipments may differ from historical - compare totals instead"
            }
        
        # Add the TRUE total comparison
        total_difference = total_historical - total_current
        if total_historical > 0:
            total_improvement_pct = (total_difference / total_historical) * 100
        else:
            total_improvement_pct = 0
        
        result.cost_comparisons["TOTAL"] = {
            "historical_cost": total_historical,
            "current_cost": total_current,
            "difference": total_difference,
            "improvement_percentage": total_improvement_pct,
            "note": "TRUE comparison - total solution cost"
        }
        
        if total_difference > 0:
            result.improvements.append(
                f"TOTAL SOLUTION: {total_improvement_pct:.2f}% improvement "
                f"(${total_difference:,.2f} saved)"
            )
    
    @staticmethod
    def is_feasible(solution: Dict[Vehicle, List[Shipment]]) -> bool:
        """Quick check if solution respects capacity constraints."""
        for vehicle, shipments in solution.items():
            total_cbm = sum(s.total_cbm for s in shipments)
            total_weight = sum(s.weight for s in shipments)
            
            if total_cbm > vehicle.max_cbm * 1.001:
                return False
            if total_weight > vehicle.max_weight * 1.001:
                return False
        
        return True


def validate_route(
    route: List[str],
    network: Network,
    origin: str = "NNG"
) -> bool:
    """
    Validate that a route is feasible in the network.
    
    Args:
        route: List of node codes to visit
        network: The transportation network
        origin: Starting point (default: NNG)
    
    Returns:
        True if route is valid, False otherwise
    """
    if not route:
        return True
    
    current = origin
    
    for next_stop in route:
        if not network.is_connected(current, next_stop):
            return False
        current = next_stop
    
    return True
