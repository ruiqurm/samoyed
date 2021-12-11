from lark import Token,Tree
from samoyed.core import Interpreter
from samoyed.libs import make_arg_parser
pos_arg = {pos_arg}
parser = make_arg_parser(pos_arg=pos_arg,option_arg={option_arg})
ast = {ast}
args = vars(parser.parse_args())
for key in args:
    value = args[key]
    if isinstance(value,list):
        args[key] = value[0]
if pos_arg is not None:
    for i,arg in enumerate(pos_arg):
        args[i+1] = arg[0]
interpreter =  Interpreter(ast,args=args)
interpreter.exec()
