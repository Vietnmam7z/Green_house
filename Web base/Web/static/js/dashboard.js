// ==========================================
// CẤU HÌNH HIỂN THỊ THÔNG SỐ CẢM BIẾN
// ==========================================
const telemetryConfig = {
    "temperature": { label: "Temperature", unit: "°C", icon: "fa-temperature-half", color: "color-temp" },
    "humidity": { label: "Humidity", unit: "%", icon: "fa-droplet", color: "color-humid" },
    "moisture": { label: "Soil Moisture", unit: "%", icon: "fa-water", color: "color-soil" },
    "light": { label: "Ambient Light", unit: "lx", icon: "fa-sun", color: "color-light" },
    "status": { label: "Status", unit: "", icon: "fa-microchip", color: "color-default" }
};

function getConfig(key) {
    const lowerKey = key.toLowerCase();
    for (let prop in telemetryConfig) {
        if (lowerKey.includes(prop)) return telemetryConfig[prop];
    }
    return { label: key, unit: "", icon: "fa-microchip", color: "color-default" };
}

let fieldsList = []; 
let currentIndex = 0; 
let currentFieldId = null; 
let isAIEnabled = true; 
let currentLoggedUser = "Unknown";


let predictionStatusDB = 'OFF'; 
let aiStepValue = 25; 
let aiResultsCache = {}; 
let aiTimer = null;

// ==========================================
// PHẦN 1: ĐỒNG BỘ CẤU HÌNH AI TỪ DATABASE
// ==========================================
async function updateAISettings() {
    if (!currentFieldId) return;
    try {
        const response = await fetch(`/api/get_ai_settings?field_id=${currentFieldId}`);
        const data = await response.json();
        if (data.success && data.data) {
            aiStepValue = parseInt(data.data.step) || 25;
            predictionStatusDB = data.data.prediction_status || 'OFF'; 
            
            // Lấy config dị thường
            const anomalyStatusDB = data.data.anomaly_status || 'OFF';       
            const anomalyScoreLowDB = parseFloat(data.data.anomaly_score_low) || 0.25;
            const anomalyScoreHighDB = parseFloat(data.data.anomaly_score_high) || 0.85;

            // Truyền config sang module Notifications
            if (typeof NotificationSystem !== 'undefined') {
                NotificationSystem.updateConfig(anomalyStatusDB, anomalyScoreLowDB, anomalyScoreHighDB);
            }

            if (aiTimer) clearInterval(aiTimer);
            if (predictionStatusDB === 'ON') {
                aiTimer = setInterval(goiAiDuDoan, aiStepValue * 60 * 1000); 
            }
        }
    } catch (err) { console.error("Lỗi cập nhật cấu hình AI:", err); }
}


// ==========================================
// PHẦN 2: LUỒNG DỰ ĐOÁN GIÁ TRỊ TƯƠNG LAI (AI NEXT VALUE)
// ==========================================
async function goiAiDuDoan() {
    if (predictionStatusDB !== 'ON' || !isAIEnabled) return;
    const boxes = document.querySelectorAll('.ai-prediction-box');
    boxes.forEach(box => {
        const deviceId = box.getAttribute('data-device-id');
        const telemetryName = box.getAttribute('data-telemetry-name');
        const unit = box.getAttribute('data-unit');
        
        if (deviceId && telemetryName) {
            fetchAIPrediction(deviceId, telemetryName, box.id, unit);
        }
    });
}

