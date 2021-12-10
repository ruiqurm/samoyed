import unittest
from samoyed.utils import *
import os
import fcntl
import subprocess
class UtilsTest(unittest.TestCase):
    def test_make_pipe(self):
        make_pipe("/tmp/test_pipe")
        try:
            fd = os.open("/tmp/test_pipe",os.O_RDWR)
            self.assertNotEqual(fd,-1)
            self.assertEqual(fcntl.fcntl(fd,FLAG_GET_PIPE_BUFFER_SIZE),8192*8)
        finally:
            delete_pipe("/tmp/test_pipe")
    def test_read_pipe(self):
        try:
            # make_pipe("/tmp/test_pipe1")
            r = get_pipe_read_end("/tmp/test_pipe1")
            # subprocess.run(["echo","hello world",">","/tmp/test_pipe1"])
            result = r(5)
            print(result)
        finally:
            delete_pipe("/tmp/test_pipe1")
if __name__ == '__main__':
    unittest.main()
