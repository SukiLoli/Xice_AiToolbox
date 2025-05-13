import os
import sys
import json

# 加载插件自身配置
allow_arbitrary_paths = True # 从插件配置中获取，确保其意图
try:
    plugin_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(plugin_config_path):
        with open(plugin_config_path, 'r', encoding='utf-8') as f:
            plugin_config_data = json.load(f)
            psc = plugin_config_data.get("plugin_specific_config", {})
            allow_arbitrary_paths = psc.get("allow_arbitrary_paths", True)
    if not allow_arbitrary_paths:
        print("严重警告: 项目生成插件 (project_generator) 被配置为不允许任意路径，但其代码逻辑当前是允许的。存在配置与行为不一致的风险！", file=sys.stderr)
except Exception as e:
    print(f"警告: 读取插件 project_generator 配置失败: {e}. 将使用默认行为（允许任意路径）。", file=sys.stderr)


def create_project_structure_recursive(base_path_from_ai: str, structure: dict, current_path_relative_to_base="", results_list=None):
    """
    递归创建目录和文件。
    base_path_from_ai: AI直接提供的绝对或相对基础路径。
    structure: {'dirname': {'filename': 'content', 'subdir': {...}}, 'file2': 'content2'}
    results_list: 用于收集操作结果的列表。
    """
    if results_list is None:
        results_list = []

    try:
        actual_base_path_root = os.path.realpath(os.path.expanduser(os.path.expandvars(base_path_from_ai)))
    except Exception as e:
        results_list.append({"item": base_path_from_ai, "status": "失败", "message": f"错误：解析基础路径 '{base_path_from_ai}' 失败: {str(e)}"})
        return results_list # 基础路径解析失败，无法继续

    current_full_path_segment_root = os.path.join(actual_base_path_root, current_path_relative_to_base)

    # 确保当前递归段的根目录存在
    if not os.path.exists(current_full_path_segment_root):
        try:
            os.makedirs(current_full_path_segment_root, exist_ok=True)
            # results_list.append({"item": os.path.join(base_path_from_ai, current_path_relative_to_base) or base_path_from_ai, 
            #                      "status": "成功", "message": "目录已创建 (或已存在)。"})
        except Exception as e:
            results_list.append({"item": os.path.join(current_path_relative_to_base, "<directory_creation_failed>"), "status": "失败", "message": f"创建目录 '{current_full_path_segment_root}' 失败: {str(e)}"})
            return results_list 

    for name, item_content in structure.items():
        # 对文件名/目录名进行基本检查
        if ".." in name or "/" in name or "\\" in name or not name.strip():
            results_list.append({"item": os.path.join(current_path_relative_to_base, name), "status": "失败", "message": "名称非法 (不允许路径分隔符、'..'或空名称)。"})
            continue

        item_path_full = os.path.join(current_full_path_segment_root, name)
        relative_item_display_path = os.path.join(current_path_relative_to_base, name)

        if isinstance(item_content, dict): 
            create_project_structure_recursive(base_path_from_ai, item_content, relative_item_display_path, results_list)
        elif isinstance(item_content, str): 
            try:
                parent_dir = os.path.dirname(item_path_full)
                if not os.path.exists(parent_dir): # 确保父目录存在 (理论上外层已创建)
                    os.makedirs(parent_dir, exist_ok=True)
                with open(item_path_full, 'w', encoding='utf-8') as f:
                    f.write(item_content)
                results_list.append({"item": relative_item_display_path, "status": "成功", "message": "文件已创建/更新。"})
            except PermissionError:
                results_list.append({"item": relative_item_display_path, "status": "失败", "message": f"权限错误：无法写入文件 '{item_path_full}'。"})
            except Exception as e:
                results_list.append({"item": relative_item_display_path, "status": "失败", "message": f"创建文件 '{item_path_full}' 失败: {str(e)}"})
        elif item_content is None: 
             try:
                if not os.path.exists(item_path_full):
                    os.makedirs(item_path_full, exist_ok=True)
                results_list.append({"item": relative_item_display_path, "status": "成功", "message": "空目录已创建。"})
             except PermissionError:
                results_list.append({"item": relative_item_display_path, "status": "失败", "message": f"权限错误：无法创建目录 '{item_path_full}'。"})
             except Exception as e:
                results_list.append({"item": relative_item_display_path, "status": "失败", "message": f"创建空目录 '{item_path_full}' 失败: {str(e)}"})
        else:
            results_list.append({"item": os.path.join(current_path_relative_to_base, name), "status": "失败", "message": "项目结构中存在无法识别的项类型。"})
            
    return results_list

def generate_project_unsafe(params_json_str: str):
    """
    允许AI指定任意基础路径来创建项目结构。
    JSON参数: '{"base_path": "C:/path/to/create/project", "structure": {...}}'
    """
    if not allow_arbitrary_paths:
        return json.dumps([{"item": "配置错误", "status": "失败", "message": "插件被配置为不允许任意路径操作。"}], ensure_ascii=False, indent=2)

    print("警告: 项目生成插件正在以不安全模式运行，允许在AI指定的任意路径创建文件/目录。", file=sys.stderr)
    try:
        params = json.loads(params_json_str)
        base_path_from_ai = params.get("base_path") 
        structure = params.get("structure")

        if not base_path_from_ai or not isinstance(base_path_from_ai, str) or not base_path_from_ai.strip():
            return json.dumps([{"item": "参数错误", "status": "失败", "message": "JSON必须包含有效的非空字符串 'base_path'。"}], ensure_ascii=False, indent=2)
        if not isinstance(structure, dict):
             return json.dumps([{"item": "参数错误", "status": "失败", "message": "JSON必须包含有效的字典 'structure'。"}], ensure_ascii=False, indent=2)
        
        initial_results = []
        # 确保基础目录存在
        try:
            actual_base_path = os.path.realpath(os.path.expanduser(os.path.expandvars(base_path_from_ai)))
            if not os.path.exists(actual_base_path):
                os.makedirs(actual_base_path, exist_ok=True)
                initial_results.append({"item": base_path_from_ai, "status": "成功", "message": f"基础目录 '{actual_base_path}' 已创建。"})
            else:
                initial_results.append({"item": base_path_from_ai, "status": "信息", "message": f"基础目录 '{actual_base_path}' 已存在。"})

        except Exception as e:
            return json.dumps([{"item": base_path_from_ai, "status": "失败", "message": f"创建或验证基础目录 '{base_path_from_ai}' 失败: {str(e)}"}], ensure_ascii=False, indent=2)


        final_results = create_project_structure_recursive(base_path_from_ai, structure, results_list=initial_results)
        return json.dumps(final_results, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps([{"item": "JSON解析错误", "status": "失败", "message": "输入参数不是有效的JSON字符串。"}], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"item": "未知错误", "status": "失败", "message": f"生成项目时发生未知错误: {str(e)}"}], ensure_ascii=False, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_param = sys.argv[1]
        result = generate_project_unsafe(json_param)
        print(result)
    else:
        print(json.dumps([{"item": "调用错误", "status": "失败", "message": "项目生成插件需要JSON参数。"}]))
        print("警告：此模式允许在任意指定路径创建文件和目录，请谨慎使用！")
    sys.stdout.flush()
