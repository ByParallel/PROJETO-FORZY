"""Gerador de dados simulados — usado apenas com --simulate ou em testes."""
import random
import math
from datetime import datetime


def gerar_leitura_simulada(t: float = 0.0) -> dict:
    """Simula uma leitura do ESP32 com padrão oscilatório realista."""
    freq_hz = 49.8 + random.gauss(0, 0.1)
    base_vib = 1.2 + 0.8 * math.sin(t / 30)  # vibração varia lentamente
    noise = random.gauss(0, 0.15)
    vibracao = max(0.05, base_vib + noise)

    ax_rms = vibracao * 0.012
    ay_rms = vibracao * 0.008
    az_rms = vibracao * 0.005
    mag_rms = math.sqrt(ax_rms**2 + ay_rms**2 + az_rms**2)

    if vibracao < 1.8:
        flag = 0
    elif vibracao < 4.5:
        flag = 1
    else:
        flag = 2

    return {
        "fonte": "simulado",
        "temperatura_c": round(45.0 + random.gauss(0, 1.5), 2),
        "vibracao_mm_s": round(vibracao, 4),
        "corrente_a": round(4.2 + random.gauss(0, 0.1), 3),
        "tensao_v": round(220.0 + random.gauss(0, 2), 1),
        "rpm": round(2980 + random.gauss(0, 5), 1),
        "fator_potencia": round(0.92 + random.gauss(0, 0.01), 3),
        "coletado_em": datetime.utcnow().isoformat(),
        "flag_anomalia": flag,
        "ax_rms": round(ax_rms, 6),
        "ay_rms": round(ay_rms, 6),
        "az_rms": round(az_rms, 6),
        "mag_rms": round(mag_rms, 6),
        "freq_hz": round(freq_hz, 2),
        "gx_rms": round(random.gauss(0, 0.05), 4),
        "gy_rms": round(random.gauss(0, 0.05), 4),
        "gz_rms": round(random.gauss(0, 0.05), 4),
        "peaks": [round(freq_hz, 1), round(freq_hz * 2, 1)],
    }
