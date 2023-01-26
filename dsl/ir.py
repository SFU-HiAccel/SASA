import copy

from dsl import utils

class Node():
    """A immutable, hashable IR node.
    """
    SCALAR_ATTRS = ()
    LINEAR_ATTRS = ()

    @property
    def ATTRS(self):
        return self.SCALAR_ATTRS + self.LINEAR_ATTRS

    def __init__(self, **kwargs):
        for attr in self.SCALAR_ATTRS:
            setattr(self, attr, kwargs.pop(attr))
        for attr in self.LINEAR_ATTRS:
            setattr(self, attr, tuple(kwargs.pop(attr)))

    def __hash__(self):
        return hash((tuple(getattr(self, _) for _ in self.SCALAR_ATTRS),
                 tuple(tuple(getattr(self, _)) for _ in self.LINEAR_ATTRS)))

    def __eq__(self, other):
        return all(hasattr(other, attr) and
               getattr(self, attr) == getattr(other, attr)
               for attr in self.ATTRS)



    def visit(self, callback, args=None, pre_recursion=None, post_recursion=None):
        """A general-purpose, flexible, and powerful visitor.

        The args parameter will be passed to the callback callable so that it may
        read or write any information from or to the caller.

        A copy of self will be made and passed to the callback to avoid destructive
        access.

        If a new object is returned by the callback, it will be returned directly
        without recursion.

        If the same object is returned by the callback, if any attribute is
        changed, it will not be recursively visited. If an attribute is unchanged,
        it will be recursively visited.
        """

        def callback_wrapper(callback, obj, args):
            if callback is None:
                return obj
            result = callback(obj, args)
            if result is not None:
                return result
            return obj

        self_copy = copy.copy(self)
        obj = callback_wrapper(callback, self_copy, args)
        if obj is not self_copy:
            return obj
        self_copy = callback_wrapper(pre_recursion, copy.copy(self), args)
        scalar_attrs = {attr: getattr(self_copy, attr).visit(
            callback, args, pre_recursion, post_recursion)
                    if isinstance(getattr(self_copy, attr), Node)
                    else getattr(self_copy, attr)
                    for attr in self_copy.SCALAR_ATTRS}
        linear_attrs = {attr: tuple(_.visit(
            callback, args, pre_recursion, post_recursion)
                                if isinstance(_, Node) else _
                                for _ in getattr(self_copy, attr))
                    for attr in self_copy.LINEAR_ATTRS}

        for attr in self.SCALAR_ATTRS:
        # old attribute may not exist in mutated object
            if not hasattr(obj, attr):
                continue
            if getattr(obj, attr) is getattr(self, attr):
                if isinstance(getattr(obj, attr), Node):
                    setattr(obj, attr, scalar_attrs[attr])
        for attr in self.LINEAR_ATTRS:
        # old attribute may not exist in mutated object
            if not hasattr(obj, attr):
                continue
            setattr(obj, attr, tuple(
                c if a is b and isinstance(a, Node) else a
                for a, b, c in zip(getattr(obj, attr), getattr(self, attr),
                             linear_attrs[attr])))
        return callback_wrapper(post_recursion, obj, args)

class Let(Node):
    SCALAR_ATTRS = 'name', 'expr'

    def __str__(self):
        result = '{} = {}'.format(self.name, self.expr)
        return result

    @property
    def c_expr(self):
        return 'const {} {} = {};'.format('float', self.name, self.expr.c_expr)

class Ref(Node):
    SCALAR_ATTRS = ('name',)
    LINEAR_ATTRS = ('idx',)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.idx = tuple(self.idx)

    def __str__(self):
        result = '{}({})'.format(self.name, ', '.join(map(str, self.idx)))
        return result

    @property
    def c_expr(self):
        result = self.name
        return result

class BinaryOp(Node):
    LINEAR_ATTRS = 'operand', 'operator'

    def __str__(self):
        result = str(self.operand[0])
        for operator, operand in zip(self.operator, self.operand[1:]):
            result += ' {} {}'.format(operator, operand)
        if self.singleton:
            return result
        return utils.parenthesize(result)

    @property
    def c_expr(self):
        result = self.operand[0].c_expr
        for operator, operand in zip(self.operator, self.operand[1:]):
            result += ' {} {}'.format(operator, operand.c_expr)
        if self.singleton:
            return result
        return utils.parenthesize(result)

    @property
    def singleton(self) -> bool:
        return len(self.operand) == 1

