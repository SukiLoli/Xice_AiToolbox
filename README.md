# Xice_Aitoolbox - AI 能力增强中间层工具箱

## 项目愿景

Xice_Aitoolbox 旨在构建一个灵活、可扩展的本地中间层框架，赋予 AI 模型与外部世界交互的能力。通过拦截和处理 AI 应用与本地 AI 服务之间的通信，本工具箱允许 AI 调用自定义插件来执行各种任务，如文件操作、代码执行、网络搜索、网页内容读取等，从而极大地扩展 AI 的应用场景和实用性。

### *警告：请谨慎使用本工具箱，尤其是涉及文件操作和命令执行的插件。确保您完全理解相关风险，并仅在受信任的环境中使用。配置不当可能导致数据丢失或系统安全问题。*

## 核心特性

*   **强大的插件化架构**:
    *   所有插件迁移至根目录下的 `Plugin/` 文件夹。
    *   每个插件拥有独立的子文件夹，包含其执行脚本和专属的 `config.json` 配置文件。
    *   框架自动扫描并加载 `Plugin/` 目录下的所有合规插件。
*   **插件调用协议**: AI 通过在回复中嵌入特定格式的占位符指令 (例如 `[插件占位符开始]参数[插件占位符结束]`) 来请求插件执行。
*   **灵活的配置管理**:
    *   **全局配置 (`config.json`)**:位于项目根目录，用于设置核心服务参数（如端口、目标URL）、日志选项、插件递归深度等。
    *   **插件专属配置 (`Plugin/<插件名>/config.json`)**: 每个插件文件夹内包含一个 `config.json`，定义该插件的元数据（ID、名称、描述、执行方式、占位符等）以及插件特有的可配置参数。
*   **Web 配置管理界面**:
    *   在服务启动时（可配置是否自动）打开浏览器界面。
    *   实时获取和修改根目录的 `config.json` (系统全局配置)。
    *   实时获取和修改所有已发现插件的 `config.json` (插件基础配置及插件独有配置)。
    *   每个插件的配置都在界面上拥有独立的区域，便于管理和查看。
*   **动态插件规则注入**: 可配置在首次请求时，将所有已启用插件的描述和调用方式自动注入到发送给 AI 模型的系统提示中。
*   **非流式响应处理**: 框架目前专注于处理 AI 的非流式响应，分析响应内容以调用插件，并将插件结果反馈给 AI 进行后续处理，或聚合成最终结果返回给用户。
*   **路径权限控制**: 根 `config.json` 中的 `file_operations_allowed_base_paths` 字段（现已移除，但类似概念应由插件自行处理或在插件配置中指明依赖的全局路径）旨在提供一定程度的文件系统访问控制。**注意：当前版本为了自由度，部分插件（如文件更新、项目生成、程序运行）默认允许AI指定任意路径，风险由用户承担。**
*   **对话聚合与显示 (`conformchat.txt`)**: 框架使用 `conformchat.txt` 临时存储多轮 AI-插件交互的文本片段，并根据 `config.json` 中的 `conform_chat_display_mode` 设置，将聚合内容作为最终响应发送给用户。

## 系统架构概览

