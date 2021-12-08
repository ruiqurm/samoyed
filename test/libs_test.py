import multiprocessing
import threading
import time
import unittest
import threading
from samoyed.libs import TimeControl


def mock_input(q: multiprocessing.Queue, plan: dict) -> None:
    """
    模拟输入
    :return:
    """
    keys = sorted(list(plan.keys()))
    if not keys:
        return
    for i, key in enumerate(keys):
        if i == 0:
            time.sleep(keys[i])
        else:
            time.sleep(keys[i] - keys[i - 1])
        q.put(plan[key])
class TimeControlTest(unittest.TestCase):
    

    def test_timecontrol(self):
        """
        测试能否正常完成输入
        :return:
        """

        """
        测试是否有正常超时
        """
        e = threading.Event()
        t = threading.Timer(1.01, lambda: e.set())
        c = TimeControl(input, 1)
        for i in c():
            pass
        self.assertEqual(e.is_set(), False)
        print("[测试是否有正常超时] pass")

        """
        测试最小时间是否满足
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 0.5: "world"}
        process = multiprocessing.Process(target=mock_input, args=(q, plan))
        e = threading.Event()
        t = threading.Timer(0.5, lambda: e.set())
        c = TimeControl(input, 1,0.5)
        t.start()
        for i in c():
            if e.is_set():
                self.assertTrue(c.can_exit.is_set())
        print("[测试最小时间是否满足] pass")
        """
        测试能否取到数据
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 0.5: "world"}
        process = multiprocessing.Process(target=mock_input, args=(q, plan))
        process.start()
        t = TimeControl(lambda q: q.get(), 1)
        result = []
        for i in t(q):
            if i is not None:
                result.append(i)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "hello")
        self.assertEqual(result[1], "world")
        process.join()
        print("[测试能否取到数据] pass")

        """
        测试能否跳出阻塞函数
        """
        q = multiprocessing.Queue()
        plan = {}
        process = multiprocessing.Process(target=mock_input, args=(q, plan))
        process.start()
        t = TimeControl(lambda q: q.get(), 1)
        result = []
        for i in t(q):
            if i is not None:
                result.append(i)
        self.assertEqual(len(result), 0)
        process.join()
        print("[测试能否跳出阻塞函数] pass")

        """
        测试能否多的数据能否接到
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 2 : "world"} # world 不应该接到
        process = multiprocessing.Process(target=mock_input, args=(q, plan))
        process.start()
        t = TimeControl(lambda q: q.get(), 1) # 超时时间1s
        result = []
        for i in t(q):
            if i is not None:
                result.append(i)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "hello")
        process.join()
        print("[测试能否多的数据能否接到] pass")

    def test_matching_before_max_time(self):
        """
        测试能否正常退出
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 0.5: "world",1:"stop"}  # 输入stop停止
        thread = threading.Thread(target=mock_input, args=(q, plan))
        e = threading.Event()
        timer = threading.Timer(1.1, lambda: e.set()) # 计时器
        thread.start()
        t = TimeControl(lambda q: q.get(), 3)  # 超时时间3s
        results = []
        timer.start()
        for result in t(q):
            if result is not None:
                results.append(result)
            if "".join(results).find("stop") != -1:
                t.cancel()
                break
        self.assertFalse(e.is_set()) # 1s的时候计时器还未触发
        self.assertEqual(3,len(results))
        timer.join()
    def test_matching_before_min_time(self):
        """
        测试是否会提前退出
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 0.5: "world",1:"stop"}  # 输入stop停止
        thread = threading.Thread(target=mock_input, args=(q, plan))
        e = threading.Event()
        e2= threading.Event()
        timer_pre = threading.Timer(1.1, lambda: e.set()) # 提前退出的计时器
        timer_after = threading.Timer(3, lambda: e2.set()) # 超时的计时器

        thread.start()
        t = TimeControl(lambda q: q.get(), 3, 1.2)  # 超时时间5s，第2秒才能退出
        results = []
        timer_pre.start()
        timer_after.start()
        for result in t(q):
            if result is not None:
                results.append(result)
            if "".join(results).find("stop") != -1 and t.can_exit.is_set():
                t.cancel()
                break
        self.assertTrue(e.is_set()) # 1.9s的时候计时器才触发。如果1s就退出了就会报错
        self.assertFalse(e2.is_set()) # 不应该超时
        timer_pre.join()
        timer_after.cancel()


