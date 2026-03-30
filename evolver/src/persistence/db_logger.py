"""
Database logging for the evolution loop.

Handles SQLite initialization and per-generation persistence so that
EvolutionLoop is not burdened with storage concerns.
"""

import json
import os
import random as _random
import sqlite3
import time
from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np
from loguru import logger

DB_PATH = os.getenv("EVOCODE_DB_PATH", "/data/evolution.db")


def init_db(clear: bool = False) -> None:
    """Initialize the database, optionally clearing all rows from a previous run.

    Args:
        clear: If True, DELETE all rows before creating tables. Pass True on a
               fresh (non-resume) run to prevent stale generations from a prior
               experiment bleeding into the UI.
    """
    logger.debug(f"[DB INIT] Checking database at {DB_PATH}...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                generation INTEGER PRIMARY KEY,
                global_best REAL,
                avg_fitness REAL,
                viability_rate REAL,
                diversity REAL,
                timestamp REAL,
                additional_metrics TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                generation INTEGER PRIMARY KEY,
                genealogy_json TEXT,
                best_code_snippet TEXT,
                strategies_json TEXT,
                embeddings_json TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                idea TEXT PRIMARY KEY,
                direction TEXT,
                status TEXT,
                impact TEXT,
                best_fit REAL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                generation INTEGER PRIMARY KEY,
                content TEXT,
                timestamp REAL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_stats (
                generation INTEGER PRIMARY KEY,
                total_calls INTEGER,
                input_tokens INTEGER,
                output_tokens INTEGER,
                call_breakdown TEXT,
                wall_time_sec REAL,
                process_cpu_pct REAL,
                process_mem_mb REAL,
                timestamp REAL
            )
        """)

        # Safe migration — add column if missing from older DB
        try:
            conn.execute("SELECT additional_metrics FROM metrics LIMIT 1")
        except sqlite3.OperationalError:
            logger.debug("[DB INIT] Migrating DB: Adding additional_metrics column...")
            conn.execute("ALTER TABLE metrics ADD COLUMN additional_metrics TEXT")

        if clear:
            logger.debug("[DB INIT] Clearing stale rows from previous run...")
            conn.execute("DELETE FROM metrics")
            conn.execute("DELETE FROM snapshots")
            conn.execute("DELETE FROM reflections")
            conn.execute("DELETE FROM strategies")
            conn.execute("DELETE FROM llm_stats")

    logger.debug("[DB INIT] Database initialized.")


def log_generation(
    generation: int,
    population: List[Dict[str, Any]],
    offspring_list: List[Dict[str, Any]],
    num_attempted: int,
    history: Dict[str, Any],
    strategy_registry: Dict[str, Any],
    embedding_service,
    llm,
    long_term_reflection: str = "",
    all_candidates: Optional[List[Dict[str, Any]]] = None,
    wall_time: float = 0.0,
) -> None:
    """Persist one generation's metrics, snapshots, and strategy table to SQLite.

    Args:
        generation: Current generation index.
        population: Current population (list of candidate dicts).
        offspring_list: Offspring produced this generation.
        num_attempted: Total candidates attempted (for viability rate).
        history: Genealogy dict mapping candidate_id → candidate dict.
        strategy_registry: Running dict of idea → strategy metadata.
        embedding_service: EmbeddingService instance (may be unavailable).
        llm: LLMAgents instance (for call stats).
        long_term_reflection: Current accumulated reflection text.
        all_candidates: All candidates evaluated this generation (elites + offspring).
                        Falls back to population if None.
        wall_time: Wall-clock seconds for this generation.
    """
    if not population:
        return

    viability = len(offspring_list) / num_attempted if num_attempted > 0 else 0.0
    fitnesses = [c["fitness"] for c in population]
    best_candidate = max(population, key=lambda x: x["fitness"])
    global_best = best_candidate["fitness"]
    avg_fitness = float(np.mean(fitnesses))

    diversity_info = embedding_service.compute_population_diversity(population)
    diversity = diversity_info["avg_diversity"] if diversity_info else float(np.var(fitnesses))

    # ── Genealogy tree ──────────────────────────────────────────────────────
    for child in offspring_list:
        history[child["candidate_id"]] = child
    for ind in population:
        if ind["candidate_id"] not in history:
            history[ind["candidate_id"]] = ind

    G = nx.DiGraph()
    living_ids = {ind["candidate_id"] for ind in population}
    for cid, data in history.items():
        G.add_node(
            cid,
            fitness=data.get("fitness", 0),
            code=data.get("code", ""),
            label=str(cid),
            alive=cid in living_ids,
            generation=data.get("generation", 0),
        )
        if data.get("parent_id") in history:
            G.add_edge(data["parent_id"], cid)

    genealogy_json = json.dumps(nx.node_link_data(G))

    # ── Strategy registry update ─────────────────────────────────────────────
    for child in offspring_list:
        idea_key = child.get("idea")
        if not idea_key or len(idea_key) < 5:
            continue
        child_fitness = child.get("fitness", 0.0)
        mutation_type = child.get("mutation_type", "Evolution")

        if idea_key not in strategy_registry:
            status = "Succeeded" if child_fitness > avg_fitness else "Exploring"
            strategy_registry[idea_key] = {
                "Direction": mutation_type,
                "Idea": idea_key,
                "Status": status,
                "Impact": f"{child_fitness:.4f}",
                "Best_Fit": child_fitness,
            }
        else:
            entry = strategy_registry[idea_key]
            if child_fitness > entry.get("Best_Fit", -float("inf")):
                entry["Best_Fit"] = child_fitness
                entry["Impact"] = f"{child_fitness:.4f}"
                if child_fitness > avg_fitness:
                    entry["Status"] = "Succeeded"
            if entry["Status"] == "Exploring" and child_fitness < (avg_fitness * 0.8):
                entry["Status"] = "Abandoned"

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_candidates = all_candidates if all_candidates is not None else population
    embeddings = embedding_service.compute_2d_embeddings(embedding_candidates)

    if embeddings is None:
        embeddings = []
        for idx, child in enumerate(embedding_candidates):
            fitness = child.get("fitness", 0.0)
            score_dict = child.get("score_vector", {})
            if not isinstance(score_dict, dict):
                score_dict = {}
            clean_values = []
            for k in sorted(score_dict.keys()):
                val = score_dict[k]
                if val in (float("inf"), -float("inf")):
                    val = 0.0
                clean_values.append(val)
            if len(clean_values) >= 2:
                x_val, y_val = clean_values[0], clean_values[1]
            elif len(clean_values) == 1:
                x_val = clean_values[0]
                y_val = idx * 0.01 + _random.uniform(-0.005, 0.005)
            else:
                x_val = idx * 0.01
                y_val = _random.uniform(-0.005, 0.005)
            embeddings.append({
                "x": x_val,
                "y": y_val,
                "Strategy Cluster": str(child.get("mutation_type", "Initial")),
                "Fitness": fitness,
            })

    embeddings_json = json.dumps(embeddings)

    # ── LLM call stats ───────────────────────────────────────────────────────
    llm_call_stats = llm.get_and_reset_stats() if llm is not None else {}
    total_calls   = sum(v["calls"]        for v in llm_call_stats.values())
    input_tokens  = sum(v["input_tokens"] for v in llm_call_stats.values())
    output_tokens = sum(v["output_tokens"] for v in llm_call_stats.values())
    call_breakdown_json = json.dumps(llm_call_stats)

    # ── Process resource snapshot ────────────────────────────────────────────
    try:
        import psutil as _psutil
        _proc = _psutil.Process()
        _proc.cpu_percent(interval=None)
        process_cpu_pct = _proc.cpu_percent(interval=0.05)
        process_mem_mb  = _proc.memory_info().rss / 1e6
    except Exception:
        process_cpu_pct = 0.0
        process_mem_mb  = 0.0

    # ── Write to DB ──────────────────────────────────────────────────────────
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except Exception:
                pass

            for s in strategy_registry.values():
                conn.execute(
                    "INSERT OR REPLACE INTO strategies VALUES (?, ?, ?, ?, ?)",
                    (s["Idea"], s["Direction"], s["Status"], s["Impact"], s.get("Best_Fit", 0.0)),
                )

            conn.execute(
                "INSERT OR REPLACE INTO metrics VALUES (?, ?, ?, ?, ?, ?, ?)",
                (generation, global_best, avg_fitness, viability, diversity, time.time(), "{}"),
            )

            current_strategies_list = json.dumps(list(strategy_registry.values()))
            conn.execute(
                "INSERT OR REPLACE INTO snapshots VALUES (?, ?, ?, ?, ?)",
                (generation, genealogy_json, best_candidate.get("code", ""),
                 current_strategies_list, embeddings_json),
            )

            conn.execute(
                "INSERT OR REPLACE INTO reflections VALUES (?, ?, ?)",
                (generation, long_term_reflection, time.time()),
            )

            conn.execute(
                "INSERT OR REPLACE INTO llm_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (generation, total_calls, input_tokens, output_tokens,
                 call_breakdown_json, wall_time, process_cpu_pct, process_mem_mb, time.time()),
            )

    except Exception as e:
        logger.error(f"[DB Error] Failed to log generation {generation}: {e}")
