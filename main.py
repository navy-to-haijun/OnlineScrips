import yaml
import logging
import os
from ssh_client import SSHClient
from telnet_client import TelnetClient
from sftp_client import SFTPClient
from ssh_port_status import SSHStatusChecker
from datetime import datetime

def init_logger(logfile='run.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(logfile, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def run_commands(client, commands, host):
    for cmd_info in commands:
        cmd = cmd_info['cmd']
        check = cmd_info.get('check', None)

        if isinstance(client, SSHClient):
            _, out, err = client.exec_command(cmd)
            output = out if out else ""
            error = err if err else ""
        else:
            _, out, err = client.exec_command(cmd)
            output = out if out else ""
            error = err if err else ""
        # 输出命令结果
        if output.strip():
            logging.info(f"[{host}] 输出:{output.strip()}")
        if error.strip():
            logging.warning(f"[{host}] 错误:{error.strip()}")
            return False
        # 检查输出
        if check and check not in output:
            logging.warning(f"[{host}] 命令 `{cmd}` 未匹配 `{check}`")
            return False
        else:
            logging.info(f"[{host}] 命令 `{cmd}` 执行成功")
    
    return True

def load_config(path='config.yaml'):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 初始化logger
    init_logger(f"run_log_{timestamp}.log")
    # 加载yaml配置文件
    config = load_config()
    #获取登录方式
    login_method = config.get('login_method', 'ssh').lower()
    hosts = config['hosts']
    port = config.get('port', 22 if login_method == 'ssh' else 23)
    logging.info(f"使用登录方式: {login_method}, 端口: {port}")
    username = config['username']
    password = config['password']

    # 获取上传文件配置
    upfile_config = config.get('upfile', {})
    upload_enabled = upfile_config.get('upload_enabled', False)
    local_path = upfile_config.get('local_path', './upfiles')
    remote_path = upfile_config.get('remote_path', '/root')
    # 遍历主机列表
    for host in hosts:
        last_status = True
        print("\n\n")

        # 上传文件(local_path存在并不为空、upload_enabledwe is True)
        if upload_enabled and os.path.exists(local_path) and os.listdir(local_path):
            logging.info(f"--------开始上传文件到控制器: {host}--------")
            logging.info(f"本地路径: {local_path}, 远程路径: {remote_path}")
            client = SFTPClient(host = host, username = username, password = password)
            client.connect()
            if client.sftp:
                # 遍历local_path的一级目录
                for item in os.listdir(local_path):
                    local_item_path = os.path.join(local_path, item)
                    remote_item_path = os.path.join(remote_path, item).replace("\\", "/")
                    # 上传
                    ret = client.upload(local_item_path, remote_item_path)
                    # 判断文件是否全部上传成功
                    last_status = last_status and ret
            else:
                logging.error(f"无法连接到 {host} 的 SFTP 服务")
                continue

            client.close()
        else:
            logging.info(f"本地上传路径 {local_path} 不存在 or 为空 or 禁用文件上传，跳过上传步骤")
        

        # 获取执行任务命令
        commands = config.get('taskcommands', [])
        # 有任务命令并且上一步执行成功（上传文件）
        if  commands and len(commands) > 0 and last_status:
            logging.info(f"--------开始执行任务命令到控制器: {host}--------")
            logging.info(f"{host}, 登录方式: {login_method}")

            if login_method == 'ssh':
                client = SSHClient(host, port, username, password)
                client.connect()
                if client.client:
                    ret = run_commands(client, commands, host)
                    last_status = last_status and ret
                client.close()
            elif login_method == 'telnet':
                client = TelnetClient(host, port, username, password)
                client.connect()
                if client.tn:
                    ret = run_commands(client, commands, host)
                    last_status = last_status and ret
                client.close()
            else:
                logging.error(f"不支持的登录方式: {login_method}")
            
            if not last_status:
                logging.warning(f"前面步骤执行失败，终止 {host} 的后续操作")
                break
        else:
            logging.warning("未配置任何任务命令, 跳过执行task 命令步骤")
        

        # 检测重启
        # 获取检测重启的参数
        reboot_params = config.get('reboot_params', {})
        reboot_enable = reboot_params.get('enable', False)
        wait_for_disconnect = reboot_params.get('wait_for_disconnect', 60)
        disconnect_failure_threshold = reboot_params.get('disconnect_failure_threshold', 3)
        wait_for_connect = reboot_params.get('wait_for_connect', 60)
        connect_success_threshold = reboot_params.get('connect_success_threshold', 3)
        # 判断是否需要重启
        if reboot_enable and last_status:
            logging.info(f"--------开始检测控制器 {host} 重启状态--------")
            port_checker = SSHStatusChecker(host)
            # 等待断开
            ret = port_checker.wait_for_disconnect(max_wait=wait_for_disconnect, failure_threshold=disconnect_failure_threshold)
            last_status = last_status and ret
            if not last_status:
                logging.warning(f"控制器 {host} 在等待断开过程中失败，终止后续操作")
                break
            # 等待连接
            ret = port_checker.wait_for_connect(max_wait=wait_for_connect, success_threshold=connect_success_threshold)
            last_status = last_status and ret
            if not last_status:
                logging.warning(f"控制器 {host} 在等待连接过程中失败，终止后续操作")
                break
        else:    
            logging.warning(f"未启用重启检测，跳过重启检测步骤")


        # 执行检测命令
        checkcommands = config.get('checkcommands', [])
        if last_status and checkcommands and len(checkcommands) > 0:
            logging.info(f"--------开始执行检测命令到控制器: {host}--------")
            if login_method == 'ssh':
                client = SSHClient(host, port, username, password)
                client.connect()
                if client.client:
                    ret = run_commands(client, checkcommands, host)
                    last_status = last_status and ret
                client.close()
            elif login_method == 'telnet':
                client = TelnetClient(host, port, username, password)
                client.connect()
                if client.tn:
                    ret = run_commands(client, checkcommands, host)
                    last_status = last_status and ret
                client.close()
            else:
                logging.error(f"不支持的登录方式: {login_method}")

            if not last_status:
                logging.warning(f"前面步骤执行失败，终止 {host} 的后续操作")
                break
        else:
            logging.warning("未配置任何检测命令, 跳过执行检测命令步骤")

        logging.info(f"################控制器 {host} 所有步骤执行成功################")
        
        

if __name__ == "__main__":
    main()
    # 按任意键退出
    logging.info("退出操作，按任意键退出...")
    input("按任意键退出...")
