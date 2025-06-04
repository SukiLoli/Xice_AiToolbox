# Xice_Aitoolbox - AI 能力增强中间层工具箱 (v0.2.0)

---

## 1. 项目概述 (Project Overview)

-   **项目名称**: Xice_Aitoolbox - AI 能力增强中间层工具箱
-   **核心理念**: 本项目旨在构建一个灵活、可扩展的本地中间层框架，赋予 AI 模型与外部世界交互的能力。通过拦截和处理 AI 应用与本地 AI 服务之间的通信，本工具箱允许 AI 调用自定义插件来执行各种任务，如文件操作、代码执行、网络搜索、网页内容读取等，从而极大地扩展 AI 的应用场景和实用性。
-   **主要实现**:
    -   **强大的插件化架构**: 插件迁移至统一的 `Plugin/` 文件夹，每个插件拥有独立子文件夹及 `config.json`。
    -   **灵活的配置管理**: 通过根 `config.json` 和各插件的 `config.json` 进行全局及插件专属配置。
    -   **Web 配置管理界面**: 提供实时编辑系统及插件配置的 Web UI。
    -   **动态插件规则注入**: 可选在首次请求时向 AI 注入已启用插件的规则。
    -   **非流式响应处理**: 专注于处理 AI 的非流式响应，支持 AI-插件的多轮交互。
    -   **对话聚合与显示**: 使用 `conformchat.txt` 聚合交互过程，并根据配置模式返回最终结果。
-   ***警告***: **请谨慎使用本工具箱，尤其是涉及文件操作和命令执行的插件。确保您完全理解相关风险，并仅在受信任的环境中使用。配置不当可能导致数据丢失或系统安全问题。**

## 2. 项目目标 (Project Goals)

-   **赋能AI**: 扩展AI模型的能力边界，使其能够执行超越文本生成的复杂任务。
-   **灵活性与可扩展性**: 提供一个易于开发者创建和集成新插件的框架。
-   **用户友好性**: 通过Web界面简化配置管理过程。
-   **交互透明化**: 记录和展示AI与插件的交互流程，便于调试和理解。
-   **实用性**: 聚焦于提升AI在实际应用中的效能和自主性。

## 3. 当前已实现功能 (Current Implemented Features)

### 3.1. 核心框架特性 (Core Framework Features)

-   **插件化架构**:
    -   所有插件均位于项目根目录下的 `Plugin/` 文件夹内。
    -   每个插件作为一个独立的子文件夹存在，其中包含其执行脚本（如 `.py`, `.js`, `.bat`）和专属的 `config.json` 配置文件。
    -   框架在启动时会自动扫描 `Plugin/` 目录，加载所有符合规范的插件及其配置。
-   **插件调用协议**:
    -   AI 模型通过在其生成的回复文本中嵌入特定格式的占位符指令来请求插件执行。
    -   通用格式为：`[插件起始占位符]参数内容[插件结束占位符]` (例如: `[列出目录]./my_folder[/列出目录]`)。
-   **分层配置管理**:
    -   **全局配置文件 (`config.json`)**: 位于项目根目录。用于设置核心服务参数（如代理端口、目标AI服务URL）、日志记录选项、插件最大递归深度、对话聚合显示模式等。
    -   **插件专属配置文件 (`Plugin/<插件名>/config.json`)**: 每个插件的子文件夹内都有一个 `config.json`。它定义了该插件的元数据（如ID、中文名称、版本、描述、作者）、执行方式（脚本类型、可执行文件名）、AI调用占位符、是否接受参数、是否为内部信号等，以及插件特有的可配置参数（`plugin_specific_config`）。
-   **动态插件规则注入**:
    -   可配置在首次与AI交互时，将所有已启用插件的描述、功能及调用方式（占位符格式）自动注入到发送给AI模型的系统提示 (system prompt) 中，引导AI正确使用插件。
-   **非流式响应的复杂处理**:
    -   框架专注于处理AI的非流式（一次性完整返回）响应。
    -   能够分析AI响应内容，检测插件调用指令。
    -   执行插件后，将插件的输出结果反馈给AI，形成新的上下文，让AI可以基于插件结果进行进一步的思考和生成，支持多轮 AI-插件 交互。
    -   最终将整个交互过程（根据配置）聚合成对用户友好的最终结果。
-   **路径权限警示与用户责任**:
    -   原 `file_operations_allowed_base_paths` 字段已移除，部分高风险插件（如文件更新、项目生成、程序运行）默认允许AI指定任意路径。**这些插件的使用风险由用户自行承担。** 强烈建议用户在使用这些插件前，仔细阅读其说明，并在插件的 `plugin_specific_config` 中（如果插件支持）配置路径白名单或限制，或者直接禁用这些高风险插件。
-   **对话聚合与显示 (`conformchat.txt`)**:
    -   框架使用位于项目根目录的 `conformchat.txt` 文件作为临时存储区。
    -   在AI与插件的多轮交互过程中，AI的回复片段和插件的执行结果（根据显示模式）会依次追加到此文件中。
    -   当整个调用链结束时，框架会读取 `conformchat.txt` 的完整内容，并根据根 `config.json` 中 `conform_chat_display_mode` 的设置（如“详细插件响应”、“紧凑插件链”或“仅最终AI响应”），将其格式化后作为最终响应发送给用户。
    -   每次新的用户请求开始时，`conformchat.txt` 会被清空。

