
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