document.addEventListener('DOMContentLoaded', function () {
  const loginForm = document.getElementById('loginForm');
  const resultBox = document.getElementById('result');
  const signupLink = document.getElementById('signupLink');
  const forgotLink = document.getElementById('forgotLink');

  // Xử lý submit login
  loginForm.addEventListener('submit', function (e) {
    e.preventDefault();

    const formData = new FormData(loginForm);
    const username = formData.get('username').trim();
    const password = formData.get('password').trim();

    if (!username || !password) {
      resultBox.innerText = "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.";
      return;
    }

    fetch('/login', {
      method: 'POST',
      body: formData
    })
      .then(res => {
        if (!res.ok) throw new Error("Server trả về lỗi");
        return res.json();
      })
      .then(data => {
        if (data.success) {
          window.location.href = data.redirect;
        } else {
          resultBox.innerText = data.message;
        }
      })
      .catch(error => {
        resultBox.innerText = "Lỗi kết nối đến server!";
        console.error("Lỗi:", error);
      });
  });

  // Chuyển route /signup
  signupLink.addEventListener('click', function (e) {
    e.preventDefault();
    window.location.href = "/signup";
  });

  // Chuyển route /forgot-password
  forgotLink.addEventListener('click', function (e) {
    e.preventDefault();
    window.location.href = "/forgot-password";
  });
});
