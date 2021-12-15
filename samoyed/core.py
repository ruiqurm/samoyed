import os
import re
import sqlite3
from functools import partial
from functools import reduce
from numbers import Number
from operator import lt, le, eq, ne, ge, gt, not_, or_, and_ \
    , sub, mul, mod, truediv, floordiv
from typing import Union, Dict
import sys

import lark
from lark import Lark, Transformer
from lark.exceptions import UnexpectedToken, UnexpectedEOF
from lark.indenter import Indenter

from .exception import *
from .libs import TimeControl, arg_seq_add, arg_option_add, mock_add, sqlite, sqlite_connect

"""
解释器核心
"""


class SamoyedIndenter(Indenter):
    """
    间隔控制
    会将若干空格转换_INDENT终结符
    如果空格数量不同，转换出的_INDENT也会不同
    """
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4  # 制表符转换出4个空格的_INDENT


class SamoyedTransformer(Transformer):
    """
    基础的语法制导，只会转换一些常量。
    """
    none = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False

    def __init__(self):
        super().__init__()
        self.dollar = set()  # type: set[str]

    def FLOAT(self, value: lark.Token) -> float:
        return float(value)

    def INT(self, value: lark.Token) -> int:
        return int(value)

    def STR(self, value: lark.Token) -> str:
        if len(value) > 3 and value[1] == value[2] == "\"":
            return value[3:-3]
        else:
            return value[1:-1]

    def DOLLAR_VAR(self, value: lark.Token):
        # 只用于追踪dollar变量
        self.dollar.add(value.value)
        return value


class Context:
    """
    上下文
    """

    def __init__(self, names: dict = None, dollar_names: Dict[str, str] = None):
        """
        Notes
        ---------
            绑定内置函数，变量，外部传入的参数到内部的参数表中。
            对于外部传入的dollar_names，如果有包含名字叫mg的方法会被过滤掉

        Parameters
        ----------
        names
            外部传入的变量表
        dollar_names
            传入的参数
        """
        self.names = dict(names) if names is not None else dict()
        self.seq_args = []
        self.option_args = []

        self.names["$PWD"] = os.getcwd()
        # 给外部传入的属性加上$
        if dollar_names is not None:
            for key in dollar_names:
                if key.startswith("mg"): continue
                self.names["$" + key] = dollar_names[key]

        # 绑定内置函数
        self.conn2curosr = {}  # type:Dict[sqlite3.Cursor,sqlite3.Connection]
        self.names["print"] = sys.stderr.write
        self.names["speak"] = print
        self.names["listen"] = input
        self.names["exit"] = sys.exit
        self.names["arg_seq_add"] = partial(arg_seq_add, self.seq_args)
        self.names["arg_option_add"] = partial(arg_option_add, self.option_args)
        self.names["sqlite_connect"] = partial(sqlite_connect, self.conn2curosr)
        self.names["sqlite"] = partial(sqlite, self.conn2curosr)
        self.names["eval"] = lambda str: eval(str, self.names)

        # 状态初始化
        self.stage = None  # type:lark.tree.Tree
        self.next = None  # type:lark.tree.Tree
        self.__exit = False

    def is_exit(self) -> bool:
        """判断当前程序是否已经退出
        Returns
        -------
        bool
            当前程序是否已经退出
        """
        return self.__exit

    def set_exit(self) -> None:
        """设置当前程序退出

        """
        self.__exit = True


