document.addEventListener("DOMContentLoaded", () => {
    // 1. Tải thông tin Admin
    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          document.getElementById('userName').innerText = data.username;
          
          // XỬ LÝ ĐỔI TÊN ROLE TỪ "admin" THÀNH "administrator"
          let displayRole = data.role;
          if (displayRole === 'admin') {
              displayRole = 'administrator';
          }
          document.getElementById('userRole').innerText = displayRole;

          // Điền tên vào Menu thả xuống
          const dropdownUserName = document.getElementById('dropdown-userName');
          if (dropdownUserName) dropdownUserName.innerText = data.username;

        } else {
          window.location.href = '/login';
        }
      })
      .catch(err => console.error("Lỗi lấy thông tin user:", err));

    // 2. Chức năng Đăng xuất (Đã cập nhật ID nút mới)
    const logoutBtn = document.getElementById('dropdown-logoutBtn');
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

    // 3. Chức năng chuyển trang của 2 nút vuông
    document.getElementById('btn-user-management')?.addEventListener('click', () => {
        window.location.href = '/admin_management/users';
    });

    document.getElementById('btn-greenhouse-management')?.addEventListener('click', () => {
        window.location.href = '/admin_management/greenhouses';
    });

    document.getElementById('btn-create-billing')?.addEventListener('click', () => {
        window.location.href = '/admin_management/billing'; 
    });
});