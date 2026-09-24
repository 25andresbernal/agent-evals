from __future__ import annotations

import pytest

from agent_evals.cases import EvalCase, load_cases


def test_eval_case_from_dict_minimal():
    case = EvalCase.from_dict({"id": "c1", "input": "hello"})
    assert case.id == "c1"
    assert case.input == "hello"
    assert case.tags == []
    assert case.expected_tool_calls == []


def test_eval_case_from_dict_requires_id():
    with pytest.raises(ValueError, match="id"):
        EvalCase.from_dict({"input": "hello"})


def test_eval_case_from_dict_requires_input():
    with pytest.raises(ValueError, match="input"):
        EvalCase.from_dict({"id": "c1"})


def test_eval_case_expected_output_contains_accepts_single_string():
    case = EvalCase.from_dict({"id": "c1", "input": "hi", "expected_output_contains": "hello"})
    assert case.expected_output_contains == ["hello"]


def test_load_cases_from_list(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
- id: c1
  input: "hi"
- id: c2
  input: "bye"
""".strip()
    )
    cases = load_cases(path)
    assert [c.id for c in cases] == ["c1", "c2"]


def test_load_cases_from_mapping_with_cases_key(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
cases:
  - id: c1
    input: "hi"
""".strip()
    )
    cases = load_cases(path)
    assert len(cases) == 1
    assert cases[0].id == "c1"


def test_load_cases_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
- id: c1
  input: "hi"
- id: c1
  input: "bye"
""".strip()
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)


def test_load_cases_rejects_empty_file(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text("")
    with pytest.raises(ValueError, match="empty"):
        load_cases(path)
