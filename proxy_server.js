const express = require('express');
const fs = require('fs').promises; // 使用 fs.promises
const fsSync = require('fs'); // 同步fs用于简单检查
const path = require('path');
const morgan = require('morgan');
const fetch = require('node-fetch');
const { Readable } = require('stream');
const { spawn } = require('child_process');

// --- 配置加载 ---
const CONFIG_FILE_PATH = path.join(__dirname, 'config.json');
let config; 

function loadFullConfig() {
    try {
        const configFileContent = fsSync.readFileSync(CONFIG_FILE_PATH, 'utf-8');
        config = JSON.parse(configFileContent);
        console.log("[NodeJS] 配置文件已加载/重新加载。");
    } catch (error) {
        console.error(`[NodeJS] 致命错误：无法加载或解析 ${path.basename(CONFIG_FILE_PATH)}。请确保文件存在且格式正确。`);
        console.error(error.message);
        process.exit(1); 
    }
}

loadFullConfig(); 

let PROXY_SERVER_PORT;
let LOG_INTERCEPTED_DATA;
let TARGET_PROXY_URL;
let LOG_RESPONSE_BODY_IN_RECEIVED_FILE;
let MAX_LOG_RESPONSE_SIZE_KB_IN_RECEIVED_FILE;
let MAX_PLUGIN_RECURSION_DEPTH;
let INJECT_PLUGIN_RULES_ON_FIRST_REQUEST;
let MAX_CONTINUATION_DEPTH;
let CONFORM_CHAT_DISPLAY_MODE; 

function reassignConfigVariables() {
    PROXY_SERVER_PORT = config.proxy_server_port || 3001;
    LOG_INTERCEPTED_DATA = config.log_intercepted_data !== undefined ? config.log_intercepted_data : true;
    TARGET_PROXY_URL = config.target_proxy_url; 
    LOG_RESPONSE_BODY_IN_RECEIVED_FILE = config.log_response_body_in_received_file !== undefined ? config.log_response_body_in_received_file : true;
    MAX_LOG_RESPONSE_SIZE_KB_IN_RECEIVED_FILE = config.max_log_response_size_kb_in_received_file || 1024;
    MAX_PLUGIN_RECURSION_DEPTH = config.max_plugin_recursion_depth || 5; 
    INJECT_PLUGIN_RULES_ON_FIRST_REQUEST = config.inject_plugin_rules_on_first_request !== undefined ? config.inject_plugin_rules_on_first_request : true;
    MAX_CONTINUATION_DEPTH = config.max_continuation_depth || 5; 
    CONFORM_CHAT_DISPLAY_MODE = config.conform_chat_display_mode || "detailed_plugin_responses";

    if (!TARGET_PROXY_URL) {
        console.error("[NodeJS] 错误：config.json 中未配置 'target_proxy_url'。无法启动服务。");
        process.exit(1);
    }
}

reassignConfigVariables(); 

const SEND_LOG_FILE = path.join(__dirname, 'send.json');
const RECEIVED_LOG_FILE = path.join(__dirname, 'received.json');
const PLUGINS_RULE_FILE = path.join(__dirname, 'PluginsRule.json');
const CONFORM_CHAT_FILE = path.join(__dirname, 'conformchat.txt');

let activePlugins = [];
let allPluginsWithStatus = [];
let systemPluginRulesDescription = "";

async function initializeConformChatFile() {
    try {
        await fs.writeFile(CONFORM_CHAT_FILE, '', 'utf-8');
        // console.log(`[NodeJS] ${path.basename(CONFORM_CHAT_FILE)} 已初始化/清空。`); 
    } catch (error) {
        console.error(`[NodeJS] 错误：初始化 ${path.basename(CONFORM_CHAT_FILE)} 失败:`, error);
    }
}

const app = express();

app.use(express.json({ limit: '100mb' }));
app.use(express.text({ limit: '100mb', type: ['text/*', 'application/xml', 'application/javascript'] }));
app.use(express.urlencoded({ extended: true, limit: '100mb' }));
app.use(morgan('dev', { stream: { write: (message) => console.log(message.trim()) } }));

