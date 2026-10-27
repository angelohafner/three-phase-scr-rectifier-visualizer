#!/usr/bin/env python3
"""Electrical graph model of rectifier and inverter six-pulse SCR commutation.

The graph contains actual conductive elements. A highlighted segment is the
union of complete directed conduction loops, never a hand-coded list of reds.
This is a topological representation, not a dynamic current-sharing solver.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable

PHASES = ('a', 'b', 'c')
UPPER = {'a': 'T1', 'b': 'T3', 'c': 'T5'}
LOWER = {'a': 'T2', 'b': 'T4', 'c': 'T6'}
PAIRS = (('a', 'c'), ('b', 'c'), ('b', 'a'), ('c', 'a'), ('c', 'b'), ('a', 'b'))
WIRE_IDS = frozenset(
    [f'FASE_{p.upper()}' for p in PHASES] +
    ['NEUTRO_AB', 'NEUTRO_BC'] +
    [f'{s}_FASE' for s in (*UPPER.values(), *LOWER.values())] +
    [f'{s}_POS' for s in UPPER.values()] +
    [f'{s}_NEG' for s in LOWER.values()] +
    ['POS_T1_T3', 'POS_T3_T5', 'POS_T5_CARGA',
     'NEG_T2_T4', 'NEG_T4_T6', 'NEG_T6_CARGA',
     'CARGA_POS_L', 'CARGA_L_R', 'CARGA_R_NEG']
)


@dataclass(frozen=True)
class Edge:
    """A directed or bidirectional physical component or wire section."""
    name: str
    u: str
    v: str
    group: str                   # AC, DC, LOAD
    kind: str                    # wire, scr, inductor, source, resistor
    forward_only: bool = False


@dataclass(frozen=True)
class Walk:
    """Traversal of an edge with explicit conventional-current direction."""
    edge: Edge
    start: str
    end: str
    direction: int              # +1 along u->v; -1 against it


@dataclass(frozen=True)
class ConductionState:
    """One normal pair or one three-SCR commutation-overlap state."""
    number: int
    kind: str
    pairs: tuple[tuple[str, str], ...]
    scrs: frozenset[str]
    theta_start: float
    theta_end: float
    mu: float
    outgoing: str | None = None
    incoming: str | None = None

    @property
    def is_overlap(self) -> bool:
        return self.kind == 'overlap'

    @property
    def label(self) -> str:
        return 'Commutation Overlap' if self.is_overlap else 'Normal Conduction'

    @property
    def scr_description(self) -> str:
        return ' + '.join(s for s in ('T1', 'T2', 'T3', 'T4', 'T5', 'T6')
                          if s in self.scrs)

    @property
    def phase_description(self) -> str:
        return '  |  '.join(f'{p.upper()}+ → {n.upper()}−' for p, n in self.pairs)


@dataclass(frozen=True)
class Highlight:
    """A graphical selection derived from graph traversals or manual inputs."""
    thyristors: frozenset[str]
    inductors: frozenset[str]
    sources: frozenset[str]
    paths: frozenset[str]
    resistor: bool = False
    arrows: bool = True
    title: str = 'THREE-PHASE SCR RECTIFIER'
    dc_source: bool = False
    step: int | None = None
    directions: tuple[tuple[str, int], ...] = ()

    def signed_edges(self) -> dict[str, int]:
        return dict(self.directions)


class CircuitTopology:
    """Connectivity and shortest paths through the actual circuit elements."""
    def __init__(self, operation: str = 'rectifier') -> None:
        if operation not in ('rectifier', 'inverter'):
            raise ValueError('operation must be rectifier or inverter')
        self.operation = operation
        self.edges: dict[str, Edge] = {}
        self.neighbors: dict[str, list[Walk]] = defaultdict(list)
        self._build()
        self._validate_topology()

    def add(self, name: str, u: str, v: str, group: str,
            kind: str = 'wire', forward_only: bool = False) -> None:
        if name in self.edges:
            raise ValueError(f'Duplicate edge: {name}')
        edge = Edge(name, u, v, group, kind, forward_only)
        self.edges[name] = edge
        self.neighbors[u].append(Walk(edge, u, v, 1))
        if not forward_only:
            self.neighbors[v].append(Walk(edge, v, u, -1))

    def _build(self) -> None:
        self.add('NEUTRO_AB', 'STAR_A', 'STAR_B', 'AC')
        self.add('NEUTRO_BC', 'STAR_B', 'STAR_C', 'AC')
        for ph in PHASES:
            p = ph.upper()
            self.add('V'+p, 'STAR_'+p, 'SRC_'+p, 'AC', 'source')
            self.add('L'+p, 'SRC_'+p, 'FEED_'+p, 'AC', 'inductor')
            self.add('FASE_'+p, 'FEED_'+p, 'PHASE_'+p, 'AC')
            top, bot = UPPER[ph], LOWER[ph]
            if self.operation == 'rectifier':
                self.add(top+'_FASE', 'PHASE_'+p, 'ANODE_'+top, 'DC')
                self.add(top+'_POS', 'CATHODE_'+top, 'POS_'+p, 'DC')
                self.add(bot+'_NEG', 'NEG_'+p, 'ANODE_'+bot, 'DC')
                self.add(bot+'_FASE', 'CATHODE_'+bot, 'PHASE_'+p, 'DC')
            else:
                # Inverter valves have anodes toward DC+ in the upper group
                # and toward the AC phase in the lower group.
                self.add(top+'_FASE', 'PHASE_'+p, 'CATHODE_'+top, 'DC')
                self.add(top+'_POS', 'ANODE_'+top, 'POS_'+p, 'DC')
                self.add(bot+'_NEG', 'NEG_'+p, 'CATHODE_'+bot, 'DC')
                self.add(bot+'_FASE', 'ANODE_'+bot, 'PHASE_'+p, 'DC')
            self.add(top, 'ANODE_'+top, 'CATHODE_'+top,
                     'DC', 'scr', forward_only=True)
            self.add(bot, 'ANODE_'+bot, 'CATHODE_'+bot,
                     'DC', 'scr', forward_only=True)
        self.add('POS_T1_T3', 'POS_A', 'POS_B', 'DC')
        self.add('POS_T3_T5', 'POS_B', 'POS_C', 'DC')
        self.add('POS_T5_CARGA', 'POS_C', 'POS_LOAD', 'DC')
        self.add('NEG_T2_T4', 'NEG_A', 'NEG_B', 'DC')
        self.add('NEG_T4_T6', 'NEG_B', 'NEG_C', 'DC')
        self.add('NEG_T6_CARGA', 'NEG_C', 'NEG_LOAD', 'DC')
        self.add('CARGA_POS_L', 'POS_LOAD', 'LDC_IN', 'LOAD')
        self.add('LDC', 'LDC_IN', 'LDC_OUT', 'LOAD', 'inductor')
        self.add('CARGA_L_R', 'LDC_OUT', 'R_IN', 'LOAD')
        self.add('R' if self.operation == 'rectifier' else 'EDC',
                 'R_IN', 'R_OUT', 'LOAD',
                 'resistor' if self.operation == 'rectifier' else 'dc_supply')
        self.add('CARGA_R_NEG', 'R_OUT', 'NEG_LOAD', 'LOAD')

    def _validate_topology(self) -> None:
        all_scrs = frozenset((*UPPER.values(), *LOWER.values()))
        actual_wires = {e.name for e in self.edges.values() if e.kind == 'wire'}
        if actual_wires != WIRE_IDS:
            raise ValueError(f'Wire registration mismatch: {actual_wires ^ WIRE_IDS}')
        if {e.name for e in self.edges.values() if e.kind == 'scr'} != all_scrs:
            raise ValueError('SCR mismatch in topological graph')

    def shortest_path(self, start: str, end: str,
                      groups: Iterable[str], allowed_scrs: Iterable[str]) -> tuple[Walk, ...]:
        """Find a directed electrical path, without reverse flow through SCRs."""
        allowed_groups = frozenset(groups)
        fired_scrs = frozenset(allowed_scrs)
        queue = deque([start])
        previous: dict[str, Walk | None] = {start: None}
        while queue:
            node = queue.popleft()
            if node == end:
                break
            for walk in self.neighbors[node]:
                edge = walk.edge
                if edge.group not in allowed_groups:
                    continue
                if edge.kind == 'scr' and edge.name not in fired_scrs:
                    continue
                if walk.end not in previous:
                    previous[walk.end] = walk
                    queue.append(walk.end)
        if end not in previous:
            raise ValueError(f'No conductive path from {start} to {end} ({allowed_groups})')
        result = []
        node = end
        while node != start:
            walk = previous[node]
            assert walk is not None
            result.append(walk)
            node = walk.start
        return tuple(reversed(result))

    def current_loop(self, high: str, low: str) -> tuple[Walk, ...]:
        """Return a closed forward-only SCR path in either energy-flow direction."""
        if high not in PHASES or low not in PHASES or high == low:
            raise ValueError('Conduction requires distinct AC phases')
        selected = {UPPER[high], LOWER[low]}
        if self.operation == 'rectifier':
            routes = (
                self.shortest_path('PHASE_'+high.upper(), 'POS_LOAD', ('DC',), selected),
                self.shortest_path('POS_LOAD', 'NEG_LOAD', ('LOAD',), selected),
                self.shortest_path('NEG_LOAD', 'PHASE_'+low.upper(), ('DC',), selected),
                self.shortest_path('PHASE_'+low.upper(), 'PHASE_'+high.upper(), ('AC',), selected),
            )
        else:
            routes = (
                self.shortest_path('POS_LOAD', 'PHASE_'+high.upper(), ('DC',), selected),
                self.shortest_path('PHASE_'+high.upper(), 'PHASE_'+low.upper(), ('AC',), selected),
                self.shortest_path('PHASE_'+low.upper(), 'NEG_LOAD', ('DC',), selected),
                self.shortest_path('NEG_LOAD', 'POS_LOAD', ('LOAD',), selected),
            )
        loop = tuple(w for route in routes for w in route)
        assert loop[0].start == loop[-1].end
        for left, right in zip(loop, loop[1:]):
            if left.end != right.start:
                raise AssertionError(f'Broken route between {left.edge.name} and {right.edge.name}')
        actual_scrs = {w.edge.name for w in loop if w.edge.kind == 'scr'}
        assert actual_scrs == selected, (actual_scrs, selected)
        assert {'LDC', 'R' if self.operation == 'rectifier' else 'EDC'} <= {w.edge.name for w in loop}
        return loop

    def highlight(self, state: ConductionState) -> Highlight:
        """Union of individually valid current loops; sums signed traversals."""
        counts: dict[str, int] = defaultdict(int)
        used = set()
        for high, low in state.pairs:
            for walk in self.current_loop(high, low):
                used.add(walk.edge.name)
                counts[walk.edge.name] += walk.direction
        scrs = {name for name in used if self.edges[name].kind == 'scr'}
        inductors = {name for name in used if self.edges[name].kind == 'inductor'}
        sources = {name for name in used if self.edges[name].kind == 'source'}
        wires = {name for name in used if self.edges[name].kind == 'wire'}
        if scrs != state.scrs:
            raise AssertionError(f'Invalid SCR set in state {state.number}: {scrs}')
        if len(scrs) != (3 if state.is_overlap else 2):
            raise AssertionError('Unexpected active SCR count')
        return Highlight(
            thyristors=frozenset(scrs), inductors=frozenset(inductors),
            sources=frozenset(sources), paths=frozenset(wires),
            resistor='R' in used, dc_source='EDC' in used, arrows=True,
            step=state.number,
            directions=tuple(sorted((k, v) for k, v in counts.items() if v)),
        )


class CommutationSequence:
    """Construct six normal states and six three-SCR overlaps in cycle order.

    The angle origin is the start of the previous overlap. Normal interval 1
    is [mu,60]; overlap interval 2 is [60,60+mu]; final overlap wraps at 360.
    No instantaneous current or commutation reactance is inferred from mu.
    """
    def __init__(self, mu: float = 15.0) -> None:
        if not 0 < mu < 60:
            raise ValueError('Overlap mu must satisfy 0 < mu < 60 degrees for 12 states')
        self.mu = float(mu)
        self.states = self._create()

    def _create(self) -> tuple[ConductionState, ...]:
        result = []
        for i, (high, low) in enumerate(PAIRS):
            next_high, next_low = PAIRS[(i + 1) % len(PAIRS)]
            current_set = frozenset((UPPER[high], LOWER[low]))
            next_set = frozenset((UPPER[next_high], LOWER[next_low]))
            diff_out = current_set - next_set
            diff_in = next_set - current_set
            if len(diff_out) != 1 or len(diff_in) != 1:
                raise AssertionError('Consecutive states must swap one SCR')
            outgoing = next(iter(diff_out))
            incoming = next(iter(diff_in))
            state_normal = ConductionState(
                number=2*i+1, kind='normal', pairs=((high, low),),
                scrs=current_set, theta_start=i*60+self.mu,
                theta_end=(i+1)*60, mu=self.mu,
            )
            state_overlap = ConductionState(
                number=2*i+2, kind='overlap',
                pairs=((high, low), (next_high, next_low)),
                scrs=frozenset(current_set | next_set),
                theta_start=(i+1)*60,
                theta_end=(i+1)*60+self.mu, mu=self.mu,
                outgoing=outgoing, incoming=incoming,
            )
            result.extend((state_normal, state_overlap))
        return tuple(result)

    def state(self, n: int) -> ConductionState:
        if not 1 <= n <= 12:
            raise ValueError('State number must be from 1 to 12')
        return self.states[n - 1]

    def ideal_pair(self, n: int) -> tuple[str, str]:
        if not 1 <= n <= 6:
            raise ValueError('Ideal pair step must be from 1 to 6')
        return PAIRS[n - 1]
