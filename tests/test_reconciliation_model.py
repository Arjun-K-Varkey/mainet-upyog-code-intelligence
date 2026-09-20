import unittest

from src.aca_reconciliation import (
    CandidateMapping,
    ReconciliationFinding,
    ReconciliationRequest,
    ReconciliationResult,
    RepositoryContext,
)


class ReconciliationModelTests(unittest.TestCase):
    def contexts(self):
        source = RepositoryContext(
            project_id="p", repository_id="mainet", revision="r1",
            analysis_run_id="run-mainet", graph_schema_version="aca-graph-0.2",
            evidence_schema_version="aca-evidence-0.2",
        )
        target = RepositoryContext(
            project_id="p", repository_id="upyog", revision="r2",
            analysis_run_id="run-upyog", graph_schema_version="aca-graph-0.2",
            evidence_schema_version="aca-evidence-0.2",
        )
        return source, target

    def request(self):
        source, target = self.contexts()
        return ReconciliationRequest(
            reconciliation_id="recon-1",
            source_context=source,
            target_context=target,
        )

    def test_candidate_mapping_identity_is_stable(self):
        mapping1 = CandidateMapping.create(
            "NODE-A", "NODE-B", reconciliation_id="recon-1",
            methodology_version="aca-recon-method-0.1",
            state="CONFIRMED", provenance="deterministic",
            evidence_refs=("E2", "E1"), mapping_signals=("signature", "identity"),
        )
        mapping2 = CandidateMapping.create(
            "NODE-A", "NODE-B", reconciliation_id="recon-1",
            methodology_version="aca-recon-method-0.1",
            state="CONFIRMED", provenance="deterministic",
            evidence_refs=("E1", "E2"), mapping_signals=("identity", "signature"),
        )
        self.assertEqual(mapping1.mapping_id, mapping2.mapping_id)
        self.assertEqual(mapping1.evidence_refs, ("E1", "E2"))
        self.assertEqual(mapping1.mapping_signals, ("identity", "signature"))

    def test_candidate_mapping_identity_includes_repository_context(self):
        m1 = CandidateMapping.create(
            "NODE-A", "NODE-B", reconciliation_id="recon-1",
            methodology_version="aca-recon-method-0.1",
            state="CONFIRMED", provenance="deterministic",
            source_repository_id="mainet", source_revision="r1",
            target_repository_id="upyog", target_revision="r2",
        )
        m2 = CandidateMapping.create(
            "NODE-A", "NODE-B", reconciliation_id="recon-1",
            methodology_version="aca-recon-method-0.1",
            state="CONFIRMED", provenance="deterministic",
            source_repository_id="other", source_revision="r1",
            target_repository_id="upyog", target_revision="r2",
        )
        self.assertNotEqual(m1.mapping_id, m2.mapping_id)

    def test_result_serialization_is_deterministic(self):
        source, target = self.contexts()
        req = self.request()
        mapping = CandidateMapping.create(
            "NODE-A", "NODE-B", reconciliation_id="recon-1",
            methodology_version=req.methodology_version,
            state="CONFIRMED", provenance="deterministic",
            evidence_refs=("E1",),
        )
        finding = ReconciliationFinding.create(
            "MATCH", "CONFIRMED", "deterministic", "NODE-A", "NODE-B",
            source, target, reconciliation_id="recon-1", evidence_refs=("E1",),
            related_mapping_ids=(mapping.mapping_id,),
        )
        result1 = ReconciliationResult(
            "recon-1", source, target, req, mappings=(mapping,), findings=(finding,),
            summaries={"matches": 1},
        )
        result2 = ReconciliationResult(
            "recon-1", source, target, req, mappings=(mapping,), findings=(finding,),
            summaries={"matches": 1},
        )
        self.assertEqual(result1.to_json(), result2.to_json())

    def test_ambiguous_mapping_requires_alternatives(self):
        source, target = self.contexts()
        req = self.request()
        mapping = CandidateMapping.create(
            "NODE-A", "NODE-B", reconciliation_id="recon-1",
            methodology_version=req.methodology_version,
            state="AMBIGUOUS", provenance="deterministic",
        )
        result = ReconciliationResult("recon-1", source, target, req, mappings=(mapping,))
        self.assertIn(
            {"code": "AMBIGUOUS_MISSING_ALTERNATIVES", "id": mapping.mapping_id},
            result.validate(),
        )

    def test_inferred_mapping_requires_confidence(self):
        source, target = self.contexts()
        req = self.request()
        mapping = CandidateMapping.create(
            "NODE-A", "NODE-B", reconciliation_id="recon-1",
            methodology_version=req.methodology_version,
            state="INFERRED", provenance="inferred",
        )
        result = ReconciliationResult("recon-1", source, target, req, mappings=(mapping,))
        self.assertIn(
            {"code": "INFERRED_MISSING_CONFIDENCE", "id": mapping.mapping_id},
            result.validate(),
        )

    def test_unknown_finding_requires_boundary(self):
        source, target = self.contexts()
        req = self.request()
        finding = ReconciliationFinding.create(
            "UNRESOLVED", "UNKNOWN", "deterministic", "NODE-A", None,
            source, target, reconciliation_id="recon-1",
        )
        result = ReconciliationResult("recon-1", source, target, req, findings=(finding,))
        self.assertIn({"code": "UNKNOWN_MISSING_BOUNDARY", "id": finding.finding_id}, result.validate())

    def test_different_repository_contexts_are_required(self):
        source, _ = self.contexts()
        req = self.request()
        result = ReconciliationResult("recon-1", source, source, req)
        self.assertIn({"code": "IDENTICAL_REPOSITORY_CONTEXTS"}, result.validate())

    def test_finding_identity_is_stable(self):
        source, target = self.contexts()
        f1 = ReconciliationFinding.create(
            "STRUCTURAL_CHANGE", "CONFIRMED", "deterministic", "A", "B",
            source, target, reconciliation_id="recon-1",
            evidence_refs=("E2", "E1"), related_mapping_ids=("M2", "M1"),
        )
        f2 = ReconciliationFinding.create(
            "STRUCTURAL_CHANGE", "CONFIRMED", "deterministic", "A", "B",
            source, target, reconciliation_id="recon-1",
            evidence_refs=("E1", "E2"), related_mapping_ids=("M1", "M2"),
        )
        self.assertEqual(f1.finding_id, f2.finding_id)


if __name__ == "__main__":
    unittest.main()
