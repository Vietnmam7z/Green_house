const telemetryConfig = {
    "temperature": { label: "Temperature", unit: "°C", icon: "fa-temperature-half", color: "color-temp" },
    "humidity": { label: "Humidity", unit: "%", icon: "fa-droplet", color: "color-humid" },
    "moisture": { label: "Soil Moisture", unit: "%", icon: "fa-water", color: "color-soil" },
    "light": { label: "Ambient Light", unit: "lx", icon: "fa-sun", color: "color-light" },
    "status": { label: "Status", unit: "", icon: "fa-microchip", color: "color-default" } // Thêm status dựa trên ảnh DB của bạn
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

// QUẢN LÝ TÁCH THỜI GIAN
let aiStepValue = 25; 
let aiStatusDB = 'OFF';
let aiResultsCache = {}; 
let aiTimer = null;

// QUẢN LÝ THÔNG BÁO VÀ DATABASE
let anomolyPredictionStatusDB = 'OFF';
let anomolyScoreLowDB = 0.25;
let anomolyScoreHighDB = 0.85;
let notificationsList = [];
let currentLoggedUser = "Unknown";

// ==========================================
// 1. LOGIC AI ĐỘC LẬP
// ==========================================
async function updateAISettings() {
    if (!currentFieldId) return;
    try {
        const response = await fetch(`/api/get_ai_settings?field_id=${currentFieldId}`);
        const data = await response.json();
        if (data.success && data.data) {
            aiStepValue = parseInt(data.data.step) || 25;
            aiStatusDB = data.data.prediction_status;
            
            anomolyPredictionStatusDB = data.data.anomoly_prediction_status || 'OFF';
            anomolyScoreLowDB = parseFloat(data.data.anomoly_score_low) || 0.25;
            anomolyScoreHighDB = parseFloat(data.data.anomoly_score_high) || 0.85;

            if (aiTimer) clearInterval(aiTimer);
            if (aiStatusDB === 'ON') {
                aiTimer = setInterval(goiAiDuDoan, aiStepValue * 60 * 1000); 
            }
        }
    } catch (err) { console.error("Lỗi AI settings:", err); }
}

async function goiAiDuDoan() {
    if (aiStatusDB !== 'ON' || !isAIEnabled) return;
    const boxes = document.querySelectorAll('.ai-prediction-box');
    boxes.forEach(box => {
        // Lấy chính xác device_id và name từ HTML
        const deviceId = box.getAttribute('data-device-id');
        const telemetryName = box.getAttribute('data-telemetry-name');
        const unit = box.getAttribute('data-unit');
        
        if (deviceId && telemetryName) {
            fetchAIPrediction(deviceId, telemetryName, box.id, unit);
        }
    });
}

// HÀM GỬI DATA CHO SERVER AI
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
            content = `<i class="fa-solid fa-robot" style="color: #4CAF50;"></i> Next: ${data.predicted_next_val} ${unit}`;
            
            if (anomolyPredictionStatusDB === 'ON' && data.anomaly_score !== undefined) {
                const score = parseFloat(data.anomaly_score);
                const fieldName = document.getElementById('current-field-name').textContent;
                const displayDeviceName = `${deviceId} (${telemetryName})`;

                if (score >= anomolyScoreHighDB) {
                    addNotificationToDBandUI("CRITICAL", deviceId, displayDeviceName, score, fieldName);
                } else if (score >= anomolyScoreLowDB) {
                    addNotificationToDBandUI("WARNING", deviceId, displayDeviceName, score, fieldName);
                }
            }
        } else if (data.status === "waiting") {
            const timeRemaining = (data.total_steps - data.current_step) * aiStepValue;
            content = `<i class="fa-solid fa-spinner fa-spin"></i> Học: ${data.current_step}/${data.total_steps}`;
        }
        
        aiResultsCache[elementId] = content; 
        if (aiContainer) aiContainer.innerHTML = content;
    } catch (err) {
        aiResultsCache[elementId] = `<i class="fa-solid fa-robot" style="color: #F44336;"></i> AI offline`;
    }
}

