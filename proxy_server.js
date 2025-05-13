const express = require('express');
const fs = require('fs').promises;
const fsSync = require('fs'); // For synchronous checks like existsSync
const path = require('path');
const morgan = require('morgan');
const fetch = require('node-fetch'); // Ensure node-fetch v2 for CJS
const { spawn } = require('child_process');

const ROOT_CONFIG_FILE_PATH = path.join(__dirname, 'config.json');
const PLUGINS_DIR = path.join(__dirname, 'Plugin');
const CONFORM_CHAT_FILE = path.join(__dirname, 'conformchat.txt');
const SEND_LOG_FILE = path.join(__dirname, 'send.json');
const RECEIVED_LOG_FILE = path.join(__dirname, 'received.json');

let rootConfig;
let activePlugins = [];
let allDiscoveredPluginsInfo = []; 
let systemPluginRulesDescription = "";

// --- Configuration Loading ---
function loadRootConfig() {
    try {
        const configFileContent = fsSync.readFileSync(ROOT_CONFIG_FILE_PATH, 'utf-8');
        rootConfig = JSON.parse(configFileContent);
        console.log("[NodeJS] 根配置文件已加载。");
    } catch (error) {
        console.error(`[NodeJS] 致命错误：无法加载或解析根配置文件 ${path.basename(ROOT_CONFIG_FILE_PATH)}: ${error.message}`);
        process.exit(1);
    }
}

async function discoverAndLoadPlugins() {
    allDiscoveredPluginsInfo = [];
    activePlugins = [];
    systemPluginRulesDescription = "";
    console.log("[NodeJS] 开始扫描插件目录:", PLUGINS_DIR);

    try {
        const pluginFolders = await fs.readdir(PLUGINS_DIR, { withFileTypes: true });
        for (const dirent of pluginFolders) {
            if (dirent.isDirectory()) {
                const pluginFolderName = dirent.name;
                const pluginConfigPath = path.join(PLUGINS_DIR, pluginFolderName, 'config.json');
                try {
                    if (!fsSync.existsSync(pluginConfigPath)) {
                        console.warn(`[NodeJS] 插件 ${pluginFolderName}: 未找到 config.json，已跳过。`);
                        continue;
                    }
                    const pluginConfigFileContent = await fs.readFile(pluginConfigPath, 'utf-8');
                    const pluginConfig = JSON.parse(pluginConfigFileContent);

                    if (!pluginConfig.plugin_id || !pluginConfig.plugin_name_cn || !pluginConfig.executable_name ||
                        !pluginConfig.placeholder_start || !pluginConfig.placeholder_end) {
                        console.warn(`[NodeJS] 插件 ${pluginFolderName}: config.json 缺少必要字段，已跳过。`);
                        continue;
                    }
                    
                    const pluginInfo = {
                        id: pluginConfig.plugin_id,
                        name: pluginConfig.plugin_name_cn,
                        version: pluginConfig.version || "0.0.0",
                        description: pluginConfig.description || "无描述",
                        author: pluginConfig.author || "未知",
                        enabled: pluginConfig.enabled === undefined ? true : pluginConfig.enabled,
                        is_python_script: pluginConfig.is_python_script === undefined ? true : pluginConfig.is_python_script,
                        executable_name: pluginConfig.executable_name,
                        placeholder_start: pluginConfig.placeholder_start,
                        placeholder_end: pluginConfig.placeholder_end,
                        accepts_parameters: pluginConfig.accepts_parameters === undefined ? false : pluginConfig.accepts_parameters,
                        is_internal_signal: pluginConfig.is_internal_signal === undefined ? false : pluginConfig.is_internal_signal,
                        parameters_schema: pluginConfig.parameters || [],
                        plugin_specific_config: pluginConfig.plugin_specific_config || {},
                        folder_name: pluginFolderName
                    };
                    allDiscoveredPluginsInfo.push(pluginInfo);

                    if (pluginInfo.enabled) {
                        activePlugins.push(pluginInfo);
                    }
                    // console.log(`[NodeJS] 已加载插件: ${pluginInfo.name} (ID: ${pluginInfo.id}), 启用状态: ${pluginInfo.enabled}`);

                } catch (err) {
                    console.error(`[NodeJS] 加载插件 ${pluginFolderName} 的 config.json 失败: ${err.message}`);
                }
            }
        }

        if (activePlugins.length > 0) {
            systemPluginRulesDescription = "你可以使用以下已启用的工具：\n";
            activePlugins.forEach(p => {
                systemPluginRulesDescription += `- ${p.name}: ${p.description}\n`;
            });
            systemPluginRulesDescription += "请严格按照占位符格式回复以调用工具。";
        } else {
            systemPluginRulesDescription = "当前没有已启用的插件工具。";
        }
        console.log(`[NodeJS] 插件扫描完成。发现 ${allDiscoveredPluginsInfo.length} 个插件定义，其中 ${activePlugins.length} 个已启用。`);

    } catch (error) {
        console.error(`[NodeJS] 扫描插件目录 ${PLUGINS_DIR} 失败: ${error.message}`);
    }
}


