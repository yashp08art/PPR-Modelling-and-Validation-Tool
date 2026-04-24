
import networkx as nx
import streamlit as st
import pandas as pd
from itertools import combinations



# 6a — PPR Coverage Requirement Check


def run_requirement_check(graph: nx.DiGraph) -> dict:
    product_violations = []
    process_violations = []

    for node_id, data in graph.nodes(data=True):
        node_type = data.get("type")
        node_name = data.get("name", node_id)

        if node_type == "Product":
            incoming_process = [
                src for src in graph.predecessors(node_id)
                if graph.nodes[src].get("type") == "Process"
            ]
            if not incoming_process:
                product_violations.append({
                    "Node ID": node_id,
                    "Name": node_name,
                    "Reason": "No assembly Process is linked to this Product — it will be left unassembled.",
                })

        elif node_type == "Process":
            incoming_resource = [
                src for src in graph.predecessors(node_id)
                if graph.nodes[src].get("type") == "Resource"
            ]
            if not incoming_resource:
                process_violations.append({
                    "Node ID": node_id,
                    "Name": node_name,
                    "Reason": "No Resource is assigned to this Process — it cannot be executed.",
                })

    passed = not product_violations and not process_violations
    return {
        "passed": passed,
        "product_violations": product_violations,
        "process_violations": process_violations,
    }


def render_requirement_check(graph: nx.DiGraph):
    st.subheader("Graph Requirement Check")

    algo_tab = st.tabs([
        "6a — PPR Coverage",
        "6b — View-Specific Dependencies",
        "6c — Similarly Structured Elements",
        "6d — Disconnected Segments",
    ])

    with algo_tab[0]:
        _render_6a(graph)
    with algo_tab[1]:
        _render_6b(graph)
    with algo_tab[2]:
        _render_6c(graph)
    with algo_tab[3]:
        _render_6d(graph)


def _render_6a(graph: nx.DiGraph):
    st.markdown("### 6a — PPR Coverage Requirement")

    result = run_requirement_check(graph)

    if result["passed"]:
        st.success("All requirements satisfied. The PPR model is fully valid.")
    else:
        st.error("Requirement violations found.")

    if result["product_violations"]:
        st.markdown("#### Product Violations")
        st.table(pd.DataFrame(result["product_violations"]))

    if result["process_violations"]:
        st.markdown("#### Process Violations")
        st.table(pd.DataFrame(result["process_violations"]))

    st.markdown("#### Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Product Violations", len(result["product_violations"]))
    c2.metric("Process Violations", len(result["process_violations"]))
    c3.metric("Overall Status", "PASS" if result["passed"] else "FAIL")



# 6b — View-Specific Dependencies

FAILURE_DEPENDENCIES = [
    ("P7", "P6", "Axle failure → Wheel mounting fails"),
    ("P1", "P2", "Chassis failure → Body block detaches"),
    ("P5", "P1", "Spoiler detachment → Chassis stress"),
]


def run_dependency_analysis(graph: nx.DiGraph) -> dict:
    failure_graph = nx.DiGraph()

    for u, v, d in graph.edges(data=True):
        failure_graph.add_edge(u, v, relation=d.get("relation", ""), origin="ppr")

    for src, tgt, desc in FAILURE_DEPENDENCIES:
        if src in graph.nodes and tgt in graph.nodes:
            failure_graph.add_edge(src, tgt, relation=desc, origin="failure")

    failure_sources = list({src for src, _, _ in FAILURE_DEPENDENCIES if src in graph.nodes})
    propagation_paths = {}

    for source in failure_sources:
        reachable = set(nx.descendants(failure_graph, source))
        propagation_paths[source] = sorted(reachable)

    impact_count = {}
    for source, affected in propagation_paths.items():
        for node in affected:
            impact_count[node] = impact_count.get(node, 0) + 1

    critical_nodes = sorted(impact_count.items(), key=lambda x: -x[1])

    return {
        "dependency_edges": FAILURE_DEPENDENCIES,
        "propagation_paths": propagation_paths,
        "critical_nodes": critical_nodes,
        "overlay_graph": failure_graph,
    }


def _render_6b(graph: nx.DiGraph):
    st.markdown("### 6b — View-Specific Dependencies (Reliability)")

    result = run_dependency_analysis(graph)

    st.markdown("#### Failure Dependency Edges")
    dep_rows = [{"From": s, "To": t, "Description": d} for s, t, d in result["dependency_edges"]]
    st.table(pd.DataFrame(dep_rows))

    st.markdown("#### Failure Propagation Paths")
    if result["propagation_paths"]:
        for source, affected in result["propagation_paths"].items():
            source_name = graph.nodes[source].get("name", source) if source in graph.nodes else source
            with st.expander(f"If {source} ({source_name}) fails → {len(affected)} nodes affected"):
                rows = []
                for a in affected:
                    node_data = graph.nodes.get(a, {})
                    rows.append({
                        "Affected Node": a,
                        "Name": node_data.get("name", ""),
                        "Type": node_data.get("type", ""),
                    })
                if rows:
                    st.table(pd.DataFrame(rows))
    else:
        st.info("No failure propagation paths found.")

    st.markdown("#### Most Impacted Nodes")
    if result["critical_nodes"]:
        crit_rows = []
        for node_id, count in result["critical_nodes"]:
            node_data = graph.nodes.get(node_id, {})
            crit_rows.append({
                "Node ID": node_id,
                "Name": node_data.get("name", ""),
                "Type": node_data.get("type", ""),
                "Affected by N Failures": count,
            })
        st.table(pd.DataFrame(crit_rows))



