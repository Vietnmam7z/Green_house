document.getElementById("forgotForm").addEventListener("submit", function(e) {
  e.preventDefault(); // chặn reload

  const email = document.getElementById("email").value.trim();

  if (!email) {
    alert("Please enter your email.");
    return;
  }

  fetch("/forgot-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email: email })
  })
  .then(res => {
    if (!res.ok) throw new Error("Server error");
    return res.json();
  })
  .then(data => {
    if (data.success) {
      // Nếu email hợp lệ và OTP đã gửi → chuyển sang trang nhập OTP
      window.location.href = "send_otp.html";
    } else {
      alert(data.message || "Email không tồn tại.");
    }
  })
  .catch(error => {
    console.error("Lỗi:", error);
    alert("Không thể kết nối đến server.");
  });
});