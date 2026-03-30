
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
    // Trả về một object đầy đủ các thuộc tính nếu không tìm thấy key
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
    // Đã gộp chung bắt ID để dùng đúng cho nút Back của bạn
    const btnBack = document.getElementById('goToDashboard') || document.getElementById('btn-back'); 
    
    const goToControl = document.getElementById('ControlBtn');
    const btnSettings = document.getElementById('btn-settings');
    const logoutBtn = document.getElementById('logoutBtn');

    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
            document.getElementById('userName').innerText = data.username;
            
            // XỬ LÝ LỖI HIỂN THỊ ROLE: Biến "admin" thành "administrator"
            let displayRole = data.role;
            if (displayRole === 'admin') displayRole = 'administrator';
            const userRoleEl = document.getElementById('userRole');
            if (userRoleEl) userRoleEl.innerText = displayRole;

            // Kiểm tra xem có phải Admin không
            const isAdmin = (data.role === 'administrator' || data.role === 'admin');

            // Ghi đè sự kiện nút Back (ĐÃ SỬA LẠI ĐƯỜNG DẪN TẠI ĐÂY)
            if (btnBack) {
                btnBack.onclick = (e) => {
                    e.preventDefault(); 
                    // Admin -> Quản lý Nhà kính | User -> Trang chủ
                    window.location.href = isAdmin ? '/admin_management/greenhouses' : '/';
                };
            }
        }
      })
      .catch(err => console.error("Lỗi lấy thông tin user:", err));
      
    if (btnSettings) {
        btnSettings.addEventListener('click', () => {
            window.location.href = '/manage';
        });
    }

    if (goToControl) {
        goToControl.addEventListener('click', function () {
            if (currentFieldId) {
                window.location.href = `/control?field_id=${currentFieldId}`;
            } else {
                window.location.href = '/control';
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            fetch('/logout', { method: 'POST' })
            .then(res => {
                if (!res.ok) throw new Error("Server trả về lỗi");
                return res.json();
            })
            .then(data => {
                if (data.success) { window.location.href = data.redirect || '/login'; } 
                else { alert(data.message || "Không thể đăng xuất."); }
            })
            .catch(error => { console.error("Lỗi kết nối!", error); });
        });
    }
});