// ==========================================
// 2. CẬP NHẬT DỮ LIỆU CẢM BIẾN (5 GIÂY)
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
                        const teleData = telemetries[teleKey];
                        if (teleData && teleData.value !== undefined) {
                            const val = parseFloat(teleData.value);
                            const config = getConfig(teleKey);
                            const safeDeviceName = deviceName.replace(/\s+/g, '_');
                            const aiElementId = `ai-${safeDeviceName}-${teleKey}`;

                            const currentAI = aiResultsCache[aiElementId] || `<i class="fa-solid fa-spinner fa-spin"></i> AI: Đang kết nối...`;

                            const panelHTML = `
                                <div class="panel" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'" onclick="openChartModal('${deviceName}', '${teleKey}', '${config.unit}', '${config.label}')">
                                    <div class="icon-box ${config.color || 'color-default'}">
                                        <i class="fa-solid ${config.icon}"></i>
                                    </div>
                                    <div class="data-box">
                                        <span class="data-label">${config.label}</span>
                                        <span class="data-value">${isNaN(val) ? "--" : val}
                                            <span class="data-unit">${config.unit}</span>
                                        </span>
                                        <!-- THIẾT LẬP data-device-id VÀ data-telemetry-name TRÙNG KHỚP DATABASE -->
                                        <div id="${aiElementId}" class="ai-prediction-box" 
                                             data-device-id="${deviceName}" 
                                             data-telemetry-name="${teleKey}" 
                                             data-unit="${config.unit}"
                                             style="display: ${(aiStatusDB === 'ON' && isAIEnabled) ? 'block' : 'none'}; margin-top: 8px; font-size: 0.85rem; color: #00bcd4; font-weight: bold;">
                                            ${currentAI}
                                        </div>
                                    </div>
                                </div>
                            `;
                            gridContainer.insertAdjacentHTML('beforeend', panelHTML);
                        }
                    }
                }
            });
        }
    } catch (err) { console.error(err); }
}

// ==========================================
// 3. KHỞI TẠO VÀ HEADER
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
    } catch (err) { console.error(err); }
}

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

            // --- ĐOẠN MÃ THÊM MỚI BẮT ĐẦU TỪ ĐÂY ---
            const profileBox = document.querySelector('.user-profile');
            if (profileBox) {
                profileBox.style.cursor = 'pointer'; // Hiển thị con trỏ dạng bàn tay
                profileBox.title = "Xem thông tin cá nhân và thanh toán"; // Gợi ý khi di chuột
                profileBox.addEventListener('click', () => {
                    window.location.href = '/profile'; // Chuyển hướng sang trang profile
                });
            }
            // --- KẾT THÚC ĐOẠN MÃ THÊM MỚI ---
        }
      })
      .catch(err => console.error("Lỗi lấy thông tin user:", err)); // Thêm catch lỗi cho an toàn

    document.getElementById('ControlBtn')?.addEventListener('click', () => {
        window.location.href = currentFieldId ? `/control?field_id=${currentFieldId}` : '/control';
    });
    document.getElementById('btn-settings')?.addEventListener('click', () => window.location.href = '/manage');
    document.getElementById('logoutBtn')?.addEventListener('click', (e) => {
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
    setInterval(kiemTraCanhBaoDiThuong, 5000);
});

// ==========================================
// 4. HÀM XỬ LÝ THÔNG BÁO VÀ CHUÔNG 
// ==========================================
async function addNotificationToDBandUI(status, device_id, displayDeviceName, score, fieldName = "Unknown Field") {
    const ts = Math.floor(Date.now() / 1000); 
    
    let message = status === "CRITICAL" 
        ? `Nguy cấp: [${fieldName}] ${displayDeviceName} vượt ngưỡng High (${score})` 
        : `Cảnh báo: [${fieldName}] ${displayDeviceName} vượt ngưỡng Low (${score})`;
    let color = status === "CRITICAL" ? "#f44336" : "#ff9800";
    
    notificationsList.unshift({
        status: status,
        device_id: device_id,
        ts: ts,
        username: currentLoggedUser,
        message: message, 
        color: color,     
        timeString: new Date().toLocaleTimeString()
    });
    
    if (notificationsList.length > 10) notificationsList.pop(); 
    renderBellUI();

    // try {
    //     await fetch('/api/save_notification', { 
    //         method: 'POST',
    //         headers: { 'Content-Type': 'application/json' },
    //         body: JSON.stringify({
    //             status: status,
    //             device_id: device_id,
    //             ts: ts,
    //             username: currentLoggedUser
    //         })
    //     });
    // } catch(err) {
    //     console.error("Lỗi đồng bộ thông báo:", err);
    // }
}

