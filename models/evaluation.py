"""
Model Evaluation — Comprehensive Metrics & Visualisation
=========================================================
Produces structured evaluation reports with confusion matrices,
ROC curves, feature importance charts, and cross-validation scores.

Usage
-----
    from models.evaluation import ModelEvaluator
    evaluator = ModelEvaluator(output_dir="models/saved_models/evaluation")
    report = evaluator.evaluate(model, X_test, y_test, "xgboost")
    evaluator.compare_models(reports_dict)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate

logger = logging.getLogger(__name__)

# Plotting imports — optional, degrade gracefully
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logger.warning("matplotlib/seaborn not installed. Plots will be skipped.")


class ModelEvaluator:
    """
    Comprehensive model evaluation with metrics, plots, and comparison.
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        random_state: int = 42,
    ):
        self.output_dir = Path(
            output_dir or Path(__file__).resolve().parent / "saved_models" / "evaluation"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.random_state = random_state

    # ── Single Model Evaluation ──────────────────────────────────────────

    def evaluate(
        self,
        model,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_name: str,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run full evaluation for a single model.

        Returns
        -------
        dict with keys: model_name, metrics, confusion_matrix,
              classification_report, feature_importances
        """
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        # Core metrics
        metrics = {}
        if y_test.nunique() > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_test, y_prob))
        else:
            metrics["roc_auc"] = None

        metrics["f1_score"] = float(f1_score(y_test, y_pred, zero_division=0))
        metrics["precision"] = float(precision_score(y_test, y_pred, zero_division=0))
        metrics["recall"] = float(recall_score(y_test, y_pred, zero_division=0))
        metrics["accuracy"] = float(accuracy_score(y_test, y_pred))

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred).tolist()

        # Classification report
        cls_report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)

        # Feature importances
        feat_imp = None
        if hasattr(model, "feature_importances_") and feature_names:
            importances = model.feature_importances_
            feat_imp = sorted(
                [
                    {"feature": name, "importance": float(imp)}
                    for name, imp in zip(feature_names, importances)
                ],
                key=lambda x: x["importance"],
                reverse=True,
            )

        report = {
            "model_name": model_name,
            "metrics": metrics,
            "confusion_matrix": cm,
            "classification_report": cls_report,
            "feature_importances": feat_imp,
        }

        # Generate plots
        if PLOTTING_AVAILABLE:
            self._plot_confusion_matrix(cm, model_name)
            if metrics["roc_auc"] is not None:
                self._plot_roc_curve(y_test, y_prob, model_name, metrics["roc_auc"])
            if feat_imp:
                self._plot_feature_importance(feat_imp, model_name)

        logger.info(
            f"{model_name} — AUC={metrics.get('roc_auc')}, "
            f"F1={metrics['f1_score']:.3f}, "
            f"Recall={metrics['recall']:.3f}, "
            f"Precision={metrics['precision']:.3f}"
        )
        return report

    # ── Cross-Validation ─────────────────────────────────────────────────

    def cross_validate(
        self,
        model,
        X: pd.DataFrame,
        y: pd.Series,
        model_name: str,
        cv_folds: int = 5,
    ) -> Dict[str, float]:
        """
        Run stratified k-fold cross-validation.

        Returns dict with mean and std for each metric.
        """
        if y.nunique() < 2 or len(X) < cv_folds * 2:
            logger.warning(f"{model_name}: skipping CV (insufficient data)")
            return {}

        cv = StratifiedKFold(
            n_splits=cv_folds,
            shuffle=True,
            random_state=self.random_state,
        )
        scoring = ["roc_auc", "f1", "precision", "recall", "accuracy"]
        scores = cross_validate(
            model, X, y, cv=cv, scoring=scoring, return_train_score=False, n_jobs=-1
        )

        summary = {}
        for metric in scoring:
            key = f"test_{metric}"
            if key in scores:
                summary[f"cv_{metric}_mean"] = float(np.mean(scores[key]))
                summary[f"cv_{metric}_std"] = float(np.std(scores[key]))

        logger.info(
            f"{model_name} CV — "
            f"AUC={summary.get('cv_roc_auc_mean', 0):.3f}±{summary.get('cv_roc_auc_std', 0):.3f}, "
            f"F1={summary.get('cv_f1_mean', 0):.3f}"
        )
        return summary

    # ── Multi-Model Comparison ───────────────────────────────────────────

    def compare_models(
        self,
        reports: Dict[str, Dict],
    ) -> pd.DataFrame:
        """
        Create a comparison table of all evaluated models.

        Parameters
        ----------
        reports : dict[model_name → evaluation report]

        Returns
        -------
        pd.DataFrame with one row per model, sorted by ROC-AUC.
        """
        rows = []
        for name, report in reports.items():
            m = report.get("metrics", {})
            rows.append({
                "model": name,
                "roc_auc": m.get("roc_auc"),
                "f1_score": m.get("f1_score"),
                "precision": m.get("precision"),
                "recall": m.get("recall"),
                "accuracy": m.get("accuracy"),
            })

        df = pd.DataFrame(rows).sort_values("roc_auc", ascending=False, na_position="last")

        # Save comparison
        comparison_path = self.output_dir / "model_comparison.csv"
        df.to_csv(comparison_path, index=False)

        comparison_json = self.output_dir / "model_comparison.json"
        df.to_json(comparison_json, orient="records", indent=2)

        logger.info(f"Model comparison saved → {comparison_path}")

        if PLOTTING_AVAILABLE:
            self._plot_model_comparison(df)

        return df

    # ── Plotting ─────────────────────────────────────────────────────────

    def _plot_confusion_matrix(self, cm: list, model_name: str):
        fig, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(
            cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["Retained", "At-Risk"],
            yticklabels=["Retained", "At-Risk"],
            ax=ax,
        )
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(f"Confusion Matrix — {model_name}")
        path = self.output_dir / f"confusion_matrix_{model_name}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        logger.info(f"Confusion matrix plot → {path}")

    def _plot_roc_curve(self, y_true, y_prob, model_name: str, auc_score: float):
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.plot(fpr, tpr, label=f"{model_name} (AUC = {auc_score:.3f})", linewidth=2)
        ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random")
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title(f"ROC Curve — {model_name}")
        ax.legend(loc="lower right")
        ax.grid(alpha=0.3)
        path = self.output_dir / f"roc_curve_{model_name}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        logger.info(f"ROC curve plot → {path}")

    def _plot_feature_importance(self, feat_imp: list, model_name: str, top_n: int = 20):
        top = feat_imp[:top_n]
        features = [f["feature"] for f in top]
        values = [f["importance"] for f in top]

        fig, ax = plt.subplots(figsize=(8, max(4, len(features) * 0.35)))
        ax.barh(features[::-1], values[::-1], color="steelblue")
        ax.set_xlabel("Importance")
        ax.set_title(f"Feature Importance — {model_name} (Top {top_n})")
        ax.grid(axis="x", alpha=0.3)
        path = self.output_dir / f"feature_importance_{model_name}.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        logger.info(f"Feature importance plot → {path}")

    def _plot_model_comparison(self, df: pd.DataFrame):
        metrics_to_plot = ["roc_auc", "f1_score", "precision", "recall"]
        available = [m for m in metrics_to_plot if m in df.columns]

        if not available:
            return

        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(df))
        width = 0.18

        for i, metric in enumerate(available):
            values = df[metric].fillna(0).values
            ax.bar(x + i * width, values, width, label=metric)

        ax.set_xlabel("Model")
        ax.set_ylabel("Score")
        ax.set_title("Model Comparison")
        ax.set_xticks(x + width * (len(available) - 1) / 2)
        ax.set_xticklabels(df["model"].values, rotation=30, ha="right")
        ax.legend()
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
        path = self.output_dir / "model_comparison.png"
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        logger.info(f"Model comparison plot → {path}")

    # ── Save full report ─────────────────────────────────────────────────

    def save_report(
        self,
        reports: Dict[str, Dict],
        cv_reports: Optional[Dict[str, Dict]] = None,
        ensemble_meta: Optional[Dict] = None,
        filename: str = "evaluation_report.json",
    ) -> Path:
        """Save the full evaluation report to JSON."""
        full_report = {
            "individual_models": {},
            "ensemble": ensemble_meta,
        }

        for name, report in reports.items():
            entry = {
                "metrics": report.get("metrics", {}),
                "confusion_matrix": report.get("confusion_matrix"),
            }
            if cv_reports and name in cv_reports:
                entry["cross_validation"] = cv_reports[name]
            if report.get("feature_importances"):
                entry["top_features"] = report["feature_importances"][:10]
            full_report["individual_models"][name] = entry

        path = self.output_dir / filename
        with open(path, "w") as f:
            json.dump(full_report, f, indent=2, default=str)

        logger.info(f"Full evaluation report saved → {path}")
        return path
