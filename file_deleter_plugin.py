import os
import sys
import json
try:
    from send2trash import send2trash # type: ignore
except ImportError:
    # 提供一个虚拟的 send2trash 函数，如果库未安装，插件将无法工作但不会在导入时崩溃
    def send2trash(paths): # type: ignore
        raise ImportError("send2trash库未安装。请运行 'pip install send2trash' 来启用文件删除到回收站的功能。")

CONFIG_FILE = "config.json"
ALLOWED_BASE_PATHS = []
try:
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        raw_paths = config_data.get("file_operations_allowed_base_paths", [])
        for p in raw_paths:
            ALLOWED_BASE_PATHS.append(os.path.realpath(p))
except Exception:
    print(f"警告: 无法从 {CONFIG_FILE} 加载 'file_operations_allowed_base_paths'。文件删除插件可能不安全或无法工作。", file=sys.stderr)
    ALLOWED_BASE_PATHS = [os.path.realpath("./safely_deletable_files")]


def is_path_allowed(target_path: str, is_dir_check=False) -> bool:
    if not ALLOWED_BASE_PATHS:
        print("错误：未配置允许的文件操作基础路径 (file_operations_allowed_base_paths)。拒绝操作。", file=sys.stderr)
        return False
    resolved_target_path = os.path.realpath(target_path)
    
    # 重要：不允许删除基础白名单路径本身
    if resolved_target_path in ALLOWED_BASE_PATHS:
        print(f"警告: 禁止删除配置的基础白名单路径本身: '{resolved_target_path}'。拒绝操作。", file=sys.stderr)
        return False

    for allowed_base in ALLOWED_BASE_PATHS:
        if resolved_target_path.startswith(allowed_base + os.sep): # 必须是子目录或文件
            # 进一步检查，确保 target_path 的确在 allowed_base 之下
            relative_path = os.path.relpath(resolved_target_path, allowed_base)
            if not relative_path.startswith(".."):
                return True
    print(f"警告: 路径 '{target_path}' (解析为 '{resolved_target_path}') 不在任何允许的基础路径的子目录内: {ALLOWED_BASE_PATHS}。拒绝操作。", file=sys.stderr)
    return False

def delete_to_trash(path_to_delete: str):
    """
    将指定的文件或文件夹移动到回收站。
    """
    try:
        if not path_to_delete:
            return json.dumps({"status": "错误", "message": "未提供要删除的路径。"})

        if not is_path_allowed(path_to_delete):
            return json.dumps({"status": "失败", "message": f"路径 '{path_to_delete}' 未被授权进行删除操作。"})

        resolved_path = os.path.realpath(path_to_delete)

        if not os.path.exists(resolved_path):
            return json.dumps({"status": "失败", "message": f"路径 '{resolved_path}' 不存在，无法删除。"})
        
        # 再次确认，不允许删除配置的根白名单目录本身
        if resolved_path in ALLOWED_BASE_PATHS:
             return json.dumps({"status": "失败", "message": f"安全限制：不允许删除配置的根白名单目录 '{resolved_path}'。"})

        send2trash(resolved_path)
        return json.dumps({"status": "成功", "message": f"路径 '{resolved_path}' 已移至回收站。"})

    except ImportError as e: # send2trash 未安装
        return json.dumps({"status": "错误", "message": str(e)})
    except Exception as e:
        return json.dumps({"status": "错误", "message": f"删除路径 '{path_to_delete}' 时发生错误: {str(e)}"})

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path_param = sys.argv[1]
        result = delete_to_trash(path_param)
        print(result)
    else:
        print("错误：文件删除插件需要一个文件或文件夹路径作为参数。")
    sys.stdout.flush()