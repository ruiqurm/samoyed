from lark import Lark,Transformer
from lark.indenter import Indenter
from samoyed.core import Interpreter,compile
# from samoyed.libs import make_arg_parser


import argparse
if __name__ == '__main__':
    f = open("test/script/simple.sam", "r")
    # i = Interpreter(f.read(),args={"名字":"ruiqurm"})
    # i.exec()
    # print(i.ast.pretty())
    compile(f.read(),"hello.py")


