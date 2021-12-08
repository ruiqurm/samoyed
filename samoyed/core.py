import os
from functools import partial
from functools import reduce
from numbers import Number
from operator import lt, le, eq, ne, ge, gt, not_, or_, and_ \
    , sub, mul, mod, truediv, floordiv
from typing import Union

import lark
from lark import Lark, Transformer
from lark.exceptions import UnexpectedToken, UnexpectedCharacters
from lark.indenter import Indenter

from libs import TimeControl
from exception import SamoyedTypeError, SamoyedInterpretError, NotFoundEntrance, \
    SamoyedNameError, NotImplementError, SamoyedRuntimeError

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
def mock_add(a: Union[int, float, bool, str, None], b: Union[int, float, bool, str, None]) -> Union[
    int, float, str, None]:
    """
    实现字符串和数字相加操作的add
    """
    if isinstance(a, Number) and isinstance(b, Number):
        return a + b
    elif isinstance(a, str) or isinstance(b, str):
        return "{}{}".format(a, b)
    else:
        return None


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

    def FLOAT(self, value: lark.Token) -> float:
        return float(value)

    def INT(self, value: lark.Token) -> int:
        return int(value)

    def STR(self, value: lark.Token) -> str:
        if len(value) > 3 and value[1] == value[2] == "\"":
            return value[3:-3]
        else:
            return value[1:-1]


class Context:
    """
    上下文
    """

    def __init__(self, outer_context: dict = None):
        """
        :param outer_context: 继承的属性
        """
        self.names = dict(outer_context) if outer_context is not None else dict()
        self.names["print"] = print
        self.names["speak"] = print
        self.names["listen"] = input
        self.names["exit"] = self.set_exit
        self.stage = None  # type:lark.tree.Tree
        self.next = None  # type:lark.tree.Tree
        self.__exit = False

    def is_exit(self):
        return self.__exit

    def set_exit(self):
        self.__exit = True


