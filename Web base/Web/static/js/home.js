// ==========================================
// CẤU HÌNH GIAO DIỆN
// ==========================================
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

// Biến toàn cục để quản lý các biểu đồ Chart.js (Chống đè biểu đồ)
window.chartInstances = {};

// ==========================================
// KHỞI CHẠY KHI TẢI TRANG
// ==========================================
document.addEventListener('DOMContentLoaded', function () {
// --- LẤY THÔNG TIN TÀI KHOẢN ĐANG ĐĂNG NHẬP ---
  fetch('/api/current_user')
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        // Điền tên và role vào HTML
        document.getElementById('userName').innerText = data.username;
        document.getElementById('userRole').innerText = data.role;
      } else {
        // Nếu server báo chưa đăng nhập, tự động đẩy ra trang login
        window.location.href = '/login'; 
      }
    })
    .catch(err => {
      console.error("Lỗi lấy thông tin user:", err);
      document.getElementById('userName').innerText = "ERROR";
    });

  const logoutBtn = document.getElementById('logoutBtn');
  const resultBox = document.getElementById('result');
  const summaryContainer = document.getElementById('field-summary-container');

  if (summaryContainer) {
    loadFieldSummaries();
  }

  // --- 1. TẢI TẤT CẢ RUỘNG ĐỂ TẠO CARD VÀ KHUNG BIỂU ĐỒ ---
  async function loadFieldSummaries() {
    try {
      summaryContainer.innerHTML = '<i>Đang tải thông tin các khu vực...</i>';

      const resFields = await fetch('/api/fields');
      if (!resFields.ok) throw new Error("Không tải được danh sách field");
      const fields = await resFields.json();

      summaryContainer.innerHTML = ''; 

      // Lặp qua từng ruộng
      for (let field of fields) {
        
        // A. TẠO CARD TÓM TẮT THÔNG SỐ
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

        // Đổ số liệu vào Card
        layDuLieuChoCard(field.field_id);

        // B. TẠO LUÔN KHUNG BIỂU ĐỒ CHO RUỘNG NÀY Ở PHÍA DƯỚI
        loadTatCaBieuDo(field.field_id, field.field_name);
      }
    } catch (err) {
      console.error(err);
      summaryContainer.innerHTML = '<span style="color:red">Lỗi tải dữ liệu hệ thống.</span>';
    }
  }

  // --- 2. LẤY DỮ LIỆU ĐIỀN VÀO CARD (MINI PANELS) ---
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
          <div style="margin-bottom: 10px;">${miniPanelsHTML}</div>
          <div style="font-size: 0.85em; color: #4CAF50; text-align: right; margin-top: 12px; font-weight: 500;">
            Vào bảng điều khiển &rarr;
          </div>
        `;
      }
    } catch (err) {
      console.error(`Lỗi lấy data cho ${fieldId}:`, err);
    }
  }

  // --- 3. QUÉT THIẾT BỊ VÀ TẠO KHUNG BIỂU ĐỒ ĐỘNG ---
  async function loadTatCaBieuDo(fieldId, fieldName) {
    const mainContainer = document.getElementById('dynamic-charts-container');
    if (!mainContainer) return;

    // Tạo một khung riêng biệt cho từng ruộng
    const fieldSection = document.createElement('div');
    fieldSection.style.cssText = "margin-top: 40px;";
    fieldSection.innerHTML = `
        <h3 style="color: #2c3e50; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; display: inline-block;">
            <i class="fa-solid fa-chart-area"></i> Biểu đồ: ${fieldName}
        </h3>
        <div id="chart-grid-${fieldId}" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-top: 15px;"></div>
    `;
    mainContainer.appendChild(fieldSection);
    
    const chartGrid = document.getElementById(`chart-grid-${fieldId}`);

    try {
        const res = await fetch('/api/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field_id: fieldId })
        });
        const data = await res.json();

        // Quét thiết bị để vẽ canvas
        if (Array.isArray(data)) {
            data.forEach(deviceObj => {
                for (const deviceName in deviceObj) {
                    const telemetries = deviceObj[deviceName];
                    
                    for (const teleKey in telemetries) {
                        if (!telemetries[teleKey] || telemetries[teleKey].value === undefined) continue;

                        // Tạo ID an toàn
                        const safeDeviceName = deviceName.replace(/\s+/g, '-');
                        const canvasId = `chart-${fieldId}-${safeDeviceName}-${teleKey}`;

                        const chartDiv = document.createElement('div');
                        chartDiv.style.cssText = "background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee;";
                        chartDiv.innerHTML = `
                            <h4 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 14px; text-transform: uppercase;">
                                <i class="fa-solid fa-chart-line" style="color:#4CAF50;"></i> ${teleKey} <span style="color:#999; font-size:12px;">(${deviceName})</span>
                            </h4>
                            
                            <div style="margin-bottom: 15px; display: flex; gap: 5px;">
                                <button onclick="window.taiBieuDoRieng('${deviceName}', '${teleKey}', '1h', '${canvasId}')" style="cursor:pointer; padding:3px 8px; font-size:12px; border-radius:4px; border:1px solid #ccc; background:#f9f9f9;">1h</button>
                                <button onclick="window.taiBieuDoRieng('${deviceName}', '${teleKey}', '1d', '${canvasId}')" style="cursor:pointer; padding:3px 8px; font-size:12px; border-radius:4px; border:1px solid #ccc; background:#f9f9f9;">1d</button>
                                <button onclick="window.taiBieuDoRieng('${deviceName}', '${teleKey}', '7d', '${canvasId}')" style="cursor:pointer; padding:3px 8px; font-size:12px; border-radius:4px; border:1px solid #ccc; background:#f9f9f9;">7d</button>
                                <button onclick="window.taiBieuDoRieng('${deviceName}', '${teleKey}', '30d', '${canvasId}')" style="cursor:pointer; padding:3px 8px; font-size:12px; border-radius:4px; border:1px solid #ccc; background:#f9f9f9;">30d</button>
                            </div>
                            
                            <div style="position: relative; height:250px; width:100%">
                                <canvas id="${canvasId}"></canvas>
                            </div>
                        `;
                        chartGrid.appendChild(chartDiv);

                        // Mặc định gọi API tải và vẽ dữ liệu 1 Ngày (1d)
                        window.taiBieuDoRieng(deviceName, teleKey, '1d', canvasId);
                    }
                }
            });
        }
    } catch (err) {
        console.error(`Lỗi tạo khung biểu đồ cho ${fieldId}:`, err);
    }
  }

  // --- 4. TÍNH NĂNG LOGOUT ---
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



window.taiBieuDoRieng = async function(deviceName, telemetry, timeMode, canvasId) {
    try {
        const res = await fetch('/api/send_chart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_name: deviceName,
                telemetry: telemetry,
                time: timeMode
            })
        });

        const data = await res.json();
        
        let labels = [];
        let values = [];

        // Bóc tách dữ liệu
        if (Array.isArray(data)) {
            labels = data.map(item => {
                
                let dateObj = new Date(item.ts); 
                
                let timeString = dateObj.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
                let dateString = dateObj.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
                return `${timeString} ${dateString}`;
            }); 
            
            
            values = data.map(item => item.value); 
        }

        const ctx = document.getElementById(canvasId);
        if (!ctx) return;


        if (window.chartInstances[canvasId]) {
            window.chartInstances[canvasId].destroy();
        }

        // Setup màu sắc
        let lineColor = '#3498db'; 
        if (telemetry.toLowerCase().includes('temp')) lineColor = '#e74c3c'; 
        if (telemetry.toLowerCase().includes('moisture')) lineColor = '#8e44ad'; 

        // Khởi tạo Chart
        window.chartInstances[canvasId] = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: `Giá trị (${timeMode})`,
                    data: values,
                    borderColor: lineColor,
                    backgroundColor: lineColor + '22',
                    borderWidth: 2,
                    pointRadius: 1, 
                    fill: true,     
                    tension: 0.3    
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }, 
                scales: {
                    x: { ticks: { autoSkip: true, maxTicksLimit: 8 } } 
                }
            }
        });

    } catch (err) {
        console.error(`Lỗi tải biểu đồ cho ${canvasId}:`, err);
    }
};