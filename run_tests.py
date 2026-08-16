"""NutriConcierge Test Runner."""

import sys
import unittest

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Running NutriConcierge Comprehensive Test Suite & Evals")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for folder in ["tests/unit", "tests/integration", "tests/evals"]:
        sub_suite = loader.discover(start_dir=folder, pattern="test_*.py", top_level_dir=".")
        suite.addTests(sub_suite)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} tests and safety evaluations passed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Test suite failed with {len(result.failures)} failure(s) and {len(result.errors)} error(s).")
        sys.exit(1)
