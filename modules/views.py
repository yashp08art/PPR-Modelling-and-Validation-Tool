

import pandas as pd
import streamlit as st
import networkx as nx

from modules.visualization import render_graphviz, render_pyvis, render_legend


RELIABILITY_DATA = {
    "P1": {"mtbf": 1000, "mttr": 5,  "fail_prob": 0.01, "maint_interval": 100},
    "P2": {"mtbf": 800,  "mttr": 4,  "fail_prob": 0.02, "maint_interval": 80},
    "P3": {"mtbf": 1200, "mttr": 2,  "fail_prob": 0.01, "maint_interval": 120},
    "P4": {"mtbf": 600,  "mttr": 3,  "fail_prob": 0.05, "maint_interval": 60},
    "P5": {"mtbf": 500,  "mttr": 5,  "fail_prob": 0.05, "maint_interval": 50},
    "P6": {"mtbf": 700,  "mttr": 2,  "fail_prob": 0.03, "maint_interval": 70},
    "P7": {"mtbf": 500,  "mttr": 2,  "fail_prob": 0.04, "maint_interval": 50},
    "PR1": {"mtbf": 300, "mttr": 10, "fail_prob": 0.02, "maint_interval": 30},
    "PR2": {"mtbf": 250, "mttr": 12, "fail_prob": 0.03, "maint_interval": 25},
    "PR5": {"mtbf": 200, "mttr": 8,  "fail_prob": 0.05, "maint_interval": 20},
    "PR6": {"mtbf": 220, "mttr": 6,  "fail_prob": 0.04, "maint_interval": 22},
    "R1":  {"mtbf": 160, "mttr": 60, "fail_prob": 0.10, "maint_interval": 16},
    "R3":  {"mtbf": 500, "mttr": 30, "fail_prob": 0.02, "maint_interval": 50},
}

FAILURE_DEPENDENCIES = [
    ("P7", "P6", "Axle failure → Wheel mounting fails"),
    ("P1", "P2", "Chassis failure → Body block detaches"),
    ("P5", "P1", "Spoiler detachment → Chassis stress"),
]


# ── Projection helpers ──────────────────────────────────────────────────────

def _basic_engineering_members(graph: nx.DiGraph) -> set:
    return {
        n for n, d in graph.nodes(data=True)
        if d.get("type") in ("Product", "Process")
    }


def _basic_engineering_labels(graph: nx.DiGraph) -> dict:
    overrides = {}
    for node_id, data in graph.nodes(data=True):
        ntype = data.get("type")
        name = data.get("name", "")
        if ntype == "Product":
            cost = data.get("cost", "N/A")
            weight = data.get("weight", "N/A")
            overrides[node_id] = f"{node_id}\n{name}\n€{cost} | {weight}g"
        elif ntype == "Process":
            atime = data.get("assembly_time", "N/A")
            oee = data.get("oee")
            oee_txt = f"{float(oee) * 100:.0f}%" if oee else "N/A"
            overrides[node_id] = f"{node_id}\n{name}\n{atime} min | OEE {oee_txt}"
    return overrides


def _reliability_members(graph: nx.DiGraph) -> set:
    return {n for n in graph.nodes() if n in RELIABILITY_DATA}


def _reliability_labels(graph: nx.DiGraph) -> dict:
    overrides = {}
    for node_id, data in graph.nodes(data=True):
        rel = RELIABILITY_DATA.get(node_id)
        if not rel:
            continue
        name = data.get("name", "")
        overrides[node_id] = (
            f"{node_id}\n{name}\n"
            f"MTBF {rel['mtbf']} | MTTR {rel['mttr']}\n"
            f"Fail {rel['fail_prob'] * 100:.1f}%"
        )
    return overrides


# ── View 4a — Basic Engineering View ────────────────────────────────────────

def render_basic_engineering_view(G: nx.DiGraph):
    st.subheader("Basic Engineering View")

    members = _basic_engineering_members(G)
    label_overrides = _basic_engineering_labels(G)

    graph_tabs = st.tabs([
        "View graph (projection)",
        "Traceability to full model",
        "Tables & KPIs",
    ])

    with graph_tabs[0]:
        render_legend()
        render_graphviz(
            G,
            title="Basic Engineering View — Projection",
            highlight_nodes=members,
            context_mode="view_only",
            node_label_overrides=label_overrides,
        )
        st.markdown("**Interactive version:**")
        render_pyvis(
            G,
            highlight_nodes=members,
            context_mode="view_only",
            node_label_overrides=label_overrides,
        )

    with graph_tabs[1]:
        render_legend()
        render_graphviz(
            G,
            title="Traceability — Basic Engineering View within the Full Model",
            highlight_nodes=members,
            context_mode="full",
        )

    with graph_tabs[2]:
        _render_basic_engineering_tables(G)


