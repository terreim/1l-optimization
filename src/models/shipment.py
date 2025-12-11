"""Shipment model representing goods to be transported."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Shipment:
    """
    Represents a shipment to be delivered.
    
    In the 1D packing context, total_cbm is used as the primary
    dimension for bin packing calculations.
    """
    shipment_id: str
    order_id: str
    total_cbm: float  # Cubic meters (used as length in 1D packing)
    weight: float     # kg
    origin: str       # Origin location ID
    delivery_location_id: str  # Destination location ID
    price: float      # Value of the shipment
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Shipment":
        """Create a Shipment from dictionary data."""
        return cls(
            shipment_id=data["id"],
            order_id=data["order_id"],
            total_cbm=data["total_cbm"],
            weight=data["weight"],
            origin=data["origin"],
            delivery_location_id=data["delivery"]["location_id"],
            price=data["price"]
        )
    
    def __hash__(self):
        return hash(self.shipment_id)
    
    def __eq__(self, other):
        if not isinstance(other, Shipment):
            return False
        return self.shipment_id == other.shipment_id