// --- Utility Functions ---
async function initializeConformChatFile() {
    try {
        await fs.writeFile(CONFORM_CHAT_FILE, '', 'utf-8');
    } catch (error) {
        console.error(`[NodeJS] 初始化 ${path.basename(CONFORM_CHAT_FILE)} 失败:`, error);
    }
}

async function logRequest(req, bodyForLog, originalUrl, sourceIp) { // bodyForLog is expected to be an object or a raw string if not JSON
    if (!rootConfig.log_intercepted_data) return;
    const data = {
        timestamp_sent_to_target: new Date().toISOString(),
        method: req.method,
        target_url: rootConfig.target_proxy_url + (req.originalUrl || originalUrl),
        original_url_received_by_listener: originalUrl ? `${req.protocol || 'http'}://${req.headers?.host || 'localhost'}${originalUrl}` : `${req.protocol}://${req.headers.host}${req.originalUrl}`,
        source_ip_of_original_request: sourceIp || req.ip || req.socket?.remoteAddress,
        request_headers_sent_to_target: req.headers,
        request_body_sent_to_target: bodyForLog, // Log the (potentially modified) object or raw string
    };
    try { await fs.writeFile(SEND_LOG_FILE, JSON.stringify(data, null, 2)); }
    catch (e) { console.error(`[NodeJS] 写入 ${path.basename(SEND_LOG_FILE)} 失败`, e); }
}

async function logResponse(response, body) {
    if (!rootConfig.log_intercepted_data) return;
    let logBody = body;
    if (!rootConfig.log_response_body_in_received_file) {
        logBody = "[响应体日志已禁用]";
    } else if (typeof body === 'string' && body.length > (rootConfig.max_log_response_size_kb_in_received_file * 1024)) {
        logBody = `[响应体过大，已截断，原始大小: ${body.length} bytes] ` + body.substring(0, 200) + "...";
    } else if (Buffer.isBuffer(body) && body.length > (rootConfig.max_log_response_size_kb_in_received_file * 1024)) {
        logBody = `[Buffer响应体过大，已截断，原始大小: ${body.length} bytes]`;
    }

    const data = {
        timestamp_received_from_target: new Date().toISOString(),
        status_code: response.status,
        response_headers_from_target: Object.fromEntries(response.headers.entries()),
        response_body_from_target: logBody,
    };
    try { await fs.writeFile(RECEIVED_LOG_FILE, JSON.stringify(data, null, 2)); }
    catch (e) { console.error(`[NodeJS] 写入 ${path.basename(RECEIVED_LOG_FILE)} 失败`, e); }
}

