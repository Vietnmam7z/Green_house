let allFields = [];      
let currentPage = 1;    
const rowsPerPage = 10; 

document.addEventListener("DOMContentLoaded", () => {
    // Tải thông tin Admin
    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) { document.getElementById('userName').innerText = data.username; }
      });

    loadFields();

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', (e) => {
        e.preventDefault();
        fetch('/logout', { method: 'POST' }).then(res => res.json()).then(data => {
            if (data.success) window.location.href = '/login';
        });
    });

    // CHỨC NĂNG XỬ LÝ CHECKBOX (MỚI)
    // 1. Nút "Select All"
    document.getElementById('selectAll').addEventListener('change', function() {
        const isChecked = this.checked;
        const checkboxes = document.querySelectorAll('.field-checkbox');
        checkboxes.forEach(cb => cb.checked = isChecked);
        toggleBinIcon();
    });

    // Tạm thời ẩn 3 nút green khi chưa có code xử lý, để UI gọn
    // document.querySelector('.action-buttons').classList.add('hidden');
});

async function loadFields() {
    try {
        const response = await fetch('/api/admin/greenhouses');
        let fields = await response.json();
        
        // Sắp xếp Field ID từ nhỏ đến lớn
        fields.sort((a, b) => a.field_id.localeCompare(b.field_id, undefined, {numeric: true}));
        
        allFields = fields;
        const maxPage = Math.ceil(allFields.length / rowsPerPage) || 1;
        if (currentPage > maxPage) currentPage = maxPage;

        renderTable();
        renderPagination();
    } catch (error) {
        console.error("Lỗi lấy danh sách Field:", error);
    }
}

function renderTable() {
    const tbody = document.getElementById('fieldTableBody');
    tbody.innerHTML = '';
    
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = startIndex + rowsPerPage;
    const paginatedFields = allFields.slice(startIndex, endIndex);

    paginatedFields.forEach((field) => {
        const tr = document.createElement('tr');
        
        // Đã cập nhật để chèn cột checkbox trước
        tr.innerHTML = `
            <td><input type="checkbox" class="field-checkbox" value="${field.field_id}"></td>
            <td>${field.field_id}</td> <td>${field.plant}</td>
            <td>${field.username}</td>
        `;

        // Gắn sự kiện click checkbox con để hiện/ẩn thùng rác
        const checkbox = tr.querySelector('.field-checkbox');
        checkbox.addEventListener('change', () => toggleBinIcon());

        tbody.appendChild(tr);
    });

    // Reset nút "Select All" khi chuyển trang
    document.getElementById('selectAll').checked = false;
    toggleBinIcon();
}

// Hàm kiểm tra xem có hiện thùng rác đỏ không
function toggleBinIcon() {
    const checkedBoxes = document.querySelectorAll('.field-checkbox:checked');
    const btnBin = document.getElementById('btn-delete-selected');
    if (checkedBoxes.length > 0) {
        btnBin.classList.remove('hidden');
    } else {
        btnBin.classList.add('hidden');
    }
}

// Phân trang (Giữ nguyên)
function renderPagination() {
    const container = document.getElementById('paginationContainer');
    container.innerHTML = '';
    
    const totalPages = Math.ceil(allFields.length / rowsPerPage);
    if (totalPages <= 1) return; 

    const prevBtn = document.createElement('button');
    prevBtn.className = 'page-btn';
    prevBtn.innerHTML = '&lt;';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => { if(currentPage > 1) { currentPage--; updateView(); } };
    container.appendChild(prevBtn);

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            const btn = document.createElement('button');
            btn.className = `page-btn ${i === currentPage ? 'active' : ''}`;
            btn.innerText = i;
            btn.onclick = () => { currentPage = i; updateView(); };
            container.appendChild(btn);
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            const dots = document.createElement('span');
            dots.className = 'page-dots';
            dots.innerText = '...';
            container.appendChild(dots);
        }
    }

    const nextBtn = document.createElement('button');
    nextBtn.className = 'page-btn';
    nextBtn.innerHTML = '&gt;';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => { if(currentPage < totalPages) { currentPage++; updateView(); } };
    container.appendChild(nextBtn);
}

function updateView() {
    renderTable();
    renderPagination();
}