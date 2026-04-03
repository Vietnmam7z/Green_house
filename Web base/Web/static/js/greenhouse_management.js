let allFields = [];      
let currentPage = 1;    
const rowsPerPage = 8; 
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

    // 2. Chức năng Clear icon (Dọn dẹp dữ liệu Plant và Username)
    document.getElementById('btn-clear-icon').addEventListener('click', async () => {
        const checkedBoxes = document.querySelectorAll('.field-checkbox:checked');
        const fieldIds = Array.from(checkedBoxes).map(cb => cb.value);

        if (fieldIds.length === 0) return;

        // Bật hộp thoại xác nhận trước khi xóa dữ liệu
        const confirmMsg = `Bạn có chắc chắn muốn dọn dẹp dữ liệu Plant và Username của ${fieldIds.length} ruộng đã chọn?\n(Field ID vẫn sẽ được giữ lại)`;
        if (!confirm(confirmMsg)) {
            return; // Nếu bấm Hủy (Cancel) thì dừng lại
        }

        // Gọi API lên Backend
        try {
            const response = await fetch('/api/admin/clear_fields', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field_ids: fieldIds })
            });
            const result = await response.json();
            
            if (result.success) {
                // Thành công thì tải lại bảng
                loadFields(); 
                // loadFields() sẽ tự động gọi renderTable() và updateToolbar() 
                // -> Các ô sẽ tự động bỏ chọn và giao diện về trạng thái gốc.
            } else {
                alert("Lỗi khi dọn dẹp: " + result.message);
            }
        } catch (error) {
            console.error("Lỗi:", error);
            alert("Lỗi hệ thống khi dọn dẹp Field!");
        }
    });
    
    // placeholder click handlers for add, edit, delete
    // --- XỬ LÝ POPUP ADD FIELD ---
    const addFieldModal = document.getElementById('addFieldModal');
    const closeAddFieldModal = document.getElementById('closeAddFieldModal');
    const btnSubmitAdd = document.getElementById('btn-submit-add-field');
    const newFieldInput = document.getElementById('newFieldId');

    // Mở popup
    document.getElementById('btn-add-icon').addEventListener('click', () => {
        newFieldInput.value = ''; // Reset rỗng ô nhập
        addFieldModal.classList.remove('hidden');
        setTimeout(() => newFieldInput.focus(), 100); // Tự động focus con trỏ vào ô nhập
    });

    // Đóng popup
    closeAddFieldModal.addEventListener('click', () => addFieldModal.classList.add('hidden'));
    
    // Đóng popup khi ấn ra vùng nền đen
    window.addEventListener('click', (e) => {
        if(e.target === addFieldModal) addFieldModal.classList.add('hidden');
    });

    // Nút Submit Add
    btnSubmitAdd.addEventListener('click', async () => {
        const fieldId = newFieldInput.value.trim();
        if (!fieldId) {
            alert("Vui lòng nhập Field ID!");
            return;
        }

        // Gọi API lên Backend
        try {
            const response = await fetch('/api/admin/add_greenhouse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field_id: fieldId })
            });
            const result = await response.json();
            
            if (result.success) {
                addFieldModal.classList.add('hidden'); // Đóng popup
                loadFields(); // Tải lại bảng để thấy Field mới
            } else {
                alert("Lỗi khi thêm: " + result.message);
            }
        } catch (error) {
            console.error("Lỗi:", error);
            alert("Lỗi hệ thống khi thêm Field!");
        }
    });

    // --- XỬ LÝ POPUP EDIT FIELD ---
    const editFieldModal = document.getElementById('editFieldModal');
    const closeEditFieldModal = document.getElementById('closeEditFieldModal');
    const btnSubmitEdit = document.getElementById('btn-submit-edit-field');
    const editFieldIdSelect = document.getElementById('editFieldId');
    const editUsernameSelect = document.getElementById('editUsername');
    const editPlantInput = document.getElementById('editPlant');

    // Mở popup Edit
    document.getElementById('btn-edit-icon').addEventListener('click', async () => {
        // Lấy Field ID đang được tích chọn
        const checkedBoxes = document.querySelectorAll('.field-checkbox:checked');
        if (checkedBoxes.length !== 1) return; 
        const selectedFieldId = checkedBoxes[0].value;

        // 1. Đổ dữ liệu vào Dropdown Field ID (Từ biến allFields có sẵn)
        editFieldIdSelect.innerHTML = '<option value="">Choose the field</option>';
        allFields.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.field_id;
            opt.innerText = f.field_id;
            if (f.field_id === selectedFieldId) opt.selected = true; // Auto chọn field đang tích
            editFieldIdSelect.appendChild(opt);
        });

        // 2. Fetch danh sách User từ backend để đổ vào Dropdown Username
        try {
            const res = await fetch('/api/admin/users'); // Tận dụng API trang User
            const users = await res.json();
            editUsernameSelect.innerHTML = '<option value="">Choose username</option><option value="---">--- (Bỏ trống)</option>';
            users.forEach(u => {
                const opt = document.createElement('option');
                opt.value = u.username;
                opt.innerText = u.username;
                editUsernameSelect.appendChild(opt);
            });
        } catch (e) {
            console.error("Lỗi lấy danh sách user:", e);
        }

        // 3. Hiển thị thông tin Plant và Username hiện tại của Field
        const currentField = allFields.find(f => f.field_id === selectedFieldId);
        if (currentField) {
            editUsernameSelect.value = (currentField.username !== '---') ? currentField.username : "---";
            editPlantInput.value = (currentField.plant !== '---') ? currentField.plant : '';
        }

        editFieldModal.classList.remove('hidden');
    });

    // Đóng popup Edit
    closeEditFieldModal.addEventListener('click', () => editFieldModal.classList.add('hidden'));
    
    window.addEventListener('click', (e) => {
        if(e.target === editFieldModal) editFieldModal.classList.add('hidden');
    });

    // Xử lý nút Submit Edit
    btnSubmitEdit.addEventListener('click', async () => {
        const fieldId = editFieldIdSelect.value;
        let username = editUsernameSelect.value;
        let plant = editPlantInput.value.trim();

        if (!fieldId || fieldId === "") {
            alert("Vui lòng chọn Field ID!");
            return;
        }

        // Chuyển hóa các giá trị trống
        if (username === "---" || username === "Choose username") username = "";

        // Gọi API lên Backend
        try {
            const response = await fetch('/api/admin/edit_greenhouse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field_id: fieldId, username: username, plant: plant })
            });
            const result = await response.json();
            
            if (result.success) {
                editFieldModal.classList.add('hidden');
                loadFields(); // Tải lại bảng, các dòng sẽ tự bỏ chọn
            } else {
                alert("Lỗi khi cập nhật: " + result.message);
            }
        } catch (error) {
            console.error("Lỗi:", error);
            alert("Lỗi hệ thống khi cập nhật Field!");
        }
    });

    // 3. Chức năng Delete icon (Xóa vĩnh viễn Field khỏi Database)
    document.getElementById('btn-delete-icon').addEventListener('click', async () => {
        const checkedBoxes = document.querySelectorAll('.field-checkbox:checked');
        const fieldIds = Array.from(checkedBoxes).map(cb => cb.value);

        if (fieldIds.length === 0) return;

        // Bật hộp thoại cảnh báo cấp độ cao hơn (Vì hành động này xóa cả ID)
        const confirmMsg = `CẢNH BÁO: Bạn có chắc chắn muốn XÓA VĨNH VIỄN ${fieldIds.length} Field đã chọn?\n\n(Hành động này sẽ xóa hoàn toàn Field ID và các dữ liệu liên quan khỏi hệ thống và không thể hoàn tác!)`;
        
        if (!confirm(confirmMsg)) {
            return; // Dừng lại nếu người dùng ấn Hủy
        }

        // Gọi API lên Backend
        try {
            const response = await fetch('/api/admin/delete_greenhouse_fields', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ field_ids: fieldIds })
            });
            const result = await response.json();
            
            if (result.success) {
                loadFields(); // Tải lại bảng, hàm này tự động reset UI và ô check
            } else {
                alert("Lỗi khi xóa: " + result.message);
            }
        } catch (error) {
            console.error("Lỗi:", error);
            alert("Lỗi hệ thống khi xóa Field!");
        }
    });
    
    // Khởi tạo trạng thái ban đầu
    updateToolbar(); 
});

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
        
        // --- BỘ LỌC GỘP DỮ LIỆU FRONTEND (CHỐNG NHÂN BẢN) ---
        const fieldDict = {};
        
        fields.forEach(f => {
            if (!fieldDict[f.field_id]) {
                // Lần đầu gặp Field ID này -> Tạo mới trong từ điển
                fieldDict[f.field_id] = { ...f };
            } else {
                // Đã tồn tại (Bị trùng lặp) -> Tiến hành gộp dữ liệu
                const existing = fieldDict[f.field_id];
                
                // Ưu tiên giữ lại tên Plant thực tế (khác '---')
                if (existing.plant === '---' && f.plant !== '---') {
                    existing.plant = f.plant;
                }
                
                // Ưu tiên giữ lại Username thực tế (khác '---')
                if (existing.username === '---' && f.username !== '---') {
                    existing.username = f.username;
                } else if (existing.username !== '---' && f.username !== '---') {
                    // Nếu ruộng có nhiều người quản lý, nối tên cách nhau bằng dấu phẩy
                    if (!existing.username.includes(f.username)) {
                        existing.username += `, ${f.username}`;
                    }
                }
            }
        });
        
        // Chuyển lại từ điển đã lọc thành mảng để xử lý tiếp
        fields = Object.values(fieldDict);
        // ---------------------------------------------------

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
        
        tr.innerHTML = `
            <td><input type="checkbox" class="field-checkbox" value="${field.field_id}"></td>
            <td>${field.field_id}</td> 
            <td style="text-align: center;">${field.plant}</td>
            <td style="text-align: right;">${field.username}</td>
        `;

        // 1. Xử lý sự kiện cho checkbox (Chặn click lan ra hàng)
        const checkbox = tr.querySelector('.field-checkbox');
        checkbox.addEventListener('click', (e) => e.stopPropagation()); // NGĂN CHẶN click lan ra ngoài thẻ tr
        checkbox.addEventListener('change', () => updateToolbar()); 

        // 2. THÊM MỚI: Click vào bất kỳ đâu trên hàng sẽ chuyển sang Dashboard
        tr.style.cursor = 'pointer'; // Đổi con trỏ chuột thành hình bàn tay
        tr.addEventListener('click', () => {
            // Chuyển hướng mang theo tham số field_id
            window.location.href = `/dashboard?field_id=${field.field_id}`;
        });

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