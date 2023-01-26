import copy
import logging
import contextlib
import math
from functools import reduce

_logger = logging.getLogger().getChild(__name__)

class InternalError(Exception):
  pass

class SemanticError(Exception):
  pass

class SemanticWarn(Exception):
  pass

class Printer():
    def __init__(self, out):
        self._out = out
        self._indent = 0
        self._tab = 2
        self._comments = []

    def println(self, line='', indent=-1):
        if indent < 0:
            indent = self._indent
        if line:
            self._out.write('%s%s\n' % (' '*indent*self._tab, line))
        else:
            self._out.write('\n')

    def do_indent(self):
        self._indent += 1

    def un_indent(self):
        self._indent -= 1

    def do_scope(self, comment=''):
        self.println('{')
        self.do_indent()
        self._comments.append(comment)

    def un_scope(self, comment='', suffix=''):
        self.un_indent()
        popped_comment = self._comments.pop()
        if comment:
            self.println('}%s // %s' % (suffix, comment))
        else:
            if popped_comment:
                self.println('}%s // %s' % (suffix, popped_comment))
            else:
                self.println('}%s' % suffix)

    def print_func(self, name, params, suffix='', align=80):
        lines = [name + '(']
        for param in params:
            if ((self._indent + min(1, len(lines) - 1)) * self._tab +
                len(lines[-1]) + len(param + ', ')) > align:
                lines.append(param + ', ')
            else:
                lines[-1] += param + ', '
        if lines[-1][-2:] == ', ':
            lines[-1] = lines[-1][:-2] + ')' + suffix
        line = lines.pop(0)
        self.println(line)
        if lines:
            self.do_indent()
            for line in lines:
                self.println(line)
            self.un_indent()

    @contextlib.contextmanager
    def for_(self, *args):
        if len(args) == 3:
            self.println('for ({}; {}; {}) {{'.format(*args))
        elif len(args) == 2:
            self.println('for ({} : {}) {{'.format(*args))
        else:
            raise InternalError('for_ takes 2 or 3 arguments')
        self.do_indent()
        yield
        self.un_indent()
        self.println('}')

    @contextlib.contextmanager
    def do_while(self, cond):
        self.println('do {')
        self.do_indent()
        yield
        self.un_indent()
        self.println('}} while ({});'.format(cond))

    @contextlib.contextmanager
    def if_(self, cond):
        self.println('if ({}) {{'.format(cond))
        self.do_indent()
        yield
        self.un_indent()
        self.println('}')

    @contextlib.contextmanager
    def ifel_(self, cond):
        self.println('if ({}) {{'.format(cond))
        self.do_indent()
        yield
        self.un_indent()

    @contextlib.contextmanager
    def elif_(self, cond):
        self.println('}} else if ({}) {{'.format(cond))
        self.do_indent()
        yield
        self.un_indent()
        self.println('}')


    @contextlib.contextmanager
    def elifel_(self, cond):
        self.println('}} else if ({}) {{'.format(cond))
        self.do_indent()
        yield


    @contextlib.contextmanager
    def else_(self):
        self.un_indent()
        self.println('} else {')
        self.do_indent()
        yield
        self.un_indent()
        self.println('}')

def print_define(printer, var, val):
    printer.println('#ifndef %s' % var)
    printer.println('#define %s %d' % (var, val))
    printer.println('#endif//%s' % var)

def print_guard(printer, var, val):
    printer.println('#ifdef %s' % var)
    printer.println('#if %s != %d' % (var, val))
    printer.println('#error %s != %d' % (var, val))
    printer.println('#endif//%s != %d' % (var, val))
    printer.println('#endif//%s' % var)

def idx2str(idx: int):
    if idx<0:
        return 'm' + str(abs(idx))
    else:
        return str(idx)

def get_module_name(module_id):
    return 'module_%d' % module_id

def get_func_name(module_id):
    return 'Module%dFunc' % module_id

def cal_relative(idx, relative):
    if len(idx) != len(relative):
        raise Exception("Should always have same index length")
    result = []
    for i, j in zip(idx, relative):
        result.append(i-j)
    return tuple(result)

def cvt_idx2offset(idx: tuple, size: tuple) -> int:
    offset = 0
    for i in range(len(size)):
        offset *= size[i]
        offset += idx[i]
    return offset

def get_parameter_printed(inputs: list, scalars: list, output: str):
    out = ', '.join(inputs)
    out = out + ', ' + output
    if scalars:
        out = out + ', ' + ', '.join(scalars)
    return out