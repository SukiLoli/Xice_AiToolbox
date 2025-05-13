import os
import sys

# 注意：此插件的路径权限由根目录的 config.json 中的 file_operations_allowed_base_paths 控制
# 但此插件本身只是读取，如果未来根配置想对此类只读操作也进行限制，则需要在这里添加逻辑。
# 目前假设其访问的路径是用户已经认可的。

def list_directory(target_path):
    """
    列出指定路径下的文件和文件夹。
    返回一个结构化的字符串描述。
    """
    try:
        resolved_path = os.path.realpath(target_path)

        if not os.path.exists(resolved_path):
            return f"错误：路径 '{target_path}' (解析为 '{resolved_path}') 不存在。"
        if not os.path.isdir(resolved_path):
            return f"错误：路径 '{target_path}' (解析为 '{resolved_path}') 不是一个文件夹。"

        items = os.listdir(resolved_path)
        if not items:
            return f"目录 '{resolved_path}' 为空。"

        files = []
        directories = []
        for item in items:
            item_path = os.path.join(resolved_path, item)
            if os.path.isdir(item_path):
                directories.append(f"[D] {item}")
            else:
                files.append(f"[F] {item}")
        
        output = f"目录 '{resolved_path}' 下的内容：\n"
        if directories:
            output += "子文件夹:\n" + "\n".join(f"  {d}" for d in directories) + "\n"
        if files:
            output += "文件:\n" + "\n".join(f"  {f}" for f in files) + "\n"
        
        return output.strip()

    except PermissionError:
        return f"错误：没有权限访问路径 '{target_path}'。"
    except Exception as e:
        return f"列出目录 '{target_path}' 时发生未知错误: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory_path_param = sys.argv[1]
        result = list_directory(directory_path_param)
        print(result)
    else:
        print("错误：列出目录插件需要一个文件夹路径作为参数。请使用格式：[列出目录]文件夹路径[/列出目录]")
    sys.stdout.flush()
