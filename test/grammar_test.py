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
        i = Interpreter(test_code,dont_init = True)
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
            i = Interpreter(test_code, dont_init=True)

        # state内没有东西
        test_code = \
"""
state hello:
"""
        with self.assertRaises(SamoyedInterpretError, msg="未闭合state不报错"):
            i = Interpreter(test_code, dont_init=True)

    def test_value(self)->None:
        """
        测试常量和变量：true,false,none,数字，字符串,name
        """
        test_code = \
"""
state hello:
    314
    -314
    1e5 # 100000.0
    1 +- 3.14 # -314
    3.1415629 # 3.1415629
    .1415926 # 0.1415926
    12345678901234567 # bigint
    "hello world" 
    \"\"\"
    cross
    line
    \"\"\"
    true
    false
    none
    variable_name
    __dunder_variable
    _v_a_r_
    _
    中文变量名
    _1_2_
    3.
"""
        i = Interpreter(test_code, dont_init=True)
        state = i.ast.children[0]
        print(state.pretty())
        delta = 1e-3
        self.assertEqual(state.children[1].children[0],314)
        self.assertEqual(state.children[2].children[0].children[1],314)
        self.assertTrue(state.children[3].children[0]-1e5 < delta)
        self.assertTrue(state.children[4].children[0].children[2].children[1]-(3.14) < delta)
        self.assertTrue(state.children[5].children[0]-3.1415629 < delta)
        self.assertTrue(state.children[6].children[0]-0.1415629 < delta)
        self.assertEqual(state.children[7].children[0],12345678901234567)
        self.assertEqual(state.children[8].children[0],"hello world")
        tmp = state.children[9].children[0].replace(" ","")
        self.assertEqual(tmp,"\ncross\nline\n")
        self.assertTrue(state.children[10].children[0])
        self.assertFalse(state.children[11].children[0])
        self.assertIsNone(state.children[12].children[0])
        self.assertEqual(state.children[13].children[0],"variable_name")
        self.assertEqual(state.children[14].children[0],"__dunder_variable")
        self.assertEqual(state.children[15].children[0],"_v_a_r_")
        self.assertEqual(state.children[16].children[0],"_")
        self.assertEqual(state.children[17].children[0],"中文变量名")
        self.assertEqual(state.children[18].children[0],"_1_2_")
        self.assertTrue(state.children[19].children[0] - 3.0 < delta)

        with self.assertRaises(SamoyedInterpretError, msg="非法数字"):
            i = Interpreter("1a\n", dont_init=True)
        with self.assertRaises(SamoyedInterpretError, msg="非法数字"):
            i = Interpreter("1.a\n", dont_init=True)
        with self.assertRaises(SamoyedInterpretError, msg="引号不闭合不报错"):
            i = Interpreter("a = \"hello\n", dont_init=True)
        with self.assertRaises(SamoyedInterpretError, msg="非法变量名"):
            i = Interpreter("12x\n", dont_init=True)
        with self.assertRaises(SamoyedInterpretError, msg="非法变量名"):
            i = Interpreter("1中文\n", dont_init=True)
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
        i = Interpreter(test_code, dont_init=True)
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
        self.assertEqual(stmt.children[2].data,"plus_expr") # (3 + 4) / 2
        self.assertEqual(stmt.children[2].children[0],3) # 3
        self.assertEqual(stmt.children[2].children[2],4) # 4
        self.assertEqual(stmt.children[3].children[0],"/") # /
        self.assertEqual(stmt.children[4],2) # 2

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
        self.assertEqual(stmt.children[2].children[0].children[2].data,"plus_expr")
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
        self.assertEqual(stmt.children[1].children[2].data, "plus_expr")
        self.assertEqual(stmt.children[1].children[2].children[0], 3)
        self.assertEqual(stmt.children[1].children[2].children[2], 4)

        i = Interpreter("1+2+(3+4*2)+5*6\n", dont_init=True)
        expr = i.ast.children[0].children[0]
        self.assertEqual(7,len(expr.children))# 三个加号，4个操作数，合起来有7个
        self.assertEqual(1,expr.children[0])
        self.assertEqual("+",expr.children[1].children[0])
        self.assertEqual(2,expr.children[2])
        self.assertEqual("+",expr.children[3].children[0])
        self.assertEqual("plus_expr",expr.children[4].data)# 3 + 4 * 2
        self.assertEqual(3, len(expr.children[4].children)) # 3,+,4*2三项
        self.assertEqual(3, expr.children[4].children[0])
        self.assertEqual("mul_expr", expr.children[4].children[2].data)
        self.assertEqual("+",expr.children[5].children[0])
        self.assertEqual("mul_expr",expr.children[6].data)
        self.assertEqual(3,len(expr.children[6].children)) # 5,*,6
        self.assertEqual(5,expr.children[6].children[0])
        self.assertEqual(6,expr.children[6].children[2])

    def test_if_stmt(self):
        test_code = \