function executePlugin(pluginInfo, pluginArgument) {
    return new Promise((resolve, reject) => {
        const pluginScriptPath = path.join(PLUGINS_DIR, pluginInfo.folder_name, pluginInfo.executable_name);
        
        let command;
        let args = [];
        let options = { encoding: 'utf-8', cwd: path.join(PLUGINS_DIR, pluginInfo.folder_name) }; 

        if (pluginInfo.is_python_script) {
            command = 'python'; 
            args.push(pluginScriptPath);
        } else { 
            command = pluginScriptPath;
            options.shell = (process.platform === "win32" && pluginScriptPath.toLowerCase().endsWith(".bat"));
        }

        if (pluginInfo.accepts_parameters && pluginArgument !== null && pluginArgument !== undefined) {
            args.push(String(pluginArgument)); 
        }
        
        console.log(`[NodeJS] 执行插件: ${pluginInfo.name} (ID: ${pluginInfo.id})`);
        // console.log(`  Cmd: ${command}, Args: ${JSON.stringify(args)}, CWD: ${options.cwd}, Shell: ${!!options.shell}`);

        const child = spawn(command, args, options);
        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (data) => stdout += data);
        child.stderr.on('data', (data) => stderr += data);

        child.on('close', (code) => {
            if (code === 0) {
                // console.log(`[NodeJS] 插件 ${pluginInfo.name} 执行成功.`);
                resolve(stdout.trim());
            } else {
                console.error(`[NodeJS] 插件 ${pluginInfo.name} 执行失败 (退出码: ${code}).`);
                if (stderr) console.error(`[NodeJS] 插件错误输出: ${stderr.trim()}`);
                reject(new Error(`插件 ${pluginInfo.name} 执行失败. ${stderr.trim() || `退出码: ${code}`}`));
            }
        });
        child.on('error', (err) => {
            console.error(`[NodeJS] 启动插件 ${pluginInfo.name} 失败:`, err);
            reject(new Error(`启动插件 ${pluginInfo.name} 失败: ${err.message}`));
        });
    });
}


