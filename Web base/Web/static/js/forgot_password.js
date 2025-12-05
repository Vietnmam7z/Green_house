// Xử lý gửi email và hiển thị pop-up OTP
document.getElementById("forgotForm").addEventListener("submit", function(e) {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();

  if (!email) {
    alert("Please enter your email.");
    return;
  }

  fetch("/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      document.getElementById("otpPopup").style.display = "flex";
      startTimer();
    } else {
      alert(data.message || "Email không tồn tại.");
    }
  });
});

// Xử lý xác thực OTP
document.getElementById("verifyOtpBtn").addEventListener("click", function() {
  const otp = document.getElementById("otpInput").value.trim();
  if (!otp) {
    alert("Please enter the OTP.");
    return;
  }

  fetch("/verify-otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ otp: otp })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.location.href = data.redirect || "/reset-password";
    } else {
      alert(data.message || "Invalid OTP.");
    }
  })
  .catch(err => {
    console.error(err);
    alert("Server error.");
  });
});

// Đóng pop-up OTP
document.getElementById("closeOtpBtn").addEventListener("click", function() {
  document.getElementById("otpPopup").style.display = "none";
});

// Logic đếm ngược và resend OTP
// const resendBtn = document.getElementById("resendBtn");
// let timer;
// let timeLeft = 180;

// function startTimer() {
//   timeLeft = 180;
//   resendBtn.disabled = true;

//   timer = setInterval(() => {
//     let minutes = Math.floor(timeLeft / 60);
//     let seconds = timeLeft % 60;
//     resendBtn.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

//     timeLeft--;

//     if (timeLeft < 0) {
//       clearInterval(timer);
//       resendBtn.disabled = false;
//       resendBtn.textContent = "Resend OTP";
//     }
//   }, 1000);
// }

// resendBtn.addEventListener("click", () => {
//   if (resendBtn.textContent === "Resend OTP") {
//     // Gửi lại OTP tới email
//     fetch("/resend-otp", { method: "POST" })
//       .then(res => res.json())
//       .then(data => {
//         if (data.success) {
//           alert("OTP resent to your email.");
//           startTimer();
//         } else {
//           alert(data.message || "Failed to resend OTP.");
//         }
//       })
//       .catch(err => {
//         console.error(err);
//         alert("Server error.");
//       });
//   }
// });