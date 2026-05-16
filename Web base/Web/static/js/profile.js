// static/js/profile.js
document.addEventListener('DOMContentLoaded', async () => {
    
    // --- LOGIC CHUYỂN TAB ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // --- LẤY THÔNG TIN USER VÀ PHÂN QUYỀN HIỂN THỊ TAB ---
    const userRes = await fetch('/api/current_user');
    const userData = await userRes.json();
    let isAdmin = false;

    if (userData.success) {
        document.getElementById('prof-email').innerText = userData.email;
        document.getElementById('prof-username').innerText = userData.username;
        let displayRole = userData.role;
        if (displayRole === 'admin') displayRole = 'administrator';
        document.getElementById('prof-role').innerText = displayRole;
        
        // Kiểm tra xem có phải là Admin không
        isAdmin = (userData.role === 'admin' || userData.role === 'administrator');

        // Lấy các nút Tab cần phân quyền
        const tabBilling = document.getElementById('tab-btn-billing');
        const tabHistory = document.getElementById('tab-btn-history');
        const tabService = document.getElementById('tab-btn-service');

        if (isAdmin) {
            // ADMIN: Ẩn 3 tab của user đi
            if (tabBilling) tabBilling.style.display = 'none';
            if (tabHistory) tabHistory.style.display = 'none';
            if (tabService) tabService.style.display = 'none';
        } else {
            // USER: Hiện lại bình thường
            if (tabBilling) tabBilling.style.display = 'block';
            if (tabHistory) tabHistory.style.display = 'block';
            if (tabService) tabService.style.display = 'block';
        }

    } else {
        window.location.href = '/login';
        return;
    }

    // --- CHỈ GỌI API TẢI DỮ LIỆU NẾU LÀ USER THƯỜNG ---
    // (Admin sẽ không tải data thừa để tối ưu hiệu suất)
    if (!isAdmin) {
        loadBills();
        loadHistory(); 
    }

    // --- TỰ ĐỘNG NHẢY TAB NẾU CÓ PARAM TRÊN URL ---
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab'); 
    
    if (tabParam) {
        const targetTabId = 'tab-' + tabParam; 
        const targetBtn = document.querySelector(`.tab-btn[data-tab="${targetTabId}"]`);
        
        // Kiểm tra nút Tab đó có tồn tại và không bị ẩn (đề phòng admin cố tình sửa URL)
        if (targetBtn && targetBtn.style.display !== 'none') {
            targetBtn.click();
        }
    }
});

async function loadBills() {
    // ... [GIỮ NGUYÊN HOÀN TOÀN LOGIC HÓA ĐƠN CỦA BẠN NHƯ CŨ] ...
    const res = await fetch('/api/fields'); 
    const fields = await res.json();
    const container = document.getElementById('billing-list');

    if (fields.length === 0) {
        container.innerHTML = "<p style='text-align:center; color:#777; padding:20px;'>Bạn hiện không quản lý khu vực nào.</p>";
        return;
    }

    const billRes = await fetch('/api/billing/unpaid', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ field_id: fields[0].field_id })
    });
    const result = await billRes.json();

    let total = 0;
    if (result.success && result.data.length > 0) {
        container.innerHTML = result.data.map(bill => {
            total += bill[3]; 
            return `
                <div class="bill-item">
                    <div class="bill-info">
                        <i class="fa-solid fa-receipt bill-icon"></i>
                        <div>
                            <div class="bill-title">${bill[2]}</div>
                            <div class="bill-date">Ngày tạo: ${bill[5]}</div>
                        </div>
                    </div>
                    <div class="bill-amount">${bill[3].toLocaleString()} đ</div>
                </div>`;
        }).join('');
        document.getElementById('total-amount').innerText = total.toLocaleString();
        document.getElementById('payment-box').style.display = 'flex';
        document.getElementById('pay-momo-btn').onclick = () => createPayment(fields[0].field_id, total);
    } else {
        container.innerHTML = "<p style='text-align:center; color:#777; padding:20px;'>Bạn không có hóa đơn nào cần thanh toán.</p>";
        document.getElementById('payment-box').style.display = 'none';
    }

    loadServicePlans(fields[0].field_id);
}