class Interpreter:
    """
    解释器
    """
    with open("{}/samoyed.gram".format(os.path.abspath(os.path.dirname(__file__)))) as f:
        parser = Lark(f.read(), parser='lalr', postlex=SamoyedIndenter(), transformer=SamoyedTransformer())

    def __init__(self, code: str, context: dict = None, dont_init=False):
        """
        
        :param code: 代码
        :param context: 额外的上下文
        :param dont_init: 不进行初始化 
        """
        self.__isinit = False
        # 词法和语法分析
        try:
            self.ast = self.parser.parse(code)  # type:lark.tree.Tree
        except UnexpectedToken as e:
            raise SamoyedInterpretError()
        except UnexpectedCharacters as e:
            raise SamoyedInterpretError()
        self.context = Context(context)
        if not dont_init:
            self.init()

    def init(self):
        self.stage = dict()
        self.entrance = None
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
            else:
                self.exec_statement(node)
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
            for stat in self.context.stage.children[1:]:
                # 遍历并执行每个状态中的语句
                self.exec_statement(stat)
                # 如果调用了exit，直接退出
                if self.context.is_exit():
                    return
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
            """
            如果是一个简单的表达式
            simple_stmt包括：
            * pass_expr 什么也不做.
            * branch_expr 跳转表达式
            * _full_expr 一个普通表达式，如果这个表达式非过程，那么它是无副作用的
            * assign_expr 赋值表达式
            """
            simple_stmt = stat.children[0]
            simple_stmt_type = simple_stmt.data
            if simple_stmt_type == "branch_expr":
                # 是一个跳转语句
                next_state = simple_stmt.children[0]
                if next_state in self.stage:
                    self.context.next = self.stage[next_state]
                else:
                    raise SamoyedNameError

            elif simple_stmt_type == "assign_expr":
                # 是一个赋值语句
                self.context.names[simple_stmt.children[0]] = self.get_expression(simple_stmt.children[2])
            elif simple_stmt_type == "pass_expr":
                return
            else:
                # 是一个表达式
                self.get_expression(stat.children[0])
        elif stat.data == "match_stmt":
            """
            match字句有两种形式
            第一种形式是带有时间控制的匹配
            其中，@的第一个参数是超时时间，必选；第二个参数是最少持续时间，可选；
            @后应该接入一个函数调用。延时表达式会不断调用这个函数
            match @(10,2)funcall :
                compare_expr =>
                    stat
                ...
                slience =>
                    stat
            第二种形式是普通的多值匹配
            match expr :
                compare_expr =>
                    stat
                compare_expr =>
                    stat
                default =>
                    stat
            """
            expr = stat.children[0] # expr
            if isinstance(expr, lark.tree.Tree) and expr.data == "stream_expr":
                """
                如果是限定时间的语句...
                会尝试一直读取值，直到超时或者匹配成功
                """
                # 获取函数
                _context = self.context.names
                if (func := _context.get(expr.children[1], None)) is not None and callable(func):
                    if expr.children[2] is not None:
                        # 如果有参数
                        func = partial(func, *[self.get_expression(i) for i in expr.children[2].children])
                else:
                    raise SamoyedNameError("No such function")

                # 构造一个TimeControl对象。将这个函数传入构造
                control = TimeControl(func, *expr.children[0].children)
                results = [] # 每次读取的值
                # 预先算出每个case的表达式，不包含silence字句
                cases = [self.get_expression(case_statment.children[0]) for case_statment in stat.children[1:] if
                         case_statment.data != "slience_stmt"]
                find_flag = False  # 是否完成匹配
                finded_case = None # 匹配的是第几个

                # 遍历生成器
                # 如果超时，生成式结束
                for result in control():
                    # 保存每次结果
                    if result is not None:
                        results.append(result)
                    # 如果结果出现在case字句中，那么跳出
                    if not control.can_exit.is_set():continue
                    for i, case in enumerate(cases):
                        concat_result = "".join(results)
                        if concat_result.find(case) != -1:
                            find_flag = True
                            finded_case = i
                            control.cancel()
                            break
                    # 如果匹配，那么执行这个子块
                    if find_flag and control.can_exit.is_set():
                        self.exec_statement(stat.children[finded_case + 1].children[1])
                        return
                # 没有完成任何匹配
                # 如果有slience块，执行slience块
                if stat.children[-1].data == "slience_stmt":
                    for st in stat.children[-1].children:
                        # 执行块中的每个语句
                        self.exec_statement(st)
            else:
                expr_result = self.get_expression(expr)
                for case_statment in stat.children[1:]: # stat.children[0]是bool表达式
                    if case_statment.data == "default_stmt":
                        """
                        如果是默认情况，直接执行这个语句
                        parser保证默认情况在最后面
                        """
                        for st in case_statment.children:
                            # 执行块中的每个语句
                            self.exec_statement(st)
                        break
                    else:
                        """
                        否则，判断值相同才执行
                        字符串只要包含子串就会执行                        
                        """
                        matching_value = self.get_expression(case_statment.children[0])
                        is_str = isinstance(matching_value, str)
                        if is_str  and expr_result.find(matching_value) or not is_str and matching_value ==expr_result:
                            for st in case_statment.children[1:]:
                                # 执行块中的每个语句
                                self.exec_statement(st)
                            break
        elif stat.data == "if_stmt":
            bool_expr = stat.children[0]
            if bool_expr:
                self.exec_statement(stat.children[1])
            else:
                self.exec_statement(stat.children[2])
        else:
            raise NotImplementError

    def get_expression(self, expr: Union[lark.tree.Tree, lark.lexer.Token, Number, str],
                       dont_compute: bool = False) \
            -> Union[int, float, bool, None, str, type(lambda x, y: x + y)]:
        """
        获取表达式的值
        :param expr: 表达式树
        :param context: 上下文,默认为None.如果传入上下文，那么按照上下文计算表达式的值
        :return: 数字，字符串或者函数
        """
        if isinstance(expr, lark.lexer.Token):
            """
            如果是终结符
            有以下几种终结符表达式：
            * parentheses(不处理)
            * FLOAT(语法制导处理)
            * INT(语法制导处理)
            * STR(语法制导处理)
            * "none"(语法制导处理)
            * "true"(语法制导处理)
            * "false"(语法制导处理)
            """
            if expr.type == "STR" or expr.type == 'none' or \
                    expr.type == "true" or expr.type == "false" or \
                    expr.type == "SIGNED_INT" or expr.type == "SIGNED_FLOAT":
                # 如果是一些常量，直接返回
                return expr
            elif expr.type == "NAME":
                _context = self.context.names
                if (var := _context.get(expr)) is not None:
                    return var
                else:
                    raise SamoyedNameError("No such variable")
            else:
                raise SamoyedInterpretError(expr.type, pos=(expr.line, expr.column))
        elif isinstance(expr, Number) or isinstance(expr, str) or expr is None:
            return expr
        elif isinstance(expr, lark.tree.Tree):
            """
            如果是非终结符
            有以下几种非终结符表达式：
            * conditional_expr: 三目表达式。
            * or_test: 子句之间做逻辑或运算
            * and_test: 子句之间做逻辑与运算
            * not_test: 子句之间做逻辑非运算
            * compare_expr: 两个子句之间根据逻辑运算符做比较。
            * plus_expr: 子句之间根据加减符号运算
            * mul_expr： 子句之间根据乘除等符号做运算
            * factor：正负号
            * NAME：从符号表中取变量
            * funccall：从符号表中取变量
            """
            if expr.data == 'add_op' or expr.data == "mul_op":
                return self.arith_operator[expr.children[0]]
            elif expr.data == "conditional_expr":
                """
                conditional_expr : bool_expr?first:second
                bool_expr = expr.children[0]
                """
                bool_expr = self.get_expression(expr.children[0])
                if bool_expr:
                    return self.get_expression(expr.children[1])
                else:
                    return self.get_expression(expr.children[2])
            elif expr.data == "compare_expr":
                """
                compare_expr : left compare_expr right
                compare_operator : expr.children[1].children[0]
                left = expr.children[0]
                right = expr.children[2]
                """
                left = self.get_expression(expr.children[0])
                right = self.get_expression(expr.children[2])
                op = self.compare_operator[expr.children[1].children[0]]

                try:
                    # 两种类型可能不能比较
                    result = op(left, right)
                except Exception:
                    raise
                return result
            elif expr.data == "not_test":
                """
                not_test : "not" test_expr
                test_expr = expr.children[0]
                """
                return bool(not_(self.get_expression(expr.children[0])))
            elif expr.data == "or_test":
                """
                or_test : expr1 "or" expr2 "or" expr3 "or" ....
                expr1 = expr.children[0]
                expr2 = expr.children[1]
                ...
                """
                return bool(reduce(or_, [self.get_expression(i) for i in expr.children]))
            elif expr.data == "and_test":
                """
                and_test : expr1 "and_" expr2 "and_" expr3 "and_" ....
                expr1 = expr.children[0]
                expr2 = expr.children[1]
                ...
                """
                return bool(reduce(and_, [self.get_expression(i) for i in expr.children]))
            elif expr.data == "plus_expr" or expr.data == "mul_expr":
                try:
                    result = self.reduce([self.get_expression(i) for i in expr.children])
                except Exception:
                    raise
                return result
            elif expr.data == "factor":
                tmp = self.get_expression(expr.children[1])
                if expr.children[0] == '-':
                    if isinstance(tmp, str):
                        raise SamoyedTypeError
                    return -tmp
                else:
                    return tmp
            elif expr.data == "funccall":
                """
                函数调用
                """
                _context = self.context.names
                if (func := _context.get(expr.children[0], None)) is not None and callable(func):
                    if expr.children[1] is not None:
                        # 如果有参数
                        return func(*[self.get_expression(i) for i in expr.children[1].children])
                    else:
                        return func()
                else:
                    raise SamoyedNameError("No such function")
            else:
                raise NotImplementError
        else:
            raise NotImplementError

    @staticmethod
    def reduce(l: list):
        """
        计算形如数值、函数混合列表的值
        :param l:
        :return:
        """
        if not l: return None
        sum = l[0]
        n = len(l)
        if n % 2 == 0: raise InterruptedError("列表个数不为奇数")
        try:
            for i in range(1, n, 2):
                """
                从1开始，步长为2，每次应该都要取到函数
                """
                op = l[i]
                operand2 = l[i + 1]
                sum = op(sum, operand2)
        except TypeError:
            # 出现字符串加数字等类型错误
            raise SamoyedTypeError("{}和{}无法做{}运算", type(sum), type(operand2), op)
        except Exception as e:
            raise SamoyedRuntimeError(e.__str__())
        return sum

    compare_operator = {
        ">": gt,
        "<": lt,
        ">=": ge,
        "<=": le,
        "==": eq,
        "!=": ne,
    }
    arith_operator = {
        "+": mock_add,
        "-": sub,
        "*": mul,
        "/": truediv,
        "//": floordiv,
        "%": mod
    }
