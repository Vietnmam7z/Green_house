#include <WiFi.h>
#include <Arduino_MQTT_Client.h>
#include <ThingsBoard.h>
#include <ModbusMaster.h>
#include <ADv2_inferencing.h>

#include "edge-impulse-sdk/tensorflow/lite/micro/all_ops_resolver.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/micro_error_reporter.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/micro_interpreter.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/system_setup.h"
#include "edge-impulse-sdk/tensorflow/lite/schema/schema_generated.h"
// ================== Cấu hình Bộ lọc (Filter Config) ==================
const int SAMPLES = 5;       // Số mẫu đọc để lấy trung vị (Nên là số lẻ: 5, 7, 9)
const float ALPHA = 0.2;     // Hệ số EMA (0.1 - 0.3 là đẹp cho độ ẩm đất). 
                             // 0.2 nghĩa là tin giá trị mới 20%, tin lịch sử 80% -> Rất mượt.
float currentEmaMoisture = 0.0; // Biến lưu giá trị sau khi đã lọc
bool firstRun = true;        // Cờ đánh dấu lần chạy đầu tiên

// ================== WiFi ==================
const char* WIFI_SSID     = "ACLAB";
const char* WIFI_PASSWORD = "ACLAB2023";

// ================== ThingsBoard ==================
#define TOKEN "L2EeczCnJSN0xBjh6Mwp"
#define THINGSBOARD_SERVER "mqtt.thingsboard.cloud"
#define THINGSBOARD_PORT 1883

WiFiClient wifiClient;
Arduino_MQTT_Client mqttClient(wifiClient);
ThingsBoard tb(mqttClient);

// ================== Modbus RTU ==================
#define RS485_RX 6   // RX2
#define RS485_TX 7   // TX2
#define RS485_DE_RE 4 // DE/RE chân điều khiển MAX485

HardwareSerial mySerial(2);
ModbusMaster node;

unsigned long lastSend = 0;

// Hàm điều khiển luồng RS485
void preTransmission() {
  digitalWrite(RS485_DE_RE, HIGH);
}

void postTransmission() {
  digitalWrite(RS485_DE_RE, LOW);
}

// ================== Hàm phụ trợ: Sắp xếp mảng (Bubble Sort) ==================
// Dùng để sắp xếp các mẫu đọc được từ bé đến lớn -> Lấy số ở giữa
void sortArray(uint16_t *a, int n) {
  for (int i = 0; i < n - 1; i++) {
    for (int j = i + 1; j < n; j++) {
      if (a[i] > a[j]) {
        uint16_t temp = a[i];
        a[i] = a[j];
        a[j] = temp;
      }
    }
  }
}

// Biến lưu trữ data để chạy AI
static float features[4] = {0};
int raw_feature_get_data(size_t offset, size_t length, float *out_ptr) {
    memcpy(out_ptr, features + offset, length * sizeof(float));
    return 0;
}


void setup() {
  Serial.begin(115200);
  delay(1000);

  // Kết nối WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");

  // UART2 cho RS485
  pinMode(RS485_DE_RE, OUTPUT);
  digitalWrite(RS485_DE_RE, LOW);
  mySerial.begin(9600, SERIAL_8N1, RS485_RX, RS485_TX);

  // Khởi tạo ModbusMaster
  node.begin(0x11, mySerial); // Slave ID = 0x11
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  Serial.println("Modbus RTU + ThingsBoard start...");
}

