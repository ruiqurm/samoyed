from lark import Lark,Transformer
from lark.indenter import Indenter
from samoyed.core import Interpreter

test_tree = """
name(1,23)
state hello:
    x = true
    pass
state dog:
    ok(1,2,hello()+"good"+2)
    speak()
    2*(3+4)
    branch hello
state cat:
    match "sad":
        asdasd =>
            asdasd
            asdasd
        sadasd =>
            asdsa
        default =>
            branch here
    for i = 1 to 5:
        hello()
        if i==1:
            break
        else:
            print("ok")
"""



if __name__ == '__main__':
    f = open("../test/script/simple.sam","r")
    i = Interpreter(f.read(),dont_parse=True)
    tree = i.ast

    print(tree.pretty())