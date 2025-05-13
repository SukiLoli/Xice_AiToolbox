import os
import sys
import json
import subprocess
import shlex

# 默认配置
DEFAULT_PROGRAM_EXECUTION_TIMEOUT = 30
DEFAULT_ALLOW_ARBITRARY = True

# 加载插件自身配置
program_execution_timeout = DEFAULT_PROGRAM_EXECUTION_TIMEOUT
allow_arbitrary_paths_and_commands = DEFAULT_ALLOW_ARBITRARY
try:
    plugin_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(plugin_config_path):
        with open(plugin_config_path, 'r', encoding='utf-8') as f:
            plugin_config_data = json.load(f)
            psc = plugin_config_data.get("plugin_specific_config", {})
            program_execution_timeout = psc.get("program_execution_timeout_seconds", DEFAULT_PROGRAM_EXECUTION_TIMEOUT)
            allow_arbitrary_paths_and_commands = psc.get("allow_arbitrary_paths_and_commands", DEFAULT_ALLOW_ARBITRARY)
    if not allow_arbitrary_paths_and_commands:
         print("严重警告: 程序运行插件 (program_runner) 被配置为不允许任意路径/命令，但其代码逻辑当前是允许的。存在配置与行为不一致的风险！", file=sys.stderr)
except Exception as e:
    print(f"警告: 读取插件 program_runner 配置失败: {e}. 将使用默认值。", file=sys.stderr)


def run_program_unsafe(params_json_str: str):
    """
    在AI指定的任意工作目录中执行AI指定的任意程序。
    """
    if not allow_arbitrary_paths_and_commands:
        return json.dumps({"status": "错误", "message": "插件被配置为不允许任意路径/命令操作。"})

    print("警告: 程序运行插件正在以不安全模式运行，允许在AI指定的任意CWD执行任意命令。", file=sys.stderr)
    results = {}
    try:
        params = json.loads(params_json_str)
        cwd_from_ai = params.get("cwd", None) # cwd 是可选的
        command_input = params.get("command")

        if not command_input:
            return json.dumps({"status": "错误", "message": "请求JSON必须包含 'command'。"})

        actual_cwd = None
        if cwd_from_ai is None or cwd_from_ai == "":
            actual_cwd = os.path.dirname(os.path.abspath(__file__)) # 默认为插件脚本所在目录
            print(f"信息: AI未提供CWD或为空，将使用插件脚本目录: {actual_cwd}", file=sys.stderr)
        elif isinstance(cwd_from_ai, str):
            try:
                actual_cwd = os.path.realpath(os.path.expanduser(os.path.expandvars(cwd_from_ai)))
                print(f"信息: AI提供的CWD为 '{cwd_from_ai}', 解析为: {actual_cwd}", file=sys.stderr)
            except Exception as e:
                return json.dumps({"status": "错误", "message": f"解析工作目录 '{cwd_from_ai}' 失败: {str(e)}"})
        else:
            return json.dumps({"status": "错误", "message": "'cwd' 必须是一个字符串或留空/null。"})

        if not os.path.exists(actual_cwd):
            return json.dumps({"status": "错误", "message": f"指定的工作目录 '{actual_cwd}' 不存在。"})
        if not os.path.isdir(actual_cwd):
            return json.dumps({"status": "错误", "message": f"指定的工作目录 '{actual_cwd}' 不是一个目录。"})

        if isinstance(command_input, str):
            command_list = shlex.split(command_input)
        elif isinstance(command_input, list):
            command_list = command_input
        else:
            return json.dumps({"status": "错误", "message": "'command' 必须是字符串或列表。"})

        if not command_list:
            return json.dumps({"status": "错误", "message": "命令不能为空。"})

        print(f"信息: 准备在CWD '{actual_cwd}' 中执行命令: {command_list}", file=sys.stderr)

        try:
            process = subprocess.run(
                command_list,
                cwd=actual_cwd,
                capture_output=True,
                text=True,
                timeout=program_execution_timeout,
                check=False, 
                encoding='utf-8',
                errors='replace',
                shell=False # 安全起见，通常不使用shell=True除非明确需要且理解风险
            )
            results["status"] = "成功" if process.returncode == 0 else "执行失败"
            results["return_code"] = process.returncode
            results["stdout"] = process.stdout
            results["stderr"] = process.stderr
        except FileNotFoundError:
            results = {"status": "错误", "message": f"命令或程序 '{command_list[0]}' 未找到。", "return_code": -1}
        except PermissionError:
            results = {"status": "错误", "message": f"权限错误：无法执行命令 '{command_list[0]}'", "return_code": -1}
        except subprocess.TimeoutExpired:
            results = {"status": "错误", "message": f"程序执行超时 ({program_execution_timeout}秒)。", "return_code": -1}
        except Exception as e:
            results = {"status": "错误", "message": f"执行程序时发生内部错误: {str(e)}", "return_code": -1}

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
        print(json.dumps({"status": "错误", "message": "程序运行插件需要JSON参数。"}))
        print("警告：此模式允许在任意指定CWD执行任意命令，请谨慎使用！")
    sys.stdout.flush()
