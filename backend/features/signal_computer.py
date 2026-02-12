"""
Base class for signal computation with weighted averaging
"""
from typing import Dict, Optional
import pandas as pd


class SignalComputer:
    """Base class for computing risk signals"""
    
    def __init__(self, weights: Dict[str, float]):
        self.weights = weights
        self.normalize_weights()
    
    def normalize_weights(self):
        """Ensure weights sum to 1.0"""
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v/total for k, v in self.weights.items()}
    
    def compute_weighted_score(self, metrics: Dict[str, Optional[float]]) -> Optional[float]:
        """
        Compute weighted average, handle NULLs
        
        Args:
            metrics: Dict of metric_name -> value (None if missing)
            
        Returns:
            Weighted score 0-100, or None if no valid data
        """
        # Filter out None values
        valid_metrics = {k: v for k, v in metrics.items() if v is not None}
        
        if not valid_metrics:
            return None  # No data → NULL score
        
        # Renormalize weights for available metrics only
        available_weight = sum(self.weights.get(k, 0) for k in valid_metrics.keys())
        
        if available_weight == 0:
            return None
        
        normalized_weights = {k: self.weights.get(k, 0) / available_weight 
                             for k in valid_metrics.keys()}
        
        score = sum(normalized_weights[k] * valid_metrics[k] 
                   for k in valid_metrics.keys())
        
        # Clamp to 0-100
        return max(0.0, min(100.0, score))