function renderBellUI() {
    const bellIcon = document.querySelector('img[alt="Notifications"]');
    if (!bellIcon) return;

    let bellWrapper = bellIcon.closest('.bell-wrapper-container');
    if (!bellWrapper) {
        bellWrapper = document.createElement('div');
        bellWrapper.className = 'bell-wrapper-container';
        bellWrapper.style.position = 'relative';
        bellWrapper.style.display = 'inline-block';
        bellIcon.parentNode.insertBefore(bellWrapper, bellIcon);
        bellWrapper.appendChild(bellIcon);
    }
    
    let badge = document.getElementById('ai-bell-badge');
    if (!badge) {
        badge = document.createElement('span');
        badge.id = 'ai-bell-badge';
        badge.style.cssText = 'position: absolute; top: -5px; right: -5px; background: red; color: white; border-radius: 50%; padding: 2px 6px; font-size: 10px; font-weight: bold; cursor: pointer;';
        bellWrapper.appendChild(badge);
    }
    badge.innerText = notificationsList.length;
    badge.style.display = notificationsList.length > 0 ? 'block' : 'none';

    let notifBox = document.getElementById('ai-notif-box');
    if (!notifBox) {
        notifBox = document.createElement('div');
        notifBox.id = 'ai-notif-box';
        notifBox.style.cssText = 'position: absolute; top: 100%; right: 0; margin-top: 10px; background: white; border: 1px solid #ccc; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 300px; max-height: 400px; overflow-y: auto; z-index: 9999; border-radius: 5px; display: none;';
        bellWrapper.appendChild(notifBox);
        
        bellWrapper.style.cursor = 'pointer';
        bellWrapper.addEventListener('click', function() {
            notifBox.style.display = notifBox.style.display === 'none' ? 'block' : 'none';
        });
    }

    if (notificationsList.length === 0) {
        notifBox.innerHTML = '<div style="padding: 10px; text-align: center; color: #666;">Không có thông báo</div>';
    } else {
        notifBox.innerHTML = notificationsList.map(n => `
            <div style="border-bottom: 1px solid #eee; padding: 10px; font-size: 13px; line-height: 1.4; text-align: left;">
                <strong style="color: ${n.color};">[${n.status}]</strong> ${n.message} <br>
                <span style="color: #999; font-size: 11px;">${n.timeString}</span>
            </div>
        `).join('');
    }
}
// ==========================================
// 5. HÀM VẼ BIỂU ĐỒ (CHART.JS)
// ==========================================
let myChartInstance = null; // Biến lưu trữ biểu đồ hiện tại

// Đóng Popup khi bấm nút X
document.getElementById('closeChartModal')?.addEventListener('click', () => {
    document.getElementById('chartModal').style.display = 'none';
});

// Hàm mở Modal và vẽ biểu đồ
async function openChartModal(deviceId, telemetryName, unit, label) {
    document.getElementById('chartModal').style.display = 'block';
    document.getElementById('chartTitle').innerText = `Lịch sử ${label} - ${deviceId}`;
    
    try {
        // Gọi API lấy lịch sử dữ liệu (Bước 2)
        const response = await fetch(`/api/send_chart?device_id=${encodeURIComponent(deviceId)}&name=${encodeURIComponent(telemetryName)}`);
        const result = await response.json();
        
        if (result.success && result.data) {
            const labels = []; // Trục X (Thời gian)
            const dataValues = []; // Trục Y (Giá trị)
            
            result.data.forEach(item => {
                // Đổi ts (mili-giây) sang dạng giờ:phút:giây
                const dateObj = new Date(item.ts);
                const timeString = `${dateObj.getHours()}:${dateObj.getMinutes() < 10 ? '0' : ''}${dateObj.getMinutes()}`;
                
                labels.push(timeString);
                dataValues.push(item.value);
            });
            
            veBieuDo(labels, dataValues, label, unit);
        }
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
        type: 'line', // Biểu đồ đường thẳng
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
function dongBieuDo() {
    const modal = document.getElementById('chartModal');
    if (modal) {
        modal.style.display = 'none';
    }
    if (myChartInstance) {
        myChartInstance.destroy();
        myChartInstance = null;
    }
}
async function kiemTraCanhBaoDiThuong() {
   
    if (anomolyPredictionStatusDB !== 'ON') return; 

    try {
        const response = await fetch('/api/check_anomaly');
        const data = await response.json();

        if (data.success) {
            const score = parseFloat(data.anomaly_score);
            const deviceName = data.device_name;
            const fieldName = data.field_name;

            let status = null;
            if (score >= anomolyScoreHighDB) {
                status = "CRITICAL";
            } else if (score >= anomolyScoreLowDB) {
                status = "WARNING";
            }
            if (status) {
                addNotificationToDBandUI(status, deviceName, deviceName, score, fieldName);
            }
        }
    } catch (err) {
        console.error("Lỗi tải dữ liệu cảnh báo dị thường:", err);
    }
}