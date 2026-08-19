"""Turn a written instruction into a sequence of operations.

Three routes, tried in order, cheapest first:

  1. The text already *is* a sequence of operations ("U L' U' L") — parse it.
  2. The text names a known intent ("solve it") — the concept knows how.
  3. Anything else — ask the reasoning model, which may only answer with
     operations from the catalogue, and must abstain when it cannot.

Most real use lands on route 1 or 2, so the common path needs no API key and
no network. The model is the fallback, not the engine.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from etu.kb.database import ConceptInfo

SOLVE_WORDS = ("solve", "unscramble", "fix", "restore", "complete")
UNDO_WORDS = ("undo", "reverse", "rewind", "invert", "back")

SYSTEM = (
    "You translate an instruction about a physical puzzle into a list of moves. "
    "You may only use moves from the catalogue you are given. "
    'Reply with JSON only: {"operations": ["..."], "rationale": "one sentence"}. '
    'If the instruction cannot be expressed in those moves, reply {"operations": [], '
    '"rationale": "why not"}.'
)


@dataclass
class OperationPlan:
    """An ordered list of operations, and how it was arrived at."""

    operations: list[str] = field(default_factory=list)
    rationale: str = ""
    route: str = "none"  # parsed | intent | model | none

    @property
    def ok(self) -> bool:
        return bool(self.operations)

    def __str__(self) -> str:
        if not self.ok:
            return f"no plan ({self.route}): {self.rationale}"
        return (
            f"{len(self.operations)} ops via {self.route}: {' '.join(self.operations)}"
        )


def instruct(
    text: str,
    concept: ConceptInfo,
    history: list[str] | None = None,
    chat_fn: Callable[[str, str], str] | None = None,
) -> OperationPlan:
    """Plan the operations that carry out `text` for this concept.

    `history` is what has been done to the model already — needed to answer
    "solve it", since undoing a scramble requires knowing the scramble.
    """
    catalog = set(concept.operations)

    literal = _as_operations(text, catalog)
    if literal:
        return OperationPlan(literal, "read the instruction as moves", "parsed")

    intent = _as_intent(text, concept, history or [])
    if intent is not None:
        return intent

    if chat_fn is None:
        return OperationPlan(
            [], "no operations recognised, and no reasoning model available", "none"
        )
    return _ask_model(text, concept, chat_fn)


def _as_operations(text: str, catalog: set[str]) -> list[str]:
    """The instruction read literally as moves, or [] if it is not one."""
    tokens = text.replace(",", " ").split()
    if not tokens:
        return []
    return tokens if all(token in catalog for token in tokens) else []


def _as_intent(
    text: str, concept: ConceptInfo, history: list[str]
) -> OperationPlan | None:
    """Recognise the standing intents any concept with a solver understands."""
    lowered = text.strip().lower()

    if any(word in lowered for word in SOLVE_WORDS):
        if concept.solve is None:
            return OperationPlan([], f"{concept.name} has no solver", "intent")
        if not history:
            return OperationPlan(
                [],
                "nothing to solve: the model is already in its target state, or the "
                "scramble that produced it is unknown",
                "intent",
            )
        return OperationPlan(
            concept.solve(history), "undo the known scramble", "intent"
        )

    if any(word in lowered for word in UNDO_WORDS) and history:
        if concept.solve is None:
            return OperationPlan([], f"{concept.name} cannot be reversed", "intent")
        return OperationPlan(
            concept.solve(history[-1:]), "undo the last move", "intent"
        )

    return None


def _ask_model(
    text: str, concept: ConceptInfo, chat_fn: Callable[[str, str], str]
) -> OperationPlan:
    prompt = (
        f"Object: {concept.name} — {concept.summary}\n"
        f"Goal: {concept.target}\n"
        f"Move catalogue: {' '.join(concept.operations)}\n\n"
        f"Instruction: {text}"
    )
    try:
        reply = chat_fn(SYSTEM, prompt)
        data = reply if isinstance(reply, dict) else json.loads(_only_json(reply))
    except (ValueError, TypeError, KeyError) as exc:
        return OperationPlan([], f"could not read the model's reply: {exc}", "model")

    catalog = set(concept.operations)
    proposed = [str(op) for op in data.get("operations", [])]
    unknown = [op for op in proposed if op not in catalog]
    if unknown:
        return OperationPlan(
            [],
            f"model proposed moves outside the catalogue: {', '.join(unknown)}",
            "model",
        )
    return OperationPlan(proposed, str(data.get("rationale", "")), "model")


def _only_json(reply: str) -> str:
    """Pull the JSON object out of a reply that may be fenced or chatty."""
    text = reply.strip()
    if "```" in text:
        chunk = text.split("```")[1]
        text = chunk[4:] if chunk.lower().startswith("json") else chunk
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in reply")
    depth, in_string, escaped = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("unbalanced JSON object in reply")


def catalog_prompt(concept: ConceptInfo) -> str:
    """The operation catalogue, formatted for a human or a prompt."""
    return f"{concept.name}: {' '.join(concept.operations)}"


def as_dict(plan: OperationPlan) -> dict[str, Any]:
    return {
        "operations": plan.operations,
        "rationale": plan.rationale,
        "route": plan.route,
    }
