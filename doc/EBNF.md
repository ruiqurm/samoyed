# EBNF

下面是一个lark风格的`EBNF`。和标准的EBNF不完全一致。
其中非终结符的`?`,`_`可以忽略认为它们没有效果。

```
start: (_NEWLINE | stmt)*
?stmt: simple_stmt | statedef
?inner_stmt : simple_stmt| match_stmt | for_stmt | if_stmt
simple_stmt: small_stmt _NEWLINE
full_expr : _full_expr
?small_stmt : pass_expr | branch_expr | _full_expr |assign_expr |break_stmt|continue_stmt
_suite:  _NEWLINE _INDENT inner_stmt+ _DEDENT
statedef: "state" NAME  ":" _suite
match_stmt : "match" _full_expr ":" _NEWLINE _INDENT case_stmt+ default_stmt? _DEDENT |  "match" at_expr ":" _NEWLINE _INDENT case_stmt+ silence_stmt? _DEDENT
case_stmt:  [_full_expr | reg]  "=>" _NEWLINE _INDENT inner_stmt+ _DEDENT | [_full_expr | reg] "=>" branch_expr
default_stmt : "default" "=>" _NEWLINE _INDENT inner_stmt+ _DEDENT | "default" "=>" branch_expr
silence_stmt : "silence" "=>" _NEWLINE _INDENT inner_stmt+ _DEDENT | "silence" "=>" branch_expr
for_stmt : "for" NAME "=" _full_expr "to" _full_expr  ":"  _NEWLINE _INDENT inner_stmt+ _DEDENT
if_stmt : "if" _full_expr ":" _NEWLINE _INDENT if_true_stmt _DEDENT ("else" ":" _NEWLINE _INDENT else_true_stmt+ _DEDENT)?
if_true_stmt : inner_stmt+
else_true_stmt : inner_stmt+
pass_expr : "pass"
branch_expr : "branch" NAME
continue_stmt : "continue"
break_stmt : "break"
assign_expr : NAME assign_op _full_expr
parameters: _NEWLINE* _full_expr ("," _NEWLINE* _full_expr)*
at_expr_parameter :  INT (","INT)?
at_expr : "@""(" at_expr_parameter ")" NAME "(" [parameters] ")"
_full_expr: or_test | conditional_expr
conditional_expr:or_test "?" or_test ":" _full_expr
?or_test: and_test ("or" and_test)*
?and_test: not_test_ ("and" not_test_)*
?not_test_: "not" not_test_ -> not_test
         | compare_expr
?compare_expr: plus_expr (comp_op plus_expr)?
?plus_expr : mul_expr (add_op mul_expr)*
?mul_expr : factor (mul_op factor)*
?factor : _unary_op factor | atom
!comp_op : "<"|">"|"=="|">="|"<="|"!="
!add_op : "+"|"-"
!mul_op : "*"|"/"|"//"|"%"
!assign_op : "="
!_unary_op: "+"|"-"
?atom :   "(" _full_expr ")"
          | FLOAT
          | INT
          | STR
          | NAME
          | "none" -> none
          | "true" -> true
          | "false" -> false
          | NAME "(" [parameters] ")" -> funccall
          | DOLLAR_VAR
STR : (STRING | LONG_STRING)+
DOLLAR_VAR : "$" NAME
CN_ZH_LETTER: /[\u4e00-\u9fa5]/
LETTER: UCASE_LETTER | LCASE_LETTER | CN_ZH_LETTER
NAME : ("_"|LETTER) ("_"|LETTER|DIGIT)*

%import common.WS_INLINE
%import common.FLOAT -> FLOAT
%import common.DIGIT -> DIGIT
%import common.LCASE_LETTER -> LCASE_LETTER
%import common.UCASE_LETTER -> UCASE_LETTER
%import common.INT -> INT

%declare _INDENT _DEDENT
%ignore WS_INLINE
%ignore COMMENT

reg : "/" /[^\/\n]+/ "/"
COMMENT: /#[^\n]*/
_NEWLINE: ( /\r?\n[\t ]*/ | COMMENT )+
STRING: /[ubf]?r?("(?!"").*?(?<!\\)(\\\\)*?"|'(?!'').*?(?<!\\)(\\\\)*?')/i
LONG_STRING: /[ubf]?r?(""".*?(?<!\\)(\\\\)*?"""|'''.*?(?<!\\)(\\\\)*?''')/is
```

