import paramiko
import logging

class SSHClient:
    def __init__(self, host, port=22, username=None, password=None, timeout=10):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = None

    def connect(self):
        self.client = paramiko.SSHClient()
        # 自动添加主机密钥
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout
            )
            logging.info(f"SSH: 连接 {self.host} 成功")
        except Exception as e:
            logging.error(f"SSH: 连接 {self.host} 失败: {e}")
            self.client = None

    def exec_command(self, command):
        if not self.client:
            logging.error("SSH: 未连接，无法执行命令")
            return None, None, None
        try:
            logging.info(f"执行命令 :{command}")
            stdin, stdout, stderr = self.client.exec_command(command)
            out = stdout.read().decode()
            err = stderr.read().decode()
            return stdin, out, err
        except Exception as e:
            logging.error(f"SSH: 执行命令失败: {e}")
            return None, None, None

    def close(self):
        if self.client:
            self.client.close()
            logging.info(f"SSH: 关闭连接 {self.host}")


