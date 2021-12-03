from lark import Lark,Transformer
from lark.indenter import Indenter
f = open("../grammar/samoyed.gram")



class SamoyedIndenter(Indenter):
    """
    间隔控制
    """
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 8
class SamoyedTransformer(Transformer):
    """
    基础的语法制导，只会转换一些常量。
    """
    none = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False
    def SIGNED_FLOAT(self,value)->float:
        return float(value)
    def SIGNED_INT(self,value)->int:
        return int(value)

parser = Lark(f.read(), parser='lalr', postlex=SamoyedIndenter(),transformer=SamoyedTransformer())

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
    tree = parser.parse(f.read())

    print(tree.pretty())