def _render_basic_engineering_tables(G: nx.DiGraph):
    st.markdown("#### Products — Cost & Material")
    prod_rows = []
    for n, d in G.nodes(data=True):
        if d.get("type") == "Product":
            prod_rows.append({
                "ID": n,
                "Name": d.get("name", ""),
                "Color": d.get("color", ""),
                "Material": d.get("material", ""),
                "Cost (€)": d.get("cost", "N/A"),
                "Weight (g)": d.get("weight", "N/A"),
            })
    if prod_rows:
        st.table(pd.DataFrame(prod_rows))

    st.markdown("#### Processes — OEE & Assembly Time")
    proc_rows = []
    for n, d in G.nodes(data=True):
        if d.get("type") == "Process":
            proc_rows.append({
                "ID": n,
                "Name": d.get("name", ""),
                "Assembly Time (min)": d.get("assembly_time", "N/A"),
                "OEE": f"{float(d.get('oee', 0)) * 100:.0f}%" if d.get("oee") else "N/A",
            })
    if proc_rows:
        st.table(pd.DataFrame(proc_rows))

    st.markdown("#### System KPIs")
    costs = [d.get("cost", 0) for _, d in G.nodes(data=True) if d.get("type") == "Product" and d.get("cost")]
    times = [d.get("assembly_time", 0) for _, d in G.nodes(data=True) if d.get("type") == "Process" and d.get("assembly_time")]
    oees  = [float(d.get("oee", 0)) for _, d in G.nodes(data=True) if d.get("type") == "Process" and d.get("oee")]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Part Cost (€)", f"€{sum(costs):.2f}")
    c2.metric("Total Assembly Time (min)", f"{sum(times)} min")
    c3.metric("Average OEE", f"{(sum(oees)/len(oees)*100):.1f}%" if oees else "N/A")

    st.markdown("#### Structural Relations (Process → Product)")
    rel_rows = []
    for u, v, d in G.edges(data=True):
        if G.nodes[u].get("type") == "Process" and G.nodes[v].get("type") == "Product":
            rel_rows.append({
                "Process": f"{u} — {G.nodes[u].get('name', '')}",
                "Relation": d.get("relation", ""),
                "Product": f"{v} — {G.nodes[v].get('name', '')}",
            })
    if rel_rows:
        st.table(pd.DataFrame(rel_rows))


# ── View 4d — Reliability View ──────────────────────────────────────────────

def render_reliability_view(G: nx.DiGraph):
    st.subheader("Reliability View")

    members = _reliability_members(G)
    label_overrides = _reliability_labels(G)

    overlay_edges = [
        (src, tgt, desc)
        for (src, tgt, desc) in FAILURE_DEPENDENCIES
        if src in G.nodes and tgt in G.nodes
    ]

    graph_tabs = st.tabs([
        "View graph (projection)",
        "Traceability to full model",
        "Tables & risk analysis",
    ])

    with graph_tabs[0]:
        render_legend()
        render_graphviz(
            G,
            title="Reliability View — Projection",
            highlight_nodes=members,
            context_mode="view_only",
            extra_edges=overlay_edges,
            node_label_overrides=label_overrides,
        )
        st.markdown("**Interactive version:**")
        render_pyvis(
            G,
            highlight_nodes=members,
            context_mode="view_only",
            extra_edges=overlay_edges,
            node_label_overrides=label_overrides,
        )

    with graph_tabs[1]:
        render_legend()
        render_graphviz(
            G,
            title="Traceability — Reliability View within the Full Model",
            highlight_nodes=members,
            context_mode="full",
            extra_edges=overlay_edges,
        )

    with graph_tabs[2]:
        _render_reliability_tables(G)


def _render_reliability_tables(G: nx.DiGraph):
    rows = []
    for node_id in G.nodes():
        rel = RELIABILITY_DATA.get(node_id)
        if rel:
            d = G.nodes[node_id]
            rows.append({
                "ID": node_id,
                "Name": d.get("name", ""),
                "Type": d.get("type", ""),
                "MTBF (cycles)": rel["mtbf"],
                "MTTR (min)": rel["mttr"],
                "Failure Probability": f"{rel['fail_prob']*100:.1f}%",
                "Maintenance Interval (cycles)": rel["maint_interval"],
            })

    if rows:
        df = pd.DataFrame(rows).sort_values("Type")
        st.table(df)

    st.markdown("#### Failure Dependency Edges")
    dep_df = pd.DataFrame(FAILURE_DEPENDENCIES, columns=["From Node", "To Node", "Description"])
    st.table(dep_df)

    st.markdown("#### High-Risk Components (Failure Probability > 4%)")
    high_risk = [r for r in rows if float(r["Failure Probability"].replace("%", "")) > 4.0]
    if high_risk:
        st.table(
            pd.DataFrame(high_risk)[["ID", "Name", "Failure Probability", "MTBF (cycles)"]]
        )
    else:
        st.info("No high-risk components found.")
