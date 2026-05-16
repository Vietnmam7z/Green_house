// ==========================================
// CẤU HÌNH GIAO DIỆN
// ==========================================
const telemetryConfig = {
  "temperature": { label: "Air Temperature", unit: "°C", icon: "fa-temperature-half", color: "#e74c3c" },
  "humidity": { label: "Air Humidity", unit: "%", icon: "fa-droplet", color: "#3498db" },
  "moisture": { label: "Soil Moisture", unit: "%", icon: "fa-water", color: "#8e44ad" },
  "light": { label: "Light Intensity", unit: "lx", icon: "fa-sun", color: "#f1c40f" }
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
fetch('/api/current_user')
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        document.getElementById('userName').innerText = data.username;
        document.getElementById('userRole').innerText = data.role;
        
        const dropdownUserName = document.getElementById('dropdown-userName');
        if (dropdownUserName) dropdownUserName.innerText = data.username;

        // Lấy 4 chức năng mới định danh bằng ID
        const menuAccount = document.getElementById('menu-account');
        const menuBilling = document.getElementById('menu-billing');
        const menuHistory = document.getElementById('menu-history');
        const menuService = document.getElementById('menu-service');
        const logoutBtn = document.getElementById('dropdown-logoutBtn');

        // THỰC THI QUY TẮC PHÂN QUYỀN CỦA BẠN
        if (data.role === 'admin' || data.role === 'administrator') {
            // ADMIN: Chỉ hiển thị phần Thông tin tài khoản, ẩn 3 chức năng còn lại
            if (menuAccount) menuAccount.style.display = 'flex';
            if (menuBilling) menuBilling.style.display = 'none';
            if (menuHistory) menuHistory.style.display = 'none';
            if (menuService) menuService.style.display = 'none';
        } else {
            // USER: Hiển thị đầy đủ cả 4 chức năng
            if (menuAccount) menuAccount.style.display = 'flex';
            if (menuBilling) menuBilling.style.display = 'flex';
            if (menuHistory) menuHistory.style.display = 'flex';
            if (menuService) menuService.style.display = 'flex';
        }
        if (logoutBtn) logoutBtn.style.display = 'flex';

      } else {
        window.location.href = '/login'; 
      }
    })
    .catch(err => {
      console.error("Lỗi lấy thông tin user:", err);
    });

  // Lắng nghe sự kiện click vào nút Đăng xuất mới trong Dropdown Menu
    document.getElementById('dropdown-logoutBtn')?.addEventListener('click', function(e) {
        e.preventDefault(); // Chặn hành vi nhảy hashtag # mặc định
        
        fetch('/logout', {
            method: 'POST'
        })
        .then(response => {
            // Chuyển hướng về trang đăng nhập sau khi xóa session thành công
            window.location.href = '/login';
        })
        .catch(err => console.error("Lỗi đăng xuất:", err));
    });
  const resultBox = document.getElementById('result');
  const summaryContainer = document.getElementById('field-summary-container');

  const btnSettings = document.getElementById('btn-settings');
  if (btnSettings) {
      btnSettings.addEventListener('click', () => {
          window.location.href = '/manage';
      });
  }
  
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
            Go to Dashboard &rarr;
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