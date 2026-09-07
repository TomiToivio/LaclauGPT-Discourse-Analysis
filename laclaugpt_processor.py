# -*- coding: utf-8 -*-
"""4CAT processor: "Analyze with LaclauGPT".

The processor is intentionally a thin 4CAT adapter. It reads text-bearing 4CAT
items, selects the canonical project/arena/machine/execution profile, and then
delegates all analysis to the same ``EffectiveRunConfig`` +
``run_canonical_pipeline`` path used by the CLI and scheduler.

Deployment (on the 4CAT host):
  1. install this repository in 4CAT's Python environment;
  2. configure the selected machine profile / Ollama environment;
  3. place this file in 4CAT's processors directory or package it as an extension;
  4. run "Analyze with LaclauGPT" on a text-bearing dataset.

The output is current LaclauGPT interchange NDJSON and remains PROVISIONAL until
human review. A review CSV is copied next to the 4CAT result when available.
"""
from __future__ import annotations

import os

from backend.abstract.processor import BasicProcessor


class LaclauGPTProcessor(BasicProcessor):
    type = "laclaugpt-analysis"
    title = "Analyze with LaclauGPT"
    description = (
        "Canonical evidence-linked Laclau/Mouffe + Palonen discourse analysis. "
        "Uses the same project/arena pipeline as the LaclauGPT CLI."
    )
    extension = "ndjson"
    accepts = [None]

    @classmethod
    def get_options(cls, parent_dataset=None, user=None):
        return {
            "project": {
                "type": "string",
                "default": os.environ.get("LACLAUGPT_PROJECT", "ai26"),
                "help": "Canonical project profile, e.g. ai26",
            },
            "arena": {
                "type": "string",
                "default": os.environ.get("LACLAUGPT_ARENA", "grassroots"),
                "help": "Canonical arena profile, e.g. elites/grassroots/parliamentary",
            },
            "machine": {
                "type": "string",
                "default": os.environ.get("LACLAUGPT_MACHINE", "roihu"),
                "help": "Canonical machine profile",
            },
            "execution": {
                "type": "string",
                "default": "cli",
                "help": "Canonical execution profile; 4CAT normally uses cli",
            },
            "model": {
                "type": "string",
                "default": os.environ.get("OLLAMA_MODEL", "auto"),
                "help": "Optional model override; auto keeps the arena model policy",
            },
            "memory_dir": {
                "type": "string",
                "default": os.environ.get("LACLAUGPT_MEMORY_DIR", ""),
                "help": "Optional persistent Context Memory directory override",
            },
            "topic_key": {
                "type": "string",
                "default": "generic",
                "help": "Optional topic-background override; generic keeps the arena default",
            },
        }

    def process(self):
        from laclaugpt.integrations.fourcat import run_fourcat_rows

        self.dataset.update_status("LaclauGPT: reading 4CAT dataset")
        rows = [dict(item) for item in self.dataset.iterate_items(self)]
        result_path = self.dataset.get_results_path()
        platform = str(self.dataset.parameters.get("platform", "") or "")
        language = str(self.dataset.parameters.get("board_language", "") or "")

        self.dataset.update_status("LaclauGPT: running canonical pipeline")
        execution = run_fourcat_rows(
            rows,
            output_path=result_path,
            dataset_key=str(self.dataset.key),
            project=str(self.parameters.get("project", "ai26") or "ai26"),
            arena=str(self.parameters.get("arena", "grassroots") or "grassroots"),
            machine=str(self.parameters.get("machine", "roihu") or "roihu"),
            execution=str(self.parameters.get("execution", "cli") or "cli"),
            model=str(self.parameters.get("model", "auto") or "auto"),
            memory_dir=str(self.parameters.get("memory_dir", "") or "") or None,
            topic_key=str(self.parameters.get("topic_key", "generic") or "generic"),
            default_platform=platform,
            default_language=language,
        )
        count = int(execution["result"].get("processed", 0))
        self.dataset.update_status(f"LaclauGPT: wrote {count} canonical annotations")
        self.dataset.finish(count)
