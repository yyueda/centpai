import pytest
from unittest.mock import MagicMock
from app.features.expenses.algorithms.dinic import Dinic, Edge


class TestEdge:
    def test_edge_default_flow(self):
        e = Edge(to=1, cap=10)
        assert e.flow == 0

    def test_edge_fields(self):
        e = Edge(to=3, cap=5, flow=2)
        assert e.to == 3
        assert e.cap == 5
        assert e.flow == 2


class TestDinic:
    def test_init(self):
        d = Dinic(5)
        assert d.n == 5
        assert len(d.graph) == 5
        assert all(len(adj) == 0 for adj in d.graph)

    def test_add_edge_creates_forward_and_reverse(self):
        d = Dinic(2)
        fwd = d.add_edge(0, 1, 10)
        assert fwd.to == 1
        assert fwd.cap == 10
        assert fwd.flow == 0
        rev = fwd.rev
        assert rev.to == 0
        assert rev.cap == 0
        assert rev.rev is fwd

    def test_add_edge_appended_to_graph(self):
        d = Dinic(3)
        d.add_edge(0, 1, 5)
        assert len(d.graph[0]) == 1
        assert len(d.graph[1]) == 1  # reverse edge

    def test_max_flow_no_path(self):
        d = Dinic(2)
        # No edges added
        assert d.max_flow(0, 1) == 0

    def test_max_flow_single_edge(self):
        d = Dinic(2)
        d.add_edge(0, 1, 7)
        assert d.max_flow(0, 1) == 7

    def test_max_flow_two_parallel_edges(self):
        d = Dinic(2)
        d.add_edge(0, 1, 3)
        d.add_edge(0, 1, 4)
        assert d.max_flow(0, 1) == 7

    def test_max_flow_serial_edges_bottleneck(self):
        # 0 ->10-> 1 ->5-> 2
        d = Dinic(3)
        d.add_edge(0, 1, 10)
        d.add_edge(1, 2, 5)
        assert d.max_flow(0, 2) == 5

    def test_max_flow_diamond(self):
        # Classic diamond: source=0, sink=3
        # 0->1 cap 10, 0->2 cap 10, 1->3 cap 10, 2->3 cap 10
        d = Dinic(4)
        d.add_edge(0, 1, 10)
        d.add_edge(0, 2, 10)
        d.add_edge(1, 3, 10)
        d.add_edge(2, 3, 10)
        assert d.max_flow(0, 3) == 20

    def test_max_flow_respects_capacity(self):
        d = Dinic(2)
        d.add_edge(0, 1, 3)
        flow = d.max_flow(0, 1)
        assert flow <= 3

    def test_max_flow_complex_graph(self):
        # source=0, sink=5
        d = Dinic(6)
        d.add_edge(0, 1, 10)
        d.add_edge(0, 2, 10)
        d.add_edge(1, 3, 4)
        d.add_edge(1, 4, 8)
        d.add_edge(2, 4, 9)
        d.add_edge(3, 5, 10)
        d.add_edge(4, 5, 10)
        assert d.max_flow(0, 5) == 14

    def test_flow_conservation_after_max_flow(self):
        d = Dinic(3)
        d.add_edge(0, 1, 5)
        d.add_edge(1, 2, 3)
        d.max_flow(0, 2)
        # forward edge flow should not exceed capacity
        for adj in d.graph:
            for e in adj:
                assert e.flow <= e.cap
