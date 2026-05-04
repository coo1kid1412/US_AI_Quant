"""MLflow experiment management wrapper for Qlib workflows.

Provides a lightweight interface on top of Qlib's R (Recorder) and MLflow
for unified experiment logging, comparison, and best-run retrieval.

Usage:
    from research.workflow.experiment_manager import ExperimentManager

    em = ExperimentManager()
    em.log_run("lgbm_baseline", params={...}, metrics={...}, artifacts=[...])
    df = em.compare_experiments(["lgbm_baseline", "lgbm_enhanced"])
    best = em.get_best_run("IC_mean", experiment_name="lgbm_baseline")
"""

import json
import logging
from pathlib import Path

import mlflow
import pandas as pd

logger = logging.getLogger(__name__)

# Default tracking URI - use sqlite to avoid MLflow file store deprecation
DEFAULT_TRACKING_URI = "sqlite:///mlruns.db"


class ExperimentManager:
    """Manage MLflow experiments for the US Alpha Pipeline.

    Parameters
    ----------
    tracking_uri : str
        MLflow tracking URI. Defaults to sqlite:///mlruns.db in project root.
    """

    def __init__(self, tracking_uri: str | None = None):
        self.tracking_uri = tracking_uri or DEFAULT_TRACKING_URI
        mlflow.set_tracking_uri(self.tracking_uri)
        logger.info("ExperimentManager initialized: %s", self.tracking_uri)

    def log_run(
        self,
        experiment_name: str,
        params: dict | None = None,
        metrics: dict | None = None,
        artifacts: list[str] | None = None,
        tags: dict | None = None,
        run_name: str | None = None,
    ) -> str:
        """Log a complete experiment run to MLflow.

        Parameters
        ----------
        experiment_name : str
            Experiment name (created if not exists).
        params : dict, optional
            Hyperparameters to log.
        metrics : dict, optional
            Metrics to log (must be numeric).
        artifacts : list[str], optional
            List of file paths to log as artifacts.
        tags : dict, optional
            Tags to attach to the run.
        run_name : str, optional
            Display name for this run.

        Returns
        -------
        str
            The MLflow run ID.
        """
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name=run_name) as run:
            if params:
                # MLflow params must be strings; flatten nested dicts
                flat_params = self._flatten_dict(params)
                mlflow.log_params(flat_params)

            if metrics:
                mlflow.log_metrics(metrics)

            if artifacts:
                for path in artifacts:
                    if Path(path).exists():
                        mlflow.log_artifact(path)
                    else:
                        logger.warning("Artifact not found, skipping: %s", path)

            if tags:
                mlflow.set_tags(tags)

            run_id = run.info.run_id
            logger.info(
                "Logged run %s to experiment '%s' (metrics: %d, params: %d)",
                run_id[:8],
                experiment_name,
                len(metrics or {}),
                len(params or {}),
            )
            return run_id

    def compare_experiments(
        self,
        experiment_names: list[str],
        metric_keys: list[str] | None = None,
    ) -> pd.DataFrame:
        """Compare runs across experiments side by side.

        Parameters
        ----------
        experiment_names : list[str]
            Experiment names to compare.
        metric_keys : list[str], optional
            Specific metrics to include. If None, includes all.

        Returns
        -------
        pd.DataFrame
            Comparison table with one row per run.
        """
        all_runs = []
        for name in experiment_names:
            try:
                runs_df = mlflow.search_runs(
                    experiment_names=[name],
                    order_by=["start_time DESC"],
                )
                if not runs_df.empty:
                    runs_df["experiment_name"] = name
                    all_runs.append(runs_df)
            except Exception as e:
                logger.warning("Could not load experiment '%s': %s", name, e)

        if not all_runs:
            return pd.DataFrame()

        df = pd.concat(all_runs, ignore_index=True)

        # Select relevant columns
        meta_cols = ["experiment_name", "run_id", "start_time", "status"]
        metric_cols = [c for c in df.columns if c.startswith("metrics.")]
        param_cols = [c for c in df.columns if c.startswith("params.")]

        if metric_keys:
            metric_cols = [
                c for c in metric_cols
                if c.replace("metrics.", "") in metric_keys
            ]

        keep_cols = [c for c in meta_cols if c in df.columns] + metric_cols + param_cols
        return df[keep_cols]

    def get_best_run(
        self,
        metric: str,
        experiment_name: str | None = None,
        higher_is_better: bool = True,
    ) -> dict | None:
        """Get the best run by a specific metric.

        Parameters
        ----------
        metric : str
            Metric name (without "metrics." prefix).
        experiment_name : str, optional
            Limit search to this experiment. If None, searches all.
        higher_is_better : bool
            If True, returns run with highest metric value.

        Returns
        -------
        dict or None
            Dict with run_id, metrics, params, or None if no runs found.
        """
        order = "DESC" if higher_is_better else "ASC"
        exp_names = [experiment_name] if experiment_name else None

        try:
            runs_df = mlflow.search_runs(
                experiment_names=exp_names,
                search_all_experiments=(exp_names is None),
                order_by=[f"metrics.{metric} {order}"],
                max_results=1,
            )
        except Exception as e:
            logger.error("Failed to search runs: %s", e)
            return None

        if runs_df.empty:
            return None

        row = runs_df.iloc[0]
        result = {
            "run_id": row["run_id"],
            "experiment_name": experiment_name or row.get("experiment_id", "unknown"),
            "metrics": {
                c.replace("metrics.", ""): row[c]
                for c in runs_df.columns
                if c.startswith("metrics.") and pd.notna(row[c])
            },
            "params": {
                c.replace("params.", ""): row[c]
                for c in runs_df.columns
                if c.startswith("params.") and pd.notna(row[c])
            },
        }
        return result

    def list_experiments(self) -> list[str]:
        """List all experiment names."""
        client = mlflow.MlflowClient()
        experiments = client.search_experiments()
        return [exp.name for exp in experiments if exp.name != "Default"]

    def get_run_artifacts(self, run_id: str) -> list[str]:
        """List artifact paths for a run."""
        client = mlflow.MlflowClient()
        artifacts = client.list_artifacts(run_id)
        return [a.path for a in artifacts]

    @staticmethod
    def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
        """Flatten nested dict for MLflow param logging."""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(ExperimentManager._flatten_dict(v, new_key, sep))
            else:
                items[new_key] = str(v)
        return items


def save_results_json(results: dict, output_path: str | Path) -> None:
    """Save evaluation results as JSON with proper serialization."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {}
    for k, v in results.items():
        if isinstance(v, (int, float, str, bool, list, dict, type(None))):
            serializable[k] = v
        else:
            serializable[k] = str(v)
    with open(output_path, "w") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
