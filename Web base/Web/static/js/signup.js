document.querySelector("form").addEventListener("submit", function(e) {
  e.preventDefault();

  const formData = new FormData(this);

  fetch("/signup", {
    method: "POST",
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      // Nếu đăng ký thành công, chuyển hướng sang trang login
      window.location.href = data.redirect || "/login";
    } else {
      // Nếu thất bại (trùng email/username), hiển thị thông báo
      showMessage(data.message || "Đăng ký thất bại, vui lòng thử lại!");
    }
  })
  .catch(error => {
    showMessage("Lỗi kết nối đến server!");
    console.error("Lỗi:", error);
  });
});

// Hàm hiển thị thông báo
function showMessage(msg) {
  let result = document.getElementById("result");
  if (!result) {
    result = document.createElement("p");
    result.id = "result";
    result.style.color = "red";
    result.style.marginTop = "10px";
    document.querySelector(".signup-container").appendChild(result);
  }
  result.innerText = msg;
}
