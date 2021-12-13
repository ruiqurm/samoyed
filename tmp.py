from lark import Lark,Transformer
from lark.indenter import Indenter
from samoyed.core import Interpreter
# from samoyed.libs import make_arg_parser

s = """
cursor = sqlite_connect("test.db")
state main:
    sqlite(cursor,"create table IF NOT EXISTS T(A varchar(255),B varchar(255))")
    sqlite(cursor,"insert into T (A) values ('Hello')")
    result = sqlite(cursor,"select * from T")
"""
if __name__ == '__main__':
    # f = open("test/script/simple.sam", "r")
    # i = Interpreter(f.read(),args={"名字":"ruiqurm"})
    # i.exec()
    # print(i.ast.pretty())
    i = Interpreter(s)
    i.exec()


