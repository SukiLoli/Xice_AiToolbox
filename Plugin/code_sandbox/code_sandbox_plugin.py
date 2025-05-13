import sys
import json
import subprocess
import tempfile
import os

# 默认配置
DEFAULT_PYTHON_EXECUTION_TIMEOUT = 10
DEFAULT_NODEJS_EXECUTION_TIMEOUT = 10

# 加载插件自身配置
python_execution_timeout = DEFAULT_PYTHON_EXECUTION_TIMEOUT
nodejs_execution_timeout = DEFAULT_NODEJS_EXECUTION_TIMEOUT
try:
    plugin_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(plugin_config_path):
        with open(plugin_config_path, 'r', encoding='utf-8') as f:
            plugin_config_data = json.load(f)
            psc = plugin_config_data.get("plugin_specific_config", {})
            python_execution_timeout = psc.get("python_execution_timeout_seconds", DEFAULT_PYTHON_EXECUTION_TIMEOUT)
            nodejs_execution_timeout = psc.get("nodejs_execution_timeout_seconds", DEFAULT_NODEJS_EXECUTION_TIMEOUT)
except Exception as e:
    print(f"警告: 读取插件 code_sandbox 配置失败: {e}. 将使用默认超时值。", file=sys.stderr)


def run_code_sandbox(params_json_str: str):
    """
    在“沙盒”中执行代码。目前主要支持Python和Node.js (实验性)。
    """
    try:
        params = json.loads(params_json_str)
        language = params.get("language", "").lower()
        code = params.get("code", "")

        if not language or not code:
            return json.dumps({"status": "错误", "output": "", "error": "请求JSON必须包含 'language' 和 'code' 字段。"})

        if language == "python":
            script_path = ""
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as tmp_script:
                    tmp_script.write(code)
                    script_path = tmp_script.name
                
                process = subprocess.run(
                    [sys.executable, script_path], # 使用当前Python解释器
                    capture_output=True,
                    text=True,
                    timeout=python_execution_timeout,
                    encoding='utf-8',
                    errors='replace'
                )
                if process.returncode == 0:
                    return json.dumps({"status": "成功", "stdout": process.stdout, "stderr": process.stderr, "return_code": process.returncode})
                else:
                    return json.dumps({"status": "执行失败", "stdout": process.stdout, "stderr": process.stderr, "return_code": process.returncode})
            except subprocess.TimeoutExpired:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"Python代码执行超时 ({python_execution_timeout}秒)。", "return_code": -1})
            except Exception as e:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"执行Python代码时发生内部错误: {str(e)}", "return_code": -1})
            finally:
                if script_path and os.path.exists(script_path):
                    os.remove(script_path)
        
        elif language == "javascript_node":
            script_path = ""
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.js', encoding='utf-8') as tmp_script:
                    tmp_script.write(code)
                    script_path = tmp_script.name
                
                process = subprocess.run(
                    ["node", script_path],
                    capture_output=True,
                    text=True,
                    timeout=nodejs_execution_timeout,
                    encoding='utf-8',
                    errors='replace'
                )
                if process.returncode == 0:
                    return json.dumps({"status": "成功", "stdout": process.stdout, "stderr": process.stderr, "return_code": process.returncode})
                else:
                    return json.dumps({"status": "执行失败", "stdout": process.stdout, "stderr": process.stderr, "return_code": process.returncode})
            except FileNotFoundError:
                 return json.dumps({"status": "错误", "stdout": "", "stderr": "Node.js解释器 (node) 未找到。无法执行JavaScript代码。", "return_code": -1})
            except subprocess.TimeoutExpired:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"JavaScript代码执行超时 ({nodejs_execution_timeout}秒)。", "return_code": -1})
            except Exception as e:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"执行JavaScript代码时发生内部错误: {str(e)}", "return_code": -1})
            finally:
                if script_path and os.path.exists(script_path):
                    os.remove(script_path)
        else:
            return json.dumps({"status": "错误", "output": "", "error": f"不支持的语言: '{language}'. 目前仅支持 'python' 和 'javascript_node' (实验性)。"})

    except json.JSONDecodeError:
        return json.dumps({"status": "错误", "output": "", "error": "输入参数不是有效的JSON字符串。"})
    except Exception as e:
        return json.dumps({"status": "错误", "output": "", "error": f"代码沙盒插件发生未知错误: {str(e)}"})

if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_param = sys.argv[1]
        result = run_code_sandbox(json_param)
        print(result)
    else:
        print(json.dumps({"status": "错误", "message": "代码沙盒插件需要JSON参数。"}))
    sys.stdout.flush()
