#ifndef MODBUS_RTU_H
#define MODBUS_RTU_H

#include <Arduino.h>

class ModbusRTU {
public:
    ModbusRTU(HardwareSerial &serial = Serial1, uint32_t baudrate = 9600, uint32_t timeout = 250);

    void sendRequest(uint8_t slaveAddr, uint8_t functionCode, uint16_t registerAddr, uint16_t registerCount);
    bool readResponse(uint8_t *buffer, size_t expectedLength);

    bool readHoldingRegisters(uint8_t slaveAddr, uint8_t funcCode, uint16_t registerAddr, uint16_t registerCount, uint16_t *outData);
    bool readFloat(uint8_t slaveAddr, uint8_t funcCode, uint16_t registerAddr, float &outValue, bool bigEndian = true);
    bool readRawBytes(uint8_t slaveAddr, uint8_t funcCode, uint16_t registerAddr, uint16_t registerCount, uint8_t *outData);

private:
    HardwareSerial &uart;
    uint32_t timeout;

    void calculateCRC(const uint8_t *data, size_t length, uint8_t *crcLow, uint8_t *crcHigh);
};

#endif