lan = """
Program:
(
    ('ITERATE' ':' iterate=INT)
    ('BOARDER' ':' boarder_type=BoarderType)?
    ('KERNEL' ':' app_name=ID)
    ('COUNT' ':' kernel_count=INT)
    ('REPEAT' ':' repeat_count=INT)?
    (scalar_stmts=ScalarStmt)*
    (input_stmts=InputStmt)+
    (local_stmts=LocalStmt)*
    (output_stmt=OutputStmt)
)#;

BoarderType: 'overlap' | 'streaming';

Comment: /\/\/.*$/;

ScalarStmt: 'scalar' name=ID;

InputStmt: 'input' name=ID '(' size=INT (',' size=INT)* ')'; //now all inputs&outputs are forced to be float value

LocalStmt: 'local' let=Let;

OutputStmt: 'output' ref=Ref '=' expr=Expr;//now all inputs&outputs are forced to be float value

//Specify Expressions
Dec: /\d+([Uu][Ll][Ll]?|[Ll]?[Ll]?[Uu]?)/;
Int: ('+'|'-')?Dec;
Float: /(((\d*\.\d+|\d+\.)([+-]?[Ee]\d+)?)|(\d+[+-]?[Ee]\d+))[FfLl]?/;
Num: Float|Int;

FuncName: 'fabs' | 'abs' | 'if' | 'sqrt'; //more functions to be added

Let: name=ID '=' expr=Expr;
Ref: name=ID '(' idx=INT (',' idx=INT)* ')';

Expr: operand=LogicAnd (operator=LogicOrOp operand=LogicAnd)*;
LogicOrOp: '||';

LogicAnd: operand=BinaryOr (operator=LogicAndOp operand=BinaryOr)*;
LogicAndOp: '&&';

BinaryOr: operand=Xor (operator=BinaryOrOp operand=Xor)*;
BinaryOrOp: '|';

Xor: operand=BinaryAnd (operator=XorOp operand=BinaryAnd)*;
XorOp: '^';

BinaryAnd: operand=EqCmp (operator=BinaryAndOp operand=EqCmp)*;
BinaryAndOp: '&';

EqCmp: operand=LtCmp (operator=EqCmpOp operand=LtCmp)*;
EqCmpOp: '=='|'!=';

LtCmp: operand=AddSub (operator=LtCmpOp operand=AddSub)*;
LtCmpOp: '<='|'>='|'<'|'>';

AddSub: operand=MulDiv (operator=AddSubOp operand=MulDiv)*;
AddSubOp: '+'|'-';

MulDiv: operand=Unary (operator=MulDivOp operand=Unary)*;
MulDivOp: '*'|'/'|'%';

Unary: (operator=UnaryOp)* operand=Operand;
UnaryOp: '+'|'-'|'~'|'!';

Operand: call=Call | ref=Ref | num=Num | '(' expr=Expr ')' | var=Var;
Call: name=FuncName '(' arg=Expr (',' arg=Expr)* ')';
Var: name=ID;
"""