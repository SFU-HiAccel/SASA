import logging

from core import utils
from dsl import arithmatic

_logger = logging.getLogger().getChild(__name__)


class Stencil():

    def __init__(self, **kwargs):
        self.iterate = kwargs.pop('iterate')
        self.boarder_type = kwargs.pop('boarder_type')
        self.kernel_count = kwargs.pop('kernel_count')
        self.repeat_count = kwargs.pop('repeat_count')
        self.app_name = kwargs.pop('app_name')
        self.size = kwargs.pop('size')
        self.scalar_stmts = kwargs.pop('scalar_stmts')
        self.input_stmts = kwargs.pop('input_stmts')
        self.local_stmts = kwargs.pop('local_stmts')
        self.output_stmt = kwargs.pop('output_stmt')

        self.scalar_vars = []
        for scalar in self.scalar_stmts:
            self.scalar_vars.append(scalar.name)

        self.input_vars = []
        for stmt in self.input_stmts:
            self.input_vars.append(stmt.name)

        _logger.debug("Get all input vars: [%s]",
                      ', '.join(self.input_vars))

        self.output_var = self.output_stmt.ref.name

        _logger.debug("Get output var: [%s]", self.output_var)

        self.output_idx = self.output_stmt.ref.idx

        self.output_stmt.expr = arithmatic.simplify(self.output_stmt.expr)
        for i in range(0, len(self.local_stmts)):
            self.local_stmts[i].let = arithmatic.simplify(self.local_stmts[i].let)

        self.all_refs = utils.find_relative_ref_position(self.output_stmt, self.output_idx, {})
        for local_stmt in self.local_stmts:
            self.all_refs = utils.find_relative_ref_position(local_stmt.let,
                                                             tuple(0 for i in range(0, len(self.output_idx))),
                                                             self.all_refs)

        _logger.debug("Get references: \n\t%s",
                      '\n\t'.join("%s:\t%s" % (name, ", ".join("(" + ", ".join("%d" % i[j]
                                                                        for j in range(0, len(self.output_idx)))+")"
                                                                            for i in pos))
                                                                                for name, pos in self.all_refs.items()))