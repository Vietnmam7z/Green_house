document.addEventListener('DOMContentLoaded', function () {
  const logoutBtn = document.getElementById('logoutBtn');
  const resultBox = document.getElementById('result');
  const goToDashboardBtn = document.getElementById('goToDashboardBtn'); // Nút mới thêm

  // --- 1. TÍNH NĂNG MỚI: CHUYỂN ĐẾN DASHBOARD ---
  if (goToDashboardBtn) {
    goToDashboardBtn.addEventListener('click', function () {
      window.location.href = '/dashboard';
    });
  }

  // --- 2. TÍNH NĂNG CŨ: ĐĂNG XUẤT (Giữ nguyên 100%) ---
  if (logoutBtn) {
    logoutBtn.addEventListener('click', function (e) {
      e.preventDefault();

      fetch('/logout', {
        method: 'POST'
      })
        .then(res => {
          if (!res.ok) throw new Error("Server trả về lỗi");
          return res.json();
        })
        .then(data => {
          if (data.success) {
            window.location.href = data.redirect || '/login';
          } else {
            resultBox.innerText = data.message || "Không thể đăng xuất.";
          }
        })
        .catch(error => {
          resultBox.innerText = "Lỗi kết nối đến server!";
          console.error("Lỗi:", error);
        });
    });
  }
});