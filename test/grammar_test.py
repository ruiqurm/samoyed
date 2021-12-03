import unittest
from samoyed.core import Interpreter,SamoyedInterpretError
import lark
class GrammarTest(unittest.TestCase):
    """
    测试文法生成出的树是否正确
    """
    def check_stage(self,node,name:str):
        self.assertEqual(node.data,"statedef")
        node = node.children[0]
        self.assertEqual(node,name)
    def test_stage(self)->None:
        """
        测试生成的状态是否正确
        """
        ###############
        # 一个正确的例子 #
        ###############
        test_code =  \
"""
state hello:
    pass
state aaaaa:
    pass
state main:
    pass
state 中文状态码:
    pass
"""
        i = Interpreter(test_code,dont_parse = True)
        self.assertEqual(len(i.ast.children),4)
        self.check_stage(i.ast.children[0],"hello")
        self.check_stage(i.ast.children[1],"aaaaa")
        self.check_stage(i.ast.children[2],"main")
        self.check_stage(i.ast.children[3],"中文状态码")
        ###############
        #  错误的测试  #
        ###############

        # 缺少冒号：
        test_code = \
"""
state hello
    pass
"""
        with self.assertRaises(SamoyedInterpretError,msg = "缺少冒号未报错"):
            i = Interpreter(test_code, dont_parse=True)

        # state内没有东西
        test_code = \
"""
state hello:
"""
        with self.assertRaises(SamoyedInterpretError, msg="未闭合state不报错"):
            i = Interpreter(test_code, dont_parse=True)

    def test_value(self)->None:
        """
        测试常量和变量：true,false,none,数字，字符串,name
        """
        pass
    def test_simple_stmt(self):
        """
        测试普通语句和赋值语句
        :return:
        """
        test_code = \
"""
state hello:
    x = 1 # 这是注释
    y = 1 * (3 + 4) / 2 or "a" == "b"
    z = not (true or false) * (3 + 4)
    z = not true or false * (3 + 4)  
"""
        i = Interpreter(test_code, dont_parse=True)
        self.assertEqual(len(i.ast.children), 1)
        self.assertEqual(len(i.ast.children[0].children), 5,"少生成了simple_stmt") # hello是第一个元素，所以一共有4个
        # 对于第一个语句：
        stmt = i.ast.children[0].children[1].children[0]
        self.assertEqual(stmt.data,"assign_expr",)
        self.assertEqual(stmt.children[0],"x")
        self.assertEqual(stmt.children[2],1)

        # 对于第二个语句
        stmt = i.ast.children[0].children[2].children[0]
        self.assertEqual(stmt.data, "assign_expr")
        self.assertEqual(stmt.children[0], "y")
        self.assertEqual(stmt.children[2].data, "or_test")
        # 1 * (3 + 4) / 2
        tmp = stmt
        stmt = stmt.children[2].children[0] # 1 , * , (3 + 4) / 2
        self.assertEqual(stmt.data, "mul_expr")
        self.assertEqual(stmt.children[0],1)
        self.assertEqual(stmt.children[2].data,"mul_expr") # (3 + 4) / 2
        self.assertEqual(stmt.children[2].children[0].data,"arith_expr") # 3 + 4
        self.assertEqual(stmt.children[2].children[0].children[0],3) # 3
        self.assertEqual(stmt.children[2].children[0].children[2],4) # 4
        self.assertEqual(stmt.children[2].children[2],2) # 2
        # "a" == "b"
        stmt = tmp
        stmt = stmt.children[2].children[1]
        self.assertEqual(stmt.data, "compare_expr")
        self.assertEqual(stmt.children[0], "a")
        self.assertEqual(stmt.children[2], "b")

        # 对于第三个语句
        # not (true or false) * (3 + 4)
        stmt = i.ast.children[0].children[3].children[0]
        self.assertEqual(stmt.data, "assign_expr")
        self.assertEqual(stmt.children[0], "z")
        self.assertEqual(stmt.children[2].data, "not_test")
        self.assertEqual(stmt.children[2].children[0].data, "mul_expr")
        self.assertEqual(stmt.children[2].children[0].children[0].data,"or_test")
        self.assertEqual(stmt.children[2].children[0].children[0].children[0],True)
        self.assertEqual(stmt.children[2].children[0].children[0].children[1],False)
        self.assertEqual(stmt.children[2].children[0].children[1].data,"mul_op")
        self.assertEqual(stmt.children[2].children[0].children[2].data,"arith_expr")
        self.assertEqual(stmt.children[2].children[0].children[2].children[0],3)
        self.assertEqual(stmt.children[2].children[0].children[2].children[2],4)

        # 对于第四个语句
        # not true or false * (3 + 4)
        # 先算not true
        # 再算 false * (3+4)
        # 最后算 false or 0
        stmt = i.ast.children[0].children[4].children[0]
        stmt = stmt.children[2]
        self.assertEqual(stmt.data, "or_test")
        self.assertEqual(stmt.children[0].data, "not_test")
        self.assertEqual(stmt.children[0].children[0], True)
        self.assertEqual(stmt.children[1].data, "mul_expr")
        self.assertEqual(stmt.children[1].children[0], False)
        self.assertEqual(stmt.children[1].children[2].data, "arith_expr")
        self.assertEqual(stmt.children[1].children[2].children[0], 3)
        self.assertEqual(stmt.children[1].children[2].children[2], 4)


    def test_if_stmt(self):
        pass
    def test_func(self):
        pass
    def test_match_stmt(self):
        pass
if __name__ == '__main__':
    unittest.main()
