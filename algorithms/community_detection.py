# algorithms/community_detection.py
import networkx as nx


def label_propagation(graph):
    """
    Apply the label propagation community detection algorithm.

    :param graph: NetworkX graph
    :return: List of lists, where each sublist contains the nodes in a cluster
    """
    print("Applying label_propagation_communities...")
    communities = nx.community.label_propagation_communities(graph)
    return [list(community) for community in communities]


def asyn_lpa_communities(graph):
    """
    Apply the asynchronous label propagation algorithm.

    :param graph: NetworkX graph
    :return: List of lists, where each sublist contains the nodes in a cluster
    """
    print("Applying asyn_lpa_communities...")
    communities = nx.community.asyn_lpa_communities(graph, weight="weight")
    return [list(community) for community in communities]


def girvan_newman(graph):
    """
    Apply the Girvan-Newman community detection algorithm.

    :param graph: NetworkX graph
    :return: List of lists, where each sublist contains the nodes in a cluster
    """
    print("Applying girvan_newman...")
    communities = nx.community.girvan_newman(graph)
    return [list(community) for community in communities]


def louvain(graph):
    """
    Apply the Louvain community detection algorithm.

    :param graph: NetworkX graph
    :return: List of lists, where each sublist contains the nodes in a cluster
    """
    print("Applying louvain...")
    communities = nx.community.louvain_communities(graph, weight="weight")
    return [list(community) for community in communities]


def modularity(graph):
    """
    Apply the modularity community detection algorithm.

    :param graph: NetworkX graph
    :return: List of lists, where each sublist contains the nodes in a cluster
    """
    print("Applying modularity...")
    communities = nx.community.modularity_max.greedy_modularity_communities(graph)
    return [list(community) for community in communities]


def kernighan_lin(graph):
    """
    Apply the Kernighan-Lin community detection algorithm.

    :param graph: NetworkX graph
    :return: List of lists, where each sublist contains the nodes in a cluster
    """
    print("Applying kernighan_lin bipartitions...")
    communities = nx.community.kernighan_lin_bisection(graph)
    return [list(community) for community in communities]
