document.addEventListener('DOMContentLoaded', function () {
  const logoutBtn = document.getElementById('logoutBtn');
  const resultBox = document.getElementById('result');
  const summaryContainer = document.getElementById('field-summary-container');

  // 1. TẢI VÀ HIỂN THỊ CÁC CARD TÓM TẮT
  if (summaryContainer) {
    loadFieldSummaries();
  }

  async function loadFieldSummaries() {
    try {
      summaryContainer.innerHTML = '<i>Đang tải thông tin các khu vực...</i>';

      // Lấy danh sách field
      const resFields = await fetch('/api/fields');
      if (!resFields.ok) throw new Error("Không tải được danh sách field");
      const fields = await resFields.json();

      summaryContainer.innerHTML = ''; // Xóa chữ Đang tải

      // Lặp qua từng field để tạo Card
      for (let field of fields) {
        const card = document.createElement('div');
        card.className = 'field-card';
        card.innerHTML = `
          <h3><i class="fa-solid fa-leaf" style="color:#4CAF50;"></i> ${field.field_name}</h3>
          <div id="summary-${field.field_id}">
            <span style="color:#999;">Đang lấy dữ liệu cảm biến...</span>
          </div>
        `;

        card.addEventListener('click', () => {
          window.location.href = '/dashboard?field_id=' + field.field_id;
        });

        summaryContainer.appendChild(card);

        layDuLieuChoCard(field.field_id);
      }
    } catch (err) {
      console.error(err);
      summaryContainer.innerHTML = '<span style="color:red">Lỗi tải dữ liệu hệ thống.</span>';
    }
  }

  const telemetryConfig = {
    "temperature": { label: "Nhiệt độ", unit: "°C", icon: "fa-temperature-half", color: "#e74c3c" },
    "humidity": { label: "Độ ẩm khí", unit: "%", icon: "fa-droplet", color: "#3498db" },
    "moisture": { label: "Độ ẩm đất", unit: "%", icon: "fa-water", color: "#8e44ad" },
    "light": { label: "Ánh sáng", unit: "lx", icon: "fa-sun", color: "#f1c40f" }
  };

  function getConfig(key) {
    const lowerKey = key.toLowerCase();
    for (let prop in telemetryConfig) {
        if (lowerKey.includes(prop)) return telemetryConfig[prop];
    }
    return { label: key, unit: "", icon: "fa-microchip", color: "#7f8c8d" };
  }

  async function layDuLieuChoCard(fieldId) {
    try {
      const resData = await fetch('/api/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_id: fieldId })
      });
      const data = await resData.json();

      let miniPanelsHTML = "";

      if (Array.isArray(data)) {
        data.forEach(deviceObj => {
          for (const deviceName in deviceObj) {
            const telemetries = deviceObj[deviceName];
            
            if (!telemetries || Object.keys(telemetries).length === 0) continue;

            miniPanelsHTML += `
              <div style="font-size: 12px; color: #2c3e50; font-weight: 600; margin-top: 12px; margin-bottom: 4px; border-bottom: 1px solid #eaeaea; padding-bottom: 3px; text-transform: uppercase;">
                <i class="fa-solid fa-microchip" style="color: #95a5a6; margin-right: 4px;"></i> ${deviceName}
              </div>
            `;

            for (const teleKey in telemetries) {
              const teleData = telemetries[teleKey];
              
              if (teleData && teleData.value !== undefined) {
                const val = parseFloat(teleData.value);
                const config = getConfig(teleKey);
                const displayVal = isNaN(val) ? "--" : val;

                miniPanelsHTML += `
                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0 4px 10px;">
                    <span style="color: #666; font-size: 13.5px;">
                      <i class="fa-solid ${config.icon}" style="color: ${config.color}; width: 18px; text-align: center;"></i> 
                      ${config.label}
                    </span>
                    <strong style="font-size: 14px; color: #333;">
                      ${displayVal} <span style="font-size: 11px; color: #888; font-weight: normal;">${config.unit}</span>
                    </strong>
                  </div>
                `;
              }
            }
          }
        });
      }
      if (miniPanelsHTML === "") {
        miniPanelsHTML = '<div style="color:#999; font-size:13px; padding: 10px 0; text-align: center;">Chưa có dữ liệu cảm biến</div>';
      }

      const summaryDiv = document.getElementById(`summary-${fieldId}`);
      if (summaryDiv) {
        summaryDiv.innerHTML = `
          <div style="margin-bottom: 10px;">
            ${miniPanelsHTML}
          </div>
          <div style="font-size: 0.85em; color: #4CAF50; text-align: right; margin-top: 12px; font-weight: 500;">
            Vào bảng điều khiển &rarr;
          </div>
        `;
      }
    } catch (err) {
      console.error(`Lỗi lấy data cho ${fieldId}:`, err);
    }
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', function (e) {
      e.preventDefault();
      fetch('/logout', { method: 'POST' })
        .then(res => {
          if (!res.ok) throw new Error("Server trả về lỗi");
          return res.json();
        })
        .then(data => {
          if (data.success) { window.location.href = data.redirect || '/login'; } 
          else { resultBox.innerText = data.message || "Không thể đăng xuất."; }
        })
        .catch(error => { resultBox.innerText = "Lỗi kết nối!"; });
    });
  }
});