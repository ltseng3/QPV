"""QOrchSim command-line interface."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import typer

from qorchsim.config.loader import load_config
from qorchsim.config.normalization import normalized_dict
from qorchsim.config.validation import validate_execution_horizon
from qorchsim.errors import QOrchSimError
from qorchsim.experiments.runner import run_experiment
from qorchsim.experiments.summary import summarize_run
from qorchsim.experiments.sweep import run_sweep

app = typer.Typer(help="Quantum orchestration and QPV security simulator.", no_args_is_help=True)


@app.command()
def validate(config: Path) -> None:
    """Validate schema and execution horizon without running a simulation."""
    try:
        loaded = load_config(config)
        validate_execution_horizon(loaded)
        typer.echo(json.dumps(normalized_dict(loaded), indent=2, sort_keys=True))
        typer.secho("Configuration is valid.", fg=typer.colors.GREEN)
    except QOrchSimError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc


@app.command()
def run(
    config: Path,
    output: Path | None = typer.Option(None, "--output", "-o"),
    seed: int | None = typer.Option(None, "--seed"),
) -> None:
    """Execute one deterministic simulation run."""
    try:
        artifacts = run_experiment(load_config(config), output_directory=output, seed_override=seed)
        typer.echo(f"run_id={artifacts.run_id}")
        typer.echo(f"output={artifacts.output_directory}")
        typer.echo(json.dumps(artifacts.summary, indent=2, sort_keys=True))
    except Exception as exc:
        typer.secho(f"{type(exc).__name__}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@app.command()
def sweep(
    sweep_config: Path,
    output: Path = typer.Option(Path("runs/sweep"), "--output", "-o"),
    processes: int = typer.Option(1, "--processes", "-p", min=1),
) -> None:
    """Run a Cartesian parameter sweep using process-based parallelism."""
    result = run_sweep(sweep_config, output, processes)
    typer.echo(json.dumps(result, indent=2, sort_keys=True))
    if result["failed"]:
        raise typer.Exit(1)


@app.command()
def summarize(run_dir: Path) -> None:
    """Regenerate a compact summary from persisted round data."""
    typer.echo(json.dumps(summarize_run(run_dir), indent=2, sort_keys=True))


@app.command()
def inspect(
    run_dir: Path,
    round_id: str = typer.Option(..., "--round"),
) -> None:
    """Print one round result and its chronological trace."""
    rounds_path = run_dir / "rounds.csv"
    with rounds_path.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["round_id"] == round_id]
    if not rows:
        typer.secho(f"round not found: {round_id}", fg=typer.colors.RED, err=True)
        raise typer.Exit(2)
    typer.echo("ROUND RESULT")
    typer.echo(json.dumps(rows[0], indent=2, sort_keys=True))
    events_path = run_dir / "events.ndjson"
    if events_path.exists():
        typer.echo("\nEVENT TRACE")
        for line in events_path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("round_id") == round_id:
                typer.echo(
                    f"{event['physical_time_ps']:>16}  {event['phase']:<20} "
                    f"{event['node_id'] or '-':<12} {event['event_type']}"
                )


if __name__ == "__main__":
    app()
