"""ExplorerSubagent — vault-walker role.

Given a user's direction, Explorer walks the vault via Read, Grep, and
Bash (for shell pipelines in the orientation bootstrap) and returns either
a Recipe (work order for the Miner) or a Denial (reason the vault can't
support the direction). The role's system prompt lives in
`prompts/explorer.md` (loaded at import time) and the tool grants are
declared below. The runtime does the actual model call via composition
on the Subagent base.

See P8 Working Notes "Explorer System Prompt Design" for the interview
(EP1-EP12) behind the prompt content.
"""

from __future__ import annotations

import logging
from dataclasses import fields
from pathlib import Path

from recipe import Bundle, Recipe, Denial

from .base import Subagent


logger = logging.getLogger(__name__)


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "explorer.md"
EXPLORER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

EXPLORER_TOOLS = ["Read", "Grep", "Bash"]


class ExplorerSubagent(Subagent):
    """Explorer role: direction -> Recipe | Denial."""

    @property
    def system_prompt(self) -> str:
        return EXPLORER_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return list(EXPLORER_TOOLS)

    def explore(
        self,
        direction: str,
        event_log: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> Recipe | Denial:
        log = logger or globals()["logger"]
        log.debug("exploring direction: %r", direction)
        packet = {"direction": direction}
        response = self.runtime.invoke(
            packet,
            system_prompt=self.system_prompt,
            tools=self.tools,
            event_log=event_log,
            logger=logger,
        )
        return _parse_explorer_output(response, log)


def _drop_unknown_fields(
    cls, payload: dict, context: str, log: logging.Logger | None = None
) -> dict:
    """Return payload filtered to cls's dataclass fields; warn on drops.

    Defensive against model confabulation — Explorer sometimes invents
    schema fields (e.g. an `artifact_description_continued` overflow key).
    Prompt-level guidance forbids extras; this is the belt-and-suspenders
    parser-side filter.
    """
    log = log or logger
    known = {f.name for f in fields(cls)}
    unknown = set(payload) - known
    if unknown:
        log.warning(
            "%s: dropping unknown fields %s", context, sorted(unknown)
        )
    return {k: v for k, v in payload.items() if k in known}


def _parse_explorer_output(
    data: dict, log: logging.Logger | None = None
) -> Recipe | Denial:
    """Parse worker JSON into a Recipe or Denial.

    Contract: top-level `"kind"` discriminator, either "recipe" or
    "denial". The discriminator is stripped before constructing the
    dataclass so Recipe/Denial stay clean of wire-level fields. Unknown
    fields at the Recipe / Bundle / Denial level are dropped with a
    WARNING rather than raising.
    """
    log = log or logger
    if "kind" not in data:
        log.error("explorer output missing 'kind' discriminator: %s", data)
        raise ValueError("Explorer output missing 'kind' discriminator")

    kind = data["kind"]
    payload = {k: v for k, v in data.items() if k != "kind"}

    if kind == "recipe":
        try:
            nn = payload.get("notes_needed")
            if nn is not None:
                if not isinstance(nn, dict):
                    raise ValueError(
                        f"'notes_needed' must be a dict of bundles, "
                        f"got {type(nn).__name__}"
                    )
                payload = dict(payload)
                payload["notes_needed"] = {
                    label: Bundle(
                        **_drop_unknown_fields(
                            Bundle, bundle, f"bundle {label!r}", log
                        )
                    )
                    for label, bundle in nn.items()
                }
            payload = _drop_unknown_fields(Recipe, payload, "recipe", log)
            return Recipe(**payload)
        except (TypeError, ValueError) as e:
            log.error("explorer recipe payload invalid: %s (%s)", payload, e)
            raise ValueError(f"Explorer recipe payload invalid: {e}") from e

    if kind == "denial":
        try:
            payload = _drop_unknown_fields(Denial, payload, "denial", log)
            return Denial(**payload)
        except TypeError as e:
            log.error("explorer denial payload invalid: %s (%s)", payload, e)
            raise ValueError(f"Explorer denial payload invalid: {e}") from e

    log.error("explorer output unknown kind %r: %s", kind, data)
    raise ValueError(
        f"Explorer output kind must be 'recipe' or 'denial', got {kind!r}"
    )
