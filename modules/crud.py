
import networkx as nx
import streamlit as st
from modules.graph_builder import VALID_EDGE_PAIRS


# ── CREATE ──────────────────────────────────────────────────────────────────

def add_node(G: nx.DiGraph, node_id: str, node_type: str, name: str, extra_attrs: dict = None):
    if node_id in G.nodes:
        st.warning(f"Node '{node_id}' already exists.")
        return False
    attrs = {"type": node_type, "name": name}
    if extra_attrs:
        attrs.update(extra_attrs)
    G.add_node(node_id, **attrs)
    st.success(f"Node '{node_id}' added successfully.")
    return True


def add_edge(G: nx.DiGraph, src: str, tgt: str, relation: str):
    if src not in G.nodes or tgt not in G.nodes:
        st.error(f"Both nodes must exist. Check '{src}' and '{tgt}'.")
        return False
    src_type = G.nodes[src].get("type")
    tgt_type = G.nodes[tgt].get("type")
    if (src_type, tgt_type) not in VALID_EDGE_PAIRS:
        st.error(
            f"PPR conformance violation: Cannot connect {src_type} → {tgt_type}. "
            f"Allowed pairs: Resource→Process, Process→Product."
        )
        return False
    if G.has_edge(src, tgt):
        st.warning(f"Edge '{src}' → '{tgt}' already exists.")
        return False
    G.add_edge(src, tgt, relation=relation)
    st.success(f"Edge '{src}' → '{tgt}' ({relation}) added.")
    return True


# ── READ ─────────────────────────────────────────────────────────────────────

def get_node_details(G: nx.DiGraph, node_id: str) -> dict | None:
    if node_id not in G.nodes:
        return None
    return {"id": node_id, **G.nodes[node_id]}


def get_all_nodes(G: nx.DiGraph) -> list[dict]:
    return [{"id": n, **G.nodes[n]} for n in G.nodes()]


def get_all_edges(G: nx.DiGraph) -> list[dict]:
    return [{"source": u, "target": v, **G.edges[u, v]} for u, v in G.edges()]


# ── UPDATE ───────────────────────────────────────────────────────────────────

def update_node_attr(G: nx.DiGraph, node_id: str, attr_key: str, attr_val):
    if node_id not in G.nodes:
        st.error(f"Node '{node_id}' not found.")
        return False
    G.nodes[node_id][attr_key] = attr_val
    st.success(f"Node '{node_id}': '{attr_key}' updated to '{attr_val}'.")
    return True


def update_edge_relation(G: nx.DiGraph, src: str, tgt: str, new_relation: str):
    if not G.has_edge(src, tgt):
        st.error(f"Edge '{src}' → '{tgt}' not found.")
        return False
    G.edges[src, tgt]["relation"] = new_relation
    st.success(f"Edge '{src}' → '{tgt}' relation updated to '{new_relation}'.")
    return True


# ── DELETE ───────────────────────────────────────────────────────────────────

def delete_node(G: nx.DiGraph, node_id: str):
    if node_id not in G.nodes:
        st.error(f"Node '{node_id}' not found.")
        return False
    G.remove_node(node_id)
    st.success(f"Node '{node_id}' and all its edges removed.")
    return True


def delete_edge(G: nx.DiGraph, src: str, tgt: str):
    if not G.has_edge(src, tgt):
        st.error(f"Edge '{src}' → '{tgt}' not found.")
        return False
    G.remove_edge(src, tgt)
    st.success(f"Edge '{src}' → '{tgt}' removed.")
    return True