import fcntl
import os
import platform
import signal
from functools import partial,wraps
from typing import Callable
from .exception import SamoyedTimeout
if platform.system() == 'Linux':
    import pathlib

    MAX_PIPE_BUFFER_SIZE = int(pathlib.Path("/proc/sys/fs/pipe-max-size").read_text())
else:
    MAX_PIPE_BUFFER_SIZE = 0

FLAG_SET_PIPE_BUFFER_SIZE = 1031  # 设置管道标志
FLAG_GET_PIPE_BUFFER_SIZE = 1032  # 读取管道缓冲区标志


def watchdog(seconds=0.1):
    """
    看门狗装饰器
    """

    def decorator(func):
        def _handle_timeout(signum, frame):
            raise SamoyedTimeout(f"Timeout for function '{func.__name__}'")

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL, seconds)  # used timer instead of alarm
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


def make_pipe(name: str, buffer_size=8192) -> None:
    """
    生成一个具名管道
    :param name: 管道位置和名字
    :param buffer_size: 缓存大小
    :return: 文件描述符
    """
    os.mkfifo(name)
    fd = os.open(name, os.O_RDWR)
    buffer_size = MAX_PIPE_BUFFER_SIZE if buffer_size > MAX_PIPE_BUFFER_SIZE else buffer_size
    fcntl.fcntl(fd, FLAG_SET_PIPE_BUFFER_SIZE, buffer_size)
    os.close(fd)


def delete_pipe(name: str):
    try:
        os.remove(name)
    except Exception:
        pass


def get_pipe_read_end(name: str) -> Callable:
    """
    获取管道的读取端函数
    :param name: 管道名
    :return: 读取函数
    """
    fd = os.open(name, os.O_RDWR)
    return partial(os.read, fd)


def get_pipe_write_end(name: str) -> Callable:
    """
    获取管道的写入端函数
    :param name: 管道名
    :return: 写入函数
    """
    fd = os.open(name, os.O_RDWR)
    return partial(os.write, fd)
