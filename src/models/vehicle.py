"""Vehicle model representing trucks in the fleet."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.models.shipment import Shipment


@dataclass
class VehicleDimensions:
    """Vehicle cargo dimensions."""
    length: float  # meters
    width: float   # meters
    height: float  # meters
    
    @property
    def volume(self) -> float:
        """Calculate total volume in cubic meters."""
        return self.length * self.width * self.height
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VehicleDimensions":
        return cls(
            length=data["length"],
            width=data["width"],
            height=data["height"]
        )


@dataclass
class Vehicle:
    """
    Represents a vehicle in the fleet.
    
    Tracks capacity, current load, assigned shipments, and routes.
    """
    vehicle_id: str
    vehicle_type: str
    dimensions: VehicleDimensions
    max_weight: float  # kg
    fuel_capacity: float  # liters
    fuel_efficiency: float  # liters per km
    
    # State fields (mutable)
    current_load_weight: float = field(default=0.0, repr=False)
    current_load_cbm: float = field(default=0.0, repr=False)
    shipments: List[Shipment] = field(default_factory=list, repr=False)
    route: List[str] = field(default_factory=list, repr=False)
    costs: Dict = field(default_factory=dict, repr=False)
    
    # Tolerance for floating point comparisons
    CAPACITY_TOLERANCE: float = field(default=1.001, repr=False)
    
    @property
    def max_cbm(self) -> float:
        """Maximum cargo volume."""
        return self.dimensions.volume
    
    @property
    def remaining_weight(self) -> float:
        """Remaining weight capacity."""
        return self.max_weight - self.current_load_weight
    
    @property
    def remaining_cbm(self) -> float:
        """Remaining volume capacity."""
        return self.max_cbm - self.current_load_cbm
    
    def reset_state(self) -> None:
        """Reset vehicle to initial empty state."""
        self.current_load_weight = 0.0
        self.current_load_cbm = 0.0
        self.shipments = []
        self.route = []
        self.costs = {}
    
    def can_add_shipment(self, shipment: Shipment, verbose: bool = False) -> bool:
        """
        Check if shipment can be added considering both volume and weight.
        
        Args:
            shipment: The shipment to check
            verbose: If True, print capacity check details
        
        Returns:
            True if shipment fits, False otherwise
        """
        new_cbm = self.current_load_cbm + shipment.total_cbm
        new_weight = self.current_load_weight + shipment.weight
        
        volume_ok = new_cbm <= (self.max_cbm * self.CAPACITY_TOLERANCE)
        weight_ok = new_weight <= (self.max_weight * self.CAPACITY_TOLERANCE)
        
        if verbose:
            print(f"Capacity check for {self.vehicle_id}:")
            print(f"  Volume: {new_cbm:.2f}/{self.max_cbm:.2f} ({'OK' if volume_ok else 'EXCEED'})")
            print(f"  Weight: {new_weight:.2f}/{self.max_weight:.2f} ({'OK' if weight_ok else 'EXCEED'})")
        
        return volume_ok and weight_ok
    
    def add_shipment(self, shipment: Shipment) -> bool:
        """
        Add a shipment to the vehicle.
        
        Args:
            shipment: The shipment to add
        
        Returns:
            True if added successfully, False if capacity exceeded
        """
        if not self.can_add_shipment(shipment):
            return False
        
        self.shipments.append(shipment)
        self.current_load_weight += shipment.weight
        self.current_load_cbm += shipment.total_cbm
        return True
    
    def remove_shipment(self, shipment: Shipment) -> bool:
        """
        Remove a shipment from the vehicle.
        
        Args:
            shipment: The shipment to remove
        
        Returns:
            True if removed, False if not found
        """
        if shipment not in self.shipments:
            return False
        
        self.shipments.remove(shipment)
        self.current_load_weight -= shipment.weight
        self.current_load_cbm -= shipment.total_cbm
        return True
    
    def get_utilization(self) -> Tuple[float, float]:
        """
        Calculate capacity utilization percentages.
        
        Returns:
            Tuple of (weight_utilization, volume_utilization) as percentages
        """
        weight_util = (self.current_load_weight / self.max_weight * 100) if self.max_weight > 0 else 0
        volume_util = (self.current_load_cbm / self.max_cbm * 100) if self.max_cbm > 0 else 0
        return weight_util, volume_util
    
    def get_remaining_capacity(self) -> Dict[str, float]:
        """Get remaining capacity in both weight and volume."""
        return {
            "weight": self.remaining_weight,
            "cbm": self.remaining_cbm
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Vehicle":
        """Create a Vehicle from dictionary data."""
        return cls(
            vehicle_id=data["id"],
            vehicle_type=data["type"],
            dimensions=VehicleDimensions.from_dict(data["dimensions"]),
            max_weight=data["max_weight"],
            fuel_capacity=data["fuel_capacity"],
            fuel_efficiency=data["fuel_efficiency"]
        )
    
    def __hash__(self):
        return hash(self.vehicle_id)
    
    def __eq__(self, other):
        if not isinstance(other, Vehicle):
            return False
        return self.vehicle_id == other.vehicle_id
