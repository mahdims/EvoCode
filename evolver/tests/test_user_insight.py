"""Test user_insight functionality"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


def test_vrpagent_prompts():
    """Test VRPAgentPrompts.user_insight_generation"""
    print("\n" + "="*60)
    print("TEST: VRPAgentPrompts.user_insight_generation")
    print("="*60)

    from vrpagent_prompts import VRPAgentPrompts

    # Test initialize (no related candidates)
    print("\n--- Testing 'initialize' type ---")
    try:
        prompt = VRPAgentPrompts.user_insight_generation(
            insight_type="initialize",
            idea="Use demand-based clustering to remove high-demand nodes together",
            related_candidates=None
        )
        print(f"Prompt length: {len(prompt)} chars")
        print(f"Prompt preview: {prompt[:200]}...")
        print("PASS: initialize prompt generated")
    except Exception as e:
        print(f"FAIL: {e}")

    # Test mutate (single related candidate)
    print("\n--- Testing 'mutate' type ---")
    mock_candidate = {
        "candidate_id": 0,
        "idea": "Random removal strategy",
        "fitness": 0.05,
        "code": "package EvoDestroy;\npublic class Test implements DestroyStrategy {}",
        "eval_results": [{"instance": "test", "improvement": 0.05, "success": True}]
    }
    try:
        prompt = VRPAgentPrompts.user_insight_generation(
            insight_type="mutate",
            idea="Add adaptive threshold based on omega size",
            related_candidates=[mock_candidate]
        )
        print(f"Prompt length: {len(prompt)} chars")
        print(f"Contains base candidate: {'Base Candidate' in prompt}")
        print("PASS: mutate prompt generated")
    except Exception as e:
        print(f"FAIL: {e}")

    # Test crossover (multiple related candidates)
    print("\n--- Testing 'crossover' type ---")
    mock_candidate2 = {
        "candidate_id": 1,
        "idea": "KNN clustering strategy",
        "fitness": 0.08,
        "code": "package EvoDestroy;\npublic class Test2 implements DestroyStrategy {}",
        "eval_results": [{"instance": "test", "improvement": 0.08, "success": True}]
    }
    try:
        prompt = VRPAgentPrompts.user_insight_generation(
            insight_type="crossover",
            idea="Combine KNN from first with demand-awareness from second",
            related_candidates=[mock_candidate, mock_candidate2]
        )
        print(f"Prompt length: {len(prompt)} chars")
        print(f"Contains Parent 1: {'Parent 1' in prompt}")
        print(f"Contains Parent 2: {'Parent 2' in prompt}")
        print("PASS: crossover prompt generated")
    except Exception as e:
        print(f"FAIL: {e}")

    # Test validation: mutate without candidate should fail
    print("\n--- Testing validation: mutate without candidate ---")
    try:
        prompt = VRPAgentPrompts.user_insight_generation(
            insight_type="mutate",
            idea="Some idea",
            related_candidates=[]
        )
        print("FAIL: Should have raised ValueError")
    except ValueError as e:
        print(f"PASS: Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"FAIL: Wrong exception: {e}")

    # Test validation: crossover with 1 candidate should fail
    print("\n--- Testing validation: crossover with 1 candidate ---")
    try:
        prompt = VRPAgentPrompts.user_insight_generation(
            insight_type="crossover",
            idea="Some idea",
            related_candidates=[mock_candidate]
        )
        print("FAIL: Should have raised ValueError")
    except ValueError as e:
        print(f"PASS: Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"FAIL: Wrong exception: {e}")


def test_llm_agents():
    """Test LLMAgents.generate_with_user_insight"""
    print("\n" + "="*60)
    print("TEST: LLMAgents.generate_with_user_insight")
    print("="*60)

    from llm_agents import LLMAgents

    # Test with LLM disabled first (fast)
    print("\n--- Testing with LLM disabled ---")
    llm = LLMAgents(use_llm=False)

    idea, code = llm.generate_with_user_insight(
        insight_type="initialize",
        idea="Test idea for initialization"
    )
    print(f"Returned idea: {idea[:50]}...")
    print(f"Returned code length: {len(code)} chars")
    print(f"Code is valid Java: {'package EvoDestroy' in code}")
    print("PASS: Template fallback works")


def test_llm_agents_with_api():
    """Test LLMAgents.generate_with_user_insight with real API"""
    print("\n" + "="*60)
    print("TEST: LLMAgents.generate_with_user_insight (with API)")
    print("="*60)

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or len(api_key) < 10:
        print("SKIP: No API key available")
        return

    from llm_agents import LLMAgents

    llm = LLMAgents(use_llm=True)

    print("\n--- Testing 'initialize' with real LLM ---")
    idea, code = llm.generate_with_user_insight(
        insight_type="initialize",
        idea="Remove nodes that are geographically isolated (far from their neighbors)"
    )
    print(f"Generated idea: {idea[:100]}...")
    print(f"Generated code length: {len(code)} chars")
    print(f"Code has package: {'package EvoDestroy' in code}")
    print(f"Code has class: {'class' in code}")
    print(f"Code has selectNodesToRemove: {'selectNodesToRemove' in code}")

    if 'package EvoDestroy' in code and 'selectNodesToRemove' in code:
        print("PASS: LLM generated valid strategy code")
    else:
        print("WARN: Generated code may have issues")
        print("--- Generated Code ---")
        print(code[:500])


if __name__ == "__main__":
    test_vrpagent_prompts()
    test_llm_agents()
    test_llm_agents_with_api()
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
