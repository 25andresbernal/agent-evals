"""Suite: ties an agent, a scorecard, and a set of cases together so the
CLI has one file to point at.

A suite YAML file looks like:

    name: Support Agent Eval Suite
    agent: agent.py:handle_support_request
    scorecard: scorecard.yaml
    cases: cases.yaml
    judge: fake

`agent`, `scorecard`, and `cases` are resolved relative to the suite file's
own directory, not the current working directory, so a suite can be run
from anywhere.

The `agent` field accepts two forms:

- `path/to/file.py:function_name`, loaded directly from disk. This is the
  form the example suite uses, and the one most teams want: no packaging,
  no import path to get right, just point at a file.
- `dotted.module.path:function_name`, imported normally. Use this when the
  agent already lives in an installed package.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml

from agent_evals.cases import EvalCase, load_cases
from agent_evals.runner import Agent
from agent_evals.scorecard import Scorecard


@dataclass
class Suite:
    name: str
    agent_spec: str
    scorecard: Scorecard
    cases: list[EvalCase]
    judge_kind: str = "fake"
    judge_model: str | None = None
    base_dir: Path = Path(".")

    def load_agent(self) -> Agent:
        return resolve_agent(self.agent_spec, self.base_dir)


def resolve_agent(spec: str, base_dir: Path) -> Agent:
    """Resolve an `agent` spec string to a callable.

    See the module docstring for the two accepted forms.
    """
    if ":" not in spec:
        raise ValueError(
            f"invalid agent spec '{spec}': expected 'module:function' or 'path/to/file.py:function'"
        )
    target, func_name = spec.rsplit(":", 1)

    if target.endswith(".py"):
        file_path = (base_dir / target).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"agent file not found: {file_path}")
        module_name = f"_agent_evals_dynamic_{uuid.uuid4().hex}"
        spec_obj = importlib.util.spec_from_file_location(module_name, file_path)
        if spec_obj is None or spec_obj.loader is None:
            raise ImportError(f"could not load agent module from {file_path}")
        module = importlib.util.module_from_spec(spec_obj)
        sys.modules[module_name] = module
        spec_obj.loader.exec_module(module)
    else:
        module = importlib.import_module(target)

    try:
        return getattr(module, func_name)
    except AttributeError as exc:
        raise AttributeError(f"agent spec '{spec}' has no function '{func_name}'") from exc


def load_suite(path: str | Path) -> Suite:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data:
        raise ValueError(f"{path} is empty")

    for required in ("agent", "scorecard", "cases"):
        if required not in data:
            raise ValueError(f"suite {path} is missing required field '{required}'")

    base_dir = path.parent
    scorecard = Scorecard.load(base_dir / data["scorecard"])
    cases = load_cases(base_dir / data["cases"])

    return Suite(
        name=str(data.get("name", path.stem)),
        agent_spec=str(data["agent"]),
        scorecard=scorecard,
        cases=cases,
        judge_kind=str(data.get("judge", "fake")),
        judge_model=data.get("judge_model"),
        base_dir=base_dir,
    )
