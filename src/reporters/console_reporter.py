"""Result reporting utilities."""

from typing import Dict, List
from src.models import Vehicle, Shipment
from src.optimization import OptimizationResult


def print_results(result: OptimizationResult) -> None:
    """
    Print optimization results to console.
    
    Args:
        result: The optimization result to print
    """
    print("\n" + "=" * 60)
    print("OPTIMIZATION RESULTS")
    print("=" * 60)
    
    # Overall summary
    print(f"\nBest Solution Cost: ${result.best_cost.defuzzify():,.2f}")
    print(f"Total Distance: {result.metrics['total_distance']:,.2f} km")
    print(f"Border Crossings: {result.metrics['total_border_crossings']}")
    print(f"Vehicles Used: {result.metrics['vehicles_used']}")
    print(f"Total Shipments: {result.metrics['total_shipments']}")
    print(f"Solution Valid: {result.validation.is_valid}")
    
    # Statistics
    print("\n--- Optimization Statistics ---")
    print(f"Iterations: {result.statistics['iterations']}")
    print(f"Accepted: {result.statistics['accepted']}")
    print(f"Rejected: {result.statistics['rejected']}")
    print(f"Improvements Found: {result.statistics['improvements']}")
    
    if result.statistics['accepted'] + result.statistics['rejected'] > 0:
        rate = result.statistics['accepted'] / (
            result.statistics['accepted'] + result.statistics['rejected']
        ) * 100
        print(f"Acceptance Rate: {rate:.1f}%")
    
    # Vehicle details
    print("\n--- Vehicle Details ---")
    for vehicle, shipments in result.best_solution.items():
        vehicle_metrics = result.metrics['vehicle_metrics'].get(vehicle.vehicle_id, {})
        
        print(f"\n{vehicle.vehicle_id}:")
        if not shipments:
            print("  No shipments assigned")
            continue
        
        route = vehicle_metrics.get('route', [])
        print(f"  Route: {' -> '.join(route)}")
        print(f"  Distance: {vehicle_metrics.get('distance', 0):,.2f} km")
        print(f"  Border Crossings: {vehicle_metrics.get('border_crossings', 0)}")
        print(f"  Volume Utilization: {vehicle_metrics.get('volume_utilization', 0):.1f}%")
        print(f"  Weight Utilization: {vehicle_metrics.get('weight_utilization', 0):.1f}%")
        print(f"  Shipments ({len(shipments)}):")
        for s in shipments:
            print(f"    - {s.shipment_id}: {s.total_cbm:.2f} CBM, {s.weight:.0f} kg -> {s.delivery_location_id}")
    
    # Cost comparisons
    if result.validation.cost_comparisons:
        print("\n--- Cost Comparison vs Historical ---")
        
        # Show total first (this is the TRUE comparison)
        if "TOTAL" in result.validation.cost_comparisons:
            total = result.validation.cost_comparisons["TOTAL"]
            print(f"\n** TOTAL SOLUTION (True Comparison) **")
            print(f"  Historical Total: ${total['historical_cost']:,.2f}")
            print(f"  Optimized Total:  ${total['current_cost']:,.2f}")
            if total['difference'] >= 0:
                print(f"  Savings:          ${total['difference']:,.2f} ({total['improvement_percentage']:.1f}% improvement)")
            else:
                print(f"  Extra Cost:       ${-total['difference']:,.2f} ({-total['improvement_percentage']:.1f}% worse)")
        
        # Show per-vehicle breakdown (informational only)
        print("\n  Per-Vehicle Breakdown (informational - shipments may differ):")
        for vehicle_id, comparison in result.validation.cost_comparisons.items():
            if vehicle_id == "TOTAL":
                continue
            print(f"    {vehicle_id}: ${comparison['current_cost']:,.2f} (was ${comparison['historical_cost']:,.2f})")
    
    # Violations
    if result.validation.violations:
        print("\n--- Violations ---")
        for violation in result.validation.violations:
            print(f"  ! {violation}")
    
    # Improvements
    if result.validation.improvements:
        print("\n--- Improvements ---")
        for improvement in result.validation.improvements:
            print(f"  + {improvement}")
    
    print("\n" + "=" * 60)


def format_solution_summary(
    solution: Dict[Vehicle, List[Shipment]]
) -> str:
    """
    Format a brief solution summary.
    
    Args:
        solution: The solution to summarize
    
    Returns:
        Formatted string summary
    """
    lines = []
    
    active_vehicles = sum(1 for s in solution.values() if s)
    total_shipments = sum(len(s) for s in solution.values())
    
    lines.append(f"Vehicles: {active_vehicles}/{len(solution)}")
    lines.append(f"Shipments: {total_shipments}")
    
    for vehicle, shipments in solution.items():
        if shipments:
            cbm = sum(s.total_cbm for s in shipments)
            weight = sum(s.weight for s in shipments)
            lines.append(
                f"  {vehicle.vehicle_id}: {len(shipments)} shipments, "
                f"{cbm:.1f} CBM, {weight:.0f} kg"
            )
    
    return "\n".join(lines)
