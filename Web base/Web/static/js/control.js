document.addEventListener("DOMContentLoaded", () => {
    // 1. Tải thông tin người dùng lên Navbar
    fetch('/api/current_user')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          document.getElementById('userName').innerText = data.username;
          document.getElementById('userRole').innerText = data.role;
        }
      })
      .catch(err => console.error("Lỗi lấy thông tin user:", err));

    // 2. Chức năng Đăng xuất
    const logoutBtn = document.getElementById('logoutBtn');
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

    // 3. Chức năng nút Back (Quay về Dashboard)
    const btnBack = document.getElementById('goToDashboard');
    if (btnBack) {
        btnBack.addEventListener('click', () => {
            // Thay vì dùng url tĩnh, bạn có thể lưu history để quay về đúng field trước đó
            window.location.href = '/dashboard';
        });
    }
    
    // 4. Chức năng Menu Quản lý
    const btnSettings = document.getElementById('btn-settings');
    if (btnSettings) {
        btnSettings.addEventListener('click', () => {
            window.location.href = '/manage';
        });
    }
});