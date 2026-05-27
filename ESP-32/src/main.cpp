#include <WiFi.h>
#include <Arduino_MQTT_Client.h>
#include <ThingsBoard.h>
#include <ModbusMaster.h>
#include <Anomaly_Detection_inferencing.h>

#include "edge-impulse-sdk/tensorflow/lite/micro/all_ops_resolver.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/micro_error_reporter.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/micro_interpreter.h"
#include "edge-impulse-sdk/tensorflow/lite/micro/system_setup.h"
#include "edge-impulse-sdk/tensorflow/lite/schema/schema_generated.h"

const int SAMPLES = 5;
const float ALPHA = 0.2;
float currentEmaMoisture = 0.0;
bool firstRun = true;

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

#define TOKEN "YOUR_COREIOT_DEVICE_TOKEN"
#define COREIOT_SERVER "app.coreiot.io"
#define COREIOT_PORT 1883

WiFiClient wifiClient;
Arduino_MQTT_Client mqttClient(wifiClient);
ThingsBoard tb(mqttClient);

#define RS485_RX 6
#define RS485_TX 7
#define RS485_DE_RE 4

HardwareSerial mySerial(2);
ModbusMaster node;

unsigned long lastSend = 0;

void preTransmission() {
  digitalWrite(RS485_DE_RE, HIGH);
}

void postTransmission() {
  digitalWrite(RS485_DE_RE, LOW);
}

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

static float features[4] = {0};

int raw_feature_get_data(size_t offset, size_t length, float *out_ptr) {
  memcpy(out_ptr, features + offset, length * sizeof(float));
  return 0;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");

  pinMode(RS485_DE_RE, OUTPUT);
  digitalWrite(RS485_DE_RE, LOW);
  mySerial.begin(9600, SERIAL_8N1, RS485_RX, RS485_TX);

  node.begin(0x11, mySerial);
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  Serial.println("Modbus RTU + CoreIoT start...");
}

void loop() {
  if (!tb.connected()) {
    Serial.print("Connecting to CoreIoT...");

    if (!tb.connect(COREIOT_SERVER, TOKEN, COREIOT_PORT)) {
      Serial.println(" Failed!");
      delay(2000);
      return;
    }

    Serial.println(" Connected!");
  }

  if (millis() - lastSend > 5000) {
    lastSend = millis();

    uint16_t rawBuffer[SAMPLES];
    int validCount = 0;

    Serial.print("Sampling: ");

    for (int i = 0; i < SAMPLES; i++) {
      uint8_t result = node.readHoldingRegisters(0x0013, 1);

      if (result == node.ku8MBSuccess) {
        uint16_t val = node.getResponseBuffer(0);

        if (val <= 1000) {
          rawBuffer[validCount] = val;
          validCount++;
          Serial.print(val);
          Serial.print(" ");
        }
      } else {
        Serial.print("Err ");
      }

      delay(50);
    }

    Serial.println();

    if (validCount > 0) {
      sortArray(rawBuffer, validCount);
      uint16_t medianVal = rawBuffer[validCount / 2];

      Serial.printf("Median Value: %u\n", medianVal);

      if (firstRun) {
        currentEmaMoisture = medianVal;
        firstRun = false;
      } else {
        currentEmaMoisture = (ALPHA * medianVal) + ((1.0 - ALPHA) * currentEmaMoisture);
      }

      float moisture = currentEmaMoisture / 10;

      Serial.printf("Filtered (EMA): %.2f\n", moisture);

      tb.sendTelemetryData("moisture", moisture);

      features[0] = temperature;
      features[1] = moisture;

      if (sizeof(features) / sizeof(float) != EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE) {
        ei_printf("The size of your 'features' array is not correct. Expected %lu items, but had %lu\n",
                  EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE, sizeof(features) / sizeof(float));
        delay(1000);
        return;
      }

      ei_impulse_result_t result = { 0 };

      signal_t features_signal;
      features_signal.total_length = sizeof(features) / sizeof(features[0]);
      features_signal.get_data = &raw_feature_get_data;

      EI_IMPULSE_ERROR res = run_classifier(&features_signal, &result, false);

      ei_printf("run_classifier returned: %d\n", res);

      if (res != 0) return;

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

      for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
        ei_printf("    %s: %.5f\n", result.classification[ix].label, result.classification[ix].value);
      }

#if EI_CLASSIFIER_HAS_ANOMALY == 1
      ei_printf("    anomaly score: %.3f\n", result.anomaly);
      tb.sendTelemetryData("anomaly_score", result.anomaly);
#endif

    } else {
      Serial.println("Read failed all samples!");
    }
  }

  tb.loop();
}