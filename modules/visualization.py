

import graphviz
import streamlit as st
import networkx as nx
from pyvis.network import Network
import tempfile
import os


# ── Color / shape map ────────────────────────────────────────────────────────
NODE_STYLE = {
    "Product":  {"color": "#4A90D9", "shape": "box",     "fontcolor": "white"},
    "Process":  {"color": "#27AE60", "shape": "ellipse", "fontcolor": "white"},
    "Resource": {"color": "#E67E22", "shape": "diamond", "fontcolor": "white"},
}

# Faded styling for non-highlighted nodes in the traceability (full) view
FADED_COLOR = "#D5D8DC"
FADED_FONT = "#7F8C8D"
FADED_EDGE = "#D5D8DC"

EDGE_COLOR = {
    "produces": "#27AE60",
    "performs": "#E67E22",
    "used_in":  "#9B59B6",
    "inspects": "#E74C3C",
}

# Style used for overlay edges such as failure dependencies
OVERLAY_EDGE_COLOR = "#E74C3C"


def _pyvis_shape(ntype: str) -> str:
    """Map a PPR node type to a PyVis shape name."""
    if ntype == "Product":
        return "box"
    if ntype == "Process":
        return "ellipse"
    return "diamond"


def render_graphviz(
    graph: nx.DiGraph,
    title: str = "PPR Graph",
    highlight_nodes: set = None,
    context_mode: str = "full",
    extra_edges: list = None,
    node_label_overrides: dict = None,
):

    highlight_nodes = highlight_nodes or set()
    extra_edges = extra_edges or []
    node_label_overrides = node_label_overrides or {}

    # Decide which nodes to actually draw
    if context_mode == "view_only" and highlight_nodes:
        visible_nodes = {n for n in graph.nodes() if n in highlight_nodes}
    else:
        visible_nodes = set(graph.nodes())

    dot = graphviz.Digraph(comment=title)
    dot.attr(rankdir="LR", bgcolor="white", fontsize="12")
    dot.attr("node", style="filled", fontname="Helvetica", fontsize="11")

    for node_id, data in graph.nodes(data=True):
        if node_id not in visible_nodes:
            continue

        ntype = data.get("type", "Product")
        style = NODE_STYLE.get(ntype, NODE_STYLE["Product"])
        base_label = node_label_overrides.get(
            node_id, f"{node_id}\n{data.get('name', '')}"
        )

        is_member = (not highlight_nodes) or (node_id in highlight_nodes)

        if is_member:
            fill = style["color"]
            font_color = style["fontcolor"]
        else:
            # Full-mode traceability: non-members rendered as faded grey
            fill = FADED_COLOR
            font_color = FADED_FONT

        dot.node(
            node_id,
            label=base_label,
            shape=style["shape"],
            fillcolor=fill,
            fontcolor=font_color,
        )

    for src, tgt, edata in graph.edges(data=True):
        if src not in visible_nodes or tgt not in visible_nodes:
            continue
        relation = edata.get("relation", "")
        both_members = (
            (not highlight_nodes)
            or (src in highlight_nodes and tgt in highlight_nodes)
        )
        color = EDGE_COLOR.get(relation, "#555555") if both_members else FADED_EDGE
        dot.edge(src, tgt, label=relation, color=color, fontsize="9")

    # Overlay edges (e.g. failure dependencies) drawn on top, dashed red
    for src, tgt, label in extra_edges:
        if src in visible_nodes and tgt in visible_nodes:
            dot.edge(
                src,
                tgt,
                label=label,
                color=OVERLAY_EDGE_COLOR,
                fontsize="9",
                style="dashed",
                penwidth="2",
            )

    st.graphviz_chart(dot.source, use_container_width=True)


