import os
from numbers import Number
from operator import lt, le, eq, ne, ge, gt, not_, or_, and_ \
    , add, sub, mul, mod, truediv, floordiv
from typing import Union

import lark
from lark import Lark, Transformer
from lark.indenter import Indenter
from lark.exceptions import UnexpectedToken,UnexpectedCharacters
from .exception import SamoyedTypeError, SamoyedInterpretError, NotFoundEntrance, \
    SamoyedNameError, NotImplementError

"""
解释器核心
"""


# class Stage:
#     """
#     DFA状态
#     """
#
#     def __init__(self, ast: lark.tree.Tree):
#         self.ast = ast
class SamoyedIndenter(Indenter):
    """
    间隔控制
    """
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 8


class SamoyedTransformer(Transformer):
    """
    基础的语法制导，只会转换一些常量。
    """
    none = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False

    def SIGNED_FLOAT(self, value:lark.Token) -> float:
        return float(value)

    def SIGNED_INT(self, value:lark.Token) -> int:
        return int(value)
    def STR(self,value:lark.Token)->str:
        if len(value)>3 and value[1] == value[2] == "\"":
            return value[3:-3]
        else:
            return value[1:-1]

class Context:
    """
    上下文
    """

    def __init__(self):
        self.names = dict()
        self.stage = None  # type:lark.tree.Tree
        self.next = None  # type:lark.tree.Tree