async function loadPluginRules() {
    try {
        try {
            await fs.access(PLUGINS_RULE_FILE);
        } catch (accessError) {
            if (accessError.code === 'ENOENT') {
                console.warn(`[NodeJS] ${path.basename(PLUGINS_RULE_FILE)} 未找到，将创建一个空的插件规则文件。`);
                await fs.writeFile(PLUGINS_RULE_FILE, '[]', 'utf-8');
                allPluginsWithStatus = [];
                activePlugins = [];
                systemPluginRulesDescription = "";
                return;
            } else { throw accessError; }
        }
        
        const rulesFileContent = await fs.readFile(PLUGINS_RULE_FILE, 'utf-8');
        const parsedPlugins = JSON.parse(rulesFileContent);

        if (!Array.isArray(parsedPlugins)) {
            console.error(`[NodeJS] 错误：${path.basename(PLUGINS_RULE_FILE)} 的内容不是一个有效的JSON数组。插件功能可能受影响。将使用空插件列表。`);
            allPluginsWithStatus = [];
            activePlugins = [];
        } else {
            allPluginsWithStatus = parsedPlugins.map(p => ({ ...p, enabled: p.enabled === undefined ? true : p.enabled }));
            activePlugins = allPluginsWithStatus.filter(p => p.enabled);
        }

        console.log('[NodeJS] 插件规则已加载/重新加载:');
        if (allPluginsWithStatus.length > 0) {
            console.log(`  总共 ${allPluginsWithStatus.length} 个插件被定义，其中 ${activePlugins.length} 个已启用。`);
            
            systemPluginRulesDescription = "你可以使用以下已启用的工具：\n";
            if (activePlugins.length > 0) {
                activePlugins.forEach(plugin => {
                    systemPluginRulesDescription += `- ${plugin.plugin_name_cn}: ${plugin.rule_description}\n`;
                });
                systemPluginRulesDescription += "请严格按照占位符格式回复以调用工具。";
            } else {
                systemPluginRulesDescription = "当前没有已启用的插件工具。";
            }
        } else {
            console.log('[NodeJS] 当前没有配置任何插件。');
            systemPluginRulesDescription = "";
        }
    } catch (error) {
        console.error(`[NodeJS] 警告：加载或解析插件规则文件 ${path.basename(PLUGINS_RULE_FILE)} 时发生错误。插件功能将不可用。`, error.message);
        allPluginsWithStatus = [];
        activePlugins = [];
        systemPluginRulesDescription = "";
    }
}

async function logSentRequest(req, reqBodyForLog, originalUrl, sourceIp) {
    if (!LOG_INTERCEPTED_DATA) return; 
    const dataToLog = {
        timestamp_sent_to_target: new Date().toISOString(),
        method: req.method,
        target_url: TARGET_PROXY_URL + (req.originalUrl || originalUrl), 
        original_url_received_by_listener: originalUrl ? `${req.protocol || 'http'}://${req.headers?.host || 'localhost'}${originalUrl}` : `${req.protocol}://${req.headers.host}${req.originalUrl}`,
        source_ip_of_original_request: sourceIp || req.ip || req.socket?.remoteAddress,
        request_headers_sent_to_target: req.headers,
        request_body_sent_to_target: reqBodyForLog,
    };
    try {
        await fs.writeFile(SEND_LOG_FILE, JSON.stringify(dataToLog, null, 2));
    } catch (error) {
        console.error(`[NodeJS] 错误：写入 ${path.basename(SEND_LOG_FILE)} 失败`, error);
    }
}

async function logReceivedResponse(responseFromTarget, resBodyForLog) {
    if (!LOG_INTERCEPTED_DATA) return; 
    const dataToLog = {
        timestamp_received_from_target: new Date().toISOString(),
        status_code: responseFromTarget.status,
        response_headers_from_target: Object.fromEntries(responseFromTarget.headers.entries()),
        response_body_from_target: resBodyForLog,
    };
    try {
        await fs.writeFile(RECEIVED_LOG_FILE, JSON.stringify(dataToLog, null, 2));
    } catch (error) {
        console.error(`[NodeJS] 错误：写入 ${path.basename(RECEIVED_LOG_FILE)} 失败`, error);
    }
}

