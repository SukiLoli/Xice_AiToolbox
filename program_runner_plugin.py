import os
import sys
import json
import subprocess
import shlex # 用于安全地分割命令字符串

# 警告：此版本的插件允许AI指定任意工作目录和执行任意命令。
# 这具有极高的安全风险，请仅在完全理解并接受风险的情况下使用。

PROGRAM_EXECUTION_TIMEOUT = 30 # 默认程序执行超时
CONFIG_FILE = "config.json"
try:
    # 尝试定位config.json，首先在脚本同级目录，然后是执行时的当前目录（通常是项目根目录）
    config_path_script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
    config_path_cwd = os.path.join(os.getcwd(), CONFIG_FILE)

    actual_config_path = None
    if os.path.exists(config_path_script_dir):
        actual_config_path = config_path_script_dir
    elif os.path.exists(config_path_cwd):
        actual_config_path = config_path_cwd
    
    if actual_config_path:
        with open(actual_config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            PROGRAM_EXECUTION_TIMEOUT = config_data.get("program_runner_timeout", 30)
            # print(f"调试: 从 {actual_config_path} 加载 program_runner_timeout: {PROGRAM_EXECUTION_TIMEOUT}s", file=sys.stderr)
    else:
        print(f"警告: 配置文件 {CONFIG_FILE} 在 {config_path_script_dir} 或 {config_path_cwd} 未找到。将使用默认 program_runner_timeout 值 {PROGRAM_EXECUTION_TIMEOUT}s。", file=sys.stderr)
except Exception as e:
    print(f"警告: 无法从 config.json 加载 'program_runner_timeout' ({e})。将使用默认值 {PROGRAM_EXECUTION_TIMEOUT}s。", file=sys.stderr)


def run_program_unsafe(params_json_str: str):
    """
    在AI指定的任意工作目录中执行AI指定的任意程序。
    JSON参数: '{"cwd": "C:/path/to/work_dir", "command": "python main.py --arg value"}'
              或者 '{"cwd": "/usr/bin", "command": ["ls", "-l", "/"]}'
    """
    print("警告: 程序运行插件正在以不安全模式运行，允许在AI指定的任意CWD执行任意命令。", file=sys.stderr)
    results = {}
    try:
        params = json.loads(params_json_str)
        cwd_from_ai = params.get("cwd")
        command_input = params.get("command")

        if cwd_from_ai is None:
            cwd_from_ai = ""

        if not isinstance(cwd_from_ai, str):
             return json.dumps({"status": "错误", "message": "'cwd' 必须是一个字符串（可以是空字符串表示当前目录）。"})

        if not command_input:
            return json.dumps({"status": "错误", "message": "请求JSON必须包含 'command'。"})

        # 解析AI提供的CWD
        actual_cwd = None
        try:
            if cwd_from_ai == "":
                actual_cwd = os.getcwd()
                print(f"信息: AI提供的CWD为空，将使用插件的当前工作目录: {actual_cwd}", file=sys.stderr)
            else:
                actual_cwd = os.path.realpath(os.path.expanduser(os.path.expandvars(cwd_from_ai)))
                print(f"信息: AI提供的CWD为 '{cwd_from_ai}', 解析为: {actual_cwd}", file=sys.stderr)
        except Exception as e:
            return json.dumps({"status": "错误", "message": f"解析工作目录 '{cwd_from_ai}' 失败: {str(e)}"})

        if not os.path.exists(actual_cwd):
            return json.dumps({"status": "错误", "message": f"指定的工作目录 '{actual_cwd}' (来自输入: '{cwd_from_ai}') 不存在。请确保路径正确或先创建目录。"})
        if not os.path.isdir(actual_cwd):
            return json.dumps({"status": "错误", "message": f"指定的工作目录 '{actual_cwd}' (来自输入: '{cwd_from_ai}') 不是一个目录。"})


        if isinstance(command_input, str):
            command_list = shlex.split(command_input)
        elif isinstance(command_input, list):
            command_list = command_input
        else:
            return json.dumps({"status": "错误", "message": "'command' 必须是字符串或列表。"})

        if not command_list:
            return json.dumps({"status": "错误", "message": "命令不能为空。"})

        print(f"信息: 准备在CWD '{actual_cwd}' 中执行命令: \"{' '.join(command_list)}\"", file=sys.stderr)

        try:
            process = subprocess.run(
                command_list,
                cwd=actual_cwd,
                capture_output=True,
                text=True,
                timeout=PROGRAM_EXECUTION_TIMEOUT,
                check=False,
                encoding='utf-8',
                errors='replace',
                shell=False
            )
            results["status"] = "成功" if process.returncode == 0 else "执行失败"
            results["return_code"] = process.returncode
            results["stdout"] = process.stdout
            results["stderr"] = process.stderr
        except FileNotFoundError:
            results["status"] = "错误"
            results["message"] = f"命令或程序 '{command_list[0]}' 未找到。请确保它在系统PATH中，或位于工作目录 '{actual_cwd}' 中，或是提供了可执行文件的完整路径。"
            results["return_code"] = -1
        except PermissionError:
            results["status"] = "错误"
            results["message"] = f"权限错误：无法执行命令 '{command_list[0]}' (可能文件不可执行或对工作目录 '{actual_cwd}' 权限不足)。"
            results["return_code"] = -1
        except subprocess.TimeoutExpired:
            results["status"] = "错误"
            results["message"] = f"程序执行超时 ({PROGRAM_EXECUTION_TIMEOUT}秒)。"
            results["return_code"] = -1
        except NotADirectoryError:
            results["status"] = "错误"
            results["message"] = f"工作目录错误：路径 '{actual_cwd}' 在执行时被发现不是一个有效的目录。"
            results["return_code"] = -1
        except Exception as e:
            results["status"] = "错误"
            results["message"] = f"执行程序时发生内部错误: {str(e)}"
            results["return_code"] = -1

        return json.dumps(results, ensure_ascii=False)

    except json.JSONDecodeError:
        return json.dumps({"status": "错误", "message": "输入参数不是有效的JSON字符串。"})
    except Exception as e:
        return json.dumps({"status": "错误", "message": f"程序运行插件发生未知错误: {str(e)}"})

if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_param = sys.argv[1]
        result = run_program_unsafe(json_param)
        print(result)
    else:
        print("错误：程序运行插件（不安全模式）需要JSON参数。")
        print("例如：'{\"cwd\": \"C:/temp/my_script_dir\", \"command\": \"python myscript.py arg1\"}'")
        print("或 '{\"cwd\": \"\", \"command\": [\"echo\", \"Hello from current dir\"]}' (空cwd表示插件脚本的当前目录)")
        print("警告：此模式允许在任意指定CWD执行任意命令，请谨慎使用！")
    sys.stdout.flush()