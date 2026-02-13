from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class Edge:
    to: int
    cap: int
    flow: int = 0
    rev: Edge = None  # type: ignore[assignment]  # always set by Dinic.add_edge


class Dinic:
    """Dinic's max-flow algorithm. O(V^2 * E) in general."""

    def __init__(self, n: int) -> None:
        self.n = n
        self.graph: list[list[Edge]] = [[] for _ in range(n)]

    # ---- graph construction ------------------------------------------------

    def add_edge(self, u: int, v: int, cap: int) -> Edge:
        """Add a directed edge u->v with given capacity. Returns the forward edge."""
        fwd = Edge(to=v, cap=cap)
        rev = Edge(to=u, cap=0)
        fwd.rev = rev
        rev.rev = fwd
        self.graph[u].append(fwd)
        self.graph[v].append(rev)
        return fwd

    # ---- BFS (build level graph) -------------------------------------------

    def _bfs(self, s: int, t: int) -> bool:
        self._level = [-1] * self.n
        self._level[s] = 0
        q: deque[int] = deque([s])
        while q:
            u = q.popleft()
            for e in self.graph[u]:
                if self._level[e.to] == -1 and e.cap - e.flow > 0:
                    self._level[e.to] = self._level[u] + 1
                    q.append(e.to)
        return self._level[t] != -1

    # ---- DFS (find blocking flow) ------------------------------------------

    def _dfs(self, u: int, t: int, pushed: int) -> int:
        if u == t:
            return pushed
        while self._iter[u] < len(self.graph[u]):
            e = self.graph[u][self._iter[u]]
            if self._level[e.to] == self._level[u] + 1 and e.cap - e.flow > 0:
                d = self._dfs(e.to, t, min(pushed, e.cap - e.flow))
                if d > 0:
                    e.flow += d
                    e.rev.flow -= d
                    return d
            self._iter[u] += 1
        return 0

    # ---- main entry --------------------------------------------------------

    def max_flow(self, s: int, t: int) -> int:
        """Compute and return the maximum flow from *s* to *t*."""
        total = 0
        while self._bfs(s, t):
            self._iter = [0] * self.n   # each index is the no.of edges at each node
            while True:
                f = self._dfs(s, t, float("inf"))  # type: ignore[arg-type]
                if f == 0:
                    break
                total += f
        return total
