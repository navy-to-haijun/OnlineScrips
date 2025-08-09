import telnetlib
import logging
import time

class TelnetClient:
    def __init__(self, host, port=23, username=None, password=None, timeout=10):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.tn = None

    def connect(self):
        try:
            logging.info(f"Telnet: 正在连接 {self.host}:{self.port} ...")
            self.tn = telnetlib.Telnet(self.host, self.port, timeout=self.timeout)

            # 登录过程：等待提示并输入用户名和密码
            if self.username:
                self.tn.read_until(b"login:", timeout=self.timeout)
                self.tn.write(self.username.encode('ascii') + b"\n")
            if self.password:
                self.tn.read_until(b"Password: ", timeout=self.timeout)
                self.tn.write(self.password.encode('ascii') + b"\n")

            time.sleep(2)  # 等待 shell 提示出现
            self.tn.read_very_eager()  # 清空 welcome 消息
            logging.info(f"Telnet: 连接 {self.host} 成功")
        except Exception as e:
            logging.error(f"Telnet: 连接 {self.host} 失败: {e}")
            self.tn = None

    def exec_command(self, command):
        if not self.tn:
            logging.error("Telnet: 未连接，无法执行命令")
            return None, None, None
        try:
            logging.info(f"执行命令: {command}")
            self.tn.write(command.encode('ascii') + b"\n")
            time.sleep(1)
            output = self.tn.read_until(b"# ", timeout=self.timeout).decode('utf-8',  errors='ignore')
            # output = self.tn.read_very_eager().decode('utf-8')
            if "# " in output:
                return None, output, None
            else:
                return None, output, "命令执行超时"
            
        except Exception as e:
            logging.error(f"Telnet: 执行命令失败: {e}")
            return None, None, None

    def close(self):
        if self.tn:
            try:
                self.tn.write(b"exit\n")
            except:
                pass
            self.tn.close()
            logging.info(f"Telnet: 关闭连接 {self.host}")