void loop() {
  // Nếu chưa kết nối tới ThingsBoard thì kết nối lại
  if (!tb.connected()) {
    Serial.print("Connecting to ThingsBoard...");
    if (!tb.connect(THINGSBOARD_SERVER, TOKEN, THINGSBOARD_PORT)) {
      Serial.println(" Failed!");
      delay(2000);
      return;
    }
    Serial.println(" Connected!");
  }

  // Gửi dữ liệu mỗi 5 giây
  if (millis() - lastSend > 5000) {
    lastSend = millis();

    uint16_t rawBuffer[SAMPLES]; // Mảng chứa các mẫu đọc thô
    int validCount = 0;          // Đếm số lần đọc thành công

    // --- BƯỚC 1: Thu thập mẫu (Sampling) ---
    Serial.print("Sampling: ");
    for (int i = 0; i < SAMPLES; i++) {
      uint8_t result = node.readHoldingRegisters(0x0013, 1);
      
      if (result == node.ku8MBSuccess) {
        uint16_t val = node.getResponseBuffer(0);
        
        // Lọc sơ cấp: Chỉ nhận giá trị trong khoảng hợp lý (VD: 0-100 hoặc 0-1000 tùy cảm biến)
        // Giả sử cảm biến trả về 0-100%. Nếu > 100 coi là nhiễu bỏ qua.
        // Nếu cảm biến bạn trả về kiểu 655 (65.5%) thì sửa số 100 thành 1000 nhé.
        if (val <= 1000) { 
           rawBuffer[validCount] = val;
           validCount++;
           Serial.print(val); Serial.print(" ");
        }
      } else {
        Serial.print("Err ");
      }
      delay(50); // Nghỉ 50ms giữa các lần đọc để tránh nghẽn Modbus
    }
    Serial.println();

    // Chỉ xử lý nếu có ít nhất 1 mẫu đọc thành công
    if (validCount > 0) {
      
      // --- BƯỚC 2: Bộ lọc Trung vị (Median Filter) ---
      // Loại bỏ nhiễu gai (Outliers)
      sortArray(rawBuffer, validCount);
      uint16_t medianVal = rawBuffer[validCount / 2]; 
      Serial.printf("Median Value: %u\n", medianVal);

      // --- BƯỚC 3: Bộ lọc EMA (Exponential Moving Average) ---
      // Làm mượt đường đồ thị
      if (firstRun) {
        currentEmaMoisture = medianVal; // Lần đầu thì gán luôn
        firstRun = false;
      } else {
        // Công thức: EMA = alpha * Mới + (1 - alpha) * Cũ
        currentEmaMoisture = (ALPHA * medianVal) + ((1.0 - ALPHA) * currentEmaMoisture);
      }

      Serial.printf("Filtered (EMA): %.2f\n", currentEmaMoisture/10);

      // --- BƯỚC 4: Gửi dữ liệu đã lọc lên ThingsBoard ---
      // Gửi giá trị thực (float) hoặc ép kiểu về int tùy nhu cầu hiển thị
      tb.sendTelemetryData("moisture", currentEmaMoisture/10); 
      
      // Mẹo: Nếu muốn gửi cả raw để so sánh trên Dashboard
      // tb.sendTelemetryData("moisture_raw", medianVal); 

      // --- BƯỚC 5: Phân loại dữ liệu ---
      features[0]= 1;
      features[1]= 1;
      features[2]= 1;
      features[3]= currentEmaMoisture/10;
      if (sizeof(features) / sizeof(float) != EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) {
        ei_printf("The size of your 'features' array is not correct. Expected %lu items, but had %lu\n",
            EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE, sizeof(features) / sizeof(float));
        delay(1000);
        return;
      }

      ei_impulse_result_t result = { 0 };

      // the features are stored into flash, and we don't want to load everything into RAM
     
      signal_t features_signal;
      features_signal.total_length = sizeof(features) / sizeof(features[0]);
      features_signal.get_data = &raw_feature_get_data;

      // invoke the impulse
      EI_IMPULSE_ERROR res = run_classifier(&features_signal, &result, false /* debug */);
      ei_printf("run_classifier returned: %d\n", res);

      if (res != 0) return;

      // print the predictions
      ei_printf("Predictions ");
      ei_printf("(DSP: %d ms., Classification: %d ms., Anomaly: %d ms.)",
          result.timing.dsp, result.timing.classification, result.timing.anomaly);
      ei_printf(": \n");
      ei_printf("[");
      for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
          ei_printf("%.5f", result.classification[ix].value);
          #if EI_CLASSIFIER_HAS_ANOMALY == 1
            ei_printf(", ");
          #else
          if (ix != EI_CLASSIFIER_LABEL_COUNT - 1) {
              ei_printf(", ");
          }
          #endif
      }
      #if EI_CLASSIFIER_HAS_ANOMALY == 1
        ei_printf("%.3f", result.anomaly);
      #endif
        ei_printf("]\n");
      // human-readable predictions
      for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
          ei_printf("    %s: %.5f\n", result.classification[ix].label, result.classification[ix].value);
      }
      #if EI_CLASSIFIER_HAS_ANOMALY == 1
      ei_printf("    anomaly score: %.3f\n", result.anomaly);
      #endif
      } else {
        Serial.println("Read failed all samples!");
      }
    }

  tb.loop(); // Xử lý MQTT
}