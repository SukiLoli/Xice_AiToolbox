import sys
import json
import subprocess
import tempfile
import os

CONFIG_FILE = "config.json"
PYTHON_EXECUTION_TIMEOUT = 10 # 默认超时时间
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        PYTHON_EXECUTION_TIMEOUT = config_data.get("code_sandbox_python_timeout", 10)
except Exception:
    print(f"警告: 无法从 {CONFIG_FILE} 加载 'code_sandbox_python_timeout'。将使用默认值 {PYTHON_EXECUTION_TIMEOUT}s。", file=sys.stderr)


def run_code_sandbox(params_json_str: str):
    """
    在“沙盒”中执行代码。目前主要支持Python。
    JSON参数: '{"language": "python", "code": "print(\\"hello\\")"}'
    """
    try:
        params = json.loads(params_json_str)
        language = params.get("language", "").lower()
        code = params.get("code", "")

        if not language or not code:
            return json.dumps({"status": "错误", "output": "", "error": "请求JSON必须包含 'language' 和 'code' 字段。"})

        if language == "python":
            # 创建一个临时文件来执行Python代码
            # 这比直接用 -c 更容易管理复杂脚本和捕获输出，但仍不安全
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as tmp_script:
                tmp_script.write(code)
                script_path = tmp_script.name
            
            try:
                # 使用与当前环境相同的Python解释器
                # 限制：无法轻易限制网络、文件系统访问等。
                process = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=PYTHON_EXECUTION_TIMEOUT,
                    encoding='utf-8',
                    errors='replace' # 处理非UTF-8输出
                )
                output = process.stdout
                error_output = process.stderr
                
                # AI有时会在Python代码中打印到stderr作为调试信息，不一定是真正的错误
                # 所以我们将两者都返回
                if process.returncode == 0:
                    return json.dumps({"status": "成功", "stdout": output, "stderr": error_output, "return_code": process.returncode})
                else:
                    return json.dumps({"status": "执行失败", "stdout": output, "stderr": error_output, "return_code": process.returncode})

            except subprocess.TimeoutExpired:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"代码执行超时 ({PYTHON_EXECUTION_TIMEOUT}秒)。", "return_code": -1})
            except Exception as e:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"执行Python代码时发生内部错误: {str(e)}", "return_code": -1})
            finally:
                if os.path.exists(script_path):
                    os.remove(script_path)
        
        elif language == "javascript_node": # 实验性: Node.js
             # 需要Node.js安装在系统路径中
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.js', encoding='utf-8') as tmp_script:
                tmp_script.write(code)
                script_path = tmp_script.name
            try:
                process = subprocess.run(
                    ["node", script_path],
                    capture_output=True,
                    text=True,
                    timeout=PYTHON_EXECUTION_TIMEOUT, # 复用超时设置
                    encoding='utf-8',
                    errors='replace'
                )
                output = process.stdout
                error_output = process.stderr
                if process.returncode == 0:
                    return json.dumps({"status": "成功", "stdout": output, "stderr": error_output, "return_code": process.returncode})
                else:
                    return json.dumps({"status": "执行失败", "stdout": output, "stderr": error_output, "return_code": process.returncode})
            except FileNotFoundError: # node命令未找到
                 return json.dumps({"status": "错误", "stdout": "", "stderr": "Node.js解释器未找到。无法执行JavaScript代码。", "return_code": -1})
            except subprocess.TimeoutExpired:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"JavaScript代码执行超时 ({PYTHON_EXECUTION_TIMEOUT}秒)。", "return_code": -1})
            except Exception as e:
                return json.dumps({"status": "错误", "stdout": "", "stderr": f"执行JavaScript代码时发生内部错误: {str(e)}", "return_code": -1})
            finally:
                if os.path.exists(script_path):
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
        print("错误：代码沙盒插件需要JSON参数。")
        print("例如：'{\"language\": \"python\", \"code\": \"print(1+1)\"}'")
    sys.stdout.flush()