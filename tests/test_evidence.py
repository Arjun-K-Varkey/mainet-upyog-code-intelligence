import json
import unittest

from src.aca_evidence import (
    EVIDENCE_TYPES, Evidence, EvidenceSource, EvidenceValidationError, SCHEMA_VERSION,
    EvidenceRegistry, EvidenceResolver,
)


class EvidenceTests(unittest.TestCase):
    def source(self, file="src/example.java"):
        return EvidenceSource("aca-test", "1.0", file=file, start_line=10, end_line=12)

    def kwargs(self, **overrides):
        data = dict(
            project_id="ACA", repository_id="REPO", revision="REV1", run_id="RUN1",
            type="source", subject="src/example.java", source=self.source(),
            value={"classification": "java", "nested": {"b": 2, "a": 1}},
        )
        data.update(overrides)
        return data

    def test_minimal_valid_record(self):
        e = Evidence.create(**self.kwargs())
        self.assertTrue(e.id.startswith("EVID-"))
        self.assertEqual(e.status, "VALID")
        self.assertEqual(e.validate(), [])

    def test_deterministic_identity_ignores_mapping_order(self):
        a = Evidence.create(**self.kwargs(value={"b": 2, "a": 1}))
        b = Evidence.create(**self.kwargs(value={"a": 1, "b": 2}))
        self.assertEqual(a.id, b.id)
        self.assertEqual(a.to_json(), b.to_json())

    def test_deterministic_identity_ignores_list_order(self):
        a = Evidence.create(**self.kwargs(value={"items": ["a", "b"]}))
        b = Evidence.create(**self.kwargs(value={"items": ["b", "a"]}))
        self.assertEqual(a.id, b.id)
        self.assertEqual(a.to_json(), b.to_json())

    def test_deterministic_identity_ignores_nested_list_order(self):
        a = Evidence.create(**self.kwargs(value={"items": [{"b": 2, "a": 1}, {"x": [2, 1]}]}))
        b = Evidence.create(**self.kwargs(value={"items": [{"x": [1, 2]}, {"a": 1, "b": 2}]}))
        self.assertEqual(a.id, b.id)

    def test_identity_independent_of_absolute_checkout_path(self):
        a = Evidence.create(**self.kwargs(subject="src/example.java", value={"path": "src/example.java"}))
        b = Evidence.create(**self.kwargs(subject="src/example.java", value={"path": "src/example.java"}))
        self.assertEqual(a.id, b.id)

    def test_absolute_source_path_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            EvidenceSource("aca-test", "1.0", file="/tmp/example.java")

    def test_windows_absolute_source_path_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            EvidenceSource("aca-test", "1.0", file="C:\\\\repo\\\\example.java")

    def test_id_tampering_rejected(self):
        e = Evidence.create(**self.kwargs())
        raw = e.to_dict()
        raw["id"] = "EVID-TAMPERED"
        with self.assertRaises(EvidenceValidationError):
            Evidence.from_dict(raw)

    def test_invalid_type_and_status_rejected(self):
        data = self.kwargs(type="not-a-type", status="NOPE")
        with self.assertRaises(EvidenceValidationError):
            Evidence.create(**data)

    def test_invalid_source_line_range_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            EvidenceSource("aca-test", "1.0", file="x.java", start_line=12, end_line=11)

    def test_unsupported_value_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            Evidence.create(**self.kwargs(value={"bad": object()}))

    def test_lifecycle_states(self):
        for status in ("VALID", "STALE", "INVALID", "REDACTED"):
            e = Evidence.create(**self.kwargs(status=status))
            self.assertEqual(e.status, status)

    def test_secret_like_values_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            Evidence.create(**self.kwargs(value={"password": "super-secret"}))

    def test_redacted_secret_is_allowed(self):
        e = Evidence.create(**self.kwargs(status="REDACTED", value={"password": "[REDACTED]"}))
        self.assertEqual(e.status, "REDACTED")

    def test_redacted_status_does_not_allow_raw_secret(self):
        with self.assertRaises(EvidenceValidationError):
            Evidence.create(**self.kwargs(status="REDACTED", value={"password": "still-secret"}))

    def test_json_round_trip(self):
        e = Evidence.create(**self.kwargs(observed_at="2026-09-20T00:00:00Z"))
        restored = Evidence.from_dict(json.loads(e.to_json()))
        self.assertEqual(restored.to_json(), e.to_json())

    def test_repeated_serialization_is_byte_stable(self):
        e = Evidence.create(**self.kwargs())
        self.assertEqual(e.to_json(), e.to_json())

    def test_immutable_value(self):
        e = Evidence.create(**self.kwargs())
        with self.assertRaises(TypeError):
            e.value["classification"] = "changed"

    def test_context_mismatch(self):
        e = Evidence.create(**self.kwargs())
        with self.assertRaises(EvidenceValidationError):
            e.require_valid(repository_id="OTHER")

    def test_registry_resolves_canonical_evidence(self):
        e = Evidence.create(**self.kwargs())
        resolver = EvidenceResolver(EvidenceRegistry([e]))
        self.assertEqual(resolver.resolve((e.id,), repository_id="REPO", revision="REV1", run_id="RUN1"), (e.id,))

    def test_registry_rejects_unresolved_or_wrong_context(self):
        e = Evidence.create(**self.kwargs())
        resolver = EvidenceResolver(EvidenceRegistry([e]))
        with self.assertRaises(EvidenceValidationError): resolver.resolve(("EVID-MISSING",))
        with self.assertRaises(EvidenceValidationError): resolver.resolve((e.id,), repository_id="OTHER", revision="REV1", run_id="RUN1")

    def test_registry_rejects_conflicting_duplicate_id(self):
        e = Evidence.create(**self.kwargs())
        other = Evidence.create(**self.kwargs(value={"classification": "other"}))
        from dataclasses import replace
        with self.assertRaises(EvidenceValidationError): EvidenceRegistry([e, replace(other, id=e.id)])

    def test_reference_id_is_stable_and_schema_versioned(self):
        e = Evidence.create(**self.kwargs())
        self.assertEqual(e.to_dict()["schema_version"], SCHEMA_VERSION)
        self.assertIn(e.id, e.to_json())


if __name__ == "__main__":
    unittest.main()
