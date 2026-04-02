// Các biến toàn cục
let fieldsList = [];
let currentIndex = 0;
let currentFieldId = null;

// ======================================================================
// 1. KHỞI TẠO BỘ NHỚ LƯU TRẠNG THÁI CÔNG TẮC (Dùng localStorage để chống mất khi F5)
// Cấu trúc: { "field_1": { "Light": true, "Vent": false }, "field_2": {...} }
// ======================================================================
let deviceStates = JSON.parse(localStorage.getItem('smartcare_device_states')) || {};

// Hàm cập nhật màn hình khi chuyển ruộng
function capNhatHienThiField() {
    if (fieldsList.length === 0) return;
    const currentField = fieldsList[currentIndex];
    currentFieldId = currentField.field_id;

    // Cập nhật tên ruộng
    const nameLabel = document.getElementById('current-field-name');
    if (nameLabel) nameLabel.textContent = currentField.field_name;

    // Cập nhật nút Back
    const btnBack = document.getElementById('goToDashboard');
    if (btnBack) {
        btnBack.onclick = () => {
            window.location.href = `/dashboard?field_id=${currentFieldId}`;
        };
    }

    // 2. GỌI HÀM CẬP NHẬT CÔNG TẮC CHO RUỘNG MỚI NÀY
    capNhatGiaoDienCongTac();
}

// Hàm load trạng thái từ bộ nhớ ra giao diện công tắc
function capNhatGiaoDienCongTac() {
    const toggles = document.querySelectorAll('.device-toggle');

    // Nếu ruộng này chưa từng được lưu trạng thái, tạo mặc định một danh sách rỗng
    if (!deviceStates[currentFieldId]) {
        deviceStates[currentFieldId] = {};
    }

    toggles.forEach(toggle => {
        const deviceName = toggle.getAttribute('data-device');
        // Đọc trạng thái từ bộ nhớ, nếu chưa có thì cho mặc định là TẮT (false)
        toggle.checked = deviceStates[currentFieldId][deviceName] || false;
    });
}

// Hàm tải danh sách ruộng từ Server
async function layDanhSachField() {
    try {
        const response = await fetch('/api/fields');
        if (!response.ok) throw new Error("Lỗi HTTP: " + response.status);

        fieldsList = await response.json();

        if (fieldsList && fieldsList.length > 0) {
            if (!currentFieldId) {
                const urlParams = new URLSearchParams(window.location.search);
                const targetFieldId = urlParams.get('field_id');

                if (targetFieldId) {
                    const foundIndex = fieldsList.findIndex(f => f.field_id === targetFieldId);
                    if (foundIndex !== -1) currentIndex = foundIndex;
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

// KHỞI CHẠY KHI TRANG TẢI XONG
document.addEventListener("DOMContentLoaded", () => {
    // Tải thông tin người dùng lên Navbar
    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          document.getElementById('userName').innerText = data.username;
          document.getElementById('userRole').innerText = data.role;
        }
      })
      .catch(err => console.error("Lỗi lấy thông tin user:", err));

    // Chức năng Đăng xuất
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            fetch('/logout', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.success) { window.location.href = '/login'; }
            });
        });
    }

    // Menu Quản lý
    const btnSettings = document.getElementById('btn-settings');
    if (btnSettings) {
        btnSettings.addEventListener('click', () => { window.location.href = '/manage'; });
    }

    // Nút chuyển ruộng trái/phải
    const btnPrev = document.getElementById('btn-prev-field');
    const btnNext = document.getElementById('btn-next-field');
    
    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            if (fieldsList.length === 0) return;
            currentIndex = (currentIndex - 1 + fieldsList.length) % fieldsList.length;
            const newFieldId = fieldsList[currentIndex].field_id;
            window.history.pushState({ field_id: newFieldId }, '', `/control?field_id=${newFieldId}`);
            capNhatHienThiField();
        });
    }

    if (btnNext) {
        btnNext.addEventListener('click', () => {
            if (fieldsList.length === 0) return;
            currentIndex = (currentIndex + 1) % fieldsList.length;
            const newFieldId = fieldsList[currentIndex].field_id;
            window.history.pushState({ field_id: newFieldId }, '', `/control?field_id=${newFieldId}`);
            capNhatHienThiField();
        });
    }

    window.addEventListener('popstate', () => {
        currentFieldId = null; 
        layDanhSachField();
    });

    // ======================================================================
    // 3. BẮT SỰ KIỆN VÀ LƯU VÀO BỘ NHỚ KHI NGƯỜI DÙNG GẠT CÔNG TẮC
    // ======================================================================
    const toggles = document.querySelectorAll('.device-toggle');
    toggles.forEach(toggle => {
        toggle.addEventListener('change', async function() {
            const deviceName = this.getAttribute('data-device');
            const isTurnedOn = this.checked;
            
            if (!currentFieldId) {
                alert("Đang tải dữ liệu ruộng, vui lòng thử lại sau!");
                this.checked = !isTurnedOn;
                return;
            }

            try {
                // Báo cáo lên Server Python
                const response = await fetch('/api/control_device', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        field_id: currentFieldId,
                        device_name: deviceName,
                        action: isTurnedOn ? 'ON' : 'OFF'
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    console.log(`Đã ${isTurnedOn ? 'BẬT' : 'TẮT'} ${deviceName} tại ${currentFieldId}`);
                    
                    // --- CẬP NHẬT VÀ LƯU VÀO LOCAL STORAGE MỚI NHẤT ---
                    if (!deviceStates[currentFieldId]) {
                        deviceStates[currentFieldId] = {};
                    }
                    deviceStates[currentFieldId][deviceName] = isTurnedOn;
                    localStorage.setItem('smartcare_device_states', JSON.stringify(deviceStates));
                    // --------------------------------------------------

                } else {
                    alert("Lỗi: " + data.message);
                    this.checked = !isTurnedOn; // Thất bại thì bật/tắt lại như cũ
                }
            } catch (error) {
                console.error("Lỗi gửi lệnh điều khiển:", error);
                alert("Lỗi kết nối đến máy chủ!");
                this.checked = !isTurnedOn; 
            }
        });
    });

    // Bắt đầu lấy dữ liệu
    layDanhSachField();
});