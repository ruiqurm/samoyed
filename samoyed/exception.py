
class SamoyedException(Exception):
    """
    错误基类
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.pos = kwargs.get('pos')
class SamoyedInterpretError(SamoyedException):
    """
    解释错误
    """
    pass
class NotFoundEntrance(SamoyedInterpretError):
    def __init__(self,*args,**kwargs):
        default_message = '找不到入口main'
        super().__init__(default_message)

class NotImplementError(SamoyedInterpretError):
    def __init__(self,*args,**kwargs):
        default_message = '未实现'
        super().__init__(default_message)
class SyntaxError(SamoyedInterpretError):
    pass
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