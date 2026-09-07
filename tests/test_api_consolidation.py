from __future__ import annotations

import importlib
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

from pydantic import ValidationError

from laclaugpt.adapters.interchange import interchange_to_v2
from laclaugpt.model import DiscursiveRoleAssignment
from laclaugpt_interchange import Discourse, DocumentAnnotation, MemoryRef, to_jsonl


class ApiConsolidationTests(unittest.TestCase):
    def test_memory_facade_reexports_persistent_resolution_api(self) -> None:
        import laclaugpt_memory
        from laclaugpt.memory import (
            CanonicalRegistry,
            ContextBuilder,
            Memory,
            MemoryRef as PublicMemoryRef,
            NER_TYPES,
        )

        self.assertIs(Memory, laclaugpt_memory.Memory)
        self.assertIs(PublicMemoryRef, laclaugpt_memory.MemoryRef)
        self.assertIs(NER_TYPES, laclaugpt_memory.NER_TYPES)
        self.assertIsNotNone(CanonicalRegistry)
        self.assertIsNotNone(ContextBuilder)

    def test_memory_facade_does_not_eagerly_import_backend_stack(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import laclaugpt.memory; "
                "assert 'networkx' not in sys.modules, 'memory facade imported networkx'",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_root_memory_module_is_a_legacy_shim_to_public_facade(self) -> None:
        sys.modules.pop("memory", None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            legacy = importlib.import_module("memory")
        from laclaugpt.memory import Memory

        self.assertIs(legacy.ContextMemory, Memory)
        self.assertEqual(legacy.__replacement__, "laclaugpt.memory")
        self.assertTrue(any("legacy compatibility shim" in str(w.message) for w in caught))

    def test_schema_13_interchange_is_readable_by_canonical_and_legacy_paths(self) -> None:
        signifier = MemoryRef(obj_id="S001", label="AI", kind="signifier", raw="AI")
        annotation = DocumentAnnotation(
            document_id="doc-1",
            source_platform="web",
            language="en",
            summary="AI is articulated as abundance.",
            signifiers=[signifier],
            discourses=[Discourse(label="abundance discourse", confidence=0.8,
                                  elements=[signifier])],
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "annotations.jsonl"
            to_jsonl([annotation], str(path))

            canonical = interchange_to_v2(str(path))
            self.assertEqual([source.source_id for source in canonical.sources], ["doc-1"])
            self.assertEqual([d.label for d in canonical.discourses], ["abundance discourse"])

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                from laclaugpt_model.bridge import interchange_to_canonical
                documents, _, concepts, _, _ = interchange_to_canonical(str(path))

            self.assertEqual([document.id for document in documents], ["doc-1"])
            discourse_concepts = [
                concept for concept in concepts
                if concept.attributes.get("kind") == "discourse"
            ]
            self.assertEqual(len(discourse_concepts), 1)
            self.assertEqual(discourse_concepts[0].label, "abundance discourse")
            self.assertEqual(discourse_concepts[0].attributes["element_ids"], ["S001"])

    def test_discursive_role_assignment_requires_evidence(self) -> None:
        with self.assertRaises(ValidationError):
            DiscursiveRoleAssignment(
                concept_id="con-1",
                discourse_id="disc-1",
                role="NODAL_POINT",
                evidence_ids=[],
                provenance_id="prov-1",
            )

        role = DiscursiveRoleAssignment(
            concept_id="con-1",
            discourse_id="disc-1",
            role="NODAL_POINT",
            evidence_ids=["ev-1"],
            provenance_id="prov-1",
        )
        self.assertEqual(role.evidence_ids, ["ev-1"])


if __name__ == "__main__":
    unittest.main()
