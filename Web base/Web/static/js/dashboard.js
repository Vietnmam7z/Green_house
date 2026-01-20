// dashboard.js
async function capNhatDuLieu() {
    try {
        const response = await fetch('/api/data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            // gửi field_id lên server
            body: JSON.stringify({ field_id: "field_999" })
        });

        const data = await response.json();
        console.log("Dữ liệu nhận được:", data);

        // --- Cập nhật số liệu ---
        const tempVal = parseFloat(data.temperature);
        const humidVal = parseFloat(data.humidity);
        const lightVal = parseFloat(data.light);
        const soilVal = parseFloat(data.soil_moisture);

        // Nhiệt độ
        const nhietDo = document.getElementById('nhiet-do');
        if (nhietDo) nhietDo.innerText = tempVal;

        // Độ ẩm
        const doAm = document.getElementById('do-am');
        if (doAm) doAm.innerText = humidVal;

        // Ánh sáng
        const anhSang = document.getElementById('anh-sang');
        if (anhSang) anhSang.innerText = lightVal;

        // Độ ẩm đất
        const soilMois = document.getElementById('soil-moisture');
        if (soilMois) soilMois.innerText = soilVal;

        // --- Badge cảnh báo ---
        const tempBadge = document.getElementById('badge-temp');
        if (tempBadge) tempBadge.style.display = (tempVal < 20 || tempVal > 50) ? 'flex' : 'none';

        const humidBadge = document.getElementById('badge-humid');
        if (humidBadge) humidBadge.style.display = (humidVal < 40 || humidVal > 90) ? 'flex' : 'none';

        const lightBadge = document.getElementById('badge-light');
        if (lightBadge) lightBadge.style.display = (lightVal < 150 || lightVal > 450) ? 'flex' : 'none';

        const soilBadge = document.getElementById('badge-soil-mois');
        if (soilBadge) soilBadge.style.display = (soilVal < 30 || soilVal > 80) ? 'flex' : 'none';

    } catch (err) {
        console.error("Lỗi tải dữ liệu:", err);
    }
}

async function layDanhSachField() {
    try {
        const response = await fetch('/api/fields', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        console.log("Danh sách field:", data);

        // Hiển thị ra giao diện
        const fieldContainer = document.getElementById('field-list');
        if (fieldContainer) {
            fieldContainer.innerHTML = "";
            data.forEach(field => {
                const li = document.createElement('li');
                // dùng đúng key field_name
                li.textContent = field.field_name; 
                fieldContainer.appendChild(li);
            });
        }
    } catch (err) {
        console.error("Lỗi khi gọi API get_field:", err);
    }
}

// Gọi ngay khi tải trang
layDanhSachField();

// Lặp lại mỗi 5 giây
setInterval(layDanhSachField, 5000);
// Gọi ngay khi tải trang
capNhatDuLieu();
// Lặp lại mỗi 5 giây
setInterval(capNhatDuLieu, 5000);