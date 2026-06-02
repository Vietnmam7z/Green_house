# Phát triển Hệ thống Giám sát, Dự báo và Điều khiển Tự động trong Nông nghiệp dựa trên công nghệ IoT

## Giới thiệu

Đây là đồ án xây dựng mô hình **nhà kính thông minh** ứng dụng công nghệ IoT nhằm hỗ trợ giám sát môi trường, dự báo xu hướng dữ liệu và điều khiển thiết bị tự động trong nông nghiệp.

Hệ thống kết hợp giữa phần cứng nhúng, cảm biến, truyền thông MQTT, Web Server, cơ sở dữ liệu và các mô hình AI để tạo thành một nền tảng quản lý nhà kính có khả năng vận hành từ xa, hỗ trợ phân quyền người dùng và điều khiển thiết bị theo thời gian thực.

## Mục tiêu hệ thống

- Giám sát các thông số môi trường trong nhà kính theo thời gian thực.
- Thu thập dữ liệu từ cảm biến như nhiệt độ, độ ẩm không khí, độ ẩm đất và ánh sáng.
- Truyền dữ liệu từ thiết bị IoT lên hệ thống thông qua MQTT.
- Hiển thị dữ liệu trực quan trên Web Dashboard.
- Điều khiển các thiết bị như đèn, quạt, van tưới, máy bơm, quạt thông gió, cooling pad, heater và CO2 valve.
- Hỗ trợ điều khiển thủ công, điều khiển tự động theo ngưỡng và lập lịch vận hành.
- Tích hợp mô hình AI phục vụ phát hiện bất thường và dự báo xu hướng môi trường.
- Hỗ trợ quản lý người dùng, phân quyền Admin/User và quản lý khu vực canh tác.

## Chức năng chính

### 1. Giám sát môi trường

Hệ thống thu thập dữ liệu môi trường từ các cảm biến được kết nối với vi điều khiển. Các thông số có thể bao gồm:

- Nhiệt độ không khí
- Độ ẩm không khí
- Độ ẩm đất
- Ánh sáng
- Trạng thái thiết bị
- Dữ liệu tưới tiêu

Dữ liệu được gửi về server và hiển thị trên giao diện Web để người dùng theo dõi trạng thái nhà kính.

### 2. Dự báo và phát hiện bất thường

Hệ thống tích hợp các mô hình AI nhằm hỗ trợ:

- Phân tích chuỗi dữ liệu thời gian từ cảm biến.
- Phát hiện bất thường trong môi trường canh tác.
- Dự báo xu hướng thay đổi của các thông số môi trường.
- Hỗ trợ người dùng đưa ra quyết định điều khiển phù hợp hơn.

Các thư viện được sử dụng có thể bao gồm TensorFlow, scikit-learn, pandas và joblib.

### 3. Điều khiển tự động thiết bị

Các thiết bị trong nhà kính có thể được điều khiển thông qua Web Server hoặc cơ chế tự động. Hệ thống hỗ trợ các nhóm thiết bị như:

- Light
- Vent
- Fan
- Valve / Irrigation
- Cooling pad
- Heater
- CO2 valve
- Fertilizer / Fertigation

Cơ chế điều khiển gồm:

- Điều khiển thủ công từ giao diện Web.
- Đồng bộ trạng thái thiết bị giữa Web Server, cơ sở dữ liệu và thiết bị thực tế.
- Điều khiển theo lịch.
- Điều khiển theo ngưỡng môi trường.
- Điều khiển dựa trên kết quả phát hiện bất thường.

### 4. Quản lý Web và phân quyền

Web Server hỗ trợ mô hình nhiều người dùng, gồm:

- **Administrator**: quản lý người dùng, quản lý nhà kính, quản lý ruộng/khu vực canh tác, quản lý hóa đơn và gói dịch vụ.
- **User/Tenant**: theo dõi dữ liệu, điều khiển thiết bị và quản lý khu vực được cấp quyền.

Các chức năng Web gồm:

- Đăng nhập
- Đăng ký
- Quên mật khẩu
- Dashboard giám sát
- Control thiết bị
- Lập lịch điều khiển
- Quản lý tài khoản
- Quản lý hóa đơn
- Quản lý gói dịch vụ

## Kiến trúc hệ thống

Hệ thống được thiết kế theo kiến trúc nhiều lớp:

1. **Lớp cảm biến**  
   Thu thập dữ liệu môi trường từ cảm biến đất, cảm biến môi trường và các thiết bị đo lường.