def render_pyvis(
    graph: nx.DiGraph,
    highlight_nodes: set = None,
    context_mode: str = "full",
    extra_edges: list = None,
    node_label_overrides: dict = None,
):

    highlight_nodes = highlight_nodes or set()
    extra_edges = extra_edges or []
    node_label_overrides = node_label_overrides or {}

    if context_mode == "view_only" and highlight_nodes:
        visible_nodes = {n for n in graph.nodes() if n in highlight_nodes}
    else:
        visible_nodes = set(graph.nodes())

    net = Network(
        height="650px",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
    )

    # No hierarchical layout — we set x/y manually so nodes are fully free to drag.
    net.set_options("""
    {
      "layout": {
        "hierarchical": {"enabled": false}
      },
      "physics": {
        "enabled": false
      },
      "edges": {
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.8}},
        "smooth": {"type": "cubicBezier", "roundness": 0.4},
        "font": {"size": 10, "color": "#cccccc", "strokeWidth": 0},
        "color": {"inherit": false}
      },
      "nodes": {
        "font": {"size": 12},
        "margin": 10
      },
      "interaction": {
        "hover": true,
        "dragNodes": true,
        "dragView": true,
        "zoomView": true
      }
    }
    """)

    # Group nodes by type for tiered placement (only count visible ones)
    y_positions = {"Resource": -300, "Process": 0, "Product": 300}
    x_spacing = 200

    type_buckets = {"Resource": [], "Process": [], "Product": []}
    for node_id, data in graph.nodes(data=True):
        if node_id not in visible_nodes:
            continue
        ntype = data.get("type", "Product")
        type_buckets.get(ntype, type_buckets["Product"]).append(node_id)

    node_positions = {}
    for ntype, node_list in type_buckets.items():
        count = len(node_list)
        start_x = -((count - 1) * x_spacing) / 2
        for i, node_id in enumerate(sorted(node_list)):
            node_positions[node_id] = (start_x + i * x_spacing, y_positions[ntype])

    for node_id, data in graph.nodes(data=True):
        if node_id not in visible_nodes:
            continue

        ntype = data.get("type", "Product")
        style = NODE_STYLE.get(ntype, NODE_STYLE["Product"])
        label = node_label_overrides.get(
            node_id, f"{node_id}\n{data.get('name', '')}"
        )
        pos_x, pos_y = node_positions.get(node_id, (0, 0))

        is_member = (not highlight_nodes) or (node_id in highlight_nodes)
        fill_color = style["color"] if is_member else FADED_COLOR
        font_color = "white" if is_member else FADED_FONT

        net.add_node(
            node_id,
            label=label,
            color=fill_color,
            shape=_pyvis_shape(ntype),
            title=str(data),
            font={"color": font_color, "size": 12},
            x=pos_x,
            y=pos_y,
            size=25 if ntype == "Resource" else 20,
        )

    for src, tgt, edata in graph.edges(data=True):
        if src not in visible_nodes or tgt not in visible_nodes:
            continue
        relation = edata.get("relation", "")
        both_members = (
            (not highlight_nodes)
            or (src in highlight_nodes and tgt in highlight_nodes)
        )
        color = EDGE_COLOR.get(relation, "#aaaaaa") if both_members else FADED_EDGE
        net.add_edge(
            src,
            tgt,
            title=relation,
            label=relation,
            color=color,
            width=1.5,
        )

    # Overlay edges (e.g. failure dependencies) — red dashed, drawn on top
    for src, tgt, label in extra_edges:
        if src in visible_nodes and tgt in visible_nodes:
            net.add_edge(
                src,
                tgt,
                title=label,
                label=label,
                color=OVERLAY_EDGE_COLOR,
                width=2,
                dashes=True,
            )

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        net.save_graph(f.name)
        html_path = f.name

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    os.unlink(html_path)
    st.components.v1.html(html_content, height=670, scrolling=False)


def render_legend():
    """Display a color/shape legend for node types."""
    st.markdown("""
    **Graph Legend:**
    🟦 **Product** — Blue Rectangle &nbsp;&nbsp;
    🟩 **Process** — Green Ellipse &nbsp;&nbsp;
    🟧 **Resource** — Orange Diamond
    """)
