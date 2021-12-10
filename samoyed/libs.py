"""
内置函数
"""
import threading
import time
from typing import List, Union, Tuple

from .utils import watchdog

"""
延迟流
"""


class TimeControl:
    """
    返回一个可调用对象，调用该对象会进行延迟
    如果主线程先结束，那么会取消计时器；
    否则，计时器会杀死主线程
    """

    def __init__(self, func, max_wait, min_wait=None, timeout_interval=0.2, sleep_interval=0.2):
        self.func = func
        self.timeout = threading.Event()
        self.can_exit = threading.Event()
        self.max_wait = max_wait
        self.min_wait = min_wait
        self.timeout_interval = 0.1
        self.sleep_interval = 0.1

    def __call__(self, *args, **kwargs):
        """
        生成流
        """
        # 启动两个计时函数
        self.timeout.clear()
        self.can_exit.clear()
        if self.min_wait is not None:
            self.min_wait_timer = threading.Timer(self.min_wait, lambda: self.min_wait_handler(self.can_exit))
            self.min_wait_timer.start()
        else:
            self.can_exit.set()
        self.max_wait_timer = threading.Timer(self.max_wait, lambda: self.max_wait_handler(self.timeout))
        self.max_wait_timer.start()

        @watchdog(self.timeout_interval)
        def timeout_on_interval(*args, **kwargs):
            return self.func(*args, *kwargs)

        while True:
            try:
                result = timeout_on_interval(*args, **kwargs)
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

    def min_wait_handler(self, event: threading.Event):
        if not event.is_set():
            event.set()

    def max_wait_handler(self, event: threading.Event):
        # 最大超时时间
        if not event.is_set():
            event.set()


import argparse
def make_arg_parser(pos_arg: List[str],
                    explain_pos: List[str] = None,
                    options: List[Union[str, Tuple[str,str], ]] = None,
                    explain_options: List[str] = None,
                    helping_message:str = None):
    """
    :param pos_arg: 位置参数个数
    :param explain_pos: 解释各个位置参数
    :param options: 选项参数
    :param explain_options: 解释各个选项参数
    :param helping_message: 帮助信息
    :return:
    """
    parser = argparse.ArgumentParser(description='自动客服脚本\n{}'.format("" if helping_message is None else helping_message))

    """
    给顺序参数添加
    """
    if explain_pos is not None and len(explain_pos)!=len(pos_arg):
        raise Exception("个数不同")
    if explain_pos is not None:
      for arg,help_msg in zip(pos_arg,explain_pos):
            parser.add_argument(arg,nargs=1,help=help_msg)
    else:
        for arg in pos_arg:
            parser.add_argument(arg, nargs=1,)

    """
    给关键词参数添加
    """
    if options is not None:
        if explain_options is not None and len(options)!=len(explain_options):
            raise Exception("个数不同")
        if explain_options is not None:
          for arg,help_msg in zip(options,explain_options):
            if isinstance(arg,str):
                parser.add_argument("-"+arg,nargs=1,help=help_msg)
            elif isinstance(arg,tuple):
                parser.add_argument("-"+arg[0],"--"+arg[1], nargs=1, help=help_msg)
        else:
            for arg in options:
                if isinstance(arg, str):
                    parser.add_argument("-" + arg, nargs=1)
                elif isinstance(arg, tuple):
                    parser.add_argument("-" + arg[0], "--" + arg[1], nargs=1)
    return parser

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