function executePlugin(plugin, pluginArgument) {
    return new Promise((resolve, reject) => {
        const executable = plugin.executable_path;
        const absoluteExecutablePath = path.isAbsolute(executable) ? executable : path.join(__dirname, executable);

        let commandToExecute;
        let commandArgs = [];
        let spawnOptions = {
            encoding: 'utf-8',
            shell: false 
        };

        if (plugin.is_python_script) {
            commandToExecute = 'python';
            commandArgs.push(absoluteExecutablePath);
            if (plugin.accepts_parameters && pluginArgument !== null && pluginArgument !== undefined) {
                commandArgs.push(pluginArgument);
            }
        } else {
            if (process.platform === "win32" && (executable.toLowerCase().endsWith(".bat") || executable.toLowerCase().endsWith(".cmd"))) {
                commandToExecute = `"${absoluteExecutablePath}"`; 
                if (plugin.accepts_parameters && pluginArgument !== null && pluginArgument !== undefined) {
                    if (typeof pluginArgument === 'string' && pluginArgument.includes(' ')) {
                        commandToExecute += ` "${pluginArgument.replace(/"/g, '""')}"`; 
                    } else if (pluginArgument !== null && pluginArgument !== undefined){
                        commandToExecute += ` ${pluginArgument}`;
                    }
                }
                spawnOptions.shell = true;
            } else { 
                commandToExecute = absoluteExecutablePath;
                if (plugin.accepts_parameters && pluginArgument !== null && pluginArgument !== undefined) {
                    commandArgs.push(pluginArgument);
                }
            }
        }
        
        console.log(`[NodeJS] 正在执行插件: ${plugin.plugin_name_cn} (ID: ${plugin.plugin_id})`);
        if (spawnOptions.shell) {
            console.log(`  Shell Command: ${commandToExecute}`);
        } else {
            console.log(`  Cmd: ${commandToExecute}`);
            console.log(`  Args: ${JSON.stringify(commandArgs)}`);
        }

        const childProcess = spawnOptions.shell ? 
                             spawn(commandToExecute, [], spawnOptions) : 
                             spawn(commandToExecute, commandArgs, spawnOptions);

        let stdoutData = '';
        let stderrData = '';

        childProcess.stdout.on('data', (data) => { stdoutData += data.toString(); });
        childProcess.stderr.on('data', (data) => { stderrData += data.toString(); });

        childProcess.on('close', (code) => {
            if (code === 0) {
                console.log(`[NodeJS] 插件 ${plugin.executable_path} 执行成功.`);
                resolve(stdoutData.trim());
            } else {
                console.error(`[NodeJS] 插件 ${plugin.executable_path} 执行失败 (退出码: ${code}).`);
                if (stderrData) console.error(`[NodeJS] 插件错误输出: ${stderrData.trim()}`);
                reject(new Error(`插件 ${plugin.executable_path} 执行失败. ${stderrData.trim()}`));
            }
        });
        childProcess.on('error', (err) => {
            console.error(`[NodeJS] 启动插件 ${plugin.executable_path} 失败 (spawn error):`, err);
            reject(new Error(`启动插件 ${plugin.executable_path} 失败: ${err.message}`));
        });
    });
}