async function fetchAIPrediction(deviceId, telemetryName, elementId, unit) {
    try {
        const response = await fetch('http://127.0.0.1:8000/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                device_id: deviceId,
                name: telemetryName,    
                step: aiStepValue
            })
        });
        const data = await response.json();
        const aiContainer = document.getElementById(elementId);
        let content = "";

        if (data.status === "success") {
            // Lấy giá trị temperature từ object predicted_next_val
            const predictedVal = data.predicted_next_val.temperature;
            content = `<i class="fa-solid fa-robot" style="color: #4CAF50;"></i> Next: ${predictedVal !== null ? predictedVal : '--'} ${unit}`;
        } else if (data.status === "waiting") {
            content = `<i class="fa-solid fa-spinner fa-spin"></i> Học: ${data.current_step}/${data.total_steps}`;
        }
        
        aiResultsCache[elementId] = content; 
        if (aiContainer) aiContainer.innerHTML = content;
    } catch (err) {
        aiResultsCache[elementId] = `<i class="fa-solid fa-robot" style="color: #F44336;"></i> AI offline`;
        if (document.getElementById(elementId)) {
            document.getElementById(elementId).innerHTML = aiResultsCache[elementId];
        }
    }
}


// ==========================================
// PHẦN 3: HIỂN THỊ DỮ LIỆU CẢM BIẾN REAL-TIME
// ==========================================
async function capNhatDuLieu() {
    if (!currentFieldId) return; 
    try {
        const response = await fetch('/api/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field_id: currentFieldId })
        });
        const data = await response.json();
        const container = document.getElementById("dynamic-devices-container");
        if (!container) return;

        container.innerHTML = "";
        if (Array.isArray(data)) {
            data.forEach(deviceObj => {
                for (const deviceName in deviceObj) {
                    const telemetries = deviceObj[deviceName];
                    const deviceSection = document.createElement("div");
                    deviceSection.innerHTML = `
                        <div class="section-title" style="margin-top: 25px;">
                            <i class="fa-solid fa-server"></i> ${deviceName}
                        </div>
                        <div class="panel-grid" id="grid-${deviceName.replace(/\s+/g, '-')}"></div>
                    `;
                    container.appendChild(deviceSection);
                    const gridContainer = deviceSection.querySelector('.panel-grid');

                    for (const teleKey in telemetries) {
                        const lowerTeleKey = teleKey.toLowerCase();

                        // Ẩn danh trường anomaly_score
                        if (lowerTeleKey === 'anomaly_score') continue;

                        const teleData = telemetries[teleKey];
                        
                        if (teleData) {
                            // Ưu tiên lấy trường consumption (nếu có)
                            const consumptionKey = Object.keys(teleData).find(k => k.includes('consumption'));
                            
                            let val;
                            if (consumptionKey && teleData[consumptionKey] !== undefined) {
                                val = parseFloat(teleData[consumptionKey]);
                            } else if (teleData.value !== undefined) {
                                val = parseFloat(teleData.value);
                            } else {
                                continue; 
                            }

                            const config = getConfig(teleKey);
                            const safeDeviceName = deviceName.replace(/\s+/g, '_');
                            const idGocChoAI = teleData.device_id || deviceName;

                            // ==============================================
                            // CHỐT CHẶN AI: CHỈ HIỂN THỊ KHUNG CHO NHIỆT ĐỘ
                            // ==============================================
                            const duocPhepDungAI = lowerTeleKey.includes('temperature');

                            let aiBoxHTML = "";
                            if (duocPhepDungAI) {
                                const aiElementId = `ai-${safeDeviceName}-${teleKey}`;
                                const currentAI = aiResultsCache[aiElementId] || `<i class="fa-solid fa-spinner fa-spin"></i> AI: Đang kết nối...`;
                                
                                aiBoxHTML = `
                                    <div id="${aiElementId}" class="ai-prediction-box" 
                                         data-device-id="${idGocChoAI}" 
                                         data-telemetry-name="${lowerTeleKey}" 
                                         data-unit="${config.unit}"
                                         style="display: ${(predictionStatusDB === 'ON' && isAIEnabled) ? 'block' : 'none'}; margin-top: 8px; font-size: 0.85rem; color: #00bcd4; font-weight: bold;">
                                        ${currentAI}
                                    </div>
                                `;
                            }

                            const panelHTML = `
                                <div class="panel" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'" 
                                     onclick="openChartModal('${idGocChoAI}', '${lowerTeleKey}', '${config.unit}', '${config.label}')">
                                    <div class="icon-box ${config.color || 'color-default'}">
                                        <i class="fa-solid ${config.icon}"></i>
                                    </div>
                                    <div class="data-box">
                                        <span class="data-label">${config.label}</span>
                                        <span class="data-value">${isNaN(val) ? "--" : val}
                                            <span class="data-unit">${config.unit}</span>
                                        </span>
                                        ${aiBoxHTML}
                                    </div>
                                </div>
                            `;
                            gridContainer.insertAdjacentHTML('beforeend', panelHTML);
                        }
                    }
                }
            });
        }
    } catch (err) { console.error("Lỗi hiển thị dữ liệu cảm biến:", err); }
}


