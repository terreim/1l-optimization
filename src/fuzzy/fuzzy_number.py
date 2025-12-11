"""Fuzzy number implementations for uncertainty modeling."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class TriangularFuzzyNumber:
    """
    Triangular Fuzzy Number representation.
    
    A triangular fuzzy number is defined by three values:
    - left: The lower bound (minimum possible value)
    - peak: The most likely value (mode)
    - right: The upper bound (maximum possible value)
    
    The membership function is triangular, with membership 1.0 at the peak
    and 0.0 at the left and right bounds.
    """
    left: float
    peak: float
    right: float
    
    def __post_init__(self):
        # Allow equal values for crisp numbers
        if not (self.left <= self.peak <= self.right):
            # Only raise if clearly invalid
            if self.left > self.right:
                raise ValueError(
                    f"Invalid fuzzy number: left ({self.left}) > right ({self.right})"
                )
    
    def __add__(self, other: TriangularFuzzyNumber) -> TriangularFuzzyNumber:
        """Add two triangular fuzzy numbers."""
        if not isinstance(other, TriangularFuzzyNumber):
            return NotImplemented
        return TriangularFuzzyNumber(
            left=self.left + other.left,
            peak=self.peak + other.peak,
            right=self.right + other.right
        )
    
    def __sub__(self, other: TriangularFuzzyNumber) -> TriangularFuzzyNumber:
        """Subtract two triangular fuzzy numbers."""
        if not isinstance(other, TriangularFuzzyNumber):
            return NotImplemented
        return TriangularFuzzyNumber(
            left=self.left - other.right,
            peak=self.peak - other.peak,
            right=self.right - other.left
        )
    
    def __mul__(self, scalar: float) -> TriangularFuzzyNumber:
        """Multiply fuzzy number by a scalar."""
        if scalar >= 0:
            return TriangularFuzzyNumber(
                left=self.left * scalar,
                peak=self.peak * scalar,
                right=self.right * scalar
            )
        else:
            return TriangularFuzzyNumber(
                left=self.right * scalar,
                peak=self.peak * scalar,
                right=self.left * scalar
            )
    
    def __rmul__(self, scalar: float) -> TriangularFuzzyNumber:
        """Right multiplication by scalar."""
        return self.__mul__(scalar)
    
    def defuzzify(self, method: str = "centroid") -> float:
        """
        Convert fuzzy number to crisp value.
        
        Args:
            method: Defuzzification method. Options:
                - "centroid": Center of gravity (default)
                - "bisector": Bisector of area
                - "mom": Mean of maximum
                - "som": Smallest of maximum
                - "lom": Largest of maximum
        
        Returns:
            Crisp (defuzzified) value.
        """
        if method == "centroid":
            return (self.left + self.peak + self.right) / 3
        elif method == "bisector":
            # For triangular, bisector is close to centroid
            return (self.left + 2 * self.peak + self.right) / 4
        elif method == "mom":
            return self.peak
        elif method == "som":
            return self.peak  # For triangular, max is at peak
        elif method == "lom":
            return self.peak
        else:
            raise ValueError(f"Unknown defuzzification method: {method}")
    
    @classmethod
    def from_crisp(cls, value: float, spread: float = 0.05) -> TriangularFuzzyNumber:
        """
        Create a fuzzy number from a crisp value with given spread.
        
        Args:
            value: The crisp value (becomes the peak)
            spread: Relative spread around the value (default 5%)
        
        Returns:
            TriangularFuzzyNumber with the given spread.
        """
        delta = abs(value * spread)
        return cls(
            left=value - delta,
            peak=value,
            right=value + delta
        )
    
    @classmethod
    def zero(cls) -> TriangularFuzzyNumber:
        """Return a zero fuzzy number."""
        return cls(0.0, 0.0, 0.0)
    
    @classmethod
    def infinity(cls) -> TriangularFuzzyNumber:
        """Return an infinite fuzzy number."""
        return cls(float('inf'), float('inf'), float('inf'))
    
    def is_better_than(self, other: TriangularFuzzyNumber) -> bool:
        """Check if this fuzzy number is clearly better (lower) than other."""
        return self.right < other.left
    
    def overlap_degree(self, other: TriangularFuzzyNumber) -> float:
        """Calculate the degree of overlap with another fuzzy number."""
        if self.right < other.left or other.right < self.left:
            return 0.0  # No overlap
        
        overlap_start = max(self.left, other.left)
        overlap_end = min(self.right, other.right)
        overlap = max(0, overlap_end - overlap_start)
        
        total_range = max(self.right, other.right) - min(self.left, other.left)
        if total_range == 0:
            return 1.0
        
        return overlap / total_range


def fuzzy_dominance(cost1: TriangularFuzzyNumber, cost2: TriangularFuzzyNumber) -> float:
    """
    Calculate the degree to which cost1 dominates (is less than) cost2.
    
    Returns a value between 0 and 1:
    - 1.0 means cost1 completely dominates cost2 (cost1 is clearly better)
    - 0.0 means cost2 completely dominates cost1 (cost2 is clearly better)
    - 0.5 means neither dominates (similar costs)
    """
    # Handle edge cases
    if cost1.peak == 0 and cost2.peak == 0:
        return 0.5
    if cost1.peak == 0:
        return 1.0  # cost1 (zero) dominates
    if cost2.peak == 0:
        return 0.0  # cost2 (zero) dominates
    
    # Use overlap to determine dominance
    overlap = cost1.overlap_degree(cost2)
    return 1.0 - overlap


def possibility_degree(a: TriangularFuzzyNumber, b: TriangularFuzzyNumber) -> float:
    """
    Calculate the possibility degree that fuzzy number a is less than or equal to b.
    
    Returns a value between 0 and 1.
    """
    # If a is completely less than b
    if a.right <= b.left:
        return 1.0
    
    # If b is completely less than a
    if b.right <= a.left:
        return 0.0
    
    # Calculate based on overlap
    if a.peak <= b.peak:
        numerator = b.right - a.left
        denominator = (a.right - a.left) + (b.right - b.left)
        if denominator == 0:
            return 0.5
        return max(0.0, min(1.0, numerator / denominator))
    else:
        numerator = b.right - a.left
        denominator = (a.right - a.left) + (b.right - b.left)
        if denominator == 0:
            return 0.5
        return max(0.0, min(1.0, numerator / denominator))
