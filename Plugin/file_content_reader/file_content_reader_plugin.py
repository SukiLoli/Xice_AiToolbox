import os
import sys
import json

# 默认配置值
DEFAULT_MAX_FILE_SIZE_MB = 5
DEFAULT_MAX_OUTPUT_CHARS = 15000

# 加载插件自身配置
max_file_size_mb = DEFAULT_MAX_FILE_SIZE_MB
max_output_chars = DEFAULT_MAX_OUTPUT_CHARS
try:
    # 插件配置在插件目录下
    plugin_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(plugin_config_path):
        with open(plugin_config_path, 'r', encoding='utf-8') as f:
            plugin_config_data = json.load(f)
            max_file_size_mb = plugin_config_data.get("plugin_specific_config", {}).get("max_file_size_mb", DEFAULT_MAX_FILE_SIZE_MB)
            max_output_chars = plugin_config_data.get("plugin_specific_config", {}).get("max_output_chars", DEFAULT_MAX_OUTPUT_CHARS)
except Exception as e:
    print(f"警告: 读取插件 file_content_reader 配置失败: {e}. 将使用默认值。", file=sys.stderr)


def read_file_content(file_path: str):
    """
    读取指定路径的文件内容。
    """
    try:
        resolved_path = os.path.realpath(file_path)

        if not os.path.exists(resolved_path):
            return f"错误：文件路径 '{file_path}' (解析为 '{resolved_path}') 不存在。"
        if not os.path.isfile(resolved_path):
            return f"错误：路径 '{file_path}' (解析为 '{resolved_path}') 不是一个文件。"

        file_size_bytes = os.path.getsize(resolved_path)
        if file_size_bytes > max_file_size_mb * 1024 * 1024:
            return f"错误：文件 '{resolved_path}' 大小为 {file_size_bytes / (1024*1024):.2f} MB，超过了 {max_file_size_mb} MB 的限制。"

        encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'iso-8859-1']
        content = None
        detected_encoding = None

        for enc in encodings_to_try:
            try:
                with open(resolved_path, 'r', encoding=enc) as f:
                    content = f.read()
                detected_encoding = enc
                break
            except UnicodeDecodeError:
                continue
            except Exception: # 其他可能的打开文件错误
                pass # 后面会统一处理 content is None 的情况
        
        if content is None:
            return f"错误：无法使用常用编码 (UTF-8, GBK, GB2312, Latin-1, ISO-8859-1) 解码文件 '{resolved_path}'。文件可能是二进制文件或使用了非常见编码。"

        output = f"[文件路径]: {resolved_path}\n"
        output += f"[文件编码 (尝试检测)]: {detected_encoding or '未知'}\n"
        output += f"[文件大小]: {file_size_bytes / 1024:.2f} KB\n\n"
        
        output += "[文件内容]:\n"
        if len(content) > max_output_chars:
            output += content[:max_output_chars] + f"\n\n[内容过长，已截断至 {max_output_chars} 字符...]"
        else:
            output += content
        
        return output.strip()

    except PermissionError:
        return f"错误：没有权限读取文件 '{file_path}'。"
    except Exception as e:
        return f"读取文件 '{file_path}' 时发生未知错误: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path_param = sys.argv[1]
        result = read_file_content(file_path_param)
        print(result)
    else:
        print("错误：读取文件内容插件需要一个文件路径作为参数。请使用格式：[读取文件]文件路径[/读取文件]")
    sys.stdout.flush()
