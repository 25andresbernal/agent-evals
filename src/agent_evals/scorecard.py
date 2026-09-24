"""Scorecard: the weighted dimensions a PM defines as "good" for an agent.

A scorecard is a small YAML file. Each dimension names a scorer, a weight,
and a pass threshold. The scorecard itself has an overall pass threshold
applied to the weighted average across dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Dimension:
    """One scored dimension, e.g. task_success, cost, or a rubric-based
    quality score.

    `scorer` is either a built-in scorer name (task_success,
    tool_correctness, cost, latency, llm_judge) or a `module:function`
    path to a custom scorer for teams that need one.
    """

    name: str
    scorer: str
    weight: float
    threshold: float = 0.0
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Dimension:
        for required in ("name", "scorer", "weight"):
            if required not in data:
                raise ValueError(f"scorecard dimension is missing required field '{required}'")
        return cls(
            name=str(data["name"]),
            scorer=str(data["scorer"]),
            weight=float(data["weight"]),
            threshold=float(data.get("threshold", 0.0)),
            config=dict(data.get("config") or {}),
        )


@dataclass
class Scorecard:
    """A named set of weighted dimensions and an overall pass threshold."""

    name: str
    dimensions: list[Dimension]
    pass_threshold: float = 0.7

    def __post_init__(self) -> None:
        if not self.dimensions:
            raise ValueError(f"scorecard '{self.name}' has no dimensions")
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight <= 0:
            raise ValueError(f"scorecard '{self.name}' dimension weights must sum to more than 0")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scorecard:
        if "dimensions" not in data:
            raise ValueError("scorecard is missing required field 'dimensions'")
        dimensions = [Dimension.from_dict(d) for d in data["dimensions"]]
        return cls(
            name=str(data.get("name", "Untitled Scorecard")),
            dimensions=dimensions,
            pass_threshold=float(data.get("pass_threshold", 0.7)),
        )

    @classmethod
    def load(cls, path: str | Path) -> Scorecard:
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            raise ValueError(f"{path} is empty")
        return cls.from_dict(data)

    def weighted_score(self, dimension_scores: dict[str, float]) -> float:
        """Combine per-dimension scores into one weighted average.

        Weights are normalized by their sum, so they do not need to add up
        to exactly 1.0 in the YAML file. Missing dimension scores count as 0.
        """
        total_weight = sum(d.weight for d in self.dimensions)
        total = sum(d.weight * dimension_scores.get(d.name, 0.0) for d in self.dimensions)
        return total / total_weight
