# Xice_Aitoolbox: 本地AI交互的中间层插件工具箱框架

**Xice_Aitoolbox 是一个强大的、开源的本地中间层框架，旨在通过灵活的插件系统，极大地增强和自定义您与本地AI模型或服务的交互方式。它允许开发者和技术爱好者轻松创建和集成自定义功能（插件），让AI能够执行超出标准聊天范围的各种任务。**

Xice_Aitoolbox 是一个强大的、开源的本地中间层框架，它拦截AI应用的请求，分析AI模型的响应，并根据预设规则或AI的指令调用各种“工具”（即插件）。这些工具可以是读取网页、执行搜索、操作文件、运行代码，乃至任何您能想到的、可以通过脚本实现的功能。

**本项目提供的是一个核心框架和一些基础示例插件。其真正的力量在于您的创造力和您为它构建的插件生态！**

## 目录

1.  [Xice_Aitoolbox：它是什么，为什么你需要它？](#xice_aitoolbox它是什么为什么你需要它)
    *   [核心理念：可扩展的插件框架](#核心理念可扩展的插件框架)
    *   [主要功能特性](#主要功能特性)
2.  [它是如何工作的？(框架流程)](#它是如何工作的框架流程)
3.  [系统架构图（给开发者）](#系统架构图给开发者)
4.  [谁适合使用这个框架？](#谁适合使用这个框架)
5.  [快速开始：部署你的工具箱框架](#快速开始部署你的工具箱框架)
    *   [前提条件：你需要准备什么？](#前提条件你需要准备什么)
    *   [第一步：获取框架代码](#第一步获取框架代码)
    *   [第二步：安装框架核心依赖 (Node.js & Python)](#第二步安装框架核心依赖-nodejs--python)
    *   [第三步：关键配置：连接你的AI环境](#第三步关键配置连接你的ai环境)
    *   [第四步：配置你的AI应用以使用本框架](#第四步配置你的ai应用以使用本框架)
6.  [运行与管理你的工具箱](#运行与管理你的工具箱)
7.  [插件系统：框架的灵魂](#插件系统框架的灵魂)
    *   [通过Web界面管理插件](#通过web界面管理插件-1)
    *   [自带的基础示例插件](#自带的基础示例插件)
    *   [**重点：如何为框架开发你自己的插件**](#重点如何为框架开发你自己的插件)
    *   [高级技巧：谷歌搜索插件的用户配置模式（高风险示例）](#高级技巧谷歌搜索插件的用户配置模式高风险示例)
8.  [对话聚合与显示模式 (`conformchat.txt`)](#对话聚合与显示模式-conformchattxt)
9.  [日志记录与调试](#日志记录与调试)
10. [安全考量：框架与插件的责任](#安全考量框架与插件的责任)
11. [参与贡献：共建框架生态](#参与贡献共建框架生态)
12. [遇到问题？](#遇到问题-1)
13. [许可证](#许可证-1)

## Xice_Aitoolbox：它是什么，为什么你需要它？

在与本地运行的AI模型（例如通过Ollama, LM Studio, Jan等工具，或接入本地反代指向的商业模型）交互时，您可能会发现AI的能力受限于其训练数据和内置功能。Xice_Aitoolbox旨在打破这些限制。

### 核心理念：可扩展的插件框架

Xice_Aitoolbox的核心价值在于它提供了一个**中间层**，这个中间层具备**高度的可扩展性**。它本身不直接提供AI模型，而是：

1.  **拦截**：捕获您的AI应用（如聊天客户端）与您的本地AI服务（或指向云端AI服务的本地反向代理）之间的通信。
2.  **分析**：检查AI模型的回复中是否包含调用特定“工具”的指令（通过预定义的占位符）。
3.  **执行**：如果检测到指令，框架会调用相应的**插件**——这些插件是外部脚本或程序，负责执行具体任务。
4.  **反馈**：插件的执行结果会返回给框架，框架再将其整合到对话流中，反馈给AI模型进行下一步处理，或直接呈现给用户。
5.  **自定义**：最重要的是，您可以**轻松编写和集成自己的插件**，让AI具备几乎无限的本地能力。想让AI控制你的智能家居？整理你的下载文件夹？生成特定格式的报告？只要你能用脚本实现，就能做成插件！

### 主要功能特性

*   **灵活的插件架构**：轻松添加、移除、配置用Python、批处理或其他语言编写的插件。
*   **HTTP流量监听与转发**：作为AI应用和AI服务之间的透明代理。
*   **请求/响应实时记录**：便于调试和分析AI通信 (`send.json`, `received.json`)。
*   **Web配置管理界面**：在浏览器中直观地管理插件和系统全局设置。
*   **AI规则动态注入**：自动向AI的对话中提示当前已启用的插件及其使用方法。
*   **对话聚合 (`conformchat.txt`)**: 将多轮插件调用和AI回复聚合成连贯的最终输出，支持多种显示模式。
*   **跨平台兼容**：基于Python和Node.js，可在Windows, macOS, Linux上运行。

## 它是如何工作的？(框架流程)

1.  **配置**：您将AI应用的请求目标指向Xice_Aitoolbox框架监听的端口。
2.  **接收与分析**：框架的Node.js服务接收到请求。如果是新对话，会初始化`conformchat.txt`。
3.  **规则注入 (可选)**：若配置，框架会将已启用插件的使用规则注入到发送给AI模型的请求中。
4.  **转发至AI模型**：框架将（可能已修改的）请求转发到您在`config.json`中配置的`target_proxy_url`（您的本地AI服务）。
5.  **AI响应**：AI模型处理请求并返回响应给框架。
6.  **插件检测与执行**：
    *   框架分析AI的回复文本，查找是否有匹配已启用插件的“占位符”指令（例如`[我的插件]参数[/我的插件]`）。
    *   **如果找到插件调用**：
        *   框架提取指令和参数。
        *   调用相应的插件脚本/程序（例如，一个Python脚本）。
        *   插件执行任务（如访问API、读写文件、运行命令等）。
        *   插件将其结果输出给框架。
        *   框架将AI的原始回复（占位符之前的部分）和插件的结果（根据显示模式格式化）添加到`conformchat.txt`中，并构建一个新的请求，将这些信息作为上下文再次发送给AI模型（返回步骤4），让AI基于新信息继续对话。
    *   **如果未找到插件调用 (或插件链结束)**：
        *   AI的最终回复被追加到`conformchat.txt`。
        *   框架读取`conformchat.txt`的全部内容，将其作为最终响应发送回给您的AI应用。
        *   清空`conformchat.txt`，为下一次交互做准备。

## 系统架构图（给开发者）
```
sequenceDiagram
    participant UserApp as 用户AI应用
    participant XiceFramework as Xice_Aitoolbox框架 (Node.js + Python)
    participant PluginX as 自定义插件 (e.g., Python脚本)
    participant LocalAIService as 本地AI服务/反代

    UserApp->>+XiceFramework: 1. 发送请求 (例如，包含AI指令)
    XiceFramework->>XiceFramework: 2. 预处理 (日志, 规则注入, conformchat初始化)
    XiceFramework->>+LocalAIService: 3. 转发请求至AI服务
    LocalAIService-->>-XiceFramework: 4. AI模型响应
    XiceFramework->>XiceFramework: 5. 分析AI响应，检测插件占位符
    alt 发现插件调用 (例如 [PluginX]params[/PluginX])
        XiceFramework->>XiceFramework: 6a. 提取参数，记录AI回复片段到conformchat
        XiceFramework->>+PluginX: 7a. 调用插件PluginX并传递参数
        PluginX-->>-XiceFramework: 8a. PluginX返回执行结果
        XiceFramework->>XiceFramework: 9a. 记录插件结果到conformchat
        XiceFramework->>XiceFramework: 10a. 构建包含插件结果的新上下文给AI
        XiceFramework->LocalAIService: 11a. 再次请求AI服务 (循环回步骤3)
    else 无插件调用 或 插件链结束
        XiceFramework->>XiceFramework: 6b. 将最终AI回复记录到conformchat
        XiceFramework->>XiceFramework: 7b. 读取完整的conformchat内容
        XiceFramework-->>-UserApp: 8b. 返回聚合后的最终响应
    end
```
谁适合使用这个框架？

AI爱好者与高级用户：希望赋予本地AI超出聊天框的能力，实现特定自动化任务。

开发者：

需要一个中间层来调试、记录和修改AI模型的输入输出。

希望快速为现有AI应用集成自定义的本地功能或第三方服务。

对构建AI工具、探索AI Agent雏形感兴趣。

需要定制化AI解决方案的团队或个人：利用框架的插件能力，将AI与特定业务流程或私有数据源结合。

快速开始：部署你的工具箱框架
前提条件：你需要准备什么？

确保你的电脑已安装以下软件（安装方法详见上一版README或网上教程）：

Node.js (版本 18.x 或 20.x+ 推荐) - 用于运行框架的核心服务。

检查：命令行输入 node -v 和 npm -v。

Python (版本 3.8+ 推荐) - 用于运行Python插件和框架的某些部分。

检查：命令行输入 python --version (或 python3 --version)。

Windows用户安装时务必勾选 "Add Python to PATH"。

第一步：获取框架代码

从GitHub下载本项目的ZIP包并解压，或使用 git clone。这个解压后的文件夹就是你的“项目根目录”。

第二步：安装框架核心依赖 (Node.js & Python)

Node.js依赖：在项目根目录打开命令行，运行 npm install。

Python依赖：在项目根目录的命令行，运行 pip install -r requirements.txt。

这将安装框架运行和自带示例插件所需的Python库（如playwright, beautifulsoup4等）。

安装Playwright浏览器驱动 (非常重要！)：

python -m playwright install chromium 
# 或 python -m playwright install (安装所有)
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

没有这个，任何依赖浏览器的插件（如网页读取、谷歌搜索）都无法工作。

第三步：关键配置：连接你的AI环境

编辑项目根目录下的 config.json 文件：

target_proxy_url (必需): 设置为你本地AI服务（或反向代理）的URL。例如 "http://localhost:3000"。这是框架将AI请求最终转发到的地方。

proxy_server_port (可选): 框架自身监听的端口，默认为 3001。

其他配置项详见文件内注释或后续章节。

第四步：配置你的AI应用以使用本框架

修改你的AI聊天客户端（或其他AI应用）的API设置，将其API基地址 (Base URL) 指向Xice_Aitoolbox框架的监听地址。

例如：如果proxy_server_port是3001，则AI应用的API基地址应设为 http://localhost:3001。

运行与管理你的工具箱

启动框架服务：

Windows: 双击项目根目录的 start.bat。

macOS/Linux (或手动): 在项目根目录命令行运行 python main.py。

管理插件与配置 (Web界面)：

服务启动后，在浏览器访问 http://localhost:{proxy_server_port}/plugin-manager (默认 http://localhost:3001/plugin-manager)。

在这里你可以启用/禁用插件、添加/编辑插件规则、修改全局配置等。

使用AI应用：正常通过你的AI应用与AI交互。当AI的回复中包含已启用插件的指令时，框架会自动调用插件。

停止框架服务：在运行服务的命令行窗口按 Ctrl + C。

插件系统：框架的灵魂

这是Xice_Aitoolbox最核心的部分。插件是独立的脚本或程序，框架通过AI的指令来调用它们。

通过Web界面管理插件

Web管理界面 (/plugin-manager) 是增删改查和启停插件最便捷的入口。所有插件的定义都保存在项目根目录的 PluginsRule.json 文件中。

自带的基础示例插件

本项目自带了一些基础插件，作为示例和开箱即用的工具：

time_plugin.py: 获取当前系统时间。

directory_lister_plugin.py: 列出指定目录内容。

file_content_reader_plugin.py: 读取文本文件内容。

web_content_reader_plugin.py: 使用Playwright读取动态网页。

google_search_plugin.py: 使用Playwright进行谷歌搜索。

以及一些用于文件操作和命令执行的高风险示例插件（请务必在理解其风险后再考虑启用和配置）。

这些只是示例！框架的强大之处在于你可以轻松添加更多、更复杂的插件。

重点：如何为框架开发你自己的插件

这是发挥Xice_Aitoolbox框架潜力的关键！

构思你的插件：

功能：它要实现什么？例如：获取天气、翻译文本、控制某个API、操作特定应用等。

输入：AI需要提供什么参数给你的插件？例如：城市名、待翻译的文本、API的查询参数等。

输出：你的插件执行完毕后，要返回什么信息给AI？例如：天气预报、翻译结果、API的响应数据等。

编写插件脚本：

语言选择：Python是最常用的选择，因为它有丰富的库并且与框架集成良好。但理论上，任何可以通过命令行调用的可执行文件（如 .bat, .sh, 编译后的 .exe 等）都可以作为插件。

接收参数 (以Python为例):

如果插件 accepts_parameters 为 true，AI在占位符之间提供的文本会作为命令行参数传递给你的Python脚本。

在Python脚本中，可以通过 sys.argv 列表获取。sys.argv[0] 是脚本本身的路径，sys.argv[1] 是第一个参数（即AI提供的完整参数字符串）。

如果参数是JSON格式，你需要在脚本中用 json.loads(sys.argv[1]) 来解析。

返回结果 (以Python为例):

插件需要将其执行结果打印到标准输出 (stdout)。框架会捕获这些输出。

使用 print() 函数即可。确保你的主要输出就是结果本身。

错误处理 (以Python为例):

如果插件执行出错，应该将错误信息打印到标准错误流 (stderr)，例如 print("错误：无法连接到API", file=sys.stderr)。

并且，通过非零退出码告诉框架执行失败，例如 sys.exit(1)。

文件路径：如果插件需要访问其他文件（例如配置文件、模板），推荐使用绝对路径，或相对于插件脚本自身的路径：

import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "my_plugin_config.json")
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END

依赖管理：如果你的Python插件需要第三方库，确保将它们添加到项目的 requirements.txt 文件中，或者在插件的文档中明确指出依赖。

注册插件到框架：

将你的插件脚本（例如 my_amazing_plugin.py）放到项目文件夹内（或者一个固定的、框架能访问到的路径）。

打开Web管理界面 (/plugin-manager) 或直接编辑 PluginsRule.json 文件。

添加一条新的插件定义，包含以下关键信息：

plugin_id: 一个简短、唯一的英文ID，例如 my_amazing_tool。

plugin_name_cn: 插件的中文名称，例如 “我的神奇工具”。

rule_description: 这是给AI看的描述和使用指南。要清晰地说明插件的功能、何时应该使用它、以及调用它时占位符和参数的格式。例如：“当你需要做[某事]时，请回复 [神奇工具]参数1,参数2[/神奇工具]。参数1是...，参数2是...。”

placeholder_start: AI调用插件的起始标记，例如 [神奇工具]。

placeholder_end: AI调用插件的结束标记，例如 [/神奇工具]。

executable_path: 指向你的插件脚本的路径（相对于项目根目录，或者是绝对路径）。例如 my_amazing_plugin.py 或 C:/MyPlugins/my_amazing_plugin.exe。

is_python_script: 如果是Python脚本，设为 true。框架会用 python 命令执行它。

accepts_parameters: 如果插件需要从占位符之间接收参数，设为 true。

is_internal_signal: 几乎总是 false。仅用于极少数框架内部控制信号。

enabled: 设为 true 以启用插件。

测试你的插件：

重启Xice_Aitoolbox框架服务以加载新的插件定义。

通过AI应用，尝试让AI使用你新定义的占位符和参数格式来调用你的插件。

检查框架的控制台日志、send.json、received.json 和插件自身的日志（如果你的插件有打印到stderr）来调试问题。

测试各种正常和异常的输入情况。

高级技巧：谷歌搜索插件的用户配置模式（高风险示例）

自带的 google_search_plugin.py 插件提供了一个高级选项，允许它加载你本地浏览器的用户配置文件（例如Chrome或Edge的User Data Directory）。

目的：尝试通过使用已有的Cookies、登录状态和浏览器指纹来减少被谷歌识别为自动化脚本的几率。

启用方法：编辑 google_search_plugin.py 文件顶部的 USER_DATA_DIRECTORY_PATH 变量，将其设置为你浏览器User Data目录的正确路径。

重大安全警告：

此功能会授予插件脚本访问该浏览器配置文件下所有数据的权限（包括保存的密码、浏览历史、所有网站的Cookies和登录状态等）。

风险极高！ 仅在你完全理解并接受这些风险，并且绝对信任此插件代码和你使用的AI模型时，才应考虑启用。

插件在启用此模式时，会尝试自动关闭所有正在使用该配置文件的相关浏览器进程，这可能导致你正在进行的工作中断。

强烈建议：如果确实需要此功能，请为你的浏览器创建一个全新的、不包含任何敏感信息或个人账户的独立配置文件 (Profile)，专门供此插件使用。

默认情况下，此功能是禁用的 (USER_DATA_DIRECTORY_PATH为空字符串)。

对话聚合与显示模式 (conformchat.txt)

当AI通过插件与外部世界交互时，往往不是一步完成的。例如，AI可能先调用插件A获取信息，然后基于信息A再调用插件B。Xice_Aitoolbox使用一个名为 conformchat.txt 的临时文件来逐步累积这些交互的文本片段（AI的思考、插件的输出）。

最终，当整个交互链完成，conformchat.txt 中的内容会根据你在 config.json (或Web界面) 中设置的 conform_chat_display_mode 选项，被格式化成一个单一、连贯的回复发送给用户。

conform_chat_display_mode 选项:

"detailed_plugin_responses" (默认): 显示AI的思考过程和插件的详细执行结果。适合调试和了解细节。

"compact_plugin_chain": 显示AI的思考过程，但隐藏插件的原始输出，使对话更自然。

"final_ai_response_only": 只显示AI最终的完整回复，过程完全隐藏。用户体验最简洁。

选择哪种模式取决于你对透明度和简洁性的偏好。

日志记录与调试

主控制台日志：start.bat 或 python main.py 运行窗口是你的主要信息来源。

send.json / received.json：记录最新一次与目标AI服务的完整HTTP交互。

conformchat.txt：临时存储对话聚合内容，有助于理解插件链。

插件标准错误流(stderr)：你的插件可以通过 print("debug info", file=sys.stderr) 输出调试信息到主控制台。Playwright插件也会在这里输出大量日志。

安全考量：框架与插件的责任

安全是使用Xice_Aitoolbox框架的首要考虑因素。 框架本身提供机制，但安全性很大程度上取决于你如何配置它以及你编写/使用的插件。

框架的责任：

提供配置选项来限制插件行为（例如，路径白名单，尽管目前部分高风险插件直接允许任意路径）。

清晰地记录插件的调用和执行。

你的责任 (作为框架用户和插件开发者)：

谨慎选择和启用插件：不要运行来源不明或你不完全信任的插件。

理解插件权限：明确每个插件能做什么，特别是那些能操作文件、执行命令或访问网络的插件。

配置路径白名单：对于文件操作类插件，务必在 config.json 中配置严格的 file_operations_allowed_base_paths 和 project_generator_allowed_base_paths_map，将AI的操作限制在安全的、指定的目录下。

警惕“危险”插件：对于标记为“危险”、“极度危险”的插件（如任意文件更新、任意命令执行、代码沙盒），在未完全理解其风险并做好隔离措施前，切勿启用。这些插件默认设计为具有高权限，是为了提供最大的灵活性给高级用户在受控环境中使用，但同时也意味着极高的风险。

用户配置模式的风险：再次强调，让插件加载你的真实浏览器用户数据目录是极度危险的行为。

不轻信AI的输入：AI生成的任何准备传递给插件的参数（如文件路径、URL、命令）都应被视为不可信输入，插件自身需要进行严格的验证和清理，以防范路径遍历、命令注入等安全漏洞。

插件代码安全：如果你自己编写插件，你需要对插件的代码安全负责。避免在插件中引入漏洞。

最小权限原则：始终只授予AI和插件完成其预定任务所必需的最小权限。

Xice_Aitoolbox是一个强大的工具，请以负责任的态度使用它，确保你的系统安全。

参与贡献：共建框架生态

Xice_Aitoolbox的潜力在于社区的共同建设。我们欢迎各种形式的贡献：

分享你的插件：开发了实用的插件？欢迎分享给大家！

改进框架核心：对Node.js服务或Python主程序有改进建议？

完善文档：觉得这份README或其他文档可以更好？

报告Bug或提出功能建议：通过项目的GitHub "Issues" 区。

提交Pull Requests：如果你修复了Bug或实现了新功能。

遇到问题？

仔细阅读本README，特别是安装、配置和安全部分。

检查运行框架的控制台输出，通常能找到错误线索。

查阅GitHub项目的 "Issues" 区，看是否已有解决方案。

若无，请创建一个新的 "Issue"，并提供尽可能详细的信息（操作系统、Node/Python版本、相关配置、错误日志、复现步骤等）。

许可证

本项目采用 ISC许可证

感谢您选择 Xice_Aitoolbox 框架！期待看到您用它创造出令人惊叹的AI应用和工具！
