

import networkx as nx

VALID_NODE_TYPES = {"Product", "Process", "Resource"}

# PPR conformance: allowed (source_type → target_type) pairs
VALID_EDGE_PAIRS = {
    ("Resource", "Process"),
    ("Process", "Product"),
}


def build_graph(data: dict) -> nx.DiGraph:
    """Build and return a directed NetworkX graph from parsed PPR data."""
    G = nx.DiGraph()

    for node in data.get("nodes", []):
        node_id = node.get("id")
        if not node_id:
            continue
        attrs = {k: v for k, v in node.items() if k != "id"}
        G.add_node(node_id, **attrs)

    for edge in data.get("edges", []):
        src = edge.get("source")
        tgt = edge.get("target")
        rel = edge.get("relation", "")
        if src and tgt:
            G.add_edge(src, tgt, relation=rel)

    return G


def validate_ppr_conformance(G: nx.DiGraph) -> list[str]:

    violations = []
    for src, tgt in G.edges():
        src_type = G.nodes[src].get("type", "Unknown")
        tgt_type = G.nodes[tgt].get("type", "Unknown")
        if (src_type, tgt_type) not in VALID_EDGE_PAIRS:
            violations.append(
                f"Invalid edge: {src} ({src_type}) → {tgt} ({tgt_type})"
            )
    return violations


def graph_to_dict(G: nx.DiGraph) -> dict:

    nodes = [{"id": n, **G.nodes[n]} for n in G.nodes()]
    edges = [{"source": u, "target": v, **G.edges[u, v]} for u, v in G.edges()]
    return {"nodes": nodes, "edges": edges}