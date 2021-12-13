"""
解释器测试
"""
import unittest
from functools import partial
from operator import add, mul, sub, truediv, mod
from queue import Queue
from threading import Thread
from typing import Callable

from lark import Tree

from samoyed.core import Interpreter, Context, mock_add
from samoyed.exception import *
from test.libs_test import mock_input


class InterpreterTest(unittest.TestCase):
    def test_reduce(self):
        """
        测试reduce函数是否正确
        :return:
        """
        self.assertEqual(1 + 2 + 3 + 4, Interpreter.reduce([1, add, 2, add, 3, add, 4]))
        self.assertEqual(1 + 2 - 3 + 4, Interpreter.reduce([1, add, 2, sub, 3, add, 4]))
        self.assertEqual(1 * 10 // 5, Interpreter.reduce([1, mul, 10, truediv, 5]))
        self.assertEqual(1 * 2 % 5, Interpreter.reduce([1, mul, 2, mod, 5]))
        self.assertEqual("hello " + "world" + "!", Interpreter.reduce(["hello ", add, "world", add, "!"]))
        self.assertEqual("asdasd1", Interpreter.reduce(["asdasd", mock_add, 1]))
        with self.assertRaises(SamoyedException):
            Interpreter.reduce(["adssad", mul, "asdasd"])
        with self.assertRaises(SamoyedException):
            Interpreter.reduce([1, truediv, 0])

    def test_get_expr(self):
        """
        测试计算表达式是否正确
        """
        # 哑解释器不需要内容，只需要计算即可
        dumb_interpreter = Interpreter("\n", dont_init=True)
        context = Context()
        dumb_interpreter.context = context
        # 测试常量
        self.assertEqual(3, dumb_interpreter.get_expression(3))
        self.assertEqual(3.14, dumb_interpreter.get_expression(3.14))
        self.assertEqual("hello", dumb_interpreter.get_expression("hello"))
        self.assertEqual(True, dumb_interpreter.get_expression(True))
        self.assertEqual(False, dumb_interpreter.get_expression(False))
        self.assertEqual(None, dumb_interpreter.get_expression(None))

        # 测试变量
        context.names = {'x': 1}
        self.assertEqual(1, dumb_interpreter.get_expression(Token('NAME', 'x')))

        # 测试函数
        # 返回1的过程
        func1 = Tree('funccall', [Token('NAME', 'hello'), None])
        context.names = {"hello": lambda: 1}
        self.assertEqual(1, dumb_interpreter.get_expression(func1))
        # 返回x+1的函数
        func2 = Tree('funccall', [Token('NAME', 'hello'), Tree(Token('RULE', 'parameters'), [1])])
        context.names = {"hello": lambda x: x + 1}
        self.assertEqual(2, dumb_interpreter.get_expression(func2))
        # 返回x+y的函数
        func3 = Tree('funccall', [Token('NAME', 'hello'), Tree(Token('RULE', 'parameters'), [1, 2])])
        context.names = {"hello": lambda x, y: x + y}
        self.assertEqual(3, dumb_interpreter.get_expression(func3))

        # 测试factor
        factor1 = Tree(Token('RULE', 'factor'), [Token('MINUS', '-'), Token('NAME', 'x')])
        context.names = {"x": 1}
        self.assertEqual(-1, dumb_interpreter.get_expression(factor1))
        factor2 = Tree(Token('RULE', 'factor'), [Token('MINUS', '-'), 1])
        self.assertEqual(-1, dumb_interpreter.get_expression(factor2))
        factor3 = Tree(Token('RULE', 'factor'), [Token('MINUS', '-'), 0])
        self.assertEqual(0, dumb_interpreter.get_expression(factor3))
        with self.assertRaises(SamoyedException):
            factor = Tree(Token('RULE', 'factor'), [Token('MINUS', '-'), "asddsa"])
            dumb_interpreter.get_expression(factor)

        # 测试plus_expr表达式
        plus = Tree(Token('RULE', 'plus_expr'), [1, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 1])
        self.assertEqual(1 + 1, dumb_interpreter.get_expression(plus))
        # 支持和字符串拼接，虽然看起来会很怪异
        plus = Tree(Token('RULE', 'plus_expr'), [1, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 1,
                                                 Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), "asd"], )
        self.assertEqual("2asd", dumb_interpreter.get_expression(plus))
        plus = Tree(Token('RULE', 'plus_expr'), ["hello", Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 3.4,
                                                 Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), "asd"], )
        self.assertEqual("hello3.4asd", dumb_interpreter.get_expression(plus))

        # 测试变量加法
        context.names = {"x": 1}
        plus = Tree(Token('RULE', 'plus_expr'), [Token('NAME', 'x'),
                                                 Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), "world"], )
        self.assertEqual("1world", dumb_interpreter.get_expression(plus))
        context.names = {"x": "hello"}
        plus = Tree(Token('RULE', 'plus_expr'), [Token('NAME', 'x'),
                                                 Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), "world"], )
        self.assertEqual("helloworld", dumb_interpreter.get_expression(plus))

        # 测试mul_expr
        mul = Tree(Token('RULE', 'mul_expr'), [1, Tree(Token('RULE', 'mul_op'), [Token('STAR', '*')]), 1])
        self.assertEqual(1, dumb_interpreter.get_expression(mul))
        mul = Tree(Token('RULE', 'mul_expr'), [1, Tree(Token('RULE', 'mul_op'), [Token('SLASH', '/')]), 5])
        self.assertEqual(0.2, dumb_interpreter.get_expression(mul))

        # 测试四则运算
        # 3.14*(6+2)*3
        complex_arith = Tree(Token('RULE', 'mul_expr'), [3.14, Tree(Token('RULE', 'mul_op'), [Token('STAR', '*')]),
                                                         Tree(Token('RULE', 'plus_expr'),
                                                              [6, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]),
                                                               2]), Tree(Token('RULE', 'mul_op'), [Token('STAR', '*')]),
                                                         3])
        self.assertEqual(3.14 * (6 + 2) * 3, dumb_interpreter.get_expression(complex_arith))
        # (3.14 + "hello")*2 => 3.14hello3.14hello
        complex_arith2 = Tree(Token('RULE', 'mul_expr'), [
            Tree(Token('RULE', 'plus_expr'), [3.14, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 'hello']),
            Tree(Token('RULE', 'mul_op'), [Token('STAR', '*')]), 2])
        self.assertEqual("3.14hello3.14hello", dumb_interpreter.get_expression(complex_arith2))

        # 测试compare
        # 1 > 2
        cmp1 = Tree(Token('RULE', 'compare_expr'), [1, Tree(Token('RULE', 'comp_op'), [Token('MORETHAN', '>')]), 2])
        self.assertEqual(False, dumb_interpreter.get_expression(cmp1))
        # 1 >= 1
        cmp2 = Tree(Token('RULE', 'compare_expr'), [1, Tree(Token('RULE', 'comp_op'), [Token('__ANON_2', '>=')]), 1])
        self.assertEqual(True, dumb_interpreter.get_expression(cmp2))

        # "hello" > "world"
        cmp3 = Tree(Token('RULE', 'compare_expr'),
                    ["hello", Tree(Token('RULE', 'comp_op'), [Token('MORETHAN', '>')]), "world"])
        self.assertEqual("hello" > "world", dumb_interpreter.get_expression(cmp3))

        # 测试not,or,and
        nott = Tree('not_test', [Token('NAME', 'good')])
        context.names = {"good": False}
        self.assertEqual(True, dumb_interpreter.get_expression(nott))

        # 1 or 2+3 or 0
        orr = Tree(Token('RULE', 'or_test'),
                   [1, Tree(Token('RULE', 'plus_expr'), [2, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 3]),
                    0])
        self.assertEqual(1 or 2 + 3 or 0, dumb_interpreter.get_expression(orr))

        # True and False or True and True
        andd = Tree(Token('RULE', 'or_test'),
                    [Tree(Token('RULE', 'and_test'), [True, False]), Tree(Token('RULE', 'and_test'), [True, True])])
        self.assertEqual(True and False or True and True, dumb_interpreter.get_expression(andd))

        # 三目运算符
        # true?1+2:2+3
        three1 = Tree(Token('RULE', 'conditional_expr'), [True, Tree(Token('RULE', 'plus_expr'), [1, Tree(
            Token('RULE', 'add_op'), [Token('PLUS', '+')]), 2]), Tree(Token('RULE', 'plus_expr'), [2, Tree(
            Token('RULE', 'add_op'), [Token('PLUS', '+')]), 3])])
        self.assertEqual(3, dumb_interpreter.get_expression(three1))

        three2 = Tree(Token('RULE', 'conditional_expr'), [False, Tree(Token('RULE', 'plus_expr'), [1, Tree(
            Token('RULE', 'add_op'), [Token('PLUS', '+')]), 2]), Tree(Token('RULE', 'plus_expr'), [2, Tree(
            Token('RULE', 'add_op'), [Token('PLUS', '+')]), 3])])
        self.assertEqual(5, dumb_interpreter.get_expression(three2))

    def test_stmt(self):
        """
        测试语句的执行
        """
        dumb_interpreter = Interpreter("\n", dont_init=True)
        context = Context()
        dumb_interpreter.context = context
        dumb_interpreter.stage = dict()

        # 测试赋值
        assign_stmt = Tree(Token('RULE', 'simple_stmt'), [Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'y'), Tree(
            Token('RULE', 'assign_op'), [Token('EQUAL', '=')]), 1])])
        dumb_interpreter.exec_statement(assign_stmt)
        self.assertEqual(context.names["y"], 1)

        with self.assertRaises(SamoyedException):
            assign_stmt = Tree(Token('RULE', 'simple_stmt'),
                               [Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'y'), Tree(
                                   Token('RULE', 'assign_op'), [Token('EQUAL', '=')]), Token('NAME', 'x')])])
            dumb_interpreter.exec_statement(assign_stmt)

        # 测试分支语句
        class MockStage():
            pass

        dumb_interpreter.stage["y"] = MockStage()
        branch_stmt = Tree(Token('RULE', 'simple_stmt'), [Tree(Token('RULE', 'branch_expr'), [Token('NAME', 'y')])])
        dumb_interpreter.exec_statement(branch_stmt)
        self.assertEqual(dumb_interpreter.stage["y"], dumb_interpreter.context.next)

        # 测试if语句
        """
if true:
    x = x + 1
else:
    x = 0
        """
        context.names["x"] = 3
        s = Tree(Token('RULE', 'if_stmt'), [True, Tree(Token('RULE', 'if_true_stmt'), [
            Tree(Token('RULE', 'simple_stmt'), [Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'x'),
                                                                                    Tree(Token('RULE', 'assign_op'),
                                                                                         [Token('EQUAL', '=')]),
                                                                                    Tree(Token('RULE', 'plus_expr'),
                                                                                         [Token('NAME', 'x'),
                                                                                          Tree(Token('RULE', 'add_op'),
                                                                                               [Token('PLUS', '+')]),
                                                                                          1])])])]),
                                            Tree(Token('RULE', 'else_true_stmt'), [Tree(Token('RULE', 'simple_stmt'), [
                                                Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'x'),
                                                                                    Tree(Token('RULE', 'assign_op'),
                                                                                         [Token('EQUAL', '=')]),
                                                                                    0])])])])
        dumb_interpreter.exec_statement(s)
        self.assertEqual(4, context.names["x"])
        s2 = Tree(Token('RULE', 'if_stmt'), [False, Tree(Token('RULE', 'if_true_stmt'), [
            Tree(Token('RULE', 'simple_stmt'), [Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'x'),
                                                                                    Tree(Token('RULE', 'assign_op'),
                                                                                         [Token('EQUAL', '=')]),
                                                                                    Tree(Token('RULE', 'plus_expr'),
                                                                                         [Token('NAME', 'x'),
                                                                                          Tree(Token('RULE', 'add_op'),
                                                                                               [Token('PLUS', '+')]),
                                                                                          1])])])]),
                                            Tree(Token('RULE', 'else_true_stmt'), [Tree(Token('RULE', 'simple_stmt'), [
                                                Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'x'),
                                                                                    Tree(Token('RULE', 'assign_op'),
                                                                                         [Token('EQUAL', '=')]),
                                                                                    0])])])])
        dumb_interpreter.exec_statement(s2)
        self.assertEqual(0, context.names["x"])

        # 测试match
        """
        match x:
            0=>
                y = 2
            1=>
                y = 3
            default =>
                y = 4
        """
        match = Tree(Token('RULE', 'match_stmt'), [Token('NAME', 'x'), Tree(Token('RULE', 'case_stmt'), [0, Tree(
            Token('RULE', 'simple_stmt'), [Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'y'),
                                                                               Tree(Token('RULE', 'assign_op'),
                                                                                    [Token('EQUAL', '=')]), 2])])]),
                                                   Tree(Token('RULE', 'case_stmt'),
                                                        [1, Tree(Token('RULE', 'simple_stmt'), [
                                                            Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'y'),
                                                                                                Tree(Token('RULE',
                                                                                                           'assign_op'),
                                                                                                     [Token('EQUAL',
                                                                                                            '=')]),
                                                                                                3])])]),
                                                   Tree(Token('RULE', 'default_stmt'),
                                                        [Tree(Token('RULE', 'simple_stmt'), [
                                                            Tree(Token('RULE', 'assign_expr'), [Token('NAME', 'y'),
                                                                                                Tree(Token('RULE',
                                                                                                           'assign_op'),
                                                                                                     [Token('EQUAL',
                                                                                                            '=')]),
                                                                                                4])])])])
        # 执行x=0子句
        context.names["x"] = 0
        dumb_interpreter.exec_statement(match)
        self.assertEqual(2, context.names["y"])

        # 执行default
        context.names["x"] = "asddsa"
        dumb_interpreter.exec_statement(match)
        self.assertEqual(4, context.names["y"])

    def test_timecontrol_match(self):
        """
        测试带时间控制的match语句
        :return:
        """
        # 建立哑解释器
        dumb_interpreter = Interpreter("\n", dont_init=True)
        context = Context()
        dumb_interpreter.context = context
        # 重新绑定input函数
        # listen将从一个队列中取值
        q = Queue()
        input_end: Callable[[dict], None] = partial(mock_input, q)
        output_end: Callable[[], str] = partial(lambda qq: qq.get(), q)
        context.names["listen"] = output_end

        # 输入一个简单的语句
        """
        match @(2)listen():
            "投诉" =>
                s="投诉"
            "账单" =>
                s="账单"
            slience =>
                s="沉默"
        """
        print("[简单匹配测试]", end=" ")
        match_stmt = Tree(Token('RULE', 'match_stmt'), [Tree(Token('RULE', 'at_expr'),
                                                             [Tree(Token('RULE', 'at_expr_parameter'), [2]),
                                                              Token('NAME', 'listen'), None]),
                                                        Tree(Token('RULE', 'case_stmt'),
                                                             ['投诉', Tree(
                                                                 Token('RULE', 'simple_stmt'),
                                                                 [Tree(Token('RULE',
                                                                             'assign_expr'),
                                                                       [Token('NAME', 's'),
                                                                        Tree(Token('RULE',
                                                                                   'assign_op'),
                                                                             [Token('EQUAL',
                                                                                    '=')]),
                                                                        '投诉'])])]),
                                                        Tree(Token('RULE', 'case_stmt'),
                                                             ['账单', Tree(Token('RULE', 'simple_stmt'), [
                                                                 Tree(Token('RULE', 'assign_expr'), [Token('NAME', 's'),
                                                                                                     Tree(Token('RULE',
                                                                                                                'assign_op'),
                                                                                                          [Token(
                                                                                                              'EQUAL',
                                                                                                              '=')]),
                                                                                                     '账单'])])]),
                                                        Tree(Token('RULE', 'slience_stmt'),
                                                             [Tree(Token('RULE', 'simple_stmt'), [
                                                                 Tree(Token('RULE', 'assign_expr'), [Token('NAME', 's'),
                                                                                                     Tree(Token('RULE',
                                                                                                                'assign_op'),
                                                                                                          [Token(
                                                                                                              'EQUAL',
                                                                                                              '=')]),
                                                                                                     '沉默'])])])])

        # 设定初始值
        context.names["s"] = ""
        plan = {0: "投诉"}

        # 进程用来提供input输入
        process = Thread(target=input_end, args=(plan,))
        process.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("投诉", context.names["s"])
        process.join()
        print("pass")

        # 排空队列
        while not q.empty(): q.get()

        ############
        #  超时测试 #
        ###########
        print("[超时测试]", end=" ")
        # 设定初始值
        context.names["s"] = ""
        plan = {2.2: "投诉"}  # 超时时间为2s，这个应该要超时。

        # 进程用来提供input输入
        process = Thread(target=input_end, args=(plan,))
        process.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("沉默", context.names["s"])
        process.join()
        print("pass")

        # 排空队列
        while not q.empty(): q.get()

        ###############
        #  多次输入测试 #
        ###############
        print("[多次输入测试]", end=" ")
        # 设定初始值
        context.names["s"] = ""
        plan = {0: "emmm..", 0.5: "我要", 1: "对你们", 1.9: "投诉"}
        # 进程用来提供input输入
        thread = Thread(target=input_end, args=(plan,))
        # process = Process(target=input_end, args=(plan,))
        # process.start()
        thread.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("投诉", context.names["s"])
        thread.join()
        print("pass")

        ######################
        #  多次输入但是没有匹配 #
        ######################
        # 排空队列
        while not q.empty(): q.get()
        print("[多次输入但是没有匹配]", end=" ")
        # 设定初始值
        context.names["s"] = ""
        plan = {0: "emmm..", 0.5: "我要", 1: "对你们", 1.9: "进行"}
        # 进程用来提供input输入
        thread = Thread(target=input_end, args=(plan,))
        thread.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("沉默", context.names["s"])
        thread.join()
        print("pass")

        ##############
        # 最短时间限制 #
        ##############

        match_stmt = Tree(Token('RULE', 'match_stmt'), [Tree(Token('RULE', 'at_expr'),
                                                             [Tree(Token('RULE', 'at_expr_parameter'), [4, 2]),
                                                              Token('NAME', 'listen'), None]),
                                                        Tree(Token('RULE', 'case_stmt'),
                                                             ['投诉', Tree(
                                                                 Token('RULE', 'simple_stmt'),
                                                                 [Tree(Token('RULE',
                                                                             'assign_expr'),
                                                                       [Token('NAME', 's'),
                                                                        Tree(Token('RULE',
                                                                                   'assign_op'),
                                                                             [Token('EQUAL',
                                                                                    '=')]),
                                                                        '投诉'])])]),
                                                        Tree(Token('RULE', 'case_stmt'),
                                                             ['账单', Tree(Token('RULE', 'simple_stmt'), [
                                                                 Tree(Token('RULE', 'assign_expr'), [Token('NAME', 's'),
                                                                                                     Tree(Token('RULE',
                                                                                                                'assign_op'),
                                                                                                          [Token(
                                                                                                              'EQUAL',
                                                                                                              '=')]),
                                                                                                     '账单'])])]),
                                                        Tree(Token('RULE', 'slience_stmt'),
                                                             [Tree(Token('RULE', 'simple_stmt'), [
                                                                 Tree(Token('RULE', 'assign_expr'), [Token('NAME', 's'),
                                                                                                     Tree(Token('RULE',
                                                                                                                'assign_op'),
                                                                                                          [Token(
                                                                                                              'EQUAL',
                                                                                                              '=')]),
                                                                                                     '沉默'])])])])
        # 排空队列
        while not q.empty(): q.get()
        print("[最短时间限制]", end=" ")
        # 设定初始值
        context.names["s"] = ""
        plan = {0: "投诉"}
        # 进程用来提供input输入
        thread = Thread(target=input_end, args=(plan,))
        thread.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("投诉", context.names["s"])
        thread.join()
        print("pass")

    def test_reg_match(self):
        """
        测试带正则表达式的匹配
        """
        # 建立哑解释器
        dumb_interpreter = Interpreter("\n", dont_init=True)
        context = Context()
        dumb_interpreter.context = context
        # 重新绑定input函数
        # listen将从一个队列中取值
        q = Queue()
        input_end: Callable[[dict], None] = partial(mock_input, q)
        output_end: Callable[[], str] = partial(lambda qq: qq.get(), q)
        context.names["listen"] = output_end

        match_stmt = Tree(Token('RULE', 'match_stmt'), [Tree(Token('RULE', 'at_expr'),
                                                             [Tree(Token('RULE', 'at_expr_parameter'), [2]),
                                                              Token('NAME', 'listen'), None]),
                                                        Tree(Token('RULE', 'case_stmt'),
                                                             [Tree(Token('RULE', 'reg'),
                                                                   [Token('__ANON_8', '.*投诉(.*)')]),
                                                              Tree(Token('RULE', 'simple_stmt'), [
                                                                  Tree(Token('RULE', 'assign_expr'),
                                                                       [Token('NAME', 's'),
                                                                        Tree(Token('RULE', 'assign_op'),
                                                                             [Token('EQUAL', '=')]), '投诉'])])]),
                                                        Tree(Token('RULE', 'case_stmt'), ['账单', Tree(
                                                            Token('RULE', 'simple_stmt'), [
                                                                Tree(Token('RULE', 'assign_expr'), [Token('NAME', 's'),
                                                                                                    Tree(Token('RULE',
                                                                                                               'assign_op'),
                                                                                                         [Token('EQUAL',
                                                                                                                '=')]),
                                                                                                    '账单'])])]),
                                                        Tree(Token('RULE', 'slience_stmt'), [
                                                            Tree(Token('RULE', 'simple_stmt'), [
                                                                Tree(Token('RULE', 'assign_expr'), [Token('NAME', 's'),
                                                                                                    Tree(Token('RULE',
                                                                                                               'assign_op'),
                                                                                                         [Token('EQUAL',
                                                                                                                '=')]),
                                                                                                    '沉默'])])])])
        #######################
        # 测试带正则表达式匹配失败#
        #######################
        print("[测试带正则表达式匹配失败]", end=" ")
        # 设定初始值
        context.names["s"] = ""
        plan = {0: "我要投", 2.1: "投诉AA"}  # 只匹配 投诉.*
        # 进程用来提供input输入
        thread = Thread(target=input_end, args=(plan,))
        thread.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("沉默", context.names["s"])
        thread.join()
        print("pass")

        #######################
        # 测试带正则表达式匹配成功#
        #######################
        print("[测试带正则表达式匹配成功]", end=" ")
        while not q.empty(): q.get()
        context.names["s"] = ""
        plan = {0: "我要投", 1.6: "投诉AA"}  # 只匹配 投诉.*
        # 进程用来提供input输入
        thread = Thread(target=input_end, args=(plan,))
        thread.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("投诉", context.names["s"])
        thread.join()
        print("pass")

        #######################
        # 测试带正则表达式匹配成功2#
        #######################
        print("[测试带正则表达式匹配成功2]", end=" ")
        while not q.empty(): q.get()
        context.names["s"] = ""
        plan = {0: "我要投", 1.6: "账单"}
        # 进程用来提供input输入
        thread = Thread(target=input_end, args=(plan,))
        thread.start()
        # 执行语句
        dumb_interpreter.exec_statement(match_stmt)
        self.assertEqual("账单", context.names["s"])
        thread.join()
        print("pass")


if __name__ == "__main__":
    unittest.main()
