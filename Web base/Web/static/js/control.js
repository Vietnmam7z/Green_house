// Các biến toàn cục
let fieldsList = [];
let currentIndex = 0;
let currentFieldId = null;

// ======================================================================
// 1. HÀM ĐỒNG BỘ TRẠNG THÁI TỪ DATABASE (Đã fix sử dụng device_controller)
// ======================================================================
function syncControlStates() {
    if (!currentFieldId) return;

    // Gọi API lấy danh sách thiết bị và trạng thái thật của device_controller
    fetch(`/api/devices_list?field_id=${currentFieldId}`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.devices) {
                
                // Bản đồ Map ngược từ Type (DB) sang tên Nút bấm (UI)
                const dbToUiType = {
                    "light": "Light",
                    "vent": "Vent",
                    "valve": "Irrigation",
                    "cooling_pad": "Cooling pad",
                    "heater": "Heater",
                    "co2_valve": "CO2 valve",
                    "fan": "Fan",
                    "fertilizer": "Fertigation"
                };

                const toggles = document.querySelectorAll('.device-toggle');
                
                toggles.forEach(toggle => {
                    const uiDeviceName = toggle.getAttribute('data-device'); // Vd: 'Irrigation'
                    
                    // Tìm thiết bị trong mảng DB trả về (d[2] là cột Type)
                    const matchingDevice = data.devices.find(d => dbToUiType[d[2]] === uiDeviceName);
                    
                    if (matchingDevice) {
                        // d[3] là cột State ('ON' hoặc 'DONE')
                        const stateFromDB = matchingDevice[3];
                        const isChecked = (stateFromDB === 'ON');
                        
                        // Nếu trạng thái DB khác với giao diện -> Cập nhật lại giao diện
                        if (toggle.checked !== isChecked) {
                            toggle.checked = isChecked;
                        }
                    } else {
                        // [QUAN TRỌNG]: Nếu không tìm thấy thiết bị đang ON ở ruộng này, ép công tắc về OFF
                        if (toggle.checked === true) {
                            toggle.checked = false;
                        }
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
    // PHẦN XỬ LÝ MODAL VÀ KẾT NỐI API SCHEDULER
    // =========================================
    
    const modalTitle = document.getElementById('modalTitle');
    let currentRowBeingEdited = null; 
    let currentSchedulerId = null; 
    let currentDevices = []; // Biến mới: Lưu danh sách thiết bị của ruộng

    // [MỚI] 1A. HÀM TẢI DANH SÁCH THIẾT BỊ TỪ DATABASE
    function loadDevicesFromServer() {
        if (!currentFieldId) return;
        fetch(`/api/devices_list?field_id=${currentFieldId}`)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.devices) {
                    // Chuyển mảng array thành object cho dễ thao tác (d[0]=id, d[1]=name, d[2]=type)
                    currentDevices = data.devices.map(d => ({
                        id: d[0],
                        name: d[1],
                        type: d[2]
                    }));
                }
            })
            .catch(err => console.error("Lỗi tải danh sách thiết bị:", err));
    }

    // [MỚI] 1B. HÀM CẬP NHẬT DROPDOWN THIẾT BỊ THEO CHẾ ĐỘ (DUR/CONS)
    function populateDeviceDropdown(mode) {
        const deviceSelect = document.getElementById('schedDevice');
        if (!deviceSelect) return;
        deviceSelect.innerHTML = ''; // Xóa sạch danh sách cũ
        
        let hasValidDevice = false;

        currentDevices.forEach(device => {
            // LOGIC CỐT LÕI: Nếu là Consumption, CHỈ cho phép 'valve' và 'fertilizer'
            if (mode === 'consumption' && device.type !== 'valve' && device.type !== 'fertilizer') {
                return; // Bỏ qua thiết bị này
            }
            
            const option = document.createElement('option');
            option.value = device.id;
            option.dataset.type = device.type; // Lưu type ngầm để nhét vào API
            option.textContent = device.name;
            deviceSelect.appendChild(option);
            hasValidDevice = true;
        });

        if (!hasValidDevice) {
            const option = document.createElement('option');
            option.value = "";
            option.textContent = "Không có thiết bị hỗ trợ chế độ này";
            deviceSelect.appendChild(option);
        }
    }

    // 1C. HÀM TẢI DỮ LIỆU LỊCH TỪ DATABASE VÀ RENDER BẢNG
    function loadSchedulesFromServer() {
        if (!currentFieldId) return;
        fetch(`/api/get_schedulers?field_id=${currentFieldId}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const tbody = document.querySelector('.schedule-table tbody');
                    tbody.innerHTML = ''; 

                    data.data.forEach(sched => {
                        let valDisplay = '<span class="badge badge-empty">-</span>';
                        let durDisplay = '<span class="badge badge-empty">-</span>';
                        if (sched.mode === 'consumption') {
                            valDisplay = `<span class="badge badge-duration">${sched.consumption} L</span>`;
                        } else {
                            durDisplay = `<span class="badge badge-duration">${sched.duration} min</span>`;
                        }

                        let repeatDisplay = sched.type_repeat;
                        
                        // Tự động viết hoa chữ cái đầu tiên
                        if (repeatDisplay && typeof repeatDisplay === 'string') {
                            repeatDisplay = repeatDisplay.charAt(0).toUpperCase() + repeatDisplay.slice(1);
                        }

                        if (sched.type_repeat === 'every_n_days') repeatDisplay = `Every ${sched.repeat_value} days`;
                        if (sched.type_repeat === 'every_n_weeks') repeatDisplay = `Every ${sched.repeat_value} weeks`;
                        if (!sched.repeat_enabled || sched.type_repeat === 'none') repeatDisplay = '—';

                        // CHỈ GIỮ LẠI ĐÚNG 1 KHỐI NÀY
                        const tr = document.createElement('tr');
                        tr.setAttribute('data-id', sched.scheduler_id); 
                        tr.setAttribute('data-full', JSON.stringify(sched)); 

                        tr.innerHTML = `
                            <td><span class="badge badge-name">${sched.name}</span></td>
                            <td>${sched.device_name || '—'}</td> 
                            <td>${sched.event_date || '—'}</td>
                            <td><span class="badge badge-time">${(sched.event_time || '').substring(0,5)}</span></td>
                            <td>${repeatDisplay}</td>
                            <td>${sched.end_date || '—'}</td>
                            <td>${durDisplay}</td>
                            <td>${valDisplay}</td>
                            <td class="action-cells">
                                <i class="fa-solid fa-pen action-icon-btn" title="Edit"></i>
                                <i class="fa-solid fa-trash action-icon-btn" title="Delete"></i>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                    updatePagination();
                }
            });
    }

    // Tự động load thiết bị & lịch khi chuyển ruộng
    const originalCapNhatHienThiField = capNhatHienThiField;
    capNhatHienThiField = function() {
        originalCapNhatHienThiField();
        loadDevicesFromServer(); // Tải lại 8 thiết bị của ruộng này
        loadSchedulesFromServer(); 
    };

    // 2. MỞ MODAL THÊM MỚI
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            currentRowBeingEdited = null;
            currentSchedulerId = null;
            if (modalTitle) modalTitle.innerText = "Add Schedule";
            if (createBtn) createBtn.innerText = "CREATE";
            
            // Render dropdown thiết bị tùy theo nút Toggle đang active
            const currentMode = document.querySelector('.toggle-btn.active').getAttribute('data-mode');
            populateDeviceDropdown(currentMode);

            addModal.classList.remove('hidden');
        });
    }

    // 3. XỬ LÝ CLICK TRÊN BẢNG (SỬA & XÓA)
    const scheduleTableBody = document.querySelector('.schedule-table tbody');
    if (scheduleTableBody) {
        scheduleTableBody.addEventListener('click', function(e) {
            const tr = e.target.closest('tr');
            if (!tr) return;
            const schedData = JSON.parse(tr.getAttribute('data-full'));

            // === A. NHẤN NÚT SỬA ===
            if (e.target.classList.contains('fa-pen')) {
                currentRowBeingEdited = tr;
                currentSchedulerId = schedData.scheduler_id;

                nameInput.value = schedData.name;
                document.getElementById('schedStartDay').value = schedData.event_date;
                document.getElementById('schedEndDay').value = schedData.end_date || "";
                document.getElementById('schedStartTime').value = (schedData.event_time || "").substring(0,5);
                
                const targetMode = schedData.mode === 'consumption' ? 'consumption' : 'duration';
                toggleBtns.forEach(b => {
                    b.classList.remove('active');
                    if(b.getAttribute('data-mode') === targetMode) b.classList.add('active');
                });
                valueLabel.innerText = targetMode === 'consumption' ? "Consumption (Liters)" : "Duration (Minutes)";
                document.getElementById('schedValue').value = targetMode === 'consumption' ? schedData.consumption : schedData.duration;

                if(schedData.repeat_enabled && schedData.type_repeat !== 'none') {
                    repeatSelect.value = schedData.type_repeat;
                    if (endDayGroup) endDayGroup.classList.remove('hidden'); // Hiện End Day

                    if(schedData.type_repeat.includes('every_n')) {
                        repeatNGroup.classList.remove('hidden');
                        document.getElementById('schedRepeatN').value = schedData.repeat_value;
                        repeatNLabel.innerText = schedData.type_repeat === 'every_n_days' ? "Repeat every N days" : "Repeat every N weeks";
                    } else {
                        repeatNGroup.classList.add('hidden');
                    }
                } else {
                    repeatSelect.value = 'none';
                    repeatNGroup.classList.add('hidden');
                    if (endDayGroup) endDayGroup.classList.add('hidden'); // Ẩn End Day
                }

                // Tái tạo lại danh sách thiết bị và chọn thiết bị cũ
                populateDeviceDropdown(targetMode);
                setTimeout(() => {
                    document.getElementById('schedDevice').value = schedData.device_id;
                }, 50);

                if (modalTitle) modalTitle.innerText = "Edit Schedule";
                if (createBtn) createBtn.innerText = "SAVE";

                updateCreateButton();
                addModal.classList.remove('hidden');
            }

            // === B. NHẤN NÚT XÓA ===
            if (e.target.classList.contains('fa-trash')) {
                if (confirm(`Bạn có chắc chắn muốn xóa lịch: "${schedData.name}"?`)) {
                    
                    // ĐÃ SỬA LẠI THÀNH delete_scheduler (thêm chữ r)
                    fetch('/api/delete_scheduler', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ scheduler_id: schedData.scheduler_id })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if(data.success) {
                            loadSchedulesFromServer(); // Tải lại bảng nếu xóa thành công
                        } else {
                            alert("Lỗi khi xóa: " + data.message);
                        }
                    })
                    .catch(err => {
                        console.error("Lỗi xóa lịch:", err);
                        alert("Không thể kết nối đến server để xóa.");
                    });
                }
            }
        });
    }

    // Toggle Buttons (Consumption/Duration) - TÍCH HỢP BỘ LỌC THIẾT BỊ
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            toggleBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const mode = this.getAttribute('data-mode');
            valueLabel.innerText = (mode === 'consumption') ? "Consumption (Liters)" : "Duration (Minutes)";
            
            // Gọi hàm lọc lại danh sách thiết bị ngay khi bấm nút
            populateDeviceDropdown(mode);
        });
    });

    // 4. LƯU DỮ LIỆU (CREATE / UPDATE VIA API)
    const scheduleForm = document.getElementById('scheduleForm');

    if (scheduleForm) {
        scheduleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const deviceSelect = document.getElementById('schedDevice');
            const selectedOption = deviceSelect.options[deviceSelect.selectedIndex];
            
            if (!selectedOption || !selectedOption.value) {
                alert("Vui lòng chọn thiết bị hợp lệ!");
                return;
            }

            createBtn.disabled = true;
            createBtn.innerText = "Processing...";

            // ==============================================================
            // BỘ KIỂM TRA AN TOÀN DỮ LIỆU (ĐẶT ĐÚNG VỊ TRÍ)
            // ==============================================================
            const startDay = document.getElementById('schedStartDay').value;
            const startTime = document.getElementById('schedStartTime').value;
            const endDay = document.getElementById('schedEndDay').value;
            const schedValue = parseFloat(document.getElementById('schedValue').value || 0);

            // Hàm phụ để reset lại nút nếu có lỗi
            function resetButtonState() {
                createBtn.disabled = false;
                createBtn.innerText = currentRowBeingEdited ? "SAVE" : "CREATE";
            }

            // 1. Kiểm tra bắt buộc nhập Start day
            if (!startDay) {
                alert("Lỗi: Vui lòng chọn Ngày bắt đầu (Start day)!");
                resetButtonState();
                return;
            }

            // 2. Kiểm tra bắt buộc nhập Start time
            if (!startTime) {
                alert("Lỗi: Vui lòng chọn Giờ bắt đầu (Start time)!");
                resetButtonState();
                return;
            }

            // 3. Kiểm tra không được nhập số âm
            if (schedValue < 0) {
                alert("Lỗi: Giá trị không được là số âm!");
                resetButtonState();
                return;
            }

            // 4. Kiểm tra Ngày kết thúc phải sau Ngày bắt đầu
            if (endDay && startDay && new Date(endDay) < new Date(startDay)) {
                alert("Lỗi: Ngày kết thúc không được nhỏ hơn ngày bắt đầu!");
                resetButtonState();
                return;
            }
            // ==============================================================

            const mode = document.querySelector('.toggle-btn.active').getAttribute('data-mode');
            const repeatVal = repeatSelect.value;
            
            const dbMode = mode === 'duration' ? 'time' : 'consumption';

            const payload = {
                field_id: currentFieldId,
                device_id: parseInt(selectedOption.value),       
                event_type: selectedOption.dataset.type,         
                name: nameInput.value,
                event_date: document.getElementById('schedStartDay').value,
                end_date: document.getElementById('schedEndDay').value,
                event_time: document.getElementById('schedStartTime').value + ":00", 
                mode: dbMode, 
                duration: mode === 'duration' ? parseInt(document.getElementById('schedValue').value || 0) : 0,
                consumption: mode === 'consumption' ? parseFloat(document.getElementById('schedValue').value || 0) : 0,
                repeat_enabled: repeatVal !== 'none',
                type_repeat: repeatVal !== 'none' ? repeatVal : null,
                repeat_value: repeatVal.includes('every_n') ? parseInt(document.getElementById('schedRepeatN').value || 1) : null
            };

            const apiUrl = currentRowBeingEdited ? '/api/update_scheduler' : '/api/create_scheduler';
            if (currentRowBeingEdited) payload.scheduler_id = currentSchedulerId;

            fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    loadSchedulesFromServer();
                    closeModal();
                } else {
                    alert("Lỗi: " + data.message);
                    createBtn.disabled = false;
                    createBtn.innerText = currentRowBeingEdited ? "SAVE" : "CREATE";
                }
            })
            .catch(err => {
                console.error(err);
                createBtn.disabled = false;
                createBtn.innerText = currentRowBeingEdited ? "SAVE" : "CREATE";
            });
        });
    }

    // Đóng Modal (Đã cập nhật ẩn End Day)
    const closeModal = () => {
        addModal.classList.add('hidden');
        document.getElementById('scheduleForm').reset();
        if (repeatNGroup) repeatNGroup.classList.add('hidden');
        if (endDayGroup) endDayGroup.classList.add('hidden'); // Reset ẩn End Day
        currentRowBeingEdited = null;
        currentSchedulerId = null;
        if (modalTitle) modalTitle.innerText = "Add Schedule";
        if (createBtn) createBtn.innerText = "CREATE";
        updateCreateButton();
    };

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    // Cập nhật trạng thái nút Create (Giữ nguyên)
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
    
    const endDayGroup = document.getElementById('endDayGroup'); // Khai báo thêm biến này

    // Repeat Select Dropdown (Đã cập nhật logic ẩn/hiện End Day)
    if (repeatSelect) {
        repeatSelect.addEventListener('change', function() {
            // 1. Xử lý hiện/ẩn cấu hình lặp N ngày/tuần
            if (this.value === 'every_n_days') {
                repeatNGroup.classList.remove('hidden');
                repeatNLabel.innerText = "Repeat every N days";
            } else if (this.value === 'every_n_weeks') {
                repeatNGroup.classList.remove('hidden');
                repeatNLabel.innerText = "Repeat every N weeks";
            } else {
                repeatNGroup.classList.add('hidden');
            }

            // 2. Xử lý hiện/ẩn End Day
            if (this.value === 'none') {
                if (endDayGroup) endDayGroup.classList.add('hidden');
                document.getElementById('schedEndDay').value = ""; // Xóa dữ liệu rác nếu ẩn
            } else {
                if (endDayGroup) endDayGroup.classList.remove('hidden');
            }
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