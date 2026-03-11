"""
Hyperparameter Tuning — Optuna-based Optimisation
==================================================
Automated hyperparameter tuning using Optuna with StratifiedKFold
cross-validation.  Optimises for ROC-AUC by default, with F1 and
Recall tracked as secondary metrics.

Usage
-----
    from models.hyperparameter_tuning import HyperparameterTuner
    tuner = HyperparameterTuner(n_trials=50, cv_folds=5)
    best_params = tuner.tune("xgboost", X_train, y_train)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score

logger = logging.getLogger(__name__)

# Optional import — degrade gracefully
try:
    import optuna
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
    # Suppress Optuna's verbose trial logs
    optuna.logging.set_verbosity(optuna.logging.WARNING)
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("Optuna not installed. Hyperparameter tuning will use defaults.")


class HyperparameterTuner:
    """
    Optuna-based hyperparameter optimiser for any model in ModelZoo.
    """

    def __init__(
        self,
        n_trials: int = 50,
        cv_folds: int = 5,
        scoring: str = "roc_auc",
        random_state: int = 42,
        timeout: Optional[int] = None,
    ):
        """
        Parameters
        ----------
        n_trials : int
            Number of Optuna trials.
        cv_folds : int
            Number of StratifiedKFold splits.
        scoring : str
            Sklearn scoring metric name (e.g. 'roc_auc', 'f1', 'recall').
        random_state : int
            Random seed for CV splits.
        timeout : int, optional
            Maximum total seconds for tuning. None = unlimited.
        """
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.scoring = scoring
        self.random_state = random_state
        self.timeout = timeout
        self._best_params: Dict[str, Dict] = {}
        self._best_scores: Dict[str, float] = {}

    def tune(
        self,
        model_name: str,
        X_train: np.ndarray,
        y_train: np.ndarray,
        scale_pos_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Run hyperparameter tuning for a single model.

        Parameters
        ----------
        model_name : str
            Model key (e.g. 'xgboost', 'random_forest', 'lightgbm',
            'catboost', 'gradient_boosting', 'mlp').
        X_train : array-like
            Training features.
        y_train : array-like
            Training labels.
        scale_pos_weight : float
            Class imbalance ratio for models that support it.

        Returns
        -------
        dict
            Best hyperparameters found.
        """
        if not OPTUNA_AVAILABLE:
            logger.warning(
                f"Optuna not available. Returning default params for {model_name}."
            )
            return {}

        from models.model_zoo import ModelZoo

        zoo = ModelZoo(random_state=self.random_state)
        cv = StratifiedKFold(
            n_splits=self.cv_folds,
            shuffle=True,
            random_state=self.random_state,
        )

        def objective(trial):
            # Get suggested parameters from ModelZoo
            params = ModelZoo.get_param_space(model_name, trial)

            # Create model with suggested parameters
            model = _create_model(
                zoo, model_name, params, scale_pos_weight, self.random_state
            )

            try:
                scores = cross_val_score(
                    model, X_train, y_train,
                    cv=cv, scoring=self.scoring, n_jobs=-1,
                )
                return float(np.mean(scores))
            except Exception as exc:
                logger.warning(f"Trial failed for {model_name}: {exc}")
                return 0.0

        study = optuna.create_study(
            direction="maximize",
            sampler=TPESampler(seed=self.random_state),
            study_name=f"tune_{model_name}",
        )

        logger.info(
            f"Tuning {model_name}: {self.n_trials} trials, "
            f"{self.cv_folds}-fold CV, metric={self.scoring}"
        )

        study.optimize(
            objective,
            n_trials=self.n_trials,
            timeout=self.timeout,
            show_progress_bar=False,
        )

        best_params = study.best_params
        best_score = study.best_value

        # Clean up Optuna prefixed param names
        clean_params = _clean_param_names(model_name, best_params)

        self._best_params[model_name] = clean_params
        self._best_scores[model_name] = best_score

        logger.info(
            f"Best {model_name}: {self.scoring}={best_score:.4f}, params={clean_params}"
        )
        return clean_params

    def tune_all(
        self,
        model_names: list,
        X_train: np.ndarray,
        y_train: np.ndarray,
        scale_pos_weight: float = 1.0,
    ) -> Dict[str, Dict]:
        """
        Tune all specified models.

        Returns
        -------
        dict[model_name → best_params]
        """
        all_params = {}
        for name in model_names:
            try:
                params = self.tune(name, X_train, y_train, scale_pos_weight)
                all_params[name] = params
            except Exception as exc:
                logger.error(f"Tuning failed for {name}: {exc}")
                all_params[name] = {}
        return all_params

    def get_best_params(self) -> Dict[str, Dict]:
        return self._best_params.copy()

    def get_best_scores(self) -> Dict[str, float]:
        return self._best_scores.copy()


# ── Helpers ──────────────────────────────────────────────────────────────────

_PREFIX_MAP = {
    "random_forest": "rf_",
    "xgboost": "xgb_",
    "lightgbm": "lgbm_",
    "catboost": "cb_",
    "gradient_boosting": "gb_",
    "mlp": "mlp_",
}


def _clean_param_names(model_name: str, params: Dict) -> Dict:
    """Remove Optuna-style prefixes from parameter names."""
    prefix = _PREFIX_MAP.get(model_name, "")
    cleaned = {}
    for key, value in params.items():
        clean_key = key.replace(prefix, "") if prefix and key.startswith(prefix) else key
        cleaned[clean_key] = value

    # Handle MLP special case: reconstruct hidden_layer_sizes from layer_0, layer_1, ...
    if model_name == "mlp":
        layer_keys = sorted([k for k in cleaned if k.startswith("layer_")])
        if layer_keys:
            layers = tuple(cleaned.pop(k) for k in layer_keys)
            cleaned["hidden_layer_sizes"] = layers
        cleaned.pop("n_layers", None)

    return cleaned


def _create_model(
    zoo,
    model_name: str,
    params: Dict,
    scale_pos_weight: float,
    random_state: int,
):
    """Create a model instance from ModelZoo with given parameters."""
    if model_name == "random_forest":
        return zoo.get_random_forest(**params)
    elif model_name == "xgboost":
        return zoo.get_xgboost(scale_pos_weight=scale_pos_weight, **params)
    elif model_name == "lightgbm":
        return zoo.get_lightgbm(scale_pos_weight=scale_pos_weight, **params)
    elif model_name == "catboost":
        return zoo.get_catboost(**params)
    elif model_name == "gradient_boosting":
        return zoo.get_gradient_boosting(**params)
    elif model_name == "mlp":
        return zoo.get_mlp(**params)
    else:
        raise ValueError(f"Unknown model: {model_name}")
