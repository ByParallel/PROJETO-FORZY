# Digital TWIN — Monitoramento Industrial em Tempo Real

> **Sprint 2** — Visualização Operacional, Representação de Ativos e Integração com Hardware Real (ESP32 + MPU6050)

Sistema de gêmeo digital industrial construído com Python, Streamlit e SQLite. Monitora motores elétricos em tempo real via sensor inercial MPU6050 acoplado a um ESP32, com análise de vibração conforme **ISO 10816**.

---

## Demonstração

### Dashboard Operacional
O dashboard exibe seis sensores em tempo real com gauges e gráficos históricos. Alertas visuais são acionados automaticamente quando leituras ultrapassam limites operacionais (ex.: temperatura > 85 °C, corrente > 125% nominal).

```
┌─────────────────────────────────────────────────────────────────┐
│  🌡 Temperatura   ⚡ Tensão   〰 Corrente   🔄 RPM   📳 Vibração │
│     62.3 °C       220 V       4.2 A       2980     1.24 mm/s   │
├─────────────────────────────────────────────────────────────────┤
│  [Gauge Temp] [Gauge Corrente] [Gauge Vibração] [Gauge FP]      │
├─────────────────────────────────────────────────────────────────┤
│  Histórico ─────────────────────────────────────────────────── │
│  [Tendências] [Comparação] [Anomalias]                          │
└─────────────────────────────────────────────────────────────────┘
```

### Dashboard de Vibração (ESP32 real-time)
Alimentado diretamente pelo ESP32 via USB-Serial. Auto-refresh a cada 2 s.

```
Status ISO 10816:  ✅ OK — 1.24 mm/s
                   ⚠️  ALERTA — 2.61 mm/s
                   🚨  ALARME — 5.03 mm/s

Faixas coloridas no gráfico temporal:
  Verde  < 1.8 mm/s  │  Amarelo 1.8–4.5 mm/s  │  Vermelho > 4.5 mm/s
```

### Análise Espectral (FFT)
Página dedicada com FFT sobre janelas históricas, pico dominante marcado e histórico de frequências ao longo do tempo.

---

## Stack Tecnológico

| Camada | Tecnologia |
|--------|------------|
| Interface | Streamlit 1.35+ |
| Gráficos | Plotly 5+ |
| Dados | SQLite + Pandas |
| Hardware | ESP32 + MPU6050 (I2C) |
| Serial | PySerial |
| Linguagem | Python 3.10+ |

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        ESP32 (firmware)                     │
│  MPU6050 → 200 Hz sampling → RMS + FFT → JSON via Serial   │
└───────────────────────────┬─────────────────────────────────┘
                            │ USB-Serial (115200 baud)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    serial_reader.py                         │
│  • Auto-detecta porta CP210x / CH340                        │
│  • Converte aceleração RMS (g) → velocidade RMS (mm/s)      │
│  • Classifica ISO 10816 (OK / Alerta / Alarme)              │
│  • Persiste em SQLite via database.py                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   data/motores.db (SQLite)                  │
│  tabelas: ativos, leituras                                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Dashboard                     │
│  1_Inicio · 2_Dashboard · 3_Espectral                       │
│  auto-refresh 2 s · gráficos Plotly interativos             │
└─────────────────────────────────────────────────────────────┘
```

---

## Estrutura do Projeto

```
digital_twin/
├── 1_Inicio.py               # Página inicial
├── app.py                    # Entrada principal (legado Sprint 2)
├── database.py               # Camada de dados (SQLite)
├── serial_reader.py          # Leitor USB-Serial + modo simulação
├── requirements.txt
├── executar.bat              # Launcher Windows (abre tudo com 1 clique)
│
├── firmware/
│   └── esp32_mpu6050_rms.ino # Firmware ESP32 — 200 Hz, RMS, JSON
│
├── pages/
│   ├── 1_Navegacao.py        # Hierarquia Planta → Área → Ativo
│   ├── 2_Dashboard.py        # Sensores em tempo real (vibração ISO 10816)
│   ├── 3_Espectral.py        # Análise FFT de vibração
│   ├── 3_Cadastro.py         # CRUD de ativos
│   ├── 4_RPA.py              # Central de automações RPA
│   └── 5_Pipeline.py         # Pipeline Placa → Cadastro
│
├── rpa/
│   ├── tag_association.py    # RPA: associação TAG/Localização
│   ├── record_updater.py     # RPA: atualização de registros
│   └── nameplate_pipeline.py # RPA: pipeline placa do motor
│
├── utils/
│   ├── mock_data.py          # Gerador de dados simulados realistas
│   └── charts.py             # Componentes visuais (Plotly)
│
└── data/
    ├── digital_twin.db       # Banco do sistema de ativos
    └── motores.db            # Banco de leituras do ESP32
