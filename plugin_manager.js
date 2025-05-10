document.addEventListener('DOMContentLoaded', () => {
    // --- 插件管理相关 DOM ---
    const pluginsTableBody = document.querySelector('#plugins-table tbody');
    const pluginForm = {
        index: document.getElementById('plugin-index'),
        enabled: document.getElementById('plugin-enabled'),
        id: document.getElementById('plugin-id'),
        nameCn: document.getElementById('plugin-name-cn'),
        description: document.getElementById('rule-description'),
        placeholderStart: document.getElementById('placeholder-start'),
        placeholderEnd: document.getElementById('placeholder-end'),
        executablePath: document.getElementById('executable-path'),
        isPythonScript: document.getElementById('is-python-script'),
        acceptsParams: document.getElementById('accepts-parameters'),
        isInternalSignal: document.getElementById('is-internal-signal')
    };
    const submitPluginButton = document.getElementById('submit-plugin-form');
    const cancelEditPluginButton = document.getElementById('cancel-edit-plugin');
    const saveAllPluginsButton = document.getElementById('save-all-plugins');
    const pluginStatusMessageDiv = document.getElementById('status-message');

    let localPluginsCache = [];

    // --- 全局配置相关 DOM ---
    const globalConfigForm = {
        proxy_server_port: document.getElementById('config-proxy-server-port'),
        target_proxy_url: document.getElementById('config-target-proxy-url'),
        log_intercepted_data: document.getElementById('config-log-intercepted-data'),
        show_node_output_in_python: document.getElementById('config-show-node-output-in-python'),
        log_response_body_in_received_file: document.getElementById('config-log-response-body-in-received-file'),
        max_log_response_size_kb_in_received_file: document.getElementById('config-max-log-response-size-kb'),
        max_plugin_recursion_depth: document.getElementById('config-max-plugin-recursion-depth'),
        inject_plugin_rules_on_first_request: document.getElementById('config-inject-plugin-rules-on-first-request'),
        project_generator_allowed_base_paths_map: document.getElementById('config-project-generator-allowed-base-paths-map'),
        file_operations_allowed_base_paths: document.getElementById('config-file-operations-allowed-base-paths'),
        code_sandbox_python_timeout: document.getElementById('config-code-sandbox-python-timeout'),
        program_runner_timeout: document.getElementById('config-program-runner-timeout'),
        max_continuation_depth: document.getElementById('config-max-continuation-depth'),
        conform_chat_display_mode: document.getElementById('config-conform-chat-display-mode')
    };
    const saveGlobalConfigButton = document.getElementById('save-global-config');
    const globalStatusMessageDiv = document.getElementById('global-status-message');


    // --- 通用函数 ---
    function showStatusMessage(element, message, type = 'success', duration = 5000) {
        element.textContent = message;
        element.className = type; // Applies .success, .error or .warning class
        element.style.display = 'block';
        setTimeout(() => {
            element.style.display = 'none';
        }, duration);
    }

    // --- 插件管理逻辑 ---
    async function fetchPlugins() {
        try {
            const response = await fetch('/api/plugins');
            if (!response.ok) {
                throw new Error(`获取插件失败: ${response.statusText} (状态码: ${response.status})`);
            }
            const fetchedPlugins = await response.json();
            if (!Array.isArray(fetchedPlugins)) {
                 console.warn("API /api/plugins 未返回数组, 可能服务器端出错或数据格式不正确。使用空列表。");
                 localPluginsCache = [];
            } else {
                localPluginsCache = fetchedPlugins.map(p => ({ ...p, enabled: p.enabled === undefined ? true : p.enabled }));
            }
            renderPluginsTable();
            saveAllPluginsButton.style.display = localPluginsCache.length > 0 ? 'block' : 'none';
        } catch (error) {
            console.error('获取插件时出错:', error);
            showStatusMessage(pluginStatusMessageDiv, `加载插件列表失败: ${error.message}`, 'error');
            localPluginsCache = []; 
            renderPluginsTable(); 
            saveAllPluginsButton.style.display = 'none';
        }
    }

    function renderPluginsTable() {
        pluginsTableBody.innerHTML = '';
        if (!Array.isArray(localPluginsCache)) { 
            localPluginsCache = [];
        }

        localPluginsCache.forEach((plugin, index) => {
            const row = pluginsTableBody.insertRow();
            row.className = plugin.enabled ? '' : 'disabled-row';

            const enabledCell = row.insertCell();
            const enabledCheckbox = document.createElement('input');
            enabledCheckbox.type = 'checkbox';
            enabledCheckbox.checked = plugin.enabled;
            enabledCheckbox.title = plugin.enabled ? '点击禁用此插件' : '点击启用此插件';
            enabledCheckbox.onchange = () => {
                plugin.enabled = enabledCheckbox.checked;
                row.className = plugin.enabled ? '' : 'disabled-row';
                showStatusMessage(pluginStatusMessageDiv, `插件 "${plugin.plugin_name_cn}" 的启用状态已在本地更改。请点击“保存所有插件更改”。`, 'warning');
            };
            enabledCell.appendChild(enabledCheckbox);

            row.insertCell().textContent = plugin.plugin_id;
            row.insertCell().textContent = plugin.plugin_name_cn;
            row.insertCell().textContent = plugin.executable_path;
            row.insertCell().textContent = plugin.is_python_script ? '是' : '否';
            row.insertCell().textContent = plugin.accepts_parameters ? '是' : '否';
            row.insertCell().textContent = plugin.is_internal_signal ? '是' : '否';

            const actionsCell = row.insertCell();
            actionsCell.classList.add('actions');

            const editButton = document.createElement('button');
            editButton.textContent = '编辑';
            editButton.classList.add('edit-btn');
            editButton.onclick = () => loadPluginIntoForm(index);
            actionsCell.appendChild(editButton);

            const deleteButton = document.createElement('button');
            deleteButton.textContent = '删除';
            deleteButton.classList.add('delete-btn');
            deleteButton.onclick = () => deletePlugin(index);
            actionsCell.appendChild(deleteButton);
        });
    }

    function loadPluginIntoForm(index) {
        const plugin = localPluginsCache[index];
        pluginForm.index.value = index;
        pluginForm.enabled.checked = plugin.enabled === undefined ? true : plugin.enabled;
        pluginForm.id.value = plugin.plugin_id;
        pluginForm.nameCn.value = plugin.plugin_name_cn;
        pluginForm.description.value = plugin.rule_description;
        pluginForm.placeholderStart.value = plugin.placeholder_start;
        pluginForm.placeholderEnd.value = plugin.placeholder_end;
        pluginForm.executablePath.value = plugin.executable_path;
        pluginForm.isPythonScript.checked = plugin.is_python_script;
        pluginForm.acceptsParams.checked = plugin.accepts_parameters;
        pluginForm.isInternalSignal.checked = plugin.is_internal_signal || false;

        submitPluginButton.textContent = '更新插件';
        cancelEditPluginButton.style.display = 'inline-block';
        pluginForm.id.disabled = true; 
        window.scrollTo(0, document.querySelector('.form-section').offsetTop - 20);
    }

    function clearPluginForm() {
        pluginForm.index.value = '-1'; 
        pluginForm.enabled.checked = true; 
        pluginForm.id.value = '';
        pluginForm.nameCn.value = '';
        pluginForm.description.value = '';
        pluginForm.placeholderStart.value = '';
        pluginForm.placeholderEnd.value = '';
        pluginForm.executablePath.value = '';
        pluginForm.isPythonScript.checked = false;
        pluginForm.acceptsParams.checked = false;
        pluginForm.isInternalSignal.checked = false;

        submitPluginButton.textContent = '添加插件';
        cancelEditPluginButton.style.display = 'none';
        pluginForm.id.disabled = false; 
    }

    cancelEditPluginButton.addEventListener('click', clearPluginForm);

    submitPluginButton.addEventListener('click', () => {
        const pluginData = {
            enabled: pluginForm.enabled.checked,
            plugin_id: pluginForm.id.value.trim(),
            plugin_name_cn: pluginForm.nameCn.value.trim(),
            rule_description: pluginForm.description.value.trim(),
            placeholder_start: pluginForm.placeholderStart.value.trim(),
            placeholder_end: pluginForm.placeholderEnd.value.trim(),
            executable_path: pluginForm.executablePath.value.trim(),
            is_python_script: pluginForm.isPythonScript.checked,
            accepts_parameters: pluginForm.acceptsParams.checked,
            is_internal_signal: pluginForm.isInternalSignal.checked
        };

        if (!pluginData.plugin_id || !pluginData.plugin_name_cn || !pluginData.executable_path || !pluginData.placeholder_start || !pluginData.placeholder_end) {
            showStatusMessage(pluginStatusMessageDiv, '错误：插件ID、中文名称、可执行路径/脚本名、起始和结束占位符不能为空！', 'error');
            return;
        }

        const editIndex = parseInt(pluginForm.index.value, 10);

        if (editIndex > -1) { 
            localPluginsCache[editIndex] = pluginData;
        } else { 
            const existingPluginWithId = localPluginsCache.find(p => p.plugin_id === pluginData.plugin_id);
            if (existingPluginWithId) {
                showStatusMessage(pluginStatusMessageDiv, `错误：插件ID "${pluginData.plugin_id}" 已存在！请使用唯一的ID。`, 'error');
                return;
            }
            localPluginsCache.push(pluginData);
        }
        renderPluginsTable();
        clearPluginForm();
        showStatusMessage(pluginStatusMessageDiv, editIndex > -1 ? '插件已在本地更新。请点击“保存所有插件更改”按钮以持久化。' : '插件已在本地添加。请点击“保存所有插件更改”按钮以持久化。', 'warning');
        saveAllPluginsButton.style.display = 'block'; 
    });

    function deletePlugin(index) {
        if (confirm(`确定要删除插件 "${localPluginsCache[index].plugin_name_cn}" 吗？此操作在点击“保存所有插件更改”前不会生效。`)) {
            localPluginsCache.splice(index, 1);
            renderPluginsTable();
            showStatusMessage(pluginStatusMessageDiv, '插件已在本地删除。请点击“保存所有插件更改”按钮以持久化。', 'warning');
            if (localPluginsCache.length === 0) {
                saveAllPluginsButton.style.display = 'none';
            }
        }
    }

    saveAllPluginsButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/plugins', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(localPluginsCache) 
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: response.statusText }));
                throw new Error(`保存插件失败: ${errorData.message || response.statusText} (状态码: ${response.status})`);
            }
            const result = await response.json();
            showStatusMessage(pluginStatusMessageDiv, result.message || '插件配置已成功保存到服务器！', 'success');
            fetchPlugins(); 
        } catch (error) {
            console.error('保存插件时出错:', error);
            showStatusMessage(pluginStatusMessageDiv, `保存插件失败: ${error.message}`, 'error');
        }
    });

    // --- 全局配置逻辑 ---
    async function fetchGlobalConfig() {
        try {
            const response = await fetch('/api/global-config');
            if (!response.ok) {
                throw new Error(`获取全局配置失败: ${response.statusText} (状态码: ${response.status})`);
            }
            const configData = await response.json();
            populateGlobalConfigForm(configData);
        } catch (error) {
            console.error('获取全局配置时出错:', error);
            showStatusMessage(globalStatusMessageDiv, `加载全局配置失败: ${error.message}`, 'error');
        }
    }

    function populateGlobalConfigForm(configData) {
        globalConfigForm.proxy_server_port.value = configData.proxy_server_port || '';
        globalConfigForm.target_proxy_url.value = configData.target_proxy_url || '';
        globalConfigForm.log_intercepted_data.checked = configData.log_intercepted_data === undefined ? true : configData.log_intercepted_data;
        globalConfigForm.show_node_output_in_python.checked = configData.show_node_output_in_python === undefined ? true : configData.show_node_output_in_python;
        globalConfigForm.log_response_body_in_received_file.checked = configData.log_response_body_in_received_file === undefined ? true : configData.log_response_body_in_received_file;
        globalConfigForm.max_log_response_size_kb_in_received_file.value = configData.max_log_response_size_kb_in_received_file || '';
        globalConfigForm.max_plugin_recursion_depth.value = configData.max_plugin_recursion_depth || '';
        globalConfigForm.inject_plugin_rules_on_first_request.checked = configData.inject_plugin_rules_on_first_request === undefined ? true : configData.inject_plugin_rules_on_first_request;
        
        // 对于 JSON 对象和数组，我们期望它们在 textarea 中是格式化的 JSON 字符串
        globalConfigForm.project_generator_allowed_base_paths_map.value = configData.project_generator_allowed_base_paths_map ? JSON.stringify(configData.project_generator_allowed_base_paths_map, null, 2) : '{}';
        globalConfigForm.file_operations_allowed_base_paths.value = configData.file_operations_allowed_base_paths ? JSON.stringify(configData.file_operations_allowed_base_paths, null, 2) : '[]';
        
        globalConfigForm.code_sandbox_python_timeout.value = configData.code_sandbox_python_timeout || '';
        globalConfigForm.program_runner_timeout.value = configData.program_runner_timeout || '';
        globalConfigForm.max_continuation_depth.value = configData.max_continuation_depth || '';
        globalConfigForm.conform_chat_display_mode.value = configData.conform_chat_display_mode || 'detailed_plugin_responses';
    }

    saveGlobalConfigButton.addEventListener('click', async () => {
        const newConfig = {
            proxy_server_port: parseInt(globalConfigForm.proxy_server_port.value, 10) || 3001,
            target_proxy_url: globalConfigForm.target_proxy_url.value.trim(),
            log_intercepted_data: globalConfigForm.log_intercepted_data.checked,
            show_node_output_in_python: globalConfigForm.show_node_output_in_python.checked,
            log_response_body_in_received_file: globalConfigForm.log_response_body_in_received_file.checked,
            max_log_response_size_kb_in_received_file: parseInt(globalConfigForm.max_log_response_size_kb_in_received_file.value, 10) || 1024,
            max_plugin_recursion_depth: parseInt(globalConfigForm.max_plugin_recursion_depth.value, 10) || 5,
            inject_plugin_rules_on_first_request: globalConfigForm.inject_plugin_rules_on_first_request.checked,
            code_sandbox_python_timeout: parseInt(globalConfigForm.code_sandbox_python_timeout.value, 10) || 10,
            program_runner_timeout: parseInt(globalConfigForm.program_runner_timeout.value, 10) || 30,
            max_continuation_depth: parseInt(globalConfigForm.max_continuation_depth.value, 10) || 5,
            conform_chat_display_mode: globalConfigForm.conform_chat_display_mode.value
        };

        // 处理 JSON 文本区域
        try {
            newConfig.project_generator_allowed_base_paths_map = JSON.parse(globalConfigForm.project_generator_allowed_base_paths_map.value || '{}');
        } catch (e) {
            showStatusMessage(globalStatusMessageDiv, '错误：项目生成器路径映射不是有效的JSON！', 'error');
            return;
        }
        try {
            newConfig.file_operations_allowed_base_paths = JSON.parse(globalConfigForm.file_operations_allowed_base_paths.value || '[]');
            if (!Array.isArray(newConfig.file_operations_allowed_base_paths)) {
                showStatusMessage(globalStatusMessageDiv, '错误：文件操作允许路径必须是一个JSON数组！', 'error');
                return;
            }
        } catch (e) {
            showStatusMessage(globalStatusMessageDiv, '错误：文件操作允许路径不是有效的JSON数组！', 'error');
            return;
        }

        if (!newConfig.target_proxy_url) {
            showStatusMessage(globalStatusMessageDiv, '错误：目标转发URL不能为空！', 'error');
            return;
        }

        try {
            const response = await fetch('/api/global-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConfig)
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: response.statusText }));
                throw new Error(`保存全局配置失败: ${errorData.message || response.statusText} (状态码: ${response.status})`);
            }
            const result = await response.json();
            showStatusMessage(globalStatusMessageDiv, result.message || '全局配置已成功保存！部分更改需重启服务生效。', 'success', 7000);
             // 重新获取并填充表单，以确保与服务器同步（特别是如果服务器做了清理或转换）
            fetchGlobalConfig();
        } catch (error) {
            console.error('保存全局配置时出错:', error);
            showStatusMessage(globalStatusMessageDiv, `保存全局配置失败: ${error.message}`, 'error');
        }
    });


    // --- 初始化 ---
    fetchPlugins();
    fetchGlobalConfig();
});