"""
内置函数
"""
import argparse
import sqlite3
import threading
import time
from numbers import Number
from typing import List, Union, Tuple,Dict

from .exception import SamoyedTimeout, SamoyedRuntimeError
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

        Parameters
        ----------
        args
        kwargs

        Returns
        -------

        Raises
        ------
        `SamoyedRuntimeError` : 函数运行出错时抛出
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
            except SamoyedTimeout:
                yield None
            except Exception as e:
                raise SamoyedRuntimeError(str(e))
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


def make_arg_parser(pos_arg: List[Tuple[str, Union[str, None]]] = None,
                    option_arg: List[Tuple[str, Union[str, None], Union[str, None]]] = None,
                    helping_message: str = None):
    parser = argparse.ArgumentParser(
        description='自动客服脚本\n{}'.format("" if helping_message is None else helping_message))

    """
    给顺序参数添加
    """
    if pos_arg is not None:
        for arg in pos_arg:
            # arg = (描述，帮助信息)
            parser.add_argument(arg[0], help=arg[1], nargs=1)

    """
    给关键词参数添加
    """
    if option_arg is not None:
        for arg in option_arg:
            # arg = (全称，简写，帮助信息)
            if arg[1] is not None:
                parser.add_argument("--" + arg[0], nargs=1, help=arg[2])
            else:
                parser.add_argument("--" + arg[0], "-" + arg[1], nargs=1, help=arg[2])
    return parser


def arg_seq_add(l: List[Tuple[str, Union[str, None]]], name: str, help_msg: str = None):
    """
    添加顺序参数
    """
    l.append((name, help_msg))


def arg_option_add(l: List[Tuple[str, Union[str, None], Union[str, None]]], full_name: str, shortcut: str = None,
                   help_msg: str = None):
    """
    添加可选参数
    """
    l.append((full_name, shortcut, help_msg))


def mock_add(a: Union[int, float, bool, str, None], b: Union[int, float, bool, str, None]) -> Union[
    int, float, str, None]:
    """
    实现字符串和数字相加操作的add
    """
    if isinstance(a, Number) and isinstance(b, Number):
        return a + b
    elif isinstance(a, str) or isinstance(b, str):
        return "{}{}".format(a, b)
    else:
        return None


def sqlite_connect(conn2curosr:Dict[sqlite3.Cursor,sqlite3.Connection],db_name: str) -> sqlite3.Cursor:
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    conn2curosr[cursor] = conn
    return cursor


def sqlite(conn2curosr:Dict[sqlite3.Cursor,sqlite3.Connection],cursor: sqlite3.Cursor, sql: str) -> str:
    cursor.execute(sql)
    conn2curosr[cursor].commit()
    return str(cursor.fetchall())

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
