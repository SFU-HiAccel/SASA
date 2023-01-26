import math

from dsl import ir

import logging

_logger = logging.getLogger().getChild(__name__)

def cal_relative(idx, relative):
    if len(idx) != len(relative):
        raise Exception("Should always have same index length")
    result = []
    for i, j in zip(idx, relative):
        result.append(i-j)
    return tuple(result)

def find_relative_ref_position(stmt, relative_position, acc_positions):
    """Find references in all positions of the stmt

    :param stmt: the input stmt
    :param relative_position: relative position
    :return: all references in the stmt
    """

    if stmt is None:
        _logger.debug('No stmt input')
        return acc_positions

    def find_in_a_place(node: ir.Node, ref_positions) -> dict:
        def visitor(node, args=None):

            if isinstance(node, ir.Ref):
                if node.name not in ref_positions.keys():
                    ref_positions[node.name] = set()
                ref_positions[node.name].add(cal_relative(node.idx, relative_position))
            elif hasattr(node, 'operand') or hasattr(node, 'arg'):
                if hasattr(node, 'operand'):
                    if hasattr(node.operand, '__iter__'):
                        for operand in node.operand:
                            temp_positions = find_in_a_place(operand, ref_positions)
                            for name, positions in temp_positions.items():
                                if name not in ref_positions.keys():
                                    ref_positions[name] = set()
                                for position in positions:
                                    ref_positions[name].add(position)
                    else:
                        operand = node.operand
                        temp_positions = find_in_a_place(operand, ref_positions)
                        for name, positions in temp_positions.items():
                            if name not in ref_positions.keys():
                                ref_positions[name] = set()
                            for position in positions:
                                ref_positions[name].add(position)

                if hasattr(node, 'arg'):
                    for arg in node.arg:
                        temp_positions = find_in_a_place(arg, ref_positions)
                        for name, positions in temp_positions.items():
                            if name not in ref_positions.keys():
                                ref_positions[name] = set()
                            for position in positions:
                                ref_positions[name].add(position)

            return ref_positions

        return node.visit(visitor)

    return find_in_a_place(stmt.expr, acc_positions)

def find_refs_by_row(postions: list) -> dict:
    result = {}
    for refs in postions:
        if refs[0] not in result.keys():
            result[refs[0]] = set()
            result[refs[0]].add(refs[1])
        else:
            result[refs[0]].add(refs[1])
    return result

def find_refs_by_offset(postions: list, size: tuple) -> list:
    result = []
    for ref in postions:
        offset = 0
        for i in range(len(size)):
            offset *= size[i]
            offset += ref[i]
        result.append(offset)
    result.sort()
    return result