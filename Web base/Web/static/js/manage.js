document.addEventListener('DOMContentLoaded', () => {
    loadSystemHierarchy();
});

function showMessage(msg, isSuccess) {
    const box = document.getElementById('notification-box');
    if (!box) return;
    box.textContent = msg;
    box.className = `notification ${isSuccess ? 'success' : 'error'}`;
    box.style.display = 'block';
    setTimeout(() => { box.style.display = 'none'; }, 3000);
}

// ==========================================
// 1. TẢI TOÀN BỘ CẤU TRÚC (RUỘNG -> THIẾT BỊ)
// ==========================================
async function loadSystemHierarchy() {
    const container = document.getElementById('hierarchy-container');
    if (!container) return;

    try {
        const resFields = await fetch('/api/fields');
        const fields = await resFields.json();
        container.innerHTML = '';

        for (const field of fields) {
            const fieldId = field.field_id;
            const fieldName = field.field_name || fieldId;
            
            const fieldBox = document.createElement('div');
            fieldBox.className = 'field-manage-box';
            
            fieldBox.innerHTML = `
                <div class="field-header">
                    <div id="view-field-${fieldId}" class="view-mode">
                        <span class="item-name-text"><i class="fa-solid fa-map-location-dot" style="color:#4CAF50;"></i> ${fieldName}</span>
                        <div style="display: flex; gap: 5px;">
                            <button class="btn-ai-toggle" onclick="toggleAISettings('${fieldId}')"><i class="fa-solid fa-robot"></i> Cấu hình AI</button>
                            <button class="btn-edit" onclick="toggleEdit('field', '${fieldId}', true)"><i class="fa-solid fa-pen"></i></button>
                        </div>
                    </div>
                    <div id="edit-field-${fieldId}" class="edit-mode" style="display: none;">
                        <input type="text" id="input-field-${fieldId}" class="item-input" value="${fieldName}">
                        <button class="btn-save" onclick="saveField('${fieldId}')"><i class="fa-solid fa-check"></i></button>
                        <button class="btn-cancel" onclick="toggleEdit('field', '${fieldId}', false)"><i class="fa-solid fa-xmark"></i></button>
                    </div>
                </div>
                
                <div class="device-list" id="devices-of-${fieldId}">
                    <span style="color:#999; font-size: 13px;">Đang tải thiết bị...</span>
                </div>

                <div class="ai-settings-section" id="ai-settings-${fieldId}" style="display: none;">
                    <div style="font-weight: bold; margin-bottom: 12px; color: #8e44ad;">
                        <i class="fa-solid fa-sliders"></i> Thông số AI Management (Field: ${fieldId})
                    </div>
                    <div class="ai-settings-grid">
                        <div class="ai-setting-item">
                            <label>anomaly_score_low</label>
                            <input type="number" step="0.01" id="ai-low-${fieldId}">
                        </div>
                        <div class="ai-setting-item">
                            <label>anomaly_score_high</label>
                            <input type="number" step="0.01" id="ai-high-${fieldId}">
                        </div>
                        <div class="ai-setting-item">
                            <label>step</label>
                            <input type="number" id="ai-step-${fieldId}">
                        </div>
                        <div class="ai-setting-item">
                            <label>anomaly_status</label>
                            <select id="ai-status-${fieldId}">
                                <option value="ON">ON</option>
                                <option value="OFF">OFF</option>
                            </select>
                        </div>
                        <div class="ai-setting-item">
                            <label>prediction_status</label>
                            <select id="ai-pred-status-${fieldId}">
                                <option value="ON">ON</option>
                                <option value="OFF">OFF</option>
                            </select>
                        </div>
                    </div>
                    <button class="btn-save-ai" onclick="saveAISettings('${fieldId}')">
                        <i class="fa-solid fa-floppy-disk"></i> Lưu Cấu Hình AI
                    </button>
                </div>
            `;
            container.appendChild(fieldBox);
            await loadDevicesForField(fieldId);
        }
    } catch (err) {
        container.innerHTML = '<span style="color:red">Lỗi tải dữ liệu hệ thống.</span>';
    }
}

// ==========================================
// 2. LOGIC CẤU HÌNH AI (QUAN TRỌNG NHẤT)
// ==========================================