async function handleRequestAndPlugins(req, res, originalRequestData, recursionDepth = 0, continuationDepth = 0) {
    if (recursionDepth === 0 && continuationDepth === 0) {
        await initializeConformChatFile();
    }

    if (recursionDepth > MAX_PLUGIN_RECURSION_DEPTH) {
        console.warn(`[NodeJS] 插件调用达到最大深度 (${MAX_PLUGIN_RECURSION_DEPTH})，停止进一步调用。`);
        if (res && !res.headersSent) {
            try {
                const conformChatContent = await fs.readFile(CONFORM_CHAT_FILE, 'utf-8');
                const finalContentToSend = (conformChatContent.trim() ? conformChatContent.trimEnd() : "[系统消息：无有效内容]") + "\n\n[系统消息：已达到最大插件处理深度，对话可能不完整]";
                const errorResponse = {
                    id: "error-recursion-limit-" + Date.now(),
                    object: "chat.completion",
                    created: Math.floor(Date.now() / 1000),
                    model: originalRequestData.body?.model || "unknown_model_error",
                    choices: [{ index: 0, message: { role: "assistant", content: finalContentToSend }, finish_reason: "length" }],
                };
                res.status(200).json(errorResponse); 
                await initializeConformChatFile(); 
            } catch (e) {
                console.error("[NodeJS] 读取 conformchat 文件失败（在插件递归超限时）:", e);
                res.status(500).json({ error: "Plugin recursion limit reached, error reading accumulated content." });
            }
        }
        return;
    }
    if (continuationDepth > MAX_CONTINUATION_DEPTH) { 
        console.warn(`[NodeJS] 继续回复达到最大深度 (${MAX_CONTINUATION_DEPTH})，停止进一步调用。`);
        if (res && !res.headersSent) {
             try {
                const conformChatContent = await fs.readFile(CONFORM_CHAT_FILE, 'utf-8');
                const finalContentToSend = (conformChatContent.trim() ? conformChatContent.trimEnd() : "[系统消息：无有效内容]") + "\n\n[系统消息：已达到最大继续回复深度，对话可能不完整]";
                const errorResponse = {
                    id: "error-continuation-limit-" + Date.now(),
                    object: "chat.completion",
                    created: Math.floor(Date.now() / 1000),
                    model: originalRequestData.body?.model || "unknown_model_error",
                    choices: [{ index: 0, message: { role: "assistant", content: finalContentToSend }, finish_reason: "length" }],
                };
                res.status(200).json(errorResponse);
                await initializeConformChatFile(); 
            } catch (e) {
                console.error("[NodeJS] 读取 conformchat 文件失败（在继续回复超限时）:", e);
                res.status(500).json({ error: "Continuation recursion limit reached, error reading accumulated content." });
            }
        }
        return;
    }

    const currentDisplayMode = CONFORM_CHAT_DISPLAY_MODE; 
    const targetUrl = TARGET_PROXY_URL + originalRequestData.url;
    let requestBodyForForwarding = originalRequestData.body;

    let parsedBody;
    if (typeof requestBodyForForwarding === 'string') {
        try { parsedBody = JSON.parse(requestBodyForForwarding); } 
        catch (e) { parsedBody = { messages: [] }; }
    } else if (typeof requestBodyForForwarding === 'object' && requestBodyForForwarding !== null) {
        parsedBody = { ...requestBodyForForwarding }; 
        if (!parsedBody.messages) parsedBody.messages = [];
    } else {
        parsedBody = { messages: [] };
    }
    
    if (INJECT_PLUGIN_RULES_ON_FIRST_REQUEST && systemPluginRulesDescription && activePlugins.length > 0 && parsedBody.messages && parsedBody.messages.length > 0) {
        const firstUserMessageIndex = parsedBody.messages.findIndex(m => m.role === 'user');
        const hasSystemPluginRule = parsedBody.messages.some(m => m.role === 'system' && m.content && m.content.startsWith("你可以使用以下已启用的工具："));
        if (firstUserMessageIndex === 0 && !hasSystemPluginRule) { 
             parsedBody.messages.unshift({ role: "system", content: systemPluginRulesDescription });
             console.log("[NodeJS] 已向请求中注入启用的插件规则描述 (在首条用户消息前)。");
        } else if (firstUserMessageIndex > 0 && !hasSystemPluginRule) {
            let injected = false;
            for (let i = 0; i < firstUserMessageIndex; i++) {
                if (parsedBody.messages[i].role === 'system') {
                    parsedBody.messages.splice(i + 1, 0, { role: "system", content: systemPluginRulesDescription });
                    injected = true;
                    console.log("[NodeJS] 已向请求中注入启用的插件规则描述 (在现有系统消息后)。");
                    break;
                }
            }
            if (!injected) { 
                 parsedBody.messages.splice(firstUserMessageIndex, 0, { role: "system", content: systemPluginRulesDescription });
                 console.log("[NodeJS] 已向请求中注入启用的插件规则描述 (在用户消息前)。");
            }
        }
    }
    
    const finalBodyToSend = JSON.stringify(parsedBody);
    if (LOG_INTERCEPTED_DATA) { await logSentRequest(req, parsedBody, originalRequestData.url, originalRequestData.sourceIp); }

    let responseFromTarget;
    let responseBodyBuffer;
    let resBodyForLog = null;

    try {
        console.log(`[NodeJS] (${currentDisplayMode}) 转发请求 (递归 ${recursionDepth}, 继续 ${continuationDepth}): ${originalRequestData.method} ${targetUrl}`);
        responseFromTarget = await fetch(targetUrl, {
            method: originalRequestData.method,
            headers: originalRequestData.headers,
            body: (originalRequestData.method !== 'GET' && originalRequestData.method !== 'HEAD') ? finalBodyToSend : undefined,
        });

        try { responseBodyBuffer = await responseFromTarget.buffer(); } 
        catch (bufferError) {
            console.error(`[NodeJS] 读取目标响应体为Buffer时出错: ${bufferError.message}`);
            resBodyForLog = "[Error reading response body from target]";
            if (LOG_INTERCEPTED_DATA) await logReceivedResponse(responseFromTarget, resBodyForLog);
            if (res && !res.headersSent) res.status(responseFromTarget.status || 500).json({ error: '读取目标服务器响应体失败', details: bufferError.message });
            return;
        }
        
        const contentType = responseFromTarget.headers.get('content-type') || '';
        let aiResponseMessageContent = null; 
        let aiFullResponseObject = null;    

        if (contentType.includes('application/json')) {
            try {
                const responseJsonString = responseBodyBuffer.toString('utf-8');
                aiFullResponseObject = JSON.parse(responseJsonString);
                if (aiFullResponseObject.choices && aiFullResponseObject.choices[0] && aiFullResponseObject.choices[0].message && aiFullResponseObject.choices[0].message.content) {
                    aiResponseMessageContent = aiFullResponseObject.choices[0].message.content;
                }
                else if (aiFullResponseObject.content && Array.isArray(aiFullResponseObject.content) && aiFullResponseObject.content[0] && aiFullResponseObject.content[0].type === 'text') { 
                    aiResponseMessageContent = aiFullResponseObject.content[0].text;
                }
                else if (aiFullResponseObject.message && aiFullResponseObject.message.content) { 
                     aiResponseMessageContent = aiFullResponseObject.message.content;
                }
                resBodyForLog = aiFullResponseObject; 
            } catch (e) {
                console.warn('[NodeJS] AI响应是JSON但解析或提取content失败:', e.message);
                const rawText = responseBodyBuffer.toString('utf-8');
                resBodyForLog = "[Could not parse JSON response body or extract content, logging as text]\n" + rawText;
                aiResponseMessageContent = rawText; 
            }
        } else if (contentType.includes('text/')) {
            aiResponseMessageContent = responseBodyBuffer.toString('utf-8');
            resBodyForLog = aiResponseMessageContent;
        } else if (responseBodyBuffer.length > 0) {
             resBodyForLog = `[Non-text/JSON response body, size: ${responseBodyBuffer.length} bytes, content-type: ${contentType}]`;
        } else {
            resBodyForLog = "[Empty response body from target]";
        }
        
        if (LOG_RESPONSE_BODY_IN_RECEIVED_FILE && typeof resBodyForLog === 'string' && responseBodyBuffer.length > (MAX_LOG_RESPONSE_SIZE_KB_IN_RECEIVED_FILE * 1024)) {
            const maxLogSizeBytes = MAX_LOG_RESPONSE_SIZE_KB_IN_RECEIVED_FILE * 1024;
            resBodyForLog = `[Response body truncated, size: ${responseBodyBuffer.length} bytes, exceeds max_log_size: ${maxLogSizeBytes} bytes]`;
            if (contentType.includes('application/json') || contentType.includes('text/')) {
                 try { resBodyForLog += `\nPartial content:\n${responseBodyBuffer.slice(0, maxLogSizeBytes).toString('utf-8')}`; } catch (e) { /* ignore */ }
            }
        } else if (!LOG_RESPONSE_BODY_IN_RECEIVED_FILE && typeof resBodyForLog !== 'string' && resBodyForLog !== null) {
            resBodyForLog = "[Response body logging disabled in received.json, but it was an object]";
        } else if (!LOG_RESPONSE_BODY_IN_RECEIVED_FILE) {
            resBodyForLog = "[Response body logging disabled in received.json]";
        }
        if (LOG_INTERCEPTED_DATA) { await logReceivedResponse(responseFromTarget, resBodyForLog); }

        let pluginMatchedAndProcessed = false;
        if (aiResponseMessageContent && activePlugins.length > 0) {
            for (const plugin of activePlugins) { 
                if (!plugin.enabled) continue; 

                const placeholderStartEsc = plugin.placeholder_start.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const placeholderEndEsc = plugin.placeholder_end.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const regexPattern = plugin.accepts_parameters ? `(.*?)` : ''; 
                const regex = new RegExp(
                    `${placeholderStartEsc}${regexPattern}${placeholderEndEsc}`,
                    's' 
                );
                const match = aiResponseMessageContent.match(regex);

                if (match) {
                    pluginMatchedAndProcessed = true; 
                    const pluginArgument = plugin.accepts_parameters && match[1] ? match[1].trim() : null;
                    
                    const textBeforePlaceholder = aiResponseMessageContent.substring(0, match.index).trimEnd();
                    
                    if (textBeforePlaceholder && !(currentDisplayMode === "final_ai_response_only" && recursionDepth > 0)) {
                         await fs.appendFile(CONFORM_CHAT_FILE, textBeforePlaceholder + "\n", 'utf-8');
                    }
                    
                    console.log(`[NodeJS] 检测到已启用插件调用: ${plugin.plugin_name_cn} (ID: ${plugin.plugin_id})`);
                    
                    if (plugin.is_internal_signal && plugin.plugin_id === "continue_ai_reply") {
                        console.log("[NodeJS] '继续回复'信号被触发。");
                        const currentAiMessage = aiFullResponseObject?.choices?.[0]?.message || 
                                                 (aiFullResponseObject?.content?.[0]?.text ? {role: "assistant", content: aiFullResponseObject.content[0].text} : null) ||
                                                 { role: "assistant", content: aiResponseMessageContent }; 

                        const newMessagesForContinuation = [...(parsedBody.messages || []), currentAiMessage];
                        const continuationPrompt = pluginArgument || "请继续生成回复的下一部分内容。";
                        newMessagesForContinuation.push({ role: "system", content: `[系统提示] ${continuationPrompt} (这是一个自动继续请求，请接着上一条回复输出)` });
                        
                        const nextRequestDataForContinuation = {
                            ...originalRequestData, 
                            body: { ...parsedBody, messages: newMessagesForContinuation }, 
                        };
                        return await handleRequestAndPlugins(req, res, nextRequestDataForContinuation, recursionDepth, continuationDepth + 1);
                    }
                    else { 
                        try {
                            const pluginResult = await executePlugin(plugin, pluginArgument);
                            
                            if (currentDisplayMode === "detailed_plugin_responses") {
                                const formattedPluginResult = `\n\n\`\`\`\n[插件 ${plugin.plugin_name_cn} 执行结果]:\n${pluginResult}\n\`\`\`\n\n`;
                                await fs.appendFile(CONFORM_CHAT_FILE, formattedPluginResult, 'utf-8');
                            } else if (currentDisplayMode === "compact_plugin_chain") {
                                const conformContentSoFar = await fs.readFile(CONFORM_CHAT_FILE, 'utf-8');
                                if (conformContentSoFar.trim() && !conformContentSoFar.endsWith('\n\n') && textBeforePlaceholder) { 
                                     await fs.appendFile(CONFORM_CHAT_FILE, "\n", 'utf-8'); 
                                }
                            }

                            const currentAiMessageForHistory = aiFullResponseObject?.choices?.[0]?.message ||
                                                            (aiFullResponseObject?.content?.[0]?.text ? {role: "assistant", content: aiFullResponseObject.content[0].text} : null) ||
                                                            { role: "assistant", content: aiResponseMessageContent };

                            const newMessagesForPlugin = [...(parsedBody.messages || []), currentAiMessageForHistory];
                            // ===================== ROLE CHANGE HERE (SUCCESS) =====================
                            newMessagesForPlugin.push({ 
                                role: "user", // MODIFIED FROM "system"
                                content: `[插件 ${plugin.plugin_name_cn} 执行结果]:\n${pluginResult}` 
                            });
                            // ======================================================================

                            const newRequestBodyForPlugin = { ...parsedBody, messages: newMessagesForPlugin };
                            const nextRequestData = { ...originalRequestData, body: newRequestBodyForPlugin };
                            
                            console.log(`[NodeJS] 插件(ID: ${plugin.plugin_id})返回结果，准备使用新消息再次请求AI...`);
                            return await handleRequestAndPlugins(req, res, nextRequestData, recursionDepth + 1, 0); 

                        } catch (pluginError) {
                            console.error(`[NodeJS] 插件 ${plugin.plugin_name_cn} (ID: ${plugin.plugin_id}) 执行出错: ${pluginError.message}`);
                            
                            if (currentDisplayMode === "detailed_plugin_responses") {
                                const errorResultForConform = `\n\n\`\`\`\n[插件执行错误: ${plugin.plugin_name_cn}]\n${pluginError.message}\n\`\`\`\n\n`;
                                await fs.appendFile(CONFORM_CHAT_FILE, errorResultForConform, 'utf-8');
                            }

                            const currentAiMessageForHistory = aiFullResponseObject?.choices?.[0]?.message ||
                                                            (aiFullResponseObject?.content?.[0]?.text ? {role: "assistant", content: aiFullResponseObject.content[0].text} : null) ||
                                                            { role: "assistant", content: aiResponseMessageContent };

                            const newMessagesAfterPluginError = [...(parsedBody.messages || []), currentAiMessageForHistory];
                            // ===================== ROLE CHANGE HERE (ERROR) =======================
                            newMessagesAfterPluginError.push({ 
                                role: "user", // MODIFIED FROM "system"
                                content: `[系统错误] 插件 '${plugin.plugin_name_cn}' (ID: ${plugin.plugin_id}) 执行失败: ${pluginError.message}. 请尝试其他方法或告知用户此工具暂时不可用。` 
                            });
                            // ======================================================================
                            
                            const nextRequestDataOnError = { ...originalRequestData, body: { ...parsedBody, messages: newMessagesAfterPluginError }};
                            console.log("[NodeJS] 插件执行失败，将错误信息反馈给AI并重新请求...");
                            return await handleRequestAndPlugins(req, res, nextRequestDataOnError, recursionDepth + 1, 0);
                        }
                    }
                } 
            } 
        } 

        if (!pluginMatchedAndProcessed) {
            if (aiResponseMessageContent) { 
                if (currentDisplayMode === "final_ai_response_only") {
                    await fs.writeFile(CONFORM_CHAT_FILE, aiResponseMessageContent.trimEnd(), 'utf-8');
                    console.log(`[NodeJS] (Mode 3) ConformChat updated with final AI response.`);
                } else {
                    const currentConformContent = await fs.readFile(CONFORM_CHAT_FILE, 'utf-8');
                    let prefix = "";
                    if (currentConformContent.trim()) { 
                        if (!currentConformContent.endsWith('\n\n') && !currentConformContent.endsWith('\n')) {
                            prefix = "\n\n";
                        } else if (!currentConformContent.endsWith('\n\n') && currentConformContent.endsWith('\n')) {
                            prefix = "\n";
                        }
                    }
                    await fs.appendFile(CONFORM_CHAT_FILE, prefix + aiResponseMessageContent.trimEnd(), 'utf-8');
                     console.log(`[NodeJS] (Mode ${currentDisplayMode === "detailed_plugin_responses" ? 1 : 2}) Final AI response appended to ConformChat.`);
                }
            }

            if (res && !res.headersSent) {
                let finalConformChatContent = "";
                try {
                    finalConformChatContent = (await fs.readFile(CONFORM_CHAT_FILE, 'utf-8')).trim();
                    await initializeConformChatFile(); 
                } catch (readError) {
                    console.error("[NodeJS] 读取conformchat文件失败（在发送最终响应时）:", readError);
                    if (responseBodyBuffer && responseBodyBuffer.length > 0 && contentType.includes('application/json')) { 
                        console.warn("[NodeJS] conformchat读取失败，将尝试发送原始AI JSON响应。");
                        res.status(responseFromTarget.status);
                        responseFromTarget.headers.forEach((value, name) => {
                            if (!['content-encoding', 'transfer-encoding', 'connection', 'content-length'].includes(name.toLowerCase())) {
                                res.setHeader(name, value);
                            }
                        });
                        if (contentType) res.setHeader('Content-Type', contentType); 
                        res.send(responseBodyBuffer); 
                        return; 
                    } else {
                        res.status(500).json({ error: 'Conformchat processing failed and no original response to send.' });
                        return; 
                    }
                }
                
                let finalResponseToClient;
                const baseResponseObject = aiFullResponseObject || {
                    id: "conformchat-" + Date.now(),
                    object: "chat.completion",
                    created: Math.floor(Date.now() / 1000),
                    model: parsedBody.model || "unknown_model_conformchat",
                    choices: [{ index: 0, message: {}, finish_reason: "stop" }],
                };

                finalResponseToClient = JSON.parse(JSON.stringify(baseResponseObject)); 

                if (!finalResponseToClient.choices || !finalResponseToClient.choices[0]) { 
                    finalResponseToClient.choices = [{ index: 0, message: {}, finish_reason: "stop" }];
                }
                if (!finalResponseToClient.choices[0].message) {
                    finalResponseToClient.choices[0].message = {};
                }

                finalResponseToClient.choices[0].message.role = "assistant";
                finalResponseToClient.choices[0].message.content = finalConformChatContent || "[系统消息：AI未返回有效内容]";
                finalResponseToClient.choices[0].finish_reason = aiFullResponseObject?.choices?.[0]?.finish_reason || "stop";

                if (finalResponseToClient.usage && finalConformChatContent !== aiResponseMessageContent) {
                    console.warn("[NodeJS] Conformchat内容已替换原始AI回复，响应中的 'usage' 统计可能不再准确。");
                }
                
                console.log("[NodeJS] 插件链处理完毕，发送conformchat的聚合内容给客户端。");
                res.status(responseFromTarget.status).json(finalResponseToClient); 
            } else if (res && res.headersSent) {
                console.log("[NodeJS] 响应头已发送，无法再次发送最终响应。conformchat内容已生成但未发送。");
                await initializeConformChatFile(); 
            }
        }

    } catch (error) {
        console.error(`[NodeJS] (${currentDisplayMode}) 转发到 ${targetUrl} 失败或处理响应时出错 (递归 ${recursionDepth}, 继续 ${continuationDepth}):`, error.message, error.stack);
        const errorResBodyForLog = `[Error during request forwarding or response processing: ${error.message}]`;
        if (LOG_INTERCEPTED_DATA) {
            const mockErrorResponse = { status: 502, headers: new Map() }; 
            await logReceivedResponse(mockErrorResponse, errorResBodyForLog);
        }
        if (res && !res.headersSent) {
            const errorResponseToClient = {
                id: "error-proxy-" + Date.now(),
                object: "error",
                message: "代理转发或响应处理失败",
                details: error.message,
                target: targetUrl,
                choices: [{ index: 0, message: { role: "assistant", content: `[系统错误] 代理转发或处理到 ${targetUrl} 的请求失败: ${error.message}` }, finish_reason: "error" }]
            };
            res.status(502).json(errorResponseToClient);
        } else if (res) {
            res.end(); 
        }
        await initializeConformChatFile(); 
    }
}