```
sequenceDiagram
    participant UserApp as 用户AI应用
    participant XiceFramework_NodeJS as Xice_Aitoolbox (Node.js Proxy)
    participant PluginScript as 插件脚本 (Python/Bat/etc.)
    participant LocalAIService as 本地AI服务/反代

    UserApp->>+XiceFramework_NodeJS: 1. 发送请求 (例如，聊天消息)
    XiceFramework_NodeJS->>XiceFramework_NodeJS: 2. (可选) 注入插件规则到请求体
    XiceFramework_NodeJS->>XiceFramework_NodeJS: 3. 记录请求到 send.json
    XiceFramework_NodeJS->>+LocalAIService: 4. 转发请求至AI服务
    LocalAIService-->>-XiceFramework_NodeJS: 5. AI模型响应
    XiceFramework_NodeJS->>XiceFramework_NodeJS: 6. 记录响应到 received.json
    XiceFramework_NodeJS->>XiceFramework_NodeJS: 7. 分析AI响应，检测插件占位符
    alt 发现插件调用 (例如 [插件名]参数[/插件名])
        XiceFramework_NodeJS->>XiceFramework_NodeJS: 8a. 提取参数，记录AI回复片段到 conformchat.txt
        XiceFramework_NodeJS->>+PluginScript: 9a. 调用插件脚本 (位于 Plugin/<插件名>/) 并传递参数
        PluginScript-->>-XiceFramework_NodeJS: 10a. 插件脚本返回执行结果 (stdout)
        XiceFramework_NodeJS->>XiceFramework_NodeJS: 11a. 根据显示模式，格式化并记录插件结果到 conformchat.txt
        XiceFramework_NodeJS->>XiceFramework_NodeJS: 12a. 构建包含插件结果的新上下文给AI
        XiceFramework_NodeJS->>LocalAIService: 13a. 再次请求AI服务 (循环回步骤4)
    else 无插件调用 或 插件链结束
        XiceFramework_NodeJS->>XiceFramework_NodeJS: 8b. 将最终AI回复记录到 conformchat.txt
        XiceFramework_NodeJS->>XiceFramework_NodeJS: 9b. 读取完整的 conformchat.txt 内容
        XiceFramework_NodeJS-->>-UserApp: 10b. 返回聚合后的最终响应 (JSON格式)
    end
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Markdown
IGNORE_WHEN_COPYING_END
```

客户端请求: 用户通过 AI 应用向 Xice_Aitoolbox 监听的端口发送请求。

Node.js 代理 (proxy_server.js):

接收请求。

如果配置了 inject_plugin_rules_on_first_request 且是合适的时机，将已启用插件的描述和用法注入到请求的系统消息中。

记录预备发送给 AI 服务的请求到 send.json (如果启用了日志)。

将请求转发到 config.json 中定义的 target_proxy_url (即用户的本地 AI 服务或反代)。

AI 模型响应: AI 服务处理请求并返回响应给 Node.js 代理。

Node.js 代理处理 AI 响应:

记录从 AI 服务收到的原始响应到 received.json (如果启用了日志)。

分析 AI 的回复文本，查找是否存在与已加载并启用的插件的占位符相匹配的指令。

如果包含插件调用:

提取指令中的参数。

将占位符之前（如果存在）的 AI 回复文本追加到 conformchat.txt。

调用位于相应插件目录下的插件执行脚本 (例如 Plugin/time/time_plugin.py)，并将参数传递给它。

插件脚本执行任务，并将结果输出到其标准输出 (stdout)。

Node.js 代理捕获插件的输出。根据 conform_chat_display_mode 的设置，可能会将插件的原始输出或格式化后的结果追加到 conformchat.txt。

Node.js 代理构建一个新的请求，将插件的执行结果作为新的用户消息（或系统消息，取决于实现）添加到对话历史中。

重复步骤 2，再次调用 AI 模型，让其基于插件的结果继续生成。此过程有最大递归深度限制。

如果 AI 响应中不包含插件调用，或插件调用链结束:

将 AI 的最终回复（或当前轮次的回复）追加到 conformchat.txt。

Node.js 代理读取 conformchat.txt 的全部内容。

将 conformchat.txt 的内容包装成符合 AI 服务响应格式的 JSON 对象，发送回给用户的 AI 应用。

清空 conformchat.txt，为下一次交互做准备。

Web 配置管理界面

为了方便用户管理系统配置和各个插件的配置，项目提供了一个 Web 管理界面。

主要功能:

系统配置管理:

在线预览和编辑项目根目录下 config.json 文件的内容。

可修改端口、目标 URL、日志选项、插件行为参数等。

插件配置管理:

自动发现并列出 Plugin/ 目录下的所有插件。

为每个已发现的插件生成独立的配置区域。

用户可以编辑每个插件 config.json 文件中的所有字段，包括：