// --- Main Request Handling Logic ---
async function handleRequestAndPlugins(req, res, originalRequestData, recursionDepth = 0, continuationDepth = 0) {
    if (recursionDepth === 0 && continuationDepth === 0) {
        await initializeConformChatFile();
    }

    const MAX_RECURSION = rootConfig.max_plugin_recursion_depth || 5;
    const MAX_CONTINUATION = rootConfig.max_continuation_depth || 5;

    if (recursionDepth > MAX_RECURSION || continuationDepth > MAX_CONTINUATION) {
        const limitType = recursionDepth > MAX_RECURSION ? "插件递归" : "继续回复";
        console.warn(`[NodeJS] ${limitType}达到最大深度，停止调用。`);
        const conformContent = await fs.readFile(CONFORM_CHAT_FILE, 'utf-8').catch(() => "");
        const finalContent = (conformContent.trim() || "[无内容]") + `\n\n[系统消息：已达到最大${limitType}深度]`;
        const errorResponse = {
            id: `error-${limitType.replace(" ", "-")}-limit-${Date.now()}`, object: "chat.completion",
            choices: [{ message: { role: "assistant", content: finalContent }, finish_reason: "length" }],
            model: (typeof originalRequestData.body === 'object' && originalRequestData.body?.model) ? originalRequestData.body.model : "unknown_model_limit"
        };
        if (res && !res.headersSent) res.status(200).json(errorResponse);
        await initializeConformChatFile();
        return;
    }

    const targetUrl = rootConfig.target_proxy_url + originalRequestData.url;
    
    // --- Refined Request Body Handling for Injection and Logging ---
    let currentRequestBodyObject; // This will be an object if original body is JSON or becomes JSON
    let originalBodyWasNonJsonString = false;

    if (typeof originalRequestData.body === 'string') {
        try {
            currentRequestBodyObject = JSON.parse(originalRequestData.body);
            // Deep clone to prevent modification of originalRequestData.body if it's parsed from string
            currentRequestBodyObject = JSON.parse(JSON.stringify(currentRequestBodyObject));
        } catch (e) {
            console.warn("[NodeJS] 初始请求体是字符串但非有效JSON，无法注入规则:", originalRequestData.body.substring(0,100));
            currentRequestBodyObject = null; // Indicate it's not a modifiable JSON object
            originalBodyWasNonJsonString = true;
        }
    } else if (typeof originalRequestData.body === 'object' && originalRequestData.body !== null) {
        currentRequestBodyObject = JSON.parse(JSON.stringify(originalRequestData.body)); // Deep copy
    } else {
        currentRequestBodyObject = { messages: [] }; // Default for null or other types, to allow injection
    }

    // Inject plugin rules if applicable, modifying 'currentRequestBodyObject'
    if (currentRequestBodyObject && // Ensure it's a valid object for modification
        rootConfig.inject_plugin_rules_on_first_request && 
        systemPluginRulesDescription && 
        activePlugins.length > 0 &&
        currentRequestBodyObject.messages // And it has a messages array
    ) {
        const firstUserMsgIdx = currentRequestBodyObject.messages.findIndex(m => m.role === 'user');
        const hasRuleInjected = currentRequestBodyObject.messages.some(m => m.role === 'system' && m.content && m.content.startsWith("你可以使用以下已启用的工具："));
        
        if (firstUserMsgIdx !== -1 && !hasRuleInjected) {
             currentRequestBodyObject.messages.splice(firstUserMsgIdx, 0, { role: "system", content: systemPluginRulesDescription });
             console.log("[NodeJS] 已注入插件规则描述。");
        }
    }
    // --- End Refined Request Body Handling ---

    // Log the request body that will be sent to the target
    // If original was non-JSON string and couldn't be modified, log that original string. Otherwise, log the object.
    if (rootConfig.log_intercepted_data) {
        await logRequest(req, 
            currentRequestBodyObject === null ? originalRequestData.body : currentRequestBodyObject, 
            originalRequestData.url, 
            originalRequestData.sourceIp
        );
    }

    // Prepare the body for the fetch call
    // If currentRequestBodyObject is null, it means original body was a non-JSON string and should be sent as is.
    // Otherwise, stringify the (potentially modified) object.
    const finalBodyForFetch = currentRequestBodyObject !== null ? JSON.stringify(currentRequestBodyObject) : originalRequestData.body;
    
    let responseFromTarget, responseBodyBuffer, aiResponseMessageContent = null, aiFullResponseObject = null;
    try {
        console.log(`[NodeJS] 转发请求 (递归 ${recursionDepth}, 继续 ${continuationDepth}): ${originalRequestData.method} ${targetUrl}`);
        responseFromTarget = await fetch(targetUrl, {
            method: originalRequestData.method, headers: originalRequestData.headers,
            body: (originalRequestData.method !== 'GET' && originalRequestData.method !== 'HEAD') ? finalBodyForFetch : undefined,
        });
        responseBodyBuffer = await responseFromTarget.buffer();
        const contentType = responseFromTarget.headers.get('content-type') || '';

        if (contentType.includes('application/json')) {
            const responseJsonString = responseBodyBuffer.toString('utf-8');
            aiFullResponseObject = JSON.parse(responseJsonString);
            aiResponseMessageContent = aiFullResponseObject?.choices?.[0]?.message?.content ||
                                     aiFullResponseObject?.content?.[0]?.text || 
                                     aiFullResponseObject?.message?.content;   
        } else if (contentType.includes('text/')) {
            aiResponseMessageContent = responseBodyBuffer.toString('utf-8');
        }
        if (rootConfig.log_intercepted_data) { await logResponse(responseFromTarget, aiFullResponseObject || aiResponseMessageContent || responseBodyBuffer); }

        let pluginMatchedAndProcessed = false;
        if (aiResponseMessageContent && activePlugins.length > 0) {
            for (const plugin of activePlugins) { // plugin is from activePlugins (contains full info)
                const regex = new RegExp(`${plugin.placeholder_start.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(.*?)${plugin.placeholder_end.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 's');
                const match = aiResponseMessageContent.match(regex);

                if (match) {
                    pluginMatchedAndProcessed = true;
                    const pluginArgument = plugin.accepts_parameters && match[1] ? match[1].trim() : null;
                    const textBeforePlaceholder = aiResponseMessageContent.substring(0, match.index).trimEnd();
                    
                    if (textBeforePlaceholder) { await fs.appendFile(CONFORM_CHAT_FILE, textBeforePlaceholder + "\n", 'utf-8'); }
                    console.log(`[NodeJS] 检测到插件调用: ${plugin.name}`);

                    // Base for next request's messages: currentRequestBodyObject (if it was JSON-like)
                    let baseMessagesForNextRequest = (currentRequestBodyObject && currentRequestBodyObject.messages) ? [...currentRequestBodyObject.messages] : [];
                    
                    // AI's message that triggered the plugin
                    const aiMessageThatTriggeredPlugin = aiFullResponseObject?.choices?.[0]?.message || 
                                                       (aiFullResponseObject?.content?.[0]?.text ? {role: "assistant", content: aiFullResponseObject.content[0].text} : null) || 
                                                       { role: "assistant", content: aiResponseMessageContent };


                    if (plugin.is_internal_signal && plugin.id === "continue_ai_reply") {
                        baseMessagesForNextRequest.push(aiMessageThatTriggeredPlugin);
                        baseMessagesForNextRequest.push({ role: "system", content: `[系统提示] ${pluginArgument || "请继续。"}` });
                        
                        const nextBodyObject = { ...(currentRequestBodyObject || {}), messages: baseMessagesForNextRequest };
                        const nextReqData = { ...originalRequestData, body: JSON.stringify(nextBodyObject) };
                        return await handleRequestAndPlugins(req, res, nextReqData, recursionDepth, continuationDepth + 1);
                    } else {
                        try {
                            const pluginResult = await executePlugin(plugin, pluginArgument);
                            const displayMode = rootConfig.conform_chat_display_mode || "detailed_plugin_responses";
                            if (displayMode === "detailed_plugin_responses") {
                                await fs.appendFile(CONFORM_CHAT_FILE, `\n\n\`\`\`\n[插件 ${plugin.name} 执行结果]:\n${pluginResult}\n\`\`\`\n\n`, 'utf-8');
                            }
                            
                            baseMessagesForNextRequest.push(aiMessageThatTriggeredPlugin);
                            baseMessagesForNextRequest.push({ role: "user", content: `[插件 ${plugin.name} 执行结果]:\n${pluginResult}` });
                            
                            const nextBodyObject = { ...(currentRequestBodyObject || {}), messages: baseMessagesForNextRequest };
                            const nextReqData = { ...originalRequestData, body: JSON.stringify(nextBodyObject) };
                            return await handleRequestAndPlugins(req, res, nextReqData, recursionDepth + 1, 0);
                        } catch (pluginError) {
                            console.error(`[NodeJS] 插件 ${plugin.name} 执行出错: ${pluginError.message}`);
                            await fs.appendFile(CONFORM_CHAT_FILE, `\n\n\`\`\`\n[插件执行错误: ${plugin.name}]\n${pluginError.message}\n\`\`\`\n\n`, 'utf-8');
                            
                            baseMessagesForNextRequest.push(aiMessageThatTriggeredPlugin);
                            baseMessagesForNextRequest.push({ role: "user", content: `[系统错误] 插件 '${plugin.name}' 执行失败: ${pluginError.message}. 请尝试其他方法。` });

                            const nextBodyObject = { ...(currentRequestBodyObject || {}), messages: baseMessagesForNextRequest };
                            const nextReqDataErr = { ...originalRequestData, body: JSON.stringify(nextBodyObject) };
                            return await handleRequestAndPlugins(req, res, nextReqDataErr, recursionDepth + 1, 0);
                        }
                    } 
                } 
            } 
        } 

        if (!pluginMatchedAndProcessed) {
            if (aiResponseMessageContent) {
                 const currentConform = await fs.readFile(CONFORM_CHAT_FILE, 'utf-8').catch(() => "");
                 let prefix = (currentConform.trim() && !currentConform.endsWith('\n\n') && !currentConform.endsWith('\n')) ? "\n\n" : (currentConform.trim() && !currentConform.endsWith('\n\n') ? "\n" : "");
                 await fs.appendFile(CONFORM_CHAT_FILE, prefix + aiResponseMessageContent.trimEnd(), 'utf-8');
            }
            if (res && !res.headersSent) {
                const finalConformContent = (await fs.readFile(CONFORM_CHAT_FILE, 'utf-8')).trim() || "[系统消息：AI未返回有效内容]";
                await initializeConformChatFile();
                
                let finalResponseToClientObject = JSON.parse(JSON.stringify(aiFullResponseObject || { // Deep copy base
                    id: `conformchat-${Date.now()}`, object: "chat.completion", created: Math.floor(Date.now()/1000),
                    model: (currentRequestBodyObject && currentRequestBodyObject.model) ? currentRequestBodyObject.model : "unknown_model_conform",
                    choices: [{ index: 0, message: {}, finish_reason: "stop" }]
                }));

                if (!finalResponseToClientObject.choices || !finalResponseToClientObject.choices[0]) finalResponseToClientObject.choices = [{ index: 0, message: {}, finish_reason: "stop" }];
                if (!finalResponseToClientObject.choices[0].message) finalResponseToClientObject.choices[0].message = {};
                finalResponseToClientObject.choices[0].message.role = "assistant";
                finalResponseToClientObject.choices[0].message.content = finalConformContent;
                
                res.status(responseFromTarget.status).json(finalResponseToClientObject);
            }
        }
    } catch (error) {
        console.error(`[NodeJS] 转发或处理响应时出错: ${error.message}`, error.stack);
        if (rootConfig.log_intercepted_data) await logResponse({status: 502, headers: new Map()}, `[错误: ${error.message}]`);
        if (res && !res.headersSent) {
             const errorResponseToClient = {
                id: "error-proxy-" + Date.now(),
                object: "error",
                message: "代理转发或响应处理失败",
                details: error.message,
                target: targetUrl,
                model: (currentRequestBodyObject && currentRequestBodyObject.model) ? currentRequestBodyObject.model : "unknown_model_proxy_error",
                choices: [{ index: 0, message: { role: "assistant", content: `[系统错误] 代理转发或处理到 ${targetUrl} 的请求失败: ${error.message}` }, finish_reason: "error" }]
            };
            res.status(502).json(errorResponseToClient);
        }
        await initializeConformChatFile();
    }
}


