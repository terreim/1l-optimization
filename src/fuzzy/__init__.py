"""Fuzzy logic module for handling uncertainty in optimization."""

from .fuzzy_number import (
    TriangularFuzzyNumber,
    fuzzy_dominance,
    possibility_degree,
)

__all__ = [
    "TriangularFuzzyNumber",
    "fuzzy_dominance",
    "possibility_degree",
]
