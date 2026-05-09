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

            // BỘ KHÓA UI: Làm mờ (disable) công tắc trong lúc chờ Server
            this.disabled = true;

            try {
                // Báo cáo lệnh điều khiển lên Server
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
                } else {
                    alert("Lỗi: " + data.message);
                    this.checked = !isTurnedOn; // Thất bại thì giật công tắc về lại như cũ
                }
            } catch (error) {
                console.error("Lỗi gửi lệnh điều khiển:", error);
                alert("Lỗi kết nối đến máy chủ!");
                this.checked = !isTurnedOn; 
            } finally {
                // MỞ KHÓA UI: Dù thành công hay thất bại cũng cho phép bấm lại
                this.disabled = false;
            }
        });
    });

    // Bắt đầu chu trình lấy dữ liệu
    layDanhSachField();

    // Thiết lập vòng lặp hỏi thăm Server mỗi 2 giây để đồng bộ tự động
    setInterval(syncControlStates, 2000);
});


// =====================================================================
// FILE: control.js - ĐÃ CẬP NHẬT SEARCH VÀ GIỮ NGUYÊN MODAL
// =====================================================================

document.addEventListener("DOMContentLoaded", () => {
    // --- 1. KHAI BÁO BIẾN CHO MODAL (THÊM LỊCH) ---
    const addModal = document.getElementById('addScheduleModal');
    const openBtn = document.getElementById('btnAddSchedule'); // Nút Thêm xanh lá
    const closeBtn = document.getElementById('closeScheduleModal');
    const cancelBtn = document.getElementById('cancelSchedule');
    const createBtn = document.getElementById('createSchedule');
    const nameInput = document.getElementById('schedName');
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    const valueLabel = document.getElementById('valueLabel');
    const repeatSelect = document.getElementById('schedRepeat');
    const repeatNGroup = document.getElementById('repeatNGroup');
    const repeatNLabel = document.getElementById('repeatNLabel');

    // --- 2. KHAI BÁO BIẾN CHO SEARCH ---
    const toggleSearchBtn = document.getElementById('toggleSearchBtn');
    const btnCloseSearch = document.getElementById('btnCloseSearch'); // Nút Đóng mới
    const searchInput = document.getElementById('searchInput');
    const btnColumns = document.getElementById('btnColumns');
    const btnAddSchedule = document.getElementById('btnAddSchedule'); // Nút Thêm

    // =========================================
    // PHẦN XỬ LÝ SEARCH (CẬP NHẬT CÓ NÚT ĐÓNG)
    // =========================================
    if (toggleSearchBtn && searchInput && btnCloseSearch) {
        
        // HÀNH ĐỘNG 1: MỞ SEARCH
        toggleSearchBtn.addEventListener('click', function() {
            // Hiện ô Search và nút Đóng
            searchInput.classList.remove('hidden');
            btnCloseSearch.classList.remove('hidden');

            // Ẩn 3 nút hành động để nhường chỗ
            btnAddSchedule.classList.add('icon-hide');
            toggleSearchBtn.classList.add('icon-hide');
            btnColumns.classList.add('icon-hide');

            searchInput.focus(); // Tự động đưa con trỏ chuột vào ô nhập
        });

        // HÀNH ĐỘNG 2: ĐÓNG SEARCH (Nhấn vào nút X)
        btnCloseSearch.addEventListener('click', function() {
            // Ẩn ô Search và nút Đóng
            searchInput.classList.add('hidden');
            btnCloseSearch.classList.add('hidden');

            // Hiện lại 3 nút hành động
            btnAddSchedule.classList.remove('icon-hide');
            toggleSearchBtn.classList.remove('icon-hide');
            btnColumns.classList.remove('icon-hide');

            // Xóa nội dung search và reset bảng
            searchInput.value = '';
            filterTable('');
        });

        // Lọc bảng khi gõ phím
        searchInput.addEventListener('input', function() {
            filterTable(this.value.toLowerCase().trim());
        });
    }

    // Hàm lọc bảng (Giữ nguyên)
    function filterTable(keyword) {
        const rows = document.querySelectorAll('.schedule-table tbody tr');
        rows.forEach(row => {
            const nameCell = row.querySelector('td:first-child');
            if (nameCell) {
                const nameText = nameCell.textContent.toLowerCase();
                row.style.display = nameText.includes(keyword) ? '' : 'none';
            }
        });
    }

    // =========================================
    // PHẦN XỬ LÝ MODAL (THÊM / SỬA LỊCH)
    // =========================================
    
    const modalTitle = document.getElementById('modalTitle'); // Lấy tiêu đề Modal
    let currentRowBeingEdited = null; // Biến siêu quan trọng: Lưu lại dòng đang được sửa

    // 1. MỞ MODAL THÊM MỚI (Khi nhấn nút + màu xanh)
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            currentRowBeingEdited = null; // Chắc chắn là chế độ Thêm mới
            if (modalTitle) modalTitle.innerText = "Add Schedule";
            if (createBtn) createBtn.innerText = "CREATE";
            addModal.classList.remove('hidden');
        });
    }

    // 2. XỬ LÝ SỰ KIỆN CLICK TRÊN BẢNG (SỬA & XÓA)
    const scheduleTableBody = document.querySelector('.schedule-table tbody');
    if (scheduleTableBody) {
        // Dùng Event Delegation để bắt sự kiện click cho toàn bộ bảng
        scheduleTableBody.addEventListener('click', function(e) {
            
            // ==========================================
            // A. NẾU CLICK VÀO ICON CÂY BÚT (SỬA)
            // ==========================================
            if (e.target.classList.contains('fa-pen')) {
                currentRowBeingEdited = e.target.closest('tr');

                const nameCell = currentRowBeingEdited.querySelector('td:nth-child(1) .badge').innerText;
                const repeatCellText = currentRowBeingEdited.querySelector('td:nth-child(4)').innerText.toLowerCase();

                nameInput.value = nameCell;
                
                if (repeatCellText === 'daily') repeatSelect.value = 'daily';
                else if (repeatCellText === 'weekly') repeatSelect.value = 'weekly';
                else repeatSelect.value = 'none';

                if (modalTitle) modalTitle.innerText = "Edit Schedule";
                if (createBtn) createBtn.innerText = "SAVE";

                updateCreateButton();
                addModal.classList.remove('hidden');
            }

            // ==========================================
            // B. NẾU CLICK VÀO ICON THÙNG RÁC (XÓA)
            // ==========================================
            if (e.target.classList.contains('fa-trash')) {
                // 1. Tìm cái dòng (thẻ <tr>) chứa nút thùng rác vừa bấm
                const rowToDelete = e.target.closest('tr');
                
                // 2. Lấy tên của lịch để hiện thông báo cho rõ ràng
                const scheduleName = rowToDelete.querySelector('td:nth-child(1) .badge').innerText;
                
                // 3. Hiện hộp thoại hỏi người dùng có chắc chắn không
                const isConfirmed = confirm(`Are you sure you want to delete the schedule: "${scheduleName}"?`);
                
                // 4. Nếu người dùng bấm OK
                if (isConfirmed) {
                    // Xóa dòng đó khỏi giao diện ngay lập tức
                    rowToDelete.remove();
                    
                    // Thông báo thành công (Bạn có thể bỏ dòng này đi nếu thấy phiền)
                    // alert(`Đã xóa thành công lịch: ${scheduleName}`);
                    
                    // LƯU Ý: Sau này bạn sẽ gọi API ở đây để xóa thật trong Database
                    // fetch('/api/delete_schedule', { method: 'POST', body: ... })
                }
            }
        });
    }

    // 3. ĐÓNG MODAL (Và reset mọi thứ)
    const closeModal = () => {
        addModal.classList.add('hidden');
        document.getElementById('scheduleForm').reset();
        if (repeatNGroup) repeatNGroup.classList.add('hidden');
        
        // Trả mọi thứ về mặc định (Add Mode)
        currentRowBeingEdited = null;
        if (modalTitle) modalTitle.innerText = "Add Schedule";
        if (createBtn) createBtn.innerText = "CREATE";
        
        updateCreateButton();
    };

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    // Xử lý các logic nút bấm bên trong Modal (Consumption/Duration) - GIỮ NGUYÊN
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            toggleBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const mode = this.getAttribute('data-mode');
            valueLabel.innerText = (mode === 'consumption') ? "Consumption (Liters)" : "Duration (Minutes)";
        });
    });

    if (repeatSelect) {
        repeatSelect.addEventListener('change', function() {
            if (this.value === 'every_n_days') {
                repeatNGroup.classList.remove('hidden');
                repeatNLabel.innerText = "Repeat every N days";
            } else if (this.value === 'every_n_weeks') {
                repeatNGroup.classList.remove('hidden');
                repeatNLabel.innerText = "Repeat every N weeks";
            } else {
                repeatNGroup.classList.add('hidden');
            }
        });
    }

    const updateCreateButton = () => {
        if (nameInput && nameInput.value.trim().length > 0) {
            createBtn.disabled = false;
            createBtn.classList.add('active');
        } else {
            createBtn.disabled = true;
            createBtn.classList.remove('active');
        }
    };

    if (nameInput) nameInput.addEventListener('input', updateCreateButton);

    // 4. LƯU DỮ LIỆU (Khi nhấn CREATE hoặc SAVE)
    const scheduleForm = document.getElementById('scheduleForm');
    if (scheduleForm) {
        scheduleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const newName = nameInput.value;

            if (currentRowBeingEdited) {
                // === NẾU ĐANG Ở CHẾ ĐỘ SỬA ===
                // Cập nhật lại tên trên dòng vừa sửa
                currentRowBeingEdited.querySelector('td:nth-child(1) .badge').innerText = newName;
                alert("Đã cập nhật lịch: " + newName);
            } else {
                // === NẾU ĐANG Ở CHẾ ĐỘ THÊM MỚI ===
                // Thực hiện gọi API thêm mới vào Backend
                alert("Đã tạo lịch mới: " + newName);
            }

            closeModal();
        });
    }

    // =========================================
    // LOGIC PHÂN TRANG (PAGINATION)
    // =========================================
    let currentPage = 1;
    const rowsPerPage = 10;

    function updatePagination() {
        const rows = document.querySelectorAll('.schedule-table tbody tr');
        const totalRows = rows.length;
        const totalPages = Math.ceil(totalRows / rowsPerPage) || 1;

        // Đảm bảo trang hiện tại không vượt quá tổng số trang
        if (currentPage > totalPages) currentPage = totalPages;

        // Ẩn/Hiện các dòng dựa trên trang hiện tại
        rows.forEach((row, index) => {
            const start = (currentPage - 1) * rowsPerPage;
            const end = start + rowsPerPage;
            if (index >= start && index < end) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });

        // Cập nhật text hiển thị (Ví dụ: Page 1 of 3)
        const pageInfo = document.getElementById('pageInfo');
        if (pageInfo) pageInfo.innerText = `Page ${currentPage} of ${totalPages}`;

        // Vô hiệu hóa nút nếu không còn trang để chuyển
        const prevBtn = document.getElementById('prevPage');
        const nextBtn = document.getElementById('nextPage');
        if (prevBtn) prevBtn.disabled = (currentPage === 1);
        if (nextBtn) nextBtn.disabled = (currentPage === totalPages);
    }

    // Gán sự kiện cho các nút bấm
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');

    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                updatePagination();
            }
        });
    }

    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', () => {
            const totalRows = document.querySelectorAll('.schedule-table tbody tr').length;
            if (currentPage < Math.ceil(totalRows / rowsPerPage)) {
                currentPage++;
                updatePagination();
            }
        });
    }

    // Gọi hàm lần đầu để khởi tạo bảng
    updatePagination();

    // Mẹo: Mỗi khi bạn thêm 1 hàng mới hoặc xóa 1 hàng, 
    // hãy nhớ gọi lại hàm updatePagination() để cập nhật lại số trang.
});