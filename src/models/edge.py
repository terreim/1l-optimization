"""Edge model representing connections between nodes in the network."""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from src.fuzzy import TriangularFuzzyNumber


@dataclass
class TimeWindow:
    """A time window with associated delay factor."""
    start_time: str
    end_time: str
    delay_factor: float
    
    @classmethod
    def from_dict(cls, data: Dict) -> "TimeWindow":
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            delay_factor=data["delay_factor"]
        )


@dataclass
class Edge:
    """
    Represents a connection between two nodes in the transportation network.
    
    Edges are undirected - they represent bidirectional travel between nodes.
    """
    from_node: str
    to_node: str
    distance: float  # km
    base_time: float  # minutes
    road_type: str
    time_windows: List[TimeWindow] = field(default_factory=list)
    
    # Computed field
    _fuzzy_travel_time: TriangularFuzzyNumber = field(init=False, repr=False)
    
    def __post_init__(self):
        self._fuzzy_travel_time = self._calculate_fuzzy_travel_time()
    
    @property
    def nodes(self) -> Tuple[str, str]:
        """Return sorted tuple of node IDs for consistent comparison."""
        return tuple(sorted([self.from_node, self.to_node]))
    
    @property
    def edge_id(self) -> str:
        """Generate a consistent edge identifier."""
        return f"{self.nodes[0]}-{self.nodes[1]}"
    
    @property
    def fuzzy_travel_time(self) -> TriangularFuzzyNumber:
        """Get the fuzzy travel time for this edge."""
        return self._fuzzy_travel_time
    
    def _calculate_fuzzy_travel_time(self) -> TriangularFuzzyNumber:
        """
        Calculate fuzzy travel time based on time windows and delay factors.
        
        The fuzzy number represents uncertainty in travel time due to
        varying traffic conditions throughout the day.
        """
        if not self.time_windows:
            # No time windows - return crisp base time
            return TriangularFuzzyNumber(
                left=self.base_time,
                peak=self.base_time,
                right=self.base_time
            )
        
        # Calculate min, typical, and max times based on delay factors
        delay_factors = [tw.delay_factor for tw in self.time_windows]
        
        min_factor = min(delay_factors)
        max_factor = max(delay_factors)
        
        # Peak time is based on typical congestion factors (1.2-1.5)
        typical_factors = [f for f in delay_factors if 1.1 <= f <= 1.5]
        peak_factor = sum(typical_factors) / len(typical_factors) if typical_factors else 1.0
        
        return TriangularFuzzyNumber(
            left=self.base_time * min_factor,
            peak=self.base_time * peak_factor,
            right=self.base_time * max_factor
        )
    
    def connects(self, node1: str, node2: str) -> bool:
        """Check if this edge connects the given nodes (in either direction)."""
        return {node1, node2} == set(self.nodes)
    
    @classmethod
    def from_route_data(
        cls, 
        route_name: str, 
        route_info: Dict, 
        time_windows: List[Dict]
    ) -> "Edge":
        """Create an Edge from route data."""
        nodes = route_name.split("-")
        if len(nodes) != 2:
            raise ValueError(f"Invalid route name format: {route_name}")
        
        return cls(
            from_node=nodes[0],
            to_node=nodes[1],
            distance=route_info["distance"],
            base_time=route_info["base_time"],
            road_type=route_info["road_type"],
            time_windows=[TimeWindow.from_dict(tw) for tw in time_windows]
        )
