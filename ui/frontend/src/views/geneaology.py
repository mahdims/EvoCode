import json
import streamlit as st
import networkx as nx
from streamlit_agraph import agraph, Node, Edge, Config

from style import UIConfig

def get_node_color_by_fitness(fitness: float, min_fit: float, max_fit: float):
    if max_fit == min_fit:
        return UIConfig.COLOR_MED_FITNESS

    normalized = (fitness - min_fit) / (max_fit - min_fit)

    if normalized > 0.7:
        return UIConfig.COLOR_HIGH_FITNESS
    elif normalized > 0.3:
        return UIConfig.COLOR_MED_FITNESS
    else:
        return UIConfig.COLOR_LOW_FITNESS

def render_genealogy_graph(snapshot, selected_node_id):
    if snapshot is None or not snapshot.get('genealogy_json'):
        st.info("No genealogy data available for this generation.")
        return None, None

    if "graph_view_seed" not in st.session_state:
        st.session_state.graph_view_seed = 0

    col_lbl, col_btn = st.columns([0.85, 0.15])
    with col_lbl:
        st.caption("Interactive Tree (Click node to inspect)")
    with col_btn:
        if st.button("Reset View", help="Click if graph is off-center or zoomed out"):
            st.session_state.graph_view_seed += 1
            st.rerun()

    try:
        tree_data = json.loads(snapshot['genealogy_json'])
        G = nx.node_link_graph(tree_data)
    except (json.JSONDecodeError, Exception) as e:
        st.error(f"Failed to parse genealogy data: {e}")
        return None, None

    if not G.nodes():
        return None, None

    # Generation range filter
    node_gens = [G.nodes[n].get('generation', 0) for n in G.nodes()]
    gen_min_val = min(node_gens) if node_gens else 0
    gen_max_val = max(node_gens) if node_gens else 0

    if gen_min_val < gen_max_val:
        gen_range = st.slider(
            "Filter by generation range",
            min_value=int(gen_min_val),
            max_value=int(gen_max_val),
            value=(int(gen_min_val), int(gen_max_val)),
            key="genealogy_gen_filter"
        )
        visible_nodes = {
            n for n in G.nodes()
            if gen_range[0] <= G.nodes[n].get('generation', 0) <= gen_range[1]
        }
    else:
        visible_nodes = set(G.nodes())

    best_node_id = max(visible_nodes, key=lambda n: G.nodes[n].get('fitness', 0))

    active_node_id = best_node_id
    if selected_node_id is not None:
        try:
            sel_int = int(selected_node_id)
            if sel_int in visible_nodes:
                active_node_id = sel_int
        except:
            pass

    fitness_values = [G.nodes[n].get('fitness', 50) for n in visible_nodes]
    min_fit = min(fitness_values) if fitness_values else 0
    max_fit = max(fitness_values) if fitness_values else 100

    path_nodes = set()
    path_edges = set()

    # Calculate ancestry path for the ACTIVE node
    try:
        if active_node_id in G.nodes():
            roots = [n for n, d in G.in_degree() if d == 0]
            if roots:
                root = roots[0]
                path_list = nx.shortest_path(G, source=root, target=active_node_id)
                path_nodes = set(path_list)
                path_edges = {
                    tuple(sorted((u, v))) for u, v in zip(path_list, path_list[1:])
                }
    except Exception as e:
        st.warning(f"Could not compute ancestry path: {e}")

    viz_nodes = []
    viz_edges = []

    for node_id in visible_nodes:
        fitness = G.nodes[node_id].get('fitness', 50)
        is_alive = G.nodes[node_id].get('alive', True)
        node_id_str = str(node_id)

        if node_id == active_node_id:
            base_color = get_node_color_by_fitness(fitness, min_fit, max_fit)
            color = {
                "background": base_color,
                "border": UIConfig.COLOR_SELECTED_NODE,
                "highlight": {"background": base_color, "border": UIConfig.COLOR_SELECTED_NODE}
            }
            size = 35
        elif node_id in path_nodes:
            color = UIConfig.COLOR_PATH_HIGHLIGHT
            size = 28
        else:
            if not is_alive:
                color = "#444444"
            else:
                color = get_node_color_by_fitness(fitness, min_fit, max_fit)
            size = 20

        viz_nodes.append(Node(
            id=node_id_str,
            label=node_id_str,
            size=size,
            color=color,
            font={'color': 'white', 'size': 10}
        ))

    for u, v in G.edges():
        if u not in visible_nodes or v not in visible_nodes:
            continue
        edge_tuple = tuple(sorted((u, v)))
        if edge_tuple in path_edges:
            color = UIConfig.COLOR_PATH_HIGHLIGHT
            width = 4.0
        else:
            color = "#444444"
            width = 1.5

        viz_edges.append(Edge(
            source=str(u),
            target=str(v),
            color=color,
            width=width,
            type="CURVE_SMOOTH"
        ))

    layout_tweak = st.session_state.graph_view_seed % 2

    config = Config(
        width="100%",
        height=UIConfig.GRAPH_HEIGHT,
        directed=True,
        physics=False,
        fit=True,
        hierarchical=True,
        layout={
            "hierarchical": {
                "enabled": True,
                "levelSeparation": 100,
                "nodeSpacing": 100 + layout_tweak, # Oscillates 100 <-> 101 to force redraw when resetting view
                "direction": "UD",
                "sortMethod": "directed"
            }
        },
        interaction={
            "dragNodes": False,
            "dragView": True,
            "zoomView": True
        }
    )

    return_value = agraph(nodes=viz_nodes, edges=viz_edges, config=config)

    st.markdown("""
    <div style="display:flex;gap:20px;align-items:center;flex-wrap:wrap;
                padding:6px 0;font-size:0.78rem;color:#8B7D6B;">
      <span style="font-weight:600;">Legend:</span>
      <span><span style="display:inline-block;width:11px;height:11px;border-radius:50%;
            background:#C96442;margin-right:4px;vertical-align:middle;"></span>High fitness</span>
      <span><span style="display:inline-block;width:11px;height:11px;border-radius:50%;
            background:#D4A853;margin-right:4px;vertical-align:middle;"></span>Mid fitness</span>
      <span><span style="display:inline-block;width:11px;height:11px;border-radius:50%;
            background:#8B8070;margin-right:4px;vertical-align:middle;"></span>Low fitness</span>
      <span><span style="display:inline-block;width:11px;height:11px;border-radius:50%;
            background:#444444;margin-right:4px;vertical-align:middle;"></span>Pruned</span>
      <span><span style="display:inline-block;width:11px;height:11px;border-radius:50%;
            background:#D4845E;margin-right:4px;vertical-align:middle;"></span>Ancestry path</span>
      <span><span style="display:inline-block;width:11px;height:11px;border-radius:50%;
            background:#C96442;border:2px solid #7B3F1A;margin-right:4px;vertical-align:middle;"></span>Selected</span>
    </div>
    """, unsafe_allow_html=True)

    return return_value, (G, active_node_id)

