"""
解释器测试
"""
import unittest
from operator import add, mul, sub, truediv, mod

from lark import Token, Tree

from samoyed.core import Interpreter, Context
from samoyed.exception import *


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
        self.assertEqual("asdasd1", Interpreter.reduce(["asdasd", Interpreter.mock_add, 1]))
        with self.assertRaises(SamoyedException):
            Interpreter.reduce(["adssad", mul, "asdasd"])
        with self.assertRaises(SamoyedException):
            Interpreter.reduce([1, truediv, 0])

    def test_get_expr(self):
        """
        测试计算表达式是否正确
        """
        # 哑解释器不需要内容，只需要计算即可
        dumb_interpreter = Interpreter("\n", dont_parse=True)
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
        self.assertEqual(1 or 2+3 or 0, dumb_interpreter.get_expression(orr))

        # True and False or True and True
        andd = Tree(Token('RULE', 'or_test'), [Tree(Token('RULE', 'and_test'), [True, False]), Tree(Token('RULE', 'and_test'), [True, True])])
        self.assertEqual(True and False or True and True, dumb_interpreter.get_expression(andd))

        # 三目运算符
        # true?1+2:2+3
        three1 = Tree(Token('RULE', 'conditional_expr'), [True, Tree(Token('RULE', 'plus_expr'), [1, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 2]), Tree(Token('RULE', 'plus_expr'), [2, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 3])])
        self.assertEqual(3,dumb_interpreter.get_expression(three1))

        three2 = Tree(Token('RULE', 'conditional_expr'), [False, Tree(Token('RULE', 'plus_expr'), [1, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 2]), Tree(Token('RULE', 'plus_expr'), [2, Tree(Token('RULE', 'add_op'), [Token('PLUS', '+')]), 3])])
        self.assertEqual(5,dumb_interpreter.get_expression(three2))

if __name__ == "__main__":
    unittest.main()
