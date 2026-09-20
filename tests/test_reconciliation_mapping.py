import unittest

from src.aca_reconciliation import ReconciliationRequest, RepositoryContext
from src.aca_reconciliation.mapping import MappingRuleRegistry


class MappingRuleTests(unittest.TestCase):
    def request(self):
        context = RepositoryContext("p", "source", "r1", "run1", "aca-graph-0.2")
        target = RepositoryContext("p", "target", "r2", "run2", "aca-graph-0.2")
        return ReconciliationRequest("recon-1", context, target)

    def test_exact_canonical_identity_confirms_mapping(self):
        result = MappingRuleRegistry().map_nodes(
            {"id": "S1", "type": "Class", "canonical_key": "org.example.Customer"},
            [
                {"id": "T1", "type": "Class", "canonical_key": "org.example.Customer"},
                {"id": "T2", "type": "Class", "canonical_key": "org.example.Order"},
            ],
            self.request(),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].target_node, "T1")
        self.assertEqual(result[0].state, "CONFIRMED")

    def test_type_difference_does_not_match(self):
        result = MappingRuleRegistry().map_nodes(
            {"id": "S1", "type": "Class", "canonical_key": "Customer"},
            [{"id": "T1", "type": "Interface", "canonical_key": "Customer"}],
            self.request(),
        )
        self.assertEqual(result, ())

    def test_mapping_is_deterministically_ordered(self):
        nodes = [
            {"id": "T2", "type": "Class", "canonical_key": "Customer"},
            {"id": "T1", "type": "Class", "canonical_key": "Customer"},
        ]
        result1 = MappingRuleRegistry().map_nodes(
            {"id": "S1", "type": "Class", "canonical_key": "Customer"}, nodes, self.request())
        result2 = MappingRuleRegistry().map_nodes(
            {"id": "S1", "type": "Class", "canonical_key": "Customer"}, reversed(nodes), self.request())
        self.assertEqual([x.mapping_id for x in result1], [x.mapping_id for x in result2])
        self.assertEqual(len(result1), 2)