def _get_descendant_stats(G, node_id):
    """Compute children count and best descendant fitness via BFS."""
    children = list(G.successors(node_id))
    children_count = len(children)

    best_desc_fitness = None
    best_desc_id = None
    queue = list(children)
    while queue:
        desc = queue.pop(0)
        f = G.nodes[desc].get('fitness', 0)
        if best_desc_fitness is None or f > best_desc_fitness:
            best_desc_fitness = f
            best_desc_id = desc
        queue.extend(G.successors(desc))

    return children_count, best_desc_fitness, best_desc_id


def render_node_inspector(G, active_node_id, language = 'java'):
    if G is None or active_node_id is None or active_node_id not in G.nodes:
        st.info("No node selected.")
        return

    node_data = G.nodes[active_node_id]

    st.markdown("### Node Inspector")

    with st.container(border=True):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Node ID", str(active_node_id))
        with col_m2:
            st.metric("Fitness", f"{node_data.get('fitness', 0):.5f}")

        # Parent Info
        parents = list(G.predecessors(active_node_id))
        if parents:
            st.caption(f"Parent Node: {parents[0]}")
        else:
            st.caption("Parent Node: None (Root)")

        # Descendant stats
        children_count, best_desc_fitness, best_desc_id = _get_descendant_stats(G, active_node_id)
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.metric("Children", children_count)
        with col_d2:
            if best_desc_fitness is not None:
                st.metric("Best Descendant", f"{best_desc_fitness:.5f}",
                          help=f"Node {best_desc_id}")
            else:
                st.metric("Best Descendant", "—")

    # Code Container
    st.markdown("#### Code Snapshot")
    code_content = node_data.get('code', '# No code available for this node.')
    st.code(code_content, language=language, line_numbers=True, height=480)