// ============================================================
// HÀM MỚI: TẢI DANH SÁCH LỊCH SỬ THANH TOÁN TỔNG QUAN
// ============================================================
async function loadHistory() {
    const container = document.getElementById('history-list');
    try {
        // Gọi Endpoint GET đã khai báo trong route.py
        const res = await fetch('/api/payment/history', { method: 'GET' }); 
        const result = await res.json();
        
        console.log("Dữ liệu lịch sử:", result.data); // Để bạn F12 kiểm tra cấu trúc mảng nếu bị lệch

        if (result.success && result.data.length > 0) {
            container.innerHTML = result.data.map(tx => {
                // Thứ tự cột theo userdata.db: (0)id, (1)user_id, (2)field_id, (3)order_id, (4)request_id, (5)amount, (6)status, (7)raw_response, (8)created_at, (9)updated_at, (10)paid_at
                let id = tx[0];
                let fieldId = tx[2];
                let orderId = tx[3];
                let amount = tx[5];
                let status = tx[6];
                let date = tx[8];

                let statusColor = status === 'success' ? '#2e7d32' : (status === 'pending' ? '#f57c00' : '#d32f2f');
                let statusText = status.toUpperCase();
                let iconBg = status === 'success' ? '#e8f5e9' : (status === 'pending' ? '#fff3e0' : '#ffebee');
                let iconClass = status === 'success' ? 'fa-check' : (status === 'pending' ? 'fa-clock' : 'fa-xmark');

                return `
                    <div class="history-item" data-id="${id}">
                        <div class="history-header" onclick="toggleDetails(this, ${id})">
                            <div class="history-info">
                                <div class="history-icon" style="background: ${iconBg}; color: ${statusColor};">
                                    <i class="fa-solid ${iconClass}"></i>
                                </div>
                                <div>
                                    <div class="history-title">Mã đơn: ${orderId}</div>
                                    <div class="history-date">Ruộng: <strong>${fieldId}</strong> | ${date}</div>
                                </div>
                            </div>
                            <div style="text-align: right; display: flex; align-items: center; gap: 15px;">
                                <div>
                                    <div class="history-amount" style="color: ${statusColor};">${parseInt(amount).toLocaleString()} đ</div>
                                    <span class="history-status" style="color: ${statusColor};">${statusText}</span>
                                </div>
                                <i class="fa-solid fa-chevron-down expand-icon"></i>
                            </div>
                        </div>
                        
                        <div class="history-details" id="details-${id}">
                            <div style="text-align: center; color: #999; padding: 10px;">
                                <i class="fa-solid fa-spinner fa-spin"></i> Đang tải chi tiết...
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = "<p style='text-align:center; color:#777; padding:20px;'>Bạn chưa có giao dịch nào.</p>";
        }
    } catch (err) {
        console.error(err);
        container.innerHTML = "<p style='text-align:center; color:red; padding:20px;'>Lỗi kết nối khi tải lịch sử.</p>";
    }
}

// ============================================================
// HÀM MỚI: SỰ KIỆN CLICK MỞ THẺ ACCORDION ĐỂ XEM CHI TIẾT
// ============================================================
async function toggleDetails(headerElement, transactionId) {
    const item = headerElement.parentElement;
    const detailsDiv = document.getElementById(`details-${transactionId}`);
    
    // Đảo trạng thái class 'active' và 'open' để tạo hiệu ứng xổ xuống
    const isOpen = item.classList.contains('active');
    
    if (isOpen) {
        item.classList.remove('active');
        detailsDiv.classList.remove('open');
    } else {
        item.classList.add('active');
        detailsDiv.classList.add('open');
        
        // KIỂM TRA: Nếu chưa tải dữ liệu chi tiết lần nào thì mới fetch
        if (!detailsDiv.dataset.loaded) {
            try {
                // Gọi POST /api/payment/items theo như route.py
                const res = await fetch('/api/payment/items', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ transaction_id: transactionId })
                });
                const result = await res.json();
                
                if (result.success && result.data.length > 0) {
                    // Đổ dữ liệu chi tiết vào thẻ div. 
                    // Database user_payment_transaction_items có cột: (0)id, (1)trans_id, (2)title, (3)amount
                    detailsDiv.innerHTML = result.data.map(row => `
                        <div class="detail-row">
                            <span><i class="fa-solid fa-circle-dot" style="color:#ccc; font-size:8px; margin-right:8px; position:relative; top:-2px;"></i> ${row[2]}</span>
                            <span>${parseInt(row[3]).toLocaleString()} đ</span>
                        </div>
                    `).join('');
                    
                    detailsDiv.dataset.loaded = "true"; // Đánh dấu đã tải
                } else {
                    detailsDiv.innerHTML = '<div style="text-align:center; color:#999; padding:10px;">Giao dịch này không có chi tiết cụ thể.</div>';
                }
            } catch (error) {
                detailsDiv.innerHTML = '<div style="text-align:center; color:red; padding:10px;">Lỗi tải dữ liệu chi tiết.</div>';
            }
        }
    }
}

// ... [GIỮ NGUYÊN HÀM createPayment() VÀ startPolling() Ở DƯỚI NHƯ CŨ] ...
async function createPayment(fieldId, amount) {
    const statusDiv = document.getElementById('status');
    statusDiv.style.display = "block";
    statusDiv.style.background = "#e3f2fd";
    statusDiv.style.color = "#1976d2";
    statusDiv.style.border = "1px solid #90caf9";
    statusDiv.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang khởi tạo thanh toán...`;

    const res = await fetch('/api/payment/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ field_id: fieldId, amount: amount })
    });
    const data = await res.json();

    if (data.success) {
        window.open(data.payUrl, "_blank"); 
        startPolling(data.order_id); 
    } else {
        statusDiv.style.background = "#ffebee";
        statusDiv.style.color = "#c62828";
        statusDiv.style.border = "1px solid #ef9a9a";
        statusDiv.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Lỗi: ` + data.message;
    }
}

function startPolling(orderId) {
    const statusDiv = document.getElementById('status');
    statusDiv.innerHTML = `<i class="fa-solid fa-qrcode"></i> Vui lòng hoàn tất thanh toán trên ứng dụng MoMo...`;

    const interval = setInterval(async () => {
        const res = await fetch('/api/payment/status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ order_id: orderId })
        });
        const result = await res.json();

        if (result.success && result.data[6] === 'success') {
            statusDiv.style.background = "#e8f5e9";
            statusDiv.style.color = "#2e7d32";
            statusDiv.style.border = "1px solid #a5d6a7";
            statusDiv.innerHTML = `<i class="fa-solid fa-circle-check"></i> Thanh toán thành công! Hệ thống đang cập nhật...`;
            clearInterval(interval);
            setTimeout(() => location.reload(), 2000);
            
        } else if (result.success && (result.data[6] === 'failed' || result.data[6] === 'error')) {
            statusDiv.style.background = "#ffebee";
            statusDiv.style.color = "#c62828";
            statusDiv.style.border = "1px solid #ef9a9a";
            statusDiv.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> Giao dịch thất bại hoặc bị hủy.`;
            clearInterval(interval);
        }
    }, 3000);
}

// ============================================================
// HÀM MỚI: TẢI THÔNG TIN CÁC GÓI ĐANG THUÊ CỦA RUỘNG
// ============================================================
async function loadServicePlans(fieldId) {
    const container = document.getElementById('service-plan-list');
    try {
        const res = await fetch('/api/service_plan/list', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ field_id: fieldId })
        });
        const result = await res.json();

        if (result.success && result.data.length > 0) {
            container.innerHTML = result.data.map(plan => {
                // Xác định trạng thái để hiển thị màu sắc huy hiệu (badge)
                let isActive = plan.status === 'active';
                let statusBadgeColor = isActive ? '#2e7d32' : '#7f8c8d';
                let statusBadgeBg = isActive ? '#e8f5e9' : '#f5f5f5';
                let statusText = isActive ? 'ĐANG KÍCH HOẠT' : 'ĐÃ HẾT HẠN';

                return `
                    <div class="bill-item" style="border-left: 5px solid ${statusBadgeColor}; flex-direction: column; align-items: flex-start; gap: 10px;">
                        <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                            <span style="font-weight: 700; font-size: 1.15rem; color: #2c3e50;">
                                <i class="fa-solid fa-cubes" style="color: #3498db; margin-right: 8px;"></i> Gói thuê Ruộng ${plan.field_id}
                            </span>
                            <span style="padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; background: ${statusBadgeBg}; color: ${statusBadgeColor};">
                                ${statusText}
                            </span>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; width: 100%; font-size: 0.95rem; color: #555; padding-left: 25px;">
                            <div><i class="fa-regular fa-calendar-play"></i> Ngày bắt đầu: <strong>${plan.start_date}</strong></div>
                            <div><i class="fa-solid fa-money-bill-wave"></i> Đơn giá hằng ngày: <strong>${plan.daily_price.toLocaleString()} đ/ngày</strong></div>
                            <div><i class="fa-regular fa-calendar-xmark"></i> Ngày hết hạn: <strong>${plan.expired_date}</strong> (${plan.service_days} ngày)</div>
                            <div><i class="fa-solid fa-calculator"></i> Phí tích lũy hiện tại: <strong style="color: #e74c3c;">${plan.accumulated_amount.toLocaleString()} đ</strong></div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = "<p style='text-align:center; color:#777; padding:20px;'>Ruộng này chưa được thiết lập gói dịch vụ thuê nào.</p>";
        }
    } catch (err) {
        console.error(err);
        container.innerHTML = "<p style='text-align:center; color:red; padding:20px;'>Lỗi hệ thống khi tải thông tin gói dịch vụ.</p>";
    }
}

// ============================================================
// HÀM XỬ LÝ ĐỔI MẬT KHẨU
// ============================================================
document.getElementById('btn-change-password').addEventListener('click', async () => {
    const oldPw = document.getElementById('old-password').value;
    const newPw = document.getElementById('new-password').value;
    const confirmPw = document.getElementById('confirm-password').value;
    const pwStatus = document.getElementById('pw-status');

    pwStatus.style.display = 'block';

    // Validate form
    if (!oldPw || !newPw || !confirmPw) {
        pwStatus.innerHTML = '<span style="color: #e74c3c;">Vui lòng điền đầy đủ thông tin!</span>';
        return;
    }

    if (newPw !== confirmPw) {
        pwStatus.innerHTML = '<span style="color: #e74c3c;">Mật khẩu mới không khớp!</span>';
        return;
    }

    if (newPw.length < 6) {
        pwStatus.innerHTML = '<span style="color: #e74c3c;">Mật khẩu mới phải từ 6 ký tự trở lên!</span>';
        return;
    }

    pwStatus.innerHTML = '<span style="color: #3498db;"><i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý...</span>';

    try {
        const res = await fetch('/api/user/change_password', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ old_password: oldPw, new_password: newPw })
        });
        const data = await res.json();

        if (data.success) {
            pwStatus.innerHTML = '<span style="color: #2e7d32;"><i class="fa-solid fa-circle-check"></i> Đổi mật khẩu thành công!</span>';
            // Xóa rỗng các ô nhập liệu
            document.getElementById('old-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
            
            // Tự ẩn thông báo sau 3 giây
            setTimeout(() => { pwStatus.style.display = 'none'; }, 3000);
        } else {
            pwStatus.innerHTML = `<span style="color: #e74c3c;"><i class="fa-solid fa-triangle-exclamation"></i> ${data.message}</span>`;
        }
    } catch (err) {
        pwStatus.innerHTML = '<span style="color: #e74c3c;">Lỗi kết nối máy chủ!</span>';
    }
});