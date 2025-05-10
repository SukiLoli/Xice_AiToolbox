import sys
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus
import traceback
import os
import subprocess # 用于执行关闭进程的命令
import platform # 用于判断操作系统

# !!! 重要配置 - 用户需手动修改下面的路径 !!!
# 如果需要使用本地浏览器配置 (cookies, 登录状态等) 来尝试绕过反爬虫，
# 请设置此路径为你的 Chrome/Edge "User Data" 目录的路径。
# 示例 Chrome (Windows): "C:/Users/你的用户名/AppData/Local/Google/Chrome/User Data"
# 示例 Edge (Windows): "C:/Users/你的用户名/AppData/Local/Microsoft/Edge/User Data"
#
# 将此路径留空 ("") 或设置为 None 则使用常规的无头浏览器模式 (不带用户配置)。
#
# !!! 安全与操作警告 !!!
# 1. 使用本地用户配置意味着此插件将能访问你浏览器中的所有数据。
# 2. 如果配置了此路径，插件会尝试自动关闭相关的浏览器进程 (Chrome或Edge) 以确保能接管配置文件。
#    这可能会中断你正在进行的浏览器工作！请谨慎配置和使用。
# 3. 如果你不想插件自动关闭浏览器进程，请将下面的 USER_DATA_DIRECTORY_PATH 留空。
USER_DATA_DIRECTORY_PATH = "C:/Users/bin/AppData/Local/Microsoft/Edge/User Data"  # <--- 你已成功测试的路径

# --- Playwright 全局设置 ---
DEFAULT_BROWSER_TYPE = "chromium"
PAGE_LOAD_TIMEOUT = 45 * 1000
WAIT_AFTER_LOAD = 3
LAUNCH_BROWSER_HEADLESS = False # 使用用户配置时，建议 False (有头)

def get_browser_type_and_kill_command(user_data_path: str):
    """根据用户数据路径猜测浏览器类型并返回相应的关闭命令。"""
    path_lower = user_data_path.lower()
    os_platform = platform.system().lower()
    
    browser_executable = None
    kill_cmd_list = []

    if "google/chrome" in path_lower or "google-chrome" in path_lower:
        browser_type = "Chrome"
        if "windows" in os_platform:
            browser_executable = "chrome.exe"
            kill_cmd_list = ["taskkill", "/F", "/IM", browser_executable]
        elif "darwin" in os_platform: # macOS
            browser_executable = "Google Chrome"
            kill_cmd_list = ["pkill", "-f", browser_executable]
        elif "linux" in os_platform:
            browser_executable = "chrome" # 通常是 'google-chrome' 或 'chrome'
            kill_cmd_list = ["pkill", "-f", browser_executable] # 或者 pkill -f google-chrome
    elif "microsoft/edge" in path_lower or "microsoft-edge" in path_lower or "msedge" in path_lower:
        browser_type = "Edge"
        if "windows" in os_platform:
            browser_executable = "msedge.exe"
            kill_cmd_list = ["taskkill", "/F", "/IM", browser_executable]
        elif "darwin" in os_platform:
            browser_executable = "Microsoft Edge"
            kill_cmd_list = ["pkill", "-f", browser_executable]
        elif "linux" in os_platform:
            browser_executable = "msedge" # 通常是 'microsoft-edge' 或 'msedge'
            kill_cmd_list = ["pkill", "-f", browser_executable]
    else:
        browser_type = "未知浏览器"
        print(f"[Google Search Plugin] 警告: 无法从路径 '{user_data_path}' 明确识别浏览器类型。将不尝试关闭进程。", file=sys.stderr)
        return browser_type, None

    if not browser_executable:
        print(f"[Google Search Plugin] 警告: 无法为平台 '{os_platform}' 和路径 '{user_data_path}' 确定浏览器可执行文件名。将不尝试关闭进程。", file=sys.stderr)
        return browser_type, None
        
    return browser_type, kill_cmd_list

