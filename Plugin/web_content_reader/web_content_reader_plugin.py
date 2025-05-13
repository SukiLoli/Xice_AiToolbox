import sys
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import traceback
import os
import json # 新增

# --- 默认配置 ---
DEFAULT_BROWSER_EXECUTABLE = "chromium"
DEFAULT_PAGE_LOAD_TIMEOUT_MS = 30 * 1000
DEFAULT_WAIT_AFTER_LOAD_S = 3
DEFAULT_MAX_TEXT_LENGTH = 20000
DEFAULT_MAX_LINKS = 25

# --- 加载插件配置 ---
browser_executable = DEFAULT_BROWSER_EXECUTABLE
page_load_timeout_ms = DEFAULT_PAGE_LOAD_TIMEOUT_MS
wait_after_load_s = DEFAULT_WAIT_AFTER_LOAD_S
max_text_length = DEFAULT_MAX_TEXT_LENGTH
max_links_to_extract = DEFAULT_MAX_LINKS

try:
    plugin_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(plugin_config_path):
        with open(plugin_config_path, 'r', encoding='utf-8') as f:
            plugin_config_data = json.load(f)
            psc = plugin_config_data.get("plugin_specific_config", {})
            browser_executable = psc.get("default_browser_type", DEFAULT_BROWSER_EXECUTABLE).lower()
            page_load_timeout_ms = psc.get("page_load_timeout_ms", DEFAULT_PAGE_LOAD_TIMEOUT_MS)
            wait_after_load_s = psc.get("wait_after_load_seconds", DEFAULT_WAIT_AFTER_LOAD_S)
            max_text_length = psc.get("max_text_length", DEFAULT_MAX_TEXT_LENGTH)
            max_links_to_extract = psc.get("max_links_to_extract", DEFAULT_MAX_LINKS)

            if browser_executable not in ["chromium", "firefox", "webkit"]:
                print(f"警告: 插件配置中指定的浏览器类型 '{browser_executable}' 无效，将回退到 'chromium'。", file=sys.stderr)
                browser_executable = "chromium"
except Exception as e:
    print(f"警告: 读取插件 web_content_reader 配置 ({plugin_config_path}) 失败: {e}. 将使用默认值。", file=sys.stderr)


async def get_dynamic_webpage_content_with_playwright(url: str):
    resolved_url_for_error_msg = url
    playwright_instance = None
    browser_context = None
    page = None

    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme: url_with_scheme = 'http://' + url.lstrip('/')
        elif not parsed_url.netloc: return f"错误：URL '{url}' 格式不正确 (无域名)。"
        else: url_with_scheme = url
        
        final_parsed_url = urlparse(url_with_scheme)
        if not all([final_parsed_url.scheme, final_parsed_url.netloc]):
            return f"错误：URL '{url}' (修正为 '{url_with_scheme}') 格式不正确。"
        resolved_url_for_error_msg = url_with_scheme

        playwright_instance = await async_playwright().start()
        
        browser_launcher = None
        if browser_executable == "chromium": browser_launcher = playwright_instance.chromium
        elif browser_executable == "firefox": browser_launcher = playwright_instance.firefox
        elif browser_executable == "webkit": browser_launcher = playwright_instance.webkit
        else: # Fallback
            browser_launcher = playwright_instance.chromium

        browser_instance = await browser_launcher.launch(headless=True) # 通常网页读取用headless
        browser_context = await browser_instance.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36 Xice_Aitoolbox/WebReader',
            java_script_enabled=True,
        )
        page = await browser_context.new_page()

        page_content_html = ""
        final_url_visited = url_with_scheme

        try:
            await page.goto(url_with_scheme, timeout=page_load_timeout_ms, wait_until='domcontentloaded')
            final_url_visited = page.url
            if wait_after_load_s > 0:
                await page.wait_for_timeout(wait_after_load_s * 1000)
            page_content_html = await page.content()
        except PlaywrightTimeoutError:
            page_content_html = await page.content()
            if not page_content_html: return f"错误：请求URL '{url_with_scheme}' 超时 ({page_load_timeout_ms / 1000}s) 且无内容。"
        except PlaywrightError as pe_page:
            traceback.print_exc(file=sys.stderr)
            return f"错误：访问URL '{url_with_scheme}' 页面操作失败: {str(pe_page)}"
        
        if not page_content_html: return f"错误：未能从URL '{url_with_scheme}' 获取HTML内容。"

        soup = BeautifulSoup(page_content_html, 'html.parser')
        title = soup.find('title').string.strip() if soup.find('title') and soup.find('title').string else "未找到标题"

        for s in soup(["script", "style", "header", "footer", "nav", "aside", "form", "noscript", "iframe", "button", "input", "select", "textarea", "link", "meta"]):
            s.decompose()
        
        main_area = soup.find('article') or soup.find('main') or soup.body or soup
        body_text_content = main_area.get_text(separator='\n', strip=True) if main_area else ""
        
        if not body_text_content.strip(): body_text_content = soup.get_text(separator='\n', strip=True) # Fallback

        full_text = "\n".join([line.strip() for line in body_text_content.splitlines() if line.strip()])
        if len(full_text) > max_text_length:
            full_text = full_text[:max_text_length] + f"...\n[内容过长，截断至 {max_text_length} 字符]"
        if not full_text.strip(): full_text = "未能提取到有效文本内容。"

        links = []
        if main_area:
            for a_tag in main_area.find_all('a', href=True):
                link_text, raw_href = a_tag.get_text(strip=True), a_tag['href']
                if not raw_href or raw_href.startswith(('#', 'javascript:', 'mailto:', 'tel:')): continue
                try:
                    absolute_href = urljoin(final_url_visited, raw_href)
                    parsed_abs_href = urlparse(absolute_href)
                    if not parsed_abs_href.scheme or not parsed_abs_href.netloc: continue
                except Exception: continue
                if link_text and absolute_href: links.append(f"- {link_text}: {absolute_href}")
        
        links_output_str = "\n".join(links[:max_links_to_extract])
        if len(links) > max_links_to_extract: links_output_str += f"\n- ... [链接列表过长，截断至前 {max_links_to_extract} 条]"
        elif not links: links_output_str = "未找到有效超链接。"

        output = f"[网页标题]: {title}\n[原始请求URL]: {url}\n[最终访问URL]: {final_url_visited}\n\n"
        output += "[主要文本内容]:\n" + full_text + "\n\n"
        output += "[提取到的超链接]:\n" + links_output_str
            
        return output.strip()

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"处理URL '{resolved_url_for_error_msg}' 时发生顶层错误: {str(e)}"
    finally:
        if page: await page.close()
        if browser_context: await browser_context.close()
        if playwright_instance: await playwright_instance.stop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url_param = sys.argv[1]
        print(f"[Plugin Log] Web Content Reader: URL '{url_param}'", file=sys.stderr)
        try:
            result = asyncio.run(get_dynamic_webpage_content_with_playwright(url_param))
            print(result)
        except Exception as e:
            print(f"网页读取插件主线程错误: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print(f"错误：执行网页读取插件时发生内部错误。")
    else:
        print(json.dumps({"status": "错误", "message": "网页读取插件需要URL参数。"}))
    sys.stdout.flush()
    sys.stderr.flush()