插件元数据：ID (通常不可修改)、名称、版本、描述、作者。

插件行为：是否启用、是否为 Python 脚本、可执行文件名、占位符、是否接受参数、是否为内部信号。

插件特定配置 (plugin_specific_config)：动态生成表单字段，允许用户修改插件独有的配置项（如超时时间、路径、API密钥等）。

实时性: 配置的更改会直接写入对应的 config.json 文件。

访问:

启动 Xice_Aitoolbox 服务 (运行 start.bat 或 python main.py)。

如果根 config.json 中的 auto_open_browser_config 设置为 true (默认)，配置界面会自动在浏览器中打开。

或者，手动在浏览器中访问 http://localhost:<proxy_server_port>/plugin-manager (例如，http://localhost:3001/plugin-manager)。

注意: 修改某些配置（如服务端口、影响 Python 插件启动时加载的配置）后，可能需要手动重启 Xice_Aitoolbox 服务 (start.bat) 才能使更改完全生效。

已实现插件示例 (部分列举)

time: 获取当前系统时间。

directory_lister: 列出指定目录的内容。

file_content_reader: 读取指定文件的文本内容（有大小和输出长度限制）。

file_deleter: 将指定文件或文件夹移动到回收站（受限于根 config.json 中 file_operations_allowed_base_paths 的白名单配置）。

file_updater: 更新或创建指定路径的文件内容。（高风险：默认允许任意路径，请谨慎使用）

project_generator: 根据给定的结构在指定基础路径创建项目框架。（高风险：默认允许任意路径，请谨慎使用）

code_sandbox: 在沙盒环境中执行 Python 或 JavaScript (Node.js) 代码片段。

program_runner: 在指定的（可选）工作目录下运行任意程序或命令。（极高风险：默认允许任意命令和CWD，请极端谨慎使用）

google_search: 使用 Playwright 进行谷歌搜索并提取结果。

web_content_reader: 使用 Playwright 读取网页的动态内容。

continue_reply: 一个内部信号插件，允许 AI 请求继续生成长回复。

插件调用方式

AI 模型通过在其生成的文本中包含特定格式的占位符来调用插件。通用格式为：
[插件起始占位符]插件参数（如果插件接收参数）[插件结束占位符]

例如：

获取时间: [获取时间][/获取时间]

列出目录: [列出目录]./my_project[/列出目录]

执行代码: [执行代码]{"language": "python", "code": "print('hello')"}[/执行代码]

每个插件的具体占位符和参数格式在其各自的 Plugin/<插件名>/config.json 文件的 description 字段中应有详细说明，这些说明会（如果启用了规则注入）提供给 AI。

安装与运行

前提条件:

Node.js: 版本 18.x 或更高版本。从 nodejs.org 下载并安装。

Python: 版本 3.8 或更高版本。从 python.org 下载并安装，安装时务必勾选 "Add Python to PATH"。

克隆或下载项目:

git clone https://github.com/your_username/Xice_Aitoolbox.git # 替换为实际仓库地址
cd Xice_Aitoolbox
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

或者下载 ZIP 包并解压。

安装主依赖 (Node.js): 在项目根目录下打开命令行/终端，运行：

npm install
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

安装 Python 插件依赖: 在项目根目录下运行：

pip install -r requirements.txt
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

这会安装如 playwright, beautifulsoup4, send2trash 等库。

安装 Playwright 浏览器驱动: (对于需要浏览器操作的插件，如网页读取、谷歌搜索)

python -m playwright install chromium 
# 或者安装所有支持的浏览器驱动: python -m playwright install
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

配置:

核心配置: 编辑项目根目录下的 config.json。至少需要配置 target_proxy_url 指向您的本地 AI 服务地址。其他配置项可根据需要调整。

AI 应用配置: 修改您的 AI 聊天客户端（或其他 AI 应用）的 API 设置，将其 API 基地址 (Base URL) 指向 Xice_Aitoolbox 框架的监听地址（例如，http://localhost:3001，端口号取决于 config.json 中的 proxy_server_port）。