async def close_browser_processes(kill_cmd_list: list, browser_type: str):
    """尝试关闭指定的浏览器进程。"""
    if not kill_cmd_list:
        return

    print(f"[Google Search Plugin] 警告: 即将尝试关闭所有 {browser_type} 进程以使用用户配置文件。这可能会中断你正在进行的工作。", file=sys.stderr)
    try:
        # 对于Windows的taskkill，如果进程不存在，它会报错但返回码可能是0或1，所以我们不严格检查check=True
        # 对于pkill，如果没找到进程，它会返回非0，但我们不希望因此中断插件
        process = await asyncio.create_subprocess_shell(
            " ".join(kill_cmd_list), # shlex.join(kill_cmd_list) in Python 3.8+
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            print(f"[Google Search Plugin] 成功执行关闭 {browser_type} 进程的命令。 (这不代表一定有关闭的进程)", file=sys.stderr)
        else:
            print(f"[Google Search Plugin] 关闭 {browser_type} 进程的命令执行完毕，但返回码为 {process.returncode} (可能未找到进程，或权限问题)。", file=sys.stderr)
            if stdout: print(f"  [STDOUT]: {stdout.decode(errors='replace').strip()}", file=sys.stderr)
            if stderr: print(f"  [STDERR]: {stderr.decode(errors='replace').strip()}", file=sys.stderr)
        
        await asyncio.sleep(1) # 等待进程关闭生效

    except FileNotFoundError:
        print(f"[Google Search Plugin] 错误: 关闭 {browser_type} 进程的命令 ('{kill_cmd_list[0]}') 未找到。请确保相关命令在系统PATH中。", file=sys.stderr)
    except Exception as e:
        print(f"[Google Search Plugin] 尝试关闭 {browser_type} 进程时发生错误: {e}", file=sys.stderr)


async def perform_google_search(keywords: str):
    search_url = f"https://www.google.com/search?q={quote_plus(keywords)}&hl=zh-CN&gl=CN"
    print(f"[Google Search Plugin] 构造的搜索URL: {search_url}", file=sys.stderr)

    playwright_instance = None
    browser_context = None
    page = None
    mode_description = ""
    browser_closed_by_plugin = False

    try:
        playwright_instance = await async_playwright().start()
        effective_user_data_dir = None

        if USER_DATA_DIRECTORY_PATH and isinstance(USER_DATA_DIRECTORY_PATH, str) and os.path.isdir(USER_DATA_DIRECTORY_PATH):
            effective_user_data_dir = USER_DATA_DIRECTORY_PATH
            browser_type_guess, kill_cmd = get_browser_type_and_kill_command(effective_user_data_dir)
            if kill_cmd:
                await close_browser_processes(kill_cmd, browser_type_guess)
                browser_closed_by_plugin = True # 标记我们尝试过关闭
            mode_description = f"使用本地用户配置: {effective_user_data_dir} (尝试关闭了 {browser_type_guess} 进程)"
        else:
            if USER_DATA_DIRECTORY_PATH:
                print(f"[Google Search Plugin] 警告: 配置的 USER_DATA_DIRECTORY_PATH ('{USER_DATA_DIRECTORY_PATH}') 无效或不是一个目录。将使用常规模式。", file=sys.stderr)
            mode_description = "使用常规模式 (无用户配置)"
        
        print(f"[Google Search Plugin] 启动模式: {mode_description}", file=sys.stderr)

        common_browser_args = [
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
            '--disable-blink-features=AutomationControlled',
            # '--window-size=1280,720', # 可以尝试固定窗口大小
        ]

        if effective_user_data_dir:
            try:
                browser_context = await playwright_instance.chromium.launch_persistent_context(
                    user_data_dir=effective_user_data_dir,
                    headless=LAUNCH_BROWSER_HEADLESS,
                    args=common_browser_args,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.43', # Edge UA 示例
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai',
                    # slow_mo=50 # 毫秒级的操作延迟，用于调试或某些反爬
                )
                page = await browser_context.new_page()
                print(f"[Google Search Plugin] 已使用 launch_persistent_context 模式启动。", file=sys.stderr)
            except PlaywrightError as pe_persistent:
                err_msg = f"错误：使用本地用户配置 '{effective_user_data_dir}' 启动浏览器失败。可能原因：1. 路径不正确。2. 相关浏览器进程未能成功关闭。3. 配置文件损坏或权限问题。错误详情: {str(pe_persistent)}"
                if browser_closed_by_plugin:
                    err_msg += " (即使在尝试关闭相关进程后依然失败)"
                print(f"--- Google Search Plugin (Playwright): Error launching with persistent context ---", file=sys.stderr)
                print(f"--- Error: {str(pe_persistent)}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return err_msg
        else:
            browser = await playwright_instance.chromium.launch(
                headless=True, args=common_browser_args
            )
            browser_context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Xice_Aitoolbox/SearchPlugin-Regular',
                java_script_enabled=True, locale='zh-CN', timezone_id='Asia/Shanghai'
            )
            page = await browser_context.new_page()
            print(f"[Google Search Plugin] 已使用常规 launch 模式启动。", file=sys.stderr)

        page_content_html = ""
        final_url_visited = search_url

        try:
            print(f"[Playwright - Google Search] 导航至: {search_url}", file=sys.stderr)
            await page.goto(search_url, timeout=PAGE_LOAD_TIMEOUT, wait_until='domcontentloaded')
            final_url_visited = page.url

            if WAIT_AFTER_LOAD > 0:
                print(f"[Playwright - Google Search] 等待 {WAIT_AFTER_LOAD}s 加载动态内容...", file=sys.stderr)
                await page.wait_for_timeout(WAIT_AFTER_LOAD * 1000)
            
            # 如果是带用户配置的模式，可能不需要主动点cookie，但常规模式下可以尝试
            if not effective_user_data_dir:
                try:
                    # 尝试处理多种可能的同意/拒绝按钮，选择器需要非常灵活
                    # 注意：谷歌页面的这些元素经常变化，以下选择器可能很快失效
                    consent_selectors = [
                        "button:has-text('Accept all')", "button:has-text('Agree')", 
                        "button:has-text('Reject all')", "button:has-text('全部拒绝')",
                        "button:has-text('I agree')", "button:has-text('我同意')",
                        "div[role='button']:textmatches(/(Accept all|Agree|Reject all|全部拒绝|I agree|我同意)/i)"
                    ]
                    action_taken = False
                    for selector in consent_selectors:
                        try:
                            button = page.locator(selector).first
                            if await button.is_visible(timeout=1000):
                                print(f"[Playwright - Google Search] 尝试点击Cookie按钮: {selector}", file=sys.stderr)
                                await button.click(timeout=1500, force=True) # force=True 可能有帮助
                                await page.wait_for_timeout(700) # 点击后稍等
                                action_taken = True
                                break
                        except Exception: # 忽略单个按钮的错误
                            pass
                    if action_taken:
                        print("[Playwright - Google Search] 已尝试处理Cookie弹窗。", file=sys.stderr)
                    else:
                        print("[Playwright - Google Search] 未找到明确的Cookie弹窗按钮或处理失败。", file=sys.stderr)
                except Exception as e_cookie:
                    print(f"[Playwright - Google Search] 处理Cookie弹窗时发生一般性错误: {e_cookie}", file=sys.stderr)


            page_content_html = await page.content()
            print(f"[Playwright - Google Search] 成功从 {final_url_visited} 获取内容", file=sys.stderr)

        except PlaywrightTimeoutError:
            print(f"[Playwright - Google Search] 加载 {search_url} 超时。尝试获取部分内容。", file=sys.stderr)
            page_content_html = await page.content() 
            if not page_content_html:
                return f"错误({mode_description})：请求谷歌搜索 '{keywords}' 超时 ({PAGE_LOAD_TIMEOUT / 1000}秒) 且未能获取任何内容。"
        except PlaywrightError as pe_page:
            print(f"--- Google Search Plugin (Playwright): Page operation error ({mode_description}) ---", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return f"错误({mode_description})：访问谷歌搜索 '{keywords}' 时页面操作失败: {str(pe_page)}"
        
        if not page_content_html:
            return f"错误({mode_description})：未能从谷歌搜索 '{keywords}' 获取到HTML内容。"

        soup = BeautifulSoup(page_content_html, 'html.parser')
        title_tag = soup.find('title')
        page_title = title_tag.string.strip() if title_tag and title_tag.string else "未找到页面标题"

        for script_or_style in soup(["script", "style", "noscript", "meta", "link", "header", "footer", "nav", "aside", "form", "input", "button"]):
            script_or_style.decompose()
        
        main_content_area = soup.find(id="main") or soup.find(id="rcnt") or soup.find("body")
        full_text = main_content_area.get_text(separator='\n', strip=True) if main_content_area else soup.get_text(separator='\n', strip=True)
        
        lines = [line.strip() for line in full_text.splitlines()]
        cleaned_lines = [line for line in lines if line] 
        full_text = "\n".join(cleaned_lines)

        max_text_length = 25000 
        if len(full_text) > max_text_length:
            full_text = full_text[:max_text_length] + f"...\n[文本内容过长，已截断至 {max_text_length} 字符]"
        
        if not full_text.strip():
            full_text = "未能从搜索结果页提取到有效的文本内容。"

        links = []
        all_a_tags = main_content_area.find_all('a', href=True) if main_content_area else soup.find_all('a', href=True)
        extracted_urls = set() 

        for a_tag in all_a_tags:
            raw_href = a_tag['href']
            link_text = ' '.join(a_tag.get_text(strip=True).split()) 

            if not raw_href or raw_href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            if raw_href.startswith("/search?q=") or raw_href.startswith("/advanced_search") or \
               any(s in raw_href for s in ["google.com/preferences", "accounts.google.com", "support.google.com", "policies.google.com", "google.com/setprefs"]):
                if not link_text or link_text.isdigit() or link_text.lower() in ["images", "videos", "news", "shopping", "maps", "books", "flights", "finance", "图片", "视频", "新闻", "购物", "地图", "图书", "更多", "设置", "工具", "隐私权", "条款", "反馈", "登录", "sign in"]:
                    continue
            
            # 如果链接文本为空，并且不是一个明显的H3标题下的链接，则可能不是主要结果
            if not link_text:
                parent_h3 = a_tag.find_parent('h3')
                if not parent_h3:
                    if "google.com" in raw_href and (raw_href.startswith("/") or "http" not in raw_href): # 过滤掉更多内部导航
                        continue

            try:
                absolute_href = urljoin(final_url_visited, raw_href)
                parsed_abs_href = urlparse(absolute_href)
                if not parsed_abs_href.scheme or not parsed_abs_href.netloc: continue

                # 处理谷歌跳转链接
                if "google.com" in parsed_abs_href.netloc and ("/url?q=" in parsed_abs_href.path or "/search?sa=U&url=" in parsed_abs_href.path):
                    from urllib.parse import parse_qs
                    query_params = parse_qs(parsed_abs_href.query)
                    real_url = None
                    if 'q' in query_params and query_params['q'][0]: real_url = query_params['q'][0]
                    elif 'url' in query_params and query_params['url'][0]: real_url = query_params['url'][0]
                    
                    if real_url:
                        absolute_href = real_url
                        parsed_abs_href = urlparse(absolute_href)
                        if not parsed_abs_href.scheme or not parsed_abs_href.netloc: continue
                    else: continue # 无法解析跳转链接

                if "google.com" in parsed_abs_href.netloc and parsed_abs_href.path.startswith("/search"): # 再次过滤掉搜索结果中的“下一页”等
                    continue

                if absolute_href not in extracted_urls and "googleusercontent.com" not in parsed_abs_href.netloc: # 过滤掉网页快照等
                    links.append({"text": link_text or "N/A", "url": absolute_href})
                    extracted_urls.add(absolute_href)
            except Exception:
                continue
        
        max_links = 30 # 进一步减少链接数量，聚焦核心结果
        if len(links) > max_links:
            links_output_list = links[:max_links]
            links_output_list.append({"text": f"... [链接列表过长（共{len(links)}条），已截断至前 {max_links} 条]", "url": ""})
        elif not links:
            links_output_list = [{"text": "未找到符合条件的核心外部超链接。", "url": ""}]
        else:
            links_output_list = links
        
        links_formatted = "\n".join([f"- {link['text']}: {link['url']}" for link in links_output_list if link['url']])
        if not links_formatted and not any(link['url'] for link in links_output_list) :
            links_formatted = "未找到符合条件的核心外部超链接。"

        output = f"[谷歌搜索关键词]: {keywords}\n"
        output += f"[搜索模式]: {mode_description}\n"
        output += f"[搜索结果页标题 (尝试提取)]: {page_title}\n"
        output += f"[实际搜索URL (Playwright)]: {final_url_visited}\n\n"
        output += "[搜索结果页主要文本内容 (可能包含非结果文本)]:\n"
        output += f"{full_text}\n\n"
        output += "[提取到的可能相关的超链接 (已尝试去重和解析跳转)]:\n" + links_formatted
            
        return output.strip()

    except Exception as e:
        print(f"--- Google Search Plugin: Unhandled Exception (Outer) ({mode_description}) ---", file=sys.stderr)
        print(f"Keywords: {keywords}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"执行谷歌搜索 '{keywords}' (模式: {mode_description}) 时发生了一个顶层未知错误。管理员请查看服务器日志。错误: {str(e)}"
    finally:
        # 清理 Playwright 资源
        if page:
            try: await page.close()
            except Exception as e: print(f"[Google Search Plugin] 关闭页面出错: {e}", file=sys.stderr)
        if browser_context:
            try: await browser_context.close()
            except Exception as e: print(f"[Google Search Plugin] 关闭浏览器上下文/浏览器出错: {e}", file=sys.stderr)
        if playwright_instance:
            try: await playwright_instance.stop()
            except Exception as e: print(f"[Google Search Plugin] 停止Playwright实例出错: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        keywords_param = sys.argv[1]
        print(f"[Plugin Log] Google Search Plugin: Received keywords '{keywords_param}'", file=sys.stderr)
        print(f"[Plugin Log] USER_DATA_DIRECTORY_PATH is set to: '{USER_DATA_DIRECTORY_PATH}'", file=sys.stderr)
        if USER_DATA_DIRECTORY_PATH and os.path.isdir(USER_DATA_DIRECTORY_PATH):
             print(f"[Plugin Log] 重要：如果配置了有效的用户数据目录，插件将尝试关闭相关的浏览器进程。", file=sys.stderr)
             print(f"[Plugin Log]       这可能会中断你正在进行的浏览器工作。请确保你了解此操作。", file=sys.stderr)
        elif USER_DATA_DIRECTORY_PATH:
             print(f"[Plugin Log] 警告：配置的用户数据目录 '{USER_DATA_DIRECTORY_PATH}' 无效，将使用常规模式。", file=sys.stderr)

        try:
            result = asyncio.run(perform_google_search(keywords_param))
            print(result)
        except Exception as e:
            print(f"执行谷歌搜索插件主线程时发生错误: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print(f"错误：执行谷歌搜索插件时发生严重内部错误。详情请查看服务器日志。")
    else:
        print("错误：谷歌搜索插件需要关键词作为参数。请使用格式：[谷歌搜索]关键词[/谷歌搜索]")
    sys.stdout.flush()
    sys.stderr.flush()