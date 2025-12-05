document.addEventListener('DOMContentLoaded', function () {
  const button = document.getElementById('logoutButton');
  const result = document.getElementById('result');

  button.addEventListener('click', function () {
    fetch('/logout', {
      method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        window.location.href = data.redirect;
      } else {
        result.innerText = "Đăng xuất thất bại!";
      }
    })
    .catch(error => {
      result.innerText = "Lỗi kết nối!";
      console.error("Lỗi:", error);
    });
  });
});
