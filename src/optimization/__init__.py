"""Optimization algorithms for the 1L-CVRP."""

from .optimizer import (
    SimulatedAnnealingOptimizer,
    SAParameters,
    OptimizationResult,
)
from .initial_solution import SolutionGenerator
from .neighborhood import (
    generate_neighbor,
    swap_between_vehicles,
    transfer_shipment,
    consolidate_destinations,
)
from .route_optimizer import (
    optimize_route,
    optimize_solution_routes,
    nearest_neighbor,
    two_opt_improvement,
    calculate_route_distance,
    evaluate_route_efficiency,
    group_shipments_by_destination,
    group_shipments_by_region,
)

__all__ = [
    "SimulatedAnnealingOptimizer",
    "SAParameters",
    "OptimizationResult",
    "SolutionGenerator",
    "generate_neighbor",
    "swap_between_vehicles",
    "transfer_shipment",
    "consolidate_destinations",
    "optimize_route",
    "optimize_solution_routes",
    "nearest_neighbor",
    "two_opt_improvement",
    "calculate_route_distance",
    "evaluate_route_efficiency",
    "group_shipments_by_destination",
    "group_shipments_by_region",
]
