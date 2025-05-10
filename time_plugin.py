import datetime
import sys

def get_current_system_time():
    """获取当前系统时间并格式化输出"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    # 这个插件不需要从命令行接收参数，直接执行功能
    current_time = get_current_system_time()
    print(f"现在的时间是：{current_time}") # 将结果打印到标准输出
    sys.stdout.flush() # 确保输出被立即发送