import unittest

from src.aca_graph.model import Graph, Node, Edge
from src.aca_reconciliation import ReconciliationRequest, RepositoryContext
from src.aca_reconciliation.structural import StructuralReconciler


class StructuralReconciliationTests(unittest.TestCase):
    def context(self, repo, revision, run):
        return RepositoryContext("p", repo, revision, run, "aca-graph-0.2")

    def graph(self, repo, revision, run, nodes):
        g = Graph({"id": repo, "project_id": "p"}, revision, run)
        for node in nodes:
            g.add_node(node)
        return g

    def request(self):
        return ReconciliationRequest(
            "recon-structural",
            self.context("source", "r1", "run-s"),
            self.context("target", "r2", "run-t"),
        )

    def test_exact_match_and_source_removal_and_target_addition(self):
        s = Node.create("Class", "source", "Customer", analysis_run_id="run-s", revision="r1")
        s_only = Node.create("Class", "source", "Legacy", analysis_run_id="run-s", revision="r1")
        t = Node.create("Class", "target", "Customer", analysis_run_id="run-t", revision="r2")
        t_only = Node.create("Class", "target", "New", analysis_run_id="run-t", revision="r2")
        mappings, findings = StructuralReconciler().reconcile(
            self.graph("source", "r1", "run-s", [s, s_only]),
            self.graph("target", "r2", "run-t", [t, t_only]),
            self.request(),
        )
        self.assertEqual(len(mappings), 1)
        categories = {f.category for f in findings}
        self.assertEqual(categories, {"MATCH", "REMOVAL", "ADDITION"})

    def test_relationship_removal_is_reported(self):
        sa = Node.create("Class", "source", "A", analysis_run_id="run-s", revision="r1")
        sb = Node.create("Class", "source", "B", analysis_run_id="run-s", revision="r1")
        ta = Node.create("Class", "target", "A", analysis_run_id="run-t", revision="r2")
        tb = Node.create("Class", "target", "B", analysis_run_id="run-t", revision="r2")
        sg = self.graph("source", "r1", "run-s", [sa, sb])
        sg.add_edge(Edge.create(sa, "DEPENDS_ON", sb, analysis_run_id="run-s", revision="r1"))
        tg = self.graph("target", "r2", "run-t", [ta, tb])
        _, findings = StructuralReconciler().reconcile(sg, tg, self.request())
        self.assertTrue(any(f.category == "RELATIONSHIP_CHANGE" for f in findings))


if __name__ == "__main__":
    unittest.main()
