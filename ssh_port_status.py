import socket
import time
import logging

class SSHStatusChecker:
    def __init__(self, host, port=22, timeout=1):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _check_ssh_port(self):
        """
        检查SSH端口是否开放。
        """
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                return True
        except Exception:
            return False

    def wait_for_disconnect(self, max_wait=30, failure_threshold=3):
        """
        等待 SSH 从连接 ➝ 断开，要求连续失败 failure_threshold 次判定断开。
        """
        logging.info(f"ssh_port: {self.host} 等待 SSH 断开（最大等待 {max_wait} s, 连续失败阈值 {failure_threshold})...")
        start = time.time()
        consecutive_failures = 0

        while time.time() - start < max_wait:
            if not self._check_ssh_port():
                consecutive_failures += 1
                logging.info(f"ssh_port: {self.host} SSH 端口不可连接（连续失败 {consecutive_failures}/{failure_threshold})")
                if consecutive_failures >= failure_threshold:
                    logging.info(f"ssh_port: {self.host} SSH 已断开, 控制重启中...")
                    return True
            else:
                if consecutive_failures > 0:
                    logging.info(f"ssh_port: {self.host} SSH 状态恢复，连续失败计数清零")
                consecutive_failures = 0
                logging.info(f"ssh_port: {self.host} SSH 仍连接中，继续等待...")

            time.sleep(1)
        
        logging.error(f"ssh_port: {self.host} 超过 {max_wait}s 仍未断开 SSH")
        return False


    def wait_for_connect(self, max_wait=30, success_threshold=5):
        """
        等待 SSH 从断开 ➝ 连接 要求连续成功 success_threshold 次, 才判断连接成功
        """
        logging.info(f"ssh_port: [{self.host}] 等待 SSH 连接（最大等待 {max_wait}s）...")
        start = time.time()
        consecutive_success = 0

        while time.time() - start < max_wait:
            if self._check_ssh_port():
                consecutive_success += 1
                logging.info(f"ssh_port: [{self.host}] SSH 可连接（{consecutive_success}/{success_threshold}）")
                if consecutive_success >= success_threshold:
                    logging.info(f"ssh_port: [{self.host}] SSH 已连接, 控制器重启完成")
                    return True
            else:
                if consecutive_success > 0:
                    logging.info(f"ssh_port: [{self.host}] SSH 状态波动，计数清零")
                consecutive_success = 0
                logging.info(f"ssh_port: [{self.host}] SSH 不可连接，继续等待...")

            time.sleep(1)
        logging.error(f"ssh_port: [{self.host}] 超过 {max_wait}s 仍未连接 SSH")
        return False