// ==========================================
// PHẦN 5: CHUYỂN ĐỔI KHU VỰC VÀ HIỂN THỊ
// ==========================================
async function capNhatHienThiField() {
    if (fieldsList.length === 0) return;
    const currentField = fieldsList[currentIndex];
    currentFieldId = currentField.field_id; 
    
    document.getElementById('current-field-name').textContent = currentField.field_name;
    document.getElementById('current-field-id').textContent = currentField.field_id;
    
    aiResultsCache = {}; 
    await updateAISettings(); 
    await capNhatDuLieu(); 
    goiAiDuDoan(); 
}

async function layDanhSachField() {
    try {
        const response = await fetch('/api/fields');
        fieldsList = await response.json();
        if (fieldsList && fieldsList.length > 0) {
            const urlParams = new URLSearchParams(window.location.search);
            const targetFieldId = urlParams.get('field_id');
            if (targetFieldId) {
                const foundIndex = fieldsList.findIndex(f => f.field_id === targetFieldId);
                currentIndex = (foundIndex !== -1) ? foundIndex : 0;
            }
            capNhatHienThiField();
        }
    } catch (err) { console.error("Lỗi lấy danh sách ruộng:", err); }
}


// ==========================================
// PHẦN 6: LỊCH SỬ BIỂU ĐỒ SENSOR (CHART.JS)
// ==========================================
let myChartInstance = null; 
document.getElementById('closeChartModal')?.addEventListener('click', () => {
    document.getElementById('chartModal').style.display = 'none';
});
window.dongBieuDo = function() {
    const modal = document.getElementById('chartModal');
    if (modal) {
        modal.style.display = 'none';
    }
};  
let currentChartContext = { deviceId: '', telemetryName: '', unit: '', label: '' };

async function openChartModal(deviceId, telemetryName, unit, label, timeMode = "1d") {
    currentChartContext = { deviceId, telemetryName, unit, label };
    
    document.getElementById('chartModal').style.display = 'block';
    document.getElementById('chartTitle').innerText = `Lịch sử ${label} - ${deviceId}`;
    
    // Gọi hàm load dữ liệu
    await changeChartTime(timeMode);
}

async function changeChartTime(timeMode) {
    document.querySelectorAll('.chart-time-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`btn-time-${timeMode}`);
    if (activeBtn) activeBtn.classList.add('active');

    const { deviceId, telemetryName, unit, label } = currentChartContext;

    const payload = { device_name: deviceId, telemetry: telemetryName, time: timeMode };

    try {
        const response = await fetch('/api/send_chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        let chartData = Array.isArray(result) ? result : (result.data || []);
        
        const labels = []; 
        const dataValues = []; 
        
        if (chartData.length > 0) {
            chartData.forEach(item => {
                const dateObj = new Date(item.ts);
                const day = dateObj.getDate().toString().padStart(2, '0');
                const month = (dateObj.getMonth() + 1).toString().padStart(2, '0');
                const hours = dateObj.getHours().toString().padStart(2, '0');
                const minutes = dateObj.getMinutes().toString().padStart(2, '0');
                const timeString = timeMode === "1h" ? `${hours}:${minutes}` : `${day}/${month} ${hours}:${minutes}`;
                
                labels.push(timeString);
                dataValues.push(item.value);
            });
        }
        
        veBieuDo(labels, dataValues, label, unit);
        
    } catch (err) { 
        console.error("Lỗi tải dữ liệu biểu đồ:", err); 
    }
}

function veBieuDo(labels, data, labelName, unit) {
    const ctx = document.getElementById('sensorChart').getContext('2d');
    if (myChartInstance) {
        myChartInstance.destroy();
    }
    
    myChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `${labelName} (${unit})`,
                data: data,
                borderColor: '#00bcd4',
                backgroundColor: 'rgba(0, 188, 212, 0.1)',
                borderWidth: 2,
                pointRadius: 3,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: false }
            }
        }
    });
}


