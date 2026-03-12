"""Compute simple degree-centrality scores from map adjacency."""

from bots.utils.tactical.base_location import base_location
from bots.utils.tactical.neighbors_for import neighbors_for


def centerity_scores(loc_abut: dict[str, list[str]]) -> dict[str, float]:
    """Return normalized degree centrality score for each base location."""
    graph: dict[str, set[str]] = {}
    for raw_loc in loc_abut.keys():
        loc = base_location(raw_loc)
        if not loc:
            continue
        graph.setdefault(loc, set())
        graph[loc] |= neighbors_for(loc, loc_abut)

    max_degree = max((len(neighbors) for neighbors in graph.values()), default=1)
    if max_degree <= 0:
        max_degree = 1
    return {loc: len(neighbors) / float(max_degree) for loc, neighbors in graph.items()}
