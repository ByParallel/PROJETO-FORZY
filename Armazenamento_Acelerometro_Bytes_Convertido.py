import serial
import struct
import time
from datetime import datetime
import csv
import os

# Configurações da porta serial
porta = 'COM3'         # Altere conforme necessário
baudrate = 115200
escala_lsb = 8192.0     # Para ±4g (1g = 8192 LSB)

# Abre a porta serial
ser = serial.Serial(porta, baudrate, timeout=1)

# Cria pasta "dados" se não existir
os.makedirs("dados", exist_ok=True)

# Gera nome do arquivo com data e hora
hora_atual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nome_arquivo = f"dados/dados_{hora_atual}.csv"

# Cria o arquivo CSV com cabeçalho
with open(nome_arquivo, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'AX_g', 'AY_g', 'AZ_g'])

print(f"Lendo dados do MPU6050 e salvando em: {nome_arquivo}\n")

# Contador de amostras por segundo
contador = 0
inicio_segundo = time.time()

while True:
    byte = ser.read(1)  # Aguarda start byte
    if byte == b'\xAA':
        pacote = ser.read(6)
        if len(pacote) == 6:
            ax, ay, az = struct.unpack('<hhh', pacote)

            # Converte para g
            ax_g = ax / escala_lsb
            ay_g = ay / escala_lsb
            az_g = az / escala_lsb

            # Timestamp com hora legível
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]

            # Exibe no terminal
            print(f"{timestamp} | AX={ax_g} g  AY={ay_g} g  AZ={az_g} g")

            # Salva no arquivo dentro da pasta "dados"
            with open(nome_arquivo, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, ax_g, ay_g, az_g])

            contador += 1

    # A cada segundo, exibe taxa de amostragem
    if time.time() - inicio_segundo >= 1.0:
        print(f"→ Taxa de dados: {contador} amostras/segundo\n")
        contador = 0
        inicio_segundo = time.time()
