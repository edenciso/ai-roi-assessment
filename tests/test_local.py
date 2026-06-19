"""
ValueOS FDE Demo — Local Smoke Tests
Run without AWS to verify JSON processing, cost calculation, and schema validation.

Usage: python -m pytest tests/test_local.py -v
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shared.utils import calc_cost, enrich_projects_with_costs, new_id


def test_pricing_openai_gpt4o():
    # 1M input + 1M output at gpt-4o rates: $2.50 + $10.00 = $12.50
    cost = calc_cost("openai", "gpt-4o", 1_000_000, 1_000_000)
    assert abs(cost - 12.50) < 0.01, f"Expected ~12.50, got {cost}"


def test_pricing_anthropic_sonnet():
    cost = calc_cost("anthropic", "claude-sonnet-4-5", 1_000_000, 1_000_000)
    assert abs(cost - 18.00) < 0.01, f"Expected ~18.00, got {cost}"


def test_pricing_unknown_model_uses_default():
    cost = calc_cost("openai", "gpt-99-turbo", 1_000_000, 1_000_000)
    # Default: $5 input + $15 output = $20
    assert abs(cost - 20.00) < 0.01, f"Expected ~20.00, got {cost}"


def test_enrich_projects():
    projects = [
        {
            "name": "Test",
            "usage": [
                {"provider": "openai", "model": "gpt-4o-mini", "input_tokens": 1000000, "output_tokens": 500000}
            ],
            "subscriptions": [{"tool": "Test Tool", "monthly_cost_usd": 100}],
        }
    ]
    result = enrich_projects_with_costs(projects)
    assert result[0]["usage"][0]["calculated_cost_usd"] > 0
    assert result[0]["total_calculated_cost_usd"] > 100  # LLM cost + $100 sub


def test_id_generation():
    id1 = new_id("proj-")
    id2 = new_id("proj-")
    assert id1 != id2
    assert id1.startswith("proj-")


def test_sample_schema_valid():
    schema_path = os.path.join(os.path.dirname(__file__), "..", "src", "sample_data", "input_schema.json")
    with open(schema_path) as f:
        data = json.load(f)
    assert "company" in data
    assert "projects" in data
    assert len(data["projects"]) > 0


if __name__ == "__main__":
    tests = [test_pricing_openai_gpt4o, test_pricing_anthropic_sonnet,
             test_pricing_unknown_model_uses_default, test_enrich_projects,
             test_id_generation, test_sample_schema_valid]
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{len(tests)} tests complete.")
