"""Node model representing locations in the transportation network."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class OperatingHours:
    """Operating hours for a location."""
    start: str  # Format: "HH:MM"
    end: str    # Format: "HH:MM"
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "OperatingHours":
        return cls(start=data["start"], end=data["end"])
    
    def to_dict(self) -> Dict[str, str]:
        return {"start": self.start, "end": self.end}


@dataclass
class Node:
    """
    Represents a location in the transportation network.
    
    Nodes can be depots, border crossings, or delivery points.
    """
    node_id: str
    name: str
    country: str
    node_type: str  # 'depot', 'border_crossing', 'delivery'
    operating_hours: OperatingHours
    
    @classmethod
    def from_dict(cls, data: Dict, node_type: str = "depot") -> "Node":
        """Create a Node from dictionary data."""
        # Handle border crossings which have 'countries' list
        country = data.get("country")
        if country is None and "countries" in data:
            country = data["countries"][0]
        
        return cls(
            node_id=data["id"],
            name=data["name"],
            country=country,
            node_type=node_type,
            operating_hours=OperatingHours.from_dict(data["operating_hours"])
        )
    
    def __hash__(self):
        return hash(self.node_id)
    
    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.node_id == other.node_id
