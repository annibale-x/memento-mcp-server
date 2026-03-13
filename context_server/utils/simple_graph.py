"""
Simple in-memory graph structure to replace NetworkX.

This module provides a lightweight graph implementation with only the
functionality needed by the mcp-context-server, eliminating the
dependency on NetworkX.
"""

import json
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


class SimpleGraph:
    """
    Simple in-memory directed graph structure.

    This class provides a minimal graph implementation with only the
    functionality needed for memory graph operations, replacing NetworkX.
    """

    def __init__(self) -> None:
        """Initialize an empty directed graph."""
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.in_edges: Dict[str, Set[Tuple[str, str]]] = {}
        self.out_edges: Dict[str, Set[Tuple[str, str]]] = {}

    def add_node(self, node_id: str, **properties: Any) -> None:
        """
        Add a node to the graph.

        Args:
            node_id: Unique identifier for the node
            **properties: Node properties as keyword arguments
        """
        self.nodes[node_id] = properties

        # Initialize edge tracking for new node
        if node_id not in self.in_edges:
            self.in_edges[node_id] = set()
        if node_id not in self.out_edges:
            self.out_edges[node_id] = set()

    def add_edge(self, from_id: str, to_id: str, **properties: Any) -> None:
        """
        Add a directed edge to the graph.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            **properties: Edge properties as keyword arguments
        """
        edge_key = (from_id, to_id)
        self.edges[edge_key] = properties

        # Update edge tracking
        self.out_edges.setdefault(from_id, set()).add(edge_key)
        self.in_edges.setdefault(to_id, set()).add(edge_key)

        # Ensure nodes exist (they should, but be defensive)
        if from_id not in self.nodes:
            self.add_node(from_id)
        if to_id not in self.nodes:
            self.add_node(to_id)

    def number_of_nodes(self) -> int:
        """
        Return the number of nodes in the graph.

        Returns:
            Number of nodes
        """
        return len(self.nodes)

    def number_of_edges(self) -> int:
        """
        Return the number of edges in the graph.

        Returns:
            Number of edges
        """
        return len(self.edges)

    def has_node(self, node_id: str) -> bool:
        """
        Check if a node exists in the graph.

        Args:
            node_id: Node ID to check

        Returns:
            True if node exists, False otherwise
        """
        return node_id in self.nodes

    def has_edge(self, from_id: str, to_id: str) -> bool:
        """
        Check if a directed edge exists.

        Args:
            from_id: Source node ID
            to_id: Target node ID

        Returns:
            True if edge exists, False otherwise
        """
        return (from_id, to_id) in self.edges

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get properties of a node.

        Args:
            node_id: Node ID

        Returns:
            Node properties dictionary, or None if node doesn't exist
        """
        return self.nodes.get(node_id)

    def get_edge(self, from_id: str, to_id: str) -> Optional[Dict[str, Any]]:
        """
        Get properties of an edge.

        Args:
            from_id: Source node ID
            to_id: Target node ID

        Returns:
            Edge properties dictionary, or None if edge doesn't exist
        """
        return self.edges.get((from_id, to_id))

    def get_predecessors(self, node_id: str) -> List[str]:
        """
        Get all nodes that have edges pointing to the given node.

        Args:
            node_id: Target node ID

        Returns:
            List of predecessor node IDs
        """
        if node_id not in self.in_edges:
            return []

        return [from_id for from_id, _ in self.in_edges[node_id]]

    def get_successors(self, node_id: str) -> List[str]:
        """
        Get all nodes that the given node has edges pointing to.

        Args:
            node_id: Source node ID

        Returns:
            List of successor node IDs
        """
        if node_id not in self.out_edges:
            return []

        return [to_id for _, to_id in self.out_edges[node_id]]

    def get_in_degree(self, node_id: str) -> int:
        """
        Get the number of edges pointing to a node.

        Args:
            node_id: Node ID

        Returns:
            In-degree of the node
        """
        return len(self.in_edges.get(node_id, set()))

    def get_out_degree(self, node_id: str) -> int:
        """
        Get the number of edges pointing from a node.

        Args:
            node_id: Node ID

        Returns:
            Out-degree of the node
        """
        return len(self.out_edges.get(node_id, set()))

    def get_total_degree(self, node_id: str) -> int:
        """
        Get the total number of edges connected to a node.

        Args:
            node_id: Node ID

        Returns:
            Total degree of the node (in-degree + out-degree)
        """
        return self.get_in_degree(node_id) + self.get_out_degree(node_id)

    def nodes_iter(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """
        Iterate over all nodes in the graph.

        Yields:
            Tuples of (node_id, properties) for each node
        """
        yield from self.nodes.items()

    def edges_iter(self) -> Iterator[Tuple[Tuple[str, str], Dict[str, Any]]]:
        """
        Iterate over all edges in the graph.

        Yields:
            Tuples of ((from_id, to_id), properties) for each edge
        """
        yield from self.edges.items()

    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node and all its connected edges from the graph.

        Args:
            node_id: Node ID to remove

        Returns:
            True if node was removed, False if it didn't exist
        """
        if node_id not in self.nodes:
            return False

        # Remove all edges connected to this node
        edges_to_remove = set()

        # Edges where this node is the source
        if node_id in self.out_edges:
            edges_to_remove.update(self.out_edges[node_id])

        # Edges where this node is the target
        if node_id in self.in_edges:
            edges_to_remove.update(self.in_edges[node_id])

        # Remove all connected edges
        for from_id, to_id in edges_to_remove:
            self.remove_edge(from_id, to_id)

        # Clean up edge tracking
        if node_id in self.out_edges:
            del self.out_edges[node_id]
        if node_id in self.in_edges:
            del self.in_edges[node_id]

        # Remove the node
        del self.nodes[node_id]

        return True

    def remove_edge(self, from_id: str, to_id: str) -> bool:
        """
        Remove a directed edge from the graph.

        Args:
            from_id: Source node ID
            to_id: Target node ID

        Returns:
            True if edge was removed, False if it didn't exist
        """
        edge_key = (from_id, to_id)

        if edge_key not in self.edges:
            return False

        # Remove from edge tracking
        if from_id in self.out_edges:
            self.out_edges[from_id].discard(edge_key)
        if to_id in self.in_edges:
            self.in_edges[to_id].discard(edge_key)

        # Remove the edge
        del self.edges[edge_key]

        return True

    def clear(self) -> None:
        """Remove all nodes and edges from the graph."""
        self.nodes.clear()
        self.edges.clear()
        self.in_edges.clear()
        self.out_edges.clear()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the graph to a dictionary representation.

        Returns:
            Dictionary with nodes and edges
        """
        # Convert edge tuples to string keys for JSON serialization
        edges_dict = {}
        for (from_id, to_id), properties in self.edges.items():
            edge_key = f"{from_id}->{to_id}"
            edges_dict[edge_key] = properties

        return {"nodes": self.nodes, "edges": edges_dict}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Load graph from a dictionary representation.

        Args:
            data: Dictionary with 'nodes' and 'edges' keys
        """
        self.clear()

        # Load nodes
        for node_id, properties in data.get("nodes", {}).items():
            self.add_node(node_id, **properties)

        # Load edges
        edges_data = data.get("edges", {})
        for edge_key, properties in edges_data.items():
            # Handle both tuple keys (from previous version) and string keys
            if isinstance(edge_key, tuple) and len(edge_key) == 2:
                from_id, to_id = edge_key
            elif isinstance(edge_key, str) and "->" in edge_key:
                from_id, to_id = edge_key.split("->", 1)
            else:
                # Skip invalid edge keys
                continue

            self.add_edge(from_id, to_id, **properties)

    def to_json(self) -> str:
        """
        Convert the graph to a JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), default=str)

    def from_json(self, json_str: str) -> None:
        """
        Load graph from a JSON string.

        Args:
            json_str: JSON string representation
        """
        data = json.loads(json_str)
        self.from_dict(data)

    def __str__(self) -> str:
        """String representation of the graph."""
        return f"SimpleGraph(nodes={self.number_of_nodes()}, edges={self.number_of_edges()})"

    def __repr__(self) -> str:
        """Detailed representation of the graph."""
        return f"SimpleGraph(nodes={self.nodes}, edges={self.edges})"