// ==========================================
// PHẦN 7: KHỞI TẠO HỆ THỐNG DOM LOADED
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
            currentLoggedUser = data.username;
            document.getElementById('userName').innerText = data.username;
            let displayRole = data.role === 'admin' ? 'administrator' : data.role;
            document.getElementById('userRole').innerText = displayRole;
            const isAdmin = (data.role === 'administrator' || data.role === 'admin');
            
            const btnBack = document.getElementById('goToDashboard') || document.getElementById('btn-back');
            if (btnBack) {
                btnBack.onclick = (e) => {
                    e.preventDefault();
                    window.location.href = isAdmin ? '/admin_management/greenhouses' : '/';
                };
            }

            const dropdownUserName = document.getElementById('dropdown-userName');
            if (dropdownUserName) dropdownUserName.innerText = data.username;

            const menuAccount = document.getElementById('menu-account');
            const menuBilling = document.getElementById('menu-billing');
            const menuHistory = document.getElementById('menu-history');
            const menuService = document.getElementById('menu-service');
            const menuAdmin = document.getElementById('menu-admin');
            const logoutBtn = document.getElementById('dropdown-logoutBtn');

            if (isAdmin) {
                if (menuAccount) menuAccount.style.display = 'flex';
                if (menuAdmin) menuAdmin.style.display = 'flex'; 
                if (menuBilling) menuBilling.style.display = 'none';
                if (menuHistory) menuHistory.style.display = 'none';
                if (menuService) menuService.style.display = 'none';
            } else {
                if (menuAccount) menuAccount.style.display = 'flex';
                if (menuBilling) menuBilling.style.display = 'flex';
                if (menuHistory) menuHistory.style.display = 'flex';
                if (menuService) menuService.style.display = 'flex';
                if (menuAdmin) menuAdmin.style.display = 'flex';
            }
            if (logoutBtn) logoutBtn.style.display = 'flex';

            const profileBox = document.querySelector('.user-profile');
            if (profileBox) {
                profileBox.style.cursor = 'pointer'; 
                profileBox.title = "Menu tài khoản"; 
            }
            
            // ---> KÍCH HOẠT MODULE NOTIFICATIONS TẠI ĐÂY <---
            if (typeof NotificationSystem !== 'undefined') {
                NotificationSystem.init(data.username);
            }
        }
      })
      .catch(err => console.error("Lỗi lấy thông tin user:", err)); 

    document.getElementById('ControlBtn')?.addEventListener('click', () => {
        window.location.href = currentFieldId ? `/control?field_id=${currentFieldId}` : '/control';
    });

    document.getElementById('dropdown-logoutBtn')?.addEventListener('click', (e) => {
        e.preventDefault();
        fetch('/logout', { method: 'POST' }).then(() => window.location.href = '/login');
    });

    document.getElementById('btn-prev-field')?.addEventListener('click', () => {
        currentIndex = (currentIndex - 1 + fieldsList.length) % fieldsList.length;
        window.history.pushState(null, '', `/dashboard?field_id=${fieldsList[currentIndex].field_id}`);
        capNhatHienThiField();
    });
    document.getElementById('btn-next-field')?.addEventListener('click', () => {
        currentIndex = (currentIndex + 1) % fieldsList.length;
        window.history.pushState(null, '', `/dashboard?field_id=${fieldsList[currentIndex].field_id}`);
        capNhatHienThiField();
    });
    
    layDanhSachField(); 
    setInterval(capNhatDuLieu, 5000); 
    setInterval(updateAISettings, 60000); 
});