import sys
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus, parse_qs
import traceback
import os
import platform
import json # 新增

# --- 默认配置 ---
DEFAULT_USER_DATA_DIRECTORY_PATH = ""
DEFAULT_BROWSER_EXECUTABLE = "chromium" # playwright的浏览器类型名
DEFAULT_PAGE_LOAD_TIMEOUT_MS = 45 * 1000
DEFAULT_WAIT_AFTER_LOAD_S = 3
DEFAULT_LAUNCH_BROWSER_HEADLESS = False # 使用用户配置时，建议 False (有头)
DEFAULT_MAX_TEXT_LENGTH = 25000
DEFAULT_MAX_LINKS = 30

# --- 加载插件配置 ---
user_data_directory_path = DEFAULT_USER_DATA_DIRECTORY_PATH
browser_executable = DEFAULT_BROWSER_EXECUTABLE
page_load_timeout_ms = DEFAULT_PAGE_LOAD_TIMEOUT_MS
wait_after_load_s = DEFAULT_WAIT_AFTER_LOAD_S
launch_browser_headless = DEFAULT_LAUNCH_BROWSER_HEADLESS
max_results_text_length = DEFAULT_MAX_TEXT_LENGTH
max_links_to_extract = DEFAULT_MAX_LINKS

try:
    plugin_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(plugin_config_path):
        with open(plugin_config_path, 'r', encoding='utf-8') as f:
            plugin_config_data = json.load(f)
            psc = plugin_config_data.get("plugin_specific_config", {})
            user_data_directory_path = psc.get("user_data_directory_path", DEFAULT_USER_DATA_DIRECTORY_PATH)
            # browser_executable 现在指Playwright的浏览器类型，如chromium, firefox, webkit
            browser_executable = psc.get("default_browser_type", DEFAULT_BROWSER_EXECUTABLE).lower() 
            page_load_timeout_ms = psc.get("page_load_timeout_ms", DEFAULT_PAGE_LOAD_TIMEOUT_MS)
            wait_after_load_s = psc.get("wait_after_load_seconds", DEFAULT_WAIT_AFTER_LOAD_S)
            launch_browser_headless = psc.get("launch_browser_headless", DEFAULT_LAUNCH_BROWSER_HEADLESS)
            max_results_text_length = psc.get("max_results_text_length", DEFAULT_MAX_TEXT_LENGTH)
            max_links_to_extract = psc.get("max_links_to_extract", DEFAULT_MAX_LINKS)
            
            # 确保 browser_executable 是 playwright 支持的类型
            if browser_executable not in ["chromium", "firefox", "webkit"]:
                print(f"警告: 插件配置中指定的浏览器类型 '{browser_executable}' 无效，将回退到 'chromium'。", file=sys.stderr)
                browser_executable = "chromium"

except Exception as e:
    print(f"警告: 读取插件 google_search 配置 ({plugin_config_path}) 失败: {e}. 将使用默认值。", file=sys.stderr)


def get_browser_type_and_kill_command(user_data_path: str):
    path_lower = user_data_path.lower()
    os_platform = platform.system().lower()
    
    browser_name_for_kill = None
    kill_cmd_list = []

    if "google/chrome" in path_lower or "google-chrome" in path_lower:
        browser_name_for_kill = "Chrome"
        if "windows" in os_platform: kill_cmd_list = ["taskkill", "/F", "/IM", "chrome.exe"]
        elif "darwin" in os_platform: kill_cmd_list = ["pkill", "-f", "Google Chrome"]
        elif "linux" in os_platform: kill_cmd_list = ["pkill", "-f", "chrome"]
    elif "microsoft/edge" in path_lower or "microsoft-edge" in path_lower or "msedge" in path_lower:
        browser_name_for_kill = "Edge"
        if "windows" in os_platform: kill_cmd_list = ["taskkill", "/F", "/IM", "msedge.exe"]
        elif "darwin" in os_platform: kill_cmd_list = ["pkill", "-f", "Microsoft Edge"]
        elif "linux" in os_platform: kill_cmd_list = ["pkill", "-f", "msedge"]
    # 可以为Firefox等添加更多判断
    # elif "firefox" in path_lower or "mozilla" in path_lower:
    #     browser_name_for_kill = "Firefox"
    # ...

    if not browser_name_for_kill:
        print(f"[Google Search Plugin] 警告: 无法从路径 '{user_data_path}' 明确识别浏览器类型以关闭进程。", file=sys.stderr)
        return "未知浏览器", None
        
    return browser_name_for_kill, kill_cmd_list

