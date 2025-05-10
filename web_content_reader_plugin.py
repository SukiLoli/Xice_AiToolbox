import sys
import asyncio # Playwright 的异步API需要asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import traceback # 用于打印详细错误

# --- Playwright 全局设置 ---
# 我们可以选择一个默认浏览器，比如 chromium
DEFAULT_BROWSER = "chromium"
# 页面加载超时 (秒)
PAGE_LOAD_TIMEOUT = 30 * 1000 # Playwright 使用毫秒
# 获取内容后的等待时间，给动态内容一些加载机会 (秒)
WAIT_AFTER_LOAD = 3 # 秒

async def get_dynamic_webpage_content_with_playwright(url: str):
    """
    使用 Playwright (无头浏览器) 获取动态加载的网页内容。
    """
    resolved_url_for_error_msg = url # 用于错误消息中显示原始请求的URL

    try:
        # 1. 验证并补充 URL scheme
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url_with_scheme = 'http://' + url.lstrip('/') # 简单处理，避免 "http:///example.com"
        elif not parsed_url.netloc:
            return f"错误：提供的URL '{url}' 格式不正确 (缺少域名部分)。"
        else:
            url_with_scheme = url
        
        final_parsed_url = urlparse(url_with_scheme)
        if not all([final_parsed_url.scheme, final_parsed_url.netloc]):
            return f"错误：提供的URL '{url}' (尝试修正为 '{url_with_scheme}') 格式不正确。"
        
        resolved_url_for_error_msg = url_with_scheme


        async with async_playwright() as p:
            browser = None
            try:
                if DEFAULT_BROWSER == "chromium":
                    browser = await p.chromium.launch(headless=True)
                elif DEFAULT_BROWSER == "firefox":
                    browser = await p.firefox.launch(headless=True)
                elif DEFAULT_BROWSER == "webkit":
                    browser = await p.webkit.launch(headless=True)
                else:
                    return f"错误：配置了不支持的浏览器类型 '{DEFAULT_BROWSER}'"
            except PlaywrightError as pe: # 捕获浏览器启动错误
                print(f"--- Web Content Reader (Playwright): Browser launch error ---", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return f"错误：启动浏览器 '{DEFAULT_BROWSER}' 失败。请确保已运行 'python -m playwright install {DEFAULT_BROWSER}'。错误: {str(pe)}"


            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36 Xice_Aitoolbox/1.1-Playwright',
                java_script_enabled=True,
                # viewport={'width': 1280, 'height': 720} # 可选：设置视口
            )
            page = await context.new_page()

            page_content_html = ""
            final_url_visited = url_with_scheme # 初始设为请求的URL

            try:
                print(f"[Playwright] Navigating to: {url_with_scheme}", file=sys.stderr)
                # 'domcontentloaded' 或 'load' 或 'networkidle'
                # 'networkidle' 通常等待网络平静，但可能导致非常慢的页面超时
                await page.goto(url_with_scheme, timeout=PAGE_LOAD_TIMEOUT, wait_until='domcontentloaded')
                final_url_visited = page.url # 获取跳转后的最终URL

                if WAIT_AFTER_LOAD > 0:
                    print(f"[Playwright] Waiting for {WAIT_AFTER_LOAD}s after load for dynamic content...", file=sys.stderr)
                    await page.wait_for_timeout(WAIT_AFTER_LOAD * 1000)

                page_content_html = await page.content() # 获取渲染后的HTML
                print(f"[Playwright] Successfully fetched content from {final_url_visited}", file=sys.stderr)

            except PlaywrightTimeoutError:
                # 即便超时，也尝试获取已加载的部分内容
                print(f"[Playwright] Timeout while loading {url_with_scheme}. Attempting to get partial content.", file=sys.stderr)
                page_content_html = await page.content() # 尝试获取当前内容
                if not page_content_html:
                    return f"错误：请求URL '{url_with_scheme}' 超时 ({PAGE_LOAD_TIMEOUT / 1000}秒) 且未能获取任何内容。"
                # 如果有部分内容，则继续处理，但会在结果中提示超时
            except PlaywrightError as pe_page: #捕获页面导航或操作相关的Playwright错误
                print(f"--- Web Content Reader (Playwright): Page operation error ---", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return f"错误：访问URL '{url_with_scheme}' 时页面操作失败: {str(pe_page)}"
            finally:
                await context.close()
                await browser.close()

        # --- 使用 BeautifulSoup 解析 Playwright 获取到的 HTML ---
        if not page_content_html:
             return f"错误：未能从URL '{url_with_scheme}' 获取到HTML内容 (可能是空页面)。"

        soup = BeautifulSoup(page_content_html, 'html.parser')

        title_tag = soup.find('title')
        title = title_tag.string.strip() if title_tag and title_tag.string else "未找到标题"

        tags_to_remove = ["script", "style", "header", "footer", "nav", "aside", "form", "noscript", "iframe", "button", "input", "select", "textarea", "link", "meta"]
        for tag_name in tags_to_remove:
            for tag_element in soup.find_all(tag_name):
                tag_element.decompose()
        
        # 文本提取逻辑与之前类似，但作用于Playwright渲染后的HTML
        main_content_tags = soup.find_all(['article', 'main', 'div']) 
        body_text_content = ""
        if main_content_tags:
            article_tag = soup.find('article')
            main_tag = soup.find('main')
            if article_tag: body_text_content = article_tag.get_text(separator='\n', strip=True)
            elif main_tag: body_text_content = main_tag.get_text(separator='\n', strip=True)
            else:
                body_tag = soup.body
                if body_tag: body_text_content = body_tag.get_text(separator='\n', strip=True)
        elif soup.body:
             body_text_content = soup.body.get_text(separator='\n', strip=True)
        
        if not body_text_content:
            body_text_content = soup.get_text(separator='\n', strip=True)

        lines = [line.strip() for line in body_text_content.splitlines()]
        cleaned_lines = []
        for line in lines:
            if line: cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1]: cleaned_lines.append("") 
        while cleaned_lines and not cleaned_lines[-1]: cleaned_lines.pop()
        full_text = "\n".join(cleaned_lines)

        max_text_length = 15000 # Playwright可能获取更多内容，适当增加
        if len(full_text) > max_text_length:
            full_text = full_text[:max_text_length] + f"...\n[内容过长，已截断至 {max_text_length} 字符]"
        
        if not full_text.strip():
            full_text = "未能提取到有效的网页主要文本内容 (经过动态渲染后)。"

        # 链接提取逻辑与之前类似
        links = []
        content_area_for_links = soup.find('article') or soup.find('main') or soup.body or soup
        if content_area_for_links:
            for a_tag in content_area_for_links.find_all('a', href=True):
                link_text = a_tag.get_text(strip=True)
                raw_href = a_tag['href']
                if not raw_href or raw_href.startswith(('#', 'javascript:', 'mailto:', 'tel:')): continue
                try:
                    absolute_href = urljoin(final_url_visited, raw_href) # 使用Playwright访问的最终URL作为base
                    parsed_abs_href = urlparse(absolute_href)
                    if not parsed_abs_href.scheme or not parsed_abs_href.netloc: continue
                except Exception: continue
                if link_text and absolute_href: links.append(f"- {link_text}: {absolute_href}")
        
        max_links = 20
        if len(links) > max_links:
            links_output = links[:max_links]
            links_output.append(f"- ... [链接列表过长（共{len(links)}条），已截断至前 {max_links} 条]")
        elif not links: links_output = ["未找到有效超链接。"]
        else: links_output = links

        output = f"[网页标题]: {title}\n"
        output += f"[原始请求URL]: {url}\n" 
        output += f"[最终访问URL (Playwright)]: {final_url_visited}\n\n"
        output += "[主要文本内容 (动态渲染后)]:\n"
        output += f"{full_text}\n\n"
        output += "[提取到的超链接]:\n" + "\n".join(links_output)
            
        return output.strip()

    except Exception as e:
        print(f"--- Web Content Reader (Playwright): Unhandled Exception (Outer) ---", file=sys.stderr)
        print(f"URL: {resolved_url_for_error_msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"使用Playwright处理URL '{resolved_url_for_error_msg}' 时发生了一个顶层未知错误。管理员请查看服务器日志。错误: {str(e)}"

# 主执行逻辑，调用异步函数
if __name__ == "__main__":
    if len(sys.argv) > 1:
        url_param = sys.argv[1]
        print(f"[Plugin Log] Web Content Reader (Playwright): Received URL '{url_param}'", file=sys.stderr)
        try:
            # Python 3.7+ has asyncio.run
            result = asyncio.run(get_dynamic_webpage_content_with_playwright(url_param))
            print(result)
        except Exception as e:
            print(f"执行Playwright网页读取插件时发生主线程错误: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            # 返回一个错误信息给AI
            print(f"错误：执行网页读取插件时发生严重内部错误。详情请查看服务器日志。")

    else:
        print("错误：读取网页内容插件(Playwright版)需要一个URL作为参数。请使用格式：[读取网页]网页URL[/读取网页]")
    sys.stdout.flush()
    sys.stderr.flush() # 确保错误流也被刷新