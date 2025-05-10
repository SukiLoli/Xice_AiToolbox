# Xice_Aitoolbox: 您的本地AI交互增强与控制工具箱

![Xice_Aitoolbox Logo](https://img.shields.io/badge/Xice_Aitoolbox-v1.2.0-blueviolet?style=for-the-badge&logo= πρώτη)
<!-- 版本号可自行更新 -->

**Xice_Aitoolbox** 是一个在您本地计算机上运行的中间层工具箱，旨在监听、记录、增强并精细控制您的AI应用程序与本地AI反代服务之间的HTTP通信。它通过引入一个灵活的插件系统，使得AI助手能够调用外部程序和脚本（例如执行谷歌搜索、读取动态网页、操作本地文件等），从而极大地扩展其实用性和能力边界。

无论您是希望AI更智能的普通用户，还是寻求深入了解和控制AI通信、扩展AI能力的开发者，Xice_Aitoolbox都能为您提供强大的支持。

**核心亮点：**
*   **动态网页交互**：通过Playwright（一种强大的浏览器自动化工具）赋能AI“真实地”浏览网页、执行搜索，有效应对动态内容和部分反爬机制。
*   **本地用户配置模式（可选，高风险）**：允许插件（如谷歌搜索）加载您本机的浏览器用户配置（Cookies、登录状态等），以进一步模拟真实用户行为，但需高度警惕其安全风险。
*   **可视化插件管理**：通过Web界面轻松管理插件的启用/禁用、添加、编辑和删除。
*   **全面的配置与日志**：提供详细的配置选项和日志记录，方便用户和开发者进行调试与监控。

## 目录

1.  [它能做什么？(功能特性)](#它能做什么功能特性)
2.  [它是如何工作的？(简易流程)](#它是如何工作的简易流程)
3.  [系统架构图（给开发者）](#系统架构图给开发者)
4.  [谁适合使用？](#谁适合使用)
5.  [快速开始：安装与配置](#快速开始安装与配置)
    *   [第零步：你需要什么？(前提条件)](#第零步你需要什么前提条件)
    *   [第一步：获取工具箱 (下载项目)](#第一步获取工具箱-下载项目)
    *   [第二步：安装“大脑助手”的依赖 (Node.js)](#第二步安装大脑助手的依赖-nodejs)
    *   [第三步：安装“小工具”的依赖 (Python)](#第三步安装小工具的依赖-python)
    *   [第四步：关键配置 (config.json)](#第四步关键配置-configjson)
    *   [第五步：认识你的AI应用](#第五步认识你的ai应用)
6.  [如何运行 Xice_Aitoolbox](#如何运行-xice_aitoolbox)
7.  [核心功能：强大的插件系统](#核心功能强大的插件系统)
    *   [通过Web界面管理插件](#通过web界面管理插件)
    *   [内置插件概览](#内置插件概览)
    *   [高级技巧：谷歌搜索插件的用户配置模式（高风险）](#高级技巧谷歌搜索插件的用户配置模式高风险)
    *   [开发者：编写你自己的插件](#开发者编写你自己的插件)
8.  [对话聚合功能 (`conformchat.txt`)](#对话聚合功能-conformchattxt)
9.  [查看日志与调试](#查看日志与调试)
10. [安全第一！(重要安全注意事项)](#安全第一重要安全注意事项)
11. [参与贡献](#参与贡献)
12. [遇到问题？](#遇到问题)
13. [许可证](#许可证)

## 它能做什么？(功能特性)

*   **AI的“眼睛”和“手”**：让AI能访问互联网、读取文件、执行命令。
*   **HTTP流量监听与转发**: 监听您AI应用的请求，并将其转发到您指定的本地AI服务地址。
*   **实时记录交互**:
    *   `send.json`: AI应用发送给AI模型的最新请求。
    *   `received.json`: AI模型返回给AI应用的最新响应。
*   **插件化扩展能力**:
    *   **谷歌搜索**: 使用关键词进行谷歌搜索，获取摘要和链接。
    *   **高级网页内容读取**: 使用 **Playwright (无头浏览器)** 抓取动态网页内容。
    *   **文件操作**: 列出目录、读取/更新/删除文件（部分操作有安全风险提示）。
    *   **代码执行**: 在“沙盒”中运行Python或JavaScript代码片段（实验性，高风险）。
    *   **自定义脚本**: 运行批处理文件或任意程序（高风险）。
    *   **插件启用/禁用开关**: 灵活控制哪些工具可用。
*   **Web配置管理界面**: 在浏览器中方便地管理插件和全局系统设置。
*   **AI规则注入**: 自动向AI的对话中提示当前可用的工具及其用法。
*   **对话聚合 (`conformchat.txt`)**: 将AI与插件的多轮交互结果聚合成更连贯的最终回复。
*   **跨平台**: 基于Python和Node.js，可在Windows, macOS, Linux上运行。

## 它是如何工作的？(简易流程)

想象一下：
1.  你的AI聊天软件（**AI应用**）想执行一个复杂任务，比如“用谷歌搜索‘今天天气怎么样’”。
2.  它不直接访问谷歌，而是把这个请求发给 **Xice_Aitoolbox**。
3.  Xice_Aitoolbox 看到请求中包含 `[谷歌搜索]今天天气怎么样[/谷歌搜索]` 这样的特殊指令。
4.  它启动“谷歌搜索”这个小工具（一个Python脚本）。
5.  这个小工具像真人一样打开浏览器（使用Playwright），在谷歌上搜索，然后把结果（网页摘要和链接）告诉Xice_Aitoolbox。
6.  Xice_Aitoolbox 把这个搜索结果再发回给你的AI模型（通过你配置的**本地AI反代**），AI模型就能理解搜索结果并回复你了。
7.  所有这些中间步骤的请求和回复，Xice_Aitoolbox都会记录下来，方便你查看。

(AI应用 ➔ **Xice_Aitoolbox** ➔ 插件执行/本地AI反代 ➔ AI服务商 ➔ 本地AI反代 ➔ **Xice_Aitoolbox** ➔ AI应用)

## 系统架构图（给开发者）

```
sequenceDiagram
    participant AI_App as AI应用 (例如聊天客户端)
    participant XiceTB as Xice_Aitoolbox (localhost:proxy_server_port)
    participant Plugins as XiceTB 插件 (Python/外部程序)
    participant LocalProxy as 目标AI反代 (localhost:target_proxy_url)
    participant AIService as 远程AI服务商

    AI_App->>+XiceTB: 1. HTTP请求 (如 /v1/chat/completions)
    XiceTB->>XiceTB: 2. (若首次) 注入插件规则到请求体
    XiceTB->>XiceTB: 3. Log到 send.json
    XiceTB->>+LocalProxy: 4. 转发请求 (body可能已修改)
    LocalProxy->>+AIService: 5. 与AI服务商通信
    AIService-->>-LocalProxy: 6. AI响应
    LocalProxy-->>-XiceTB: 7. AI响应返回给XiceTB
    XiceTB->>XiceTB: 8. Log到 received.json
    
    alt AI响应中不含插件调用 或 插件链结束
        XiceTB->>XiceTB: 9a. (根据显示模式) 追加AI回复到 conformchat.txt
        XiceTB->>XiceTB: 10a. 读取 conformchat.txt 全部内容
        XiceTB-->>-AI_App: 11a. 发送聚合后的单一JSON响应
        XiceTB->>XiceTB: 12a. (若成功) 清空 conformchat.txt
    else AI响应中检测到启用的插件调用
        XiceTB->>XiceTB: 9b. (根据显示模式) 追加占位符前文本到 conformchat.txt
        XiceTB->>+Plugins: 10b. 执行对应插件 (带参数)
        Plugins-->>-XiceTB: 11b. 插件返回结果 (stdout)
        XiceTB->>XiceTB: 12b. (根据显示模式) 追加插件结果到 conformchat.txt
        XiceTB->>XiceTB: 13b. 构建新请求 (原对话历史 + AI回复 + 插件结果作为 'user' 消息)
        XiceTB-)LocalProxy: 14b. 再次请求AI (返回步骤4)
    end
```
谁适合使用？

AI应用普通用户：希望你的AI助手能上网查资料、看懂网页、帮你搜索。

AI开发者/技术爱好者：需要调试AI通信、扩展AI的本地能力、对Web自动化和中间件感兴趣。

自动化任务探索者：想结合AI的智能与脚本的执行力，完成更复杂的任务。

效率追求者：让AI帮你处理本地文件、运行常用命令。

快速开始：安装与配置

请一步步跟我来，让Xice_Aitoolbox跑起来！

第零步：你需要什么？(前提条件)

你需要两样“法宝”装在你的电脑上：

Node.js (版本 18.x 或 20.x+ 推荐)

是什么？ 一个让JavaScript能在你电脑上跑的工具（不仅仅是在浏览器里）。Xice_Aitoolbox的“大脑中枢”会用到它。

怎么装？

打开 nodejs.org。

下载推荐的LTS版本安装包。

像安装普通软件一样安装它。安装时请确保勾选了类似 "Add to PATH" 的选项。

怎么检查？ 打开你的命令行工具（Windows上是 cmd 或 PowerShell，macOS/Linux上是 Terminal），输入 node -v 然后按回车，再输入 npm -v 按回车。如果都显示版本号，就说明装好了！

Python (版本 3.8+ 推荐)

是什么？ 一种流行的编程语言。Xice_Aitoolbox的各种“小工具”（插件）是用它写的。

怎么装？

打开 python.org。

下载最新的Python 3版本安装包。

Windows用户特别注意：在安装开始界面，务必勾选 "Add Python to PATH" 或 "将Python添加到环境变量" 这个选项，非常重要！然后点 "Install Now"。

怎么检查？ 在命令行里输入 python --version 或 python3 --version，如果显示版本号，就OK。

第一步：获取工具箱 (下载项目)

访问 Xice_Aitoolbox 的 GitHub页面 (请替换为实际链接)。

点击绿色的 "Code" 按钮，然后选择 "Download ZIP"。

下载完成后，解压这个ZIP包到你电脑上一个你喜欢的位置（比如桌面、文档等）。这个文件夹就是我们的“项目根目录”。

第二步：安装“大脑助手”的依赖 (Node.js)

“大脑助手”需要一些辅助工具才能工作。

打开你的命令行工具。

导航到项目根目录：

例如，如果你解压到了桌面的 Xice_Aitoolbox_v1.2 文件夹，你可能需要输入类似 cd C:\Users\你的用户名\Desktop\Xice_Aitoolbox_v1.2 (Windows) 或 cd /Users/你的用户名/Desktop/Xice_Aitoolbox_v1.2 (macOS/Linux)。

小技巧：在文件管理器中打开项目根目录，然后在地址栏输入 cmd (Windows) 或右键选择“在此处打开终端/命令行”(某些系统)可以直接在该目录打开命令行。

在命令行里，输入以下命令并按回车：

npm install
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

这会自动下载并安装所有Node.js需要的依赖项。看到一些进度条和文字输出是正常的。

第三步：安装“小工具”的依赖 (Python)

各种“小工具”（插件）也需要一些Python库的支持。

确保你的命令行还在项目根目录下。

输入以下命令并按回车：

pip install -r requirements.txt
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

这会根据 requirements.txt 文件自动安装所有Python依赖，包括 playwright, beautifulsoup4, requests 和 send2trash。

重要：安装Playwright的“遥控器” (浏览器驱动)
Playwright需要控制一个真实的浏览器来工作。你需要告诉它下载哪个浏览器。
在命令行输入（推荐至少安装Chromium）：

python -m playwright install chromium
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

或者，如果你想一次性安装所有主流浏览器的驱动（Chromium, Firefox, WebKit），可以输入：

python -m playwright install
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

提示：这个步骤会下载浏览器文件，可能需要一些时间和磁盘空间。如果下载慢或失败，请检查你的网络连接，或者尝试更换网络环境。没有浏览器驱动，网页读取和谷歌搜索插件将无法工作！

第四步：关键配置 (config.json)

你需要告诉Xice_Aitoolbox一些重要信息。这些信息都在项目根目录的 config.json 文件里。

在项目根目录找到 config.json 文件。

用文本编辑器打开它（比如记事本、VS Code、Notepad++等）。

最重要的配置项是 target_proxy_url:

这个URL是你本地AI反向代理服务的地址。你的AI应用（如聊天软件）原本是直接和这个地址通信的。

现在，Xice_Aitoolbox会作为中间人。你需要把这个地址填对。

示例：如果你的本地AI反代服务运行在 http://localhost:3000，那么 config.json 中应该是：

"target_proxy_url": "http://localhost:3000",
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Json
IGNORE_WHEN_COPYING_END

新手提示：如果你不确定这个地址是什么，请查看你正在使用的AI聊天软件或反代工具的设置。它通常是一个以 http://localhost: 或 http://127.0.0.1: 开头的地址，后面跟着一个端口号。

（可选）其他配置项：

proxy_server_port: Xice_Aitoolbox自己监听的端口，默认为 3001。通常不需要修改。

conform_chat_display_mode: 控制最终AI回复的详细程度，新手可以暂时不管，用默认的 "detailed_plugin_responses"。

其他配置项的详细说明请参考下文或 config.json 内的注释。

你也可以通过Web界面修改这些配置 (启动服务后访问 http://localhost:3001/plugin-manager，端口号以你的配置为准)。

第五步：认识你的AI应用

最后，你需要让你的AI聊天软件（或其他AI应用）把请求发送给Xice_Aitoolbox，而不是直接发送给原来的本地AI反代地址。

打开你的AI应用的设置界面。

找到API基地址 (Base URL) 或类似的设置项。

将其修改为 http://localhost:{proxy_server_port}，其中 {proxy_server_port} 是你在 config.json 中设置的端口（默认为 3001）。

示例：如果 proxy_server_port 是 3001，那么API基地址就改成 http://localhost:3001。

恭喜！基础安装和配置完成！

如何运行 Xice_Aitoolbox

确保你已经完成了上面的所有安装和配置步骤。 特别是 target_proxy_url 必须正确配置！

确保你的AI应用已经配置为将请求发送给Xice_Aitoolbox的监听端口 (例如 http://localhost:3001)。

启动Xice_Aitoolbox服务：

Windows用户: 直接双击项目根目录下的 start.bat 文件。它会打开一个命令行窗口，并开始运行服务。

macOS/Linux用户 (或手动启动):

打开命令行工具。

导航到项目根目录。

输入 python main.py 并按回车。

观察控制台输出：

你应该会看到一些启动信息，包括Node.js服务监听的端口、目标转发URL、加载的插件数量等。

如果没有严重错误提示，说明服务已成功启动。

开始使用你的AI应用：

正常与你的AI对话。

尝试让AI调用一个已启用的插件，例如：“[获取时间][/获取时间]” 或 “[谷歌搜索]今天的新闻[/谷歌搜索]”。

观察Xice_Aitoolbox的控制台输出，你应该能看到请求被拦截、插件被调用等日志信息。

停止服务：

在Xice_Aitoolbox运行的那个命令行窗口中，按 Ctrl + C 组合键。

系统会提示你是否终止批处理作业，按 Y 然后回车即可。

核心功能：强大的插件系统

插件是Xice_Aitoolbox的灵魂，它们赋予AI执行各种外部任务的能力。

通过Web界面管理插件

这是管理插件最方便的方式。

启动Xice_Aitoolbox服务。

打开你的网页浏览器（如Chrome, Edge, Firefox）。

访问 http://localhost:{proxy_server_port}/plugin-manager (默认是 http://localhost:3001/plugin-manager)。

在这个页面上，你可以：

查看所有已定义的插件列表。

启用或禁用单个插件。

添加新插件：填写插件的ID、名称、给AI的描述、占位符、可执行文件路径等信息。

编辑现有插件。

删除插件。

保存更改到 PluginsRule.json 文件。

管理全局系统配置（config.json 的内容）。

注意：部分全局配置（如端口号）和影响Python插件行为的配置（如路径白名单）修改后，需要重启Xice_Aitoolbox服务 (即重新运行 start.bat 或 python main.py) 才能完全生效。

内置插件概览

以下是一些预置的插件示例（你可以在Web管理界面查看完整列表和详细描述）：

获取当前系统时间 (time_plugin.py)：简单实用。

列出指定目录内容 (directory_lister_plugin.py)：让AI查看文件夹。

读取文件内容 (file_content_reader_plugin.py)：AI可以阅读本地文件。

读取网页内容 (Playwright版) (web_content_reader_plugin.py)：AI的“火眼金睛”，能看懂动态网页。

谷歌搜索 (Playwright版) (google_search_plugin.py)：AI的“超级大脑”，能用谷歌搜索。

更新文件内容 (危险!) (file_updater_plugin.py)：允许AI修改或创建文件，请务必在理解安全风险的前提下启用和配置。

生成项目框架 (危险!) (project_generator_plugin.py)：AI可以帮你搭建项目目录结构，同样有安全风险。

执行代码片段 (沙盒 - 实验性, 危险!) (code_sandbox_plugin.py)：允许AI运行代码，风险极高，默认的沙盒非常不完善，请勿用于不受信任的代码。

删除文件或文件夹 (移至回收站) (file_deleter_plugin.py)：需要配置白名单路径。

运行程序或命令 (极度危险!) (program_runner_plugin.py)：赋予AI执行任意系统命令的能力，安全风险最高，请仅在完全隔离和受控的环境中使用，或确保其被禁用。

继续AI回复 (continue_reply_plugin.py)：一个内部信号插件，帮助AI处理超长回复。

插件的配置文件是项目根目录下的 PluginsRule.json。

高级技巧：谷歌搜索插件的用户配置模式（高风险）

google_search_plugin.py 提供了一个可选的高级模式，可以尝试加载你本地浏览器的用户配置文件 (User Data Directory)。

目的：携带你的Cookies、登录状态等信息访问谷歌，可能有助于减少被识别为机器人。

如何启用：

打开 google_search_plugin.py 文件。

在文件顶部找到 USER_DATA_DIRECTORY_PATH = "" 这一行。

将其修改为你的Chrome或Edge的 "User Data" 目录的绝对路径。文件内有常见操作系统的路径示例。

例如，你提供的路径是 C:\Users\bin\AppData\Local\Microsoft\Edge\User Data，在Python中应写为 USER_DATA_DIRECTORY_PATH = "C:/Users/bin/AppData/Local/Microsoft/Edge/User Data" (注意斜杠方向)。

重要：如果配置了此路径，插件在运行时会尝试自动关闭所有相关的浏览器进程 (例如，关闭所有Edge进程) 以确保能成功加载配置文件。这可能会中断你正在进行的浏览器工作！

安全警告（再次强调！）：

此模式会授予插件访问你浏览器所有数据的权限（密码、历史、登录态等）。

风险极高！请仅在你完全理解并接受这些风险，并且信任此插件代码和调用它的AI时才使用。

强烈建议：为此功能创建一个全新的、干净的浏览器配置文件 (Profile)，专门给这个插件使用，不要用你日常的主配置文件。

如果你不想冒这个风险，或者不想插件自动关闭你的浏览器，请将 USER_DATA_DIRECTORY_PATH 留空。插件会自动回退到不加载用户配置的常规模式。

开发者：编写你自己的插件

想让AI拥有更多超能力？你可以自己动手写插件！

明确功能：你的插件要做什么？接收什么参数？输出什么结果？

编写脚本 (通常是Python)：

参数通过 sys.argv 列表获取 (例如 sys.argv[1] 是第一个参数)。

结果通过 print() 函数输出到标准输出 (stdout)。

错误信息可以打印到标准错误流 (stderr) print("错误信息", file=sys.stderr)，并通过非零退出码 sys.exit(1) 表示执行失败。

Playwright插件：需要使用 asyncio 库，并确保用户已正确安装Playwright和浏览器驱动。

路径管理：如果插件需要访问同目录下的其他文件，建议使用 os.path.join(os.path.dirname(os.path.abspath(__file__)), "文件名") 来构造绝对路径。

放置脚本：将你的 .py 或 .bat 等可执行文件放到Xice_Aitoolbox项目文件夹内（或者一个你知道的绝对路径）。

在Web界面添加插件定义 (或手动编辑 PluginsRule.json)：

提供一个唯一的 plugin_id。

plugin_name_cn：插件的中文名。

rule_description：给AI的提示，告诉它如何使用这个插件（包括占位符和参数格式）。

placeholder_start 和 placeholder_end：AI调用插件时使用的特殊标记，例如 [我的插件] 和 [/我的插件]。

executable_path：你的脚本文件名（如果和proxy_server.js同级）或完整路径。

is_python_script：如果你的插件是Python脚本，勾选此项，系统会用 python 命令执行它。

accepts_parameters：如果你的插件需要接收占位符之间的参数，勾选此项。

is_internal_signal：仅用于特殊内部控制插件（如“继续回复”），普通插件不勾选。

enabled：是否启用此插件。

测试：充分测试你的插件，确保它能按预期工作，并能正确处理各种输入和异常情况。

对话聚合功能 (conformchat.txt)

当AI的回复需要调用多个插件，或者插件的输出需要进一步被AI处理时，Xice_Aitoolbox会将这些中间的文本片段（AI的回复片段、插件的执行结果）逐步累积到一个临时文件 conformchat.txt 中。

当整个插件调用链处理完毕后，Xice_Aitoolbox会将 conformchat.txt 中的完整内容，根据你在 config.json (或Web界面) 中设置的 conform_chat_display_mode，格式化为最终的、单一的、连贯的消息，发送给前端的AI应用。

ConformChat 显示模式 (conform_chat_display_mode):

"detailed_plugin_responses" (模式1: 详细插件响应 - 默认):

最终回复会包含AI的思考片段 + 清晰标记的插件执行结果 + ... + 最终AI总结。

优点：过程完全透明，方便调试和理解AI的思考过程及插件效果。

缺点：最终回复可能显得冗长，包含较多技术性信息。

"compact_plugin_chain" (模式2: 紧凑插件链):

最终回复会包含AI的思考片段 + ... + 最终AI总结。插件的原始输出结果不会直接展示给用户，但会被AI在后台“看到”并用于生成下一步回复。

优点：对话更流畅自然，隐藏了中间的技术细节。

缺点：如果插件执行出错或结果不理想，用户可能不知道问题出在哪里。

"final_ai_response_only" (模式3: 仅最终AI响应):

**只显示整个插件链执行完毕后，AI生成的最后一条完整回复。**所有中间的AI思考片段和插件结果都被隐藏。

优点：用户体验最简洁，就像AI一次性完成了所有事情。

缺点：完全屏蔽了过程，调试困难，用户无法感知插件的运作。

你可以根据自己的需求和偏好，在 config.json 或Web管理界面中选择合适的显示模式。

查看日志与调试

遇到问题时，日志是你的好帮手：

实时控制台日志:

运行 start.bat (Windows) 或 python main.py (macOS/Linux) 的那个命令行窗口会实时显示Node.js服务和Python插件的活动日志，包括请求拦截、插件调用、错误信息等。这是排查问题的第一站。

请求/响应快照:

send.json (项目根目录)：记录了Xice_Aitoolbox发送给目标AI反代的最新一次请求的详细信息（请求头、请求体等）。

received.json (项目根目录)：记录了Xice_Aitoolbox从目标AI反代接收到的最新一次响应的详细信息。

这些文件对于分析AI通信的具体内容非常有用。注意：它们只保存最新一次的交互。

对话聚合临时文件:

conformchat.txt (项目根目录)：在插件调用链处理过程中，用于临时存储AI回复片段和插件结果。可以帮助你理解不同显示模式下的内容聚合过程。它在每次新的对话开始时通常会被清空。

插件特定日志:

Playwright插件 (如网页读取、谷歌搜索) 会在主控制台（stderr流）输出它们详细的导航和操作日志，例如正在访问哪个URL，是否点击了按钮等。

你编写的自定义插件也可以通过 print("调试信息", file=sys.stderr) 输出调试日志到主控制台。

安全第一！(重要安全注意事项)

Xice_Aitoolbox赋予了AI强大的能力，但也带来了潜在的安全风险。请务必仔细阅读并理解以下安全准则：

信任边界在你手中：

你启用的插件、config.json 中的配置（尤其是路径白名单）以及你允许AI执行的操作，共同决定了整个系统的安全边界。

不要启用你不理解或不信任的插件。

目标URL (target_proxy_url) 的信任：

此URL必须指向你完全信任的本地AI反向代理服务。不要将其指向不受信任的外部网络地址。

插件执行权限 - 最小权限原则：

定期审查你启用的插件。对于不常用或具有高风险操作（如文件修改、命令执行）的插件，请在不需要时禁用它们。

Playwright插件 (网页读取/谷歌搜索)：虽然它们模拟真实浏览器，但它们是在你的计算机上以你的网络身份执行操作。确保AI提供的URL或搜索关键词是可信的，避免访问恶意网站或下载恶意文件。

谷歌搜索插件的用户配置模式：如前所述，加载你的真实浏览器用户配置（USER_DATA_DIRECTORY_PATH）风险极高。它允许插件访问你的Cookies、登录会话、浏览历史等。

强烈建议：如果必须使用此功能，请创建一个专用的、干净的浏览器配置文件 (Profile)，不包含任何个人敏感信息，仅供此插件使用。

切勿轻易使用你日常包含重要数据的主浏览器配置文件。

插件会尝试关闭相关浏览器进程，这本身也是一个需要注意的操作。

“危险”标记的插件 - 务必谨慎：

PluginsRule.json 和Web管理界面中，一些插件被明确标记为“危险”、“极度危险”或有高风险。这些插件通常允许AI在更广泛的范围内操作你的计算机（例如，在任意路径更新文件、生成项目结构、执行任意命令或代码）。

除非你完全理解其潜在后果，并且在完全隔离和受控的环境中进行测试，否则不要轻易启用这些插件。

对于日常使用，如果需要类似功能，请确保这些插件通过 config.json 中的路径白名单 (file_operations_allowed_base_paths, project_generator_allowed_base_paths_map) 进行了严格限制，或者干脆禁用它们。

代码沙盒 (code_sandbox_plugin.py)：它提供的“沙盒”环境非常初级，不能提供真正的安全隔离。执行AI提供的未知代码具有极高风险。

参数处理与网络访问：

所有插件都应该对其从AI接收到的参数进行严格的校验和清理，以防止路径遍历、命令注入等攻击。

插件在访问网络资源时应格外小心。

核心原则：不轻信AI的输入：

虽然AI是你的助手，但它生成的内容（包括要操作的文件路径、要执行的命令、要访问的URL）都应被视为不可信输入，需要经过插件或系统的严格校验。

不要给予AI超出其完成任务所必需的最小权限。

Xice_Aitoolbox是一个强大的工具，请负责任地使用它。

参与贡献

我们欢迎各种形式的贡献！

报告Bug：发现问题？请通过项目GitHub页面的 "Issues"板块告诉我们。

功能建议：有好点子？也请通过 "Issues" 分享。

代码贡献：想改进代码或添加新功能？欢迎提交 "Pull Requests"。

文档改进：觉得这份README可以写得更好？也请不吝赐教。

遇到问题？

仔细阅读本README，特别是“快速开始”和“安全注意事项”部分。

检查Xice_Aitoolbox运行的控制台日志，通常错误信息会直接显示在那里。

查看项目GitHub页面的 "Issues" 板块，看看是否有人遇到过类似的问题。

如果找不到答案，请创建一个新的 "Issue"，并提供尽可能详细的信息：

你的操作系统和版本。

Node.js 和 Python 的版本。

相关的 config.json 和 PluginsRule.json 配置内容（请隐去敏感信息如API密钥）。

你具体执行了什么操作？AI的输入是什么？

详细的错误日志或截图。

你期望的结果是什么？实际结果是什么？

许可证

本项目采用 ISC许可证 (或你在项目中指定的其他开源许可证)。

感谢您使用 Xice_Aitoolbox！希望它能为您的AI交互带来更多可能！
