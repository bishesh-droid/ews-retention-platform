"""
Model Zoo — Multi-Model Factory
================================
Provides standardised model creation with default hyperparameters and
Optuna parameter search spaces for automated tuning.

Supported models:
  - Random Forest
  - XGBoost
  - LightGBM
  - CatBoost
  - Gradient Boosting
  - MLP (Multi-Layer Perceptron)

Usage
-----
    from models.model_zoo import ModelZoo
    zoo = ModelZoo(random_state=42)
    candidates = zoo.get_all_candidates()         # dict[name → model]
    space = zoo.get_param_space("xgboost", trial)  # Optuna trial params
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

# Optional imports — degrade gracefully
try:
    from lightgbm import LGBMClassifier
    LGBM_AVAILABLE = True
except ImportError:
    LGBM_AVAILABLE = False
    logger.warning("LightGBM not installed. LGBMClassifier will be unavailable.")

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    logger.warning("CatBoost not installed. CatBoostClassifier will be unavailable.")


class ModelZoo:
    """
    Factory for creating model candidates with sensible defaults
    and Optuna-compatible hyperparameter search spaces.
    """

    def __init__(self, random_state: int = 42, n_jobs: int = -1):
        self.random_state = random_state
        self.n_jobs = n_jobs

    # ── Default Model Instances ──────────────────────────────────────────

    def get_random_forest(self, **overrides) -> RandomForestClassifier:
        params = dict(
            n_estimators=300,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=3,
            max_features="sqrt",
            class_weight="balanced",
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )
        params.update(overrides)
        return RandomForestClassifier(**params)

    def get_xgboost(self, scale_pos_weight: float = 1.0, **overrides) -> XGBClassifier:
        params = dict(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            verbosity=0,
        )
        params.update(overrides)
        return XGBClassifier(**params)

    def get_lightgbm(self, scale_pos_weight: float = 1.0, **overrides):
        if not LGBM_AVAILABLE:
            raise ImportError("LightGBM is not installed. Install with: pip install lightgbm")
        params = dict(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_samples=20,
            num_leaves=31,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            verbose=-1,
        )
        params.update(overrides)
        return LGBMClassifier(**params)

    def get_catboost(self, class_weights: Optional[Dict] = None, **overrides):
        if not CATBOOST_AVAILABLE:
            raise ImportError("CatBoost is not installed. Install with: pip install catboost")
        params = dict(
            iterations=300,
            depth=6,
            learning_rate=0.05,
            l2_leaf_reg=3.0,
            random_seed=self.random_state,
            verbose=0,
            auto_class_weights="Balanced",
        )
        if class_weights:
            params["class_weights"] = class_weights
            params.pop("auto_class_weights", None)
        params.update(overrides)
        return CatBoostClassifier(**params)

    def get_gradient_boosting(self, **overrides) -> GradientBoostingClassifier:
        params = dict(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_split=5,
            min_samples_leaf=3,
            random_state=self.random_state,
        )
        params.update(overrides)
        return GradientBoostingClassifier(**params)

    def get_mlp(self, **overrides) -> MLPClassifier:
        params = dict(
            hidden_layer_sizes=(128, 64, 32),
            activation="relu",
            solver="adam",
            alpha=0.001,
            batch_size="auto",
            learning_rate="adaptive",
            learning_rate_init=0.001,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=15,
            random_state=self.random_state,
        )
        params.update(overrides)
        return MLPClassifier(**params)

    # ── Get All Candidates ───────────────────────────────────────────────

    def get_all_candidates(
        self,
        scale_pos_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Return a dictionary of all available model candidates.

        Parameters
        ----------
        scale_pos_weight : float
            Ratio of negative to positive samples for class imbalance.

        Returns
        -------
        dict[str, model]
            Keys are model names, values are unfitted estimators.
        """
        candidates = {
            "random_forest": self.get_random_forest(),
            "xgboost": self.get_xgboost(scale_pos_weight=scale_pos_weight),
            "gradient_boosting": self.get_gradient_boosting(),
            "mlp": self.get_mlp(),
        }

        if LGBM_AVAILABLE:
            candidates["lightgbm"] = self.get_lightgbm(scale_pos_weight=scale_pos_weight)

        if CATBOOST_AVAILABLE:
            candidates["catboost"] = self.get_catboost()

        logger.info(f"ModelZoo: {len(candidates)} candidates available: {list(candidates.keys())}")
        return candidates

    # ── Optuna Parameter Spaces ──────────────────────────────────────────

    @staticmethod
    def get_param_space(model_name: str, trial) -> Dict[str, Any]:
        """
        Return an Optuna-compatible parameter dict for the given model.

        Parameters
        ----------
        model_name : str
            One of: random_forest, xgboost, lightgbm, catboost,
                    gradient_boosting, mlp
        trial : optuna.Trial
            Optuna trial object for suggesting hyperparameters.

        Returns
        -------
        dict
            Hyperparameter dict that can be passed to the model constructor.
        """
        if model_name == "random_forest":
            return {
                "n_estimators": trial.suggest_int("rf_n_estimators", 100, 500, step=50),
                "max_depth": trial.suggest_int("rf_max_depth", 5, 25),
                "min_samples_split": trial.suggest_int("rf_min_samples_split", 2, 20),
                "min_samples_leaf": trial.suggest_int("rf_min_samples_leaf", 1, 10),
                "max_features": trial.suggest_categorical("rf_max_features", ["sqrt", "log2", None]),
            }

        elif model_name == "xgboost":
            return {
                "n_estimators": trial.suggest_int("xgb_n_estimators", 100, 500, step=50),
                "max_depth": trial.suggest_int("xgb_max_depth", 3, 12),
                "learning_rate": trial.suggest_float("xgb_learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("xgb_subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("xgb_colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("xgb_min_child_weight", 1, 10),
                "gamma": trial.suggest_float("xgb_gamma", 0.0, 0.5),
                "reg_alpha": trial.suggest_float("xgb_reg_alpha", 0.0, 1.0),
                "reg_lambda": trial.suggest_float("xgb_reg_lambda", 0.5, 2.0),
            }

        elif model_name == "lightgbm":
            return {
                "n_estimators": trial.suggest_int("lgbm_n_estimators", 100, 500, step=50),
                "max_depth": trial.suggest_int("lgbm_max_depth", 3, 15),
                "learning_rate": trial.suggest_float("lgbm_learning_rate", 0.01, 0.3, log=True),
                "num_leaves": trial.suggest_int("lgbm_num_leaves", 15, 63),
                "subsample": trial.suggest_float("lgbm_subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("lgbm_colsample_bytree", 0.6, 1.0),
                "min_child_samples": trial.suggest_int("lgbm_min_child_samples", 5, 50),
            }

        elif model_name == "catboost":
            return {
                "iterations": trial.suggest_int("cb_iterations", 100, 500, step=50),
                "depth": trial.suggest_int("cb_depth", 4, 10),
                "learning_rate": trial.suggest_float("cb_learning_rate", 0.01, 0.3, log=True),
                "l2_leaf_reg": trial.suggest_float("cb_l2_leaf_reg", 1.0, 10.0),
            }

        elif model_name == "gradient_boosting":
            return {
                "n_estimators": trial.suggest_int("gb_n_estimators", 100, 400, step=50),
                "max_depth": trial.suggest_int("gb_max_depth", 3, 10),
                "learning_rate": trial.suggest_float("gb_learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("gb_subsample", 0.6, 1.0),
                "min_samples_split": trial.suggest_int("gb_min_samples_split", 2, 20),
                "min_samples_leaf": trial.suggest_int("gb_min_samples_leaf", 1, 10),
            }

        elif model_name == "mlp":
            n_layers = trial.suggest_int("mlp_n_layers", 1, 3)
            layer_sizes = tuple(
                trial.suggest_int(f"mlp_layer_{i}", 32, 256, step=32)
                for i in range(n_layers)
            )
            return {
                "hidden_layer_sizes": layer_sizes,
                "alpha": trial.suggest_float("mlp_alpha", 1e-5, 1e-2, log=True),
                "learning_rate_init": trial.suggest_float("mlp_lr_init", 1e-4, 1e-2, log=True),
            }

        else:
            raise ValueError(f"Unknown model name: {model_name}")
