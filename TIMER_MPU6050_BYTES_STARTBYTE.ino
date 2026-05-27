#include <Wire.h>
#include <MPU6050.h>
#include "esp_timer.h"

MPU6050 mpu;

#define ACCEL_SCALE_FACTOR 8192.0  // ±4g
#define NUM_SAMPLES 100
#define START_BYTE 0xAA
#define AMOSTRAGEM_US 3333  // 300 Hz

float offsetX = 0.0, offsetY = 0.0, offsetZ = 0.0;

// Função chamada pelo timer
void coletarDadosTimer(void* arg) {
  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  // Aplica offset
  ax += offsetX * ACCEL_SCALE_FACTOR;
  ay += offsetY * ACCEL_SCALE_FACTOR;
  az += offsetZ * ACCEL_SCALE_FACTOR;

  // Envia pacote binário: [START][AX][AY][AZ]
  Serial.write(START_BYTE);
  Serial.write((uint8_t*)&ax, 2);
  Serial.write((uint8_t*)&ay, 2);
  Serial.write((uint8_t*)&az, 2);
}

void setup() {
  Serial.begin(115200);
  Wire.begin();

  mpu.initialize();
  if (!mpu.testConnection()) {
    while (1);  // trava se falhar
  }

  mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_4);
  calibrarMPU();

  // Configura timer usando ESP_TIMER_TASK (modo seguro)
  const esp_timer_create_args_t args = {
    .callback = &coletarDadosTimer,
    .arg = nullptr,
    .dispatch_method = ESP_TIMER_TASK,
    .name = "coleta_timer"
  };

  esp_timer_handle_t periodic_timer;
  esp_timer_create(&args, &periodic_timer);
  esp_timer_start_periodic(periodic_timer, AMOSTRAGEM_US);  // 300 Hz
}

void loop() {
  // loop vazio, toda leitura é feita pelo timer
}

void calibrarMPU() {
  int16_t ax, ay, az;
  float ax_g[NUM_SAMPLES], ay_g[NUM_SAMPLES], az_g[NUM_SAMPLES];

  for (int i = 0; i < NUM_SAMPLES; i++) {
    mpu.getAcceleration(&ax, &ay, &az);
    ax_g[i] = ax / ACCEL_SCALE_FACTOR;
    ay_g[i] = ay / ACCEL_SCALE_FACTOR;
    az_g[i] = az / ACCEL_SCALE_FACTOR;
    delay(20);
  }

  ordenar(ax_g, NUM_SAMPLES);
  ordenar(ay_g, NUM_SAMPLES);
  ordenar(az_g, NUM_SAMPLES);

  int start = NUM_SAMPLES * 0.1;
  int end = NUM_SAMPLES * 0.9;
  float somaX = 0, somaY = 0, somaZ = 0;

  for (int i = start; i < end; i++) {
    somaX += ax_g[i];
    somaY += ay_g[i];
    somaZ += az_g[i];
  }

  int n = end - start;
  offsetX = -somaX / n;
  offsetY = -somaY / n;
  offsetZ = 1.0 - (somaZ / n);
}

void ordenar(float *v, int n) {
  for (int i = 0; i < n - 1; i++) {
    for (int j = 0; j < n - i - 1; j++) {
      if (v[j] > v[j + 1]) {
        float temp = v[j];
        v[j] = v[j + 1];
        v[j + 1] = temp;
      }
    }
  }
}
