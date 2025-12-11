#!/usr/bin/env python3
"""
Demo Session Setup Script

Prepares the application for demo by:
1. Loading sample questions
2. Creating demo user sessions
3. Setting up test data

Usage:
    python scripts/setup_demo.py [--reset]
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.services.question_bank_service import Difficulty, QuestionBankService


def verify_question_bank():
    """Verify the question bank is properly loaded."""
    print("\n📚 Verifying Question Bank...")

    try:
        service = QuestionBankService()
        service.load()

        print(f"  ✓ Loaded {len(service.questions)} questions")
        print(f"  ✓ Found {len(service.categories)} categories:")

        for cat in service.categories:
            cat_questions = service.get_questions_by_category(cat.id, shuffle=False)
            print(f"    - {cat.name}: {len(cat_questions)} questions")

            # Show breakdown by difficulty
            easy = len([q for q in cat_questions if q.difficulty == Difficulty.EASY])
            medium = len([q for q in cat_questions if q.difficulty == Difficulty.MEDIUM])
            hard = len([q for q in cat_questions if q.difficulty == Difficulty.HARD])
            print(f"      (Easy: {easy}, Medium: {medium}, Hard: {hard})")

        return True

    except FileNotFoundError as e:
        print(f"  ✗ Question bank not found: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error loading question bank: {e}")
        return False


def create_demo_sessions():
    """Create pre-configured demo sessions."""
    print("\n🎯 Creating Demo Sessions...")

    demo_configs = [
        {"name": "Algebra Quick Quiz", "category": "algebra", "count": 3, "description": "A quick 3-question algebra review"},
        {"name": "Geometry Challenge", "category": "geometry", "count": 5, "description": "Test your geometry knowledge"},
        {"name": "Python Fundamentals", "category": "python_basics", "count": 3, "description": "Practice basic Python programming"},
    ]

    for config in demo_configs:
        print(f"  → {config['name']}: {config['description']}")

    # Save demo configs for the UI to use
    demo_config_path = Path(__file__).parent.parent / "data" / "demo_sessions.json"
    demo_config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(demo_config_path, "w") as f:
        json.dump(
            {
                "demo_sessions": demo_configs,
                "default_session": "algebra",
            },
            f,
            indent=2,
        )

    print(f"  ✓ Saved demo configurations to {demo_config_path}")
    return True


def show_demo_instructions():
    """Display instructions for running the demo."""
    print("\n" + "=" * 60)
    print("🎬 DEMO READY!")
    print("=" * 60)
    print("""
To run the demo:

1. Start the infrastructure (if not running):
   $ make up

2. Start the agent-host service:
   $ cd src/agent-host && make run

3. Open the browser:
   http://localhost:8001

4. Demo Scenarios:

   📐 Algebra Session:
   - Type: /learn algebra
   - Answer 5 multiple-choice and free-text questions
   - See your score at the end

   📏 Geometry Session:
   - Type: /learn geometry
   - Mix of multiple-choice and calculation questions

   🐍 Python Coding Session:
   - Type: /learn python_basics
   - Write code in the interactive editor
   - Get instant feedback

5. Widget Features to Showcase:
   - Multiple choice: Click or use keyboard (↑↓ + Enter)
   - Free text: Type answer and submit
   - Code editor: Write code with line numbers

6. Session Features:
   - Progress tracking
   - Instant feedback
   - Score summary
   - Ability to continue or start new

Press Ctrl+C to exit the demo at any time.
""")


def reset_demo_data():
    """Reset any demo data to initial state."""
    print("\n🔄 Resetting Demo Data...")

    # Remove any cached sessions
    cache_dir = Path(__file__).parent.parent / "data" / "cache"
    if cache_dir.exists():
        import shutil

        shutil.rmtree(cache_dir)
        print("  ✓ Cleared session cache")

    # Recreate demo sessions
    create_demo_sessions()

    print("  ✓ Demo data reset complete")
    return True


def main():
    parser = argparse.ArgumentParser(description="Set up demo environment")
    parser.add_argument("--reset", action="store_true", help="Reset demo data")
    parser.add_argument("--verify-only", action="store_true", help="Only verify setup")
    args = parser.parse_args()

    print("🚀 Agent Host Demo Setup")
    print("=" * 40)

    if args.reset:
        reset_demo_data()

    # Verify question bank
    if not verify_question_bank():
        print("\n❌ Setup failed: Question bank not available")
        sys.exit(1)

    if args.verify_only:
        print("\n✅ Verification complete!")
        sys.exit(0)

    # Create demo sessions
    if not create_demo_sessions():
        print("\n❌ Setup failed: Could not create demo sessions")
        sys.exit(1)

    # Show instructions
    show_demo_instructions()

    print("\n✅ Demo setup complete!")


if __name__ == "__main__":
    main()
