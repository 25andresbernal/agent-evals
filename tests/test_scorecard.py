from __future__ import annotations

import pytest

from agent_evals.scorecard import Dimension, Scorecard


def test_dimension_from_dict_defaults():
    dim = Dimension.from_dict({"name": "task_success", "scorer": "task_success", "weight": 1.0})
    assert dim.threshold == 0.0
    assert dim.config == {}


def test_scorecard_requires_dimensions():
    with pytest.raises(ValueError, match="dimensions"):
        Scorecard.from_dict({"name": "empty"})


def test_scorecard_rejects_zero_total_weight():
    with pytest.raises(ValueError, match="weight"):
        Scorecard(
            name="s",
            dimensions=[Dimension(name="a", scorer="task_success", weight=0.0)],
        )


def test_weighted_score_normalizes_weights():
    scorecard = Scorecard(
        name="s",
        dimensions=[
            Dimension(name="a", scorer="task_success", weight=2.0),
            Dimension(name="b", scorer="cost", weight=2.0),
        ],
    )
    # weights of 2 and 2 should behave the same as 0.5 and 0.5
    score = scorecard.weighted_score({"a": 1.0, "b": 0.0})
    assert score == pytest.approx(0.5)


def test_weighted_score_treats_missing_dimension_as_zero():
    scorecard = Scorecard(
        name="s",
        dimensions=[
            Dimension(name="a", scorer="task_success", weight=1.0),
            Dimension(name="b", scorer="cost", weight=1.0),
        ],
    )
    score = scorecard.weighted_score({"a": 1.0})
    assert score == pytest.approx(0.5)


def test_scorecard_load_from_yaml(tmp_path):
    path = tmp_path / "scorecard.yaml"
    path.write_text(
        """
name: Test Scorecard
pass_threshold: 0.8
dimensions:
  - name: task_success
    scorer: task_success
    weight: 1.0
    threshold: 0.9
""".strip()
    )
    scorecard = Scorecard.load(path)
    assert scorecard.name == "Test Scorecard"
    assert scorecard.pass_threshold == 0.8
    assert scorecard.dimensions[0].threshold == 0.9
