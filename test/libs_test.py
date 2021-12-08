import multiprocessing
import threading
import time
import unittest

from samoyed.libs import TimeControl

"""
q =  multiprocessing.Queue()
process = multiprocessing.Process(target = mock_input,args=(q,plan))
process.start()
def test(q):
    while True:
        yield q.get()
        
for i in test(q):
    print(i)
"""


class TimeControlTest(unittest.TestCase):
    @staticmethod
    def mock_input(q: multiprocessing.Queue, plan: dict) -> None:
        """
        模拟输入
        :return:
        """
        keys = sorted(list(plan.keys()))
        if not keys:
            return
        for i, key in enumerate(keys[:-1]):
            q.put(plan[key])
            print("put {},sleep time{}".format(plan[key], keys[i + 1] - keys[i]))
            time.sleep(keys[i + 1] - keys[i])
        q.put(plan[keys[-1]])

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
        """
        测试最小时间是否满足
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 0.5: "world"}
        process = multiprocessing.Process(target=self.mock_input, args=(q, plan))
        e = threading.Event()
        t = threading.Timer(0.5, lambda: e.set())
        c = TimeControl(input, 1,0.5)
        t.start()
        for i in c():
            if e.is_set():
                self.assertTrue(c.can_exit.is_set())
        """
        测试能否取到数据
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 0.5: "world"}
        process = multiprocessing.Process(target=self.mock_input, args=(q, plan))
        process.start()
        t = TimeControl(lambda q: q.get(), 1)
        result = []
        for i in t(q):
            result.append(i)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "hello")
        self.assertEqual(result[1], "world")
        process.join()

        """
        测试能否跳出阻塞函数
        """
        q = multiprocessing.Queue()
        plan = {}
        process = multiprocessing.Process(target=self.mock_input, args=(q, plan))
        process.start()
        t = TimeControl(lambda q: q.get(), 1)
        result = []
        for i in t(q):
            result.append(i)
        self.assertEqual(len(result), 0)
        process.join()

        """
        测试能否多的数据能否接到
        """
        q = multiprocessing.Queue()
        plan = {0: "hello", 2 : "world"} # world 不应该接到
        process = multiprocessing.Process(target=self.mock_input, args=(q, plan))
        process.start()
        t = TimeControl(lambda q: q.get(), 1) # 超时时间1s
        result = []
        for i in t(q):
            result.append(i)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "hello")
        process.join()

        """
        测试最小时间
        """
        q = multiprocessing.Queue()
        process = multiprocessing.Process(target=self.mock_input, args=(q, plan))
        process.start()
        t = TimeControl(lambda q: q.get(), 1,0.5)  # 超时时间1s
        result = []
        for i in t(q):
            result.append(i)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "hello")
        process.join()
    def test_matching(self):
        pass
        # for result in control():
        #     # 保存每次结果
        #     results.append(result)
        #     # 如果结果出现在case字句中，那么跳出
        #     for i, case in enumerate(cases):
        #         concat_result = "".join(results)
        #         if concat_result.find(case):
        #             find_flag = True
        #             finded_case = i
        #             break
