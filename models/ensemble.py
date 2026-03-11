"""
Weighted Voting Ensemble — Production Grade
============================================
Combines multiple trained classifiers using soft voting with
performance-based weights (ROC-AUC on validation set).

Usage
-----
    from models.ensemble import WeightedVotingEnsemble
    ensemble = WeightedVotingEnsemble()
    ensemble.fit(models_dict, X_val, y_val)
    proba = ensemble.predict_proba(X_new)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

logger = logging.getLogger(__name__)


class WeightedVotingEnsemble:
    """
    Soft voting ensemble with weights derived from validation AUC scores.

    The ensemble probability for class 1 is:
        p = sum(w_i * p_i) / sum(w_i)
    where w_i = AUC_i^power (power controls how aggressively better models
    are weighted).

    Implements predict_proba() and predict() to match the sklearn interface.
    """

    def __init__(self, power: float = 2.0, threshold: float = 0.5):
        """
        Parameters
        ----------
        power : float
            Exponent applied to AUC scores to compute weights.
            Higher = more weight on best models.
        threshold : float
            Classification threshold for predict().
        """
        self.power = power
        self.threshold = threshold
        self._models: Dict[str, Any] = {}
        self._weights: Dict[str, float] = {}
        self._auc_scores: Dict[str, float] = {}
        self._fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def fit(
        self,
        models: Dict[str, Any],
        X_val: pd.DataFrame,
        y_val: pd.Series,
        top_n: Optional[int] = None,
    ) -> "WeightedVotingEnsemble":
        """
        Compute ensemble weights from validation performance.

        Parameters
        ----------
        models : dict[str, estimator]
            Dictionary of model_name → fitted model.
        X_val : pd.DataFrame
            Validation feature matrix.
        y_val : pd.Series
            Validation target.
        top_n : int, optional
            If set, only keep the top_n models by AUC.
        """
        auc_scores: Dict[str, float] = {}

        for name, model in models.items():
            try:
                y_prob = model.predict_proba(X_val)[:, 1]
                auc = float(roc_auc_score(y_val, y_prob))
                auc_scores[name] = auc
                logger.info(f"  Ensemble candidate '{name}': AUC = {auc:.4f}")
            except Exception as exc:
                logger.warning(f"  Ensemble candidate '{name}' failed: {exc} — excluded")

        if not auc_scores:
            raise ValueError("No models produced valid AUC scores. Cannot build ensemble.")

        # Select top N if requested
        if top_n is not None and top_n < len(auc_scores):
            sorted_models = sorted(auc_scores.items(), key=lambda x: x[1], reverse=True)
            selected = dict(sorted_models[:top_n])
            logger.info(
                f"Ensemble: selected top-{top_n} models: "
                f"{list(selected.keys())} from {list(auc_scores.keys())}"
            )
            auc_scores = selected

        # Compute weights: w_i = AUC_i^power
        raw_weights = {name: auc ** self.power for name, auc in auc_scores.items()}
        total_weight = sum(raw_weights.values())
        normalised_weights = {name: w / total_weight for name, w in raw_weights.items()}

        self._models = {name: models[name] for name in auc_scores}
        self._weights = normalised_weights
        self._auc_scores = auc_scores
        self._fitted = True

        logger.info("Ensemble weights:")
        for name, weight in sorted(normalised_weights.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {name}: weight={weight:.4f} (AUC={auc_scores[name]:.4f})")

        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Weighted average of predicted probabilities.

        Returns
        -------
        np.ndarray, shape (n_samples, 2)
            Column 0 = P(class 0), Column 1 = P(class 1).
        """
        if not self._fitted:
            raise RuntimeError("Ensemble not fitted. Call fit() first.")

        n_samples = len(X)
        weighted_proba = np.zeros(n_samples)

        for name, model in self._models.items():
            weight = self._weights[name]
            try:
                proba = model.predict_proba(X)[:, 1]
                weighted_proba += weight * proba
            except Exception as exc:
                logger.warning(f"Model '{name}' predict_proba failed in ensemble: {exc}")

        # Stack into (n_samples, 2) format
        proba_2d = np.column_stack([1 - weighted_proba, weighted_proba])
        return proba_2d

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Binary prediction using the ensemble threshold."""
        proba = self.predict_proba(X)[:, 1]
        return (proba >= self.threshold).astype(int)

    # ── Accessors ────────────────────────────────────────────────────────

    def get_weights(self) -> Dict[str, float]:
        """Return normalised ensemble weights."""
        return self._weights.copy()

    def get_auc_scores(self) -> Dict[str, float]:
        """Return individual model AUC scores."""
        return self._auc_scores.copy()

    def get_model_names(self) -> List[str]:
        """Return names of models in the ensemble."""
        return list(self._models.keys())

    def get_model(self, name: str):
        """Return a single model from the ensemble by name."""
        return self._models.get(name)

    def get_metadata(self) -> Dict:
        """Return serialisable metadata about the ensemble."""
        return {
            "n_models": len(self._models),
            "model_names": list(self._models.keys()),
            "weights": {k: round(v, 6) for k, v in self._weights.items()},
            "auc_scores": {k: round(v, 6) for k, v in self._auc_scores.items()},
            "power": self.power,
            "threshold": self.threshold,
        }

    @property
    def feature_importances_(self) -> Optional[np.ndarray]:
        """
        Weighted average of feature importances across ensemble members.
        Only includes models that have feature_importances_ attribute.
        """
        importances_list = []
        weights_list = []

        for name, model in self._models.items():
            if hasattr(model, "feature_importances_"):
                importances_list.append(model.feature_importances_)
                weights_list.append(self._weights[name])

        if not importances_list:
            return None

        total_w = sum(weights_list)
        weighted_imp = np.zeros_like(importances_list[0])
        for imp, w in zip(importances_list, weights_list):
            weighted_imp += (w / total_w) * imp

        return weighted_imp
