document.addEventListener('DOMContentLoaded', () => {
    loadSystemHierarchy();
});

function showMessage(msg, isSuccess) {
    const box = document.getElementById('notification-box');
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
            const fieldName = field.field_name || fieldId; // Lấy tên ruộng
            
            const fieldBox = document.createElement('div');
            fieldBox.className = 'field-manage-box';
            
            // Đã thay đổi: Hiển thị và Nhập liệu bằng fieldName thay vì fieldId
            fieldBox.innerHTML = `
                <div class="field-header">
                    <div id="view-field-${fieldId}" class="view-mode">
                        <span class="item-name-text"><i class="fa-solid fa-map-location-dot" style="color:#4CAF50;"></i> ${fieldName}</span>
                        <button class="btn-edit" onclick="toggleEdit('field', '${fieldId}', true)"><i class="fa-solid fa-pen"></i></button>
                    </div>
                    <div id="edit-field-${fieldId}" class="edit-mode" style="display: none;">
                        <input type="text" id="input-field-${fieldId}" class="item-input" value="${fieldName}">
                        
                        <button class="btn-save" onclick="saveField('${fieldId}', '${fieldName}')"><i class="fa-solid fa-check"></i></button>
                        <button class="btn-cancel" onclick="toggleEdit('field', '${fieldId}', false)"><i class="fa-solid fa-xmark"></i></button>
                    </div>
                </div>
                <div class="device-list" id="devices-of-${fieldId}">
                    <span style="color:#999; font-size: 13px;">Đang tải thiết bị...</span>
                </div>
            `;
            container.appendChild(fieldBox);

            loadDevicesForField(fieldId);
        }
    } catch (err) {
        container.innerHTML = '<span style="color:red">Lỗi tải dữ liệu hệ thống.</span>';
    }
}

async function loadDevicesForField(fieldId) {
    const devContainer = document.getElementById(`devices-of-${fieldId}`);
    try {
        const response = await fetch('/api/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                field_id: fieldId
            })
        });
        const data = await response.json();
        devContainer.innerHTML = '';

        let hasDevice = false;

        if (Array.isArray(data)) {
            data.forEach(deviceObj => {
                for (const deviceName in deviceObj) {
                    hasDevice = true;
                    // Tạo ID an toàn cho HTML
                    const safeName = deviceName.replace(/\s+/g, '-');
                    const domId = `${fieldId}-${safeName}`; // Gắn thêm fieldId để ID không trùng lặp

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

        if (!hasDevice) {
            devContainer.innerHTML = '<span style="color:#999; font-size: 13px;">Không có thiết bị.</span>';
        }
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
    if (!newFieldName || newFieldName === oldFieldId) return toggleEdit('field', oldFieldId, false);

    try {
        const res = await fetch('/api/rename_field', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field_id: oldFieldId, new_field_name: newFieldName })
        });
        const data = await res.json();
        showMessage(data.message, data.success);
        if (data.success) loadSystemHierarchy(); // Refresh toàn bộ cây
    } catch (err) {
        showMessage("Lỗi kết nối đến Server!", false);
    }
}

async function saveDevice(oldName, domId) {
    const newName = document.getElementById(`input-device-${domId}`).value.trim();
    if (!newName || newName === oldName) return toggleEdit('device', domId, false);

    try {
        const res = await fetch('/api/rename_device', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
        });
        const data = await res.json();
        showMessage(data.message, data.success);
        if (data.success) loadSystemHierarchy(); // Refresh toàn bộ cây để update tên
    } catch (err) {
        showMessage("Lỗi kết nối đến Server!", false);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const goToDashboard = document.getElementById('goToDashboard');
    const goToControl = document.getElementById('ControlBtn');
    const btnSettings = document.getElementById('btn-settings');
    
    if (btnSettings) {
        btnSettings.addEventListener('click', () => { window.location.href = '/manage'; });
    }
    if (goToDashboard) {
        goToDashboard.addEventListener('click', () => { window.location.href = '/'; });
    }
    if (goToControl) {
        goToControl.addEventListener('click', () => { window.location.href = '/control'; });
    }
});