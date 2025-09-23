const resendBtn = document.getElementById("resendBtn");
let timer;
let timeLeft = 180;

function startTimer() {
  timeLeft = 180;
  resendBtn.disabled = true;

  timer = setInterval(() => {
    let minutes = Math.floor(timeLeft / 60);
    let seconds = timeLeft % 60;
    resendBtn.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

    timeLeft--;

    if (timeLeft < 0) {
      clearInterval(timer);
      resendBtn.disabled = false;
      resendBtn.textContent = "Resend OTP";
    }
  }, 1000);
}

resendBtn.addEventListener("click", () => {
  if (resendBtn.textContent === "Resend OTP") {
    startTimer();
  }
});

// Khi load trang thì bắt đầu đếm luôn
window.onload = startTimer;