```

---

## Como Rodar

### Pré-requisitos

- Python 3.10+
- Driver USB-Serial instalado: [CP210x](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers) ou CH340
- Arduino IDE (para gravar firmware no ESP32)

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Gravar firmware no ESP32

1. Abra `firmware/esp32_mpu6050_rms.ino` no Arduino IDE
2. Instale as bibliotecas pelo Library Manager:
   - `MPU6050` (ElectronicCats ou jrowberg/i2cdevlib)
   - `arduinoFFT` (opcional — descomente `#define USE_FFT` no firmware)
3. Selecione **ESP32 Dev Module** e a porta COM correta
4. Grave e abra o Serial Monitor para verificar o JSON:

```json
{"ax_rms":0.003821,"ay_rms":0.002104,"az_rms":0.001533,
 "mag_rms":0.004512,"freq_hz":49.80,"peaks":[49.8,99.6],
 "temp_c":38.24,"gx_rms":0.041,"gy_rms":0.038,"gz_rms":0.029}
```

### 3. Iniciar o sistema

**Opção A — Double-click (recomendado no Windows):**
```
executar.bat
```
O script pergunta se você quer usar hardware real ou simulação, sobe o `serial_reader.py` em segundo plano e abre o Streamlit.

**Opção B — Manual:**
```bash
# Terminal 1: leitor serial (ESP32 conectado)
python serial_reader.py

# Terminal 1 alternativo: modo simulação (sem hardware)
python serial_reader.py --simulate

# Terminal 2: dashboard
python -m streamlit run 1_Inicio.py
```

Acesse: **http://localhost:8501**

---

## Hardware

### Conexões ESP32 ↔ MPU6050

| MPU6050 | ESP32 |
|---------|-------|
| VCC | 3.3 V |
| GND | GND |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

> O MPU6050 está configurado em **±4g** (acelerômetro) e **±250°/s** (giroscópio), com filtro passa-baixa DLPF a 44 Hz — ideal para capturar vibração de motores até ~22 Hz.

### Princípio de funcionamento

O firmware coleta **200 amostras por segundo**, remove a componente DC (gravidade) calculando a média da janela, e obtém o **RMS de vibração dinâmica** de cada eixo. A velocidade de vibração em mm/s é calculada no `serial_reader.py` pela fórmula:

```
v_rms (mm/s) = (a_rms_g × 9806.65) / (2π × f_hz)
```

---

## Classificação ISO 10816 — Classe I

Motores de pequeno porte (< 15 kW):

| Zona | Vibração RMS | Ação |
|------|-------------|------|
| ✅ OK | < 1,8 mm/s | Operação normal |
| ⚠️ Alerta | 1,8 – 4,5 mm/s | Monitorar — planejar manutenção |
| 🚨 Alarme | > 4,5 mm/s | Parada imediata recomendada |

---

## Banco de Dados

### `leituras` (motores.db)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `ativo_id` | TEXT | Identificador do motor (ex: `MTR-MPU-01`) |
| `fonte` | TEXT | `esp32` ou `simulado` |
| `vibracao_mm_s` | REAL | Velocidade RMS de vibração |
| `temperatura_c` | REAL | Temperatura interna do MPU6050 |
| `freq_hz` | REAL | Frequência dominante de vibração |
| `ax_rms / ay_rms / az_rms` | REAL | Aceleração RMS por eixo (g) |
| `mag_rms` | REAL | Magnitude vetorial RMS (g) |
| `flag_anomalia` | INT | 0=OK · 1=Alerta · 2=Alarme |
| `coletado_em` | TEXT | Timestamp UTC da coleta |

### Hierarquia completa (digital_twin.db)

```
plantas ──< areas ──< ativos ──< leituras_sensores
                                 log_rpa
```

---

## Módulos da Sprint 2

| Módulo | Arquivo | Descrição |
|--------|---------|-----------|
| Início | `1_Inicio.py` | Visão geral e instruções |
| Navegação | `pages/1_Navegacao.py` | Hierarquia Planta → Área → Ativo com mapa |
| Dashboard | `pages/2_Dashboard.py` | Vibração ISO 10816 + sensores em tempo real |
| Espectral | `pages/3_Espectral.py` | FFT de vibração com pico dominante |
| Cadastro | `pages/3_Cadastro.py` | CRUD de ativos industriais |
| RPA | `pages/4_RPA.py` | Associação automática TAG/Localização |
| Pipeline | `pages/5_Pipeline.py` | OCR Placa → Normalização → Banco |

---

## Simulação (sem hardware)

Para desenvolver e testar sem o ESP32:

```bash
python serial_reader.py --simulate
# ou com intervalo personalizado:
python serial_reader.py --simulate --rate 0.5
```

O modo simulação gera leituras realistas com variação senoidal lenta de vibração, ruído gaussiano e temperaturas plausíveis — adequado para demonstrações e testes de UI.

---

## Licença

Projeto acadêmico — uso livre para fins educacionais.
