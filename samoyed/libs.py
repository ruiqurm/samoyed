"""
内置函数
"""
import threading
import inspect,ctypes

import ctypes

def kill_thread(thread):
    """
    thread: a threading.Thread object
    """
    thread_id = thread.ident
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
        print('Exception raise failure')
"""
延迟流
"""
class TimeControl:
    """
    返回一个可调用对象，调用该对象会进行延迟
    如果主线程先结束，那么会取消计时器；
    否则，计时器会杀死主线程
    """
    def __init__(self,func,max_wait,min_wait=None):
        self.func = func
        self.timeout = threading.Event()
        self.can_exit = threading.Event()
        self.max_wait = max_wait
        self.min_wait = min_wait
    def __call__(self,*args,**kwargs):
        """
        生成流
        """
        # 启动两个计时函数
        self.timeout.clear()
        self.can_exit.clear()
        if self.min_wait is not None:
            self.min_wait_timer = threading.Timer(self.min_wait, lambda:self.max_wait_handler(self.can_exit))
            self.min_wait_timer.start()
        else:
            self.can_exit.set()

        self.max_wait_timer = threading.Timer(self.max_wait, lambda:self.max_wait_handler(self.timeout))
        self.max_wait_timer.start()
        t = threading.Thread(target = self.main)
        t.start()
        self.max_wait_timer.join()
    def main(self):
        while True:
            yield self.func()
            if self.timeout.is_set():
                print("done")
                self.max_wait_timer.cancel()
                if self.min_wait_timer is not None:
                    self.min_wait_timer.cancel()
                return
    def min_wait_handler(self,event:threading.Event):
        if not event.is_set():
            event.set()
    def max_wait_handler(self,event:threading.Event):
        # 最大超时时间
        if not event.is_set():
            event.set()
