// static/js/profile.js
document.addEventListener('DOMContentLoaded', async () => {
    
    // --- LOGIC CHUYỂN TAB ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Xóa class active ở tất cả
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Thêm class active cho tab được bấm
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // 1. Lấy thông tin user (Đã khôi phục lại để đổ vào Tab Thông tin tài khoản)
    const userRes = await fetch('/api/current_user');
    const userData = await userRes.json();
    if (userData.success) {
        document.getElementById('prof-username').innerText = userData.username;
        
        let displayRole = userData.role;
        if (displayRole === 'admin') displayRole = 'administrator';
        document.getElementById('prof-role').innerText = displayRole;
    } else {
        window.location.href = '/login';
        return;
    }

    // 2. Lấy danh sách hóa đơn
    loadBills();
});

async function loadBills() {
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
        // TẠO GIAO DIỆN HÓA ĐƠN
        container.innerHTML = result.data.map(bill => {
            total += bill[3]; // bill[3] là amount
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
        
        // Gán sự kiện cho nút Thanh Toán
        document.getElementById('pay-momo-btn').onclick = () => createPayment(fields[0].field_id, total);
    } else {
        container.innerHTML = "<p style='text-align:center; color:#777; padding:20px;'>Bạn không có hóa đơn nào cần thanh toán.</p>";
        document.getElementById('payment-box').style.display = 'none';
    }
}

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
        window.open(data.payUrl, "_blank"); // Mở trang MoMo
        startPolling(data.order_id); // Kiểm tra trạng thái
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

        // Kiểm tra cột Status trong DB
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