// ==========================================
// FILE: notifications.js (Phiên bản mới)
// QUẢN LÝ HIỂN THỊ CHUÔNG THÔNG BÁO TRÊN NAVBAR
// ==========================================

const NotificationSystem = (function() {
    let notificationsList = [];
    let currentUser = "Unknown";
    let refreshInterval = null;

    // Khởi tạo hệ thống chuông
    function init(username) {
        currentUser = username;
        fetchNotificationHistory();
        
        // Cứ 10 giây hỏi Backend 1 lần để xem có thông báo mới (chưa đọc) không
        if (refreshInterval) clearInterval(refreshInterval);
        refreshInterval = setInterval(fetchNotificationHistory, 10000);
    }

    // Tải danh sách thông báo CHƯA ĐỌC từ Backend
    async function fetchNotificationHistory() {
        if (currentUser === "Unknown") return;
        try {
            const res = await fetch(`/api/get_notifications?username=${currentUser}`);
            const data = await res.json();
            if (data.success) {
                // Chỉ lấy những cái chưa đọc để gắn lên số màu đỏ của chuông
                notificationsList = data.data.filter(n => n.is_read === 0); 
                renderBellUI();
            }
        } catch (err) { console.error("Lỗi tải thông báo cho chuông:", err); }
    }

    // Đánh dấu đã đọc ngay trên popup của chuông
    window.danhDauDaDoc = async function(ts, deviceId) {
        try {
            await fetch('/api/mark_read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ts: ts, device_id: deviceId, username: currentUser })
            });
            fetchNotificationHistory(); // Tải lại để mất số đỏ
        } catch (err) { console.error("Lỗi đánh dấu đã xem:", err); }
    };
    
    function updateConfig(newConfig) {
        console.log("Hệ thống chuông đã nhận cấu hình AI mới:", newConfig);
        // Có thể ép tải lại thông báo ngay khi AI vừa đổi cấu hình
        fetchNotificationHistory(); 
    }
    // Vẽ giao diện chuông
    function renderBellUI() {
        const bellIcon = document.querySelector('img[alt="Notifications"]');
        if (!bellIcon) return;

        let bellWrapper = bellIcon.closest('.bell-wrapper-container');
        let notifBox = document.getElementById('ai-notif-box');

        // Tạo wrapper bọc cái chuông nếu chưa có
        if (!bellWrapper) {
            bellWrapper = document.createElement('div');
            bellWrapper.className = 'bell-wrapper-container';
            bellWrapper.style.position = 'relative';
            bellWrapper.style.display = 'inline-block';
            bellIcon.parentNode.insertBefore(bellWrapper, bellIcon);
            bellWrapper.appendChild(bellIcon);
            
            // Xử lý bật/tắt popup khi click chuông
            bellWrapper.addEventListener('click', function(e) {
                if (e.target === bellWrapper || e.target === bellIcon) {
                    notifBox.style.display = notifBox.style.display === 'none' ? 'block' : 'none';
                }
            });

            // Click ra ngoài thì tắt popup
            document.addEventListener('click', function(event) {
                if (!bellWrapper.contains(event.target) && notifBox) {
                    notifBox.style.display = 'none';
                }
            });
        }
        
        // Vẽ số đỏ (Badge)
        const unreadCount = notificationsList.length;
        let badge = document.getElementById('ai-bell-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.id = 'ai-bell-badge';
            badge.style.cssText = 'position: absolute; top: -5px; right: -5px; background: red; color: white; border-radius: 50%; padding: 2px 6px; font-size: 10px; font-weight: bold; cursor: pointer;';
            bellWrapper.appendChild(badge);
        }
        badge.innerText = unreadCount;
        badge.style.display = unreadCount > 0 ? 'block' : 'none';

        // Vẽ hộp thoại chứa nội dung (Popup)
        if (!notifBox) {
            notifBox = document.createElement('div');
            notifBox.id = 'ai-notif-box';
            notifBox.style.cssText = 'position: absolute; top: 100%; right: 0; margin-top: 10px; background: white; border: 1px solid #ccc; box-shadow: 0 4px 12px rgba(0,0,0,0.15); width: 350px; max-height: 400px; overflow-y: auto; z-index: 9999; border-radius: 8px; display: none;';
            bellWrapper.appendChild(notifBox);
        }

        if (notificationsList.length === 0) {
            notifBox.innerHTML = '<div style="padding: 20px; text-align: center; color: #666; font-size: 14px;">Không có thông báo mới nào</div>';
        } else {
            notifBox.innerHTML = notificationsList.map(n => {
                const dateObj = new Date(n.ts);
                const timeStr = `${dateObj.getHours()}:${dateObj.getMinutes() < 10 ? '0':''}${dateObj.getMinutes()} - ${dateObj.getDate()}/${dateObj.getMonth()+1}`;
                const colorStatus = n.status === "CRITICAL" ? "#d32f2f" : "#f57c00";
                const bgStatus = n.status === "CRITICAL" ? "#ffebee" : "#fff3e0";
                
                const fieldName = n.field_name || "Khu vực";
                const deviceName = n.device_name || n.device_id;
                
                const msgText = n.status === "CRITICAL" 
                    ? `Nguy cấp: [${fieldName}] ${deviceName} ghi nhận chỉ số rất xấu!` 
                    : `Cảnh báo: [${fieldName}] ${deviceName} ghi nhận chỉ số bất thường.`;

                return `
                <div onclick="danhDauDaDoc(${n.ts}, '${n.device_id}')" style="cursor: pointer; border-bottom: 1px solid #eee; padding: 12px; font-size: 13px; line-height: 1.4; text-align: left; background-color: ${bgStatus};">
                    <strong style="color: ${colorStatus};">[${n.status}]</strong> ${msgText} <br>
                    <span style="color: #666; font-size: 11px; margin-top: 4px; display: inline-block;">
                        <i class="fa-regular fa-clock"></i> ${timeStr}
                    </span>
                </div>
                `;
            }).join('');
            
            // Thêm nút "Xem tất cả" dẫn sang trang Trung tâm thông báo
            notifBox.innerHTML += `
                <div style="text-align: center; padding: 10px; border-top: 1px solid #ddd; background: #f9f9f9; border-radius: 0 0 8px 8px;">
                    <a href="/notifications" style="color: #2e7d32; text-decoration: none; font-weight: bold; font-size: 13px;">
                        Đến Trung tâm thông báo <i class="fa-solid fa-arrow-right"></i>
                    </a>
                </div>
            `;
        }
    }

    return {
        init,
        refresh: fetchNotificationHistory, updateConfig // Dùng trong trường hợp muốn gọi ép tải lại từ file khác
    };
})();