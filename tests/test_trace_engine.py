import json
import unittest

from src.aca_graph import Edge, Graph, Node, TraceEngine, TraceRequest, TraceValidationError


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

    def test_direct_and_multihop_trace(self):
        graph, a, b, c = self.graph()
        result = TraceEngine(graph).trace(
            TraceRequest(a.id, target_id=c.id, direction="OUTGOING", max_depth=2)
        )
        self.assertEqual(result.state, "CONFIRMED")
        self.assertEqual(len(result.paths), 1)
        self.assertEqual(result.paths[0].node_ids, (a.id, b.id, c.id))
        self.assertEqual(result.evidence_refs, ("E1",))

    def test_depth_limit_returns_unknown(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(
            TraceRequest(a.id, target_id=c.id, max_depth=1)
        )
        self.assertEqual(result.state, "UNKNOWN")
        self.assertEqual(result.reason, "NO_PATH")

    def test_relationship_filter(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(
            TraceRequest(a.id, target_id=c.id, excluded_relations=("CONTAINS",), max_depth=2)
        )
        self.assertEqual(result.state, "UNKNOWN")
        self.assertEqual(result.reason, "NO_PATH")

    def test_incoming_trace(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(
            TraceRequest(c.id, target_id=a.id, direction="INCOMING", max_depth=2)
        )
        self.assertEqual(result.state, "CONFIRMED")

    def test_ambiguous_trace_is_deterministic(self):
        graph, a, _, c = self.graph()
        d = Node.create("File", "REPO", "file:d", analysis_run_id=self.RUN, revision=self.REV)
        graph.add_node(d)
        graph.add_edge(Edge.create(a, "CONTAINS", d, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        graph.add_edge(Edge.create(d, "CONTAINS", c, evidence_refs=("E1",),
                                   analysis_run_id=self.RUN, revision=self.REV))
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=3))
        self.assertEqual(result.state, "AMBIGUOUS")
        self.assertEqual(len(result.paths), 2)
        self.assertEqual(result.to_json(), TraceEngine(graph).trace(
            TraceRequest(a.id, target_id=c.id, max_depth=3)
        ).to_json())

    def test_inferred_path_preserves_confidence(self):
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
        self.assertEqual(result.state, "INFERRED")
        self.assertEqual(result.confidence, 0.6)

    def test_serialization_round_trip_and_tamper_rejection(self):
        graph, a, _, c = self.graph()
        result = TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=2))
        restored = TraceEngine.from_json(result.to_json())
        self.assertEqual(restored.to_json(), result.to_json())
        data = json.loads(result.to_json())
        data["trace_id"] = "TRACE-TAMPERED"
        with self.assertRaises(TraceValidationError):
            TraceEngine.from_json(json.dumps(data))

    def test_missing_source_is_rejected(self):
        graph, _, _, _ = self.graph()
        with self.assertRaises(TraceValidationError):
            TraceEngine(graph).trace(TraceRequest("NODE-MISSING"))

    def test_trace_does_not_mutate_graph(self):
        graph, a, _, c = self.graph()
        before = graph.to_json()
        TraceEngine(graph).trace(TraceRequest(a.id, target_id=c.id, max_depth=2))
        self.assertEqual(graph.to_json(), before)


if __name__ == "__main__":
    unittest.main()