### 3.2. Web 配置管理界面 (Web Configuration Management Interface)

-   **便捷访问**: 服务启动时，可配置是否自动在默认浏览器中打开配置管理界面。用户也可手动访问 `http://localhost:<proxy_server_port>/plugin-manager`。
-   **系统配置实时编辑**:
    -   允许用户在线预览和修改位于项目根目录的 `config.json` 文件的所有内容。
    -   可调整的参数包括：代理服务监听端口、目标AI服务URL、日志记录行为（如是否记录拦截数据、是否在Python控制台显示Node.js日志、是否在received.json中记录响应体）、插件行为参数（最大插件递归深度、最大继续回复深度）、ConformChat显示模式、是否在首次请求时注入插件规则、项目生成器路径映射、文件操作允许的基础路径等。
-   **插件配置集中管理**:
    -   自动发现并以列表形式展示 `Plugin/` 目录下的所有已识别插件。
    -   为每个插件提供独立的配置区域，允许用户查看和修改该插件的 `config.json` 文件内容。
    -   可编辑的插件元数据包括：插件中文名称、版本号、作者、给AI的描述（影响规则注入）、是否启用该插件。
    -   可编辑的插件执行配置包括：脚本类型（Python, Node.js, 可执行文件）、插件目录内的可执行文件名、AI调用该插件的起始和结束占位符、插件是否接受参数、是否为内部信号插件（如“继续回复”）。
    -   **插件特定配置 (`plugin_specific_config`)**: 如果插件的 `config.json` 中定义了 `plugin_specific_config` 对象，Web界面会动态生成对应的表单字段，允许用户修改这些插件独有的配置项（例如，特定插件的API密钥、超时时间、路径限制、功能开关等）。
-   **即时保存**: 对系统配置或任何插件配置的更改，在点击保存后会立即写入对应的 `.json` 文件。
-   **重启提示**: 对于某些需要重启Xice_Aitoolbox主服务（如 `start.bat` 或 `python main.py`）才能完全生效的配置更改（例如代理端口、影响Python环境的路径配置），界面会给予提示。

### 3.3. 已实现插件示例 (Implemented Plugin Examples)

-   **time**: 获取当前系统时间。
-   **directory_lister**: 列出指定目录的内容。
-   **file_content_reader**: 读取指定文件的文本内容（有大小和输出长度限制）。
-   **file_deleter**: 将指定文件或文件夹移动到回收站。
-   **file_updater (高风险)**: 更新或创建指定路径的文件内容。**默认允许AI指定任意路径，请极端谨慎使用！**
-   **project_generator (高风险)**: 根据给定的结构在指定基础路径创建项目框架。**默认允许AI指定任意路径，请极端谨慎使用！**
-   **code_sandbox**: 在沙盒环境中执行 Python 或 JavaScript (Node.js) 代码片段。
-   **program_runner (极高风险)**: 在指定的（可选）工作目录下运行任意程序或命令。**默认允许AI指定任意命令和CWD，请极端谨慎使用！**
-   **google_search**: 使用 Playwright 进行谷歌搜索并提取结果。
-   **web_content_reader**: 使用 Playwright 读取网页的动态内容。
-   **continue_reply**: 一个内部信号插件，允许 AI 请求继续生成长回复，不直接返回内容给用户，而是触发框架继续向AI请求。
-   **daily_note_writer**: 记录包含角色名、日期和内容的日记到指定目录结构。

## 4. 核心系统实现详解 (Core Systems Deep Dive)

### 4.1. 系统架构 (System Architecture)

-   **概览**: Xice_Aitoolbox 作为中间层，拦截用户AI应用与本地AI服务之间的通信。它解析AI的响应，根据特定指令调用相应插件执行任务，并将插件结果反馈给AI，实现AI能力的扩展。

