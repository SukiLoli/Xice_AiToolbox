import sys

if __name__ == "__main__":
    continuation_hint = ""
    if len(sys.argv) > 1:
        continuation_hint = sys.argv[1]

    if continuation_hint:
        print(f"[继续回复插件]: 已收到您的继续请求，提示为：'{continuation_hint}'. AI应基于此提示继续生成。")
    else:
        print("[继续回复插件]: 已收到您的继续请求。AI应继续生成原始内容。")
    
    sys.stdout.flush()