"""
state hello:
    if a==1 :
        print("hello,world")
    else:
        print("don't hello world")
"""
        i = Interpreter(test_code, dont_init=True)
        stmt = i.ast.children[0].children[1]
        self.assertEqual(3,len(stmt.children))# bool表达式，if字句，else字句
        self.assertEqual("compare_expr",stmt.children[0].data)
        self.assertEqual("simple_stmt",stmt.children[1].data)
        self.assertEqual("simple_stmt",stmt.children[2].data)

        # 嵌套if
        test_code = \
"""
state hello:
    if a==1 :
        print("1")
    else:
        if b==1:
            print("2")
"""
        i = Interpreter(test_code, dont_init=True)
        stmt = i.ast.children[0].children[1]
        self.assertEqual(3,len(stmt.children))# bool表达式，if字句，else字句
        self.assertEqual("compare_expr",stmt.children[0].data)
        self.assertEqual("simple_stmt",stmt.children[1].data)
        self.assertEqual("if_stmt",stmt.children[2].data)
        self.assertEqual(2,len(stmt.children[2].children))# bool表达式，if字句
        self.assertEqual("compare_expr",stmt.children[2].children[0].data)
        self.assertEqual("simple_stmt",stmt.children[2].children[1].data)

    def test_func(self):
        i = Interpreter("hello()\n", dont_init=True)
        self.assertEqual("funccall", i.ast.children[0].children[0].data)
        self.assertIsNone(i.ast.children[0].children[0].children[1])

        i = Interpreter("hello(world,1,2,3,4)\n", dont_init=True)
        stmt = i.ast.children[0].children[0]
        self.assertEqual("funccall", stmt.data)
        self.assertEqual("hello", stmt.children[0])
        self.assertEqual(5, len(stmt.children[1].children))
        self.assertEqual("world", stmt.children[1].children[0])
        self.assertEqual(1, stmt.children[1].children[1])
        self.assertEqual(2, stmt.children[1].children[2])

        #允许跨行参数，下面不应该报错
        try:
            i = Interpreter("hello(\na)\n", dont_init=True)
            i = Interpreter("hello(a,\nb)\n", dont_init=True)
        except SamoyedInterpretError:
            raise AssertionError("跨行测试失败")
        # 测试不正确的函数
        with self.assertRaises(SamoyedInterpretError, msg="函数参数未结束没有报错"):
            i = Interpreter("hello(world,1,)\n", dont_init=True)
        with self.assertRaises(SamoyedInterpretError, msg="函数括号有问题没有报错"):
            i = Interpreter("hello(world,1,）\n", dont_init=True)

    def test_match_stmt(self):
        code = \
"""
state hello:
    match dog:
        "samoyed" =>
            print("samoyed")
        "doge" =>
            print("doge")
        "shiba" =>
            print("shiba")
        default =>
            print("unknown dog")
"""
        i = Interpreter(code, dont_init=True)
        stmt = i.ast.children[0].children[1]
        print(stmt.pretty())
        self.assertEqual(5,len(stmt.children))
        self.assertEqual("case_stmt",stmt.children[1].data)
        self.assertEqual("case_stmt",stmt.children[2].data)
        self.assertEqual("case_stmt",stmt.children[3].data)
        self.assertEqual("default_stmt",stmt.children[4].data)

        # 嵌套match
        code = \
"""
state hello:
    match animal:
        "cat" =>
            print("cat")
        "dog" =>
            match animal:
                "samoyed" =>
                    print("samoyed")
                "doge" =>
                    print("doge")
                "shiba" =>
                    print("shiba")
                default =>
                    print("unknown dog")
"""
        i = Interpreter(code, dont_init=True)
        stmt = i.ast.children[0].children[1]
        print(stmt.pretty())
        self.assertEqual(3,len(stmt.children)) # cat dog
        self.assertEqual("case_stmt",stmt.children[1].data)
        self.assertEqual("case_stmt",stmt.children[2].data)
        self.assertEqual("dog",stmt.children[2].children[0])
        self.assertEqual("match_stmt",stmt.children[2].children[1].data)
        stmt = stmt.children[2].children[1]
        self.assertEqual(5, len(stmt.children))
        self.assertEqual("case_stmt", stmt.children[1].data)
        self.assertEqual("case_stmt", stmt.children[2].data)
        self.assertEqual("case_stmt", stmt.children[3].data)
        self.assertEqual("default_stmt", stmt.children[4].data)

if __name__ == '__main__':
    unittest.main()
