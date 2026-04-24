
import json
import pandas as pd
import xml.etree.ElementTree as ET
import streamlit as st


def parse_json(file) -> dict:
    data = json.load(file)
    return {"nodes": data.get("nodes", []), "edges": data.get("edges", [])}


def parse_xml(file) -> dict:
    tree = ET.parse(file)
    root = tree.getroot()

    nodes, edges = [], []

    for node_el in root.find("nodes") or []:
        nodes.append(dict(node_el.attrib))

    for edge_el in root.find("edges") or []:
        edges.append(dict(edge_el.attrib))

    return {"nodes": nodes, "edges": edges}


def parse_excel(file) -> dict:
    xls = pd.ExcelFile(file)
    nodes_df = pd.read_excel(xls, sheet_name="nodes")
    edges_df = pd.read_excel(xls, sheet_name="edges")
    return {
        "nodes": nodes_df.to_dict(orient="records"),
        "edges": edges_df.to_dict(orient="records"),
    }


def load_from_upload(uploaded_file) -> dict | None:

    if uploaded_file is None:
        return None

    name = uploaded_file.name.lower()

    try:
        if name.endswith(".json"):
            return parse_json(uploaded_file)
        elif name.endswith(".xml"):
            return parse_xml(uploaded_file)
        elif name.endswith(".xlsx"):
            return parse_excel(uploaded_file)
        else:
            st.error(f"Unsupported file format: {name}")
            return None
    except Exception as e:
        st.error(f"Error parsing file: {e}")
        return None
