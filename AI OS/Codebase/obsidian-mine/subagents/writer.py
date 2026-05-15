"""WriterSubagent — artifact-composer role.

Given the artifact-level guidance from Explorer and the records produced
by all the Miners, the Writer composes the deliverable as one Markdown
string. The role's system prompt lives in `prompts/writer.md` (loaded at
import time) and the tool grants are declared below. The runtime does
the actual model call via composition on the Subagent base.

The method takes explicit fields (artifact_name, artifact_description,
output_schema, bundles), not the full Recipe — closes the cross-bundle
leakage footgun at the type signature, parallel to MinerSubagent.mine.
The Writer never produces the Mining Summary; that file is rendered
mechanically by the orchestrator from run metadata (W1=C).

See P8 Working Notes "Writer Design (W1-W10)" for the design decisions
behind this role.
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

from recipe import BundleResult

from .base import Subagent


logger = logging.getLogger(__name__)


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "writer.md"
WRITER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

WRITER_TOOLS = ["Read"]


class WriterSubagent(Subagent):
    """Writer role: records + artifact_description -> Markdown artifact."""

    @property
    def system_prompt(self) -> str:
        return WRITER_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return list(WRITER_TOOLS)

    def write(
        self,
        artifact_name: str,
        artifact_description: str,
        output_schema: str,
        bundles: dict[str, BundleResult],
        event_log: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> str:
        log = logger or globals()["logger"]
        log.debug(
            "writing artifact %r from %d bundle(s)",
            artifact_name, len(bundles),
        )
        packet = {
            "artifact_name": artifact_name,
            "artifact_description": artifact_description,
            "output_schema": output_schema,
            "bundles": {
                label: dataclasses.asdict(result)
                for label, result in bundles.items()
            },
        }
        response = self.runtime.invoke(
            packet,
            system_prompt=self.system_prompt,
            tools=self.tools,
            event_log=event_log,
            logger=logger,
        )
        return _parse_writer_output(response, log)


def _parse_writer_output(data: dict, log: logging.Logger | None = None) -> str:
    """Parse worker JSON into the artifact's Markdown body.

    Contract: top-level object with a `markdown` key holding a string.
    Unknown top-level fields (anything other than `markdown`) are dropped
    with a WARNING; this is the parallel of Miner's defensive parser
    pattern.
    """
    log = log or logger
    if "markdown" not in data:
        log.error("writer output missing 'markdown' key: %s", data)
        raise ValueError("Writer output missing 'markdown' key")

    markdown = data["markdown"]
    if not isinstance(markdown, str):
        log.error(
            "writer 'markdown' must be a string, got %s: %s",
            type(markdown).__name__, data,
        )
        raise ValueError(
            f"Writer 'markdown' must be a string, "
            f"got {type(markdown).__name__}"
        )

    unknown = set(data) - {"markdown"}
    if unknown:
        log.warning(
            "writer output: dropping unknown top-level fields %s",
            sorted(unknown),
        )

    return markdown