2. **Lớp thiết bị chấp hành**  
   Bao gồm các thiết bị điều khiển như bơm nước, van tưới, quạt, đèn, heater, cooling pad và các thiết bị phụ trợ khác.

3. **Lớp Gateway / Edge**  
   Sử dụng ESP32 để đọc dữ liệu cảm biến, xử lý cục bộ và giao tiếp với server hoặc nền tảng IoT.

4. **Lớp Cloud / Server**  
   Web Server xử lý API, lưu trữ dữ liệu, quản lý người dùng, điều khiển thiết bị, chạy scheduler và tích hợp AI.

5. **Lớp ứng dụng**  
   Giao diện Web cho phép người dùng theo dõi dữ liệu, điều khiển thiết bị và cấu hình hệ thống.

## Công nghệ sử dụng

### Phần cứng và IoT

- ESP32 / ESP32-S3
- Cảm biến môi trường
- Cảm biến đất
- Relay điều khiển thiết bị
- MQTT
- RS485 / Modbus RTU nếu dùng cảm biến công nghiệp

### Web Server và AI

- Python
- Flask
- FastAPI
- SQLite
- APScheduler
- TensorFlow
- scikit-learn
- pandas
- joblib
- paho-mqtt
- flask-cors
- python-dotenv

## Cấu trúc thư mục

```text
.
├── ESP-32/
│   └── Source code firmware cho vi điều khiển ESP32
│
├── Web base/
│   └── Source code Web Server, API, database, AI model và giao diện quản lý
│
└── README.md
```

## Hướng dẫn chạy thư mục ESP-32

Thư mục `ESP-32` chứa mã nguồn dành cho vi điều khiển ESP32. Dự án được build và nạp bằng **PlatformIO**.

### Các bước thực hiện

1. Cài đặt Visual Studio Code.
2. Cài đặt extension **PlatformIO IDE**.
3. Mở thư mục `ESP-32` bằng VS Code.
4. Kiểm tra file `platformio.ini` và cấu hình đúng board ESP32 đang sử dụng.
5. Kết nối ESP32 với máy tính qua cổng USB.
6. Build chương trình bằng PlatformIO.
7. Upload firmware xuống ESP32.
8. Mở Serial Monitor để kiểm tra log hoạt động.

Lệnh PlatformIO tham khảo:

```bash
pio run
pio run --target upload
pio device monitor
```

## Hướng dẫn chạy thư mục Web base

Thư mục `Web base` chứa Web Server, API, giao diện quản lý, xử lý điều khiển thiết bị, scheduler và các thành phần AI.

### 1. Di chuyển vào thư mục Web base

```bash
cd "Web base"
```

### 2. Cài đặt các thư viện cần thiết

Chạy lần lượt các lệnh sau:

```bash
pip install joblib
pip install fastapi
pip install tensorflow
pip install scikit-learn
pip install apscheduler
pip install flask
pip install requests
pip install pandas
pip install flask requests python-dotenv flask-cors
pip install paho-mqtt==1.6.1
```

### 3. Chạy chương trình

```bash
python main
```

Trong một số môi trường, nếu file chính có đuôi `.py`, có thể chạy:

```bash
python main.py
```

## Ghi chú cấu hình

Trước khi chạy hệ thống, cần kiểm tra các thông tin cấu hình như:

- Địa chỉ MQTT broker
- Token và thông tin kết nối thiết bị
- Cấu hình database
- Cổng chạy Flask/FastAPI

## Kết quả mong đợi

Sau khi triển khai, hệ thống có thể:

- Nhận dữ liệu từ thiết bị ESP32.
- Lưu dữ liệu cảm biến vào cơ sở dữ liệu.
- Hiển thị dữ liệu trên Web Dashboard.
- Điều khiển thiết bị từ giao diện Web.
- Đồng bộ trạng thái thiết bị giữa Web và hệ thống IoT.
- Tạo và xử lý lịch điều khiển tự động.
- Phát hiện bất thường hoặc dự báo xu hướng môi trường bằng mô hình AI.

## Nhóm thực hiện

- Nông Văn Trung - 2213707
- Phan Huy Trung - 2213709
- Hồ Ngọc Anh Tuấn - 2213768

## Hướng dẫn tải

Tải source code bằng cách chọn **Code → Download ZIP** trên GitHub hoặc dùng lệnh `git clone <repository-url>` để tải project về máy.
