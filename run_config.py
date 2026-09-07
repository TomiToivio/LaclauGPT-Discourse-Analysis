# -*- coding: utf-8 -*-
"""Validated run configuration for paper-driven LaclauGPT analyses.

The paper defines three empirical arenas. Their YAML files are the canonical
run specifications; this module loads them instead of silently falling back to
the old hard-coded single-topic configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SourceSpec:
    platform: str
    country: str = ""
    language: str = ""
    query: str = ""
    notes: str = ""


@dataclass
class RunConfig:
    run_id: str
    topic_key: str
    sources: list[SourceSpec]
    paper_section: str = ""
    analytic_hints: dict[str, list[str]] = field(default_factory=dict)
    csv_dir: Path = Path("./csv")
    database_dir: Path = Path("./database")
    keyframe_dir: Path = Path("./Keyframes")
    log_dir: Path = Path("./logs")
    output_path: Path | None = None
    memory_dir: Path | None = None
    model_vision: str = "gemma4:e4b"
    model_text: str = "gemma4:e4b"
    # machine-tier routing: local (GPU machines / cluster nodes) vs
    # cloud (too little GPU / micromodels only). auto probes the endpoint.
    ollama_mode: str = "auto"          # auto | local | cloud | external
    ollama_host: str = ""              # e.g. http://my-gpu-host:11434; default 127.0.0.1:11434
    # Data-boundary policy: a local run must fail locally unless the dataset
    # configuration explicitly permits one retry through Ollama Cloud.
    allow_cloud_fallback: bool = False
    temperature: float = 0.0
    num_ctx: int = 8192
    num_predict: int = 2048
    max_keyframes: int = 6
    min_keyframe_gap: int = 10
    max_video_duration: int = 180
    glossary_max_lines: int = 200
    glossary_lock_threshold: int = 3
    dedup_fuzzy_topic: float = 0.86
    dedup_fuzzy_entity: float = 0.90
    stages: tuple[str, ...] = ("summary", "discourse", "postprocess", "populism")
    multimodal: bool = False
    # priming control (paper §3.6): true runs the same prompts with the
    # ideological seed labels removed, so robustness tables can report how
    # often classifications change when the seeds are ablated.
    ablate_hints: bool = False
    languages: tuple[str, ...] = ()
    config_path: Path | None = None

    def sources_for_language(self, language: str) -> list[SourceSpec]:
        return [s for s in self.sources if s.language == language]

    def source_for_row(self, language: str = "", platform: str = "") -> SourceSpec:
        matches = self.sources_for_language(language) if language else self.sources
        if platform:
            platform_matches = [s for s in matches if s.platform.casefold() == platform.casefold()]
            if platform_matches:
                return platform_matches[0]
        if matches:
            return matches[0]
        return SourceSpec(platform=platform or "unknown", language=language)

    def fingerprint_payload(self) -> dict[str, Any]:
        """Fields that make cached model output analytically reproducible."""
        return {
            "run_id": self.run_id,
            "topic_key": self.topic_key,
            "model": self.model_text,
            "model_vision": self.model_vision,
            "ollama_mode": self.ollama_mode,
            "ollama_host": self.ollama_host,
            "allow_cloud_fallback": self.allow_cloud_fallback,
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
            "stages": list(self.stages),
            "analytic_hints": self.analytic_hints,
            "ablate_hints": self.ablate_hints,
            "sources": [source.__dict__ for source in self.sources],
            "languages": list(self.languages),
            "multimodal": self.multimodal,
        }


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def load_run_config(path: str | Path) -> RunConfig:
    """Load one of the paper's YAML arena specifications."""
    import yaml

    config_path = Path(path).resolve()
    with config_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    missing = [key for key in ("name", "topic_key") if not raw.get(key)]
    if missing:
        raise ValueError(f"run config {config_path} missing: {', '.join(missing)}")

    platforms = _as_tuple(raw.get("source_platform", "unknown"))
    languages = _as_tuple(raw.get("languages") or raw.get("language"))
    countries = _as_tuple(raw.get("countries"))
    source_rows = raw.get("sources") or []
    if source_rows:
        sources = [SourceSpec(**row) for row in source_rows]
    else:
        sources = [
            SourceSpec(
                platform=platform,
                country=country,
                language=language,
                query=str(raw.get("collection_query", "")),
                notes=str(raw.get("collection_notes", "")),
            )
            for platform in platforms
            for country in (countries or ("",))
            for language in (languages or ("",))
        ]

    enabled_stages = tuple(
        name for name, enabled in (raw.get("stages") or {}).items() if bool(enabled)
    ) or ("summary", "discourse", "postprocess", "populism")
    base = config_path.parent.parent
    data_dir = base / "data" / str(raw["name"])
    memory_dir = raw.get("memory_dir")
    analytic_hints = {
        "signifiers": list(raw.get("seed_signifiers") or []),
        "actors": list(raw.get("seed_actors") or []),
        "formations": list(raw.get("seed_formations") or []),
    }
    if raw.get("governance_anchor"):
        analytic_hints["governance_anchors"] = [str(raw["governance_anchor"])]

    cfg = RunConfig(
        run_id=str(raw["name"]),
        topic_key=str(raw["topic_key"]),
        sources=sources,
        paper_section=str(raw.get("paper_section", "")),
        analytic_hints=analytic_hints,
        database_dir=Path(raw.get("database_dir") or data_dir / "database"),
        log_dir=Path(raw.get("log_dir") or data_dir / "logs"),
        output_path=Path(raw.get("output_path") or data_dir / "annotations.jsonl"),
        memory_dir=Path(memory_dir).resolve() if memory_dir else None,
        model_vision=str(raw.get("model_vision") or raw.get("model") or "gemma4:e4b"),
        model_text=str(raw.get("model") or "gemma4:e4b"),
        ollama_mode=str(raw.get("ollama_mode", "auto")).casefold(),
        ollama_host=str(raw.get("ollama_host", "")),
        allow_cloud_fallback=bool(raw.get("allow_cloud_fallback", False)),
        temperature=float(raw.get("temperature", 0.0)),
        num_ctx=int(raw.get("num_ctx", 8192)),
        num_predict=int(raw.get("num_predict", 2048)),
        stages=enabled_stages,
        multimodal=bool(raw.get("multimodal", False)),
        ablate_hints=bool(raw.get("ablate_hints", False)),
        languages=languages,
        config_path=config_path,
    )
    return cfg



def get_run(run_id: str) -> RunConfig:
    candidate = Path(run_id)
    if candidate.suffix.casefold() in {".yaml", ".yml"} or candidate.exists():
        return load_run_config(candidate)
    for cfg in ():
        if cfg.run_id == run_id:
            return cfg
    arena = Path(__file__).resolve().parent / "run_configs" / f"{run_id}.yaml"
    if arena.exists():
        return load_run_config(arena)
    raise KeyError(f"unknown run or YAML config: {run_id}")