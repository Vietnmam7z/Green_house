document.getElementById('loginForm').addEventListener('submit', function(e) {
  e.preventDefault();

  const formData = new FormData(this);

  fetch('/login', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.location.href = data.redirect;
    } else {
      document.getElementById('result').innerText = data.message;
    }
  })
  .catch(error => {
    document.getElementById('result').innerText = "Lỗi kết nối đến server!";
    console.error("Lỗi:", error);
  });
});
