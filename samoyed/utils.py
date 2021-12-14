import fcntl
import os
import platform
import signal
from functools import wraps
from typing import Callable

from .exception import SamoyedTimeout

if platform.system() == 'Linux':
    import pathlib

    MAX_PIPE_BUFFER_SIZE = int(pathlib.Path("/proc/sys/fs/pipe-max-size").read_text())
else:
    MAX_PIPE_BUFFER_SIZE = 0

FLAG_SET_PIPE_BUFFER_SIZE = 1031  # 设置管道缓冲区的标志
FLAG_GET_PIPE_BUFFER_SIZE = 1032  # 读取管道缓冲区的标志


def watchdog(seconds=0.1):
    """看门狗装饰器

    seconds间隔后会抛出异常中断程序的执行，防止程序超时

    Parameters
    ----------
    seconds
        最大执行时间
    Returns
    -------
        装饰的函数
    """

    def decorator(func):
        # 处理抛出timeout的函数
        def _handle_timeout(signum, frame):
            raise SamoyedTimeout(f"Timeout for function '{func.__name__}'")

        def wrapper(*args, **kwargs):
            # 添加中断信号
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL, seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                # 取消信号
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


def make_pipe(name: str, buffer_size=8192) -> None:
    """
    生成一个具名管道
    Parameters
    ----------
    name
        管道位置和名字
    buffer_size
        缓存大小
    Returns
    -------
        文件描述符
    """

    os.mkfifo(name)
    fd = os.open(name, os.O_RDWR)
    buffer_size = MAX_PIPE_BUFFER_SIZE if buffer_size > MAX_PIPE_BUFFER_SIZE else buffer_size
    fcntl.fcntl(fd, FLAG_SET_PIPE_BUFFER_SIZE, buffer_size)
    os.close(fd)


def delete_pipe(name: str) -> None:
    """删除一个管道

    Parameters
    ----------
    name
        管道路径
    -------

    """
    try:
        os.remove(name)
    except Exception:
        pass


def get_pipe_read_end(name: str) -> (int, Callable):
    """
    获取管道的读取端函数
    :param name: 管道名
    :return: 读取函数
    """
    fd = os.open(name, os.O_RDWR)
    return fd, lambda num: os.read(fd, num).decode("utf-8")


def get_pipe_write_end(name: str) -> Callable:
    """
    获取管道的写入端函数
    :param name: 管道名
    :return: 写入函数
    """
    fd = os.open(name, os.O_RDWR)
    return lambda s: os.write(fd, s.encode("utf-8"))
