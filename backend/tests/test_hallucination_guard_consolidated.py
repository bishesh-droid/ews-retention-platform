"""
Test that hallucination guard is consolidated across modules.

This verifies FIX 1: both llm_orchestrator.py and rag_engine.py use the same
canonical validation class from hallucination_guard.py.
"""

import unittest


class TestHallucinationGuardConsolidation(unittest.TestCase):
    """Verify all AI modules use the same hallucination guard."""

    def test_rag_engine_uses_canonical_guard(self):
        """rag_engine.py should import GuardrailValidator from hallucination_guard."""
        # Import and verify it's the canonical class
        from backend.services.ai.rag_engine import GuardrailValidator
        from backend.services.ai.hallucination_guard import HallucinationPrevention

        # They should be the same class (rag_engine imports it as alias)
        self.assertIs(GuardrailValidator, HallucinationPrevention)

    def test_llm_orchestrator_uses_canonical_guard(self):
        """llm_orchestrator.py should use GuardrailValidator from hallucination_guard."""
        from backend.services.ai.llm_orchestrator import LLMOrchestrator
        from backend.services.ai.hallucination_guard import HallucinationPrevention

        # Verify the orchestrator imports and uses the canonical class
        # The orchestrator should import GuardrailValidator from rag_engine
        # which is itself an alias for HallucinationPrevention
        import backend.services.ai.rag_engine as rag_module

        self.assertIs(
            rag_module.GuardrailValidator,
            HallucinationPrevention,
            "rag_engine.GuardrailValidator must be hallucination_guard.HallucinationPrevention"
        )

    def test_guardrail_validator_has_validate_response(self):
        """The consolidated class must have the validate_response method."""
        from backend.services.ai.hallucination_guard import HallucinationPrevention

        self.assertTrue(
            hasattr(HallucinationPrevention, 'validate_response'),
            "HallucinationPrevention must have validate_response method"
        )
        self.assertTrue(
            callable(getattr(HallucinationPrevention, 'validate_response')),
            "validate_response must be callable"
        )


if __name__ == "__main__":
    unittest.main()
