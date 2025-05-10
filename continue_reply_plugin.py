import sys

# 这个插件的主要目的是被 proxy_server.js 检测到。
# 它本身不需要做太多事情，只需要成功返回即可。
# 返回的文本可以给AI一些上下文，说明它的“继续回复”请求已被处理。

if __name__ == "__main__":
    # 获取传递给插件的参数 (即 [继续回复]...[/继续回复] 之间的内容)
    continuation_hint = ""
    if len(sys.argv) > 1:
        continuation_hint = sys.argv[1]

    if continuation_hint:
        print(f"[继续回复插件]: 已收到您的继续请求，提示为：'{continuation_hint}'. AI应基于此提示继续生成。")
    else:
        print("[继续回复插件]: 已收到您的继续请求。AI应继续生成原始内容。")
    
    sys.stdout.flush()