from lark import Lark
from lark.indenter import Indenter
f = open("../grammar/samoyed.gram")



class SamoyedIndenter(Indenter):
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 8

parser = Lark(f.read(), parser='lalr', postlex=SamoyedIndenter())

test_tree = """
name(1,23)
state hello:
    x = 2
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
"""

def test():
    print(parser.parse(test_tree).pretty())

if __name__ == '__main__':
    test()