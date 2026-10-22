"""Exact selected forests. This representation is not an eligibility authority."""

from copy import deepcopy
from .store import StateError, digest

WITNESS_FORMAT = 'selected-witness-forest-v1'
NODE_FIELDS = {'inference', 'inference_hash', 'claim', 'environment', 'assumptions', 'premises'}


def pack(roots, table):
    """Project only the selected reachable nodes, sharing identical subarguments."""
    selected, pending = {}, list(roots)
    while pending:
        identifier = pending.pop()
        if identifier in selected:
            continue
        node = table[identifier]
        selected[identifier] = deepcopy(node)
        pending.extend(node['premises'])
    return {'format': WITNESS_FORMAT, 'roots': list(roots), 'nodes': selected}


def nodes(forest):
    """Verify exact structural integrity, including no unreachable injected data."""
    if (not isinstance(forest, dict) or set(forest) != {'format', 'roots', 'nodes'}
            or forest['format'] != WITNESS_FORMAT or not isinstance(forest['roots'], list)
            or not isinstance(forest['nodes'], dict)):
        raise StateError('Malformed selected witness forest')
    table = forest['nodes']
    if any(not isinstance(r, str) or r not in table for r in forest['roots']):
        raise StateError('Witness root is absent')
    for identifier, node in table.items():
        if (not isinstance(identifier, str) or not isinstance(node, dict) or set(node) != NODE_FIELDS
                or any(not isinstance(node[k], str) or not node[k] for k in ('inference', 'inference_hash', 'claim'))
                or any(not isinstance(node[k], list) or any(not isinstance(v, str) or not v for v in node[k])
                       for k in ('environment', 'assumptions', 'premises'))
                or digest(node) != identifier):
            raise StateError('Witness node content/hash is malformed')
    completed, active = set(), set()
    pending = [(r, False) for r in reversed(forest['roots'])]
    while pending:
        identifier, leaving = pending.pop()
        if leaving:
            active.remove(identifier)
            completed.add(identifier)
        elif identifier in active:
            raise StateError('Witness node cycle')
        elif identifier not in completed:
            if identifier not in table:
                raise StateError('Witness child is absent')
            active.add(identifier)
            pending.append((identifier, True))
            pending.extend((child, False) for child in reversed(table[identifier]['premises']))
    if completed != set(table):
        raise StateError('Unreachable data in selected witness forest')
    return table


def roots(forest):
    table = nodes(forest)
    return [table[r] for r in forest['roots']]


def single_root(forest):
    selected = roots(forest)
    if len(selected) != 1:
        raise StateError('Expected one exact proof root')
    return selected[0]


def merge(forests):
    selected, table = [], {}
    for forest in forests:
        validated = nodes(forest)
        selected.extend(forest['roots'])
        for identifier, node in validated.items():
            if identifier in table and table[identifier] != node:
                raise StateError('Conflicting content-addressed witness node')
            table[identifier] = node
    return pack(selected, table)
