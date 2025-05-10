import os
import sys
import json

# 警告：此版本的插件允许AI指定任意系统路径进行项目创建。
# 这具有极高的安全风险，请仅在完全理解并接受风险的情况下使用。
# 强烈建议恢复到使用 config.json 白名单的版本。

# 不再从 config.json 加载白名单路径
# ALLOWED_BASE_PATHS_CONFIG = {} 

def create_project_structure_unsafe(base_path_from_ai: str, structure: dict, current_path_relative_to_base=""):
    """
    递归创建目录和文件。
    base_path_from_ai: AI直接提供的绝对或相对基础路径。
    structure: {'dirname': {'filename': 'content', 'subdir': {...}}, 'file2': 'content2'}
    """
    results = []

    try:
        # 解析AI提供的基础路径
        # 如果是相对路径，它将相对于Xice_Aitoolbox的当前工作目录
        actual_base_path = os.path.realpath(os.path.expanduser(os.path.expandvars(base_path_from_ai)))
    except Exception as e:
        return [{"item": base_path_from_ai, "status": "失败", "message": f"错误：解析基础路径 '{base_path_from_ai}' 失败: {str(e)}"}]


    # 第一次调用时，current_path_relative_to_base为空
    current_full_path_root = os.path.join(actual_base_path, current_path_relative_to_base)

    # 确保基础目录存在（如果AI提供的路径不存在，则尝试创建）
    if not os.path.exists(actual_base_path):
        try:
            print(f"信息: 尝试创建AI指定的基础目录: {actual_base_path}", file=sys.stderr)
            os.makedirs(actual_base_path, exist_ok=True)
            # results.append({"item": actual_base_path, "status": "成功", "message": f"AI指定的基础目录 '{actual_base_path}' 已创建。"})
        except Exception as e:
            return [{"item": actual_base_path, "status": "失败", "message": f"创建AI指定的基础目录 '{actual_base_path}' 失败: {str(e)}"}]
    
    # 确保当前递归的根目录存在
    if current_path_relative_to_base and not os.path.exists(current_full_path_root):
        try:
            os.makedirs(current_full_path_root, exist_ok=True)
        except Exception as e:
            results.append({"item": os.path.join(current_path_relative_to_base, "<directory>"), "status": "失败", "message": f"创建目录 '{current_full_path_root}' 失败: {str(e)}"})
            return results # 如果目录创建失败，则不继续此分支

    for name, item_content in structure.items():
        # 安全性：仍然对文件名/目录名进行基本检查，防止 '..' 和路径分隔符
        # 但这不能阻止AI通过 base_path_from_ai 提供一个危险的顶级路径
        if ".." in name or "/" in name or "\\" in name or not name.strip():
            results.append({"item": name, "status": "失败", "message": "名称非法 (不允许路径分隔符、'..'或空名称)。"})
            continue

        item_path_full = os.path.join(current_full_path_root, name)
        relative_item_display_path = os.path.join(current_path_relative_to_base, name)

        # 由于允许任意路径，路径安全性检查变得复杂且效果有限。
        # resolved_item_path = os.path.realpath(item_path_full)
        # 我们只能依赖Python和操作系统的权限控制。

        if isinstance(item_content, dict): # 是一个子目录
            results.extend(create_project_structure_unsafe(base_path_from_ai, item_content, relative_item_display_path))
        elif isinstance(item_content, str): # 是一个文件及其内容
            try:
                parent_dir = os.path.dirname(item_path_full)
                if not os.path.exists(parent_dir): # 确保父目录存在
                    os.makedirs(parent_dir, exist_ok=True)
                with open(item_path_full, 'w', encoding='utf-8') as f:
                    f.write(item_content)
                results.append({"item": relative_item_display_path, "status": "成功", "message": "文件已创建/更新。"})
            except PermissionError:
                results.append({"item": relative_item_display_path, "status": "失败", "message": f"权限错误：无法写入文件 '{item_path_full}'。"})
            except Exception as e:
                results.append({"item": relative_item_display_path, "status": "失败", "message": f"创建文件 '{item_path_full}' 失败: {str(e)}"})
        elif item_content is None: # 创建空目录
             try:
                if not os.path.exists(item_path_full):
                    os.makedirs(item_path_full, exist_ok=True)
                results.append({"item": relative_item_display_path, "status": "成功", "message": "空目录已创建。"})
             except PermissionError:
                results.append({"item": relative_item_display_path, "status": "失败", "message": f"权限错误：无法创建目录 '{item_path_full}'。"})
             except Exception as e:
                results.append({"item": relative_item_display_path, "status": "失败", "message": f"创建空目录 '{item_path_full}' 失败: {str(e)}"})
        else:
            results.append({"item": name, "status": "失败", "message": "项目结构中存在无法识别的项类型。"})
            
    return results

def generate_project_unsafe(params_json_str: str):
    """
    允许AI指定任意基础路径来创建项目结构。
    JSON参数: '{"base_path": "C:/path/to/create/project", "structure": {...}}'
    """
    print("警告: 项目生成插件正在以不安全模式运行，允许在AI指定的任意路径创建文件/目录。", file=sys.stderr)
    try:
        params = json.loads(params_json_str)
        # 参数名从 "base_path_key" 修改为 "base_path" 以反映其含义的改变
        base_path_from_ai = params.get("base_path") 
        structure = params.get("structure")

        if not base_path_from_ai or not isinstance(base_path_from_ai, str) or not base_path_from_ai.strip():
            return json.dumps([{"item": "参数错误", "status": "失败", "message": "输入参数JSON必须包含一个有效的非空字符串 'base_path'。"}], ensure_ascii=False, indent=2)
        if not isinstance(structure, dict):
             return json.dumps([{"item": "参数错误", "status": "失败", "message": "输入参数JSON必须包含一个有效的字典 'structure'。"}], ensure_ascii=False, indent=2)
        
        # 直接使用AI提供的路径调用创建函数
        results = create_project_structure_unsafe(base_path_from_ai, structure)
        return json.dumps(results, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps([{"item": "JSON解析错误", "status": "失败", "message": "输入参数不是有效的JSON字符串。"}], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"item": "未知错误", "status": "失败", "message": f"生成项目时发生未知错误: {str(e)}"}], ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_param = sys.argv[1]
        result = generate_project_unsafe(json_param) # 调用不安全的版本
        print(result)
    else:
        print("错误：项目框架生成插件（不安全模式）需要JSON参数。")
        print("例如：'{\"base_path\": \"C:/Users/YourUser/Desktop/MyNewAIProject\", \"structure\": {\"src\": {\"main.py\": \"print('hello')\"}, \"docs\": null}}'")
        print("警告：此模式允许在任意指定路径创建文件和目录，请谨慎使用！")
    sys.stdout.flush()