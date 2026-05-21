import streamlit as st

st.set_page_config(page_title="Digital TWIN — Motor", layout="wide")

st.title("Digital TWIN — Monitoramento de Motor")
st.markdown("""
Bem-vindo ao sistema de monitoramento em tempo real via **ESP32 + MPU6050**.

### Páginas disponíveis
| Página | Descrição |
|--------|-----------|
| 📊 Dashboard | Vibração RMS em tempo real com limites ISO 10816 |
| 🔬 Espectral | Análise FFT das leituras de vibração |

### Como iniciar
```
# Com hardware (ESP32 conectado via USB):
python serial_reader.py

# Sem hardware (simulação):
python serial_reader.py --simulate
```

### Classificação ISO 10816 — Classe I
| Zona | Vibração RMS | Significado |
|------|-------------|-------------|
| ✅ OK | < 1.8 mm/s | Operação normal |
| ⚠️ Alerta | 1.8 – 4.5 mm/s | Monitorar — manutenção planejada |
| 🚨 Alarme | > 4.5 mm/s | Parada imediata recomendada |
""")
