# -*- coding: utf-8 -*-
"""Pipeline-facing adapter for the canonical LaclauGPT configuration chain.

New executions are composed by :mod:`laclaugpt.config` as
project -> arena -> machine -> execution -> EffectiveRunConfig.  This module no
longer owns a second research configuration system: ``RunConfig`` is the compact
shape consumed by the historical root pipeline implementation.

The three old ``run_configs/arena_*.yaml`` files remain accepted as deprecated
aliases for their matching canonical ``config/arenas/*.yaml`` profiles.  Custom
legacy YAML files are still loadable for reproducibility and old tests/scripts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass
class SourceSpec:
    platform: str
    country: str = ""
    language: str = ""
    query: str = ""
    notes: str = ""


@dataclass
class RunConfig:
    # Execution-instance identity. In canonical execution this is exactly the
    # RunStore/Run.run_id, never the arena/profile name.
    run_id: str
    topic_key: str
    sources: list[SourceSpec]
    analysis_profile: str = ""
    arena_id: str = ""
    project: str = ""
    analysis_modules: dict[str, bool] = field(default_factory=dict)
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
    ollama_mode: str = "auto"
    ollama_host: str = ""
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
    ablate_hints: bool = False
    languages: tuple[str, ...] = ()
    config_path: Path | None = None

    def enabled(self, module: str) -> bool:
        return bool(self.analysis_modules.get(module, False))

    def sources_for_language(self, language: str) -> list[SourceSpec]:
        return [s for s in self.sources if s.language == language]

    def source_for_row(self, language: str = "", platform: str = "") -> SourceSpec:
        matches = self.sources_for_language(language) if language else self.sources
        if platform:
            platform_matches = [
                s for s in matches if s.platform.casefold() == platform.casefold()
            ]
            if platform_matches:
                return platform_matches[0]
        if matches:
            return matches[0]
        return SourceSpec(platform=platform or "unknown", language=language)

    def fingerprint_payload(self) -> dict[str, Any]:
        """Fields making stage-cache output analytically reproducible."""
        return {
            "run_id": self.run_id,
            "analysis_profile": self.analysis_profile,
            "arena_id": self.arena_id,
            "project": self.project,
            "analysis_modules": dict(sorted(self.analysis_modules.items())),
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


def stages_for_analysis(analysis: Mapping[str, bool]) -> tuple[str, ...]:
    """Map authoritative project module switches onto implemented stages."""
    stages = ["summary"]
    # Palonen consumes the discourse description even when Laclaudian output is
    # disabled, so it also requires the shared discourse-model call.
    if any(bool(analysis.get(name)) for name in (
        "laclau", "sociotechnical_imaginaries", "palonen"
    )):
        stages.append("discourse")
    if any(bool(analysis.get(name)) for name in ("topics", "entities", "sentiment")):
        stages.append("postprocess")
    if bool(analysis.get("palonen")):
        stages.append("populism")
    return tuple(stages)


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def _get(config: Any, key: str, default: Any = None) -> Any:
    if isinstance(config, Mapping):
        return config.get(key, default)
    return getattr(config, key, default)


def _sources_from_dataset(dataset: Mapping[str, Any]) -> list[SourceSpec]:
    source_rows = dataset.get("sources") or []
    if source_rows:
        return [SourceSpec(**dict(row)) for row in source_rows]
    platforms = _as_tuple(dataset.get("platforms") or dataset.get("source_platform") or "unknown")
    languages = _as_tuple(dataset.get("languages") or dataset.get("language"))
    countries = _as_tuple(dataset.get("countries"))
    return [
        SourceSpec(
            platform=platform,
            country=country,
            language=language,
            query=str(dataset.get("collection_query", "")),
            notes=str(dataset.get("collection_notes", "")),
        )
        for platform in platforms
        for country in (countries or ("",))
        for language in (languages or ("",))
    ]


def run_config_from_effective(config: Any, run_id: str, *,
                              repository_root: str | Path | None = None) -> RunConfig:
    """Adapt one composed effective config to the root pipeline runtime shape."""
    dataset = dict(_get(config, "dataset", {}) or {})
    analysis = {
        str(key): bool(value) for key, value in dict(_get(config, "analysis", {}) or {}).items()
    }
    model = dict(dataset.get("model") or {})
    policy = dict(dataset.get("data_policy") or {})
    storage = dict(dataset.get("storage") or {})
    root = Path(repository_root or Path(__file__).resolve().parent).resolve()
    work_dir = Path(storage.get("work_dir") or f"data/{_get(config, 'analysis_profile', 'analysis')}")
    if not work_dir.is_absolute():
        work_dir = root / work_dir
    memory_dir = storage.get("memory_dir")
    resolved_memory = None
    if memory_dir:
        resolved_memory = Path(memory_dir)
        if not resolved_memory.is_absolute():
            resolved_memory = root / resolved_memory

    languages = _as_tuple(dataset.get("languages") or dataset.get("language"))
    hints = {
        str(kind): [str(value) for value in values]
        for kind, values in dict(dataset.get("analytic_hints") or {}).items()
    }
    pipeline_options = dict(dataset.get("pipeline") or {})

    return RunConfig(
        run_id=str(run_id),
        analysis_profile=str(_get(config, "analysis_profile", "")),
        arena_id=str(_get(config, "arena", "") or dataset.get("arena_id") or ""),
        project=str(_get(config, "project", "")),
        analysis_modules=analysis,
        topic_key=str(dataset.get("topic_key") or _get(config, "project", "generic")),
        sources=_sources_from_dataset(dataset),
        paper_section=str(dataset.get("paper_section", "")),
        analytic_hints=hints,
        database_dir=work_dir / "database",
        log_dir=work_dir / "logs",
        output_path=Path(dataset["output"]) if dataset.get("output") else work_dir / "annotations.jsonl",
        memory_dir=resolved_memory,
        model_vision=str(model.get("vision") or model.get("text") or "gemma4:e4b"),
        model_text=str(model.get("text") or "gemma4:e4b"),
        ollama_mode=str(model.get("ollama_mode", "auto")).casefold(),
        ollama_host=str(model.get("ollama_host", "")),
        allow_cloud_fallback=bool(policy.get("allow_cloud_fallback", False)),
        temperature=float(model.get("temperature", 0.0)),
        num_ctx=int(model.get("num_ctx", 8192)),
        num_predict=int(model.get("num_predict", 2048)),
        stages=stages_for_analysis(analysis),
        multimodal=bool(analysis.get("multimodal", False)),
        ablate_hints=bool(dataset.get("ablate_hints", pipeline_options.get("ablate_hints", False))),
        languages=languages,
        config_path=None,
    )


def _load_legacy_yaml(config_path: Path) -> RunConfig:
    """Generic compatibility loader for non-migrated historical/custom YAML."""
    import yaml

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

    # Infer module switches only for this compatibility path. Canonical runs
    # always get them from config/projects/*.yaml.
    legacy_modules = {
        "laclau": "discourse" in enabled_stages,
        "sociotechnical_imaginaries": "discourse" in enabled_stages,
        "palonen": "populism" in enabled_stages,
        "topics": "postprocess" in enabled_stages,
        "entities": "postprocess" in enabled_stages,
        "sentiment": "postprocess" in enabled_stages,
        "context_memory": True,
        "temporal": True,
        "multimodal": bool(raw.get("multimodal", False)),
    }
    return RunConfig(
        run_id=str(raw["name"]),
        analysis_profile=f"legacy:{raw['name']}",
        arena_id=str(raw["name"]),
        project="legacy",
        analysis_modules=legacy_modules,
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


def load_run_config(path: str | Path) -> RunConfig:
    """Load a deprecated arena alias or generic historical run YAML."""
    from laclaugpt.config import arena_from_legacy_config, compose_config

    config_path = Path(path).resolve()
    try:
        arena = arena_from_legacy_config(config_path)
    except ValueError:
        return _load_legacy_yaml(config_path)

    effective = compose_config("ai26", "roihu", "cli", arena=arena)
    cfg = run_config_from_effective(
        effective, run_id=f"arena-{arena}", repository_root=Path(__file__).resolve().parent
    )
    cfg.config_path = config_path
    return cfg


def get_run(run: str | Path | RunConfig) -> RunConfig:
    if isinstance(run, RunConfig):
        return run
    candidate = Path(run)
    if candidate.suffix.casefold() in {".yaml", ".yml"} or candidate.exists():
        return load_run_config(candidate)
    arena = Path(__file__).resolve().parent / "run_configs" / f"{run}.yaml"
    if arena.exists():
        return load_run_config(arena)
    raise KeyError(f"unknown run or YAML config: {run}")