// Hàm lấy dữ liệu thật từ DB và hiện form
async function toggleAISettings(fieldId) {
    const panel = document.getElementById(`ai-settings-${fieldId}`);
    
    // Nếu đang đóng thì mới đi lấy dữ liệu từ Database về điền vào ô
    if (panel.style.display === 'none' || panel.style.display === '') {
        try {
            const res = await fetch(`/api/get_ai_settings?field_id=${fieldId}`);
            const result = await res.json();

            if (result.success && result.data) {
                const d = result.data;
                // Điền dữ liệu từ Database vào các ô input
                document.getElementById(`ai-low-${fieldId}`).value = d.anomaly_score_low;
                document.getElementById(`ai-high-${fieldId}`).value = d.anomaly_score_high;
                document.getElementById(`ai-step-${fieldId}`).value = d.step;
                document.getElementById(`ai-status-${fieldId}`).value = d.anomaly_status;
                document.getElementById(`ai-pred-status-${fieldId}`).value = d.prediction_status;
                
                panel.style.display = 'block';
            } else {
                showMessage("Không tìm thấy cấu hình AI trong Database!", false);
            }
        } catch (err) {
            showMessage("Lỗi kết nối Server khi tải cấu hình AI!", false);
        }
    } else {
        panel.style.display = 'none';
    }
}

// Hàm gửi dữ liệu đã sửa về lại Database
async function saveAISettings(fieldId) {
    const payload = {
        field_id: fieldId,
        anomaly_score_low: parseFloat(document.getElementById(`ai-low-${fieldId}`).value),
        anomaly_score_high: parseFloat(document.getElementById(`ai-high-${fieldId}`).value),
        step: parseInt(document.getElementById(`ai-step-${fieldId}`).value),
        anomaly_status: document.getElementById(`ai-status-${fieldId}`).value,
        prediction_status: document.getElementById(`ai-pred-status-${fieldId}`).value,
    };

    try {
        const res = await fetch('/api/update_ai_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        showMessage(data.message, data.success);
        if (data.success) {
            document.getElementById(`ai-settings-${fieldId}`).style.display = 'none';
        }
    } catch (err) {
        showMessage("Lỗi kết nối Server khi lưu cấu hình AI!", false);
    }
}

// ==========================================
// 3. CÁC HÀM QUẢN LÝ TÊN (GIỮ NGUYÊN)
// ==========================================
async function loadDevicesForField(fieldId) {
    const devContainer = document.getElementById(`devices-of-${fieldId}`);
    try {
        const response = await fetch('/api/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field_id: fieldId })
        });
        const data = await response.json();
        devContainer.innerHTML = '';
        let hasDevice = false;

        if (Array.isArray(data)) {
            data.forEach(deviceObj => {
                for (const deviceName in deviceObj) {
                    hasDevice = true;
                    const safeName = deviceName.replace(/\s+/g, '-');
                    const domId = `${fieldId}-${safeName}`; 
                    const devDiv = document.createElement('div');
                    devDiv.className = 'device-item';
                    devDiv.innerHTML = `
                        <div id="view-device-${domId}" class="view-mode">
                            <span class="device-name-text"><i class="fa-solid fa-microchip" style="color:#7f8c8d;"></i> ${deviceName}</span>
                            <button class="btn-edit" onclick="toggleEdit('device', '${domId}', true)"><i class="fa-solid fa-pen"></i></button>
                        </div>
                        <div id="edit-device-${domId}" class="edit-mode" style="display: none;">
                            <input type="text" id="input-device-${domId}" class="item-input" value="${deviceName}">
                            <button class="btn-save" onclick="saveDevice('${deviceName}', '${domId}')"><i class="fa-solid fa-check"></i></button>
                            <button class="btn-cancel" onclick="toggleEdit('device', '${domId}', false)"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                    `;
                    devContainer.appendChild(devDiv);
                }
            });
        }
        if (!hasDevice) devContainer.innerHTML = '<span style="color:#999; font-size: 13px;">Không có thiết bị.</span>';
    } catch (err) {
        devContainer.innerHTML = '<span style="color:red; font-size: 13px;">Lỗi tải thiết bị.</span>';
    }
}

function toggleEdit(type, id, isEditing) {
    document.getElementById(`view-${type}-${id}`).style.display = isEditing ? 'none' : 'flex';
    document.getElementById(`edit-${type}-${id}`).style.display = isEditing ? 'flex' : 'none';
}

async function saveField(oldFieldId) {
    const newFieldName = document.getElementById(`input-field-${oldFieldId}`).value.trim();
    if (!newFieldName) return toggleEdit('field', oldFieldId, false);
    try {
        const res = await fetch('/api/rename_field', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field_id: oldFieldId, new_field_name: newFieldName })
        });
        const data = await res.json();
        showMessage(data.message, data.success);
        if (data.success) loadSystemHierarchy(); 
    } catch (err) {
        showMessage("Lỗi kết nối đến Server!", false);
    }
}

async function saveDevice(oldName, domId) {
    const newName = document.getElementById(`input-device-${domId}`).value.trim();
    if (!newName) return toggleEdit('device', domId, false);
    try {
        const res = await fetch('/api/rename_device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
        });
        const data = await res.json();
        showMessage(data.message, data.success);
        if (data.success) loadSystemHierarchy(); 
    } catch (err) {
        showMessage("Lỗi kết nối đến Server!", false);
    }
}