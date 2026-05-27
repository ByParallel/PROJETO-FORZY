# IMS · Forzy — Industrial Monitoring System

> **Sprint 2** — Dashboard consolidado, navegação customizada, monitoramento dual-motor em tempo real

Sistema de monitoramento industrial de bombas centrífugas construído com Python e Streamlit. Monitora 2 motores com dados históricos do dataset Forzy, análise espectral FFT, visualização SCADA 2D/3D e integração com ESP32 + MPU6050 em tempo real.

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Interface | Streamlit 1.45.1 |
| Graficos | Plotly 5+ (WebGL) |
| Dados | Pandas + forzy.csv + SQLite |
| Hardware | ESP32-CAM + MPU6050 (I2C) |
| Serial | PySerial (auto-detect VID/PID) |
| Linguagem | Python 3.10+ |

---

## Como Rodar

```powershell
pip install -r requirements.txt
python -m streamlit run 1_Inicio.py
```

**Com ESP32 conectado:**
```powershell
# Terminal 1 — coletor serial
python Armazenamento_Acelerometro_Bytes_Convertido.py

# Terminal 2 — dashboard
python -m streamlit run 1_Inicio.py
```

Acesse: **http://localhost:8501**

---

## Estrutura de Navegacao

```
Inicio
Dashboard
  Monitoramento   — Motor 1 e Motor 2 ao vivo (dataset ou simulado)
  Espectral       — FFT + espectrograma parametrizado pelo dado real
  Operacional     — Analise historica completa do dataset Forzy
  Historico       — Player/timelapse animado
SCADA             — Planta 2D + modelo 3D (STP real) com player
IoT · ESP32       — Leitura ao vivo via USB-Serial
```

---

## Dashboard Consolidado

### Monitoramento
- Motor 1 e Motor 2 lado a lado com gauges (velocidade, aceleracao, temperatura)
- Health score e banner de status ISO 10816 por motor
- Graficos de historico recente (janela deslizante de 120 frames)
- Fonte selecionavel: Dataset Forzy (player automatico) ou Simulado
- Auto-refresh configuravel (intervalo + passo de frames)

### Espectral
- FFT com fs=1000 Sa/s, amplitude parametrizada pelo RMS real do dataset
- Espectrograma por janelas sequenciais
- Marcacao de harmonicas RPM e bandas de falha
- Fonte: Dataset Forzy ou Simulado

### Operacional
- Timeline, analise estatistica, comparacao M1 x M2, eventos e anomalias

### Historico
- Player animado com controle de velocidade

---

## ESP32 + MPU6050

```
ESP32-CAM (AI Thinker) — COM auto-detectada
MPU6050 (I2C) → AX, AY, AZ (g) + GX, GY, GZ (dps)
Taxa: 5 Sa/s (delay 200 ms no firmware)
Saida serial: AX (g): 0.012 | AY (g): 0.974 | ...
```

O coletor serial salva em `dados/dados_YYYY-MM-DD_HH-MM-SS.csv`. A pagina IoT le o CSV mais recente a cada 2s e remove o componente DC de gravidade antes de calcular o RMS dinamico.

**Importante:** porta aberta com `rts=False, dtr=False` — caso contrario o ESP32 entra em modo bootloader.

---

## Classificacao ISO 10816

| Zona | Velocidade RMS | Acao |
|------|---------------|------|
| Normal | < 1,8 mm/s | Operacao normal |
| Alerta | 1,8 – 4,5 mm/s | Monitorar, planejar manutencao |
| Alarme | > 4,5 mm/s | Parada imediata recomendada |

---

## Dataset Forzy

`data/forzy.csv` — separador `;`, `skiprows=3`

| Coluna | Unidade | Descricao |
|--------|---------|-----------|
| timestamp | — | Data/hora da medicao |
| m1_vel | mm/s | Velocidade RMS Motor 1 |
| m1_acel | g | Aceleracao RMS Motor 1 |
| m1_temp | C | Temperatura Motor 1 |
| m2_vel | mm/s | Velocidade RMS Motor 2 |
| m2_acel | g | Aceleracao RMS Motor 2 |
| m2_temp | C | Temperatura Motor 2 |

Os valores sao RMS agregados (nao waveform bruto). A FFT espectral usa esses valores para parametrizar um sinal sintetico em 1000 Sa/s.

---

## Licenca

Projeto academico — uso livre para fins educacionais.  
Sprint 2 · Forzy–Promon · 2026