-   **Mermaid 流程图**:
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
    ```

-   **流程详解**:
    1.  **客户端请求**: 用户通过其AI应用（如聊天客户端）向Xice_Aitoolbox监听的端口发送API请求（通常是符合OpenAI或其他大模型服务接口规范的JSON请求）。
    2.  **Node.js代理 (`proxy_server.js`) 接收与预处理**:
        -   代理服务器接收到请求。
        -   如果根 `config.json` 中配置了 `inject_plugin_rules_on_first_request: true`，并且是合适的时机（例如，对话的开始或特定条件下），代理会将所有已启用插件的描述和调用方式（占位符格式）自动注入到请求体中的系统消息 (system prompt) 部分。
        -   如果启用了日志记录 (`log_intercepted_data: true`)，代理会将预备发送给目标AI服务的请求内容（包括头部和处理过的请求体）记录到项目根目录下的 `send.json` 文件中。
        -   代理根据根 `config.json` 中定义的 `target_proxy_url`，将（可能已修改的）请求转发到用户本地的AI服务或另一个反向代理。
    3.  **AI模型响应**: 本地AI服务处理请求，并将AI模型的原始响应返回给Node.js代理。
    4.  **Node.js代理处理AI响应**:
        -   代理接收到AI的响应。如果启用了日志记录，会将从AI服务收到的原始响应（包括状态码、头部和响应体）记录到 `received.json` 文件中。响应体大小会根据 `max_log_response_size_kb_in_received_file` 进行限制。
        -   代理核心逻辑开始分析AI响应的文本内容（通常是 `choices[0].message.content` 或类似字段），查找是否存在与任何已加载并启用的插件的占位符相匹配的指令。
    5.  **插件调用流程 (如果检测到插件指令)**:
        -   **指令提取**: 如果匹配到插件占位符（例如 `[插件A开始]参数XYZ[/插件A结束]`），代理会提取占位符之间的参数内容（`参数XYZ`）。
        -   **内容暂存**: 占位符之前（如果存在）的AI回复文本会被追加到项目根目录的 `conformchat.txt` 文件中。这个文件用于累积多轮AI与插件交互的对话片段。
        -   **插件执行**: 代理根据插件的 `config.json` 中定义的 `executable_name` 和 `script_type` (Python, Node.js, 或其他可执行文件)，在对应的插件目录 (例如 `Plugin/插件A/`) 下启动插件脚本，并将提取到的参数传递给它（通常作为命令行参数或通过stdin，取决于插件设计）。
        -   **结果捕获**: 插件脚本执行其任务（如文件操作、API调用、代码执行等），并将结果输出到其标准输出 (stdout)。Node.js代理会捕获这个输出。
        -   **结果记录**: 根据根 `config.json` 中 `conform_chat_display_mode` 的设置，插件的原始输出或经过格式化（例如，添加"\[插件 插件A 执行结果\]: ..."的前缀）的结果会被追加到 `conformchat.txt`。
        -   **构建新上下文**: Node.js代理将插件的执行结果包装成一条新的用户消息（或系统消息，具体取决于实现策略），并将其添加到原始的对话历史（从 `send.json` 或当前请求中获取）之后。
        -   **递归调用AI**: 代理使用这个包含插件结果的新对话历史，重新构建一个请求体，并返回到流程的第2步（预处理并再次调用本地AI服务）。这个递归调用过程有最大深度限制（`max_plugin_recursion_depth`），以防止无限循环。
    6.  **无插件调用或插件链结束**:
        -   如果AI的当前响应中不包含任何插件调用指令，或者插件调用链因为达到最大深度或AI不再调用插件而自然结束。
        -   AI的最终回复（或当前轮次的非插件调用回复）会被追加到 `conformchat.txt`。
        -   Node.js代理读取 `conformchat.txt` 的全部累积内容。
        -   代理将 `conformchat.txt` 的内容包装成一个符合目标AI服务响应格式的JSON对象（例如，模拟一个OpenAI的`chat.completion`对象），然后将这个聚合后的最终响应发送回给最初发起请求的用户AI应用。
        -   最后，`conformchat.txt` 文件通常会被清空，为下一次独立的用户请求-响应交互做准备。

### 4.2. 插件调用机制 (Plugin Invocation Mechanism)

-   **占位符驱动**: AI模型通过在其生成的文本回复中包含特定格式的占位符来触发插件的执行。
-   **通用格式**: `[插件起始占位符]插件参数（如果插件接收参数）[插件结束占位符]`
-   **参数传递**:
    -   如果插件的 `config.json` 中 `accepts_parameters` 设置为 `true`，占位符之间的文本内容（去除首尾空格后）会作为参数传递给插件脚本。
    -   参数通常以单个字符串的形式通过命令行参数（例如，在Python中通过 `sys.argv[1]`）传递。
    -   如果插件期望接收复杂的JSON结构作为参数，AI需要在占位符之间提供合法的JSON字符串，插件脚本内部需要负责解析这个JSON字符串（例如，在Python中使用 `json.loads(sys.argv[1])`）。
-   **插件配置**:
    -   每个插件的 `config.json` 文件中必须定义 `placeholder_start` 和 `placeholder_end` 字段，这两个字段共同构成了调用该插件的唯一指令。
    -   `description` 字段应详细说明插件的功能、使用场景、参数格式（如果适用）以及预期的输出格式。这些信息在启用“规则注入”时会提供给AI，以指导其正确使用插件。
-   **示例**:
    -   **获取时间**: `[获取时间][/获取时间]` (无参数)
    -   **列出目录**: `[列出目录]./my_project[/列出目录]` (参数为相对路径 `./my_project`)
    -   **执行Python代码**: `[执行代码]{"language": "python", "code": "print('hello from AI')"}[/执行代码]` (参数为一个JSON字符串)
-   **处理流程**:
    1.  Node.js代理在收到AI的响应后，会遍历所有已启用的插件。
    2.  对于每个插件，代理会使用其配置的起始和结束占位符构建正则表达式，在AI的回复文本中进行匹配。
    3.  一旦匹配成功，代理会提取参数，执行相应的插件脚本，并将插件的输出结果用于后续处理（可能再次调用AI或作为最终结果的一部分）。
    4.  框架目前不支持在单次AI回复中处理多个不同的插件调用；它会处理第一个匹配到的插件指令。如果需要多个插件操作，AI应分步骤、在多次回复中逐个调用。

### 4.3. 对话聚合与显示 (`conformchat.txt`)

-   **用途**: `conformchat.txt` 文件位于项目根目录，作为AI与插件多轮交互过程中的一个临时文本聚合区。
-   **聚合内容**:
    -   当AI的回复中包含插件调用指令时，指令占位符之前的部分文本会被追加到 `conformchat.txt`。
    -   插件执行完毕后，其结果（可能经过格式化）也会根据配置追加到 `conformchat.txt`。
    -   如果AI在插件执行后继续生成文本（在下一次调用中，或作为插件调用后的直接延续），这部分文本也会被追加。
-   **显示模式 (`conform_chat_display_mode`)**: 此配置项位于根目录的 `config.json` 文件中，决定了最终如何处理和展示 `conformchat.txt` 的内容给用户。可选模式包括：
    -   **`detailed_plugin_responses`**: 详细显示AI的每段回复和每个插件的完整执行结果。
    -   **`compact_plugin_chain`**: 可能尝试更紧凑地展示AI思考链和插件结果，减少冗余。
    -   **`final_ai_response_only`**: 可能只显示AI在整个插件调用链结束后的最终总结性回复，隐藏中间的插件交互细节（具体实现可能依赖AI的配合）。
-   **最终输出**: 当整个AI-插件交互链结束（即AI的最新回复不再包含插件调用，或达到最大递归深度），`proxy_server.js` 会读取 `conformchat.txt` 的完整内容，将其作为最终的助手回复内容，包装成标准的API响应格式（如OpenAI的聊天完成格式）返回给客户端。
-   **清理**: 在一次完整的用户请求-响应周期结束后（即最终响应已发送给客户端），`conformchat.txt` 的内容会被清空，为下一次新的交互做准备。

## 5. 技术栈 (Technical Stack)

-   **后端核心 (Node.js Proxy Server - `proxy_server.js`)**:
    -   **运行时**: Node.js (版本 >=18.0.0 推荐)
    -   **Web框架**: Express.js (用于处理HTTP请求，提供API接口和Web配置界面)
    -   **HTTP客户端**: `node-fetch` (v2.x, 用于向目标AI服务转发请求)
    -   **文件系统操作**: Node.js 内置 `fs`模块 (`fs.promises` 和 `fsSync`)
    -   **子进程管理**: Node.js 内置 `child_process`模块 (用于执行插件脚本)
    -   **日志**: `morgan` (HTTP请求日志)
    -   **环境变量**: `dotenv` (虽然在`package.json`中列出，但当前版本似乎主要通过`config.json`管理配置)
-   **主启动与管理脚本 (`main.py`)**:
    -   **语言**: Python (版本 >=3.8 推荐)
    -   **功能**: 负责启动Node.js代理服务器作为子进程，并监控其运行状态。提供跨平台启动便利（通过`start.bat`）。
    -   **依赖**: Python标准库 (subprocess, os, sys, threading, json, time, re, webbrowser)。
-   **插件脚本执行环境**:
    -   **Python**: 大部分插件使用Python编写。
        -   **核心依赖 (见 `requirements.txt`)**:
            -   `playwright` (用于需要浏览器自动化的插件，如谷歌搜索、网页内容读取)
            -   `beautifulsoup4` (用于HTML内容解析)
            -   `requests` (用于插件内部进行HTTP请求，虽然Playwright也能做，但requests更轻量)
            -   `send2trash` (用于安全删除文件到回收站)
    -   **Node.js**: 部分插件可使用Node.js编写 (例如 `daily-note-write.js`)。
    -   **其他可执行文件**: 支持执行系统原生的可执行文件或批处理/Shell脚本 (如 `.bat`, `.sh`, `.exe`)。
-   **前端 (Web 配置管理界面 - `plugin_manager.html`, `plugin_manager.js`)**:
    -   **语言**: HTML, CSS, JavaScript (Vanilla JS)
    -   **无外部框架**: 直接使用原生Web技术实现。
-   **配置文件格式**:
    -   **JSON**: 所有配置文件 (`config.json` 全局配置及各插件配置) 均使用JSON格式。
-   **日志与临时文件**:
    -   `send.json`: 记录发送到目标AI服务的请求。
    -   `received.json`: 记录从目标AI服务接收的响应。
    -   `conformchat.txt`: 临时存储AI与插件交互的聚合文本。

## 6. 项目结构 (Project Structure)

```
/Xice_AiToolbox-main/
|-- .gitignore
|-- AiGeneratedProjects/      # (示例) AI插件可能操作的目录
|-- AiManagedFiles/           # (示例) AI插件可能操作的目录
|-- LICENSE.md
|-- MyDiaries/                # (示例) daily_note_writer插件的默认数据存储路径
|   |-- dailynote/
|       |-- 小白/
|           |-- 2024.07.05-22_25_19.txt
|           |-- ...
|-- Plugin/                   # 插件根目录
|   |-- code_sandbox/         # 代码沙盒插件
|   |   |-- code_sandbox_plugin.py
|   |   |-- config.json
|   |-- continue_reply/       # 继续回复插件
|   |   |-- config.json
|   |   |-- continue_reply_plugin.py
|   |-- daily_note_writer/    # 日记写入插件
|   |   |-- README.md
|   |   |-- config.json
|   |   |-- daily-note-write.js
|   |-- directory_lister/     # 目录列表示例插件
|   |   |-- config.json
|   |   |-- directory_lister_plugin.py
|   |-- file_content_reader/  # 文件内容读取插件
|   |   |-- config.json
|   |   |-- file_content_reader_plugin.py
|   |-- file_deleter/         # 文件删除插件
|   |   |-- config.json
|   |   |-- file_deleter_plugin.py
|   |-- file_updater/         # 文件更新插件 (高风险)
|   |   |-- config.json
|   |   |-- file_updater_plugin.py
|   |-- google_search/        # 谷歌搜索插件
|   |   |-- config.json
|   |   |-- google_search_plugin.py
|   |-- program_runner/       # 程序运行插件 (极高风险)
|   |   |-- config.json
|   |   |-- program_runner_plugin.py
|   |-- project_generator/    # 项目生成插件 (高风险)
|   |   |-- config.json
|   |   |-- project_generator_plugin.py
|   |-- web_content_reader/   # 网页内容读取插件
|   |   |-- config.json
|   |   |-- web_content_reader_plugin.py
|-- README.txt                # 本文档的原始文本文件
|-- config.json               # 全局配置文件
|-- conformchat.txt           # AI与插件交互的临时聚合文本
|-- generated_projects_default/ # (示例) AI插件可能操作的目录
|-- main.py                   # Python主启动脚本
|-- node_modules/             # Node.js依赖
|-- package-lock.json
|-- package.json              # Node.js项目元数据和依赖
|-- plugin_manager.html       # Web配置界面的HTML文件
|-- plugin_manager.js         # Web配置界面的JavaScript文件
|-- proxy_server.js           # Node.js代理服务器核心逻辑
|-- received.json             # 记录从AI服务收到的响应
|-- requirements.txt          # Python插件的依赖列表
|-- send.json                 # 记录发送到AI服务的请求
|-- start.bat                 # Windows启动脚本
```

## 7. 安装与启动 (Setup and Running Instructions)

### 7.1. 前提条件 (Prerequisites)

-   **Node.js**: 版本 18.x 或更高版本。请从 [nodejs.org](https://nodejs.org/) 下载并安装。
-   **Python**: 版本 3.8 或更高版本。请从 [python.org](https://python.org/) 下载并安装。安装时，请务必勾选 "Add Python to PATH" (将Python添加到系统路径) 选项。
-   **Git (推荐)**: 用于克隆项目。

### 7.2. 项目设置 (Project Setup)

1.  **克隆或下载项目**:
    -   使用Git克隆 (推荐):
        ```bash
        git clone [https://github.com/your_username/Xice_Aitoolbox.git](https://github.com/your_username/Xice_Aitoolbox.git) # 请替换为实际的仓库地址
        cd Xice_Aitoolbox
        ```
    -   或者，从项目源下载ZIP压缩包并解压到您的本地计算机。
2.  **安装 Node.js 依赖**:
    -   打开命令行/终端，导航到项目根目录 (例如 `Xice_Aitoolbox/`)。
    -   运行以下命令来安装Node.js代理服务器所需的依赖包 (如Express.js, node-fetch等):
        ```bash
        npm install
        ```
3.  **安装 Python 插件依赖**:
    -   在项目根目录下，运行以下命令来安装Python插件可能需要的库 (如Playwright, BeautifulSoup4, send2trash等):
        ```bash
        pip install -r requirements.txt
        ```
4.  **安装 Playwright 浏览器驱动 (如果需要使用相关插件)**:
    -   如果计划使用依赖Playwright的插件（例如 `google_search`, `web_content_reader`），需要安装相应的浏览器驱动。建议至少安装Chromium：
        ```bash
        python -m playwright install chromium
        ```
    -   若要安装所有Playwright支持的浏览器驱动，可以运行：
        ```bash
        python -m playwright install
        ```
5.  **配置核心参数 (`config.json`)**:
    -   编辑位于项目根目录下的 `config.json` 文件。
    -   **最重要的配置项是 `target_proxy_url`**: 必须将其设置为您本地AI服务或反向代理的正确访问地址 (例如 `http://localhost:8000/v1` 或您的AI服务商提供的本地代理地址)。
    -   其他配置项如 `proxy_server_port` (Xice_Aitoolbox自身监听的端口，默认为3001), `log_intercepted_data` (是否记录send/received.json), `conform_chat_display_mode` 等可以根据需要进行调整。
6.  **配置AI应用**:
    -   修改您正在使用的AI聊天客户端或其他AI应用程序的API设置。
    -   将其API基地址 (Base URL 或 API Endpoint) 指向Xice_Aitoolbox框架的监听地址。例如，如果 `config.json` 中的 `proxy_server_port` 设置为 `3001` (默认值)，则AI应用应连接到 `http://localhost:3001` (如果您的AI服务路径是 `/v1/chat/completions`，则应用中可能是 `http://localhost:3001/v1/chat/completions`，具体取决于您的AI服务路径结构)。
7.  **检查插件配置 (可选，推荐)**:
    -   服务首次启动后，建议通过Web配置界面 (默认为 `http://localhost:3001/plugin-manager`) 检查所有已发现插件的配置。
    -   确保您理解每个已启用插件的功能和潜在风险，特别是高风险插件。根据需要调整插件的 `enabled` 状态或其 `plugin_specific_config` 中的参数。

### 7.3. 启动服务 (Starting the Service)

-   **Windows 用户**:
    -   确保已完成上述所有设置步骤。
    -   双击项目根目录下的 `start.bat` 文件。此脚本会自动启动Python主程序 (`main.py`)，后者会再启动Node.js代理服务器。
-   **macOS/Linux 用户 (或手动启动)**:
    -   打开命令行/终端，导航到项目根目录。
    -   运行以下命令来启动Python主程序：
        ```bash
        python main.py
        ```
-   服务启动成功后，您会在Python控制台看到Node.js代理服务器的启动日志，包括监听的端口号和转发的目标URL。如果 `auto_open_browser_config` 设置为 `true` (默认)，Web配置界面会自动在浏览器中打开。

### 7.4. 开始使用 (Usage)

-   通过您已配置好的AI应用程序与AI进行交互。
-   当AI的回复中包含已启用插件的特定指令占位符时，Xice_Aitoolbox框架会自动拦截响应，调用相应插件执行任务，并将结果反馈给AI（可能进行多轮交互），最终将聚合后的结果返回给您的AI应用。
-   监控Python控制台和Node.js服务输出的日志，以及项目根目录下的 `send.json`, `received.json`, `conformchat.txt` 文件，以了解框架的运行情况和AI与插件的交互细节。

## 8. 开发者指南：创建新插件 (Developer Guide: Creating New Plugins)

1.  **创建插件目录**:
    -   在项目根目录的 `Plugin/` 文件夹下为您的新插件创建一个唯一的子文件夹。文件夹名称应清晰描述插件功能，例如 `Plugin/MyNewUtility/`。

2.  **编写插件执行脚本**:
    -   在您创建的插件目录中，放置插件的主执行文件。这可以是一个Python脚本 (`.py`)，一个Node.js脚本 (`.js`)，一个Windows批处理文件 (`.bat`)，一个Shell脚本 (`.sh`)，或任何其他可执行文件。
    -   **输入参数**:
        -   如果插件的 `config.json` 中 `accepts_parameters` 设置为 `true`，Node.js代理会将AI在占位符之间提供的参数内容（去除首尾空格后）作为单个字符串，通过命令行参数传递给您的脚本。
        -   对于Python脚本，这通常通过 `sys.argv[1]` 获取。
        -   如果参数是JSON格式的字符串，您的脚本需要自行解析它 (例如，在Python中使用 `json.loads(sys.argv[1])`)。
        -   对于Node.js脚本，参数通过 `process.argv[2]` 获取 (因为 `process.argv[0]` 是node，`process.argv[1]` 是脚本路径)。
        -   对于批处理/Shell脚本，参数通过 `%1` 或 `$1` 获取。
    -   **输出结果**:
        -   插件的执行结果（通常是文本）必须打印到其标准输出 (stdout)。Node.js代理会捕获此输出，并将其用于后续处理。
        -   输出格式应尽可能对AI友好，清晰明了。
    -   **错误处理**:
        -   如果插件执行过程中发生错误，相关的错误信息可以打印到标准错误流 (stderr)。Node.js代理也会捕获stderr。
        -   非零的退出码通常表示插件执行失败。
    -   **依赖管理**:
        -   **Python插件**: 如果您的Python插件依赖于外部库，请将这些库及其版本添加到项目根目录的 `requirements.txt` 文件中，以便用户可以通过 `pip install -r requirements.txt` 一并安装。
        -   **Node.js插件**: 如果插件是Node.js脚本且有npm依赖，建议在插件目录内包含一个 `package.json` 并指导用户单独 `npm install`，或者使插件尽可能不依赖外部npm模块（除非这些模块已作为主项目的依赖安装）。
        -   **其他脚本**: 确保脚本的运行环境（如特定解释器、系统工具）在目标系统上可用，并在插件的文档（如README.md）中说明这些依赖。

3.  **创建插件配置文件 (`config.json`)**:
    -   在您的插件目录 (例如 `Plugin/MyNewUtility/`) 中创建一个名为 `config.json` 的文件。此文件使用JSON格式。
    -   **核心字段 (必需)**:
        -   `plugin_id` (string): 插件的全局唯一标识符，例如 `"my_new_utility_plugin"`。一旦设定并被AI使用，不应轻易更改。建议使用小写字母、数字和下划线。
        -   `plugin_name_cn` (string): 插件在Web配置界面和给AI的描述中显示的中文名称，例如 `"我的新工具"`。
        -   `executable_name` (string): 位于插件目录内的可执行脚本的文件名，例如 `"my_script.py"` 或 `"run.bat"`。
        -   `placeholder_start` (string): AI调用此插件时使用的起始占位符，例如 `"[我的工具开始]"`。必须是唯一的，以避免与其他插件冲突。
        -   `placeholder_end` (string): AI调用此插件时使用的结束占位符，例如 `"[我的工具结束]"`。必须是唯一的。
    -   **常用字段 (推荐填写)**:
        -   `version` (string): 插件的版本号，例如 `"1.0.2"`。
        -   `description` (string): 给AI的详细描述。这是至关重要的一环，AI会根据此描述来理解插件的功能、何时应该使用它、参数的格式（如果 `accepts_parameters` 为 `true`）、参数的含义、以及插件预期输出的格式和内容。描述应清晰、准确、易于AI理解。
        -   `author` (string): 插件的作者或维护者。
        -   `enabled` (boolean): 插件是否默认启用。`true` 表示启用，`false` 表示禁用。用户可以在Web配置界面更改此设置。默认为 `true`。
        -   `script_type` (string): 指明插件脚本的类型。可选值为：
            -   `"python"`: Python脚本。
            -   `"nodejs"`: Node.js脚本。
            -   `"executable"`: 其他可执行文件或系统脚本（如 `.bat`, `.sh`, `.exe`）。
        -   `accepts_parameters` (boolean): 指示插件是否接受占位符之间的参数。`true` 表示接受，`false` 表示不接受（此时AI调用时占位符之间不应有内容）。默认为 `false`。
        -   `is_internal_signal` (boolean): 标记此插件是否为一个内部信号插件（例如，`continue_ai_reply`插件）。内部信号插件的输出可能不会直接展示给用户，而是用于控制框架的流程。默认为 `false`。
    -   **可选高级字段**:
        -   `parameters_schema` (array of objects, 可选): （原`parameters`字段）一个JSON数组，用于更详细地描述插件接受的参数的模式。这主要用于未来的UI自动生成、参数校验或更精细的AI提示。数组中的每个对象可以包含以下键：
            -   `name` (string): 参数的名称（主要供文档和开发者参考）。
            -   `type` (string): 参数的预期类型 (例如, `"string"`, `"number"`, `"boolean"`, `"json_string"`, `"file_path"`)。
            -   `description` (string): 对该参数的详细描述。
            -   `required` (boolean): 此参数是否为必需。
            -   `example` (any): 一个参数示例。
        -   `plugin_specific_config` (object, 可选): 一个JSON对象，包含此插件独有的配置项及其默认值。这些配置项将显示在Web配置界面的该插件配置区域，允许用户修改。插件脚本在执行时应尝试从其自身的 `config.json` 文件中读取这些 `plugin_specific_config` 的当前值。如果读取失败或特定项不存在，脚本应使用其内部定义的后备默认值。
            例如:
            ```json
            "plugin_specific_config": {
                "api_endpoint": "[https://api.example.com/data](https://api.example.com/data)",
                "retry_attempts": 3,
                "output_format": "text",
                "enable_feature_xyz": false
            }
            ```
        -   `notes_for_proxy_server` (string, 可选): 给 `proxy_server.js` 维护者或高级用户的备注。可以说明插件执行时可能需要的特殊环境变量传递、文件系统结构依赖等，这些是 `proxy_server.js` 在 `executePlugin` 函数中可能需要考虑的。

4.  **测试插件**:
    -   **重启服务**: 在添加新插件或修改现有插件的 `config.json` 后，通常需要重启Xice_Aitoolbox服务（例如，重新运行 `start.bat` 或 `python main.py`），以确保框架能发现并正确加载插件。
    -   **检查Web配置界面**: 打开Web配置界面 (通常是 `http://localhost:3001/plugin-manager`)。
        -   确认您的新插件是否出现在插件列表中。
        -   点击“配置插件”，检查所有配置项（包括元数据、执行配置和 `plugin_specific_config`）是否按预期显示，并且可以编辑和保存。
    -   **启用插件**: 确保插件在Web配置界面中处于“已启用”状态。
    -   **AI调用测试**:
        -   通过您的AI应用，与AI进行交互，尝试引导AI调用您的新插件。您可能需要明确告知AI新插件的功能和调用方式（占位符和参数格式），或者依赖于之前注入的插件规则。
        -   观察Python主程序和Node.js代理服务器的控制台输出日志，查找与插件执行相关的消息，包括参数传递、脚本启动、stdout/stderr输出以及任何错误信息。
        -   检查项目根目录下的 `send.json` (发送给AI的请求，看插件结果是否正确反馈), `received.json` (AI的响应，看是否正确调用插件), 和 `conformchat.txt` (交互过程的聚合文本) 文件，以帮助调试。
    -   **迭代优化**: 根据测试结果，修改插件脚本或其 `config.json`，然后重复测试步骤，直到插件按预期工作。

## 9. 安全考量与使用限制 (Security Considerations and Usage Restrictions)

### 9.1. 安全考量 (Security Considerations)

-   **插件权限等同于运行环境**: 插件脚本（无论是Python、Node.js还是其他可执行文件）将以运行Xice_Aitoolbox服务（通常是`proxy_server.js`，由`main.py`启动）的用户身份执行。这意味着插件拥有与该用户相同的系统权限。请务必意识到，如果AI能够调用一个设计不当或恶意的插件，它可能会执行非预期的系统操作。
-   **“危险”插件的警示**:
    -   项目中包含一些名称中明确带有“危险” (`_unsafe`) 标记的插件，例如 `file_updater_unsafe` (任意路径文件更新)、`project_generator_unsafe` (任意路径项目生成)、`run_program_command_unsafe` (任意命令执行)。
    -   这些插件被设计为提供最大的灵活性，允许AI指定任意文件路径或执行任意命令。这同时也带来了极高的安全风险。
    -   **强烈建议**: 除非您完全理解这些风险，并且在严格隔离和受控的环境（例如，虚拟机、Docker容器）中使用Xice_Aitoolbox，否则应通过Web配置界面禁用这些高风险插件，或者仔细审查并修改其 `plugin_specific_config`（如果插件支持）来严格限制其操作范围（例如，配置路径白名单、命令黑名单等）。
-   **用户最终责任**:
    -   Xice_Aitoolbox框架提供的是一套工具。如何配置和使用这些工具及插件，以及由此产生的安全后果，最终责任在于用户。
    -   **不运行来源不明的插件**: 在集成来自第三方或不完全信任来源的插件之前，请务必谨慎。
    -   **代码审查**: 如果可能，请审查插件的源代码，了解其具体行为。
    -   **最小权限原则**: 如果您在特定环境（如服务器）中运行Xice_Aitoolbox，请确保运行服务的用户账户具有完成任务所需的最小权限。
-   **警惕AI生成的参数**:
    -   AI模型可能会生成非预期或甚至恶意的参数传递给插件。例如，为一个期望文件路径的插件提供一个指向系统关键文件的路径，或者为一个执行命令的插件提供恶意指令。
    -   插件开发者应尽可能在其脚本内部进行严格的输入验证、清理和路径规范化，以防止路径遍历、命令注入等安全漏洞。
    -   框架用户应意识到AI生成内容的不确定性，并对高权限插件的调用保持警惕。
-   **Web配置界面的安全**:
    -   Web配置界面允许修改核心配置文件，这些文件直接影响系统的行为和安全。
    -   确保Xice_Aitoolbox服务监听的端口（默认为3001）不被未授权访问，尤其是在多用户或网络环境中。考虑使用防火墙规则限制访问。
    -   目前配置界面没有内置认证机制。

### 9.2. 免责声明与使用限制 (Disclaimer and Usage Restrictions)

-   **开发阶段**: 本Xice_Aitoolbox项目目前仍处于积极开发与实验阶段。可能存在未知的错误、功能缺陷或不完整的特性。我们不保证其在所有情况下的稳定性或可靠性。
-   **“按原样”提供**: 本项目及其所有组件均按“原样”和“可用”状态提供，不附带任何形式的明示或暗示的保证，包括但不限于对适销性、特定用途适用性或非侵权性的保证。
-   **风险自负**: 您理解并同意，使用本项目的风险完全由您自行承担。对于因使用或无法使用本项目（包括其任何插件、配置或文档）而导致的任何直接、间接、偶然、特殊、惩戒性或后果性损害（包括但不限于数据丢失、利润损失、业务中断、系统损坏或安全漏洞），开发者、贡献者或许可方在任何情况下均不承担任何责任，即使已被告知此类损害的可能性。
-   **非商业化授权**: 本项目采用Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) 许可证。这明确禁止将本项目及其任何衍生作品用于主要的商业目的。如果您希望将此工具用于商业场景，请联系开发者讨论可能的授权选项。
-   **API使用成本与限制**: 部分插件可能依赖于第三方API服务（例如，某些AI模型API、搜索引擎API等）。这些服务可能会有其自身的使用限制、配额和费用。您有责任了解并遵守这些第三方服务的使用条款，并承担因使用这些API而产生的任何相关成本。
-   **敏感信息保护**: 请勿在插件的 `config.json` 文件（尤其是 `plugin_specific_config` 部分）中硬编码或通过Web配置界面输入真实的、敏感的API密钥、密码或其他凭证，特别是当您计划将项目代码或配置文件提交到公共代码库（如GitHub）或与他人共享时。请使用环境变量、安全的密钥管理服务或其他适当的方法来妥善保管您的敏感信息。