async def close_browser_processes(kill_cmd_list: list, browser_type: str):
    if not kill_cmd_list: return
    print(f"[Google Search Plugin] 警告: 即将尝试关闭所有 {browser_type} 进程以使用用户配置文件。", file=sys.stderr)
    try:
        process = await asyncio.create_subprocess_shell(
            " ".join(kill_cmd_list),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            print(f"[Google Search Plugin] 成功执行关闭 {browser_type} 进程的命令。", file=sys.stderr)
        else:
            print(f"[Google Search Plugin] 关闭 {browser_type} 进程的命令返回码 {process.returncode}.", file=sys.stderr)
            if stdout: print(f"  [STDOUT]: {stdout.decode(errors='replace').strip()}", file=sys.stderr)
            if stderr: print(f"  [STDERR]: {stderr.decode(errors='replace').strip()}", file=sys.stderr)
        await asyncio.sleep(1)
    except FileNotFoundError:
        print(f"[Google Search Plugin] 错误: 关闭命令 '{kill_cmd_list[0]}' 未找到。", file=sys.stderr)
    except Exception as e:
        print(f"[Google Search Plugin] 关闭 {browser_type} 进程时出错: {e}", file=sys.stderr)


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
        if user_data_directory_path and isinstance(user_data_directory_path, str) and os.path.isdir(user_data_directory_path):
            effective_user_data_dir = user_data_directory_path
            browser_type_guess, kill_cmd = get_browser_type_and_kill_command(effective_user_data_dir)
            if kill_cmd:
                await close_browser_processes(kill_cmd, browser_type_guess)
                browser_closed_by_plugin = True
            mode_description = f"本地用户配置: {effective_user_data_dir} (尝试关闭 {browser_type_guess})"
        else:
            if user_data_directory_path: # 如果配置了但无效
                print(f"[Google Search Plugin] 警告: 配置的 user_data_directory_path 无效。使用常规模式。", file=sys.stderr)
            mode_description = "常规模式 (无用户配置)"
        
        print(f"[Google Search Plugin] 启动模式: {mode_description}", file=sys.stderr)

        common_browser_args = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        
        browser_launcher = None
        if browser_executable == "chromium": browser_launcher = playwright_instance.chromium
        elif browser_executable == "firefox": browser_launcher = playwright_instance.firefox
        elif browser_executable == "webkit": browser_launcher = playwright_instance.webkit
        else: # Fallback, should not happen due to earlier check
            print(f"错误: 不支持的浏览器类型 '{browser_executable}' for Playwright. 使用 Chromium.", file=sys.stderr)
            browser_launcher = playwright_instance.chromium


        if effective_user_data_dir:
            try:
                # launch_persistent_context 只支持 chromium
                if browser_executable != "chromium":
                     print(f"[Google Search Plugin] 警告: 使用用户数据目录 (launch_persistent_context) 当前仅 Playwright 的 Chromium 支持。配置的浏览器是 {browser_executable}。将尝试常规模式启动 {browser_executable}。", file=sys.stderr)
                     # 回退到常规模式
                     browser_instance = await browser_launcher.launch(headless=launch_browser_headless, args=common_browser_args)
                     browser_context = await browser_instance.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Xice_Aitoolbox/SearchPlugin-Regular',
                        locale='zh-CN', timezone_id='Asia/Shanghai'
                     )
                     mode_description += " (回退到常规模式)"
                else:
                    browser_context = await browser_launcher.launch_persistent_context(
                        user_data_dir=effective_user_data_dir,
                        headless=launch_browser_headless,
                        args=common_browser_args,
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.43',
                        locale='zh-CN', timezone_id='Asia/Shanghai',
                    )
                page = await browser_context.new_page()
            except PlaywrightError as pe_persistent:
                err_msg = f"错误：使用本地用户配置 '{effective_user_data_dir}' ({browser_executable}) 启动浏览器失败: {str(pe_persistent)}"
                if browser_closed_by_plugin: err_msg += " (即使在尝试关闭相关进程后依然失败)"
                traceback.print_exc(file=sys.stderr)
                return err_msg
        else: # 常规模式
            browser_instance = await browser_launcher.launch(headless=True, args=common_browser_args) # 常规模式强制headless=True
            browser_context = await browser_instance.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Xice_Aitoolbox/SearchPlugin-Regular',
                locale='zh-CN', timezone_id='Asia/Shanghai'
            )
            page = await browser_context.new_page()

        page_content_html = ""
        final_url_visited = search_url

        try:
            await page.goto(search_url, timeout=page_load_timeout_ms, wait_until='domcontentloaded')
            final_url_visited = page.url
            if wait_after_load_s > 0:
                await page.wait_for_timeout(wait_after_load_s * 1000)
            
            # 尝试处理Cookie弹窗 (仅在非用户配置模式下更可能需要)
            if not effective_user_data_dir:
                consent_selectors = ["button:has-text('Accept all')", "button:has-text('全部同意')", "button:has-text('Reject all')", "button:has-text('全部拒绝')"]
                for selector in consent_selectors:
                    try:
                        button = page.locator(selector).first
                        if await button.is_visible(timeout=1000):
                            await button.click(timeout=1500, force=True)
                            await page.wait_for_timeout(700)
                            break 
                    except Exception: pass
            
            page_content_html = await page.content()
        except PlaywrightTimeoutError:
            page_content_html = await page.content() 
            if not page_content_html: return f"错误({mode_description})：请求谷歌 '{keywords}' 超时 ({page_load_timeout_ms / 1000}s) 且无内容。"
        except PlaywrightError as pe_page:
            traceback.print_exc(file=sys.stderr)
            return f"错误({mode_description})：访问谷歌 '{keywords}' 页面操作失败: {str(pe_page)}"
        
        if not page_content_html: return f"错误({mode_description})：未能从谷歌 '{keywords}' 获取HTML内容。"

        soup = BeautifulSoup(page_content_html, 'html.parser')
        page_title = soup.find('title').string.strip() if soup.find('title') and soup.find('title').string else "未找到标题"

        for s in soup(["script", "style", "noscript", "meta", "link", "header", "footer", "nav", "aside", "form", "input", "button"]): s.decompose()
        
        main_area = soup.find(id="main") or soup.find(id="rcnt") or soup.find("body")
        full_text = main_area.get_text(separator='\n', strip=True) if main_area else soup.get_text(separator='\n', strip=True)
        
        full_text = "\n".join([line.strip() for line in full_text.splitlines() if line.strip()])
        if len(full_text) > max_results_text_length:
            full_text = full_text[:max_results_text_length] + f"...\n[截断至 {max_results_text_length} 字符]"
        if not full_text.strip(): full_text = "未能提取到有效文本。"

        links, extracted_urls = [], set()
        all_a = main_area.find_all('a', href=True) if main_area else soup.find_all('a', href=True)
        for a in all_a:
            href, text = a['href'], ' '.join(a.get_text(strip=True).split())
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')): continue
            
            # 过滤谷歌内部链接
            parsed_href_host = urlparse(urljoin(final_url_visited, href)).netloc
            if "google.com" in parsed_href_host and ("/search?" in href or "/advanced_search" in href or \
                any(s in href for s in ["preferences", "accounts.", "support.", "policies.", "setprefs"])):
                if not text or text.isdigit() or text.lower() in ["images", "videos", "news", "shopping", "maps", "books", "flights", "finance", "图片", "视频", "新闻", "购物", "地图", "图书", "更多", "设置", "工具", "隐私", "条款", "反馈", "登录"]:
                    continue
            
            abs_href = urljoin(final_url_visited, href)
            # 处理谷歌跳转
            if "google.com" in urlparse(abs_href).netloc and ("/url?q=" in abs_href or "/search?sa=U&url=" in abs_href):
                qs_params = parse_qs(urlparse(abs_href).query)
                real_url = (qs_params.get('q') or qs_params.get('url'))
                if real_url and real_url[0]: abs_href = real_url[0]
                else: continue
            
            if urlparse(abs_href).netloc and "google.com" not in urlparse(abs_href).netloc and "googleusercontent.com" not in urlparse(abs_href).netloc:
                 if abs_href not in extracted_urls:
                    links.append({"text": text or "N/A", "url": abs_href})
                    extracted_urls.add(abs_href)
        
        links_output = links[:max_links_to_extract]
        if len(links) > max_links_to_extract: links_output.append({"text": f"... [截断至前 {max_links_to_extract} 条]", "url": ""})
        elif not links: links_output = [{"text": "未找到核心外部链接。", "url": ""}]
        
        links_formatted = "\n".join([f"- {l['text']}: {l['url']}" for l in links_output if l['url']]) or "未找到核心外部链接。"

        output = f"[谷歌搜索关键词]: {keywords}\n[搜索模式]: {mode_description}\n"
        output += f"[结果页标题]: {page_title}\n[实际搜索URL]: {final_url_visited}\n\n"
        output += "[主要文本内容]:\n" + full_text + "\n\n"
        output += "[相关超链接]:\n" + links_formatted
            
        return output.strip()

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"执行谷歌搜索 '{keywords}' (模式: {mode_description}) 时发生顶层错误: {str(e)}"
    finally:
        if page: await page.close()
        if browser_context: await browser_context.close()
        if playwright_instance: await playwright_instance.stop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        keywords_param = sys.argv[1]
        print(f"[Plugin Log] Google Search: Keywords '{keywords_param}', UserDataPath: '{user_data_directory_path}'", file=sys.stderr)
        try:
            result = asyncio.run(perform_google_search(keywords_param))
            print(result)
        except Exception as e:
            print(f"谷歌搜索插件主线程错误: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print(f"错误：执行谷歌搜索时发生内部错误。")
    else:
        print(json.dumps({"status": "错误", "message": "谷歌搜索插件需要关键词参数。"}))
    sys.stdout.flush()
    sys.stderr.flush()
