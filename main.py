#!/usr/bin/env python3
"""
1L-CVRP Optimization

Capacitated Vehicle Routing Problem with 1-Dimensional Loading optimization
using Simulated Annealing with fuzzy cost calculations.

Usage:
    python main.py [options]

Options:
    --packing-plan FILE      Packing plan JSON filename (default: packing_plan3.json)
    --historical-costs FILE  Historical costs JSON filename (default: cost_breakdown3.json)
    --results-file FILE      Output results filename (default: optimization_results.json)
    --max-iterations N       Maximum SA iterations (default: 1000)
    --verbose               Enable verbose logging
"""

import argparse
import sys
import logging
from pathlib import Path

from src import Config, OptimizerParams, setup_logging
from src.utils import (
    load_json,
    save_json,
    parse_nodes,
    parse_edges,
    parse_vehicles,
    load_historical_costs,
    build_network,
    SolutionValidator,
)
from src.models import CostCalculator
from src.optimization import SimulatedAnnealingOptimizer, SAParameters
from src.reporters import print_results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="1L-CVRP Optimization using Simulated Annealing"
    )
    parser.add_argument(
        "--packing-plan",
        type=str,
        default="packing_plan3.json",
        help="Filename of the packing plan JSON"
    )
    parser.add_argument(
        "--historical-costs",
        type=str,
        default="cost_breakdown3.json",
        help="Filename of the historical costs JSON"
    )
    parser.add_argument(
        "--results-file",
        type=str,
        default="optimization_results.json",
        help="Filename to save results"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1000,
        help="Maximum SA iterations"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(level=log_level)
    
    try:
        # Create configuration
        config = Config(
            packing_plan_file=args.packing_plan,
            historical_costs_file=args.historical_costs,
            results_file=args.results_file,
            optimizer_params=OptimizerParams(max_iterations=args.max_iterations)
        )
        
        logger.info("Loading data...")
        
        # Load and parse data
        nodes_data = load_json(config.nodes_file)
        vehicles_data = load_json(config.vehicles_file)
        edges_data = load_json(config.edges_file)
        packing_data = load_json(config.packing_plan_file)
        historical_costs_data = load_json(config.historical_costs_file)
        
        # Parse into objects
        nodes = parse_nodes(nodes_data)
        edges = parse_edges(edges_data)
        vehicles = parse_vehicles(vehicles_data, packing_data)
        historical_costs = load_historical_costs(historical_costs_data)
        
        # Build network
        network = build_network(nodes, edges)
        
        logger.info(f"Loaded {len(nodes)} nodes, {len(edges)} edges, {len(vehicles)} vehicles")
        
        # Initialize components
        cost_calculator = CostCalculator()
        validator = SolutionValidator(historical_costs)
        
        # Get all shipments
        shipments = [s for v in vehicles for s in v.shipments]
        logger.info(f"Total shipments: {len(shipments)}")
        
        # Create optimizer
        sa_params = SAParameters(
            initial_temperature=config.optimizer_params.initial_temperature,
            cooling_rate=config.optimizer_params.cooling_rate,
            termination_temperature=config.optimizer_params.termination_temperature,
            max_iterations=config.optimizer_params.max_iterations
        )
        
        optimizer = SimulatedAnnealingOptimizer(
            vehicles=vehicles,
            shipments=shipments,
            network=network,
            cost_calculator=cost_calculator,
            validator=validator,
            params=sa_params
        )
        
        # Run optimization
        logger.info("Starting optimization...")
        result = optimizer.optimize()
        
        # Print results
        print_results(result)
        
        # Save results
        output_data = {
            "solution": {
                vehicle.vehicle_id: {
                    "shipments": [s.shipment_id for s in shipments],
                    "route": result.metrics["vehicle_metrics"][vehicle.vehicle_id]["route"],
                    "metrics": result.metrics["vehicle_metrics"][vehicle.vehicle_id]
                }
                for vehicle, shipments in result.best_solution.items()
            },
            "overall_metrics": {
                "total_distance": result.metrics["total_distance"],
                "total_border_crossings": result.metrics["total_border_crossings"],
                "is_valid": result.validation.is_valid
            },
            "cost_comparisons": result.validation.cost_comparisons,
            "statistics": result.statistics
        }
        
        save_json(output_data, config.results_file)
        logger.info(f"Results saved to {config.results_file}")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Data error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