## 10. 未来展望 (Future Outlook)

-   **流式响应的初步支持**: 探索对AI流式响应的更完善处理机制，包括在流式输出过程中检测和处理插件调用指令，以及如何将插件的即时结果优雅地反馈到流中。
-   **插件间通信与协作**: 研究更高级的插件间直接通信机制或共享数据上下文的方法，使多个插件能够更紧密地协作完成复杂任务。
-   **更细致的权限控制与沙盒化**:
    -   考虑引入一个更精细的、基于每个插件声明其所需权限（如文件读/写特定目录、网络访问特定域名、命令执行白名单等）的系统。
    -   探索更安全的插件执行沙盒环境，进一步限制插件对宿主系统的潜在影响，特别是对于代码执行和命令运行类插件。
-   **异步插件与长时间任务管理**: 优化对长时间运行的异步插件的支持，包括任务状态跟踪、超时管理和结果回调机制。
-   **插件市场/仓库概念**: 远期设想一个社区驱动的插件发现和分享机制，方便用户查找和集成更多实用、创新的插件。
-   **用户界面与体验增强**:
    -   持续改进Web配置管理界面的用户体验，例如提供更友好的JSON编辑器、参数校验提示、一键备份/恢复配置等。
    -   考虑为插件开发者提供更便捷的调试工具或日志查看界面。
