# algorithms/superpoint_graph.py
import numpy as np
from sklearn.neighbors import NearestNeighbors
import networkx as nx
from scipy.spatial.distance import pdist, squareform


def create_knn_graph(points, k):
    """
    Create a KNN graph from point cloud data.

    :param points: Numpy array of point cloud coordinates (shape: [n_points, 3]).
    :param k: Number of nearest neighbors to consider for graph construction.
    :return: NetworkX graph representing the KNN graph.
    """
    print("Creating KNN graph...")
    nbrs = NearestNeighbors(n_neighbors=k, algorithm="auto").fit(points)
    distances, indices = nbrs.kneighbors(points)

    G = nx.Graph()
    for i in range(indices.shape[0]):
        for j in range(1, indices.shape[1]):  # Start from 1 to avoid self-loop
            G.add_edge(i, indices[i, j], weight=distances[i, j])

    return G


def create_mst_graph(points):
    """
    Create a Minimum Spanning Tree (MST) graph from point cloud data.

    :param points: Numpy array of point cloud coordinates (shape: [n_points, 3]).
    :return: NetworkX graph representing the MST graph.
    """
    print("Creating MST graph...")
    # Calculate pairwise distances between points
    dist_matrix = squareform(pdist(points))

    # Create a complete graph
    G = nx.Graph()
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            G.add_edge(i, j, weight=dist_matrix[i, j])

    # Generate MST from the complete graph
    G = nx.minimum_spanning_tree(G)
    return G
