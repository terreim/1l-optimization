# 1L-CVRP Optimization

Capacitated Vehicle Routing Problem with 1-Dimensional Loading (1L-CVRP) optimization using Simulated Annealing with fuzzy cost calculations.
Experimental and subjected to possible changes in the future.

## Overview

This project solves the 1L-CVRP problem for a cross-border logistics network in Southeast Asia. It optimizes:

- **Vehicle assignment**: Which shipments go on which vehicle
- **Route planning**: The order of deliveries to minimize cost
- **Capacity utilization**: Maximizing vehicle load efficiency

The optimization uses **Simulated Annealing** with **Triangular Fuzzy Numbers** to handle uncertainty in travel times and costs.

## Project Structure

```
1l-cvrp-optimization/
├── main.py                 # Main entry point
├── src/
│   ├── config.py          # Configuration management
│   ├── fuzzy/             # Fuzzy number implementations
│   │   └── fuzzy_number.py
│   ├── models/            # Data models
│   │   ├── node.py        # Network nodes (depots, borders)
│   │   ├── edge.py        # Network edges (roads)
│   │   ├── shipment.py    # Cargo shipments
│   │   ├── vehicle.py     # Fleet vehicles
│   │   ├── route_leg.py   # Route segments
│   │   ├── network.py     # Graph wrapper
│   │   └── cost.py        # Cost calculations
│   ├── optimization/      # Optimization algorithms
│   │   ├── optimizer.py   # Main SA optimizer
│   │   ├── initial_solution.py
│   │   ├── neighborhood.py # Move operators
│   │   └── route_optimizer.py
│   ├── utils/             # Utilities
│   │   ├── data_loader.py # JSON parsing
│   │   └── validators.py  # Solution validation
│   └── reporters/         # Output formatting
│       └── console_reporter.py
└── data/                  # Input data (not included)
    ├── constants/
    │   ├── nodes.json
    │   ├── vehicles.json
    │   └── edges.json
    └── historical_data/
        ├── packing_plan/
        └── cost_breakdown/
```

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd 1l-cvrp-optimization

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install networkx
```

## Usage

### Basic Usage

```bash
python main.py
```

### With Options

```bash
python main.py \
    --packing-plan packing_plan3.json \
    --historical-costs cost_breakdown3.json \
    --results-file results.json \
    --max-iterations 2000 \
    --verbose
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--packing-plan` | Packing plan JSON file | `packing_plan3.json` |
| `--historical-costs` | Historical costs JSON file | `cost_breakdown3.json` |
| `--results-file` | Output results file | `optimization_results.json` |
| `--max-iterations` | Maximum SA iterations | `1000` |
| `--verbose` | Enable debug logging | `False` |

## Algorithm

### Simulated Annealing

The optimizer uses Simulated Annealing with:

- **Initial Solution**: First-Fit Decreasing with destination grouping
- **Neighborhood Operations**:
  - Swap shipments between vehicles
  - Transfer shipments to different vehicles
  - Relocate shipments within a vehicle
  - Reverse subroutes
- **Route Optimization**: Nearest Neighbor + 2-opt improvement
- **Acceptance Criterion**: Metropolis with fuzzy cost comparison

### Fuzzy Cost Calculation

Costs are represented as Triangular Fuzzy Numbers (TFN) to capture uncertainty:

- Travel time varies with traffic conditions
- Customs processing has variable delays
- Driver costs depend on experience level

The fuzzy cost is defuzzified using the centroid method for acceptance decisions.

## Input Data Format

### nodes.json

```json
{
  "locations": {
    "depots": [
      {
        "id": "NNG",
        "name": "Nanning",
        "country": "China",
        "operating_hours": {"start": "06:00", "end": "22:00"}
      }
    ],
    "border_crossings": [...]
  }
}
```

### vehicles.json

```json
{
  "fleet": [
    {
      "id": "VH001",
      "type": "standard_truck",
      "dimensions": {"length": 12.192, "width": 2.438, "height": 2.591},
      "max_weight": 24000,
      "fuel_capacity": 400,
      "fuel_efficiency": 0.3
    }
  ]
}
```

### packing_plan.json

```json
{
  "vehicles": [
    {
      "id": "VH001",
      "shipments": [
        {
          "id": "SHP001",
          "order_id": "ORD001",
          "total_cbm": 5.5,
          "weight": 1200,
          "origin": "Nanning",
          "delivery": {"location_id": "BKK"},
          "price": 15000
        }
      ]
    }
  ]
}
```

## Output

The optimizer produces:

1. **Console output**: Summary of optimization results
2. **JSON file**: Detailed results including:
   - Best solution (vehicle assignments and routes)
   - Cost comparisons with historical data
   - Optimization statistics
   - Vehicle utilization metrics

## Key Features

- **Fuzzy optimization**: Handles uncertainty in real-world logistics
- **Multi-country routing**: Considers border crossings and customs
- **Capacity constraints**: Both weight and volume limits
- **Route efficiency**: Minimizes backtracking and redundant travel
- **Historical comparison**: Validates improvements against past performance

## License

MIT License

## Author

For thesis research on vehicle routing optimization in cross-border logistics.