class Interpreter:
    """解释器类
    """

    # 语法制导。用于构件AST时转换一些常量
    # 因为每次语法制导
    transformer = SamoyedTransformer()

    # 读取文法
    with open("{}/samoyed.gram".format(os.path.abspath(os.path.dirname(__file__)))) as f:
        parser = Lark(f.read(), parser='lalr', postlex=SamoyedIndenter(), transformer=transformer)

    def __init__(self, code: Union[str, lark.Tree], context: dict = None, args: dict = None, dont_init=False):
        """
        Parameters
        ----------
        code: Union[str, lark.Tree]
            代码
        context:dict
            额外的上下文
        args:dict
            命令行等特殊参数
        dont_init:bool
            是否执行初始化
        """
        self.__isinit = False
        self.transformer.dollar.clear()

        # 词法和语法分析
        if isinstance(code, str):
            # 如果传入的是代码
            try:
                self.ast = self.parser.parse(code)  # type:lark.tree.Tree
                # 提取出扫描到的dollar符号
                self.dollar_symbol = self.transformer.dollar.copy()
            except (UnexpectedEOF, UnexpectedToken) as e:
                raise SamoyedSyntaxError(e.expected, e.token, pos=(e.line, e.column))
        else:
            # 否则直接绑定
            self.ast = code

        # 建立上下文
        self.context = Context(names=context, dollar_names=args)

        # 初始化会执行所有外部的语句。
        if not dont_init:
            self.init()

    def init(self) -> None:
        """执行所有外部的语句
        外部的语句指下面这种情况：
        x = 1
        state main:
            pass
        这里x=1就是外部的语句
        """
        self.stage = dict()
        self.entrance = None
        # 遍历AST的顶层，确定所有的stage和入口
        for node in self.ast.children:
            if node.data == 'statedef':
                # 如果是状态定义
                name = node.children[0]  # 第一个子节点是名称
                # 如果是入口，绑定入口点
                if name == "main":
                    self.entrance = self.stage[name] = node
                else:
                    self.stage[name] = node
            else:
                # 如果不是状态，那么直接执行
                self.exec_statement(node)

        # 如果没有入口，报错
        if self.entrance is None:
            raise SamoyedNotFoundEntrance

        self.context.stage = self.entrance
        self.__isinit = True

    def exec(self) -> None:
        """解释执行程序

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
                # 如果指定了状态跳到该状态
                self.context.stage = self.context.next
                self.context.next = None

    def exec_statement(self, stat: lark.tree.Tree) -> None:
        """执行每一个语句
        可执行的语句有以下几种：
        * simple_stmt 简单的语句，包括赋值表达式，跳转表达式，pass表达式和普通表达式
        * if_stmt if语句
        * match_stmt 包括普通的match和可以控制输入时间的match

        Parameters
        ----------
        stat
            语句的语法分析结果

        Raises
        -------
            `SamoyedRuntimeError`:
                其他运行错误
            `SamoyedTypeError`:
                类型错误
        """
        if stat.data == "simple_stmt":
            """
            如果是一个简单的表达式
            simple_stmt包括：
            * pass_expr 什么也不做.
            * branch_expr 跳转表达式
            * _full_expr 一个普通表达式，如果这个表达式非过程，那么它是无副作用的
            * assign_expr 赋值表达式
            
            对于simple_stmt，其语法分析的结果类似下面的结构：
            simple_stmt
                |
               expr 
                |
               ...
            通过判断children[0]的类型，即可知道它是什么表达式
            """
            simple_stmt = stat.children[0]
            # 如果是终结符，那么不需要再处理了
            if not isinstance(simple_stmt,lark.Tree):return

            simple_stmt_type = simple_stmt.data
            if simple_stmt_type == "branch_expr":
                """
                是一个跳转语句
                branch_expr
                    |
                   node(NAME)
                NAME即要跳转到的状态名
                """
                next_state = simple_stmt.children[0]
                if next_state in self.stage:
                    self.context.next = self.stage[next_state]
                else:
                    raise SamoyedNameError

            elif simple_stmt_type == "assign_expr":
                """
                是一个赋值语句
                assign_expr
                    |
                ┌───┬─────┐
                var =    expr
                simple_stmt.children[0].value -> var
                simple_stmt.children[2]       -> expr
                """
                self.context.names[simple_stmt.children[0].value] = self.get_expression(simple_stmt.children[2])
            elif simple_stmt_type == "pass_expr":
                """
                是跳过语句
                """
                return
            else:
                """
                是一个普通的表达式
                直接执行即可
                """
                self.get_expression(stat.children[0])
        elif stat.data == "match_stmt":
            """
            match字句有两种形式
            第一种形式是**带有时间控制**的匹配
            其中，@的第一个参数是超时时间，必选；第二个参数是最少持续时间，可选；
            @后应该接入一个函数调用。延时表达式会不断调用这个函数
            ```
            match @(10,2)funcall :
                compare_expr =>
                    stat
                ...
                silence =>
                    stat
            ```        
            第二种形式是普通的多值匹配
            ```
            match expr :
                compare_expr =>
                    stat
                compare_expr =>
                    stat
                default =>
                    stat
            ```
            """
            expr = stat.children[0]  # expr
            if isinstance(expr, lark.tree.Tree) and expr.data == "at_expr":
                self.__time_control_match(stat)
            else:
                self.__normal_match(stat)
        elif stat.data == "if_stmt":
            """
            如果是if语句
                 if_stmt
                    |
            ┌───────┬─────────┐
            expr  true_st false_st
            """
            bool_expr = bool(self.get_expression(stat.children[0]))
            if bool_expr:
                for stmt in stat.children[1].children:
                    self.exec_statement(stmt)
                    if self.context.next is not None:
                        return
            elif len(stat.children) == 3:
                for stmt in stat.children[2].children:
                    self.exec_statement(stmt)
                    if self.context.next is not None:
                        return
        else:
            raise SamoyedNotImplementError

    def get_expression(self, expr: Union[lark.tree.Tree, lark.lexer.Token, Number, str]) \
            -> Union[int, float, bool, None, str, type(lambda x, y: x + y)]:
        """获取表达式的值

        Parameters
        ----------
        expr 表达式树

        Returns
        -------
            表达式运算后的结果。可能是常量，也可能是一个函数

        Raises
        -------
            `SamoyedRuntimeError`:
                其他运行错误
            `SamoyedTypeError`:
                类型错误
        """


        if isinstance(expr, lark.lexer.Token):
            """
            如果是终结符....
            
            终结符有type和value两个域。
            type是类型，
            value是其值
            
            有以下几种终结符表达式：
            * FLOAT(语法制导处理)
            * INT(语法制导处理)
            * STR(语法制导处理)
            * "none"(语法制导处理)
            * "true"(语法制导处理)
            * "false"(语法制导处理)
            * NAME,DOLLAR_VAR(查表）
            """
            if expr.type == "STR" or expr.type == 'none' or \
                    expr.type == "true" or expr.type == "false" or \
                    expr.type == "SIGNED_INT" or expr.type == "SIGNED_FLOAT":
                # 如果是一些常量，直接返回
                return expr
            elif expr.type == "NAME" or expr.type == "DOLLAR_VAR":
                # 查看是否有该变量
                _context = self.context.names
                if (var := _context.get(expr.value)) is not None:
                    return var
                else:
                    raise SamoyedNameError("No such variable {}".format(expr.value))
            else:
                raise SamoyedInterpretError(expr.type, pos=(expr.line, expr.column))
        elif isinstance(expr, Number) or isinstance(expr, str) or expr is None:
            """
            如果是普通的常量
            直接返回
            """
            return expr
        elif isinstance(expr, lark.tree.Tree):
            """
            如果是非终结符...
            
            非终结符是一棵树
            形式为： (data=....,children=Tree[...])
            
            有以下几种非终结符表达式：
            * conditional_expr: 三目表达式。
            * or_test: 子句之间做逻辑或运算
            * and_test: 子句之间做逻辑与运算
            * not_test: 子句之间做逻辑非运算
            * compare_expr: 两个子句之间根据逻辑运算符做比较。
            * plus_expr: 子句之间根据加减符号运算
            * mul_expr： 子句之间根据乘除等符号做运算
            * factor：正负号
            * funccall：函数调用，从符号表中取变量
            * REG ：正则表达式
            """
            if expr.data == 'add_op' or expr.data == "mul_op":
                return self.arith_operator[expr.children[0]]
            elif expr.data == "conditional_expr":
                """
                如果是条件表达式..
                类似if语句的处理
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
                如果是比较表达式....
                
                compare_expr : left compare_expr right
                compare_operator : expr.children[1].children[0]
                left = expr.children[0] 左边的表达式
                right = expr.children[2] 右边的表达式
                """
                left = self.get_expression(expr.children[0])
                right = self.get_expression(expr.children[2])
                op = self.compare_operator[expr.children[1].children[0]]

                try:
                    # 两种类型可能不能比较
                    result = op(left, right)
                except Exception:
                    raise SamoyedTypeError("can not compare{} and {}".format(type(left),type(right)))
                return result
            elif expr.data == "not_test":
                """
                not表达式
                not_test : "not" test_expr
                test_expr = expr.children[0]
                """
                return bool(not_(self.get_expression(expr.children[0])))
            elif expr.data == "or_test":
                """
                or表达式。
                这里可能有多个参数，因此这里用了reduce
                or_test : expr1 "or" expr2 "or" expr3 "or" ....
                expr1 = expr.children[0]
                expr2 = expr.children[1]
                ...
                """
                return bool(reduce(or_, [self.get_expression(i) for i in expr.children]))
            elif expr.data == "and_test":
                """
                and表达式，同上
                and_test : expr1 "and_" expr2 "and_" expr3 "and_" ....
                expr1 = expr.children[0]
                expr2 = expr.children[1]
                ...
                """
                return bool(reduce(and_, [self.get_expression(i) for i in expr.children]))
            elif expr.data == "plus_expr" or expr.data == "mul_expr":
                """
                加法或乘法
                其结构形如：
                [1,+,2,-,3]或者[1,*,2,//,3]
                因此不能直接用reduce。这里改造了一下reduce
                """
                try:
                    result = self.reduce([self.get_expression(i) for i in expr.children])
                except Exception:
                    raise SamoyedRuntimeError("can not compute {}".format(expr))
                return result
            elif expr.data == "factor":
                """
                加上正负号。
                这里可能操作对象是字符串
                """
                tmp = self.get_expression(expr.children[1])
                if expr.children[0] == '-':
                    if isinstance(tmp, str):
                        raise SamoyedTypeError("can not add '-' to string")
                    return -tmp
                else:
                    return tmp
            elif expr.data == "funccall":
                """
                函数调用
                """
                _context = self.context.names
                if (func := _context.get(expr.children[0], None)) is not None and callable(func):
                    try:
                        if expr.children[1] is not None:
                            # 如果有参数
                            return func(*[self.get_expression(i) for i in expr.children[1].children])
                        else:
                            return func()
                    except Exception as e:
                        # 函数可能会崩溃
                        raise SamoyedRuntimeError(str(e))
                else:
                    raise SamoyedNameError("No such function {}".format(expr.children[0]))
            elif expr.data == "reg":
                """
                如果是正则表达式...
                直接编译后，返回
                """
                return re.compile(expr.children[0].value)
            else:
                raise SamoyedNotImplementError
        else:
            raise SamoyedNotImplementError

    @staticmethod
    def reduce(l: list)->Union[Number,None]:
        """
        计算形如数值、函数混合列表的值
        大致原理是，分为奇数位和偶数位进行计算。
        奇数位都是操作数，偶数为都是操作符。

        Parameters
        ----------
        l:
            操作数和操作符的序列，形如[1,+,2,-,3]

        Returns
        -------
            运算结果
        Raises
        -------
            `SamoyedRuntimeError`:
                其他运行错误
            `SamoyedTypeError`:
                类型错误
        """
        if not l: return None
        sum = l[0]
        n = len(l)
        if n % 2 == 0: raise SamoyedRuntimeError("列表个数不为奇数")
        operand2 = None
        op = None
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
            raise SamoyedTypeError("{}和{}无法做{}运算".format(type(sum), type(operand2), op))
        except Exception as e:
            raise SamoyedRuntimeError(e.__str__())
        return sum

    def _match_value(self, value1: Union[int, float, bool, None, str],
                     value2: Union[int, float, bool, None, str, re.Pattern]) -> Tuple[bool, Union[re.Match, None]]:
        """
        判断节点的值是否匹配
        如果是正则匹配会返回匹配结果
        Parameters
        ----------
        value1
            要匹配的值
        value2
            匹配的值2，可以是正则表达式。判断value1是否满足正则表达式的pattern

        Returns
        -------
            bool 匹配是否成功
            result 匹配结果
        """
        if value1 is None and value2 is None: return True, None
        if value1 is None or value2 is None: return False, None
        if isinstance(value2, re.Pattern):
            """
            如果node是正则表达式
            """
            result = value2.match(value1)
            return result is not None, result
        else:
            """
            否则，先计算出值，直接进行值的比较
            如果两个对象都是字符串，value2只要是value1的子串即可
            """
            if isinstance(value1, str) and isinstance(value2, str):
                return value1.find(value2) != -1, None
            else:
                return value1 == value2, None
    def __normal_match(self,stat)->None:
        """
        如果是简单的switch型match
        语法分析的树大致如下：
            match_stmt
                 |
        ┌──────────────┬────────────┬─────────────┐
        expr0      match_case1  match_case..   default
                       |                          |
                  ┌────┬──────┐                ┌────┐
                expr1 stmt1  ...            stmt1  ...

        match_case1中的expr1如果是字符串，那么其语义是:
        如果expr0中存在子串expr1，则匹配成功（而不需要expr0==expr1)

        match_case1中的expr1如果是正则表达式，则按正则表达式的匹配处理

        其他情况按expr0==expr1处理
        """
        expr = stat.children[0]
        expr_result = self.get_expression(expr)
        for case_statment in stat.children[1:]:  # stat.children[0]是bool表达式
            if case_statment.data == "default_stmt":
                """
                如果是默认情况，直接执行这个语句
                parser解析的结果保证默认情况在最后面
                """
                # 执行块中的每个语句
                for st in case_statment.children:
                    self.exec_statement(st)
                    if self.context.next is not None: break
                break
            else:
                """
                否则，判断值相同才执行
                字符串只要包含子串就会执行                        
                """
                matching_value = self.get_expression(case_statment.children[0])
                is_matched, result = self._match_value(matching_value, expr_result)
                # 如果匹配成功
                # 如果为正则表达式，保存组的结果
                # 跳出循环，结束
                if is_matched:
                    # 执行块中的每个语句
                    for st in case_statment.children[1:]:
                        self.exec_statement(st)

                    if result is not None:
                        self.context.names["$mg0"] = result.group(0)
                        for i, group in enumerate(result.groups()):
                            self.context.names["$mg{}".format(i + 1)] = group
                    break
    def __time_control_match(self,stat)->None:
        """
        如果是限定时间的语句...
        会尝试一直读取值，直到超时或者匹配成功
        语法分析的树大致如下：
            match_stmt
                 |
        ┌─────────────────────────────────┬────────────┬─────────────┐
        expr0                          match_case1  match_case..  silence
        |                                 |                          |
        ┌────────┬─────────┐         ┌────┬──────┐                 ┌────┐
        at_para func    func_para   expr1 stmt1  ...              stmt1  ...

        * match_case1中的expr1如果是字符串，那么其语义是:
            如果expr0中存在子串expr1，则匹配成功（而不需要expr0==expr1)

        * match_case1中的expr1如果是正则表达式，则按正则表达式的匹配处理

        * 其他情况按expr0==expr1处理

        Parameters
        ----------
        stat
            执行的time_control语句

        """
        expr = stat.children[0]
        # 下面首先是获取@()func()的函数
        # expr.children[0] -> @内部的参数，用于控制时间
        # expr.children[1] -> func的函数名
        # expr.children[2] -> func的参数，可能为None
        _context = self.context.names
        if (func := _context.get(expr.children[1], None)) is not None and callable(func):
            if expr.children[2] is not None:
                # 如果有参数
                assert expr.children[2] < expr.children[1]
                func = partial(func, *[self.get_expression(i) for i in expr.children[2].children])
        else:
            raise SamoyedNameError("No such function {}".format(expr.children[1]))

        # 接着构造定时器
        # 构造一个TimeControl对象。将这个函数传入构造
        control = TimeControl(func, *expr.children[0].children)

        # 预先算出每个case的表达式，不包含silence字句
        cases = [self.get_expression(case_statment.children[0]) for case_statment in stat.children[1:] if
                 case_statment.data != "silence_stmt"]

        results = ""  # 每次读取的值
        find_flag = False  # 是否完成匹配
        finded_case = None  # 匹配的是第几个

        """
        开始执行匹配

        允许断断续续地输入，
        每一次新的输入都会更新值并判断结果是否匹配
        """
        for result in control():
            # 如果新的结果不为空，保存
            if result is not None:
                results += result

            # 如果当前时间不允许退出，那么即使匹配了也无法退出
            # 这种情况下，直接跳过即可
            if not control.can_exit.is_set(): continue

            # 依次对每个case进行判断
            for i, case in enumerate(cases):
                # 拼接结果
                concat_result = "".join(results)

                """
                匹配结果:
                会返回一个bool变量和一个匹配结果。
                如果是正则表达式，匹配结果才有效
                匹配结果保存的是分组后的信息
                """
                is_matched, result = self._match_value(concat_result, case)
                if is_matched:
                    find_flag = True
                    finded_case = i
                    control.cancel()

                    # 将正则匹配结果绑定到特殊变量上
                    if result is not None:
                        self.context.names["$mg0"] = result.group(0)
                        for i, group in enumerate(result.groups()):
                            self.context.names["$mg{}".format(i + 1)] = group
                    break

            # 如果匹配，那么执行这个子块，并返回
            if find_flag and control.can_exit.is_set():
                for st in stat.children[finded_case + 1].children[1:]:
                    self.exec_statement(st)
                    if self.context.next is not None:break
                return
        """
        匹配块结束....
        如果超时了，并且没有完成任何匹配...
        """
        # 如果有silence块，执行silence块
        if stat.children[-1].data == "silence_stmt":
            for st in stat.children[-1].children:
                # 执行块中的每个语句
                self.exec_statement(st)
                if self.context.next is not None:break

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
