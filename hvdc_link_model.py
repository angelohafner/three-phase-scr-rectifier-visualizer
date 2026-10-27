#!/usr/bin/env python3
"""Graph-validated, two-terminal six-pulse LCC HVDC learning model.

This model intentionally uses *one* Graetz bridge at each converter station.
The positive conductor and metallic return form a closed, directed DC loop.
Transformer primaries are electrically isolated from the valve-side secondaries.

Highlighted paths are unions of topologically valid routes, not EMT solutions.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import product
from math import isfinite
from typing import Iterable

from rectifier_model import CommutationSequence, ConductionState, LOWER, UPPER


@dataclass(frozen=True)
class LinkEdge:
    """A physical oriented edge; bidirectional edges allow reverse traversal."""
    id: str
    src: str
    dst: str
    group: str
    kind: str
    forward_only: bool = False


@dataclass(frozen=True)
class Passage:
    """A directed traversal in a complete two-station closed loop."""
    edge: LinkEdge
    start: str
    end: str
    orientation: int


@dataclass(frozen=True)
class LinkSettings:
    """Synchronized schematic timing and commutation-angle assumptions."""
    alpha_rectifier: float = 15.0
    alpha_inverter: float = 145.0
    mu_rectifier: float = 12.0
    mu_inverter: float = 15.0
    gamma_min: float = 10.0
    ac_phase_offset: float = 30.0

    def __post_init__(self) -> None:
        fields = (
            self.alpha_rectifier, self.alpha_inverter,
            self.mu_rectifier, self.mu_inverter,
            self.gamma_min, self.ac_phase_offset,
        )
        if not all(isfinite(x) for x in fields):
            raise ValueError('All angles must be finite numbers')
        if not 0 <= self.alpha_rectifier < 90:
            raise ValueError('Rectifier delay alpha_rectifier must satisfy 0 <= alpha < 90 degrees')
        if not 90 < self.alpha_inverter < 180:
            raise ValueError('Inverter delay alpha_inverter must satisfy 90 < alpha < 180 degrees')
        if not 0 < self.mu_rectifier < 60 or not 0 < self.mu_inverter < 60:
            raise ValueError('Overlap angles must satisfy 0 < mu < 60 degrees')
        if not 0 < self.gamma_min < 60:
            raise ValueError('gamma_min must satisfy 0 < gamma_min < 60 degrees')
        if not 0 <= self.ac_phase_offset < 360:
            raise ValueError('ac_phase_offset must satisfy 0 <= phase_offset < 360 degrees')
        if self.gamma < self.gamma_min:
            raise ValueError(
                f'Inverter extinction angle gamma={self.gamma:g} degrees '
                f'is below the allowed minimum {self.gamma_min:g} degrees'
            )

    @property
    def gamma(self) -> float:
        """Idealized six-pulse extinction angle in the stated angle convention."""
        return 180 - self.alpha_inverter - self.mu_inverter


@dataclass(frozen=True)
class CombinedState:
    """One interval of simultaneous, phase-offset rectifier/inverter states."""
    number: int
    theta_start: float
    theta_end: float
    rectifier: ConductionState
    inverter: ConductionState

    @property
    def theta_mid(self) -> float:
        return (self.theta_start + self.theta_end) / 2

    @property
    def rectifier_overlap(self) -> bool:
        return self.rectifier.is_overlap

    @property
    def inverter_overlap(self) -> bool:
        return self.inverter.is_overlap

    @property
    def name(self) -> str:
        if self.rectifier_overlap and self.inverter_overlap:
            return 'Simultaneous station commutations'
        if self.rectifier_overlap:
            return 'Rectifier commutation overlap'
        if self.inverter_overlap:
            return 'Inverter commutation overlap'
        return 'Normal conduction at both stations'


class CombinedSchedule:
    """Partition a global 360-degree timeline at *all* commutation boundaries.

    The station commutation offset is independent of firing delay angles.
    It is an illustrative relative shift between valve-sequence timelines,
    not a physical AC-grid phase angle, PLL reference, or solved quantity.
    The historic JSON/CLI key ``ac_phase_offset`` is retained for compatibility.
    """

    def __init__(self, settings: LinkSettings) -> None:
        self.settings = settings
        self.r_sequence = CommutationSequence(settings.mu_rectifier)
        self.i_sequence = CommutationSequence(settings.mu_inverter)
        self.intervals = self._create()

    @staticmethod
    def state_at(theta: float, seq: CommutationSequence, offset: float) -> ConductionState:
        """Map a global angle to the exact local six-pulse pair/overlap state."""
        rel = (theta - offset) % 360
        sector = int(rel // 60)
        fraction = rel - 60 * sector
        if fraction < seq.mu - 1e-9:
            return seq.state(12 if sector == 0 else 2 * sector)
        return seq.state(2 * sector + 1)

    def at(self, theta: float) -> CombinedState:
        """Sample the actual joint station states at any global angle."""
        theta = theta % 360
        for state in self.intervals:
            if state.theta_start <= theta < state.theta_end:
                return state
        raise AssertionError(f'No timeline interval at {theta}')

    def _create(self) -> tuple[CombinedState, ...]:
        s = self.settings
        boundaries = [0.0, 360.0]
        for offset, mu in ((0.0, s.mu_rectifier), (s.ac_phase_offset, s.mu_inverter)):
            for sector in range(6):
                start = (offset + sector * 60) % 360
                end = (start + mu) % 360
                boundaries.extend((start, end))
        positions = sorted({round(x, 9) for x in boundaries})
        intervals = []
        for i, (lo, hi) in enumerate(zip(positions, positions[1:]), start=1):
            mid = (lo + hi) / 2
            intervals.append(CombinedState(
                number=i,
                theta_start=lo,
                theta_end=hi,
                rectifier=self.state_at(mid, self.r_sequence, 0),
                inverter=self.state_at(mid, self.i_sequence, s.ac_phase_offset),
            ))
        if not intervals or intervals[0].theta_start != 0 or intervals[-1].theta_end != 360:
            raise AssertionError('Timeline must cover one complete electrical cycle')
        for left, right in zip(intervals, intervals[1:]):
            if abs(left.theta_end - right.theta_start) > 1e-8:
                raise AssertionError('A temporal gap was found in the schedule')
            if (left.rectifier.number, left.inverter.number) == (
                right.rectifier.number, right.inverter.number
            ):
                raise AssertionError('Redundant interval without a state transition')
        return tuple(intervals)


class HVDCLinkTopology:
    """Two converter bridges plus complete forward-only metal-return DC loop.

    For clarity the second inverter bridge uses the opposite vertical SCR
    orientation to the first rectifier bridge. This keeps I_dc positive on
    the upper pole left-to-right, then right-to-left in the metallic return.
    """

    def __init__(self) -> None:
        self.edges: dict[str, LinkEdge] = {}
        self.adjacency: dict[str, list[Passage]] = defaultdict(list)
        self._build()

    def add(self, edge_id: str, src: str, dst: str, group: str,
            kind: str, forward_only: bool = False) -> None:
        if edge_id in self.edges:
            raise ValueError(f'Duplicate HVDC element {edge_id}')
        edge = LinkEdge(edge_id, src, dst, group, kind, forward_only)
        self.edges[edge_id] = edge
        self.adjacency[src].append(Passage(edge, src, dst, 1))
        if not forward_only:
            self.adjacency[dst].append(Passage(edge, dst, src, -1))

    def _build(self) -> None:
        for side in ('R', 'I'):
            for phase in 'abc':
                p = phase.upper()
                self.add(f'{side}_TR_{p}', f'{side}_O', f'{side}_X_{p}',
                         f'AC_{side}', 'transformer_secondary')
                self.add(f'{side}_LC_{p}', f'{side}_X_{p}', f'{side}_{p}',
                         f'AC_{side}', 'commutation_inductor')
                top, low = UPPER[phase], LOWER[phase]
                if side == 'R':
                    self.add(f'R_{top}', f'R_{p}', 'R_DC_POS', 'R_UPPER', 'scr', True)
                    self.add(f'R_{low}', 'R_DC_NEG', f'R_{p}', 'R_LOWER', 'scr', True)
                else:
                    self.add(f'I_{top}', 'I_DC_POS', f'I_{p}', 'I_UPPER', 'scr', True)
                    self.add(f'I_{low}', f'I_{p}', 'I_DC_NEG', 'I_LOWER', 'scr', True)
        self.add('L_DR', 'R_DC_POS', 'DC_LR', 'LINE', 'smoothing_reactor', True)
        self.add('R_LINE', 'DC_LR', 'DC_R', 'LINE', 'line_resistor', True)
        self.add('L_DI', 'DC_R', 'I_DC_POS', 'LINE', 'smoothing_reactor', True)
        self.add('METALLIC_RETURN', 'I_DC_NEG', 'R_DC_NEG', 'RETURN', 'metallic_return', True)

        scr_names = {k for k, e in self.edges.items() if e.kind == 'scr'}
        assert len(scr_names) == 12

    def route(self, start: str, end: str, *, groups: Iterable[str],
              active_scrs: frozenset[str]) -> tuple[Passage, ...]:
        allowed = frozenset(groups)
        queue = deque([start])
        parents: dict[str, Passage | None] = {start: None}
        while queue:
            u = queue.popleft()
            if u == end:
                break
            for walk in self.adjacency[u]:
                e = walk.edge
                if e.group not in allowed or (e.kind == 'scr' and e.id not in active_scrs):
                    continue
                if walk.end not in parents:
                    queue.append(walk.end)
                    parents[walk.end] = walk
        if end not in parents:
            raise ValueError(f'No continuous path from {start} to {end}')
        result = []
        vertex = end
        while vertex != start:
            walk = parents[vertex]
            assert walk is not None
            result.append(walk)
            vertex = walk.start
        return tuple(reversed(result))

    def conduction_loop(self, rectifier_pair: tuple[str, str],
                        inverter_pair: tuple[str, str]) -> tuple[Passage, ...]:
        """Four SCRs, two AC secondary paths and one closed metallic DC circuit."""
        rh, rl = (k.upper() for k in rectifier_pair)
        ih, il = (k.upper() for k in inverter_pair)
        if rh == rl or ih == il:
            raise ValueError('Each bridge must select two distinct phases')
        selected = frozenset((f'R_{UPPER[rh.lower()]}', f'R_{LOWER[rl.lower()]}',
                              f'I_{UPPER[ih.lower()]}', f'I_{LOWER[il.lower()]}'))
        spans = (
            self.route(f'R_{rh}', f'I_{ih}', groups=('R_UPPER', 'LINE', 'I_UPPER'),
                       active_scrs=selected),
            self.route(f'I_{ih}', f'I_{il}', groups=('AC_I',), active_scrs=selected),
            self.route(f'I_{il}', f'R_{rl}', groups=('I_LOWER', 'RETURN', 'R_LOWER'),
                       active_scrs=selected),
            self.route(f'R_{rl}', f'R_{rh}', groups=('AC_R',), active_scrs=selected),
        )
        loop = tuple(w for span in spans for w in span)
        assert loop[0].start == loop[-1].end
        if any(a.end != b.start for a, b in zip(loop, loop[1:])):
            raise AssertionError('Broken DC/AC conduction path')
        if {w.edge.id for w in loop if w.edge.kind == 'scr'} != selected:
            raise AssertionError('Incorrect conducting SCR population')
        if not {'L_DR', 'L_DI', 'R_LINE', 'METALLIC_RETURN'} <= {w.edge.id for w in loop}:
            raise AssertionError('DC line is not closed through metallic return')
        for w in loop:
            if w.edge.forward_only and w.orientation != 1:
                raise AssertionError(f'Reverse current across directed element {w.edge.id}')
        return loop

    def highlight(self, combined: CombinedState) -> dict[str, object]:
        """Union all valid combinations, including both commutations if they overlap."""
        signed: dict[str, int] = defaultdict(int)
        selected: set[str] = set()
        loops = []
        for rpair, ipair in product(combined.rectifier.pairs, combined.inverter.pairs):
            path = self.conduction_loop(rpair, ipair)
            loops.append(path)
            for walk in path:
                selected.add(walk.edge.id)
                signed[walk.edge.id] += walk.orientation
        scrs = {e for e in selected if self.edges[e].kind == 'scr'}
        expected = {
            *(f'R_{s}' for s in combined.rectifier.scrs),
            *(f'I_{s}' for s in combined.inverter.scrs),
        }
        if scrs != expected:
            raise AssertionError('Graph-derived SCR set differs from active state')
        n_expected = 4 + int(combined.rectifier_overlap) + int(combined.inverter_overlap)
        if len(scrs) != n_expected:
            raise AssertionError('Unexpected number of conducting valves')
        return {
            'active': frozenset(selected),
            'scrs': frozenset(scrs),
            'directions': dict(sorted(signed.items())),
            'loops': tuple(loops),
            'loop_count': len(loops),
        }
