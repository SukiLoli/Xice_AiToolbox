import subprocess
import os
import sys
import threading
import json
import time
import re

# --- 配置 ---
CONFIG_FILE = "config.json"
NODE_SCRIPT = "proxy_server.js"
# LOG_DIR_BASE = "Interception_log" # 不再需要此行

# --- 全局变量 ---
node_process = None

def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return config_data
    except FileNotFoundError:
        print(f"[Python]错误：配置文件 {CONFIG_FILE} 未找到。")
        return None
    except json.JSONDecodeError:
        print(f"[Python]错误：配置文件 {CONFIG_FILE} 格式无效。")
        return None

def print_colored(text, color_code):
    """在支持ANSI转义的终端打印带颜色的文本"""
    # 检查是否在PyCharm等可能不支持直接ANSI的环境
    if sys.stdout.isatty():
        print(f"\033[{color_code}m{text}\033[0m")
    else:
        print(text)

def strip_ansi_codes(text):
    """移除文本中的ANSI转义码"""
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

def start_node_proxy(config_data):
    """启动Node.js代理服务器"""
    global node_process
    if not config_data:
        print_colored("[Python]无法启动 Node.js 代理，配置加载失败。", "31") # 红色
        return False

    proxy_port = config_data.get("proxy_server_port", 3001)
    show_node_output = config_data.get("show_node_output_in_python", True)

    try:
        # 检查 Node.js 是否安装
        try:
            node_version_result = subprocess.run(["node", "--version"], check=True, capture_output=True, text=True, encoding='utf-8')
            print_colored(f"[Python]检测到 Node.js 版本: {node_version_result.stdout.strip()}", "32")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_colored("[Python]错误：未找到 Node.js。请确保 Node.js 已安装并添加到系统 PATH。", "31")
            print_colored("[Python]你可以从 https://nodejs.org/ 下载并安装 Node.js。", "33")
            return False

        # 检查 package.json 和 node_modules
        if not os.path.exists("package.json"):
            print_colored("[Python]警告: package.json 未找到。", "33")
        elif not os.path.exists("node_modules"):
            print_colored("[Python]警告: node_modules 目录未找到。可能需要安装依赖。", "33")
            if os.path.exists("package-lock.json") or os.path.exists("yarn.lock"): # 更可靠地判断是否需要install
                print_colored("[Python]检测到锁定文件但无 node_modules，建议运行 'npm install' 或 'yarn install'。", "33")

        print_colored(f"[Python]正在启动 Node.js 拦截服务 ({NODE_SCRIPT})...", "36") # 青色
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8" 

        node_process = subprocess.Popen(
            ["node", NODE_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, 
            encoding='utf-8', 
            errors='replace', 
            env=env,
        )
        print_colored(f"[Python]Node.js 拦截服务已启动 (PID: {node_process.pid})。", "32") # 绿色
        print_colored(f"[Python]Node.js 服务应该在端口 {proxy_port} 上监听。", "32")
        print_colored(f"[Python]请确保你的本地AI反代应用将目标请求转发到 http://localhost:{proxy_port}", "33")
        if show_node_output:
            print_colored("--- Node.js 服务日志 ---", "35") # 紫色

        def stream_output(process):
            for line in iter(process.stdout.readline, ''):
                if show_node_output:
                    sys.stdout.write(line) 
                    sys.stdout.flush()

        output_thread = threading.Thread(target=stream_output, args=(node_process,), daemon=True)
        output_thread.start()
        return True

    except FileNotFoundError:
        print_colored(f"[Python]错误：找不到 Node.js 脚本 '{NODE_SCRIPT}'。", "31")
    except Exception as e:
        print_colored(f"[Python]启动 Node.js 代理时发生错误: {e}", "31")
    return False

def stop_node_proxy():
    """停止Node.js代理服务器"""
    global node_process
    if node_process and node_process.poll() is None:
        print_colored("\n[Python]正在停止 Node.js 拦截服务...", "36")
        if sys.platform == "win32":
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(node_process.pid)], check=True, capture_output=True)
                print_colored(f"[Python]已发送 taskkill 命令到 PID {node_process.pid}", "32")
            except Exception as e:
                print_colored(f"[Python]使用 taskkill 关闭 PID {node_process.pid} 失败: {e}. 尝试 terminate()。", "33")
                node_process.terminate()
        else:
            node_process.terminate() 
        
        try:
            node_process.wait(timeout=10) 
            print_colored("[Python]Node.js 拦截服务已停止。", "32")
        except subprocess.TimeoutExpired:
            print_colored("[Python]Node.js 服务未在超时内停止，尝试强制终止。", "33")
            node_process.kill() 
            node_process.wait() 
            print_colored("[Python]Node.js 拦截服务已强制停止。", "32")
        node_process = None


def main():
    print_colored("欢迎使用 Xice_Aitoolbox!", "34") # 蓝色
    print_colored("=========================", "34")

    config = load_config()
    if not config:
        input("[Python]按 Enter 键退出。")
        return

    # 不再需要创建 Interception_log 目录
    # log_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_DIR_BASE)
    # if not os.path.exists(log_dir_path):
    #     try:
    #         os.makedirs(log_dir_path)
    #         print(f"[Python]已创建日志目录: {log_dir_path}")
    #     except OSError as e:
    #         print_colored(f"[Python]无法创建日志目录 {log_dir_path}: {e}", "31")

    if not start_node_proxy(config):
        input("[Python]按 Enter 键退出。")
        return

    print_colored("-------------------------", "35")
    print_colored("Xice_Aitoolbox 正在运行。按 Ctrl+C 退出。", "32")

    try:
        while True:
            if node_process and node_process.poll() is not None:
                print_colored("[Python]Node.js 代理进程似乎已意外终止。", "31")
                print_colored(f"[Python]Node.js 进程返回码: {node_process.returncode}", "31")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print_colored("\n[Python]收到用户中断信号 (Ctrl+C)。", "33")
    finally:
        stop_node_proxy()
        print_colored("Xice_Aitoolbox 已关闭。", "34")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            subprocess.run("chcp 65001 > nul", shell=True, check=False)
        except Exception:
            pass
    main()