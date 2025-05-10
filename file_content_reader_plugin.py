import os
import sys

# 配置项
MAX_FILE_SIZE_MB = 5  # 限制读取的最大文件大小 (MB)
MAX_OUTPUT_CHARS = 15000 # 限制返回给AI的文本长度，防止过长

def read_file_content(file_path: str):
    """
    读取指定路径的文件内容。
    """
    try:
        # 安全性：解析真实路径，防止 ../../ 之类的路径逃逸到非预期目录
        # 在更严格的场景下，这里应该有白名单或更强的路径限制
        resolved_path = os.path.realpath(file_path)

        # 简单安全检查：确保路径存在且是一个文件
        if not os.path.exists(resolved_path):
            return f"错误：文件路径 '{file_path}' (解析为 '{resolved_path}') 不存在。"
        if not os.path.isfile(resolved_path):
            return f"错误：路径 '{file_path}' (解析为 '{resolved_path}') 不是一个文件。"

        # 检查文件大小
        file_size_bytes = os.path.getsize(resolved_path)
        if file_size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
            return f"错误：文件 '{resolved_path}' 大小为 {file_size_bytes / (1024*1024):.2f} MB，超过了 {MAX_FILE_SIZE_MB} MB 的限制。"

        # 尝试以 UTF-8 读取，如果失败，尝试常见的编码
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
            except Exception as e: # 其他可能的打开文件错误
                return f"读取文件 '{resolved_path}' 时发生错误 (尝试编码 {enc}): {str(e)}"
        
        if content is None:
            return f"错误：无法使用常用编码 (UTF-8, GBK, GB2312, Latin-1, ISO-8859-1) 解码文件 '{resolved_path}'。文件可能是二进制文件或使用了非常见编码。"

        output = f"[文件路径]: {resolved_path}\n"
        output += f"[文件编码 (尝试检测)]: {detected_encoding or '未知'}\n"
        output += f"[文件大小]: {file_size_bytes / 1024:.2f} KB\n\n"
        
        output += "[文件内容]:\n"
        if len(content) > MAX_OUTPUT_CHARS:
            output += content[:MAX_OUTPUT_CHARS] + f"\n\n[内容过长，已截断至 {MAX_OUTPUT_CHARS} 字符...]"
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