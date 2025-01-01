#include <Wire.h> 
#include <Adafruit_ADS1X15.h> 
#include <Adafruit_MPU6050.h> 
#include <BLEDevice.h> 
#include <BLEUtils.h> 
#include <BLEServer.h> 

Adafruit_ADS1115 ads1; 
Adafruit_ADS1115 ads2; 
Adafruit_MPU6050 mpu; 

#define MPU6050_ADDRESS 0X68 
#define SERVICE_UUID "12345678-1234-5678-1234-56789abcdef0" 
#define CHARACTERISTIC_UUID_ADC "12345678-1234-5678-1234-56789abcdef1" 
#define CHARACTERISTIC_UUID_ACCEL "12345678-1234-5678-1234-56789abcdef2" 
#define CHARACTERISTIC_UUID_ROT "12345678-1234-5678-1234-56789abcdef3" 

BLECharacteristic *adcCharacteristic; 
BLECharacteristic *accelCharacteristic; 
BLECharacteristic *rotCharacteristic; 

void setup() { 
  Serial.begin(115200); 
  // Initialize I2C with Fast Mode 
  Wire.begin(); 
  Wire.setClock(400000); 
  
  // Initialize ADS1115 
  if (!ads1.begin(0x48)) { 
    Serial.println("Failed to initialize ADS1."); 
    while (1); 
  } 
  if (!ads2.begin(0x49)) { 
    Serial.println("Failed to initialize ADS2."); 
    while (1); 
  } 
  ads1.setGain(GAIN_ONE); 
  ads2.setGain(GAIN_ONE); 
  ads1.setDataRate(RATE_ADS1115_860SPS); 
  ads2.setDataRate(RATE_ADS1115_860SPS); 
  
  // Initialize MPU6050 
  if (!mpu.begin()) { 
    Serial.println("Failed to find MPU6050"); 
    while(1); 
  } 
  mpu.setAccelerometerRange(MPU6050_RANGE_2_G); 
  mpu.setGyroRange(MPU6050_RANGE_250_DEG); 
  mpu.setFilterBandwidth(MPU6050_BAND_260_HZ); 
  
  // Configure MPU6050 sample rate to 1kHz 
  Wire.beginTransmission(MPU6050_ADDRESS); 
  Wire.write(0x19); // Sample Rate Divider register 
  Wire.write(0x00); // Set to 1kHz Wire. 
  Wire.endTransmission(); 
  
  // BLE Initialization 
  BLEDevice::init("ESP32_Sensor_Module"); 
  BLEServer *server = BLEDevice::createServer(); 
  
  // Create BLE Service 
  BLEService *service = server->createService(SERVICE_UUID); 
  
  // Create Characteristics 
  adcCharacteristic = service->createCharacteristic( CHARACTERISTIC_UUID_ADC, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY); 
  accelCharacteristic = service->createCharacteristic( CHARACTERISTIC_UUID_ACCEL, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY); 
  rotCharacteristic = service->createCharacteristic( CHARACTERISTIC_UUID_ROT, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY); 
  
  // Start the Service 
  service->start(); 
  
  // Start BLE Advertising 
  BLEAdvertising *advertising = BLEDevice::getAdvertising(); 
  advertising->addServiceUUID(SERVICE_UUID); 
  advertising->start(); 
  Serial.println("BLE setup complete. Waiting for connections..."); 
} 

int16_t readADC(Adafruit_ADS1115& ads, int channel) { 
  return ads.readADC_SingleEnded(channel); 
} 

void readMPU(uint8_t* buffer) { 
  Wire.beginTransmission(MPU6050_ADDRESS); 
  Wire.write(0x3B); // Start reading at ACCEL_XOUT_H 
  Wire.endTransmission(false); // Restart for burst read 
  Wire.requestFrom(MPU6050_ADDRESS, 14); // Read 14 bytes (accel + gyro + temp) 
  for (int i = 0; i < 14; i++) { 
    buffer[i] = Wire.read(); 
  } 
} 

void loop() { 
  // Read ADC values 
  int16_t adcValues[8]; 
  for (int i = 0; i < 4; i++) { 
    adcValues[i] = readADC(ads1, i); 
    adcValues[i + 4] = readADC(ads2, i); 
  } 
  
  // Send ADC values 
  adcCharacteristic->setValue((uint8_t*)adcValues, sizeof(adcValues)); 
  adcCharacteristic->notify(); 
  
  // Read and send MPU6050 data 
  uint8_t mpuBuffer[14]; 
  readMPU(mpuBuffer); 
  accelCharacteristic->setValue(mpuBuffer, 6); 
  accelCharacteristic->notify(); 
  rotCharacteristic->setValue(mpuBuffer + 8, 6); 
  rotCharacteristic->notify();
   
  delay(100); // Add delay to avoid flooding BLE notifications }
}