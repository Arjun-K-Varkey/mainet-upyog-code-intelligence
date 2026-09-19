import json
import unittest

from src.aca_graph import Edge, Graph, Node
from src.aca_graph.trace import (
    ANALYZER_VERSION,
    METHODOLOGY_VERSION,
    CandidatePath,
    Trace,
    TraceBoundary,
    TraceEngine,
    TraceRequest,
    TraceStep,
    TraceValidationError,
    TraceRule,
    TraceRuleRegistry,
)


class TraceEngineTests(unittest.TestCase):
    RUN = "RUN"
    REV = "REV1"

    def graph(self):
        graph = Graph({"id": "REPO"}, self.REV, self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN, revision=self.REV)
        b = Node.create("Module", "REPO", "module:b", analysis_run_id=self.RUN, revision=self.REV)
        c = Node.create("File", "REPO", "file:c", analysis_run_id=self.RUN, revision=self.REV)
        for node in (a, b, c):
            graph.add_node(node)
        graph.evidence["E1"] = {"source": "test"}
        graph.add_edge(Edge.create(a, "CONTAINS", b, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        graph.add_edge(Edge.create(b, "CONTAINS", c, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        graph.require_valid()
        return graph, a, b, c

    def test_confirmed_trace_has_canonical_steps(self):
        graph, a, b, c = self.graph()
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=2))
        self.assertEqual(result.status, "CONFIRMED")
        self.assertEqual([s.sequence for s in result.steps], [1, 2])
        self.assertEqual(result.steps[0].source_node, a.id)
        self.assertEqual(result.steps[0].target_node, b.id)
        self.assertEqual(result.steps[1].target_node, c.id)
        self.assertEqual(result.steps[0].provenance, "deterministic")
        self.assertEqual(result.evidence, ("E1",))

    def test_depth_limit_creates_unknown_boundary(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=1))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.boundaries[0].boundary_type, "MISSING_EVIDENCE")

    def test_relationship_filter(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(
            TraceRequest(a.id, target_id=c.id, excluded_relations=("CONTAINS",), max_depth=2)
        )
        self.assertEqual(result.status, "UNKNOWN")

    def test_incoming_trace(self):
        graph, a, b, c = self.graph()
        result = TraceEngine(graph).trace(
            TraceRequest(c.id, target_id=a.id, direction="INCOMING", max_depth=2)
        )
        self.assertEqual(result.status, "CONFIRMED")
        self.assertEqual(result.steps[0].source_node, c.id)
        self.assertEqual(result.steps[0].target_node, b.id)
        self.assertEqual(result.steps[0].relation, "CONTAINS")
        self.assertIn(result.steps[0].evidence_refs[0], graph.evidence)

    def test_explicit_boundary_evidence_produces_unknown(self):
        graph, a, b, _ = self.graph()
        edge = next(iter(graph.outgoing(a.id)))
        graph.evidence["E_BOUNDARY"] = {
            "boundary_type": "reflection",
            "reason": "Target is reached through reflection.",
        }
        from dataclasses import replace
        replacement = replace(edge, evidence_refs=("E_BOUNDARY",))
        graph.edges[replacement.id] = replacement
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=b.id, max_depth=1))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.steps[0].status, "UNKNOWN")
        self.assertEqual(result.boundaries[0].boundary_type, "REFLECTION")

    def test_ambiguous_path_preserves_missing_evidence_boundary(self):
        graph, a, b, c = self.graph()
        edge = next(iter(graph.outgoing(a.id)))
        from dataclasses import replace
        graph.edges[edge.id] = replace(edge, evidence_refs=())
        result = TraceEngine(graph).trace(TraceRequest(a.id, max_depth=1, max_paths=2))
        self.assertTrue(any(b.boundary_type == "MISSING_EVIDENCE" for b in result.boundaries + tuple(
            boundary for candidate in result.alternatives for boundary in candidate.boundaries
        )))

    def test_incoming_contradiction_matches_canonical_edge(self):
        graph, a, b, _ = self.graph()
        edge = next(iter(graph.outgoing(a.id)))
        from src.aca_graph import Edge
        conflicting = Edge.create(
            a, "DEPENDS_ON", b, evidence_refs=("E_CONTRADICTION",),
            analysis_run_id=self.RUN, revision=self.REV)
        graph.add_edge(conflicting)
        graph.evidence["E_CONTRADICTION"] = {
            "type": "contradiction",
            "edge_ids": [edge.id, conflicting.id],
            "claims": [{
                "source_node": edge.source, "relation": edge.relation,
                "target_node": edge.target, "evidence_refs": ["E_CONTRADICTION"],
            }, {
                "source_node": conflicting.source, "relation": conflicting.relation,
                "target_node": conflicting.target, "evidence_refs": ["E_CONTRADICTION"],
            }],
            "affected_step": 1, "resolution_state": "UNRESOLVED",
            "evidence_refs": ["E_CONTRADICTION"],
        }
        result = TraceEngine(graph).trace(TraceRequest(b.id, target_id=a.id, direction="INCOMING", max_depth=1))
        self.assertEqual(result.status, "CONTRADICTED")


    def test_ambiguous_trace_aggregates_candidate_boundaries(self):
        graph, a, b, c = self.graph()
        from dataclasses import replace
        edge = next(iter(graph.outgoing(a.id)))
        graph.evidence["E_BOUNDARY"] = {
            "boundary_type": "reflection",
            "reason": "Reflection prevents deterministic resolution.",
        }
        graph.edges[edge.id] = replace(edge, evidence_refs=("E_BOUNDARY",))
        d = Node.create("File", "REPO", "file:d", analysis_run_id=self.RUN, revision=self.REV)
        graph.add_node(d)
        graph.add_edge(Edge.create(a, "CONTAINS", d, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        graph.add_edge(Edge.create(d, "CONTAINS", c, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=3))
        self.assertEqual(result.status, "AMBIGUOUS")
        self.assertIn("REFLECTION", {b.boundary_type for b in result.boundaries})
        self.assertTrue(any(
            b.boundary_type == "REFLECTION"
            for candidate in result.alternatives
            for b in candidate.boundaries
        ))

    def test_contradicted_trace_aggregates_candidate_boundaries(self):
        graph, a, b, _ = self.graph()
        edge = next(iter(graph.outgoing(a.id)))
        from dataclasses import replace
        graph.evidence["E_BOUNDARY"] = {
            "boundary_type": "reflection",
            "reason": "Reflection prevents deterministic resolution.",
        }
        graph.edges[edge.id] = replace(edge, evidence_refs=("E_BOUNDARY",))
        conflicting = Edge.create(a, "DEPENDS_ON", b, evidence_refs=("E_CONTRADICTION",),
                                  analysis_run_id=self.RUN, revision=self.REV)
        graph.add_edge(conflicting)
        graph.evidence["E_CONTRADICTION"] = {
            "type": "contradiction",
            "edge_ids": [edge.id, conflicting.id],
            "affected_step": 1,
            "resolution_state": "UNRESOLVED",
        }
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=b.id, max_depth=1))
        self.assertEqual(result.status, "CONTRADICTED")
        self.assertIn("REFLECTION", {b.boundary_type for b in result.boundaries})
        self.assertIn("UNRESOLVED_PATH", {b.boundary_type for b in result.boundaries})

    def test_serialized_edge_identity_is_validated(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=2))
        data = result.to_dict()
        data["steps"][0]["edge_id"] = "EDGE-TAMPERED"
        with self.assertRaises(TraceValidationError):
            Trace.from_dict(data, graph=graph)

        public_errors = __import__("src.aca_graph.trace", fromlist=["validate_trace_dict"]).validate_trace_dict(data, graph=graph)
        self.assertTrue(public_errors)

    def test_incoming_edge_identity_rejects_wrong_orientation(self):
        graph, a, b, _ = self.graph()
        result = TraceEngine(graph).trace(
            TraceRequest(b.id, target_id=a.id, direction="INCOMING", max_depth=1)
        )
        data = result.to_dict()
        data["steps"][0]["traversal_direction"] = "OUTGOING"
        with self.assertRaises(TraceValidationError):
            Trace.from_dict(data, graph=graph)

    def test_injected_rule_registry_is_used(self):
        graph, a, b, _ = self.graph()

        class CustomRule(TraceRule):
            name = "custom-rule"
            version = "custom-1"
            def classify(self, edge):
                return "INFERRED", "inferred", 0.7

        registry = TraceRuleRegistry((CustomRule(),))
        result = TraceEngine(graph, rule_registry=registry).trace(
            TraceRequest(a.id, target_id=b.id, max_depth=1)
        )
        self.assertEqual(result.status, "INFERRED")
        self.assertEqual(result.confidence, 0.7)
        self.assertEqual(result.methodology_version, "custom-rule:custom-1")

    def test_boundary_round_trip_preserves_nested_metadata(self):
        graph, a, b, _ = self.graph()
        edge = next(iter(graph.outgoing(a.id)))
        from dataclasses import replace
        graph.evidence["E_BOUNDARY"] = {
            "boundary_type": "reflection",
            "reason": "Target is reached through reflection.",
        }
        graph.edges[edge.id] = replace(edge, evidence_refs=("E_BOUNDARY",))
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=b.id, max_depth=1))
        restored = Trace.from_dict(result.to_dict())
        self.assertEqual(restored.steps[0].boundaries[0].boundary_type, "REFLECTION")
        self.assertEqual(restored.boundaries[0].boundary_type, "REFLECTION")

    def test_ambiguous_trace_preserves_alternatives(self):
        graph, a, _, c = self.graph()
        d = Node.create("File", "REPO", "file:d", analysis_run_id=self.RUN, revision=self.REV)
        graph.add_node(d)
        graph.add_edge(Edge.create(a, "CONTAINS", d, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        graph.add_edge(Edge.create(d, "CONTAINS", c, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=3))
        self.assertEqual(result.status, "AMBIGUOUS")
        self.assertEqual(len(result.alternatives), 2)
        self.assertTrue(all(candidate.steps for candidate in result.alternatives))

    def test_explicit_contradiction_evidence_is_not_confused_with_ambiguity(self):
        graph, a, b, c = self.graph()
        d = Node.create("File", "REPO", "file:d", analysis_run_id=self.RUN, revision=self.REV)
        graph.add_node(d)
        e1 = Edge.create(a, "CONTAINS", b, evidence_refs=("E1",), analysis_run_id=self.RUN, revision=self.REV)
        e2 = Edge.create(a, "CONTAINS", d, evidence_refs=("E1",), analysis_run_id=self.RUN, revision=self.REV)
        graph.add_edge(e1); graph.add_edge(e2)
        graph.evidence["E_CONTRADICTION"] = {"type": "contradiction", "edge_ids": [e1.id, e2.id], "reason": "mutually exclusive mapping"}
        graph.require_valid()
        result = TraceEngine(graph).trace(TraceRequest(a.id, max_depth=1))
        self.assertEqual(result.status, "CONTRADICTED")
        self.assertTrue(result.contradictions)
        self.assertIn("E_CONTRADICTION", result.evidence)

    def test_inferred_trace_preserves_confidence(self):
        graph, a, b, c = self.graph()
        graph.edges.clear()
        graph.evidence["E2"] = {"source": "inference"}
        graph.add_edge(Edge.create(a, "DEPENDS_ON", b, provenance="inferred",
                                    confidence=0.8, evidence_refs=("E2",),
                                    analysis_run_id=self.RUN, revision=self.REV))
        graph.add_edge(Edge.create(b, "DEPENDS_ON", c, provenance="inferred",
                                    confidence=0.6, evidence_refs=("E2",),
                                    analysis_run_id=self.RUN, revision=self.REV))
        graph.require_valid()
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=2))
        self.assertEqual(result.status, "INFERRED")
        self.assertEqual(result.confidence, 0.6)
        self.assertEqual(result.steps[0].confidence, 0.8)

    def test_contradicted_trace_requires_structured_claims_and_resolution(self):
        trace_id = Trace.compute_id(
            repository_id="REPO", revision="REV1", origin="N1", target="N2",
            methodology_version=METHODOLOGY_VERSION, analyzer_version=ANALYZER_VERSION)
        base = Trace(
            trace_id=trace_id, repository_id="REPO", revision="REV1", analysis_run_id="RUN",
            origin="N1", target="N2", status="CONTRADICTED", confidence=None,
            methodology_version=METHODOLOGY_VERSION, analyzer_version=ANALYZER_VERSION,
            contradictions=({"claims": ["N1->N2", "N1->N3"], "evidence_refs": ["E1", "E2"]},),
            evidence=("E1", "E2"),
            boundaries=(TraceBoundary("UNRESOLVED_PATH", 1, "CONTRADICTED",
                                      "Conflicting claims remain.", ("E1", "E2")),),
        )
        codes = {error["code"] for error in base.validate()}
        self.assertIn("INVALID_CONTRADICTION_CLAIM", codes)
        self.assertIn("CONTRADICTION_MISSING_AFFECTED_STEP", codes)
        self.assertIn("CONTRADICTION_MISSING_RESOLUTION", codes)

    def test_evidence_less_edge_cannot_be_confirmed(self):
        graph, a, b, _ = self.graph()
        graph.edges.clear()
        graph.evidence.clear()
        graph.add_edge(Edge.create(
            a, "CONTAINS", b, evidence_refs=(),
            analysis_run_id=self.RUN, revision=self.REV))
        graph.require_valid()
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=b.id, max_depth=1))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.steps[0].status, "UNKNOWN")
        self.assertEqual(result.steps[0].evidence_refs, ())
        self.assertEqual(result.boundaries[0].boundary_type, "MISSING_EVIDENCE")

    def test_invalid_alternative_is_rejected(self):
        trace_id = Trace.compute_id(
            repository_id="REPO", revision="REV1", origin="N1", target="N2",
            methodology_version=METHODOLOGY_VERSION, analyzer_version=ANALYZER_VERSION)
        step = TraceStep(
            step_id="STEP-BAD", sequence=2, source_node="N1", relation="CONTAINS",
            target_node="N2", status="NOT_A_STATUS", provenance="bad",
            confidence=2.0, evidence_refs=("E1",))
        trace = Trace(
            trace_id=trace_id, repository_id="REPO", revision="REV1", analysis_run_id="RUN",
            origin="N1", target="N2", status="AMBIGUOUS", confidence=None,
            methodology_version=METHODOLOGY_VERSION, analyzer_version=ANALYZER_VERSION,
            alternatives=(CandidatePath((step,), "NOT_A_STATUS", 2.0),),
            evidence=("E1",))
        codes = {error["code"] for error in trace.validate()}
        self.assertIn("INVALID_ALTERNATIVE_STATUS", codes)
        self.assertIn("INVALID_STEP_STATUS", codes)
        self.assertIn("INVALID_PROVENANCE", codes)
        self.assertIn("ALTERNATIVE_CONFIDENCE_OUT_OF_RANGE", codes)
        self.assertIn("NON_CONTIGUOUS_SEQUENCE", codes)

    def test_path_truncation_is_exposed(self):
        graph, a, b, c = self.graph()
        d = Node.create("File", "REPO", "file:d", analysis_run_id=self.RUN, revision=self.REV)
        graph.add_node(d)
        graph.evidence["E2"] = {"source": "test"}
        graph.add_edge(Edge.create(a, "CONTAINS", d, evidence_refs=("E2",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        result = TraceEngine(graph).trace(TraceRequest(a.id, max_depth=1, max_paths=1))
        self.assertEqual(result.status, "AMBIGUOUS")
        self.assertTrue(any("max_paths" in b.reason for b in result.boundaries))

    def test_validation_rejects_malformed_steps(self):
        trace_id = Trace.compute_id(
            repository_id="REPO", revision="REV1", origin="N1", target="N2",
            methodology_version=METHODOLOGY_VERSION, analyzer_version=ANALYZER_VERSION)
        step = TraceStep(
            step_id="STEP-1", sequence=2, source_node="N1", relation="CONTAINS",
            target_node="N2", status="CONFIRMED", provenance="deterministic",
            confidence=0.9, evidence_refs=())
        trace = Trace(
            trace_id=trace_id, repository_id="REPO", revision="REV1", analysis_run_id="RUN",
            origin="N1", target="N2", status="CONFIRMED", confidence=None,
            methodology_version=METHODOLOGY_VERSION, analyzer_version=ANALYZER_VERSION,
            steps=(step,))
        codes = {error["code"] for error in trace.validate()}
        self.assertIn("NON_CONTIGUOUS_SEQUENCE", codes)
        self.assertIn("DETERMINISTIC_UNSUPPORTED_CONFIDENCE", codes)

    def test_serialization_round_trip_and_tamper_rejection(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=2))
        restored = Trace.from_dict(json.loads(result.to_json()))
        self.assertEqual(restored.to_json(), result.to_json())
        data = json.loads(result.to_json())
        data["trace_id"] = "TRACE-TAMPERED"
        with self.assertRaises(TraceValidationError):
            Trace.from_dict(data)

    def test_trace_identity_is_independent_of_checkout_path(self):
        first = Trace.compute_id(repository_id="REPO", revision="REV1", origin="N1",
                                 target="N2", methodology_version=METHODOLOGY_VERSION,
                                 analyzer_version=ANALYZER_VERSION)
        second = Trace.compute_id(repository_id="REPO", revision="REV1", origin="N1",
                                  target="N2", methodology_version=METHODOLOGY_VERSION,
                                  analyzer_version=ANALYZER_VERSION)
        self.assertEqual(first, second)

    def test_read_only_behavior(self):
        graph, a, _, c = self.graph()
        before = graph.to_json()
        TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=2))
        self.assertEqual(graph.to_json(), before)


if __name__ == "__main__":
    unittest.main()
