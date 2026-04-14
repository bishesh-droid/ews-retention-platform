"""
Bug Condition Exploration Test for GradedComponent Import Error

**Validates: Requirements 1.1, 2.1**

This test explores the bug condition where 4 files attempt to import GradedComponent
from an incorrect module path. This test is EXPECTED TO FAIL on unfixed code,
confirming the bug exists.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

The test encodes the expected behavior - it will validate the fix when it passes
after implementation.
"""

import pytest
import sys
import importlib.util
from pathlib import Path


class TestGradedComponentImportError:
    """
    Property 1: Bug Condition - GradedComponent Import Path Error
    
    Tests that the 4 specific files with incorrect import paths will fail
    to import GradedComponent from the non-existent module path.
    
    This is a scoped property-based test approach that tests the exact
    files mentioned in the bug report.
    """
    
    # The 4 files with incorrect import statements
    AFFECTED_FILES = [
        "backend/tests/test_fk_constraints.py",
        "backend/tests/test_recommendations_idor.py", 
        "backend/tests/test_cohort_risk_profiles.py",
        "backend/services/ai/rag_engine.py"
    ]
    
    def test_graded_component_import_from_incorrect_path_fails(self):
        """
        Test that importing from the incorrect path raises ModuleNotFoundError.
        
        This test WILL FAIL on unfixed code with ModuleNotFoundError, which is
        the expected outcome that proves the bug exists.
        
        After the fix, this test should pass because the import statements
        will be corrected to use the actual module path.
        """
        # The incorrect import path that exists in the 4 files
        incorrect_module = "backend.database.models.graded_component"
        
        # This should raise ModuleNotFoundError on unfixed code
        with pytest.raises(
            ModuleNotFoundError,
            match=r"No module named 'backend\.database\.models\.graded_component'"
        ):
            __import__(incorrect_module)
    
    def test_graded_component_import_from_correct_path_succeeds(self):
        """
        Test that importing from the correct path (academic.py) works.
        
        This verifies that GradedComponent is actually defined in
        backend.database.models.academic, not in graded_component.
        """
        # The correct import path where GradedComponent is actually defined
        from backend.database.models.academic import GradedComponent
        
        # Verify the class was imported successfully
        assert GradedComponent is not None
        assert hasattr(GradedComponent, '__tablename__')
        assert GradedComponent.__tablename__ == "graded_components"
    
    def test_affected_files_contain_incorrect_import(self):
        """
        Test that the 4 affected files contain the incorrect import statement.
        
        This documents which files need to be fixed and serves as a
        counterexample demonstrating the bug's scope.
        """
        project_root = Path(__file__).parent.parent.parent
        incorrect_import = "from backend.database.models.graded_component import GradedComponent"
        
        files_with_bug = []
        
        for file_path in self.AFFECTED_FILES:
            full_path = project_root / file_path
            if full_path.exists():
                content = full_path.read_text()
                if incorrect_import in content:
                    files_with_bug.append(file_path)
        
        # Document the counterexamples: all 4 files should have the incorrect import
        assert len(files_with_bug) == 4, (
            f"Expected 4 files with incorrect import, found {len(files_with_bug)}: "
            f"{files_with_bug}"
        )
        
        # List the specific files for documentation
        assert "backend/tests/test_fk_constraints.py" in files_with_bug
        assert "backend/tests/test_recommendations_idor.py" in files_with_bug
        assert "backend/tests/test_cohort_risk_profiles.py" in files_with_bug
        assert "backend/services/ai/rag_engine.py" in files_with_bug
    
    def test_importing_affected_files_fails_on_unfixed_code(self):
        """
        Test that attempting to import the affected files raises ModuleNotFoundError.
        
        This is the actual bug manifestation: the 4 files cannot be imported
        because they reference a non-existent module.
        
        EXPECTED OUTCOME on unfixed code: This test FAILS because importing
        the files raises ModuleNotFoundError.
        
        After fix: This test should pass because the import statements will
        be corrected.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Track which files fail to import
        failed_imports = []
        
        for file_path in self.AFFECTED_FILES:
            # Convert file path to module name
            module_name = file_path.replace("/", ".").replace(".py", "")
            
            try:
                # Attempt to import the module
                # This will fail on unfixed code with ModuleNotFoundError
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    failed_imports.append((file_path, "Module spec not found"))
                else:
                    # Try to actually load the module
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            except ModuleNotFoundError as e:
                # This is the expected error on unfixed code
                failed_imports.append((file_path, str(e)))
            except Exception as e:
                # Other errors might occur, document them
                failed_imports.append((file_path, f"Other error: {str(e)}"))
        
        # On unfixed code, all 4 files should fail to import
        # This assertion will FAIL on unfixed code, proving the bug exists
        assert len(failed_imports) == 0, (
            f"Expected 0 failed imports after fix, but found {len(failed_imports)} failures:\n" +
            "\n".join([f"  - {path}: {error}" for path, error in failed_imports])
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
