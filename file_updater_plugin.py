import os
import sys
import json

# 警告：此版本的插件允许AI指定任意系统路径进行文件更新。
# 这具有极高的安全风险，请仅在完全理解并接受风险的情况下使用。
# 强烈建议恢复到使用 config.json 白名单的版本。

# 不再从 config.json 加载白名单路径
# ALLOWED_BASE_PATHS = [] 
# CONFIG_FILE = "config.json" # 也不再需要读取config

MAX_FILE_SIZE_MB_WRITE = 5  # 限制写入的最大文件大小 (MB) - 这个限制仍然保留

# is_path_allowed 函数不再需要，因为我们允许任意路径
# def is_path_allowed(target_path: str) -> bool:
#     ... (移除此函数) ...

def update_files_unsafe(operations_json_str: str):
    """
    根据JSON字符串描述更新一个或多个文件内容。允许AI指定任意路径。
    JSON格式: '[{"path": "C:/path/to/file1.txt", "content": "new content1"}, ...]'
    """
    print("警告: 文件更新插件正在以不安全模式运行，允许在AI指定的任意路径更新文件。", file=sys.stderr)
    results = []
    try:
        operations = json.loads(operations_json_str)
        if not isinstance(operations, list):
            return json.dumps([{"path": "参数错误", "status": "失败", "message": "输入参数必须是一个JSON数组，描述要更新的文件操作。"}], ensure_ascii=False, indent=2)

        if not operations:
            return json.dumps([{"path": "无操作", "status": "信息", "message": "没有提供任何文件更新操作。"}], ensure_ascii=False, indent=2)

        for op in operations:
            if not isinstance(op, dict) or "path" not in op or "content" not in op:
                results.append({"path": op.get("path", "未知路径"), "status": "失败", "message": "操作格式错误，缺少'path'或'content'字段。"})
                continue

            file_path_from_ai = op["path"]
            content = op["content"]
            op_result = {"path": file_path_from_ai, "status": "失败"}

            # 直接使用AI提供的路径，进行必要的解析
            try:
                resolved_path = os.path.realpath(os.path.expanduser(os.path.expandvars(file_path_from_ai)))
            except Exception as e:
                op_result["message"] = f"解析路径 '{file_path_from_ai}' 失败: {str(e)}"
                results.append(op_result)
                continue
            
            # 准备写入目录
            try:
                dir_name = os.path.dirname(resolved_path)
                if dir_name and not os.path.exists(dir_name): # 确保目录存在
                    # 在不安全模式下，也尝试创建AI指定的路径中的目录
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

            # 检查预估内容大小
            try:
                content_bytes = content.encode('utf-8') # 预估大小
                if len(content_bytes) > MAX_FILE_SIZE_MB_WRITE * 1024 * 1024:
                    op_result["message"] = f"内容大小超过 {MAX_FILE_SIZE_MB_WRITE}MB 限制。"
                    results.append(op_result)
                    continue
            except Exception as e: # content 可能不是字符串
                op_result["message"] = f"无法预估内容大小（可能不是文本）: {str(e)}"
                results.append(op_result)
                continue
            
            try:
                with open(resolved_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                op_result["status"] = "成功"
                op_result["message"] = f"文件 '{resolved_path}' 已更新。"
            except PermissionError:
                op_result["message"] = f"权限错误：无法写入文件 '{resolved_path}'。"
            except FileNotFoundError: # 理论上目录已创建，但以防万一
                 op_result["message"] = f"文件未找到错误（可能是路径问题）: '{resolved_path}'。"
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
        result = update_files_unsafe(json_param) # 调用不安全的版本
        print(result)
    else:
        print("错误：文件更新插件（不安全模式）需要一个JSON字符串作为参数，描述文件路径和内容。")
        print("例如：'[{\"path\": \"C:/temp/anyfile.txt\", \"content\": \"Hello World from AI\"}]'")
        print("警告：此模式允许在任意指定路径更新文件，请谨慎使用！")
    sys.stdout.flush()