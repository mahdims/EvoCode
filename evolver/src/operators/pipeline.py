"""
Work-stealing parallel pipeline for candidate generation.

Decouples the threading infrastructure from EvolutionLoop so the
orchestrator stays focused on evolutionary logic.
"""

from queue import Queue
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger


def generate_offspring_batch(
    num_offspring: int,
    num_workers: int,
    starting_candidate_id: int,
    generate_one: Callable[[int, int], Optional[Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], int]:
    """Run *num_offspring* candidate pipelines across *num_workers* threads.

    Each worker repeatedly pulls a task index from a shared queue and calls
    ``generate_one(task_index, candidate_id)`` to produce a candidate dict.
    Workers that finish early steal tasks from the remaining queue (work-stealing).

    Args:
        num_offspring: Number of candidates to attempt.
        num_workers: Thread-pool size (capped at num_offspring).
        starting_candidate_id: First candidate ID to assign; IDs are allocated
                               atomically so parallel workers don't collide.
        generate_one: ``(task_index, candidate_id) -> Optional[Dict]``
                      Returns a candidate dict on success, or None on failure.

    Returns:
        ``(results, next_candidate_id)`` where *next_candidate_id* is the
        first unused ID after this batch.
    """
    task_queue: Queue = Queue()
    for i in range(num_offspring):
        task_queue.put(i)

    results: List[Dict[str, Any]] = []
    results_lock = Lock()

    candidate_id_counter = [starting_candidate_id]
    candidate_id_lock = Lock()

    def _next_id() -> int:
        with candidate_id_lock:
            cid = candidate_id_counter[0]
            candidate_id_counter[0] += 1
            return cid

    DONE = object()

    def _worker(worker_id: int) -> None:
        while True:
            task = task_queue.get()
            if task is DONE:
                task_queue.task_done()
                break

            task_idx = task
            candidate_id = _next_id()
            try:
                result = generate_one(task_idx, candidate_id)
                if result is not None:
                    with results_lock:
                        results.append(result)
            except Exception as e:
                logger.error(f"[Worker{worker_id}] Candidate {candidate_id} failed: {e}")
            finally:
                task_queue.task_done()

    actual_workers = min(num_workers, num_offspring)
    logger.debug(f"[PIPELINE] Starting {actual_workers} workers for {num_offspring} offspring")

    workers = [Thread(target=_worker, args=(i,), daemon=True) for i in range(actual_workers)]
    for w in workers:
        w.start()

    task_queue.join()

    for _ in range(actual_workers):
        task_queue.put(DONE)

    for w in workers:
        w.join(timeout=1)

    next_id = candidate_id_counter[0]
    logger.debug(f"[PIPELINE] Complete: {len(results)}/{num_offspring} offspring succeeded")
    return results, next_id
