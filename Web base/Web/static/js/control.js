// Các biến toàn cục
let fieldsList = [];
let currentIndex = 0;
let currentFieldId = null;

// ======================================================================
// 1. HÀM ĐỒNG BỘ TRẠNG THÁI TỪ DATABASE (Thay thế cho localStorage cũ)
// ======================================================================
function syncControlStates() {
    if (!currentFieldId) return;

    fetch(`/api/get_control_status?field_id=${currentFieldId}`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.states) {
                // Quét tất cả các công tắc trên giao diện
                const toggles = document.querySelectorAll('.device-toggle');
                
                toggles.forEach(toggle => {
                    const deviceName = toggle.getAttribute('data-device');
                    // Lấy trạng thái từ DB, nếu 'ON' thì là true, ngược lại là false
                    const stateFromDB = data.states[deviceName];
                    const isChecked = (stateFromDB === 'ON');
                    
                    // Chỉ cập nhật nếu trạng thái trên UI khác với DB (tránh chớp nháy)
                    if (toggle.checked !== isChecked) {
                        toggle.checked = isChecked;
                    }
                });
            }
        })
        .catch(err => console.error("Lỗi đồng bộ Control:", err));
}

// Hàm cập nhật màn hình khi chuyển ruộng
function capNhatHienThiField() {
    if (fieldsList.length === 0) return;
    const currentField = fieldsList[currentIndex];
    currentFieldId = currentField.field_id;

    // Cập nhật Field Name
    const nameLabel = document.getElementById('current-field-name');
    if (nameLabel) nameLabel.textContent = currentField.field_name;

    // Cập nhật Field ID (MỚI THÊM)
    const idLabel = document.getElementById('current-field-id');
    if (idLabel) idLabel.textContent = currentField.field_id;

    // Cập nhật URL cho nút Back để lùi về đúng Dashboard của ruộng hiện tại
    const btnBack = document.getElementById('goToDashboard') || document.getElementById('btn-back');
    if (btnBack) {
        btnBack.onclick = (e) => {
            e.preventDefault();
            window.location.href = `/dashboard?field_id=${currentFieldId}`;
        };
    }

    // Gọi đồng bộ ngay lập tức khi vừa chuyển sang ruộng mới
    syncControlStates();
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

// ======================================================================
// KHỞI CHẠY KHI TRANG TẢI XONG
// ======================================================================
document.addEventListener("DOMContentLoaded", () => {
    // 2. LẤY THÔNG TIN USER (Đã fix hiển thị administrator)
    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
            document.getElementById('userName').innerText = data.username;
            
            // XỬ LÝ ĐỔI TÊN ROLE TỪ "admin" THÀNH "administrator"
            let displayRole = data.role;
            if (displayRole === 'admin') displayRole = 'administrator';
            
            const userRoleEl = document.getElementById('userRole');
            if (userRoleEl) userRoleEl.innerText = displayRole;
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
    // 3. GỬI LỆNH LÊN SERVER KHI NGƯỜI DÙNG GẠT CÔNG TẮC
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
                // Báo cáo lệnh điều khiển lên Server (Đồng thời server sẽ lưu vào DB)
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
                    // (Đã xóa phần lưu localStorage ở đây vì Server đã lo việc nhớ trạng thái)
                } else {
                    alert("Lỗi: " + data.message);
                    this.checked = !isTurnedOn; // Thất bại thì giật công tắc về lại như cũ
                }
            } catch (error) {
                console.error("Lỗi gửi lệnh điều khiển:", error);
                alert("Lỗi kết nối đến máy chủ!");
                this.checked = !isTurnedOn; 
            }
        });
    });

    // Bắt đầu chu trình lấy dữ liệu
    layDanhSachField();

    // Thiết lập vòng lặp hỏi thăm Server mỗi 2 giây để đồng bộ tự động
    setInterval(syncControlStates, 2000);
});