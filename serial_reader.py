"""
serial_reader.py — Lê JSON do ESP32 via USB-Serial e persiste no banco.

Uso:
    python serial_reader.py                    # porta auto-detectada
    python serial_reader.py --port COM3        # porta explícita
    python serial_reader.py --simulate         # sem hardware, usa mock_data
    python serial_reader.py --simulate --rate 0.5  # simula a cada 0.5s
"""

import argparse
import json
import math
import sys
import time
from datetime import datetime

import serial
import serial.tools.list_ports

import database
from utils.mock_data import gerar_leitura_simulada

ATIVO_ID = "MTR-MPU-01"
BAUD = 115200

# ISO 10816 Classe I (motores pequenos <15 kW)
ISO_OK = 1.8      # mm/s RMS — abaixo: OK
ISO_ALERTA = 4.5  # mm/s RMS — acima: ALARME


def _flag_iso(vibracao_mm_s: float) -> int:
    if vibracao_mm_s < ISO_OK:
        return 0
    if vibracao_mm_s < ISO_ALERTA:
        return 1
    return 2


def _accel_to_velocity(a_rms_g: float, freq_hz: float) -> float:
    """Converte aceleração RMS (g) para velocidade RMS (mm/s)."""
    if freq_hz <= 0:
        return 0.0
    return (a_rms_g * 9806.65) / (2 * math.pi * freq_hz)


def _detect_port() -> str | None:
    """Detecta automaticamente porta CP210x ou CH340."""
    keywords = ["CP210", "CH340", "USB-SERIAL", "UART", "Silicon"]
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").upper() + (p.manufacturer or "").upper()
        if any(k.upper() in desc for k in keywords):
            print(f"[auto] Porta detectada: {p.device} — {p.description}")
            return p.device
    # fallback: primeira porta COM disponível
    if ports:
        p = ports[0]
        print(f"[auto] Usando primeira porta disponível: {p.device}")
        return p.device
    return None


def _ensure_ativo():
    criado = database.cadastrar_ativo(
        ATIVO_ID,
        descricao="Motor acoplado ao MPU6050 via ESP32",
        localizacao="Bancada de testes",
    )
    if criado:
        print(f"[db] Ativo '{ATIVO_ID}' cadastrado.")
    else:
        print(f"[db] Ativo '{ATIVO_ID}' já existe.")


def _processar_payload(payload: dict) -> dict:
    """Transforma o JSON do ESP32 no formato do banco."""
    freq = payload.get("freq_hz", 50.0) or 50.0
    mag_rms_g = payload.get("mag_rms", 0.0)
    vibracao = _accel_to_velocity(mag_rms_g, freq)

    return {
        "fonte": "esp32",
        "temperatura_c": payload.get("temp_c"),
        "vibracao_mm_s": round(vibracao, 4),
        "corrente_a": None,
        "tensao_v": None,
        "rpm": None,
        "fator_potencia": None,
        "coletado_em": datetime.utcnow().isoformat(),
        "flag_anomalia": _flag_iso(vibracao),
        "ax_rms": payload.get("ax_rms"),
        "ay_rms": payload.get("ay_rms"),
        "az_rms": payload.get("az_rms"),
        "mag_rms": mag_rms_g,
        "freq_hz": freq,
        "gx_rms": payload.get("gx_rms"),
        "gy_rms": payload.get("gy_rms"),
        "gz_rms": payload.get("gz_rms"),
        "peaks": payload.get("peaks", []),
    }


def run_serial(port: str):
    print(f"[serial] Conectando em {port} @ {BAUD} baud…")
    with serial.Serial(port, BAUD, timeout=2) as ser:
        print("[serial] Conectado. Aguardando dados do ESP32…\n")
        while True:
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if not line or not line.startswith("{"):
                    continue
                payload = json.loads(line)
                dados = _processar_payload(payload)
                row_id = database.insert_leitura(ATIVO_ID, dados)
                flag_str = ["OK", "ALERTA", "ALARME"][dados["flag_anomalia"]]
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"vib={dados['vibracao_mm_s']:.3f} mm/s  "
                    f"freq={dados['freq_hz']:.1f} Hz  "
                    f"temp={dados['temperatura_c']}°C  "
                    f"→ {flag_str}  (id={row_id})"
                )
            except json.JSONDecodeError:
                pass
            except KeyboardInterrupt:
                print("\n[serial] Interrompido pelo usuário.")
                break
            except Exception as exc:
                print(f"[serial] Erro: {exc}", file=sys.stderr)
                time.sleep(1)


def run_simulate(rate: float):
    print(f"[simulate] Modo simulação ativo (intervalo={rate}s)\n")
    t = 0.0
    while True:
        try:
            dados = gerar_leitura_simulada(t)
            row_id = database.insert_leitura(ATIVO_ID, dados)
            flag_str = ["OK", "ALERTA", "ALARME"][dados["flag_anomalia"]]
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"vib={dados['vibracao_mm_s']:.3f} mm/s  "
                f"freq={dados['freq_hz']:.1f} Hz  "
                f"temp={dados['temperatura_c']}°C  "
                f"→ {flag_str}  (id={row_id})"
            )
            t += rate
            time.sleep(rate)
        except KeyboardInterrupt:
            print("\n[simulate] Interrompido.")
            break


def main():
    parser = argparse.ArgumentParser(description="Leitor serial ESP32 → SQLite")
    parser.add_argument("--port", help="Porta COM explícita (ex: COM3)")
    parser.add_argument("--simulate", action="store_true", help="Usa dados simulados")
    parser.add_argument("--rate", type=float, default=1.0, help="Intervalo simulação (s)")
    args = parser.parse_args()

    _ensure_ativo()

    if args.simulate:
        run_simulate(args.rate)
        return

    port = args.port or _detect_port()
    if not port:
        print("[erro] Nenhuma porta serial encontrada. Use --port COM? ou --simulate.")
        sys.exit(1)

    run_serial(port)


if __name__ == "__main__":
    main()