app.get('/api/plugins', async (req, res) => { 
    try {
        if (!allPluginsWithStatus || !Array.isArray(allPluginsWithStatus)) {
            console.warn("[NodeJS] /api/plugins: allPluginsWithStatus 无效, 尝试重新加载规则...");
            await loadPluginRules(); 
        }
        res.json(allPluginsWithStatus || []); 
    } catch (error) {
        console.error(`[NodeJS] 获取插件规则失败 (/api/plugins):`, error);
        res.status(500).json({ message: '获取插件规则失败', error: error.message });
    }
});

app.post('/api/plugins', async (req, res) => {
    try {
        const newPluginsConfiguration = req.body;
        if (!Array.isArray(newPluginsConfiguration)) {
            return res.status(400).json({ message: '请求体必须是一个JSON数组' });
        }
        const processedConfig = newPluginsConfiguration.map(p => ({
            ...p,
            enabled: p.enabled === undefined ? true : p.enabled
        }));

        await fs.writeFile(PLUGINS_RULE_FILE, JSON.stringify(processedConfig, null, 2), 'utf-8');
        console.log(`[NodeJS] 插件规则已更新到 ${path.basename(PLUGINS_RULE_FILE)}`);
        await loadPluginRules(); 
        res.json({ message: '插件配置已成功更新并重新加载！' });
    } catch (error) {
        console.error(`[NodeJS] 更新插件规则失败 (/api/plugins):`, error);
        res.status(500).json({ message: '更新插件规则失败', error: error.message });
    }
});

