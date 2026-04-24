

import json
import os

import pandas as pd
import streamlit as st

from modules.parser import load_from_upload
from modules.graph_builder import build_graph, validate_ppr_conformance
from modules.crud import (
    add_node, add_edge, update_node_attr, update_edge_relation,
    delete_node, delete_edge, get_all_nodes, get_all_edges
)
from modules.views import render_basic_engineering_view, render_reliability_view
from modules.algorithms import render_requirement_check
from modules.visualization import render_graphviz, render_pyvis, render_legend


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PPR Modeling Tool",
    page_icon="🏎️",
    layout="wide",
)

st.title("🏎️ PPR Modeling Tool")


# ── Helpers ──────────────────────────────────────────────────────────────────
SAMPLE_PATH = "data/lego_car_ppr.json"


def _load_sample():
    """Load the bundled Lego Car sample model into session state."""
    with open(SAMPLE_PATH) as f:
        raw = json.load(f)
    st.session_state.graph = build_graph(raw)


# ── Session state init ───────────────────────────────────────────────────────
if "graph" not in st.session_state:
    st.session_state.graph = None


# ── Sidebar: File Upload ─────────────────────────────────────────────────────
with st.sidebar:
    st.header("📂 Load PPR Model")
    fmt = st.selectbox("File Format", ["JSON", "XML", "Excel (.xlsx)"])

    ext_map = {"JSON": ["json"], "XML": ["xml"], "Excel (.xlsx)": ["xlsx"]}
    uploaded = st.file_uploader("Upload PPR File", type=ext_map[fmt])

    if st.button("Load Model", type="primary"):
        raw = load_from_upload(uploaded)
        if raw:
            G = build_graph(raw)
            violations = validate_ppr_conformance(G)
            if violations:
                st.warning(f"PPR conformance warnings ({len(violations)}):")
                for v in violations:
                    st.caption(v)
            st.session_state.graph = G
            st.success(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")

    st.divider()

    # Load default sample data
    if st.button("Load Sample Lego Car (JSON)"):
        _load_sample()
        st.success("Sample model loaded!")

    # NEW: reset button — restores the sample in case the user has edited it
    if st.session_state.graph is not None:
        if st.button("🔄 Reset to Sample", help="Discard all edits and reload the original Lego Car sample model."):
            if os.path.exists(SAMPLE_PATH):
                _load_sample()
                st.success("Model reset to sample.")
            else:
                st.error(f"Sample file not found at {SAMPLE_PATH}.")

    st.divider()
    st.markdown("**Node type guide:**")
    st.markdown("- `P__` → Product\n- `PR__` → Process\n- `R__` → Resource")


# ── Main area ────────────────────────────────────────────────────────────────
G = st.session_state.graph

if G is None:
    st.info("👈 Upload a PPR file or load the sample model from the sidebar to begin.")
    st.stop()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Graph View",
    "🔧 Engineering View",
    "🛡️ Reliability View",
    "✏️ CRUD Operations",
    "✅ Requirement Check",
    "📋 Data Tables",
])


# ── Tab 1: Graph Visualization ───────────────────────────────────────────────
with tabs[0]:
    st.subheader("PPR Graph Visualization")
    render_legend()
    viz_mode = st.radio("Render mode", ["Graphviz (static)", "PyVis (interactive)"], horizontal=True)
    if viz_mode == "Graphviz (static)":
        render_graphviz(G)
    else:
        render_pyvis(G)


# ── Tab 2: Basic Engineering View ────────────────────────────────────────────
with tabs[1]:
    render_basic_engineering_view(G)


# ── Tab 3: Reliability View ──────────────────────────────────────────────────
with tabs[2]:
    render_reliability_view(G)


