import os
import paramiko
import logging
from stat import S_ISDIR

class SFTPClient:
    def __init__(self, host=None, port=22, username=None, password=None, timeout=10):
        """
        初始化SFTP客户端
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ssh = None
        self.sftp = None

    def connect(self):
        """
        建立SSH连接并打开SFTP会话
        """
        try:
            self.ssh = paramiko.SSHClient()
            # 自动添加未在known_hosts中的主机密钥
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout
            )
            self.sftp = self.ssh.open_sftp()
            logging.info(f"sftp: 连接 {self.host} 成功")
        except Exception as e:
            logging.error(f"sftp: 连接 {self.host} 失败: {e}")
            self.sftp = None
            self.ssh = None

    def close(self):
        """
        关闭SFTP会话和SSH连接
        """
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        logging.info(f"sftp: 关闭连接 {self.host}")

    def _is_dir(self, path):
        """
        判断远程路径是否为目录
        """
        # 获取文件状态信息
        try:
            return S_ISDIR(self.sftp.stat(path).st_mode)
        except IOError:
            return False  # 路径不存在或其他错误，认为不是目录


    def _exists(self, path):
        """
        判断远程路径是否存在（通过抛出异常来判断路径是否存在）
        """
        try:
            self.sftp.stat(path)
            return True
        except IOError:
            return False

    def _mkdir_recursive(self, remote_directory):
        """
        递归创建远程目录（如果不存在）
        """
        dirs = []
        head = remote_directory
        while len(head) > 1:
            if self._exists(head):
                break
            dirs.append(head)
            # 获取上级目录
            head, _ = os.path.split(head)
        # 从最后一级开始创建目录
        for dir_path in reversed(dirs):
            try:
                self.sftp.mkdir(dir_path)
                logging.info(f"创建远程目录: {dir_path}")
            except Exception as e:
                logging.warning(f"目录创建失败或已存在: {dir_path}，原因: {e}")

    def upload(self, local_path, remote_path):
        """
        上传本地文件或目录到远程
        """
        try:
            if os.path.isfile(local_path):
                self._upload_file(local_path, remote_path)
            elif os.path.isdir(local_path):
                self._upload_dir(local_path, remote_path)
            else:
                logging.error(f"本地路径不存在: {local_path}")
                return False
            return True
        except Exception as e:
            logging.error(f"上传失败: {e}")
            return False

    def _upload_file(self, local_file, remote_file):
        """
        上传单个文件，自动创建远程目录（如果不存在）
        """
        try:
            remote_dir = os.path.dirname(remote_file)
            if not self._exists(remote_dir):
                self._mkdir_recursive(remote_dir)
            self.sftp.put(local_file, remote_file)
            logging.info(f"上传文件: {local_file} -> {remote_file}")
        except Exception as e:
            logging.error(f"上传文件失败: {local_file} -> {remote_file}，错误: {e}")

    def _upload_dir(self, local_dir, remote_dir):
        """
        递归上传目录及其内容
        """
        try:
            if not self._exists(remote_dir):
                self._mkdir_recursive(remote_dir)
            # 遍历本地目录，上传所有文件和子目录
            for root, dirs, files in os.walk(local_dir):

                rel_path = os.path.relpath(root, local_dir).replace("\\", "/")
                remote_root = remote_dir.rstrip("/") + "/" + rel_path if rel_path != "." else remote_dir
                if not self._exists(remote_root):
                    self._mkdir_recursive(remote_root)
                for file in files:
                    local_file = os.path.join(root, file)
                    remote_file = remote_root + "/" + file
                    try:
                        self.sftp.put(local_file, remote_file)
                        logging.info(f"上传文件: {local_file} -> {remote_file}")
                    except Exception as e:
                        logging.error(f"上传文件失败: {local_file} -> {remote_file}，错误: {e}")
        except Exception as e:
            logging.error(f"上传目录失败: {local_dir} -> {remote_dir}，错误: {e}")

    def download(self, remote_path, local_path):
        """
        下载远程文件或目录到本地
        :param remote_path: 远程文件或目录路径
        :param local_path: 本地目标路径
        """
        try:
            if self._is_dir(remote_path):
                self._download_dir(remote_path, local_path)
            else:
                self._download_file(remote_path, local_path)
        except Exception as e:
            logging.error(f"下载失败: {e}")

    def _download_file(self, remote_file, local_file):
        """
        下载单个远程文件
        :param remote_file: 远程文件路径
        :param local_file: 本地文件路径
        """
        try:
            local_dir = os.path.dirname(local_file)
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            self.sftp.get(remote_file, local_file)
            logging.info(f"下载文件: {remote_file} -> {local_file}")
        except Exception as e:
            logging.error(f"下载文件失败: {remote_file} -> {local_file}，错误: {e}")

    def _download_dir(self, remote_dir, local_dir):
        """
        递归下载远程目录及其内容
        :param remote_dir: 远程目录路径
        :param local_dir: 本地目录路径
        """
        try:
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            for item in self.sftp.listdir_attr(remote_dir):
                remote_item = remote_dir + "/" + item.filename
                local_item = os.path.join(local_dir, item.filename)
                if S_ISDIR(item.st_mode):
                    self._download_dir(remote_item, local_item)
                else:
                    self._download_file(remote_item, local_item)
        except Exception as e:
            logging.error(f"下载目录失败: {remote_dir} -> {local_dir}，错误: {e}")