app.get('/api/global-config', async (req, res) => {
    try {
        res.json(config || {}); 
    } catch (error) { 
        console.error(`[NodeJS] 获取全局配置失败 (/api/global-config):`, error);
        res.status(500).json({ message: '获取全局配置失败', error: error.message });
    }
});

app.post('/api/global-config', async (req, res) => {
    try {
        const newGlobalConfig = req.body;
        if (typeof newGlobalConfig !== 'object' || newGlobalConfig === null) {
            return res.status(400).json({ message: '请求体必须是一个有效的JSON对象' });
        }
        await fs.writeFile(CONFIG_FILE_PATH, JSON.stringify(newGlobalConfig, null, 2), 'utf-8');
        console.log(`[NodeJS] 全局配置已更新到 ${path.basename(CONFIG_FILE_PATH)}.`);
        
        loadFullConfig(); 
        reassignConfigVariables(); 
        await loadPluginRules(); 

        res.json({ message: '全局配置已成功更新！部分更改（如端口号）可能需要重启服务才能完全生效。' });
    } catch (error) {
        console.error(`[NodeJS] 更新全局配置失败 (/api/global-config):`, error);
        res.status(500).json({ message: '更新全局配置失败', error: error.message });
    }
});


app.get('/plugin-manager', (req, res) => {
    res.sendFile(path.join(__dirname, 'plugin_manager.html'));
});
app.get('/plugin_manager.js', (req, res) => {
    res.sendFile(path.join(__dirname, 'plugin_manager.js'));
});


