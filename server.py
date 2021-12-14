import os
import socket
import subprocess
import sys
import time

from samoyed.utils import make_pipe,get_pipe_read_end
import threading
HOST = '127.0.0.1'
PORT = 65431

def handle_request(conn):
    username = conn.recv(11)
    username = username.decode()
    command = ["./venv/bin/python","simple2.sam.py", username]
    fd = os.open("/tmp/test_pipe", os.O_RDWR)
    sproc = subprocess.Popen(command,stdin=fd,stdout=subprocess.PIPE)
    conn.sendall("ok".encode())
    while sproc.poll() is None:
        print(f"check={sproc.poll()}")
        data = conn.recv(128)
        data = data.decode()
        os.write(fd,data.encode())
        data = sproc.stdout.read(1024)
        conn.sendall(data)
        time.sleep(0.2)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    while True:
        conn, addr = s.accept()
        print('Connected by', addr)
        t = threading.Thread(target=handle_request,args=(conn,))
        t.start()

# # command = ["./venv/bin/python","simple2.sam.py", "ruiqurm"]
# fd = os.open("/tmp/test_pipe", )
# # sproc = subprocess.Popen(command,stdin=fd)
# time.sleep(0.1)
# os.write(fd,"查询".encode())
# # sproc.wait()

