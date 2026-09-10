from laclaugpt.config import compose_config, list_executions, list_machines


def _compose(machine: str, execution: str):
    return compose_config("ai26", machine, execution, arena="elites")


def test_required_machine_profiles_exist():
    machines = set(list_machines())
    assert {
        "laptop-collector",
        "laptop-ollama",
        "laptop-cloud",
        "linux-dashboard",
        "linux-gpu-realtime",
        "roihu",
    } <= machines


def test_required_execution_profiles_exist():
    executions = set(list_executions())
    assert {
        "collector-only",
        "local-analysis",
        "cloud-analysis",
        "dashboard-only",
        "realtime-fullstack",
        "slurm",
    } <= executions


def test_laptop_collector_has_no_llm_analysis_or_dashboard():
    cfg = _compose("laptop-collector", "collector-only")
    services = cfg["services"]
    runtime = cfg["orchestration"]["runtime"]
    assert services["collector"]["enabled"] is True
    assert services["analysis"]["enabled"] is False
    assert services["dashboard"]["enabled"] is False
    assert services["llm"]["mode"] == "none"
    assert runtime == {
        "collector": True,
        "analysis": False,
        "dashboard": False,
        "slurm": False,
    }


def test_laptop_local_analysis_uses_small_ollama_model():
    cfg = _compose("laptop-ollama", "local-analysis")
    services = cfg["services"]
    assert services["analysis"]["enabled"] is True
    assert services["llm"]["mode"] == "local"
    assert services["llm"]["provider"] == "ollama"
    assert services["llm"]["model"] == "gemma4:e2b"
    assert services["dashboard"]["enabled"] is False


def test_laptop_cloud_analysis_uses_cloud_model():
    cfg = _compose("laptop-cloud", "cloud-analysis")
    llm = cfg["services"]["llm"]
    assert llm["mode"] == "cloud"
    assert llm["model"] == "gemma4:31b-cloud"
    assert cfg["orchestration"]["runtime"]["analysis"] is True


def test_linux_dashboard_requires_neither_collector_nor_llm():
    cfg = _compose("linux-dashboard", "dashboard-only")
    services = cfg["services"]
    assert services["dashboard"]["enabled"] is True
    assert services["collector"]["enabled"] is False
    assert services["analysis"]["enabled"] is False
    assert services["llm"]["mode"] == "none"


def test_linux_gpu_realtime_runs_all_services_with_local_ollama():
    cfg = _compose("linux-gpu-realtime", "realtime-fullstack")
    services = cfg["services"]
    assert services["collector"]["enabled"] is True
    assert services["analysis"]["enabled"] is True
    assert services["dashboard"]["enabled"] is True
    assert services["llm"]["mode"] == "local"
    assert services["llm"]["model"] == "gemma4:26b"
    assert cfg["orchestration"]["runtime"]["incremental"] is True


def test_roihu_is_slurm_analysis_only():
    cfg = _compose("roihu", "slurm")
    services = cfg["services"]
    runtime = cfg["orchestration"]["runtime"]
    assert services["collector"]["enabled"] is False
    assert services["analysis"]["enabled"] is True
    assert services["dashboard"]["enabled"] is False
    assert services["llm"]["mode"] == "local"
    assert services["llm"]["model"] == "gemma4:26b"
    assert runtime["slurm"] is True
    assert runtime["collector"] is False
    assert runtime["dashboard"] is False


def test_research_semantics_do_not_change_with_machine_topology():
    local_cfg = _compose("laptop-ollama", "local-analysis")
    roihu_cfg = _compose("roihu", "slurm")
    assert local_cfg["analysis"] == roihu_cfg["analysis"]
    assert local_cfg["codebook"] == roihu_cfg["codebook"]
    assert local_cfg["dataset"] == roihu_cfg["dataset"]
