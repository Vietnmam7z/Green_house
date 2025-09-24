document.getElementById("resetForm").addEventListener("submit", function(e) {
  e.preventDefault();

  const newPassword = document.getElementById("newPassword").value.trim();
  const confirmPassword = document.getElementById("confirmPassword").value.trim();

  if (!newPassword || !confirmPassword) {
    alert("Please fill in both fields.");
    return;
  }

  if (newPassword !== confirmPassword) {
    alert("Passwords do not match.");
    return;
  }

  fetch("/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert(data.message);
      window.location.href = data.redirect;
    } else {
      alert(data.message);
    }
  })
  .catch(err => {
    console.error("Error:", err);
    alert("Something went wrong.");
  });
});