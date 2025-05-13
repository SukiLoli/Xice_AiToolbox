import os
import sys
import json

# 默认配置
DEFAULT_MAX_FILE_SIZE_MB_WRITE = 5

# 加载插件自身配置
max_file_size_mb_write = DEFAULT_MAX_FILE_SIZE_MB_WRITE
allow_arbitrary_paths = True # 从插件配置中获取，确保其意图
try:
    plugin_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(plugin_config_path):
        with open(plugin_config_path, 'r', encoding='utf-8') as f:
            plugin_config_data = json.load(f)
            psc = plugin_config_data.get("plugin_specific_config", {})
            max_file_size_mb_write = psc.get("max_file_size_mb_write", DEFAULT_MAX_FILE_SIZE_MB_WRITE)
            allow_arbitrary_paths = psc.get("allow_arbitrary_paths", True) 
    if not allow_arbitrary_paths:
        print("严重警告: 文件更新插件 (file_updater) 被配置为不允许任意路径，但其代码逻辑当前是允许的。存在配置与行为不一致的风险！", file=sys.stderr)
except Exception as e:
    print(f"警告: 读取插件 file_updater 配置失败: {e}. 将使用默认值。", file=sys.stderr)


def update_files_unsafe(operations_json_str: str):
    """
    根据JSON字符串描述更新一个或多个文件内容。
    如果 allow_arbitrary_paths 为 true (来自插件配置)，则允许AI指定任意路径。
    """
    if not allow_arbitrary_paths:
        return json.dumps([{"path": "配置错误", "status": "失败", "message": "插件被配置为不允许任意路径操作，但此功能被调用。请检查插件配置。"}], ensure_ascii=False, indent=2)
    
    print("警告: 文件更新插件正在以不安全模式运行，允许在AI指定的任意路径更新文件。", file=sys.stderr)
    results = []
    try:
        operations = json.loads(operations_json_str)
        if not isinstance(operations, list):
            return json.dumps([{"path": "参数错误", "status": "失败", "message": "输入参数必须是一个JSON数组。"}], ensure_ascii=False, indent=2)

        if not operations:
            return json.dumps([{"path": "无操作", "status": "信息", "message": "没有提供任何文件更新操作。"}], ensure_ascii=False, indent=2)

        for op in operations:
            if not isinstance(op, dict) or "path" not in op or "content" not in op:
                results.append({"path": op.get("path", "未知路径"), "status": "失败", "message": "操作格式错误，缺少'path'或'content'字段。"})
                continue

            file_path_from_ai = op["path"]
            content = op["content"]
            op_result = {"path": file_path_from_ai, "status": "失败"}

            try:
                resolved_path = os.path.realpath(os.path.expanduser(os.path.expandvars(file_path_from_ai)))
            except Exception as e:
                op_result["message"] = f"解析路径 '{file_path_from_ai}' 失败: {str(e)}"
                results.append(op_result)
                continue
            
            try:
                dir_name = os.path.dirname(resolved_path)
                if dir_name and not os.path.exists(dir_name):
                    print(f"信息: 尝试为文件 '{resolved_path}' 创建父目录: {dir_name}", file=sys.stderr)
                    os.makedirs(dir_name, exist_ok=True)
            except PermissionError:
                op_result["message"] = f"权限错误：无法创建目录 '{os.path.dirname(resolved_path)}'。"
                results.append(op_result)
                continue
            except Exception as e:
                op_result["message"] = f"创建目录时发生错误 '{os.path.dirname(resolved_path)}': {str(e)}"
                results.append(op_result)
                continue

            try:
                content_bytes = str(content).encode('utf-8') 
                if len(content_bytes) > max_file_size_mb_write * 1024 * 1024:
                    op_result["message"] = f"内容大小超过 {max_file_size_mb_write}MB 限制。"
                    results.append(op_result)
                    continue
            except Exception as e:
                op_result["message"] = f"无法预估内容大小（可能不是文本）: {str(e)}"
                results.append(op_result)
                continue
            
            try:
                with open(resolved_path, 'w', encoding='utf-8') as f:
                    f.write(str(content)) #确保写入的是字符串
                op_result["status"] = "成功"
                op_result["message"] = f"文件 '{resolved_path}' 已更新。"
            except PermissionError:
                op_result["message"] = f"权限错误：无法写入文件 '{resolved_path}'。"
            except IsADirectoryError:
                 op_result["message"] = f"路径错误：'{resolved_path}' 是一个目录，不能作为文件写入。"
            except Exception as e:
                op_result["message"] = f"写入文件 '{resolved_path}' 时发生错误: {str(e)}"
            results.append(op_result)
            
        return json.dumps(results, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        return json.dumps([{"path": "JSON解析错误", "status": "失败", "message": "输入参数不是有效的JSON字符串。"}], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"path": "未知错误", "status": "失败", "message": f"处理文件更新时发生未知错误: {str(e)}"}], ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_param = sys.argv[1]
        result = update_files_unsafe(json_param)
        print(result)
    else:
        print(json.dumps([{"path": "调用错误", "status": "失败", "message": "文件更新插件需要一个JSON字符串作为参数。"}]))
        print("警告：此模式允许在任意指定路径更新文件，请谨慎使用！")
    sys.stdout.flush()
