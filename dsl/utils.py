import contextlib
import logging
import signal

_logger = logging.getLogger().getChild(__name__)

class InternalError(Exception):
    pass

class SemanticError(Exception):
    pass

class SemanticWarn(Exception):
    pass

def parenthesize(expr) -> str:
    return '({})'.format(unparenthesize(expr))

def unparenthesize(expr) -> str:
    expr_str = str(expr)
    while expr_str.startswith('(') and expr_str.endswith(')'):
        expr_str = expr_str[1:-1]
    return expr_str