// --- Express App Setup ---
const app = express();
app.use(express.json({ limit: '100mb' }));
app.use(express.text({ limit: '100mb', type: ['text/*', 'application/xml', 'application/javascript'] }));
app.use(express.urlencoded({ extended: true, limit: '100mb' }));
app.use(morgan('dev', { stream: { write: (msg) => console.log(msg.trim()) } }));

// --- API Endpoints for Frontend ---
app.get('/api/system-config', (req, res) => res.json(rootConfig || {}));
app.post('/api/system-config', async (req, res) => {
    try {
        const newConfig = req.body;
        await fs.writeFile(ROOT_CONFIG_FILE_PATH, JSON.stringify(newConfig, null, 2), 'utf-8');
        loadRootConfig(); 
        await discoverAndLoadPlugins(); 
        res.json({ message: '系统配置已更新！部分更改需重启服务生效。' });
    } catch (e) { res.status(500).json({ message: '保存系统配置失败', error: e.message }); }
});

app.get('/api/plugins', (req, res) => res.json(allDiscoveredPluginsInfo || []));

app.get('/api/plugin-config/:plugin_id', async (req, res) => {
    const pluginId = req.params.plugin_id;
    const pluginInfo = allDiscoveredPluginsInfo.find(p => p.id === pluginId);
    if (!pluginInfo) return res.status(404).json({ message: '插件未找到' });
    try {
        const configPath = path.join(PLUGINS_DIR, pluginInfo.folder_name, 'config.json');
        const configContent = await fs.readFile(configPath, 'utf-8');
        res.json(JSON.parse(configContent));
    } catch (e) { res.status(500).json({ message: '读取插件配置失败', error: e.message }); }
});

