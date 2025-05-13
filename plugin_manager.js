document.addEventListener('DOMContentLoaded', () => {
    // --- Globals & DOM Cache ---
    const systemConfigForm = document.getElementById('system-config-form');
    const systemStatusMessage = document.getElementById('system-status-message');
    const pluginListContainer = document.getElementById('plugin-list-container');
    const pluginsStatusMessage = document.getElementById('plugins-status-message');
    const pluginModal = document.getElementById('plugin-config-modal');
    const pluginConfigForm = document.getElementById('plugin-config-form');
    const modalPluginName = document.getElementById('modal-plugin-name');
    const modalPluginIdInput = document.getElementById('modal-plugin-id'); // Hidden input for actual ID
    const modalPluginIdDisplay = document.getElementById('modal-plugin-id-display'); // Readonly display
    const modalPluginSpecificConfigArea = document.getElementById('modal-plugin-specific-config-area');

    let currentEditingPlugin = null; // Stores the full config of the plugin being edited

    // --- Tab Management ---
    window.openTab = function(event, tabName) {
        document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
        document.querySelectorAll('.tab-button').forEach(tb => tb.classList.remove('active'));
        document.getElementById(tabName).style.display = 'block';
        event.currentTarget.classList.add('active');
    }

    // --- Utility Functions ---
    function showStatus(element, message, type = 'success', duration = 5000) {
        element.textContent = message;
        element.className = `status-message ${type}`;
        element.style.display = 'block';
        if (duration > 0) {
            setTimeout(() => element.style.display = 'none', duration);
        }
    }

    function getFormJson(formElement) {
        const formData = new FormData(formElement);
        const jsonData = {};
        formData.forEach((value, key) => {
            if (formElement.elements[key]?.type === 'checkbox') {
                jsonData[key] = formElement.elements[key].checked;
            } else if (formElement.elements[key]?.type === 'number') {
                jsonData[key] = parseFloat(value) || 0;
            } else if (key.includes("JSON:")) { // Handle JSON textareas
                 try {
                    jsonData[key.replace("JSON:", "")] = JSON.parse(value || '{}');
                 } catch (e) {
                    showStatus(systemStatusMessage, `字段 ${key.replace("JSON:", "")} 的JSON格式无效!`, 'error');
                    throw e; // Propagate error to stop submission
                 }
            }
            else {
                jsonData[key] = value;
            }
        });
        return jsonData;
    }
    
    function populateForm(formElement, data) {
        for (const key in data) {
            if (formElement.elements[key]) {
                const field = formElement.elements[key];
                if (field.type === 'checkbox') {
                    field.checked = data[key];
                } else if (typeof data[key] === 'object' && data[key] !== null) { // Handle JSON objects for textareas
                    field.value = JSON.stringify(data[key], null, 2);
                }
                else {
                    field.value = data[key];
                }
            }
        }
    }

    // --- System Config ---
    async function fetchSystemConfig() {
        try {
            const response = await fetch('/api/system-config');
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            const config = await response.json();
            
            // Special handling for object/array fields that should be JSON in textareas
            const formFriendlyConfig = { ...config };
            if (config.project_generator_allowed_base_paths_map) {
                formFriendlyConfig.project_generator_allowed_base_paths_map = JSON.stringify(config.project_generator_allowed_base_paths_map, null, 2);
            }
            if (config.file_operations_allowed_base_paths) {
                formFriendlyConfig.file_operations_allowed_base_paths = JSON.stringify(config.file_operations_allowed_base_paths, null, 2);
            }
            populateForm(systemConfigForm, formFriendlyConfig);

        } catch (error) {
            showStatus(systemStatusMessage, `加载系统配置失败: ${error.message}`, 'error');
        }
    }

    systemConfigForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        try {
            const formData = new FormData(systemConfigForm);
            const configData = {};
            formData.forEach((value, key) => {
                const element = systemConfigForm.elements[key];
                if (element.type === 'checkbox') {
                    configData[key] = element.checked;
                } else if (element.type === 'number') {
                    configData[key] = parseFloat(value) || (key.includes("port") ? 3001 : 0);
                } else if (element.tagName === 'TEXTAREA') { // Assume textareas for JSON
                    try {
                        configData[key] = JSON.parse(value || (element.name.includes("map") ? '{}' : '[]'));
                    } catch (e) {
                        showStatus(systemStatusMessage, `配置项 "${element.labels[0]?.textContent || key}" 的JSON格式无效.`, 'error');
                        throw e; // Stop submission
                    }
                } 
                else {
                    configData[key] = value;
                }
            });

            const response = await fetch('/api/system-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message || `HTTP error ${response.status}`);
            showStatus(systemStatusMessage, result.message || '系统配置已保存！', 'success');
        } catch (error) {
            showStatus(systemStatusMessage, `保存系统配置失败: ${error.message}`, 'error');
        }
    });

    // --- Plugin Management ---
    async function fetchPlugins() {
        try {
            const response = await fetch('/api/plugins');
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            const plugins = await response.json();
            renderPluginList(plugins);
        } catch (error) {
            showStatus(pluginsStatusMessage, `加载插件列表失败: ${error.message}`, 'error');
        }
    }

    function renderPluginList(plugins) {
        pluginListContainer.innerHTML = '';
        if (!plugins || plugins.length === 0) {
            pluginListContainer.innerHTML = '<li>未发现任何插件。请检查Plugin目录。</li>';
            return;
        }
        plugins.forEach(plugin => {
            const item = document.createElement('li');
            item.className = `plugin-item ${plugin.enabled ? '' : 'disabled'}`;
            item.innerHTML = `
                <h3>${plugin.name} (ID: ${plugin.id}) <small>v${plugin.version || 'N/A'}</small></h3>
                <p>作者: ${plugin.author || '未知'}</p>
                <p>描述: ${plugin.description || '无'}</p>
                <p>状态: ${plugin.enabled ? '已启用' : '已禁用'}</p>
                <div class="actions">
                    <button onclick="openPluginModalForEdit('${plugin.id}')">配置</button>
                </div>
            `;
            pluginListContainer.appendChild(item);
        });
    }

    window.openPluginModalForEdit = async function(pluginId) {
        try {
            const response = await fetch(`/api/plugin-config/${pluginId}`);
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            currentEditingPlugin = await response.json();
            
            modalPluginName.textContent = `配置插件: ${currentEditingPlugin.plugin_name_cn}`;
            modalPluginIdInput.value = currentEditingPlugin.plugin_id; // Store actual ID
            modalPluginIdDisplay.value = currentEditingPlugin.plugin_id; // For display
            
            // Populate common fields
            document.getElementById('modal-plugin-enabled').checked = currentEditingPlugin.enabled === undefined ? true : currentEditingPlugin.enabled;
            document.getElementById('modal-plugin-name-cn').value = currentEditingPlugin.plugin_name_cn || '';
            document.getElementById('modal-plugin-version').value = currentEditingPlugin.version || '';
            document.getElementById('modal-plugin-author').value = currentEditingPlugin.author || '';
            document.getElementById('modal-plugin-description').value = currentEditingPlugin.description || ''; // This is rule_description in older files
            document.getElementById('modal-plugin-executable').value = currentEditingPlugin.executable_name || '';
            document.getElementById('modal-plugin-placeholder-start').value = currentEditingPlugin.placeholder_start || '';
            document.getElementById('modal-plugin-placeholder-end').value = currentEditingPlugin.placeholder_end || '';
            document.getElementById('modal-plugin-is-python').checked = currentEditingPlugin.is_python_script === undefined ? true : currentEditingPlugin.is_python_script;
            document.getElementById('modal-plugin-accepts-params').checked = currentEditingPlugin.accepts_parameters || false;
            document.getElementById('modal-plugin-is-internal').checked = currentEditingPlugin.is_internal_signal || false;

            // Dynamically generate specific config fields
            modalPluginSpecificConfigArea.innerHTML = '<h3>插件特定配置:</h3>';
            if (currentEditingPlugin.plugin_specific_config && Object.keys(currentEditingPlugin.plugin_specific_config).length > 0) {
                for (const key in currentEditingPlugin.plugin_specific_config) {
                    const value = currentEditingPlugin.plugin_specific_config[key];
                    const formGroup = document.createElement('div');
                    formGroup.className = 'form-group';
                    
                    const label = document.createElement('label');
                    label.htmlFor = `psc-${key}`;
                    label.textContent = `${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:`;
                    formGroup.appendChild(label);

                    let input;
                    if (typeof value === 'boolean') {
                        input = document.createElement('input');
                        input.type = 'checkbox';
                        input.checked = value;
                        const checkboxLabel = document.createElement('label');
                        checkboxLabel.className = 'checkbox-label';
                        checkboxLabel.htmlFor = `psc-${key}`;
                        checkboxLabel.style.marginLeft = "5px"; // Align with text input style
                        checkboxLabel.textContent = "启用"; // Generic for boolean
                        formGroup.appendChild(input);
                        formGroup.appendChild(checkboxLabel);

                    } else if (typeof value === 'number') {
                        input = document.createElement('input');
                        input.type = 'number';
                        input.value = value;
                    } else if (Array.isArray(value) || typeof value === 'object') {
                         input = document.createElement('textarea');
                         input.rows = value.length > 3 ? value.length +1 : 4;
                         input.value = JSON.stringify(value, null, 2);
                         const small = document.createElement('small');
                         small.textContent = " (JSON格式)";
                         formGroup.appendChild(small);
                    }
                    else { // Default to text
                        input = document.createElement('input');
                        input.type = 'text';
                        input.value = value;
                    }
                    if (input.tagName !== 'INPUT' || input.type !== 'checkbox') { // Add name only to non-boolean for simpler form data
                         input.id = `psc-${key}`;
                         input.name = `psc-${key}`; // Prefix to identify specific config
                         formGroup.appendChild(input);
                    } else { // For checkbox, the label is already there
                        input.id = `psc-${key}`;
                        input.name = `psc-${key}`;
                    }
                    modalPluginSpecificConfigArea.appendChild(formGroup);
                }
            } else {
                modalPluginSpecificConfigArea.innerHTML += '<p>此插件没有特定的配置项。</p>';
            }

            pluginModal.style.display = 'block';
        } catch (error) {
            showStatus(pluginsStatusMessage, `打开插件配置失败: ${error.message}`, 'error');
        }
    }

    window.closePluginModal = function() {
        pluginModal.style.display = 'none';
        currentEditingPlugin = null;
        pluginConfigForm.reset();
        modalPluginSpecificConfigArea.innerHTML = '<h3>插件特定配置:</h3>';
    }

    pluginConfigForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!currentEditingPlugin) return;

        const pluginId = modalPluginIdInput.value; // Get the actual ID from hidden input
        const updatedConfig = { ...currentEditingPlugin }; // Start with existing full config

        // Update common fields
        updatedConfig.enabled = document.getElementById('modal-plugin-enabled').checked;
        updatedConfig.plugin_name_cn = document.getElementById('modal-plugin-name-cn').value;
        updatedConfig.version = document.getElementById('modal-plugin-version').value;
        updatedConfig.author = document.getElementById('modal-plugin-author').value;
        updatedConfig.description = document.getElementById('modal-plugin-description').value;
        updatedConfig.executable_name = document.getElementById('modal-plugin-executable').value;
        updatedConfig.placeholder_start = document.getElementById('modal-plugin-placeholder-start').value;
        updatedConfig.placeholder_end = document.getElementById('modal-plugin-placeholder-end').value;
        updatedConfig.is_python_script = document.getElementById('modal-plugin-is-python').checked;
        updatedConfig.accepts_parameters = document.getElementById('modal-plugin-accepts-params').checked;
        updatedConfig.is_internal_signal = document.getElementById('modal-plugin-is-internal').checked;

        // Update specific config fields
        const specificConfig = {};
        if (currentEditingPlugin.plugin_specific_config) {
            for (const key in currentEditingPlugin.plugin_specific_config) {
                const inputElement = document.getElementById(`psc-${key}`);
                if (inputElement) {
                    if (inputElement.type === 'checkbox') {
                        specificConfig[key] = inputElement.checked;
                    } else if (inputElement.type === 'number') {
                        specificConfig[key] = parseFloat(inputElement.value);
                    } else if (inputElement.tagName === 'TEXTAREA') {
                        try { specificConfig[key] = JSON.parse(inputElement.value); }
                        catch(e) { alert(`特定配置项 ${key} 的JSON无效!`); return; }
                    }
                    else {
                        specificConfig[key] = inputElement.value;
                    }
                }
            }
        }
        updatedConfig.plugin_specific_config = specificConfig;
        
        try {
            const response = await fetch(`/api/plugin-config/${pluginId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedConfig)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message || `HTTP error ${response.status}`);
            showStatus(pluginsStatusMessage, result.message || `插件 ${pluginId} 配置已保存！`, 'success');
            closePluginModal();
            fetchPlugins(); // Refresh list
        } catch (error) {
            // Show error inside modal for better UX if modal is still open
            const modalErrorDiv = document.createElement('div');
            modalErrorDiv.className = 'status-message error';
            modalErrorDiv.textContent = `保存失败: ${error.message}`;
            modalErrorDiv.style.display = 'block';
            pluginConfigForm.insertBefore(modalErrorDiv, pluginConfigForm.firstChild);
            setTimeout(() => modalErrorDiv.remove(), 7000);
        }
    });

    // --- Init ---
    fetchSystemConfig();
    fetchPlugins();
    document.querySelector('.tab-button').click(); // Activate first tab
});
