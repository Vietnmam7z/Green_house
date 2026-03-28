let allUsers = [];      // Chứa toàn bộ user lấy từ DB
let currentPage = 1;    // Trang hiện tại đang xem
const rowsPerPage = 10; // Giới hạn 10 user / 1 trang

document.addEventListener("DOMContentLoaded", () => {
    // Tải thông tin Admin
    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) { document.getElementById('userName').innerText = data.username; }
      });

    // Nút Back
    document.getElementById('btn-back').addEventListener('click', () => {
        window.location.href = '/admin_management';
    });

    // Lấy dữ liệu và khởi tạo
    loadUsers();

    // Xử lý các Popups
    const deleteModal = document.getElementById('deleteModal');
    const fieldModal = document.getElementById('fieldModal');
    const btnDeleteSelected = document.getElementById('btn-delete-selected');

    btnDeleteSelected.addEventListener('click', () => {
        const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
        document.getElementById('deleteCount').innerText = checkedBoxes.length;
        deleteModal.classList.remove('hidden');
    });

    document.getElementById('btn-cancel-delete').addEventListener('click', () => deleteModal.classList.add('hidden'));
    document.getElementById('closeFieldModal').addEventListener('click', () => fieldModal.classList.add('hidden'));
    
    window.addEventListener('click', (e) => {
        if(e.target === fieldModal) fieldModal.classList.add('hidden');
        if(e.target === deleteModal) deleteModal.classList.add('hidden');
    });

    // Xác nhận Xóa User
    document.getElementById('btn-confirm-delete').addEventListener('click', async () => {
        const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
        const userIds = Array.from(checkedBoxes).map(cb => cb.value); // Giá trị này vẫn là ID thật của DB

        const response = await fetch('/api/admin/delete_users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_ids: userIds })
        });
        
        const result = await response.json();
        if(result.success) {
            deleteModal.classList.add('hidden');
            loadUsers(); // Tải lại dữ liệu
            toggleBinIcon();
            document.getElementById('selectAll').checked = false;
        } else {
            alert("Lỗi khi xóa: " + result.message);
        }
    });

    // Xử lý nút Select All
    document.getElementById('selectAll').addEventListener('change', function() {
        const isChecked = this.checked;
        const checkboxes = document.querySelectorAll('.user-checkbox');
        checkboxes.forEach(cb => cb.checked = isChecked);
        toggleBinIcon();
    });
});

// Hàm lấy dữ liệu và khởi tạo phân trang
async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        let users = await response.json();
        
        // YÊU CẦU 1: Sắp xếp theo bảng chữ cái A-Z (theo username)
        users.sort((a, b) => a.username.localeCompare(b.username));
        
        allUsers = users;
        // Nếu trang hiện tại bị quá đà do xóa user, lùi lại 1 trang
        const maxPage = Math.ceil(allUsers.length / rowsPerPage) || 1;
        if (currentPage > maxPage) currentPage = maxPage;

        renderTable();
        renderPagination();
    } catch (error) {
        console.error("Lỗi lấy danh sách user:", error);
    }
}

// Hàm render bảng theo trang hiện tại
function renderTable() {
    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = '';
    
    // Cắt mảng lấy đúng 10 user cho trang hiện tại
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = startIndex + rowsPerPage;
    const paginatedUsers = allUsers.slice(startIndex, endIndex);

    paginatedUsers.forEach((user, index) => {
        const tr = document.createElement('tr');
        
        // YÊU CẦU 1: Gán Số Thứ Tự (STT) hiển thị dựa trên vị trí của nó trong mảng tổng
        const displayId = startIndex + index + 1; 
        const fieldsString = user.fields.length > 0 ? user.fields.join(', ') : 'None';

        tr.innerHTML = `
            <td onclick="event.stopPropagation();">
                <input type="checkbox" class="user-checkbox" value="${user.id}">
            </td>
            <td>${displayId}</td> <td style="font-weight: 500;">${user.username}</td>
            <td>${user.email}</td>
            <td style="text-align: center;">${user.fields.length}</td>
        `;

        tr.addEventListener('click', () => {
            document.getElementById('fieldListContent').innerText = fieldsString;
            document.getElementById('fieldModal').classList.remove('hidden');
        });

        const checkbox = tr.querySelector('.user-checkbox');
        checkbox.addEventListener('change', () => toggleBinIcon());

        tbody.appendChild(tr);
    });
    
    // Reset nút chọn tất cả khi chuyển trang
    document.getElementById('selectAll').checked = false;
    toggleBinIcon();
}

// YÊU CẦU 2: Hàm tạo thanh phân trang linh hoạt
function renderPagination() {
    const container = document.getElementById('paginationContainer');
    container.innerHTML = '';
    
    const totalPages = Math.ceil(allUsers.length / rowsPerPage);
    if (totalPages <= 1) return; // Nếu chỉ có 1 trang (hoặc 0) thì không hiện thanh phân trang

    // Nút < (Previous)
    const prevBtn = document.createElement('button');
    prevBtn.className = 'page-btn';
    prevBtn.innerHTML = '&lt;';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => { if(currentPage > 1) { currentPage--; updateView(); } };
    container.appendChild(prevBtn);

    // Thuật toán hiển thị số trang
    for (let i = 1; i <= totalPages; i++) {
        // Luôn hiện trang đầu, trang cuối, trang hiện tại, và 1 trang kề sát trang hiện tại
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            const btn = document.createElement('button');
            btn.className = `page-btn ${i === currentPage ? 'active' : ''}`;
            btn.innerText = i;
            btn.onclick = () => { currentPage = i; updateView(); };
            container.appendChild(btn);
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            // Hiện dấu 3 chấm
            const dots = document.createElement('span');
            dots.className = 'page-dots';
            dots.innerText = '...';
            container.appendChild(dots);
        }
    }

    // Nút > (Next)
    const nextBtn = document.createElement('button');
    nextBtn.className = 'page-btn';
    nextBtn.innerHTML = '&gt;';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => { if(currentPage < totalPages) { currentPage++; updateView(); } };
    container.appendChild(nextBtn);
}

// Cập nhật lại giao diện khi nhấn đổi trang
function updateView() {
    renderTable();
    renderPagination();
}

function toggleBinIcon() {
    const checkedBoxes = document.querySelectorAll('.user-checkbox:checked');
    const btnDelete = document.getElementById('btn-delete-selected');
    if (checkedBoxes.length > 0) {
        btnDelete.classList.remove('hidden');
    } else {
        btnDelete.classList.add('hidden');
    }
}