app.post('/api/plugin-config/:plugin_id', async (req, res) => {
    const pluginId = req.params.plugin_id;
    const pluginInfo = allDiscoveredPluginsInfo.find(p => p.id === pluginId);
    if (!pluginInfo) return res.status(404).json({ message: '插件未找到' });
    try {
        const newPluginConfig = req.body;
        if (!newPluginConfig.plugin_id || newPluginConfig.plugin_id !== pluginId) {
            return res.status(400).json({ message: '插件ID不匹配或丢失。' });
        }
        const configPath = path.join(PLUGINS_DIR, pluginInfo.folder_name, 'config.json');
        await fs.writeFile(configPath, JSON.stringify(newPluginConfig, null, 2), 'utf-8');
        await discoverAndLoadPlugins(); 
        res.json({ message: `插件 ${pluginInfo.name} 配置已更新！` });
    } catch (e) { res.status(500).json({ message: '保存插件配置失败', error: e.message }); }
});


// Serve frontend
app.get('/plugin-manager', (req, res) => res.sendFile(path.join(__dirname, 'plugin_manager.html')));
app.get('/plugin_manager.js', (req, res) => res.sendFile(path.join(__dirname, 'plugin_manager.js')));


// Catch-all for proxying
app.all('*', (req, res, next) => {
    if (req.path.startsWith('/api/') || req.path.startsWith('/plugin-manager')) {
        return next();
    }
    const initialRequestData = {
        method: req.method, url: req.originalUrl, headers: { ...req.headers },
        body: req.body, sourceIp: req.ip || req.socket?.remoteAddress
    };
    delete initialRequestData.headers['host'];
    delete initialRequestData.headers['content-length']; 

    handleRequestAndPlugins(req, res, initialRequestData);
});

