from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from laclaugpt.integrations.hermes import HermesTools

# Agent-triggered runs require local Ollama only (both Hermes and Claude).
LOCAL_ONLY_ENV = {"LLM_MODE": "local"}


class HermesIntegrationTests(unittest.TestCase):
    def test_import_has_no_external_hermes_dependency(self) -> None:
        self.assertNotIn("hermes", sys.modules)

    def test_validate_run_forces_agent_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tool = HermesTools(Path(tmp) / "audit.jsonl", cli=lambda argv: 0)
            with mock.patch.dict("os.environ", LOCAL_ONLY_ENV):
                config = tool.validate_run(
                    project="ai26", arena="elites", machine="roihu", dataset="synthetic.csv"
                )
            self.assertEqual(config["execution"], "agent")
            self.assertEqual(config["dataset"]["input"], "synthetic.csv")

    def test_invalid_configuration_is_rejected_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.jsonl"
            tool = HermesTools(audit, cli=lambda argv: 0)
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

    def test_dry_run_calls_only_canonical_agent_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[list[str]] = []

            def fake_cli(argv):
                calls.append(list(argv or []))
                return 0

            audit = Path(tmp) / "audit.jsonl"
            tool = HermesTools(audit, cli=fake_cli)
            with mock.patch.dict("os.environ", LOCAL_ONLY_ENV):
                code = tool.dry_run(
                    project="ai26", arena="elites", machine="roihu", dataset="synthetic.csv"
                )
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            self.assertIn("--execution", calls[0])
            self.assertEqual(calls[0][calls[0].index("--execution") + 1], "agent")
            self.assertNotIn("--ollama-mode", calls[0])
            self.assertNotIn("--allow-cloud-fallback", calls[0])
            records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(r["action"] == "dry_run" and r["status"] == "ok" for r in records))

    def test_analysis_run_is_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls: list[list[str]] = []

            def fake_cli(argv):
                calls.append(list(argv or []))
                return 0

            audit = Path(tmp) / "audit.jsonl"
            tool = HermesTools(audit, cli=fake_cli)
            with mock.patch.dict("os.environ", LOCAL_ONLY_ENV):
                tool.run_analysis(
                    project="ai26", arena="elites", machine="roihu", dataset="synthetic.csv"
                )
            argv = calls[0]
            self.assertEqual(argv[0], "run")
            self.assertEqual(argv[argv.index("--execution") + 1], "agent")
            records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(r["action"] == "run_analysis" and r["status"] == "ok" for r in records))

    def test_destructive_actions_are_not_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.jsonl"
            tool = HermesTools(audit, cli=lambda argv: 0)
            with self.assertRaises(PermissionError):
                tool.request_destructive_action("delete dataset")
            record = json.loads(audit.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(record["status"], "rejected")

    def test_cloud_model_routing_is_rejected_for_agents(self) -> None:
        """Agents use only local Ollama open-source models."""
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.jsonl"
            tool = HermesTools(audit, cli=lambda argv: 0)
            # explicit cloud mode
            with mock.patch.dict("os.environ", {"LLM_MODE": "cloud"}):
                with self.assertRaises(PermissionError):
                    tool.validate_run(
                        project="ai26", arena="elites", machine="roihu",
                        dataset="synthetic.csv",
                    )
            # auto routing may resolve to cloud on a weak machine
            with mock.patch.dict("os.environ", {"LLM_MODE": "auto"}):
                with self.assertRaises(PermissionError):
                    tool.validate_run(
                        project="ai26", arena="elites", machine="roihu",
                        dataset="synthetic.csv",
                    )
            # authorised cloud fallback is equally forbidden under local mode
            with mock.patch.dict("os.environ", {
                "LLM_MODE": "local", "LLM_ALLOW_CLOUD_FALLBACK": "1",
            }):
                with self.assertRaises(PermissionError):
                    tool.validate_run(
                        project="ai26", arena="elites", machine="roihu",
                        dataset="synthetic.csv",
                    )
            records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(
                sum(1 for r in records
                    if r["action"] == "model_policy" and r["status"] == "rejected"),
                3,
            )


if __name__ == "__main__":
    unittest.main()