class Interpreter:
    """
    解释器
    """
    with open("{}/samoyed.gram".format(os.path.abspath(os.path.dirname(__file__)))) as f:
        parser = Lark(f.read(), parser='lalr', postlex=SamoyedIndenter(), transformer=SamoyedTransformer())

    def __init__(self, code: str, dont_parse=False):
        self.__isinit = False
        # 词法和语法分析
        try:
            self.ast = self.parser.parse(code)  # type:lark.tree.Tree
        except UnexpectedToken as e:
            raise SamoyedInterpretError()
        except UnexpectedCharacters as e:
            raise SamoyedInterpretError()
    def init(self):
        self.stage = dict()
        self.entrance = None
        self.context = Context()
        # 遍历AST的顶层，确定所有的stage和入口
        for node in self.ast.children:
            if node.data == 'statedef':
                # 如果是状态定义
                # 第一个子节点是名称
                name = node.children[0]
                if name == "main":
                    self.entrance = self.stage[name] = node
                else:
                    self.stage[name] = node
            elif node.data == "assign_call":
                # 如果是赋值语句，直接进行赋值
                # 赋值语句由三个部分组成：0[name] 1[=] 2[expression]
                name = node.children[0]
                self.context.names[name] = self.get_expression(node.children[2])
        if self.entrance is None:
            raise NotFoundEntrance

        self.context.stage = self.entrance
        self.__isinit = True

    def exec(self):
        """
        执行
        :return:
        """
        if not self.__isinit:
            return
        while True:
            for stat in self.context.stage.children:
                # 遍历并执行每个状态中的语句
                self.exec_statement(stat)
            if self.context.next is None:
                # 如果未指定下一个状态，那么结束
                return
            else:
                self.context.stage = self.context.next
                self.context.next = None

    def exec_statement(self, stat: lark.tree.Tree) -> None:
        """
        执行每一个语句
        :param stat: 语句语法节点
        :return:
        """
        if stat.data == "simple_stmt":
            simple_stmt = stat.children[0]
            simple_stmt_type = simple_stmt.data
            if simple_stmt_type == "branch_expr":
                next_state = simple_stmt.children[0].data
                if next_state in self.stage:
                    self.context.next = self.stage[next_state]
                else:
                    raise SamoyedNameError
            elif simple_stmt_type == "full_expr":
                # 单纯的表达式不会产生任何副作用，因此跳过这里
                pass
            elif simple_stmt_type == "assign_expr":
                self.context.names[simple_stmt.children[0]] = self.get_expression(simple_stmt.children[2])
            else:
                raise NotImplementError
        elif stat.data == "match_stmt":
            """
            match expr :
                compare_value =>
                    stat
            """
            # stat.children[0]为
            expr = stat.children[0]
            expr_result = self.get_expression(expr)
            for case_statment in stat.children[1:]:
                if case_statment.data == "default_stmt":
                    # 如果是默认情况
                    # 直接执行这个语句
                    self.exec_statement(case_statment.children[1])
                    break
                else:
                    # 否则，判断值相同才执行
                    compare_value = self.get_expression(case_statment.children[0])
                    if compare_value == expr_result:
                        self.exec_statement(case_statment.children[1])
                        break
        elif stat.data == "if_stmt":
            raise NotImplementError
        else:
            raise NotImplementError

    def get_expression(self, expr: Union[lark.tree.Tree, lark.lexer.Token]) -> Union[int, float, bool, None, str]:
        """
        递归计算表达式的值
        :param expr:
        :return:
        """
        if isinstance(expr, lark.lexer.Token):
            # 如果是终结符
            if expr.type == "NAME":
                # 如果是变量
                return self.context.names.get(expr, None)
            elif expr.type == "STR" or expr.type == 'none' or \
                    expr.type == "true" or expr.type == "false" or \
                    expr.type == "SIGNED_INT" or expr.type == "SIGNED_FLOAT":
                # 如果是一些常量
                return expr
            elif expr.type == "funcall":
                # 如果是函数调用
                # todo
                if (func := self.context.names.get(expr, None)) is None and callable(func):
                    return func()
                else:
                    raise SamoyedNameError("No such function {}".format(expr), pos=(expr.line, expr.column))
            else:
                raise SamoyedInterpretError(expr.type, pos=(expr.line, expr.column))
        else:
            # 如果是非终结符
            if expr.data == "compare_expr" or expr.data == "or_test" or \
                    expr.data == "and_test" or expr.data == "not_test":
                left = self.get_expression(expr.children[0])
                right = self.get_expression(expr.children[2])
                # expr.children[1] 是符号非终止符
                # expr.children[1].children[0] 即比较符号本身
                operator = expr.children[1].children[0]
                return self.compare(operator, left, right)
            elif expr.data == "arith_expr":
                left = self.get_expression(expr.children[0])
                right = self.get_expression(expr.children[2])
                operator = expr.children[1].children[0]
                return self.arith(operator, left, right)

    def compare(self, operator: str, a: Union[int, float, str], b: Union[int, float, str]) -> bool:

        if isinstance(a, Number) and isinstance(b, Number) or isinstance(a, str) and isinstance(b, str):
            return add(a, b)
        else:
            raise SamoyedTypeError("无法比较类型{}和{}".format(type(a), type(b)))

    def arith(self, operator, a: Union[int, float, str], b: Union[int, float, str]) -> Union[int, float, str]:
        if operator == "+":
            if isinstance(a, Number) and isinstance(b, Number):
                # 如果a,b都是数字
                return add(a, b)
            elif isinstance(a, str) or isinstance(b, str):
                # a,b有字符串
                return "{}{}".format(a, b)
            else:
                raise SamoyedTypeError("无法运算类型{}{}{}".format(type(a), operator, type(b)))
        else:
            if isinstance(a, str) or isinstance(b, str):
                raise SamoyedTypeError("无法运算类型{}{}{}".format(type(a), operator, type(b)))
            return self.arith_operator[operator](a, b)

    compare_operator = {
        ">": gt,
        "<": lt,
        ">=": ge,
        "<=": le,
        "==": eq,
        "!=": ne,
        "not": not_,
        "or": or_,
        "and": and_
    }
    arith_operator = {
        "+": add,
        "-": sub,
        "*": mul,
        "/": truediv,
        "//": floordiv,
        "%": mod
    }