# ── Tab 4: CRUD Operations (enhanced) ────────────────────────────────────────
with tabs[3]:
    st.subheader("✏️ CRUD Operations")
    st.caption(
        "Edit the Lego Car model: add or remove nodes and edges, or update "
        "existing attributes. Current values are shown so you can edit with context."
    )

    op = st.selectbox(
        "Select Operation",
        [
            "Create Node",
            "Create Edge",
            "Edit Node",
            "Update Edge Relation",
            "Delete Node",
            "Delete Edge",
        ],
    )

    # ── Create Node ─────────────────────────────────────────────────────
    if op == "Create Node":
        with st.form("create_node"):
            nid   = st.text_input("Node ID (e.g. P8)")
            ntype = st.selectbox("Type", ["Product", "Process", "Resource"])
            nname = st.text_input("Name")

            # Optional view-specific attributes typed per node type
            extra_attrs = {}
            if ntype == "Product":
                c1, c2 = st.columns(2)
                with c1:
                    color = st.text_input("Color (optional)", value="")
                    material = st.text_input("Material (optional)", value="")
                with c2:
                    cost = st.number_input("Cost (€, optional)", min_value=0.0, value=0.0, step=0.10)
                    weight = st.number_input("Weight (g, optional)", min_value=0.0, value=0.0, step=1.0)
                if color:    extra_attrs["color"] = color
                if material: extra_attrs["material"] = material
                if cost > 0: extra_attrs["cost"] = cost
                if weight > 0: extra_attrs["weight"] = weight

            elif ntype == "Process":
                c1, c2 = st.columns(2)
                with c1:
                    atime = st.number_input("Assembly time (min, optional)", min_value=0, value=0, step=1)
                with c2:
                    oee = st.slider("OEE (optional)", 0.0, 1.0, 0.0, 0.01)
                if atime > 0: extra_attrs["assembly_time"] = atime
                if oee > 0:   extra_attrs["oee"] = oee

            submitted = st.form_submit_button("Add Node")
            if submitted:
                add_node(G, nid.strip(), ntype, nname.strip(), extra_attrs or None)

    # ── Create Edge ─────────────────────────────────────────────────────
    elif op == "Create Edge":
        node_ids = list(G.nodes())
        with st.form("create_edge"):
            src = st.selectbox("Source Node", node_ids)
            tgt = st.selectbox("Target Node", node_ids)
            rel = st.selectbox(
                "Relation",
                ["performs", "produces", "used_in", "inspects", "other…"],
            )
            custom_rel = ""
            if rel == "other…":
                custom_rel = st.text_input("Custom relation")
            submitted = st.form_submit_button("Add Edge")
            if submitted:
                final_rel = custom_rel.strip() if rel == "other…" else rel
                add_edge(G, src, tgt, final_rel)

    # ── Edit Node (rich editor — shows current values) ──────────────────
    elif op == "Edit Node (rich editor)":
        node_ids = list(G.nodes())
        if not node_ids:
            st.info("No nodes in the graph yet.")
        else:
            nid = st.selectbox("Select node to edit", node_ids)
            current = dict(G.nodes[nid])
            ntype = current.get("type", "Product")

            st.caption(f"Editing **{nid}** — type **{ntype}**")

            with st.form("edit_node"):
                # Name is always editable
                new_name = st.text_input("Name", value=current.get("name", ""))

                # Type-specific typed widgets pre-filled from the current node
                updates = {"name": new_name}

                if ntype == "Product":
                    c1, c2 = st.columns(2)
                    with c1:
                        new_color = st.text_input("Color", value=current.get("color", ""))
                        new_material = st.text_input("Material", value=current.get("material", ""))
                    with c2:
                        new_cost = st.number_input(
                            "Cost (€)", min_value=0.0,
                            value=float(current.get("cost", 0.0) or 0.0), step=0.10,
                        )
                        new_weight = st.number_input(
                            "Weight (g)", min_value=0.0,
                            value=float(current.get("weight", 0.0) or 0.0), step=1.0,
                        )
                    updates.update({
                        "color": new_color, "material": new_material,
                        "cost": new_cost, "weight": new_weight,
                    })

                elif ntype == "Process":
                    c1, c2 = st.columns(2)
                    with c1:
                        new_atime = st.number_input(
                            "Assembly time (min)", min_value=0,
                            value=int(current.get("assembly_time", 0) or 0), step=1,
                        )
                    with c2:
                        new_oee = st.slider(
                            "OEE", 0.0, 1.0,
                            float(current.get("oee", 0.0) or 0.0), 0.01,
                        )
                    updates.update({"assembly_time": new_atime, "oee": new_oee})

                # Free-form attribute for any other edits
                with st.expander("Advanced: edit any other attribute"):
                    extra_key = st.text_input("Attribute key (optional)", value="")
                    extra_val = st.text_input("Attribute value (optional)", value="")

                submitted = st.form_submit_button("Save Changes")
                if submitted:
                    for k, v in updates.items():
                        # Skip empty strings so we don't overwrite with blanks
                        if v == "" or v is None:
                            continue
                        update_node_attr(G, nid, k, v)
                    if extra_key.strip() and extra_val.strip():
                        update_node_attr(G, nid, extra_key.strip(), extra_val.strip())

    # ── Update Edge Relation ────────────────────────────────────────────
    elif op == "Update Edge Relation":
        edge_list = [(u, v) for u, v in G.edges()]
        if not edge_list:
            st.info("No edges in the graph yet.")
        else:
            with st.form("update_edge"):
                edge = st.selectbox("Edge (source → target)", [f"{u} → {v}" for u, v in edge_list])
                # Pre-fill current relation
                src, tgt = edge.split(" → ")
                current_rel = G.edges[src.strip(), tgt.strip()].get("relation", "")
                new_rel = st.text_input("New Relation", value=current_rel)
                submitted = st.form_submit_button("Update")
                if submitted:
                    update_edge_relation(G, src.strip(), tgt.strip(), new_rel.strip())

    # ── Delete Node ─────────────────────────────────────────────────────
    elif op == "Delete Node":
        node_ids = list(G.nodes())
        if not node_ids:
            st.info("No nodes to delete.")
        else:
            with st.form("delete_node"):
                nid = st.selectbox("Node to Delete", node_ids)
                confirm = st.checkbox("Yes, I want to delete this node and all its edges.")
                submitted = st.form_submit_button("Delete Node", type="primary")
                if submitted:
                    if confirm:
                        delete_node(G, nid)
                    else:
                        st.warning("Please confirm deletion by ticking the checkbox.")

    # ── Delete Edge ─────────────────────────────────────────────────────
    elif op == "Delete Edge":
        edge_list = [(u, v) for u, v in G.edges()]
        if not edge_list:
            st.info("No edges to delete.")
        else:
            with st.form("delete_edge"):
                edge = st.selectbox("Edge to Delete", [f"{u} → {v}" for u, v in edge_list])
                submitted = st.form_submit_button("Delete Edge", type="primary")
                if submitted:
                    src, tgt = edge.split(" → ")
                    delete_edge(G, src.strip(), tgt.strip())


# ── Tab 5: Requirement Check ─────────────────────────────────────────────────
with tabs[4]:
    render_requirement_check(G)


# ── Tab 6: Data Tables ───────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("📋 Raw Data Tables")
    st.markdown("#### Nodes")
    nodes_df = pd.DataFrame(get_all_nodes(G))
    st.dataframe(nodes_df, use_container_width=True)

    st.markdown("#### Edges")
    edges_df = pd.DataFrame(get_all_edges(G))
    st.dataframe(edges_df, use_container_width=True)
