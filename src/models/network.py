"""Network model for transportation graph operations."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import networkx as nx

from src.models.node import Node
from src.models.edge import Edge
from src.fuzzy import TriangularFuzzyNumber


@dataclass
class DistanceMatrix:
    """
    Pre-computed distance matrix for fast lookups.
    
    Computing shortest paths is expensive (O(E log V) per call).
    For repeated queries, pre-computing all pairs is much faster.
    """
    distances: Dict[Tuple[str, str], float] = field(default_factory=dict)
    
    def get(self, source: str, target: str) -> float:
        """Get cached distance, or infinity if not found."""
        if source == target:
            return 0.0
        return self.distances.get((source, target), float("inf"))
    
    def set(self, source: str, target: str, distance: float) -> None:
        """Set distance in both directions (undirected graph)."""
        self.distances[(source, target)] = distance
        self.distances[(target, source)] = distance
    
    @classmethod
    def from_graph(cls, graph: nx.Graph, weight: str = "distance") -> "DistanceMatrix":
        """
        Build distance matrix from a NetworkX graph.
        
        Uses Floyd-Warshall / all-pairs shortest path for efficiency.
        """
        matrix = cls()
        
        # Get all-pairs shortest paths at once - much faster than individual calls
        try:
            all_pairs = dict(nx.all_pairs_dijkstra_path_length(graph, weight=weight))
            
            for source, targets in all_pairs.items():
                for target, distance in targets.items():
                    matrix.set(source, target, distance)
        except nx.NetworkXError:
            # Fallback for disconnected graphs
            for source in graph.nodes():
                for target in graph.nodes():
                    if source != target:
                        try:
                            dist = nx.shortest_path_length(graph, source, target, weight=weight)
                            matrix.set(source, target, dist)
                        except nx.NetworkXNoPath:
                            pass
        
        return matrix


@dataclass
class Network:
    """
    Transportation network graph wrapper.
    
    Provides a clean interface for graph operations with consistent
    node naming (converting between codes and full names).
    Includes distance caching for performance.
    """
    graph: nx.Graph = field(default_factory=nx.Graph)
    code_to_name: Dict[str, str] = field(default_factory=dict)
    name_to_code: Dict[str, str] = field(default_factory=dict)
    origin_code: str = "NNG"  # Default origin (Nanning)
    origin_name: str = "Nanning"
    _distance_cache: Dict[Tuple[str, str], float] = field(default_factory=dict, repr=False)
    _path_cache: Dict[Tuple[str, str], List[str]] = field(default_factory=dict, repr=False)
    
    def add_node(self, node: Node) -> None:
        """Add a node to the network."""
        self.graph.add_node(
            node.node_id,
            name=node.name,
            country=node.country,
            type=node.node_type,
            operating_hours=node.operating_hours.to_dict()
        )
        self.code_to_name[node.node_id] = node.name
        self.name_to_code[node.name] = node.node_id
    
    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the network."""
        # Ensure both nodes exist
        node1, node2 = edge.nodes
        if node1 not in self.graph or node2 not in self.graph:
            return
        
        self.graph.add_edge(
            node1,
            node2,
            edge_id=edge.edge_id,
            distance=edge.distance,
            base_time=edge.base_time,
            road_type=edge.road_type,
            fuzzy_travel_time=edge.fuzzy_travel_time,
            time_windows=[tw.__dict__ for tw in edge.time_windows]
        )
    
    def get_node_name(self, code: str) -> str:
        """Convert node code to full name."""
        return self.code_to_name.get(code, code)
    
    def get_node_code(self, name: str) -> str:
        """Convert full name to node code."""
        return self.name_to_code.get(name, name)
    
    def get_country(self, node_id: str) -> Optional[str]:
        """Get the country for a node."""
        if node_id in self.graph:
            return self.graph.nodes[node_id].get("country")
        return None
    
    def shortest_path(
        self, 
        source: str, 
        target: str, 
        weight: str = "distance"
    ) -> Optional[List[str]]:
        """
        Find shortest path between two nodes.
        
        Args:
            source: Source node (code or name)
            target: Target node (code or name)
            weight: Edge weight to minimize
        
        Returns:
            List of node codes representing the path, or None if no path exists
        """
        # Normalize to codes
        source_code = self.name_to_code.get(source, source)
        target_code = self.name_to_code.get(target, target)
        
        try:
            return nx.shortest_path(self.graph, source_code, target_code, weight=weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def shortest_path_length(
        self, 
        source: str, 
        target: str, 
        weight: str = "distance"
    ) -> float:
        """
        Find shortest path length between two nodes (cached).
        
        Args:
            source: Source node (code or name)
            target: Target node (code or name)
            weight: Edge weight to minimize
        
        Returns:
            Path length, or infinity if no path exists
        """
        # Normalize to codes
        source_code = self.name_to_code.get(source, source)
        target_code = self.name_to_code.get(target, target)
        
        # Check cache
        cache_key = (source_code, target_code, weight)
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]
        
        try:
            length = nx.shortest_path_length(self.graph, source_code, target_code, weight=weight)
            self._distance_cache[cache_key] = length
            # Also cache reverse direction (undirected graph)
            self._distance_cache[(target_code, source_code, weight)] = length
            return length
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self._distance_cache[cache_key] = float("inf")
            return float("inf")
    
    def get_fuzzy_path_time(self, path: List[str]) -> Optional[TriangularFuzzyNumber]:
        """
        Calculate total fuzzy travel time for a path.
        
        Args:
            path: List of node codes representing the path
        
        Returns:
            Total fuzzy travel time, or None if path is invalid
        """
        if not path or len(path) < 2:
            return None
        
        total_time = TriangularFuzzyNumber.zero()
        
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i + 1])
            if edge_data and "fuzzy_travel_time" in edge_data:
                total_time = total_time + edge_data["fuzzy_travel_time"]
            else:
                return None
        
        return total_time
    
    def find_nearest_neighbors(
        self, 
        node_id: str, 
        n: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find the n nearest neighbors to a node based on distance.
        
        Args:
            node_id: The node to find neighbors for
            n: Number of neighbors to find
        
        Returns:
            List of (neighbor_id, distance) tuples sorted by distance
        """
        if node_id not in self.graph:
            return []
        
        distances = []
        for neighbor in self.graph.nodes():
            if neighbor != node_id:
                dist = self.shortest_path_length(node_id, neighbor)
                if dist < float("inf"):
                    distances.append((neighbor, dist))
        
        return sorted(distances, key=lambda x: x[1])[:n]
    
    def is_connected(self, source: str, target: str) -> bool:
        """Check if two nodes are connected."""
        return self.shortest_path(source, target) is not None
    
    def precompute_distances(self) -> None:
        """
        Pre-compute all pairwise shortest distances.
        
        This is MUCH faster than computing them on demand for repeated queries.
        With 39 nodes and 136 edges, this takes ~10ms once vs ~0.02ms per query.
        For 1000 iterations with 100+ queries each, pre-computing saves minutes.
        """
        # Use Dijkstra's all-pairs which is optimized for sparse graphs
        all_pairs = dict(nx.all_pairs_dijkstra_path_length(self.graph, weight="distance"))
        
        for source, targets in all_pairs.items():
            for target, distance in targets.items():
                cache_key = (source, target, "distance")
                self._distance_cache[cache_key] = distance
        
        # Log cache size
        import logging
        logger = logging.getLogger("cvrp.network")
        logger.debug(f"Pre-computed {len(self._distance_cache)} distance pairs")
    
    @classmethod
    def build_from_data(
        cls, 
        nodes: Dict[str, Node], 
        edges: Dict[str, Edge],
        precompute: bool = True
    ) -> "Network":
        """
        Build a network from node and edge data.
        
        Args:
            nodes: Dictionary of nodes keyed by node_id
            edges: Dictionary of edges keyed by edge_id
            precompute: Whether to pre-compute all distances (recommended)
        
        Returns:
            Constructed Network instance
        """
        network = cls()
        
        # Add all nodes
        for node in nodes.values():
            network.add_node(node)
        
        # Store mappings in graph attributes for compatibility
        network.graph.graph["code_to_name"] = network.code_to_name
        network.graph.graph["name_to_code"] = network.name_to_code
        
        # Add all edges
        for edge in edges.values():
            network.add_edge(edge)
        
        # Pre-compute all distances for O(1) lookups
        if precompute:
            network.precompute_distances()
        
        return network
