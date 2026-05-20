document.addEventListener("DOMContentLoaded", () => {
    // 1. Tải thông tin User
    fetch('/api/current_user').then(res => res.json()).then(data => {
        if (data.success) {
            document.getElementById('userName').innerText = data.username;
        } else {
            window.location.href = '/login';
        }
    });

    loadAllBills();

    // ==========================================
    // LOGIC POP-UP TẠO NHIỀU HÓA ĐƠN
    // ==========================================
    const modal = document.getElementById('multiBillingModal');
    const dynamicRows = document.getElementById('dynamic-bill-rows');
    const btnOpen = document.getElementById('btn-open-modal');
    const btnAddRow = document.getElementById('btn-add-row');
    const btnSubmit = document.getElementById('btn-submit-bills');

    // Hàm tạo 1 dòng nhập liệu mới
    function createRow(fieldId = '', title = '', amount = '') {
        const row = document.createElement('div');
        row.className = 'dynamic-row';
        row.innerHTML = `
            <input type="text" class="input-field-id" placeholder="VD: 001" style="flex: 1;" required value="${fieldId}">
            <input type="text" class="input-title" placeholder="Tiền điện, nước..." style="flex: 2;" required value="${title}">
            <input type="number" class="input-amount" placeholder="0 VNĐ" min="1000" style="flex: 1.5;" required value="${amount}">
            <i class="fa-solid fa-trash btn-remove-row"></i>
        `;
        // Chức năng xóa dòng
        row.querySelector('.btn-remove-row').onclick = () => row.remove();
        dynamicRows.appendChild(row);
    }

    // Mở Pop-up (Reset form và tạo sẵn 1 dòng)
    btnOpen.onclick = () => {
        dynamicRows.innerHTML = '';
        createRow(); 
        modal.classList.remove('hidden');
    };

    // Đóng Pop-up
    const closeModal = () => modal.classList.add('hidden');
    document.getElementById('closeBillingModal').onclick = closeModal;
    document.getElementById('btn-cancel-modal').onclick = closeModal;

    // Nút Thêm dòng
    btnAddRow.onclick = () => createRow();

    // Gửi dữ liệu tạo hàng loạt hóa đơn
    btnSubmit.onclick = async () => {
        const rows = document.querySelectorAll('.dynamic-row');
        if (rows.length === 0) {
            alert("Vui lòng thêm ít nhất 1 hóa đơn!");
            return;
        }

        const promises = [];
        let isValid = true;

        rows.forEach(row => {
            const fieldId = row.querySelector('.input-field-id').value.trim();
            const title = row.querySelector('.input-title').value.trim();
            const amount = parseFloat(row.querySelector('.input-amount').value);

            if (!fieldId || !title || !amount) isValid = false;

            // Đẩy từng lệnh tạo vào mảng chờ thực thi
            promises.push(
                fetch('/api/billing/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ field_id: fieldId, title: title, amount: amount })
                })
            );
        });

        if (!isValid) {
            alert("Vui lòng điền đầy đủ thông tin ở tất cả các dòng!");
            return;
        }

        btnSubmit.innerText = "Đang xử lý...";
        btnSubmit.disabled = true;

        try {
            // Thực thi toàn bộ API cùng một lúc
            await Promise.all(promises);
            alert(`Đã phát hành thành công ${rows.length} hóa đơn!`);
            closeModal();
            loadAllBills(); // Tải lại bảng ngay lập tức
        } catch (error) {
            console.error(error);
            alert("Có lỗi xảy ra trong quá trình tạo hóa đơn!");
        } finally {
            btnSubmit.innerText = "Xác nhận phát hành";
            btnSubmit.disabled = false;
        }
    };
});

// ==========================================
// LOGIC HIỂN THỊ DANH SÁCH & GOM NHÓM THEO NGÀY
// ==========================================
async function loadAllBills() {
    const container = document.getElementById('bill-list-container');
    try {
        const res = await fetch('/api/admin/all_bills');
        const result = await res.json();

        if (result.success && result.data.length > 0) {
            // Thuật toán gom nhóm hóa đơn theo ngày tạo (cắt lấy chuỗi YYYY-MM-DD)
            const groupedBills = {};
            result.data.forEach(bill => {
                const dateOnly = bill.created_at.substring(0, 10);
                if (!groupedBills[dateOnly]) groupedBills[dateOnly] = [];
                groupedBills[dateOnly].push(bill);
            });

            // Lấy danh sách các ngày và sắp xếp mới nhất lên đầu
            const sortedDates = Object.keys(groupedBills).sort((a, b) => b.localeCompare(a));

            let html = '';
            sortedDates.forEach(date => {
                const billsInDate = groupedBills[date];
                
                // Tiêu đề ngày
                html += `<div class="bill-group-date"><i class="fa-regular fa-calendar-days"></i> Ngày tạo: ${date} <span style="float: right; font-weight: normal;">${billsInDate.length} giao dịch</span></div>`;
                
                // Bảng hóa đơn của ngày đó
                html += `<table class="bill-table">
                            <thead>
                                <tr>
                                    <th>Mã Ruộng</th>
                                    <th>Dịch vụ</th>
                                    <th>Số tiền</th>
                                    <th>Trạng thái</th>
                                    <th>Ngày thanh toán</th>
                                    <th>Thao tác</th>
                                </tr>
                            </thead>
                            <tbody>`;
                
                billsInDate.forEach(b => {
                    let statusHtml = b.status === 'paid' 
                        ? `<span class="status-badge status-paid"><i class="fa-solid fa-check"></i> Đã thanh toán</span>` 
                        : `<span class="status-badge status-unpaid"><i class="fa-solid fa-clock"></i> Chưa thanh toán</span>`;
                    
                    let paidDate = b.status === 'paid' ? b.paid_at : "---";

                    html += `<tr>
                                <td><strong>${b.field_id}</strong></td>
                                <td>${b.title}</td>
                                <td><strong style="color: #4CAF50;">${b.amount.toLocaleString()} đ</strong></td>
                                <td>${statusHtml}</td>
                                <td style="color: #666; font-size: 0.9rem;">${paidDate}</td>
                                <td>
                                    <i class="fa-solid fa-trash" style="color: #e74c3c; cursor: pointer;" title="Xóa" onclick="deleteBill(${b.id})"></i>
                                </td>
                             </tr>`;
                });
                html += `</tbody></table>`;
            });

            container.innerHTML = html;
        } else {
            container.innerHTML = "<p style='text-align:center; padding: 30px; color:#888;'>Hệ thống chưa ghi nhận hóa đơn nào.</p>";
        }
    } catch (error) {
        console.error(error);
        container.innerHTML = "<p style='text-align:center; padding: 30px; color:red;'>Lỗi tải dữ liệu hóa đơn!</p>";
    }
}

// Hàm xóa hóa đơn bằng API đã có sẵn của bạn
async function deleteBill(billId) {
    if (!confirm("Bạn có chắc chắn muốn xóa hóa đơn này không?")) return;
    
    try {
        await fetch('/api/billing/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ bill_id: billId })
        });
        loadAllBills(); // Tải lại bảng sau khi xóa
    } catch (error) {
        alert("Lỗi khi xóa hóa đơn!");
    }
}