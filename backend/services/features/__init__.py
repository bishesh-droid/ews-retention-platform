"""
Feature Engineering Package
----------------------------
Modular feature extraction system organized by domain.

Usage:
    from backend.services.features import FeatureEngineer

    engineer = FeatureEngineer(registry_lookup=optional_func)
    features = engineer.get_features(student_id, db)

Domains:
    - Academic: Graded performance, exam scores, academic flags
    - Engagement: LMS activity, content completion, time investment
    - Consistency: Login patterns, ghost detection, behavioral trends
    - Intent: Engagement pattern classification, motivation signals
"""

from .academic import AcademicFeatureExtractor, AcademicFeatures
from .engagement import EngagementFeatureExtractor, EngagementFeatures
from .consistency import ConsistencyFeatureExtractor, ConsistencyFeatures
from .intent import IntentFeatureExtractor, IntentFeatures
from .composer import FeatureEngineer

__all__ = [
    # Composer (public interface)
    "FeatureEngineer",
    # Extractors
    "AcademicFeatureExtractor",
    "EngagementFeatureExtractor",
    "ConsistencyFeatureExtractor",
    "IntentFeatureExtractor",
    # Dataclasses
    "AcademicFeatures",
    "EngagementFeatures",
    "ConsistencyFeatures",
    "IntentFeatures",
]
