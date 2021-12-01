from numbers import Number
from operator import lt, le, eq, ne, ge, gt, not_, or_, and_ \
    , add, sub, mul, mod, truediv, floordiv
from typing import Union

import lark

from exception import SamoyedTypeError,SamoyedInterpretError


class Stage:
    """
    DFA状态
    """

    def __init__(self, ast: lark.tree.Tree):
        self.ast = ast


class Context:
    """
    上下文
    """

    def __init__(self):
        self._var = dict()

    def names(self) -> dict:
        return self._var


class Interpreter:
    """
    解释器
    """
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

    def __init__(self, ast: lark.tree.Tree):
        self.ast = ast
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
                    self.entrance = self.stage[name] = Stage(node)
                else:
                    self.stage[name] = Stage(node)
            elif node.data == "assign_call":
                # 如果是赋值语句，直接进行赋值
                # 赋值语句由三个部分组成：0[name] 1[=] 2[expression]
                name = node.children[0]
                self.context.names()[name] = node.children[2]

    def get_expr_result(self, expr: lark.tree.Tree) -> Union[int, float, str]:
        """
        获取表达式的结果
        :param expr: 表达式
        :return: 表达式的结果
        """
        stack = []
        return self.get_expression(expr)

    def get_expression(self, expr: Union[lark.tree.Tree, lark.lexer.Token])->Union[int,float,bool,None,str]:
        """
        递归计算表达式的值
        :param expr:
        :return:
        """
        if isinstance(expr, lark.lexer.Token):
            # 如果是终结符
            if expr.type == "NAME":
                # 如果是变量
                return self.context.names().get(expr, None)
            elif expr.type == "STR" or expr.type =='none' or \
                 expr.type =="true" or expr.type=="false" or \
                 expr.type == "SIGNED_INT" or expr.type == "SIGNED_FLOAT":
                # 如果是一些常量
                    return expr
            elif expr.type == "funcall":
                # 如果是函数调用
                # todo
                return 0
            else:
                raise SamoyedInterpretError(expr.type,pos=(expr.line,expr.column))
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