// Error handler
app.use((err, req, res, next) => {
    console.error("[NodeJS] 未捕获的服务器错误:", err.stack || err.message);
    if (!res.headersSent) res.status(500).json({ error: '服务器内部错误', details: err.message });
});


// --- Start Server ---
(async () => {
    loadRootConfig();
    await initializeConformChatFile();
    await discoverAndLoadPlugins();
    
    const port = rootConfig.proxy_server_port || 3001;
    app.listen(port, '0.0.0.0', () => {
        console.log("======================================================================");
        console.log(`[NodeJS] Xice_Aitoolbox 监听服务正在运行于端口: ${port}`);
        console.log(`[NodeJS] 转发到: ${rootConfig.target_proxy_url}`);
        console.log(`[NodeJS] 插件管理界面: http://localhost:${port}/plugin-manager`);
        console.log(`[NodeJS] 当前 ConformChat 显示模式: ${rootConfig.conform_chat_display_mode}`);
        console.log("======================================================================");
    }).on('error', (err) => {
        if (err.code === 'EADDRINUSE') console.error(`[NodeJS] 致命错误：端口 ${port} 已被占用。`);
        else console.error("[NodeJS] 启动服务器失败:", err);
        process.exit(1);
    });
})();

process.on('SIGINT', () => {
    console.log('[NodeJS] 收到 SIGINT，正在关闭...');
    process.exit(0);
});