插件配置: 服务启动后，通过 Web 配置界面 (http://localhost:<port>/plugin-manager) 检查并按需修改各个插件的配置。

启动服务器:

Windows: 双击项目根目录下的 start.bat。

macOS/Linux (或手动): 在项目根目录的命令行/终端中运行 python main.py。

使用: 通过您的 AI 应用与 AI 交互。当 AI 的回复中包含已启用插件的指令时，框架会自动调用插件。

开发者指南：创建新插件

创建插件目录: 在项目根目录的 Plugin/ 文件夹下为您的新插件创建一个唯一的子文件夹，例如 Plugin/MyNewPlugin/。

编写插件执行脚本:

在插件目录中创建主执行文件 (例如 my_new_plugin.py 或 my_new_plugin.bat)。

输入: 如果插件接受参数 (在插件的 config.json 中 accepts_parameters 为 true)，参数会作为单个字符串通过命令行参数传递给脚本 (例如，在 Python 中通过 sys.argv[1])。如果参数是 JSON 结构，插件脚本需要自行解析 (例如 json.loads(sys.argv[1]))。

输出: 插件的执行结果应打印到标准输出 (stdout)。Node.js 代理会捕获此输出。

错误: 错误信息可以打印到标准错误流 (stderr)，Node.js 代理也会捕获。非零退出码通常表示执行失败。

依赖: 如果是 Python 插件且有外部库依赖，请确保这些库已包含在项目根目录的 requirements.txt 中，或在插件文档中明确指出安装需求。

创建插件配置文件 (config.json):

在插件目录 (Plugin/MyNewPlugin/) 中创建 config.json 文件。

核心字段 (必需):

plugin_id (string): 插件的唯一标识符 (例如, "my_new_plugin")。一旦设定，不应轻易更改，因为AI的调用依赖此ID（间接通过占位符）。

plugin_name_cn (string): 插件的中文名称 (例如, "我的新插件")。

executable_name (string): 插件目录内可执行脚本的文件名 (例如, "my_new_plugin.py")。

placeholder_start (string): AI 调用此插件的起始占位符 (例如, "[新插件开始]")。

placeholder_end (string): AI 调用此插件的结束占位符 (例如, "[/新插件结束]")。

常用字段 (推荐):

version (string): 插件版本 (例如, "1.0.0")。

description (string): 给 AI 的详细描述，说明插件功能、何时使用、参数格式（如果 accepts_parameters 为 true）、预期输出格式等。这是 AI 理解如何使用插件的关键。

author (string): 插件作者。

enabled (boolean): 插件是否默认启用 (默认为 true)。

is_python_script (boolean): 是否为 Python 脚本 (默认为 true)。如果为 false，Node.js 会尝试直接执行 executable_name (对于 .bat 文件，在 Windows 上会使用 shell: true)。

accepts_parameters (boolean): 插件是否接受占位符之间的参数 (默认为 false)。

is_internal_signal (boolean): 是否为内部信号插件，如 "继续回复" (默认为 false)。

可选字段:

parameters (array of objects): (可选，主要用于未来更精细的 UI 生成或参数校验) 描述插件接受的参数的模式。每个对象可包含:

name (string): 参数名。

type (string): 参数类型 (例如, "string", "number", "boolean", "json_string")。

description (string): 参数描述。

required (boolean): 是否必需。

default: 默认值。

plugin_specific_config (object): (可选) 包含插件独有的配置项及其默认值。这些配置项可以在 Web 界面的插件配置区域被用户修改。例如:

"plugin_specific_config": {
    "api_key": "YOUR_API_KEY_HERE",
    "timeout_seconds": 30,
    "max_retries": 3,
    "feature_x_enabled": true,
    "allowed_file_types": ["txt", "md", "json"]
}
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Json
IGNORE_WHEN_COPYING_END

插件脚本在执行时，应尝试从其自身的 config.json 文件中读取这些 plugin_specific_config 的值，如果读取失败或特定项不存在，则使用脚本内部定义的后备默认值。

测试:

重启 Xice_Aitoolbox 服务。

打开 Web 配置界面，检查新插件是否被发现，并确认其配置是否正确显示。

按需修改插件的配置（尤其是 enabled 状态和 plugin_specific_config 中的项）。

通过您的 AI 应用，尝试让 AI 调用新插件。观察控制台日志和 conformchat.txt (如果适用) 进行调试。

安全考量

插件权限: 插件（尤其是那些执行代码、读写文件、运行命令的插件）具有与其运行环境（通常是 Xice_Aitoolbox 服务运行用户）相同的权限。请务必谨慎。

“危险”插件: 对于名称中包含 "unsafe", "危险", "任意路径" 等字样的插件，它们通常被设计为提供最大的灵活性，但也带来了最高的安全风险。这些插件默认可能允许 AI 指定任意文件路径或执行任意命令。除非您完全理解这些风险，并在严格隔离和受控的环境中使用，否则强烈建议禁用这些插件，或通过修改其 plugin_specific_config（如果插件支持）来限制其操作范围。

用户责任: 框架提供工具，但最终的安全责任在于用户如何配置和使用这些工具及插件。

不运行来源不明的插件。

仔细审查插件代码（如果可能）。

最小权限原则: 仅授予必要的权限。如果插件不需要写权限，确保其运行环境没有不必要的写权限。

警惕 AI 的输入: AI 可能生成意外或恶意的参数传递给插件。插件自身应尽可能进行输入验证和清理。

Web 配置界面: 虽然配置界面本身不直接执行高危操作，但它修改的是可能影响系统行为的配置文件。确保您的运行环境安全。

未来展望

流式响应支持: 探索对 AI 流式响应的更完善处理，包括在流式输出中检测和处理插件调用。

插件间通信: 研究更高级的插件间直接通信或数据共享机制。

更细致的权限控制: 考虑引入更精细的、基于每个插件的权限声明和控制系统。

异步插件模型: 完善对长时间运行的异步插件的支持。

更丰富的插件生态: 鼓励社区贡献更多实用和创新的插件。

许可证 (License)

本项目采用 Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) 许可证。