-   **多语言支持**: 考虑对框架本身及文档提供多语言支持。
-   **更广泛的AI模型兼容性**: 测试并优化框架与更多不同类型AI模型服务（包括开源模型和商业API）的兼容性。
-   **安全性增强**: 持续关注并提升框架和插件的安全性，例如引入可选的API端点认证、更严格的输入清理机制等。

## 11. 许可证 (License)

本项目采用 **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** 许可证。

简单来说，这意味着您可以：

-   **共享 (Share)** — 在任何媒介以任何形式复制、发行本作品。
-   **演绎 (Adapt)** — 修改、转换或以本作品为基础进行创作。

只要你遵守许可协议条款，许可人就无法收回你的这些权利。

**惟须遵守下列条件：**

-   **署名 (BY)** — 您必须给出适当的署名（例如，指明原作者为Xice，并链接到项目源，如果适用），提供指向本 CC BY-NC-SA 4.0 许可证的链接，同时标明是否（对原始作品）作了修改。您可以用任何合理的方式来署名，但是不得以任何方式暗示许可人为您或您的使用背书。
-   **非商业性使用 (NC)** — 您不得将本作品及其衍生作品用于商业目的。
-   **相同方式共享 (SA)** — 如果您再混合、转换或者基于本作品进行创作，您必须基于与原先许可协议（CC BY-NC-SA 4.0）相同的许可协议分发您贡献的作品。

**没有附加限制** — 您不得适用法律术语或者技术措施从而限制其他人做许可协议允许的事情。

详情请参阅项目根目录下的 `LICENSE.md` 文件 (如果存在) 或访问 Creative Commons 官方网站了解此许可证的完整法律文本：[https://creativecommons.org/licenses/by-nc-sa/4.0/](https://creativecommons.org/licenses/by-nc-sa/4.0/)
