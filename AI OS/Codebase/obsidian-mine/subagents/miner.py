"""MinerSubagent — bundle-extractor role.

Given one bundle of notes from a Recipe, the Miner reads them and emits
structured records that match the Recipe's `output_schema` and the
bundle's `expected_output`. The role's system prompt lives in
`prompts/miner.md` (loaded at import time) and the tool grants are
declared below. The runtime does the actual model call via composition
on the Subagent base.

The method takes the four worker-relevant fields explicitly (Bundle plus
miner_objective + output_schema), not the full Recipe — closes the
cross-bundle leakage footgun at the type signature. The Orchestrator
unpacks Recipe at the call site.

See [[P8 Miner Design]] for the M1-M7 design decisions behind this role.
"""

from __future__ import annotations

import logging
from pathlib import Path

from recipe import Bundle

from .base import Subagent


logger = logging.getLogger(__name__)


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "miner.md"
MINER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

MINER_TOOLS = ["Read", "Grep", "Bash"]


class MinerSubagent(Subagent):
    """Miner role: bundle -> list of records matching the Recipe's schema."""

    @property
    def system_prompt(self) -> str:
        return MINER_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return list(MINER_TOOLS)

    def mine(
        self,
        bundle: Bundle,
        bundle_label: str,
        miner_objective: str,
        output_schema: str,
        event_log: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> list[dict]:
        log = logger or globals()["logger"]
        log.debug(
            "mining bundle %r (%d paths)", bundle_label, len(bundle.paths)
        )
        packet = {
            "bundle_label": bundle_label,
            "miner_objective": miner_objective,
            "output_schema": output_schema,
            "bundle_description": bundle.description,
            "expected_output": bundle.expected_output,
            "paths": list(bundle.paths),
        }
        response = self.runtime.invoke(
            packet,
            system_prompt=self.system_prompt,
            tools=self.tools,
            event_log=event_log,
            logger=logger,
        )
        return _parse_miner_output(response, log)


def _parse_miner_output(data: dict, log: logging.Logger | None = None) -> list[dict]:
    """Parse worker JSON into a list of records.

    Contract: top-level object with a `records` key holding a list. Each
    record must be a dict with a `kind` string field. Records pass
    through unchanged — the Orchestrator interprets them against the
    Recipe's output_schema at assembly time. Unknown top-level fields
    (anything other than `records`) are dropped with a WARNING; this is
    the parallel of Explorer's defensive parser pattern.
    """
    log = log or logger
    if "records" not in data:
        log.error("miner output missing 'records' key: %s", data)
        raise ValueError("Miner output missing 'records' key")

    records = data["records"]
    if not isinstance(records, list):
        log.error(
            "miner 'records' must be a list, got %s: %s",
            type(records).__name__, data,
        )
        raise ValueError(
            f"Miner 'records' must be a list, got {type(records).__name__}"
        )

    unknown = set(data) - {"records"}
    if unknown:
        log.warning(
            "miner output: dropping unknown top-level fields %s",
            sorted(unknown),
        )

    for i, record in enumerate(records):
        if not isinstance(record, dict):
            log.error(
                "miner record %d must be a dict, got %s: %s",
                i, type(record).__name__, record,
            )
            raise ValueError(
                f"Miner record {i} must be a dict, got {type(record).__name__}"
            )
        if "kind" not in record:
            log.error("miner record %d missing 'kind' field: %s", i, record)
            raise ValueError(f"Miner record {i} missing 'kind' field")
        if not isinstance(record["kind"], str):
            log.error(
                "miner record %d 'kind' must be a string, got %s: %s",
                i, type(record["kind"]).__name__, record,
            )
            raise ValueError(
                f"Miner record {i} 'kind' must be a string, "
                f"got {type(record['kind']).__name__}"
            )

    return records
