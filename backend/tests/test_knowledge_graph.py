import unittest

from services.knowledge_graph import (
    apply_knowledge_candidates,
    empty_graph,
    upsert_edge,
    upsert_node,
)


class KnowledgeGraphTests(unittest.TestCase):
    def test_node_insertion(self):
        graph = upsert_node(empty_graph(), node_type="project", label="OMEGA-ARC")
        self.assertEqual(len(graph["nodes"]), 1)

    def test_node_deduplication(self):
        graph = upsert_node(empty_graph(), node_type="project", label="OMEGA-ARC")
        graph = upsert_node(graph, node_type="project", label="OMEGA-ARC")
        self.assertEqual(len(graph["nodes"]), 1)

    def test_attribute_updates(self):
        graph = upsert_node(empty_graph(), node_type="system", label="OMEGA-ARC backend", attributes={"port": 8001})
        graph = upsert_node(graph, node_type="system", label="OMEGA-ARC backend", attributes={"port": 8002})
        node = next(node for node in graph["nodes"] if node["id"] == "system:omega-arc-backend")
        self.assertEqual(node["attributes"]["port"], 8002)

    def test_edge_insertion(self):
        graph = upsert_edge(empty_graph(), source="user:bill", relationship="builds", target="project:omega-arc", confidence=1.0, source_type="explicit_user_statement")
        self.assertEqual(len(graph["edges"]), 1)

    def test_edge_deduplication(self):
        graph = upsert_edge(empty_graph(), source="user:bill", relationship="builds", target="project:omega-arc", confidence=1.0, source_type="explicit_user_statement")
        graph = upsert_edge(graph, source="user:bill", relationship="builds", target="project:omega-arc", confidence=0.9, source_type="explicit_user_statement")
        self.assertEqual(len(graph["edges"]), 1)

    def test_higher_confidence_edge_replacement(self):
        graph = upsert_edge(empty_graph(), source="user:bill", relationship="builds", target="project:omega-arc", confidence=0.5, source_type="explicit_user_statement")
        graph = upsert_edge(graph, source="user:bill", relationship="builds", target="project:omega-arc", confidence=0.9, source_type="explicit_user_statement")
        edge = graph["edges"][0]
        self.assertEqual(edge["confidence"], 0.9)

    def test_backend_port_candidate_application(self):
        graph = apply_knowledge_candidates(empty_graph(), [{"key": "backend_port", "value": 8001}])
        self.assertTrue(any(node["type"] == "system" for node in graph["nodes"]))


if __name__ == "__main__":
    unittest.main()
