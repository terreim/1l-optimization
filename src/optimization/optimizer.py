"""Simulated Annealing optimizer for the 1L-CVRP."""

import copy
import math
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from src.fuzzy import TriangularFuzzyNumber, fuzzy_dominance
from src.models import Vehicle, Shipment, Network, CostCalculator
from src.utils import SolutionValidator, ValidationResult
from src.optimization.initial_solution import SolutionGenerator
from src.optimization.neighborhood import generate_neighbor, consolidate_destinations
from src.optimization.route_optimizer import (
    optimize_solution_routes,
    evaluate_route_efficiency,
    calculate_route_distance,
)

logger = logging.getLogger("cvrp.optimization")


@dataclass
class OptimizationResult:
    """Results from the optimization run."""
    best_solution: Dict[Vehicle, List[Shipment]]
    best_cost: TriangularFuzzyNumber
    validation: ValidationResult
    metrics: Dict
    statistics: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.validation.is_valid,
            "best_cost": self.best_cost.defuzzify(),
            "metrics": self.metrics,
            "statistics": self.statistics,
            "cost_comparisons": self.validation.cost_comparisons,
            "improvements": self.validation.improvements,
            "violations": self.validation.violations,
        }


@dataclass
class SAParameters:
    """Simulated Annealing parameters."""
    initial_temperature: float = 2000.0
    cooling_rate: float = 0.995
    termination_temperature: float = 0.1
    max_iterations: int = 1000
    # Acceptance probability parameters
    min_acceptance: float = 0.0001


