"""
内置函数
"""
import threading
import signal

import time
from functools import wraps

def timeout(seconds=0.1):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise Exception(f"Timeout for function '{func.__name__}'")

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL,seconds) #used timer instead of alarm
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wraps(func)(wrapper)
    return decorator
"""
延迟流
"""
class TimeControl:
    """
    返回一个可调用对象，调用该对象会进行延迟
    如果主线程先结束，那么会取消计时器；
    否则，计时器会杀死主线程
    """
    def __init__(self,func,max_wait,min_wait=None,timeout_interval=0.2,sleep_interval=0.2):
        self.func = func
        self.timeout = threading.Event()
        self.can_exit = threading.Event()
        self.max_wait = max_wait
        self.min_wait = min_wait
        self.timeout_interval = 0.2
        self.sleep_interval = 0.2
    def __call__(self,*args,**kwargs):
        """
        生成流
        """
        # 启动两个计时函数
        self.timeout.clear()
        self.can_exit.clear()
        if self.min_wait is not None:
            self.min_wait_timer = threading.Timer(self.min_wait, lambda:self.min_wait_handler(self.can_exit))
            self.min_wait_timer.start()
        else:
            self.can_exit.set()
        self.max_wait_timer = threading.Timer(self.max_wait, lambda:self.max_wait_handler(self.timeout))
        self.max_wait_timer.start()
        @timeout(self.timeout_interval)
        def timeout_on_interval(*args,**kwargs):
            return self.func(*args,*kwargs)

        while True:
            try:
                result = timeout_on_interval(*args,**kwargs)
            except Exception:
                yield None
            else:
                yield result
            if self.timeout.is_set():
                self.max_wait_timer.cancel()
                if self.min_wait is not None:
                    self.min_wait_timer.cancel()
                return
            time.sleep(self.sleep_interval)
    def cancel(self):
        self.max_wait_timer.cancel()
        if self.min_wait is not None:
            self.min_wait_timer.cancel()
    def min_wait_handler(self,event:threading.Event):
        if not event.is_set():
            event.set()

    def max_wait_handler(self,event:threading.Event):
        # 最大超时时间
        if not event.is_set():
            event.set()

# result = []
# t = TimeControl(input,30)
# for i in t():
#     result.append(i)
#     print("".join(result))
#     if "".join(result).find("stop") != -1:
#         t.cancel()
#         break
# if not result:
#     print("silence")
# print("done")