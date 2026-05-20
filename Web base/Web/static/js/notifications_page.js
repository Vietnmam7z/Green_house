let currentFilter = 'unread';
let allNotifications = [];
let currentUser = "";

// 1. Tải dữ liệu ban đầu và thiết lập sự kiện
document.addEventListener('DOMContentLoaded', () => {
    // Lấy thông tin user
    fetch('/api/current_user')
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                currentUser = data.username;
                loadNotifications();
            } else {
                window.location.href = '/login';
            }
        })
        .catch(err => console.error("Lỗi lấy thông tin người dùng:", err));

    // Thiết lập sự kiện lắng nghe cho nút gạt cài đặt Web/Email
    const webToggle = document.getElementById('toggle-web-status');
    if (webToggle) {
        webToggle.addEventListener('change', handleWebToggleChange);
    }
});

// 2. Chuyển đổi Tab
function setFilter(filterType) {
    currentFilter = filterType;
    document.getElementById('tab-unread').classList.toggle('active', filterType === 'unread');
    document.getElementById('tab-all').classList.toggle('active', filterType === 'all');
    renderTable();
}

// 3. Tải danh sách thông báo
async function loadNotifications() {
    try {
        const res = await fetch(`/api/get_notifications?username=${currentUser}`);
        const data = await res.json();
        if (data.success) {
            allNotifications = data.data;
            renderTable();
        }
    } catch (e) {
        console.error("Lỗi tải thông báo:", e);
        document.getElementById('notif-tbody').innerHTML = '<tr><td colspan="6" class="empty-state">Lỗi kết nối máy chủ</td></tr>';
    }
}

// 4. Vẽ bảng HTML
function renderTable() {
    const tbody = document.getElementById('notif-tbody');
    
    // Đóng nút Thùng rác tổng và bỏ chọn Check-all khi vẽ lại bảng
    document.getElementById('check-all').checked = false;
    document.getElementById('bulk-delete-btn').style.display = 'none';
    
    const filteredData = allNotifications.filter(n => {
        if (currentFilter === 'unread') return n.is_read === 0;
        return true; 
    });

    if (filteredData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Không có thông báo nào</td></tr>';
        return;
    }

    tbody.innerHTML = filteredData.map(n => {
        const dateObj = new Date(n.ts);
        const timeStr = dateObj.getFullYear() + "-" + 
                        String(dateObj.getMonth() + 1).padStart(2, '0') + "-" + 
                        String(dateObj.getDate()).padStart(2, '0') + " " +
                        String(dateObj.getHours()).padStart(2, '0') + ":" + 
                        String(dateObj.getMinutes()).padStart(2, '0') + ":" + 
                        String(dateObj.getSeconds()).padStart(2, '0');
        
        const typeClass = n.status === "CRITICAL" ? "type-critical" : "type-warning";
        const isReadClass = n.is_read === 1 ? "read-row" : "";
        
        const fieldName = n.field_name || "Khu vực";
        const deviceName = n.device_name || n.device_id;
        
        return `
        <tr class="${isReadClass}">
            <td><input type="checkbox" class="row-checkbox" data-ts="${n.ts}" data-device="${n.device_id}" onclick="handleRowCheckboxChange()"></td>
            <td>${timeStr}</td>
            <td class="${typeClass}">${n.status} ALERT</td>
            <td>Cảnh báo tại '${fieldName}'</td>
            <td>Thiết bị <b>${deviceName}</b> ghi nhận chỉ số bất thường. Vui lòng kiểm tra.</td>
            <td class="row-actions">
                ${n.is_read === 0 
                    ? `<button class="icon-btn" title="Đánh dấu đã xem" onclick="markAsRead(${n.ts}, '${n.device_id}')"><i class="fa-solid fa-check"></i></button>`
                    : ''
                }
                <button class="icon-btn trash" title="Xóa" onclick="deleteSingleNotification(this, ${n.ts}, '${n.device_id}')"><i class="fa-solid fa-trash"></i></button>
            </td>
        </tr>
        `;
    }).join('');
}

// 5. Đánh dấu 1 mục đã đọc
async function markAsRead(ts, deviceId) {
    try {
        await fetch('/api/mark_read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ts: ts, device_id: deviceId, username: currentUser })
        });
        loadNotifications();
    } catch (e) { console.error("Lỗi cập nhật đã đọc:", e); }
}

// 6. Đánh dấu tất cả đã đọc
function markAllAsRead() {
    const unreadItems = allNotifications.filter(n => n.is_read === 0);
    if(unreadItems.length === 0) return;
    
    Promise.all(unreadItems.map(n => 
        fetch('/api/mark_read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ts: n.ts, device_id: n.device_id, username: currentUser })
        })
    )).then(() => loadNotifications());
}

// ==========================================
// CÁC HÀM XỬ LÝ CHỌN VÀ XÓA (SINGLE & BULK)
// ==========================================

// Xóa 1 mục lẻ
async function deleteSingleNotification(btnElement, ts, deviceId) {
    const row = btnElement.closest('tr');
    row.style.opacity = '0.5';
    row.style.pointerEvents = 'none';

    try {
        const payload = { ts: ts, device_id: deviceId, username: currentUser };
        const res = await fetch('/api/delete_notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if (data.success) {
            row.style.transition = 'all 0.3s';
            row.style.transform = 'translateX(50px)';
            row.style.opacity = '0';
            setTimeout(() => { loadNotifications(); }, 300);
        } else {
            alert("Lỗi xóa thông báo: " + data.message);
            row.style.opacity = '1';
            row.style.pointerEvents = 'auto';
        }
    } catch (e) { 
        console.error("Lỗi xóa:", e); 
        row.style.opacity = '1'; 
        row.style.pointerEvents = 'auto';
    }
}

