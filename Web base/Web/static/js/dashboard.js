
const telemetryConfig = {
    "temperature": { label: "Temperature", unit: "°C", icon: "fa-temperature-half", color: "color-temp" },
    "humidity": { label: "Humidity", unit: "%", icon: "fa-droplet", color: "color-humid" },
    "moisture": { label: "Soil Moisture", unit: "%", icon: "fa-water", color: "color-soil" },
    "light": { label: "Ambient Light", unit: "lx", icon: "fa-sun", color: "color-light" }
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



function capNhatHienThiField() {
    if (fieldsList.length === 0) return;
    const currentField = fieldsList[currentIndex];
    currentFieldId = currentField.field_id; 
    
    const nameLabel = document.getElementById('current-field-name');
    if (nameLabel) nameLabel.textContent = currentField.field_name;
    
    capNhatDuLieu(); 
}

async function layDanhSachField() {
    try {
        const response = await fetch('/api/fields', { method: 'GET' });
        if (!response.ok) throw new Error("Lỗi HTTP: " + response.status);

        fieldsList = await response.json();
        
        if (fieldsList && fieldsList.length > 0) {
            if (!currentFieldId) {
                const urlParams = new URLSearchParams(window.location.search);
                const targetFieldId = urlParams.get('field_id');

                if (targetFieldId) {
                    const foundIndex = fieldsList.findIndex(f => f.field_id === targetFieldId);
                    if (foundIndex !== -1) {
                        currentIndex = foundIndex;
                    } else {
                        currentIndex = 0; 
                    }
                } else {
                    currentIndex = 0;
                }
                
                capNhatHienThiField();
            }
        } else {
            document.getElementById('current-field-name').textContent = "Không có dữ liệu";
        }
    } catch (err) {
        console.error("Lỗi lấy danh sách Field:", err);
    }
}

async function capNhatDuLieu() {
    if (!currentFieldId) return; 

    try {
        const response = await fetch('/api/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field_id: currentFieldId })
        });

        if (!response.ok) throw new Error("Lỗi HTTP: " + response.status);

        const data = await response.json();
        

        const container = document.getElementById("dynamic-devices-container");
        if (!container) return;

        // Xóa sạch vùng chứa để chuẩn bị vẽ lại từ đầu
        container.innerHTML = "";

        if (Array.isArray(data)) {
            // Bước 1: Lặp qua từng object thiết bị trong mảng
            data.forEach(deviceObj => {
                
                // Bước 2: Lấy tên thiết bị (VD: "SI Soil Moisture 8", "Moisture 5")
                for (const deviceName in deviceObj) {
                    const telemetries = deviceObj[deviceName];

                    // Tạo tiêu đề (tên thiết bị) và một vùng lưới (grid) chứa panel
                    const deviceSection = document.createElement("div");
                    deviceSection.innerHTML = `
                        <div class="section-title" style="margin-top: 25px;">
                            <i class="fa-solid fa-server"></i> ${deviceName}
                        </div>
                        <div class="panel-grid" id="grid-${deviceName.replace(/\s+/g, '-')}"></div>
                    `;
                    container.appendChild(deviceSection);
                    
                    const gridContainer = deviceSection.querySelector('.panel-grid');

                    // Bước 3: Lặp qua các thông số của thiết bị này (VD: moisture, temperature)
                    for (const teleKey in telemetries) {
                        const teleData = telemetries[teleKey];
                        
                        // Kiểm tra xem cấu trúc có trường "value" hay không
                        if (teleData && teleData.value !== undefined) {
                            const val = parseFloat(teleData.value);
                            const config = getConfig(teleKey);

                            // Sinh HTML cho từng panel thông số
                            const panelHTML = `
                                <div class="panel">
                                    <div class="icon-box ${config.color || 'color-default'}">
                                        <i class="fa-solid ${config.icon}"></i>
                                    </div>
                                    <div class="data-box">
                                        <span class="data-label">${config.label}</span>
                                        <span class="data-value">${isNaN(val) ? "--" : val}
                                            <span class="data-unit">${config.unit}</span>
                                        </span>
                                    </div>
                                </div>
                            `;
                            gridContainer.insertAdjacentHTML('beforeend', panelHTML);
                        }
                    }
                }
            });
        }
    } catch (err) {
        console.error("Lỗi tải dữ liệu cảm biến:", err);
    }
}


document.addEventListener("DOMContentLoaded", () => {
    const btnPrev = document.getElementById('btn-prev-field');
    const btnNext = document.getElementById('btn-next-field');

    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            if (fieldsList.length === 0) return;
            
            // Tính toán vị trí của ruộng trước đó
            currentIndex = (currentIndex - 1 + fieldsList.length) % fieldsList.length;
            
            // Lấy ID của ruộng mới
            const newFieldId = fieldsList[currentIndex].field_id;
            
            // THAY ĐỔI ĐƯỜNG DẪN URL TRÊN TRÌNH DUYỆT (Không load lại trang)
            window.history.pushState({ field_id: newFieldId }, '', `/dashboard?field_id=${newFieldId}`);
            
            // Cập nhật giao diện mượt mà
            capNhatHienThiField();
        });
    }

    if (btnNext) {
        btnNext.addEventListener('click', () => {
            if (fieldsList.length === 0) return;
            
            // Tính toán vị trí của ruộng tiếp theo
            currentIndex = (currentIndex + 1) % fieldsList.length;
            
            // Lấy ID của ruộng mới
            const newFieldId = fieldsList[currentIndex].field_id;
            
            // THAY ĐỔI ĐƯỜNG DẪN URL TRÊN TRÌNH DUYỆT (Không load lại trang)
            window.history.pushState({ field_id: newFieldId }, '', `/dashboard?field_id=${newFieldId}`);
            
            // Cập nhật giao diện mượt mà
            capNhatHienThiField();
        });
    }

    // Bắt thêm sự kiện khi người dùng bấm nút "Back" hoặc "Forward" trên trình duyệt
    window.addEventListener('popstate', (event) => {
        // Tải lại danh sách field để tự động nhảy về đúng tab theo URL
        layDanhSachField();
    });

    // Khởi chạy các hàm đầu tiên
    layDanhSachField(); 
    setInterval(layDanhSachField, 10000); 
    setInterval(capNhatDuLieu, 5000); 
});
document.addEventListener("DOMContentLoaded", () => {
    const goToDashboard = document.getElementById('goToDashboard');
    const goToControl = document.getElementById('ControlBtn');
    const btnSettings = document.getElementById('btn-settings');
    if (btnSettings) {
        btnSettings.addEventListener('click', () => {
            // Chuyển hướng sang route '/manage' của Python
            window.location.href = '/manage';
        });
    }
    if (goToDashboard) {
    goToDashboard.addEventListener('click', function () {
      window.location.href = '/';
    });
    }
    if (goToControl) {
    goToControl.addEventListener('click', function () {
      window.location.href = '/control';
    });
    }
});
// document.addEventListener("DOMContentLoaded", () => {
//     const goToControl = document.getElementById('goToControl');
//     if (goToControl) {
//     goToControl.addEventListener('click', function () {
//       window.location.href = '/';
//     });
//   }
// });