简单来说，这意味着您可以：

共享 — 在任何媒介以任何形式复制、发行本作品。

演绎 — 修改、转换或以本作品为基础进行创作。
只要你遵守许可协议条款，许可人就无法收回你的这些权利。

惟须遵守下列条件：

署名 (BY) — 您必须给出适当的署名，提供指向本许可的链接，同时标明是否（对原始作品）作了修改。您可以用任何合理的方式来署名，但是不得以任何方式暗示许可人为您或您的使用背书。

非商业性使用 (NC) — 您不得将本作品用于商业目的。

相同方式共享 (SA) — 如果您再混合、转换或者基于本作品进行创作，您必须基于与原先许可协议相同的许可协议分发您贡献的作品。

详情请参阅 LICENSE.md 文件。

免责声明与使用限制

开发阶段: 本 Xice_Aitoolbox 项目目前仍处于积极开发阶段。可能存在未知的错误、缺陷或不完整的功能。

按原样提供: 本项目按“原样”和“可用”状态提供，不附带任何形式的明示或暗示的保证。

风险自负: 您理解并同意，使用本项目的风险完全由您自行承担。对于因使用或无法使用本项目（包括其插件）而导致的任何直接、间接损害，开发者不承担任何责任。

无商业化授权: 鉴于项目采用的 CC BY-NC-SA 4.0 许可证，明确禁止将本项目及其衍生作品用于任何主要的商业目的。

API 使用成本: 部分插件可能依赖于第三方 API 服务，这些服务可能会产生费用。您有责任了解并承担使用这些 API 所产生的任何成本。

安全责任: 请勿在插件的 config.json (尤其是 plugin_specific_config 部分) 中硬编码或提交真实的、敏感的 API 密钥到公共代码库。请妥善保管您的密钥和敏感配置。

感谢您使用 Xice_Aitoolbox！