class SimulatedAnnealingOptimizer:
    """
    Simulated Annealing optimizer for the 1L-CVRP.
    
    Uses fuzzy cost calculations and multiple neighborhood operations
    to find good solutions.
    """
    
    def __init__(
        self,
        vehicles: List[Vehicle],
        shipments: List[Shipment],
        network: Network,
        cost_calculator: CostCalculator,
        validator: Optional[SolutionValidator] = None,
        params: Optional[SAParameters] = None
    ):
        self.vehicles = vehicles
        self.shipments = shipments
        self.network = network
        self.cost_calculator = cost_calculator
        self.validator = validator or SolutionValidator()
        self.params = params or SAParameters()
        
        # State
        self.current_solution: Optional[Dict[Vehicle, List[Shipment]]] = None
        self.current_cost: Optional[TriangularFuzzyNumber] = None
        self.best_solution: Optional[Dict[Vehicle, List[Shipment]]] = None
        self.best_cost: Optional[TriangularFuzzyNumber] = None
        self.best_validation: Optional[ValidationResult] = None
        
        # Temperature
        self.temperature = self.params.initial_temperature
    
    def optimize(self) -> OptimizationResult:
        """
        Run the optimization.
        
        Returns:
            OptimizationResult with best solution and statistics
        """
        # Generate initial solution
        logger.info("Generating initial solution...")
        generator = SolutionGenerator(
            self.vehicles,
            self.shipments,
            self.network,
            self.cost_calculator
        )
        self.current_solution = generator.generate(strategy="ffd_grouped")
        
        # Evaluate initial solution
        self.current_cost, current_validation = self._evaluate(self.current_solution)
        
        # Initialize best
        self.best_solution = copy.deepcopy(self.current_solution)
        self.best_cost = self.current_cost
        self.best_validation = current_validation
        
        logger.info(f"Initial cost: {self.current_cost.defuzzify():.2f}")
        
        # Statistics
        stats = {
            "iterations": 0,
            "accepted": 0,
            "rejected": 0,
            "improvements": 0,
        }
        
        # Main loop
        iteration = 0
        route_optimization_interval = 50  # Only optimize routes every N iterations
        
        while (self.temperature > self.params.termination_temperature and 
               iteration < self.params.max_iterations):
            
            # Generate neighbor
            neighbor = generate_neighbor(self.current_solution, self.network)
            
            # Only optimize routes periodically to save time
            if iteration % route_optimization_interval == 0:
                neighbor = optimize_solution_routes(neighbor, self.network)
            
            # Evaluate neighbor
            neighbor_cost, neighbor_validation = self._evaluate(neighbor)
            
            # Skip invalid solutions
            if not neighbor_validation.is_valid:
                stats["rejected"] += 1
                iteration += 1
                self.temperature *= self.params.cooling_rate
                continue
            
            # Calculate acceptance probability
            cost_diff = neighbor_cost.defuzzify() - self.current_cost.defuzzify()
            accept_prob = self._acceptance_probability(cost_diff)
            
            # Accept or reject
            if random.random() < accept_prob:
                self.current_solution = copy.deepcopy(neighbor)
                self.current_cost = neighbor_cost
                stats["accepted"] += 1
                
                # Update best if improved
                if neighbor_cost.defuzzify() < self.best_cost.defuzzify():
                    self.best_solution = copy.deepcopy(neighbor)
                    self.best_cost = neighbor_cost
                    self.best_validation = neighbor_validation
                    stats["improvements"] += 1
                    logger.info(f"New best: {self.best_cost.defuzzify():.2f} at iteration {iteration}")
            else:
                stats["rejected"] += 1
            
            # Cool down
            self.temperature *= self.params.cooling_rate
            iteration += 1
            
            # Log progress
            if iteration % 100 == 0:
                logger.info(
                    f"Iteration {iteration}: T={self.temperature:.2f}, "
                    f"Current={self.current_cost.defuzzify():.2f}, "
                    f"Best={self.best_cost.defuzzify():.2f}"
                )
        
        stats["iterations"] = iteration
        
        # Final consolidation
        self.best_solution = consolidate_destinations(self.best_solution, self.network)
        self.best_solution = optimize_solution_routes(self.best_solution, self.network)
        self.best_cost, self.best_validation = self._evaluate(self.best_solution)
        
        logger.info(f"Optimization complete. Best cost: {self.best_cost.defuzzify():.2f}")
        
        # Calculate final metrics
        metrics = self._calculate_metrics(self.best_solution)
        
        return OptimizationResult(
            best_solution=self.best_solution,
            best_cost=self.best_cost,
            validation=self.best_validation,
            metrics=metrics,
            statistics=stats
        )
    
    def _evaluate(
        self, 
        solution: Dict[Vehicle, List[Shipment]]
    ) -> Tuple[TriangularFuzzyNumber, ValidationResult]:
        """
        Evaluate a solution.
        
        Returns fuzzy cost and validation results.
        """
        total_cost = TriangularFuzzyNumber.zero()
        solution_costs = {}
        
        for vehicle, shipments in solution.items():
            if not shipments:
                continue
            
            # Build route
            route = [self.network.origin_code]
            seen = set()
            for s in shipments:
                if s.delivery_location_id not in seen:
                    route.append(s.delivery_location_id)
                    seen.add(s.delivery_location_id)
            
            # Calculate route cost
            route_cost = self.cost_calculator.calculate_route_cost(
                route, self.network, vehicle, shipments
            )
            
            # Add utilization penalties
            weight_util, vol_util = vehicle.get_utilization()
            if vol_util < 60 or weight_util < 30:
                penalty = TriangularFuzzyNumber(500, 750, 1000)
                route_cost = route_cost + penalty
            
            # Add route efficiency penalty
            efficiency = evaluate_route_efficiency(route, self.network)
            if efficiency > 0:
                eff_penalty = TriangularFuzzyNumber(
                    efficiency * 0.1,
                    efficiency * 0.15,
                    efficiency * 0.2
                )
                route_cost = route_cost + eff_penalty
            
            solution_costs[vehicle] = route_cost
            total_cost = total_cost + route_cost
        
        # Validate
        validation = self.validator.validate_solution(solution, solution_costs)
        
        return total_cost, validation
    
    def _acceptance_probability(self, cost_diff: float) -> float:
        """Calculate acceptance probability for a cost difference."""
        if cost_diff <= 0:
            return 1.0
        
        prob = math.exp(-cost_diff / max(self.temperature, 0.001))
        return max(self.params.min_acceptance, min(1.0, prob))
    
    def _calculate_metrics(
        self, 
        solution: Dict[Vehicle, List[Shipment]]
    ) -> Dict:
        """Calculate detailed metrics for a solution."""
        metrics = {
            "total_distance": 0.0,
            "total_border_crossings": 0,
            "vehicles_used": 0,
            "total_shipments": 0,
            "vehicle_metrics": {}
        }
        
        for vehicle, shipments in solution.items():
            if not shipments:
                metrics["vehicle_metrics"][vehicle.vehicle_id] = {
                    "num_shipments": 0,
                    "distance": 0,
                    "border_crossings": 0,
                    "volume_utilization": 0,
                    "weight_utilization": 0,
                    "route": []
                }
                continue
            
            metrics["vehicles_used"] += 1
            metrics["total_shipments"] += len(shipments)
            
            # Build route
            route = [self.network.origin_code]
            for s in shipments:
                if s.delivery_location_id not in route:
                    route.append(s.delivery_location_id)
            
            # Calculate distance
            distance = calculate_route_distance(
                self.network.origin_code,
                route[1:],
                self.network
            )
            metrics["total_distance"] += distance
            
            # Count border crossings
            crossings = 0
            current_country = self.network.get_country(self.network.origin_code)
            for node in route[1:]:
                next_country = self.network.get_country(node)
                if next_country and current_country != next_country:
                    crossings += 1
                    current_country = next_country
            metrics["total_border_crossings"] += crossings
            
            # Utilization
            weight_util, vol_util = vehicle.get_utilization()
            
            # Named route
            named_route = [self.network.get_node_name(n) for n in route]
            
            metrics["vehicle_metrics"][vehicle.vehicle_id] = {
                "num_shipments": len(shipments),
                "distance": distance,
                "border_crossings": crossings,
                "volume_utilization": vol_util,
                "weight_utilization": weight_util,
                "route": named_route
            }
        
        return metrics