class Expr(BinaryOp):
    pass

class LogicAnd(BinaryOp):
    pass

class BinaryOr(BinaryOp):
    pass

class Xor(BinaryOp):
    pass

class BinaryAnd(BinaryOp):
    pass

class EqCmp(BinaryOp):
    pass

class LtCmp(BinaryOp):
    pass

class AddSub(BinaryOp):
    pass

class MulDiv(BinaryOp):
    pass

class Unary(Node):
    SCALAR_ATTRS = ('operand',)
    LINEAR_ATTRS = ('operator',)

    def __str__(self):
        return ''.join(self.operator) + str(self.operand)

    @property
    def c_expr(self):
        return ''.join(self.operator)+self.operand.c_expr

class Operand(Node):
    SCALAR_ATTRS = 'call', 'ref', 'num', 'expr', 'var'

    def __str__(self):
        for attr in ('call', 'ref', 'num', 'var'):
            if getattr(self, attr) is not None:
                return str(getattr(self, attr))
        else:
            return str(self.expr)

    @property
    def c_expr(self):
        for attr in ('call', 'ref', 'num', 'var'):
            if attr == 'num':
                attr = getattr(self, attr)
                if attr is not None:
                    return '(float)' + str(attr)
            else:
                attr = getattr(self, attr)
                if attr is not None:
                    if hasattr(attr, 'c_expr'):
                        return attr.c_expr
                    else:
                        return str(attr)
        else:
            return utils.parenthesize(self.expr.c_expr)

class Call(Node):
    SCALAR_ATTRS = ('name',)
    LINEAR_ATTRS = ('arg',)

    def __str__(self):
        if self.name == 'if':
            return ' ({}?{}:{})'.format(str(self.arg[0]), str(self.arg[1]), str(self.arg[2]))
        else:
            return ' {} ({})'.format(self.name, ', '.join(map(str, self.arg)))


    @property
    def c_expr(self):
        if self.name == 'if':
            return ' ({}?{}:{})'.format(str(self.arg[0].c_expr), str(self.arg[1].c_expr), str(self.arg[2].c_expr))
        else:
            return ' {} ({})'.format(self.name, ', '.join(_.c_expr for _ in self.arg))

class Var(Node):
    SCALAR_ATTRS = ('name',)

    def __str__(self):
        return self.name

    @property
    def c_expr(self):
        return self.name

class ScalarStmt(Node):
    SCALAR_ATTRS = ('name', )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __str__(self):
        result = 'scalar float: {}'.format(self.name)
        return result

class InputStmt(Node):
    SCALAR_ATTRS = ('name', )
    LINEAR_ATTRS = ('size', )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __str__(self):
        result = 'input float: {}'.format(self.name)
        if self.size:
            result += '[{}]'.format(', '.join(map(str, self.size)))
        return result

class LocalStmt(Node):
    SCALAR_ATTRS = ['let',]

    def __str__(self):
        return str(self.let)

class OutputStmt(Node):
    SCALAR_ATTRS = 'ref', 'expr'

    @property
    def name(self):
        return self.ref.name

    def __str__(self):
        return 'output float: {} = {}'.format(self.ref, self.expr)

class Program(Node):
    SCALAR_ATTRS = ('iterate', 'app_name', 'kernel_count', 'repeat_count', 'output_stmt', 'boarder_type')
    LINEAR_ATTRS = ('scalar_stmts', 'input_stmts', 'local_stmts')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = self.input_stmts[0].size
        self.dim = len(self.input_stmts[0].size)

    def __str__(self):
        return '\n'.join(filter(None, (
            'kernel: {}'.format(self.app_name),
            'iterate: {}'.format(self.iterate),
            'boarder type: {}'.format(self.boarder_type),
            'kernel count: {}'.format(self.kernel_count),
            'repeat count: {}'.format(self.repeat_count),
            'size: {}'.format(self.size),
            '\n'.join(map(str, self.scalar_stmts)),
            '\n'.join(map(str, self.input_stmts)),
            '\n'.join(map(str, self.local_stmts)),
            str(self.output_stmt)
        )))

CLASSES = (
    Program,
    ScalarStmt,
    InputStmt,
    LocalStmt,
    OutputStmt,
    Let,
    Ref,
    Expr,
    LogicAnd,
    BinaryOr,
    Xor,
    BinaryAnd,
    EqCmp,
    LtCmp,
    AddSub,
    MulDiv,
    Unary,
    Operand,
    Call,
    Var
)