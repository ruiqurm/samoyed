"""
内置函数
"""
import argparse
import sqlite3
import threading
import time
from numbers import Number
from typing import List, Union, Tuple, Dict, Any

from .exception import SamoyedTimeout, SamoyedRuntimeError
from .utils import watchdog


class TimeControl:
    """
    返回一个可调用对象，调用该对象会进行延迟
    如果主线程先结束，那么会取消计时器；
    否则，计时器会杀死主线程
    """

    def __init__(self, func, max_wait, min_wait=None, timeout_interval=0.2, sleep_interval=0.2):
        """初始化
        Parameters
        ----------
        func
            要定时的函数
        max_wait
            最大等待
        min_wait
            至少等待时间
        timeout_interval
            函数执行最大周期
        sleep_interval
            每循环停顿周期
        """
        self.func = func
        self.timeout = threading.Event()
        self.can_exit = threading.Event()
        self.max_wait = max_wait
        self.min_wait = min_wait
        self.timeout_interval = 0.1
        self.sleep_interval = 0.1

    def __call__(self, *args, **kwargs):
        """
        调用函数

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

        # 给函数创建看门狗
        @watchdog(self.timeout_interval)
        def timeout_on_interval(*args, **kwargs):
            return self.func(*args, *kwargs)

        # 外层的try只用于处理KeyboardInterrupt，无其他用途
        try:
            while True:
                # 尝试执行函数
                try:
                    result = timeout_on_interval(*args, **kwargs)
                except SamoyedTimeout:
                    # 如果超时，返回None
                    yield None
                except Exception as e:
                    raise SamoyedRuntimeError(str(e))
                else:
                    # 否则，返回结果
                    yield result

                # 如果函数执行时间已经超时，那么退出
                if self.timeout.is_set():
                    self.cancel()
                    return

                # 睡眠，防止频繁运行
                time.sleep(self.sleep_interval)

        except KeyboardInterrupt:
            self.cancel()
            raise KeyboardInterrupt

    def cancel(self)->None:
        """撤销两个定时器线程
        """
        self.max_wait_timer.cancel()
        if self.min_wait is not None:
            self.min_wait_timer.cancel()

    def min_wait_handler(self, event: threading.Event):
        """定时器将信号量置位
        """
        if not event.is_set():
            event.set()

    def max_wait_handler(self, event: threading.Event):
        """定时器将信号量置位
        """
        # 最大超时时间
        if not event.is_set():
            event.set()


def make_arg_parser(pos_arg: List[Tuple[str, Union[str, None]]] = None,
                    option_arg: List[Tuple[str, Union[str, None], Union[str, None]]] = None,
                    helping_message: str = None):
    """
    创建一个模式化的命令行参数处理程序
    Parameters
    ----------
    pos_arg
        顺序参数，传入的列表内保存2维元组
        元组第一个参数是命令行参数名字
        第二个参数是帮助信息
    option_arg
        可选参数，传入的列表内保存3维元组
        元组第一个参数是命令行参数全称
        第二个参数是简写
        第三个参数是帮助信息
    helping_message
        全局帮助信息
    Returns
    -------
        一个命令行参数解析器
    """
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
    Parameters
    ----------
    l
        一个列表
    name
        参数名
    help_msg
        帮助信息
    """
    l.append((name, help_msg))


def arg_option_add(l: List[Tuple[str, Union[str, None], Union[str, None]]], full_name: str, shortcut: str = None,
                   help_msg: str = None):
    """
    添加可选参数
    Parameters
    ----------
    l
        一个列表
    full_name
        参数名全称
    shortcut
        参数名缩写
    help_msg
        帮助信息
    """
    l.append((full_name, shortcut, help_msg))


def mock_add(a: Union[int, float, bool, str, None], b: Union[int, float, bool, str, None]) -> Union[
    int, float, str, None]:
    """解释器内部使用的加法
    python内置的add不支持字符串和数字加法。
    这里允许进行这样的操作

    Parameters
    ----------
    a
        参数a
    b
        参数b

    Returns
    -------
        a+b的结果
    """
    if isinstance(a, Number) and isinstance(b, Number):
        return a + b
    elif isinstance(a, str) or isinstance(b, str):
        return "{}{}".format(a, b)
    else:
        return None


def sqlite_connect(conn2curosr: Dict[sqlite3.Cursor, sqlite3.Connection], db_name: str) -> sqlite3.Cursor:
    """
    建立一个sql连接
    Parameters
    ----------
    conn2curosr
        用于绑定cursor和connection的一个字典
    db_name
        数据库名

    Returns
    -------
        一个cursor对象
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    conn2curosr[cursor] = conn
    return cursor


def sqlite(conn2curosr: Dict[sqlite3.Cursor, sqlite3.Connection], cursor: sqlite3.Cursor, sql: str) -> List[Any]:
    """
    执行一条sql指令。
    注意，由于脚本语言不支持列表，因此这里把返回结果全部转化成了字符串
    Parameters
    ----------
    conn2curosr
        用于绑定cursor和connection的一个字典
    cursor
        执行指令的cursor
    sql
        sql指令

    Returns
    -------
        sql的结果
    """
    cursor.execute(sql)
    conn2curosr[cursor].commit()
    return cursor.fetchall()


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
