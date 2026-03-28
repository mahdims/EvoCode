# EvoCode Dashboard

A real-time Streamlit dashboard for monitoring and guiding the EvoCode evolutionary loop. The UI connects to a shared SQLite database populated by the evolution process and provides interactive visualizations of fitness progress, code diffs, strategy exploration, and solution space analysis.

## Quick Start

```bash
cd ui/frontend
pip install -r requirements.txt
streamlit run src/dashboard.py --server.address=localhost
```

The dashboard opens at **http://localhost:8501**. Start an evolution run in a separate terminal so the UI has data to display:

```bash
cd evolver
python evo_agent.py config.json
```

> **Note:** Do not pass `--novisual` to the evolution command -- that flag disables writing to the database the UI reads from.

## Features Overview

The dashboard is organized into five tabs, a sidebar for navigation controls, and a shared generation history inspector.

---

### Sidebar Controls

| Control | Description |
|---------|-------------|
| **Track Latest Generation** | When enabled, the UI auto-refreshes and always shows the most recent generation. Disable to manually browse older generations via the history table. |
| **Poll Rate (seconds)** | How often the UI checks for new data (1--10 seconds, default 2). Only active when tracking the latest generation. |
| **Snapshot Stats** | Displays the selected generation's best fitness, average fitness, and diversity index. Also shows the latest generation's fitness and improvement delta. |

---

### Tab 1: Plots -- Performance Metrics

Tracks the evolution's progress over time with three charts:

- **Fitness Line Chart** -- Best fitness (blue) and average fitness (purple) across generations. A dashed vertical line marks the currently selected generation. A dropdown lets you switch between the default fitness metric and any additional metrics logged by the evaluator.
- **Diversity Index** (area chart, green) -- Measures genetic diversity within the population. A declining diversity may indicate premature convergence.
- **Viability Rate** (bar chart, red) -- Percentage of generated candidates that compile and pass the smoke test each generation.

All charts are interactive (Plotly): zoom, pan, and hover for exact values.

---

### Tab 2: Genealogy -- Evolutionary Tree

Visualizes the parent-child relationships across all candidates:

- **Interactive Graph** (left panel, 60%) -- A hierarchical network where each node is a candidate. Nodes are color-coded by fitness: green (high), yellow (medium), gray (low), dark gray (dead/failed). Click a node to inspect it. The ancestry path from the selected node to the root is highlighted in cyan.
- **Node Inspector** (right panel, 40%) -- Shows the selected node's ID, fitness, parent, and full source code with syntax highlighting.
- **Reset View** -- Repositions the graph if it drifts after interactions.

---

### Tab 3: Code Diff -- Code Evolution Comparison

Side-by-side comparison of the best candidate's code between any two generations:

- **Baseline Selector** -- Choose which earlier generation to compare against (defaults to generation 1).
- **Diff View** -- Two-column layout showing the baseline code on the left and the current generation's code on the right. Changed lines are highlighted: red background for removals, green for additions. Syntax highlighting follows the Catppuccin Mocha theme.

Useful for understanding exactly what the LLM changed between iterations.

---

### Tab 4: Strategies -- Strategy Analysis & Expert Guidance

Combines automated strategy tracking with a human-in-the-loop input mechanism:

- **Expert Guidance** (top) -- A text box where you can review the tested strategies below and then provide direction for what the EvoAgent should explore next. Click "Send to EvoAgent" to submit. This is a UI placeholder for future human-in-the-loop functionality.
- **Strategies Table** -- Lists all exploration strategies the evolution has tried, with columns for direction, idea description, status, and impact. Strategies are sorted by status: Succeeded (green) > Exploring (blue) > Queued > Interrupted (orange) > Abandoned (red).
- **Long-Term Reflections** -- Markdown-rendered synthesis of what the LLM has learned across generations: which principles work, which patterns to avoid, and what to try next.

---

### Tab 5: Embeddings -- Solution Space Visualization

Maps the population of candidates into a 2D semantic space:

- **Embeddings Scatter Plot** -- Each point is a candidate, positioned by semantic similarity. Point size reflects fitness; color reflects strategy cluster. Reveals whether the search is exploring diverse regions or converging.
- **Exploration Density Heatmap** (expandable) -- A 2D histogram showing which regions of the solution space have been heavily explored (red) versus unexplored (blue). Helps identify gaps in the search.

---

### Generation History Inspector

A shared component that appears at the bottom of the Plots, Genealogy, and Code Diff tabs:

- Sortable table of all generations with columns: Generation, Best Fitness, Avg Fitness, Viability Rate, Diversity.
- Click any row to jump to that generation. This automatically disables "Track Latest" so you can inspect historical data without being pulled forward.
- The selected row is highlighted in gold.

---

## Architecture

```
ui/frontend/
  src/
    dashboard.py          Main entry point and tab layout
    dao.py                SQLite data access layer (read-only, WAL mode)
    utils.py              Session state management and metric processing
    style.py              UI constants, colors, and Catppuccin Mocha theme
    views/
      metrics.py          Plots tab (fitness, diversity, viability charts)
      geneaology.py       Genealogy tab (network graph + node inspector)
      code_diff.py        Code Diff tab (side-by-side diff with highlighting)
      strategy.py         Strategies tab (expert input + strategy table + reflections)
      embedding.py        Embeddings tab (scatter plot + density heatmap)
      history.py          Reusable generation history inspector table
  .streamlit/
    config.toml           Streamlit theme configuration (dark mode)
  Dockerfile              Container build for deployment
  requirements.txt        Python dependencies
```

### Data Flow

1. The evolution process (`evo_agent.py`) writes generation data to a shared SQLite database.
2. The UI connects in read-only mode with WAL enabled for concurrent access.
3. On each poll cycle, the UI fetches the latest metrics and renders the active tab.
4. User interactions (row clicks, node selections) update Streamlit session state and trigger a rerun.

### Database Tables

| Table | Contents |
|-------|----------|
| `metrics` | Per-generation aggregates: global_best, avg_fitness, diversity, viability_rate, additional_metrics (JSON) |
| `snapshots` | Per-generation details: best_code_snippet, genealogy_json, embeddings_json |
| `strategies` | Global strategy tracking: idea, direction, status, impact, best_fit |
| `reflections` | LLM-generated long-term reflections per generation |

## Configuration

### Streamlit Theme

The dashboard uses a dark theme configured in `.streamlit/config.toml`:

- Background: `#011627` (Night Owl)
- Primary accent: `#82aaff`
- Text: `#d6deeb`

### Docker Deployment

```bash
cd ui/frontend
docker build -t evocode-dashboard .
docker run -p 8501:8501 -v /data:/data evocode-dashboard
```

Or use the project-level `docker-compose.yaml` to start the full stack (LiteLLM + EvoCode + Dashboard).

## Dependencies

- `streamlit` -- Web framework
- `pandas` / `numpy` -- Data processing
- `plotly` -- Interactive charts
- `networkx` -- Graph algorithms for genealogy
- `pygments` -- Syntax highlighting
- `streamlit-agraph` -- Interactive network graph component
