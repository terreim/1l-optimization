"""Configuration module for the 1L-CVRP optimization model."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("cvrp")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


@dataclass
class OptimizerParams:
    """Parameters for the Simulated Annealing optimizer."""
    initial_temperature: float = 2000.0
    cooling_rate: float = 0.995
    termination_temperature: float = 0.1
    max_iterations: int = 1000


@dataclass
class Config:
    """Configuration class for the optimization model."""
    
    # File paths
    packing_plan_file: str
    historical_costs_file: str
    results_file: str = "optimization_results.json"
    
    # Optimizer parameters
    optimizer_params: OptimizerParams = field(default_factory=OptimizerParams)
    
    # Logging
    log_level: int = logging.INFO
    
    # Base directories (computed)
    _base_dir: Path = field(init=False)
    _data_dir: Path = field(init=False)
    
    def __post_init__(self):
        self._base_dir = Path(__file__).parent.parent
        self._data_dir = self._base_dir / "data"
        
        # Resolve relative paths
        if not Path(self.packing_plan_file).is_absolute():
            self.packing_plan_file = str(
                self._data_dir / "historical_data" / "packing_plan" / self.packing_plan_file
            )
        
        if not Path(self.historical_costs_file).is_absolute():
            self.historical_costs_file = str(
                self._data_dir / "historical_data" / "cost_breakdown" / self.historical_costs_file
            )
    
    @property
    def nodes_file(self) -> Path:
        return self._data_dir / "constants" / "nodes.json"
    
    @property
    def vehicles_file(self) -> Path:
        return self._data_dir / "constants" / "vehicles.json"
    
    @property
    def edges_file(self) -> Path:
        return self._data_dir / "constants" / "edges.json"


# Default configuration
def get_default_config() -> Config:
    """Return default configuration."""
    return Config(
        packing_plan_file="packing_plan3.json",
        historical_costs_file="cost_breakdown3.json"
    )
