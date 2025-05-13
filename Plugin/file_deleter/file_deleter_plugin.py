import os
import sys
import json
try:
    from send2trash import send2trash
except ImportError:
    def send2trash(paths): # type: ignore
        raise ImportError("send2trash库未安装。请运行 'pip install send2trash' 来启用文件删除到回收站的功能。")

# 加载根目录的全局配置以获取路径白名单
ROOT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config.json")
ALLOWED_BASE_PATHS = []
try:
    if os.path.exists(ROOT_CONFIG_FILE):
        with open(ROOT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            root_config_data = json.load(f)
            raw_paths = root_config_data.get("file_operations_allowed_base_paths", [])
            for p in raw_paths:
                ALLOWED_BASE_PATHS.append(os.path.realpath(p))
    if not ALLOWED_BASE_PATHS: # 如果根配置文件没找到或没配置
        print(f"警告: 无法从根 {ROOT_CONFIG_FILE} 加载 'file_operations_allowed_base_paths'，或列表为空。文件删除插件将非常受限或不安全。", file=sys.stderr)
        # 作为一个极端的后备，可以设置一个非常受限的默认值，或者干脆不允许操作
        # ALLOWED_BASE_PATHS = [os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "safely_deletable_files_fallback"))]
except Exception as e:
    print(f"警告: 从根 {ROOT_CONFIG_FILE} 加载 'file_operations_allowed_base_paths' 出错: {e}。文件删除插件可能不安全或无法工作。", file=sys.stderr)


def is_path_allowed(target_path: str) -> bool:
    if not ALLOWED_BASE_PATHS:
        print("错误：未配置允许的文件操作基础路径 (file_operations_allowed_base_paths)。拒绝操作。", file=sys.stderr)
        return False
    
    try:
        resolved_target_path = os.path.realpath(target_path)
    except Exception as e:
        print(f"警告: 解析路径 '{target_path}' 时出错: {e}。拒绝操作。", file=sys.stderr)
        return False
        
    if resolved_target_path in ALLOWED_BASE_PATHS:
        print(f"警告: 禁止删除配置的基础白名单路径本身: '{resolved_target_path}'。拒绝操作。", file=sys.stderr)
        return False

    for allowed_base in ALLOWED_BASE_PATHS:
        # 检查 resolved_target_path 是否在 allowed_base 之下
        if os.path.commonpath([resolved_target_path, allowed_base]) == allowed_base:
            # 确保它不是 allowed_base 本身，并且确实是一个子路径
            if resolved_target_path != allowed_base:
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
        
        # 再次确认（理论上 is_path_allowed 已处理）
        if resolved_path in ALLOWED_BASE_PATHS:
             return json.dumps({"status": "失败", "message": f"安全限制：不允许删除配置的根白名单目录 '{resolved_path}'。"})

        send2trash(resolved_path)
        return json.dumps({"status": "成功", "message": f"路径 '{resolved_path}' 已移至回收站。"})

    except ImportError as e: 
        return json.dumps({"status": "错误", "message": str(e)})
    except Exception as e:
        return json.dumps({"status": "错误", "message": f"删除路径 '{path_to_delete}' 时发生错误: {str(e)}"})

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path_param = sys.argv[1]
        result = delete_to_trash(path_param)
        print(result)
    else:
        print(json.dumps({"status": "错误", "message": "文件删除插件需要一个文件或文件夹路径作为参数。"}))
    sys.stdout.flush()
