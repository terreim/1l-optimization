"""Route leg model representing a segment of a vehicle's journey."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional


@dataclass
class DrivingRules:
    """Regulations and constraints for driving."""
    max_driving_time: float = 8.5  # Maximum continuous driving hours
    rest_time: int = 45  # Minutes of rest required after max driving
    max_daily_driving: float = 10.0  # Maximum daily driving hours
    daily_rest: int = 11  # Daily rest hours required
    border_crossing_time: int = 240  # Minutes for border crossing
    loading_time: int = 60  # Minutes for loading/unloading
    avg_speed_city: float = 40.0  # km/h in city
    avg_speed_highway: float = 70.0  # km/h on highway
    night_driving_allowed: bool = False
    working_hours_start: str = "06:00"
    working_hours_end: str = "20:00"


DEFAULT_RULES = DrivingRules()


@dataclass
class RouteLeg:
    """
    Represents a segment of a vehicle's route.
    
    A route leg is the journey between two consecutive stops,
    including travel time, rest time, and any border crossings.
    """
    destination: str
    distance_travelled: float  # km
    time_travelled: int  # minutes
    time_rested: int  # minutes
    refuel_count: int
    arrival: Optional[datetime] = None
    time_stayed: int = 0  # minutes
    departure: Optional[datetime] = None
    is_border_crossing: bool = False
    from_country: Optional[str] = None
    to_country: Optional[str] = None
    
    @staticmethod
    def calculate_refuel_stops(
        distance: float,
        fuel_efficiency: float = 0.3,  # L/km
        tank_capacity: float = 500.0   # L
    ) -> Dict:
        """
        Calculate number of refuel stops needed.
        
        Args:
            distance: Distance in kilometers
            fuel_efficiency: Fuel consumption in L/km
            tank_capacity: Fuel tank capacity in liters
        
        Returns:
            Dictionary with refueling information
        """
        range_per_tank = tank_capacity / fuel_efficiency
        total_fuel_needed = distance * fuel_efficiency
        
        if distance <= range_per_tank:
            refuel_stops = 0
        else:
            refuel_stops = int((distance - range_per_tank) / range_per_tank) + 1
        
        return {
            "stops": refuel_stops,
            "total_fuel_needed": total_fuel_needed,
            "fuel_per_stop": tank_capacity if refuel_stops > 0 else total_fuel_needed
        }
    
    @staticmethod
    def calculate_travel_time(
        distance: float,
        is_border_crossing: bool = False,
        highway_ratio: float = 0.8,
        rules: Optional[DrivingRules] = None
    ) -> Dict:
        """
        Calculate travel time including mandatory rest periods and refueling.
        
        Args:
            distance: Distance in kilometers
            is_border_crossing: Whether route includes border crossing
            highway_ratio: Ratio of distance on highways (0-1)
            rules: Driving rules to apply
        
        Returns:
            Dictionary with detailed travel time breakdown
        """
        rules = rules or DEFAULT_RULES
        
        # Calculate base travel time by road type
        highway_distance = distance * highway_ratio
        city_distance = distance * (1 - highway_ratio)
        
        highway_time = highway_distance / rules.avg_speed_highway
        city_time = city_distance / rules.avg_speed_city
        base_travel_hours = highway_time + city_time
        
        # Calculate working days needed
        working_hours_per_day = min(
            rules.max_daily_driving,
            14.0  # Assume 14 working hours max from 06:00 to 20:00
        ) - 1  # Account for breaks
        
        days_needed = max(1, int(base_travel_hours / working_hours_per_day + 0.5))
        
        # Calculate rest periods
        rest_periods = int(base_travel_hours / rules.max_driving_time)
        rest_time_minutes = rest_periods * rules.rest_time
        
        # Add daily rest for multi-day trips
        if days_needed > 1:
            rest_time_minutes += (days_needed - 1) * rules.daily_rest * 60
        
        # Border crossing time
        border_time = rules.border_crossing_time if is_border_crossing else 0
        
        # Refueling
        refuel_info = RouteLeg.calculate_refuel_stops(distance)
        refuel_time = refuel_info["stops"] * 30  # 30 minutes per stop
        
        return {
            "total_travel_time": int(base_travel_hours * 60),  # minutes
            "total_rest_time": rest_time_minutes,
            "working_days": days_needed,
            "border_time": border_time,
            "refuel_time": refuel_time,
            "breakdown": {
                "highway_time": highway_time * 60,
                "city_time": city_time * 60,
                "rest_periods": rest_periods,
                "refuel_stops": refuel_info["stops"]
            }
        }
    
    def calculate_arrival_time(
        self, 
        start_time: datetime,
        rules: Optional[DrivingRules] = None
    ) -> Optional[datetime]:
        """
        Calculate expected arrival time based on travel and rest times.
        
        Args:
            start_time: Departure time
            rules: Driving rules to apply
        
        Returns:
            Expected arrival datetime
        """
        if not start_time:
            return None
        
        travel_info = self.calculate_travel_time(
            self.distance_travelled,
            self.is_border_crossing,
            rules=rules
        )
        
        total_minutes = (
            travel_info["total_travel_time"] +
            travel_info["total_rest_time"] +
            travel_info["border_time"] +
            travel_info["refuel_time"]
        )
        
        return start_time + timedelta(minutes=total_minutes)
    
    @staticmethod
    def parse_time(time_str: str) -> datetime:
        """Parse time string in 'YYYY/M/D - HH:MM' format."""
        return datetime.strptime(time_str, "%Y/%m/%d - %H:%M")