# 6c — Similarly Structured Elements


def run_similarity_analysis(graph: nx.DiGraph) -> dict:
    signatures = {}

    for node_id, data in graph.nodes(data=True):
        node_type = data.get("type", "Unknown")

        predecessor_types = tuple(sorted(
            graph.nodes[p].get("type", "Unknown") for p in graph.predecessors(node_id)
        ))
        successor_types = tuple(sorted(
            graph.nodes[s].get("type", "Unknown") for s in graph.successors(node_id)
        ))

        sig = (node_type, predecessor_types, successor_types)
        if sig not in signatures:
            signatures[sig] = []
        signatures[sig].append(node_id)

    similar_groups = {sig: nodes for sig, nodes in signatures.items() if len(nodes) >= 2}

    labeled_groups = {}
    for sig, nodes in similar_groups.items():
        node_type, predecessor_types, successor_types = sig
        pred_str = ", ".join(predecessor_types) if predecessor_types else "none"
        successor_str = ", ".join(successor_types) if successor_types else "none"
        label = f"{node_type} | predecessors: [{pred_str}] | successors: [{successor_str}]"
        labeled_groups[label] = nodes

    pairs = []
    for label, nodes in labeled_groups.items():
        for a, b in combinations(nodes, 2):
            pairs.append({
                "Node A": a,
                "Name A": graph.nodes[a].get("name", ""),
                "Node B": b,
                "Name B": graph.nodes[b].get("name", ""),
                "Shared Signature": label,
            })

    return {"groups": labeled_groups, "pairs": pairs}


def _render_6c(graph: nx.DiGraph):
    st.markdown("### 6c — Similarly Structured Elements")

    result = run_similarity_analysis(graph)

    if not result["groups"]:
        st.info("No similarly structured elements found.")
        return

    st.markdown(f"#### {len(result['groups'])} Similarity Group(s) Found")

    for label, nodes in result["groups"].items():
        with st.expander(f"{label} — {len(nodes)} nodes"):
            rows = []
            for n in nodes:
                d = graph.nodes[n]
                rows.append({
                    "Node ID": n,
                    "Name": d.get("name", ""),
                    "Type": d.get("type", ""),
                    "In-Degree": graph.in_degree(n),
                    "Out-Degree": graph.out_degree(n),
                })
            st.table(pd.DataFrame(rows))

    st.markdown("#### All Similar Pairs")
    if result["pairs"]:
        st.table(pd.DataFrame(result["pairs"]))
    st.metric("Total Similar Pairs", len(result["pairs"]))



# 6d — Disconnected Production Segments


def run_disconnected_segments(graph: nx.DiGraph) -> dict:
    components = list(nx.weakly_connected_components(graph))
    components = sorted(components, key=len, reverse=True)

    component_details = []
    for i, comp in enumerate(components):
        products = [n for n in comp if graph.nodes[n].get("type") == "Product"]
        processes = [n for n in comp if graph.nodes[n].get("type") == "Process"]
        resources = [n for n in comp if graph.nodes[n].get("type") == "Resource"]
        subgraph = graph.subgraph(comp)

        component_details.append({
            "Component": i + 1,
            "Total Nodes": len(comp),
            "Products": len(products),
            "Processes": len(processes),
            "Resources": len(resources),
            "Edges": subgraph.number_of_edges(),
            "Node IDs": ", ".join(sorted(comp)),
        })

    return {
        "components": components,
        "is_connected": len(components) == 1,
        "component_details": component_details,
    }


def _render_6d(graph: nx.DiGraph):
    st.markdown("### 6d — Disconnected Production Segments")

    result = run_disconnected_segments(graph)

    if result["is_connected"]:
        st.success(
            f"The graph is fully connected — 1 component with {graph.number_of_nodes()} nodes."
        )
    else:
        st.warning(
            f"The graph has {len(result['components'])} disconnected segments."
        )

    st.markdown("#### Component Breakdown")
    if result["component_details"]:
        st.table(pd.DataFrame(result["component_details"]))

    if len(result["components"]) > 1:
        st.markdown("#### Component Details")
        for i, comp in enumerate(result["components"]):
            with st.expander(f"Component {i + 1} — {len(comp)} nodes"):
                rows = []
                for n in sorted(comp):
                    d = graph.nodes[n]
                    rows.append({
                        "Node ID": n,
                        "Name": d.get("name", ""),
                        "Type": d.get("type", ""),
                    })
                st.table(pd.DataFrame(rows))

    st.markdown("#### Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Components", len(result["components"]))
    c2.metric("Largest Component", max((len(c) for c in result["components"]), default=0))
    c3.metric("Connected?", "YES" if result["is_connected"] else "NO")
