from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from laclaugpt.integrations.claude import ClaudeTools
from laclaugpt.integrations.hermes import HermesTools

# Agent-triggered runs require local Ollama only (both Hermes and Claude).
LOCAL_ONLY_ENV = {"LLM_MODE": "local"}


class ClaudeIntegrationTests(unittest.TestCase):
    def test_import_has_no_claude_dependency(self) -> None:
        self.assertNotIn("anthropic", sys.modules)
        self.assertNotIn("claude_code_sdk", sys.modules)

    def test_reuses_the_hermes_tool_surface(self) -> None:
        self.assertTrue(issubclass(ClaudeTools, HermesTools))

    def test_validate_run_forces_agent_execution_and_local_ollama(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tool = ClaudeTools(Path(tmp) / "audit.jsonl", cli=lambda argv: 0)
            with mock.patch.dict("os.environ", LOCAL_ONLY_ENV):
                config = tool.validate_run(
                    project="ai26", arena="elites", machine="roihu", dataset="synthetic.csv"
                )
            self.assertEqual(config["execution"], "agent")
            self.assertEqual(config["dataset"]["input"], "synthetic.csv")

    def test_audit_records_claude_code_actor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.jsonl"
            tool = ClaudeTools(audit, cli=lambda argv: 0)
            with mock.patch.dict("os.environ", LOCAL_ONLY_ENV):
                tool.profiles()
            record = json.loads(audit.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(record["actor"], "claude-code")
            self.assertEqual(record["action"], "profiles")
            self.assertEqual(record["status"], "ok")

    def test_invalid_configuration_is_rejected_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.jsonl"
            tool = ClaudeTools(audit, cli=lambda argv: 0)
            with mock.patch.dict("os.environ", LOCAL_ONLY_ENV):
                with self.assertRaises(Exception):
                    tool.validate_run(
                        project="not-a-project",
                        arena="elites",
                        machine="roihu",
                        dataset="synthetic.csv",
                    )
            record = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(record["action"], "validate_run")
            self.assertEqual(record["status"], "rejected")

    def test_run_analysis_goes_through_canonical_agent_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[list[str]] = []

            def fake_cli(argv):
                calls.append(list(argv or []))
                return 0

            audit = Path(tmp) / "audit.jsonl"
            tool = ClaudeTools(audit, cli=fake_cli)
            with mock.patch.dict("os.environ", LOCAL_ONLY_ENV):
                tool.run_analysis(
                    project="ai26", arena="elites", machine="roihu", dataset="synthetic.csv"
                )
            argv = calls[0]
            self.assertEqual(argv[0], "run")
            self.assertIn("--execution", argv)
            self.assertEqual(argv[argv.index("--execution") + 1], "agent")
            self.assertNotIn("--ollama-mode", argv)
            self.assertNotIn("--allow-cloud-fallback", argv)
            records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(r["action"] == "run_analysis" and r["status"] == "ok" for r in records))

    def test_destructive_actions_are_not_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.jsonl"
            tool = ClaudeTools(audit, cli=lambda argv: 0)
            with self.assertRaises(PermissionError):
                tool.request_destructive_action("push to remote")
            record = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(record["actor"], "claude-code")
            self.assertEqual(record["status"], "rejected")

    def test_cloud_model_routing_is_rejected_for_agents(self) -> None:
        """Claude Code, like Hermes, uses only local Ollama open-source models."""
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.jsonl"
            tool = ClaudeTools(audit, cli=lambda argv: 0)
            for env in (
                {"LLM_MODE": "cloud"},
                {"LACLAUGPT_OLLAMA_MODE": "external", "OLLAMA_HOST": "example.invalid"},
                {"LLM_MODE": "local", "LLM_ALLOW_CLOUD_FALLBACK": "1"},
                {},  # no explicit local mode: auto routing may pick cloud
            ):
                with mock.patch.dict("os.environ", env):
                    with self.assertRaises(PermissionError):
                        tool.validate_run(
                            project="ai26", arena="elites", machine="roihu",
                            dataset="synthetic.csv",
                        )
            records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(
                sum(1 for r in records
                    if r["action"] == "model_policy" and r["status"] == "rejected"),
                4,
            )


if __name__ == "__main__":
    unittest.main()