"""Cartesian parameter sweep engine."""

from __future__ import annotations

import copy
import itertools
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

from qorchsim.config.models import QOrchSimConfig
from qorchsim.experiments.runner import run_experiment


def _set_path(document: Any, path: str, value: Any) -> None:
    normalized = path.replace("[", ".").replace("]", "")
    parts = normalized.split(".")
    current = document
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    last = parts[-1]
    if isinstance(current, list):
        current[int(last)] = value
    else:
        current[last] = value


def expand_sweep(path: str | Path) -> list[tuple[QOrchSimConfig, dict[str, Any], int]]:
    sweep_path = Path(path)
    spec = yaml.safe_load(sweep_path.read_text(encoding="utf-8"))
    base_path = (sweep_path.parent / spec["base_config"]).resolve()
    base_raw = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    parameter_items = list(spec.get("parameters", {}).items())
    replicates = int(spec.get("replicates", 1))
    expanded = []
    for values in itertools.product(*(item[1] for item in parameter_items)):
        parameters = dict(zip((item[0] for item in parameter_items), values, strict=True))
        for replicate in range(replicates):
            raw = copy.deepcopy(base_raw)
            for key, value in parameters.items():
                _set_path(raw, key, value)
            seed = int(raw["simulation"]["seed"]) + replicate
            raw["simulation"]["seed"] = seed
            expanded.append((QOrchSimConfig.model_validate(raw), parameters, replicate))
    return expanded


def _run_point(args):
    config, output = args
    artifacts = run_experiment(config, output_directory=output)
    return artifacts.run_id, artifacts.summary


def run_sweep(path: str | Path, output_directory: str | Path, processes: int = 1) -> dict[str, object]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    points = expand_sweep(path)

    jobs = []
    metadata = []
    for index, (config, parameters, replicate) in enumerate(points):
        jobs.append((config, output / f"point-{index:05d}"))
        metadata.append(
            {
                "index": index,
                "parameters": parameters,
                "replicate": replicate,
                "seed": config.simulation.seed,
            }
        )

    results: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    def success(index: int, run_id: str, summary: dict[str, object]) -> dict[str, object]:
        return {**metadata[index], "run_id": run_id, "summary": summary}

    def failure(index: int, exc: Exception) -> dict[str, object]:
        return {**metadata[index], "error": f"{type(exc).__name__}: {exc}"}

    if processes == 1:
        for index, job in enumerate(jobs):
            try:
                run_id, summary = _run_point(job)
                results.append(success(index, run_id, summary))
            except Exception as exc:
                failures.append(failure(index, exc))
    else:
        with ProcessPoolExecutor(max_workers=processes) as pool:
            future_map = {pool.submit(_run_point, job): index for index, job in enumerate(jobs)}
            for future in as_completed(future_map):
                index = future_map[future]
                try:
                    run_id, summary = future.result()
                    results.append(success(index, run_id, summary))
                except Exception as exc:
                    failures.append(failure(index, exc))

    results.sort(key=lambda item: int(item["index"]))
    failures.sort(key=lambda item: int(item["index"]))
    aggregate = {
        "points": len(points),
        "completed": len(results),
        "failed": len(failures),
        "results": results,
        "failures": failures,
    }
    (output / "sweep-summary.json").write_text(
        json.dumps(aggregate, indent=2, sort_keys=True), encoding="utf-8"
    )
    return aggregate
