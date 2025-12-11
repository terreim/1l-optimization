"""Cost calculation model for route and solution costing."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.fuzzy import TriangularFuzzyNumber
from src.models.network import Network
from src.models.vehicle import Vehicle
from src.models.shipment import Shipment


@dataclass
class CostParameters:
    """Parameters for cost calculations."""
    fuel_price_per_liter: float = 0.8
    per_diem_rate: float = 18.0  # Calibrated: historical shows $16-20/day
    max_driving_hours_per_day: float = 10.0
    average_speed: float = 60.0  # km/h
    fuel_tank_capacity: float = 400.0  # liters
    refuel_time: float = 0.5  # hours
    rest_time_per_day: float = 10.0  # hours
    border_crossing_time: float = 4.0  # hours
    
    # Tax rates by country (calibrated: 10% matches historical)
    tax_rates: Dict[str, float] = field(default_factory=lambda: {
        "China": 0.10,
        "Vietnam": 0.10,
        "Laos": 0.10,
        "Cambodia": 0.10,
        "Thailand": 0.07,
        "Myanmar": 0.12,
        "Malaysia": 0.10,
        "Singapore": 0.08
    })
    
    # Customs fees by country pairs
    customs_fees: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        ("China", "Vietnam"): 160,
        ("China", "Laos"): 162,
        ("Vietnam", "Laos"): 162,
        ("Vietnam", "Cambodia"): 160,
        ("Laos", "Cambodia"): 160,
        ("Laos", "Thailand"): 161,
        ("Laos", "Myanmar"): 160,
        ("Cambodia", "Thailand"): 160,
        ("Myanmar", "Thailand"): 160,
        ("Thailand", "Malaysia"): 158,
        ("Malaysia", "Singapore"): 158
    })
    
    # Refueling costs by country
    refuel_costs: Dict[str, float] = field(default_factory=lambda: {
        "China": 5,
        "Vietnam": 4,
        "Laos": 4,
        "Cambodia": 4,
        "Thailand": 3,
        "Myanmar": 4,
        "Malaysia": 3,
        "Singapore": 6
    })


class CostCalculator:
    """
    Calculator for route and solution costs.
    
    Handles fuel costs, customs fees, taxes, driver costs, and penalties.
    """
    
    def __init__(self, params: Optional[CostParameters] = None):
        self.params = params or CostParameters()
    
    def calculate_fuel_cost(self, distance: float, fuel_efficiency: float) -> float:
        """Calculate fuel cost for a given distance."""
        return distance * fuel_efficiency * self.params.fuel_price_per_liter
    
    def get_tax_rate(self, country: str) -> float:
        """Get tax rate for a country."""
        return self.params.tax_rates.get(country, 0.10)
    
    def calculate_tax(self, goods_value: float, country: str) -> float:
        """Calculate tax based on goods value and destination country."""
        return goods_value * self.get_tax_rate(country)
    
    def get_customs_fee(self, from_country: str, to_country: str) -> float:
        """Get base customs fee for crossing between two countries."""
        # Sort to ensure consistent lookup
        countries = tuple(sorted([from_country, to_country]))
        return self.params.customs_fees.get(countries, 160.0)
    
    def get_driver_salary(self, distance: float, days: int = 1) -> TriangularFuzzyNumber:
        """
        Calculate fuzzy driver salary based on route distance and days.
        
        Calibrated against historical data:
        - V001 (504 km, 1 day): $26.50
        - V002 (2959 km, 4 days): $118 = $29.50/day
        - V003 (2779 km, 4 days): $122 = $30.50/day  
        - V004 (3796 km, 5 days): $162.50 = $32.50/day
        
        Pattern: base ~$26-28/day for short trips, ~$30-33/day for long trips
        """
        # Base daily rate with fuzzy uncertainty
        if distance <= 500:  # Short haul (1 day)
            daily_rate = TriangularFuzzyNumber(24.0, 26.5, 29.0)
        elif distance <= 1500:  # Medium haul (2-3 days)
            daily_rate = TriangularFuzzyNumber(27.0, 29.5, 32.0)
        elif distance <= 3000:  # Long haul (3-4 days)
            daily_rate = TriangularFuzzyNumber(29.0, 31.0, 33.0)
        else:  # Very long haul (5+ days)
            daily_rate = TriangularFuzzyNumber(31.0, 32.5, 34.0)
        
        # Multiply by days
        return TriangularFuzzyNumber(
            daily_rate.left * days,
            daily_rate.peak * days,
            daily_rate.right * days
        )
    
    def calculate_travel_info(
        self, 
        distance: float, 
        is_border_crossing: bool
    ) -> Dict:
        """
        Calculate travel time including breaks and border crossings.
        
        Returns dictionary with days, hours, and refuel stops.
        """
        if distance == float("inf"):
            return {"days": float("inf"), "hours": float("inf"), "refuel_stops": 0}
        
        # Calculate pure driving time
        driving_hours = distance / self.params.average_speed
        
        # Add border crossing time
        if is_border_crossing:
            driving_hours += self.params.border_crossing_time
        
        # Calculate refuel stops
        fuel_range = self.params.fuel_tank_capacity / 0.3  # km per tank
        refuel_stops = max(0, int(distance / fuel_range))
        refuel_time = refuel_stops * self.params.refuel_time
        
        total_hours = driving_hours + refuel_time
        
        # Calculate days needed
        days = max(1, round(total_hours / self.params.max_driving_hours_per_day))
        
        return {
            "days": days,
            "hours": total_hours,
            "refuel_stops": refuel_stops
        }
    
    def calculate_leg_cost(
        self,
        distance: float,
        fuel_efficiency: float,
        goods_value: float,
        from_country: str,
        to_country: str,
        is_border_crossing: bool,
        is_first_day: bool
    ) -> Dict:
        """
        Calculate all costs for a route leg.
        
        Returns dictionary with cost breakdown.
        """
        if distance == float("inf"):
            return {"total_cost": float("inf"), "details": "Invalid route"}
        
        travel_info = self.calculate_travel_info(distance, is_border_crossing)
        
        # Base costs
        costs = {
            "per_diem": self.params.per_diem_rate,
            "driver_salary": self.get_driver_salary(distance).defuzzify(),
            "fuel_cost": self.calculate_fuel_cost(distance, fuel_efficiency),
            "custom_fee": self.get_customs_fee(from_country, to_country) if is_border_crossing else 0.0,
            "tax_on_goods": self.calculate_tax(goods_value, to_country),
            "overhead": 100.0 if is_first_day else 50.0,
            "emergency": 200.0 if is_first_day else 100.0,
            "refuel_service": self.params.refuel_costs.get(from_country, 4) * travel_info["refuel_stops"]
        }
        
        costs["total_cost"] = sum(costs.values())
        costs["travel_days"] = travel_info["days"]
        costs["refuel_stops"] = travel_info["refuel_stops"]
        
        return costs
    
    def calculate_route_cost(
        self,
        route: List[str],
        network: Network,
        vehicle: Optional[Vehicle] = None,
        shipments: Optional[List[Shipment]] = None
    ) -> TriangularFuzzyNumber:
        """
        Calculate total cost for a route using fuzzy numbers.
        
        Cost structure (calibrated against historical data):
        - PER TRIP (once): per_diem, driver_salary, overhead, emergency
        - PER LEG: fuel_cost, refuel_service
        - PER BORDER CROSSING: custom_fee
        - PER DELIVERY: tax_on_goods (at each destination)
        
        Args:
            route: List of node codes representing the route
            network: The transportation network
            vehicle: Optional vehicle for fuel efficiency
            shipments: Optional shipments for goods value calculation
        
        Returns:
            Total fuzzy cost for the route
        """
        if not route or len(route) < 2:
            return TriangularFuzzyNumber.infinity()
        
        fuel_efficiency = vehicle.fuel_efficiency if vehicle else 0.3
        
        # Calculate goods value at each stop
        stop_values = {}
        if shipments:
            for s in shipments:
                dest = s.delivery_location_id
                stop_values[dest] = stop_values.get(dest, 0) + s.price
        
        # Accumulate costs
        total_distance = 0.0
        total_fuel_cost = 0.0
        total_customs_fee = 0.0
        total_tax = 0.0
        total_refuel_stops = 0
        border_crossings = 0
        
        for i in range(len(route) - 1):
            from_node = route[i]
            to_node = route[i + 1]
            
            # Get distance
            distance = network.shortest_path_length(from_node, to_node)
            if distance == float("inf"):
                return TriangularFuzzyNumber.infinity()
            
            total_distance += distance
            
            # Fuel cost (per leg)
            total_fuel_cost += self.calculate_fuel_cost(distance, fuel_efficiency)
            
            # Refuel stops
            fuel_range = self.params.fuel_tank_capacity / fuel_efficiency
            refuel_stops = max(0, int(distance / fuel_range))
            total_refuel_stops += refuel_stops
            
            # Get countries
            from_country = network.get_country(from_node) or "Unknown"
            to_country = network.get_country(to_node) or "Unknown"
            is_border_crossing = from_country != to_country
            
            # Customs fee (per border crossing)
            if is_border_crossing:
                border_crossings += 1
                total_customs_fee += self.get_customs_fee(from_country, to_country)
            
            # Tax on goods at destination (per delivery)
            goods_value = stop_values.get(to_node, 0)
            if goods_value > 0:
                total_tax += self.calculate_tax(goods_value, to_country)
        
        # Calculate trip duration for per-day costs
        driving_hours = total_distance / self.params.average_speed
        driving_hours += border_crossings * self.params.border_crossing_time
        trip_days = max(1, int((driving_hours + self.params.rest_time_per_day - 1) / 
                               (self.params.max_driving_hours_per_day + self.params.rest_time_per_day)) + 1)
        
        # Per-trip costs (charged ONCE, not per leg)
        per_diem = self.params.per_diem_rate * trip_days
        driver_salary = self.get_driver_salary(total_distance, trip_days)
        overhead = 100.0  # Fixed per trip
        emergency = 200.0  # Fixed per trip
        
        # Refuel service cost
        # Get the primary country for refuel cost (use origin country)
        origin_country = network.get_country(route[0]) or "China"
        refuel_service = self.params.refuel_costs.get(origin_country, 4) * total_refuel_stops
        
        # Build total cost
        base_cost = (
            per_diem +
            driver_salary.defuzzify() +
            total_fuel_cost +
            total_customs_fee +
            total_tax +
            overhead +
            emergency +
            refuel_service
        )
        
        # Convert to fuzzy number with 5% uncertainty
        return TriangularFuzzyNumber(
            base_cost * 0.95,
            base_cost,
            base_cost * 1.05
        )
    
    def calculate_solution_cost(
        self,
        solution: Dict[Vehicle, List[Shipment]],
        network: Network
    ) -> TriangularFuzzyNumber:
        """
        Calculate total cost for a complete solution.
        
        Args:
            solution: Dictionary mapping vehicles to their shipments
            network: The transportation network
        
        Returns:
            Total fuzzy cost for the solution
        """
        total_cost = TriangularFuzzyNumber.zero()
        
        for vehicle, shipments in solution.items():
            if not shipments:
                continue
            
            # Build route from shipments
            route = [network.origin_code]
            for s in shipments:
                if s.delivery_location_id not in route:
                    route.append(s.delivery_location_id)
            
            route_cost = self.calculate_route_cost(route, network, vehicle, shipments)
            total_cost = total_cost + route_cost
        
        return total_cost
