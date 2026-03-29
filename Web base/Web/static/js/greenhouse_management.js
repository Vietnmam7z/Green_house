let allFields = [];      
let currentPage = 1;    
const rowsPerPage = 10; 
let isSelectAllIndeterminate = false;

document.addEventListener("DOMContentLoaded", () => {
    const btnBack = document.getElementById('btn-back');
    if (btnBack) {
        btnBack.addEventListener('click', () => {
            window.location.href = '/admin_management';
        });
    }
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

    // CHỨC NĂNG XỬ LÝ THANH TOOLBAR MỚI (UPDATE)
    // 1. Nút "Select All"
    document.getElementById('selectAll').addEventListener('click', function(e) {
        // Nếu trước đó đang có dấu trừ (-), ép nó thành rỗng!
        if (isSelectAllIndeterminate) {
            this.checked = false;
        }
        
        // Cập nhật trạng thái xuống các ô con
        const isChecked = this.checked;
        const checkboxes = document.querySelectorAll('.field-checkbox');
        checkboxes.forEach(cb => cb.checked = isChecked);
        
        updateToolbar();
    });

    // 2. Chức năng Clear icon (Deselect all)
    document.getElementById('btn-clear-icon').addEventListener('click', () => {
        const checkboxes = document.querySelectorAll('.field-checkbox');
        checkboxes.forEach(cb => cb.checked = false);
        const selectAllCheckbox = document.getElementById('selectAll');
        if (selectAllCheckbox) selectAllCheckbox.checked = false;
        updateToolbar();
    });
    
    // placeholder click handlers for add, edit, delete
    document.getElementById('btn-add-icon').addEventListener('click', () => alert('Add new field logic goes here'));
    document.getElementById('btn-edit-icon').addEventListener('click', () => alert('Edit selected field logic goes here'));
    document.getElementById('btn-delete-icon').addEventListener('click', () => alert('Delete selected field(s) logic goes here'));
    
    // Khởi tạo trạng thái ban đầu
    updateToolbar(); 
});

// Function mới để cập nhật trạng thái toolbar
// Function mới để cập nhật trạng thái toolbar
function updateToolbar() {
    const checkedBoxes = document.querySelectorAll('.field-checkbox:checked');
    const totalBoxes = document.querySelectorAll('.field-checkbox');
    const checkedCount = checkedBoxes.length;
    
    const addIcon = document.getElementById('btn-add-icon');
    const editIcon = document.getElementById('btn-edit-icon');
    const deleteIcon = document.getElementById('btn-delete-icon');
    const clearIcon = document.getElementById('btn-clear-icon');

    // Ẩn tất cả trước
    [addIcon, editIcon, deleteIcon, clearIcon].forEach(icon => icon.classList.add('hidden'));

    if (checkedCount === 0) {
        addIcon.classList.remove('hidden');
    } else if (checkedCount === 1) {
        [addIcon, editIcon, deleteIcon, clearIcon].forEach(icon => icon.classList.remove('hidden'));
    } else if (checkedCount >= 2) {
        [deleteIcon, clearIcon].forEach(icon => icon.classList.remove('hidden'));
    }
    
    // CẬP NHẬT TRẠNG THÁI CHECKBOX TỔNG: (Trống) / (Dấu trừ) / (Tích V)
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        if (checkedCount === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
            isSelectAllIndeterminate = false;
        } else if (checkedCount === totalBoxes.length && totalBoxes.length > 0) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
            isSelectAllIndeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true; // HIỆN DẤU TRỪ (-) Ở ĐÂY
            isSelectAllIndeterminate = true;
        }
    }
}

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
        checkbox.addEventListener('change', () => updateToolbar()); // Cập nhật toggleBinIcon() cũ

        tbody.appendChild(tr);
    });

    // Reset nút "Select All" khi chuyển trang
    document.getElementById('selectAll').checked = false;
    updateToolbar(); // Cập nhật toggleBinIcon() cũ
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