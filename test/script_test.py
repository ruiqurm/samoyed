import sqlite3
import subprocess
import sys
import time
import unittest
import warnings
import os
from typing import Callable, Tuple
import os
import sqlite3
import subprocess
import sys
import unittest
import warnings
from typing import Callable, Tuple


class MockTerminal:

    def __init__(self, filename, *args):
        self.arg = args
        self.command = [sys.executable, "tmp.py", *args]
        self.fd = os.open("/tmp/test_pipe", os.O_RDWR | os.O_NONBLOCK)
        self.filename = filename

    def __enter__(self) -> Tuple[Callable, subprocess.Popen]:
        self.compile(self.filename)
        self.proc = subprocess.Popen(self.command, stdin=self.fd, stdout=subprocess.PIPE, text=True)
        return lambda s: os.write(self.fd, s.encode()), self.proc

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.close(self.fd)
        self.proc.terminate()
        self.clean_compile()

    def compile(self, file, output="tmp.py"):
        samc = "{}/samc".format("/".join(__file__.split("/")[:-2]))
        command = [sys.executable, samc, "gen", file, "-o", output]
        subprocess.run(command)

    def clean_compile(self, output="tmp.py"):
        if os.path.exists(output):
            os.remove(output)


class ScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore")

    def test_print_sam(self):
        """
        测试 script/print.sam
        """
        print("[测试print.sam] ", end="")
        path = "{}/script/print.sam".format("/".join(__file__.split("/")[:-1]))
        with MockTerminal(path) as (_, proc):
            proc.wait()
            result = proc.stdout.read()
        self.assertEqual(result.replace("\n", ""), "mainabmain")
        print("pass")

    def test_example_sam(self):
        """
        测试 script/example.sam
        """
        path = "{}/script/example.sam".format("/".join(__file__.split("/")[:-1]))
        print("[example脚本测试]")
        print("    [发送hello]",end='')
        with MockTerminal(path) as (write, proc):
            write("hello\n")
            proc.wait()
            result = proc.stdout.read()
        self.assertTrue(str(result).find("hello world")!=-1)
        print("pass")
        print("    [不发送]",end='')
        with MockTerminal(path) as (write, proc):
            proc.wait()
            result = proc.stdout.read()
        self.assertTrue(str(result).find("超时") != -1)
        print("pass")
    def test_database_sam(self):
        try:
            if os.path.exists("test.db"):
                os.remove("test.db")
            """
            数据库
            """
            conn = sqlite3.connect("test.db")
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS USER (id INTEGER PRIMARY KEY,"
                           "username VARCHAR(255) UNIQUE ,"
                           "phone VARCHAR(16));")
            cursor.execute("INSERT INTO USER(username,phone) VALUES('ruiqurm','123456789')")
            cursor.execute("INSERT INTO USER(username,phone) VALUES('a','987654321')")
            cursor.execute("INSERT INTO USER(username,phone) VALUES('b','222222222')")
            cursor.execute("CREATE TABLE IF NOT EXISTS BALANCE (id INTEGER REFERENCES USER(id),"
                           "month integer,"
                           "fee FLOAT);")
            cursor.execute("INSERT INTO BALANCE(id,month,fee) VALUES(1,1,100)")
            cursor.execute("INSERT INTO BALANCE(id,month,fee) VALUES(1,2,200)")
            cursor.execute("INSERT INTO BALANCE(id,month,fee) VALUES(1,3,300)")
            cursor.execute("INSERT INTO BALANCE(id,month,fee) VALUES(1,4,400)")
            conn.commit()
            print("[数据库脚本测试]")
            print("   [测试'3月账单']", end='')
            path = "{}/script/database.sam".format("/".join(__file__.split("/")[:-1]))
            with MockTerminal(path, "ruiqurm") as (write, proc):
                write("3月账单\n")
                proc.wait()
                result = proc.stdout.read()
            self.assertTrue(str(result).find("300") != -1)

            print("pass\n   [测试'4月账单']", end='')
            with MockTerminal(path, "ruiqurm") as (write, proc):
                write("4月账单\n")
                proc.wait()
                result = proc.stdout.read()
            self.assertTrue(str(result).find("400") != -1)

            print("pass\n   [测试'5月账单']", end='')
            with MockTerminal(path, "ruiqurm") as (write, proc):
                write("5月账单\n")
                proc.wait()
                result = proc.stdout.read()
            self.assertTrue(str(result).find("没有找到") != -1)

            print("pass\n   [测试'查询a的id']", end='')
            with MockTerminal(path, "a") as (write, proc):
                write("id\n")
                proc.wait()
                result = proc.stdout.read()
            self.assertTrue(str(result).find("2") != -1)

            print("pass\n   [测试'超时']", end='')
            with MockTerminal(path, "ruiqurm") as (write, proc):
                proc.wait()
                result = proc.stdout.read()
            self.assertTrue(str(result).find("听不清楚。结束通话") != -1)
            print("pass\n", end='')
        finally:
            if os.path.exists("test.db"):
                os.remove("test.db")
    def test_simple_sam(self):
        """
        测试 script/simple.sam
        """
        path = "{}/script/simple.sam".format("/".join(__file__.split("/")[:-1]))
        print("[simple脚本测试]")
        # 测试账单
        print("   [测试输入'我的账单']", end='')
        with MockTerminal(path, "ruiqurm","100") as (write, proc):
            write("我的账单\n")
            proc.wait()
            result = proc.stdout.read()
        self.assertTrue(str(result).find("ruiqurm") != -1)
        self.assertTrue(str(result).find("100") != -1)

        print("pass\n   [测试'投诉']", end='')
        with MockTerminal(path, "ruiqurm","100") as (write, proc):
            write("投诉aaaaaaaaaaaaaa\n")
            time.sleep(1)
            proc.wait()
            result = proc.stdout.read()
        self.assertTrue(str(result).find("您的投诉为") != -1)
        print("pass\n", end='')
if __name__ == '__main__':
    unittest.main()