// Xử lý khi click vào ô Checkbox Chọn Tất Cả
function toggleSelectAll(masterCheckbox) {
    const checkboxes = document.querySelectorAll('.row-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = masterCheckbox.checked;
    });
    toggleBulkDeleteButtonVisibility();
}

// Xử lý khi click vào ô Checkbox từng dòng
function handleRowCheckboxChange() {
    const masterCheckbox = document.getElementById('check-all');
    const totalCheckboxes = document.querySelectorAll('.row-checkbox').length;
    const checkedCheckboxes = document.querySelectorAll('.row-checkbox:checked').length;
    
    masterCheckbox.checked = (totalCheckboxes === checkedCheckboxes && totalCheckboxes > 0);
    toggleBulkDeleteButtonVisibility();
}

// Hiển thị nút Thùng rác đỏ nếu có dòng được chọn
function toggleBulkDeleteButtonVisibility() {
    const checkedCount = document.querySelectorAll('.row-checkbox:checked').length;
    const bulkBtn = document.getElementById('bulk-delete-btn');
    if (checkedCount > 0) {
        bulkBtn.style.display = 'inline-block';
    } else {
        bulkBtn.style.display = 'none';
    }
}

// Nút Bấm Xóa Hàng Loạt
async function deleteSelectedNotifications() {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    if (checkedBoxes.length === 0) return;

    if (!confirm(`Bạn có chắc chắn muốn xóa ${checkedBoxes.length} thông báo đã chọn?`)) {
        return;
    }

    const itemsToDelete = [];
    checkedBoxes.forEach(cb => {
        itemsToDelete.push({
            ts: parseInt(cb.getAttribute('data-ts')),
            device_id: cb.getAttribute('data-device'),
            username: currentUser
        });
    });

    try {
        const res = await fetch('/api/delete_notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(itemsToDelete)
        });
        
        const data = await res.json();
        if (data.success) {
            loadNotifications();
        } else {
            alert("Lỗi khi xóa hàng loạt: " + data.message);
        }
    } catch (e) {
        console.error("Lỗi xóa hàng loạt:", e);
        alert("Không thể kết nối máy chủ để xóa dữ liệu.");
    }
}

// ================= QUẢN LÝ CÀI ĐẶT THÔNG BÁO =================

// Hàm xử lý logic: Web tắt -> Ép tắt Email và làm mờ
function handleWebToggleChange() {
    const webToggle = document.getElementById('toggle-web-status');
    const emailToggle = document.getElementById('toggle-email-status');

    if (!webToggle.checked) {
        // Nếu tắt Web -> Ép tắt Email và không cho click
        emailToggle.checked = false;
        emailToggle.disabled = true;
    } else {
        // Nếu bật Web -> Cho phép tương tác với nút Email
        emailToggle.disabled = false;
    }
}

// 1. Mở popup và tự động lấy trạng thái cấu hình hiện tại
async function openSettingsModal() {
    document.getElementById('settingsModal').style.display = 'flex';
    
    const webToggle = document.getElementById('toggle-web-status');
    const emailToggle = document.getElementById('toggle-email-status');
    
    // Disable nút gạt tạm thời trong lúc chờ API
    webToggle.disabled = true; 
    emailToggle.disabled = true;

    try {
        const res = await fetch(`/api/get_notification_settings?username=${currentUser}`);
        const data = await res.json();
        
        if (data.success && data.data) {
            webToggle.checked = (data.data.status === 'ON');
            emailToggle.checked = (data.data.email_status === 'ON');
        } else {
            // Mặc định ON nếu chưa có dữ liệu
            webToggle.checked = true;
            emailToggle.checked = true;
        }

        // BẢO VỆ LOGIC FRONTEND NGAY KHI VỪA LOAD LÊN
        if (!webToggle.checked) {
            emailToggle.checked = false;
        }

    } catch (e) {
        console.error("Lỗi lấy cấu hình:", e);
    } finally {
        webToggle.disabled = false; 
        // Chỉ mở khóa nút Email nếu Web đang bật
        emailToggle.disabled = !webToggle.checked; 
    }
}

// 2. Đóng popup
function closeSettingsModal() {
    document.getElementById('settingsModal').style.display = 'none';
}

// 3. Gửi lệnh Lưu về Database
async function saveNotificationSettings() {
    const webStatus = document.getElementById('toggle-web-status').checked ? 'ON' : 'OFF';
    
    // Đảm bảo an toàn: Nếu Web OFF thì Email chắc chắn OFF bất chấp Frontend bị hack/lỗi
    let emailStatus = document.getElementById('toggle-email-status').checked ? 'ON' : 'OFF';
    if (webStatus === 'OFF') {
        emailStatus = 'OFF';
    }

    try {
        const btn = document.querySelector('.btn-save');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
        btn.disabled = true;

        const [resWeb, resEmail] = await Promise.all([
            fetch('/api/set_notification_status', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: webStatus }) 
            }),
            fetch('/api/set_notification_email_status', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: emailStatus })
            })
        ]);
        
        const dataWeb = await resWeb.json();
        const dataEmail = await resEmail.json();
        
        if(dataWeb.success && dataEmail.success) {
            closeSettingsModal();
        } else {
            alert("Lỗi: Không thể lưu một trong các cấu hình. " + (dataWeb.message || dataEmail.message));
        }
    } catch (e) {
        console.error("Lỗi lưu cấu hình:", e);
        alert("Không thể kết nối máy chủ");
    } finally {
        const btn = document.querySelector('.btn-save');
        btn.innerHTML = 'Lưu cài đặt';
        btn.disabled = false;
    }
}