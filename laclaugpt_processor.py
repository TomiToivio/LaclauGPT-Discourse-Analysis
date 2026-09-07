# -*- coding: utf-8 -*-
"""4CAT processor: "Analyze with LaclauGPT".

This shipped compatibility processor reads text-bearing 4CAT datasets, analyses
them with the configured Ollama runtime, and writes LaclauGPT interchange JSONL
using the current schema 1.3 plus a flat review-oriented output surface.

Important architecture note: this file currently retains its own compact
summary/populism implementation. It is **not yet exact execution parity** with
``python -m laclaugpt.cli`` and the canonical evidence-linked pipeline. The work
to turn 4CAT into a thin adapter around that pipeline is tracked separately.

Deployment (on the 4CAT host):
  1. install this repository's runtime dependencies in 4CAT's Python environment;
  2. configure local, cloud, or external Ollama according to the data policy;
  3. place this file in 4CAT's processors directory or package it as an extension;
  4. run "Analyze with LaclauGPT" on a text-bearing dataset.
"""
from __future__ import annotations

import json
import os

from backend.abstract.processor import BasicProcessor
from common.config_manager import ConfigWrapper


class LaclauGPTProcessor(BasicProcessor):
    type = "laclaugpt-analysis"
    title = "Analyze with LaclauGPT"
    description = ("Theory-guided computational discourse analysis "
                   "(Laclau/Mouffe + Palonen): entities, topics, signifiers, "
                   "affects, Formula of Populism. Uses the configured Ollama "
                   "model and the canonical laclaugpt.memory facade.")
    extension = "ndjson"
    accepts = [None]  # accept any dataset with text bodies

    @classmethod
    def get_options(cls, parent_dataset=None, user=None):
        return {
            "model": {
                "type": "string",
                "default": os.environ.get("OLLAMA_MODEL", "auto"),
                "help": "Ollama model; auto applies the machine-tier policy",
            },
            "memory_dir": {
                "type": "string",
                "default": os.environ.get("LACLAUGPT_MEMORY_DIR",
                                          "/scratch/project_2009497/laclaugpt2/memory"),
                "help": "Persistent Context Memory directory",
            },
            "topic_key": {
                "type": "string",
                "default": "generic",
                "help": "Topic background key (ai-contestation/...)",
            },
            "stages": {
                "type": "toggle",
                "default": True,
                "help": "Include Formula of Populism stage (slower)",
            },
        }

    def process(self):
        from laclaugpt.memory import Memory, MemoryRef
        from laclaugpt_interchange import DocumentAnnotation, from_memory_results, to_jsonl
        from prompts import topic_background as tb

        from llm import resolve_endpoint
        _, model = resolve_endpoint(self.parameters.get("model", "auto"))
        memory_dir = self.parameters.get("memory_dir", "./data/memory")
        topic_key = self.parameters.get("topic", "generic")
        with_populism = self.parameters.get("stages", True)

        memory = Memory(memory_dir=memory_dir)
        topic = tb.topic_background(topic_key) if topic_key != "generic" else ""

        self.dataset.update_status("LaclauGPT: iterating dataset")
        results = []
        for item in self.dataset.iterate_items(self):
            doc_id = str(item.get("id", ""))
            body = item.get("body") or item.get("text") or ""
            if not body.strip():
                continue
            ctx = memory.context_prompt_block(body[:2000])
            # summary stage (structured)
            from prompts import summary as summary_prompt
            system = summary_prompt.build_system_prompt(topic, "", "")
            SummaryModel = summary_prompt.pydantic_models()
            from llm import chat_structured
            payload = chat_structured(model, system,
                                      f"Analyze:\n\n{body[:6000]}",
                                      SummaryModel,
                                      {"temperature": 0.0, "num_ctx": 8192})
            # resolve entities/topics into memory
            entity_refs = [MemoryRef(obj_id=rr.obj_id, label=rr.label, kind=rr.kind,
                                     raw=rr.raw)
                           for rr in [memory.resolve(v, "entity", stage="4cat",
                                                     video_key=doc_id)
                                      for v in getattr(payload, "political_entities", [])]
                           ]
            topic_refs = [MemoryRef(obj_id=rr.obj_id, label=rr.label, kind="topic",
                                    raw=rr.raw)
                          for rr in [memory.resolve(v, "topic", stage="4cat",
                                                    video_key=doc_id)
                                     for v in getattr(payload, "key_political_topics", [])]]
            populism = {}
            if with_populism:
                _, Formula = _populism_models()
                pop = chat_structured(model, _populism_system(topic),
                                      payload.model_dump_json(),
                                      Formula,
                                      {"temperature": 0.0, "num_ctx": 8192})
                populism = {
                    "populism_us": [{"obj_id": _resolve_topic(memory, e.populism_element,
                                                              doc_id).obj_id,
                                     "label": e.populism_element,
                                     "affect": e.populism_affect}
                                    for e in pop.populism_us],
                    "populism_frontier": [{"obj_id": _resolve_topic(memory, e.populism_element,
                                                                    doc_id).obj_id,
                                           "label": e.populism_element,
                                           "affect": e.populism_affect}
                                          for e in pop.populism_frontier],
                }
            ann = from_memory_results(
                document_id=doc_id,
                platform=self.dataset.parameters.get("platform", ""),
                language=self.dataset.parameters.get("board_language", ""),
                model=model, run_id=self.dataset.key,
                summary=getattr(payload, "summary", "") or payload.model_dump_json()[:500],
                entity_refs=entity_refs, topic_refs=topic_refs,
                populism=populism or None,
            )
            results.append(ann.model_dump())

        # write output (NDJSON = interchange schema)
        self.dataset.update_status(f"LaclauGPT: writing {len(results)} annotations")
        with self.dataset.get_results_path().open("w", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        self.dataset.finish(len(results))
        memory.export_review_csv(str(self.dataset.get_results_path()) + ".review.csv")


def _resolve_topic(memory, label: str, doc_id: str):
    r = memory.resolve(label, "topic", stage="4cat", video_key=doc_id)
    from laclaugpt.memory import MemoryRef
    return MemoryRef(obj_id=r.obj_id, label=r.label, kind="topic", raw=label)


def _populism_system(topic: str) -> str:
    from prompts import populism as populism_prompt
    return populism_prompt.build_system_prompt(topic, "", "")


def _populism_models():
    from prompts import populism as populism_prompt
    return populism_prompt.pydantic_models()
