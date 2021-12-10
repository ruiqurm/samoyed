from lark import Lark,Transformer
from lark.indenter import Indenter
from samoyed.core import Interpreter




if __name__ == '__main__':
    f = open("test/script/simple.sam", "r")
    i = Interpreter(f.read(),dont_init=True)
    print(i.ast.pretty())