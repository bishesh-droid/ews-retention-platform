"""
Hallucination Prevention \u0026 Response Validation
------------------------------------------------
Ensures LLM responses are grounded in real data and don't fabricate information.
"""

from typing import Dict, Any, List, Set
import re
from sqlalchemy.orm import Session


class HallucinationPrevention:
    """
    Validates LLM responses against actual data to prevent hallucinations.
    """

    def __init__(self, db: Session):
        self.db = db

    def validate_response(
        self,
        llm_response: str,
        allowed_data_sources: Dict[str, Any],
        confidence_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Validate LLM response against allowed data sources.

        Args:
            llm_response: The LLM-generated response text
            allowed_data_sources: Dict of data the LLM had access to
            confidence_threshold: Minimum confidence to pass validation

        Returns:
            Dictionary with validation results and confidence score
        """
        validation_result: Dict[str, Any] = {
            "is_valid": True,
            "confidence": 1.0,
            "issues": [],
            "warnings": [],
        }

        # Check 1: Verify no fabricated student IDs
        student_ids_in_response = self._extract_student_ids(llm_response)
        allowed_student_ids = self._get_allowed_student_ids(allowed_data_sources)

        fabricated_ids = student_ids_in_response - allowed_student_ids
        if fabricated_ids:
            validation_result["is_valid"] = False
            validation_result["confidence"] = 0.0
            validation_result["issues"].append(
                f"Response references student IDs not in source data: {fabricated_ids}"
            )

        # Check 2: Verify numerical claims
        numbers_in_response = self._extract_numbers(llm_response)
        if not self._verify_numbers_plausible(
            numbers_in_response, allowed_data_sources
        ):
            validation_result["confidence"] *= 0.7
            validation_result["warnings"].append(
                "Response contains numerical values that may not align with source data"
            )

        # Check 3: Check for hedge words that indicate uncertainty
        uncertainty_indicators = ["might", "could", "possibly", "perhaps", "maybe"]
        hedge_count = sum(
            1 for word in uncertainty_indicators if word in llm_response.lower()
        )

        if hedge_count > 2:
            validation_result["confidence"] *= 0.75
            validation_result["warnings"].append(
                f"Response contains {hedge_count} uncertainty indicators - may be speculative"
            )

        # Check 4: Ensure response doesn't claim unavailable data
        unavailable_phrases = [
            "based on future predictions",
            "in next semester",
            "will definitely",
            "guaranteed to",
        ]

        for phrase in unavailable_phrases:
            if phrase in llm_response.lower():
                validation_result["confidence"] *= 0.5
                validation_result["warnings"].append(
                    f"Response makes claims about unavailable data: '{phrase}'"
                )

        # Final validation
        if validation_result["confidence"] < confidence_threshold:
            validation_result["is_valid"] = False

        return validation_result

    def _extract_student_ids(self, text: str) -> Set[str]:
        """Extract potential student IDs from text."""
        # Look for patterns like "student 1234" or "ID: 1234"
        pattern = r"(?:student|id)[:\s]+(\d{3,6})"
        matches = re.findall(pattern, text.lower())
        return set(matches)

    def _get_allowed_student_ids(self, data_sources: Dict[str, Any]) -> Set[str]:
        """Get set of student IDs that were in the allowed data."""
        allowed_ids = set()

        # Extract from various data source structures
        if "student_data" in data_sources:
            if isinstance(data_sources["student_data"], dict):
                if "id" in data_sources["student_data"]:
                    allowed_ids.add(str(data_sources["student_data"]["id"]))
            elif isinstance(data_sources["student_data"], list):
                for student in data_sources["student_data"]:
                    if "id" in student:
                        allowed_ids.add(str(student["id"]))

        if "students" in data_sources:
            for student in data_sources.get("students", []):
                if "id" in student:
                    allowed_ids.add(str(student["id"]))

        return allowed_ids

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract numerical values from text."""
        # Find numbers (including percentages and decimals)
        pattern = r"\b\d+\.?\d*%?\b"
        numbers = re.findall(pattern, text)

        # Convert to float, removing % if present
        return [float(n.replace("%", "")) for n in numbers]

    def _verify_numbers_plausible(
        self, numbers: List[float], data_sources: Dict[str, Any]
    ) -> bool:
        """
        Check if numbers in response are plausible given source data.
        Returns True if plausible, False if suspicious.
        """
        # Extract numbers from source data
        source_numbers = self._extract_numbers_from_data(data_sources)

        if not source_numbers:
            return True  # No baseline to compare

        # Check for numbers that are way outside the range of source data
        min_source = min(source_numbers)
        max_source = max(source_numbers)

        for num in numbers:
            # Allow reasonable extrapolation (e.g., percentages 0-100)
            if num < 0 or num > 100:
                # If it's not a percentage, check against source range
                if num < min_source * 0.5 or num > max_source * 2:
                    return False

        return True

    def _extract_numbers_from_data(self, data: Any) -> List[float]:
        """Recursively extract all numbers from data structure."""
        numbers = []

        if isinstance(data, dict):
            for value in data.values():
                numbers.extend(self._extract_numbers_from_data(value))
        elif isinstance(data, list):
            for item in data:
                numbers.extend(self._extract_numbers_from_data(item))
        elif isinstance(data, (int, float)):
            numbers.append(float(data))
        elif isinstance(data, str):
            try:
                numbers.append(float(data))
            except ValueError:
                pass

        return numbers


class ContentFilter:
    """
    Filters inappropriate or harmful content from LLM responses.
    """

    # Inappropriate phrases that should not appear in educational context
    BLOCKED_PHRASES = [
        "you should drop out",
        "you're going to fail",
        "hopeless",
        "worthless",
        "stupid",
    ]

    # Sensitive topics that need careful handling (topic -> category mapping)
    SENSITIVE_TOPICS = {
        "mental health": "mental health",
        "depression": "mental health",
        "anxiety": "mental health",
        "suicide": "mental health",
        "self-harm": "mental health",
    }

    @staticmethod
    def check_content(response: str) -> Dict[str, Any]:
        """
        Check if response contains inappropriate content.

        Returns:
            Dict with 'is_appropriate', 'issues', and 'needs_escalation' flags
        """
        result: Dict[str, Any] = {
            "is_appropriate": True,
            "issues": [],
            "needs_escalation": False,
            "filtered_response": response,
        }

        response_lower = response.lower()

        # Check for blocked phrases
        for phrase in ContentFilter.BLOCKED_PHRASES:
            if phrase in response_lower:
                result["is_appropriate"] = False
                result["issues"].append(f"Contains inappropriate phrase: '{phrase}'")

        # Check for sensitive topics (flag but don't block)
        for topic, category in ContentFilter.SENSITIVE_TOPICS.items():
            if topic in response_lower:
                result["needs_escalation"] = True
                result["issues"].append(
                    f"Contains sensitive topic '{category}' - human review recommended"
                )

        # If inappropriate, replace with safe message
        if not result["is_appropriate"]:
            result["filtered_response"] = (
                "I'm sorry, but I can't provide that response. "
                "Please contact a counselor or advisor for personalized support."
            )

        return result

    @staticmethod
    def add_safety_disclaimer(response: str, topic: str) -> str:
        """Add appropriate disclaimer for sensitive topics."""
        disclaimers = {
            "mental health": (
                "\n\n⚠️ If you're experiencing mental health concerns, please reach out to "
                "campus counseling services or call the national hotline: 988."
            ),
            "financial": (
                "\n\n💡 For specific financial advice, please consult with financial aid office."
            ),
            "medical": (
                "\n\n🏥 This is not medical advice. Please consult healthcare professionals."
            ),
        }

        disclaimer = disclaimers.get(topic, "")
        return response + disclaimer


class ConfidenceScorer:
    """
    Calculates confidence scores for LLM responses based on data quality.
    """

    @staticmethod
    def calculate_confidence(
        data_completeness: float,  # 0-1
        data_recency: float,  # 0-1 (how recent is the data)
        sample_size: int,  # Number of data points
        llm_uncertainty: float = 0.0,  # Any uncertainty expressed by LLM itself
    ) -> Dict[str, Any]:
        """
        Calculate overall confidence score.

        Returns:
            Dict with 'score', 'level', and 'reasoning'
        """
        # Weighted combination
        base_score = (
            data_completeness * 0.4
            + data_recency * 0.3
            + min(sample_size / 100, 1.0) * 0.3
        )

        # Penalize for LLM-expressed uncertainty
        final_score = base_score * (1 - llm_uncertainty)

        # Determine level
        if final_score >= 0.8:
            level = "high"
            reasoning = "Based on comprehensive, recent data with strong patterns"
        elif final_score >= 0.6:
            level = "medium"
            reasoning = "Based on available data, but some limitations exist"
        else:
            level = "low"
            reasoning = "Limited data available - treat as exploratory"

        return {
            "score": final_score,
            "level": level,
            "reasoning": reasoning,
            "factors": {
                "data_completeness": data_completeness,
                "data_recency": data_recency,
                "sample_size": sample_size,
            },
        }
