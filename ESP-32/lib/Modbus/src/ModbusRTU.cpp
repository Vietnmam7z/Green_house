#include "ModbusRTU.h"

ModbusRTU::ModbusRTU(HardwareSerial &serial, uint32_t baudrate, uint32_t timeout)
    : uart(serial), timeout(timeout) {
    uart.begin(baudrate);
}

void ModbusRTU::calculateCRC(const uint8_t *data, size_t length, uint8_t *crcLow, uint8_t *crcHigh) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x0001) {
                crc >>= 1;
                crc ^= 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    *crcLow = crc & 0xFF;
    *crcHigh = (crc >> 8) & 0xFF;
}

void ModbusRTU::sendRequest(uint8_t slaveAddr, uint8_t functionCode, uint16_t registerAddr, uint16_t registerCount) {
    uint8_t frame[8];
    frame[0] = slaveAddr;
    frame[1] = functionCode;
    frame[2] = (registerAddr >> 8) & 0xFF;
    frame[3] = registerAddr & 0xFF;
    frame[4] = (registerCount >> 8) & 0xFF;
    frame[5] = registerCount & 0xFF;

    uint8_t crcLow, crcHigh;
    calculateCRC(frame, 6, &crcLow, &crcHigh);
    frame[6] = crcLow;
    frame[7] = crcHigh;

    uart.write(frame, 8);
}

bool ModbusRTU::readResponse(uint8_t *buffer, size_t expectedLength) {
    size_t index = 0;
    unsigned long start = millis();
    while (index < expectedLength) {
        if (uart.available()) {
            buffer[index++] = uart.read();
        }
        if (millis() - start > timeout) {
            return false;
        }
    }
    return true;
}

bool ModbusRTU::readHoldingRegisters(uint8_t slaveAddr, uint8_t funcCode, uint16_t registerAddr, uint16_t registerCount, uint16_t *outData) {
    sendRequest(slaveAddr, funcCode, registerAddr, registerCount);
    size_t expectedBytes = 5 + 2 * registerCount;
    uint8_t response[256];
    if (!readResponse(response, expectedBytes)) return false;

    for (uint16_t i = 0; i < registerCount; i++) {
        outData[i] = (response[4 + i*2] << 8) | response[3 + i*2];
    }
    return true;
}

bool ModbusRTU::readFloat(uint8_t slaveAddr, uint8_t funcCode, uint16_t registerAddr, float &outValue, bool bigEndian) {
    sendRequest(slaveAddr, funcCode, registerAddr, 2);
    size_t expectedBytes = 5 + 4;
    uint8_t response[256];
    if (!readResponse(response, expectedBytes)) return false;

    uint8_t raw[4];
    raw[0] = response[3];
    raw[1] = response[4];
    raw[2] = response[5];
    raw[3] = response[6];

    if (!bigEndian) {
        outValue = *((float*)raw);
    } else {
        uint8_t swapped[4] = { raw[1], raw[0], raw[3], raw[2] };
        outValue = *((float*)swapped);
    }
    return true;
}

bool ModbusRTU::readRawBytes(uint8_t slaveAddr, uint8_t funcCode, uint16_t registerAddr, uint16_t registerCount, uint8_t *outData) {
    sendRequest(slaveAddr, funcCode, registerAddr, registerCount);
    size_t expectedBytes = 5 + 2 * registerCount;
    uint8_t response[256];
    if (!readResponse(response, expectedBytes)) return false;

    for (uint16_t i = 0; i < registerCount * 2; i++) {
        outData[i] = response[3 + i];
    }
    return true;
}