app.all('*', async (req, res, next) => {
    if (req.path.startsWith('/api/') || req.path === '/plugin-manager' || req.path === '/plugin_manager.js') {
        return next(); 
    }

    const initialRequestData = {
        method: req.method,
        url: req.originalUrl, 
        headers: { ...req.headers }, 
        body: req.body, 
        sourceIp: req.ip || req.socket?.remoteAddress
    };
    
    delete initialRequestData.headers['content-length'];
    delete initialRequestData.headers['host']; 

    await handleRequestAndPlugins(req, res, initialRequestData, 0, 0);
});

app.use((err, req, res, next) => {
    console.error("[NodeJS] 未捕获的服务器错误:", err.stack || err.message || err);
    if (!res.headersSent) {
        res.status(500).json({ error: '服务器内部错误', details: err.message });
    } else {
        next(err); 
    }
});

(async () => {
    await initializeConformChatFile(); 
    await loadPluginRules();
    app.listen(PROXY_SERVER_PORT, '0.0.0.0', () => { 
        console.log("======================================================================");
        console.log(`[NodeJS] Xice_Aitoolbox 监听服务正在运行于端口: ${PROXY_SERVER_PORT}`);
        console.log(`[NodeJS] 所有发往此端口的请求将被处理(可能调用插件)并转发到: ${TARGET_PROXY_URL}`);
        console.log(`[NodeJS] 插件管理界面请访问: http://localhost:${PROXY_SERVER_PORT}/plugin-manager`);
        console.log(`[NodeJS] conformchat 文件路径: ${CONFORM_CHAT_FILE}`);
        if (LOG_INTERCEPTED_DATA) {
            console.log(`[NodeJS] 最新交互的请求将记录到: ${path.basename(SEND_LOG_FILE)}`);
            console.log(`[NodeJS] 最新交互的响应将记录到: ${path.basename(RECEIVED_LOG_FILE)}`);
        } else {
            console.log(`[NodeJS] 请求/响应日志记录已禁用`);
        }
        if (allPluginsWithStatus.length > 0) { 
            console.log(`[NodeJS] 共定义 ${allPluginsWithStatus.length} 个插件, 其中 ${activePlugins.length} 个已启用。`);
             activePlugins.forEach(p => console.log(`  - (启用) ID: ${p.plugin_id}, Name: ${p.plugin_name_cn}`));
            if (INJECT_PLUGIN_RULES_ON_FIRST_REQUEST && activePlugins.length > 0) {
                 console.log(`[NodeJS] 已启用插件的规则描述将在适当时机注入。`);
            } else if (activePlugins.length === 0) {
                console.log(`[NodeJS] 所有已定义的插件均被禁用，或没有插件被定义。`);
            }
        } else {
            console.log(`[NodeJS] 未加载任何插件或插件规则文件不存在/错误。`);
        }
        console.log(`[NodeJS] 当前 ConformChat 显示模式: ${CONFORM_CHAT_DISPLAY_MODE}`);
        console.log("======================================================================");
    }).on('error', (err) => {
        if (err.code === 'EADDRINUSE') {
            console.error(`[NodeJS] 致命错误：端口 ${PROXY_SERVER_PORT} 已被占用。请检查 config.json 或关闭占用该端口的程序。`);
        } else {
            console.error("[NodeJS] 启动服务器失败:", err);
        }
        process.exit(1);
    });
})();

process.on('SIGINT', () => {
    console.log('[NodeJS] 收到 SIGINT，正在关闭服务器...');
    process.exit(0); 
});