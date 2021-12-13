from typing import Tuple, List

from lark import Token


class SamoyedException(Exception):
    """
    错误基类
    """

    def __init__(self, message: str=None, pos: Tuple[int, int] = None):
        message = message or ""
        if pos:
            super().__init__("line {},column {}:{}".format(pos[0], pos[1], message))
        else:
            super().__init__(message)


class SamoyedInterpretError(SamoyedException):
    """
    解释错误
    """
    pass


class SamoyedNotFoundEntrance(SamoyedInterpretError):
    def __init__(self, *args, **kwargs):
        default_message = '找不到入口main'
        super().__init__(default_message)


class SamoyedNotImplementError(SamoyedInterpretError):
    def __init__(self, *args, **kwargs):
        default_message = '未实现'
        super().__init__(default_message)


class SamoyedSyntaxError(SamoyedInterpretError):
    TOKEN_TO_CHINESE = {
        "_INDENT": "缩进",
        "_NEWLINE": "换行",
        "NAME": "标识符名称",
        "INT": "int",
        "FLOAT": "float",
        "STR": "str",
        "DOLLAR_VAR": "$变量",
        "LETTER": "字符",
        "COMMENT": "注释",
        "STRING": "字符串",
        "LONG_STRING": "跨行字符串",
        "$END": "EOF",
        "LESSTHAN" :"<=",
        "MORETHAN" :">=",
        "COMMA" : "逗号",
        "SLASH" : "/",
        "STAR" : "*",
        "QMARK" : "?",
        "PLUS" : "+",
        "MINUS" : "-",

    }

    def __init__(self, expected: List[str], t: Token, pos=None):
        message = "\nexpected: [{}]\ngot:{}".format(
            ",".join([self.TOKEN_TO_CHINESE[exp] if exp in self.TOKEN_TO_CHINESE else exp for exp in expected]),
            f"{t.value}({self.TOKEN_TO_CHINESE[t.type] if t.type in self.TOKEN_TO_CHINESE else t.type})")
        if pos:
            super().__init__("line {},column {}:{}".format(pos[0], pos[1], message))
        else:
            super().__init__(message)


class SamoyedRuntimeError(SamoyedException):
    """
    运行时错误
    """
    pass


class SamoyedTypeError(SamoyedRuntimeError):
    """
    类型错误
    """
    pass


class SamoyedNameError(SamoyedRuntimeError):
    """
    类型错误
    """
    pass

class SamoyedTimeout(SamoyedRuntimeError):
    pass