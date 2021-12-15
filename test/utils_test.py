import threading
import time
import unittest
from samoyed.utils import *

class UtilsTest(unittest.TestCase):

    def test_watchdog(self):
        """
        测试看门狗
        """
        def test_function(timeout:float,sleep_time:float)->Callable:
            @watchdog(timeout)
            def func():
                time.sleep(sleep_time)
            return func
        print("[看门狗测试]",end=' ')
        t = test_function(0.5,0.1)
        t() #不会异常
        t = test_function(0.2, 0.3)
        with self.assertRaises(Exception):
            t()
        t = test_function(0.2, 0.2)
        with self.assertRaises(Exception):
            t()
        t = test_function(0.21, 0.2)
        t()
        print("pass")

if __name__ == '__main__':
    unittest.main()
    print("通过utils_test\n")