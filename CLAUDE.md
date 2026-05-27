# CLAUDE.md — IMS · Forzy Industrial Monitoring System

## Visão Geral

Sistema de monitoramento industrial de bombas centrífugas construído com Python e Streamlit. Exibe dados históricos de 2 motores via CSV, análise espectral FFT, visualização SCADA 2D/3D com modelo STP real, e interface de conexão IoT/ESP32.

## Como Rodar

```powershell
cd "C:\Users\gel\Desktop\ESP\PROJETO-FORZY"
pip install -r requirements.txt
python -m streamlit run 1_Inicio.py
# → http://localhost:8501
```

Com ESP32 conectado:
```powershell
# Terminal 1 — coletor serial (deixar rodando)
python Armazenamento_Acelerometro_Bytes_Convertido.py

# Terminal 2 — site
python -m streamlit run 1_Inicio.py
```

## Arquitetura

```
PROJETO-FORZY/
├── 1_Inicio.py              # Home — landing page, status geral, cards de navegação
├── pages/
│   ├── 2_Dashboard.py       # Dashboard consolidado (4 tabs: Monitoramento, Espectral, Operacional, Histórico)
│   ├── 3_SCADA.py           # Planta 2D (DWG renderizado) + Vista 3D (STP real) + player
│   ├── 4_IoT.py             # Interface de conexão ESP32 + leitura ao vivo real/simulada
│   ├── _2_Monitoramento.py  # (oculto — backup Sprint 1)
│   ├── _3_Espectral.py      # (oculto — backup Sprint 1)
│   ├── _4_Operacional.py    # (oculto — backup Sprint 1)
│   └── _5_Historico.py      # (oculto — backup Sprint 1)
├── utils/
│   ├── mock_data.py         # Gerador de dados simulados (4 modos de falha)
│   └── theme.py             # CSS global + sidebar_nav() — importar em toda página
├── data/
│   ├── forzy.csv            # Dataset histórico: 2 motores, ~7k linhas brutas
│   ├── bomba.png            # Modelo STP renderizado em vista de perfil (2 bombas)
│   ├── bomba_verts.npy      # Vértices tessellados do STP (float32)
│   ├── bomba_faces.npy      # Faces tesselladas do STP (int32)
│   └── motores.db           # SQLite para leituras do ESP32 (pode estar vazio)
├── dados/                   # CSVs gerados pelo coletor serial (dados_YYYY-MM-DD_HH-MM-SS.csv)
├── firmware/
│   ├── esp32_mpu6050_rms/
│   │   └── esp32_mpu6050_rms.ino        # Firmware com timer (300 Hz)
│   └── TIMER_MPU6050_BYTES_STARTBYTE/
│       └── TIMER_MPU6050_BYTES_STARTBYTE.ino  # Firmware binário alternativo
├── Armazenamento_Acelerometro_Bytes_Convertido.py  # Coletor serial ativo (auto-detecta porta, salva CSV)
├── database.py              # Camada SQLite (tabelas: ativos, leituras)
└── serial_reader.py         # Leitor USB-Serial legado (não usado ativamente)
```

## Navegação (Sprint 2)

A navegação lateral é **customizada** — o nav padrão do Streamlit está oculto. Toda página chama:

```python
from utils.theme import apply as _apply_theme, sidebar_nav as _snav
_apply_theme(); _snav("inicio")  # ou "dashboard", "scada", "iot"
```

Estrutura da sidebar:
- **Início**
- **Dashboard** (com sub-itens: Monitoramento, Espectral, Operacional, Histórico)
  - Sub-itens usam `st.button` + `st.switch_page` + `st.session_state["_dash_tab"]`
  - Dashboard lê `_dash_tab` e injeta JS para clicar no tab correto
- **SCADA**
- **IoT · ESP32**

**Nunca** usar `sidebar_header()` — substituída por `sidebar_nav()`.

## Dashboard Consolidado (`pages/2_Dashboard.py`)

4 tabs em uma única página:

### Tab 1 — Monitoramento
- Fonte selecionável: **Dataset Forzy** (player por frames) ou **Simulado** (mock_data)
- Autorefresh com intervalo e passo configuráveis — só ativo quando `_active_tab == 0`
- Seleção de tab via `st.query_params["tab"]` + JS click — preserva tab entre reruns
- Motor 1 e Motor 2 lado a lado: banner status, health score, KPIs, 3 gauges
- Gráficos de histórico recente (janela deslizante 120 frames): Vel, Acel, Temp

### Tab 2 — Espectral
- Fonte: Dataset Forzy (amplitude parametrizada pelo RMS real) ou Simulado
- FFT com fs=1000 Sa/s sintético — o forzy.csv contém RMS agregado (~1 Sa/s), não waveform
- Espectrograma por janelas sequenciais do dataset
- Harmônicas e bandas de falha configuráveis

### Tab 3 — Operacional
- Análise completa do dataset forzy.csv
- Sub-tabs: Timeline, Análise, Comparação, Eventos, Estatísticas

### Tab 4 — Histórico
- Player/timelapse animado do dataset

## Dados

### Dataset Forzy (`data/forzy.csv`)
- Separador `;`, 3 linhas de cabeçalho, `skiprows=3`
- Colunas usadas: `[0,3,4,5,6,7,8]` → `timestamp | m1_vel | m1_acel | m1_temp | m2_vel | m2_acel | m2_temp`
- Unidades: velocidade em **mm/s**, aceleração em **g**, temperatura em **°C**
- Valores são **RMS agregados** (não waveform bruto) — não fazer FFT direta neles

### Limiares ISO 10816 (padrão)
| Zona    | Velocidade RMS |
|---------|---------------|
| Normal  | < 1,8 mm/s    |
| Alerta  | 1,8–4,5 mm/s  |
| Alarme  | > 4,5 mm/s    |

## Tema e CSS

**Nunca** adicionar CSS inline em páginas individuais sem antes verificar `utils/theme.py`. Cores base:

```
fundo app:     #060d18
fundo card:    #0a1628
borda card:    #0f2a45
fundo sidebar: #080f1c
texto primário:    #e2eaf4
texto secundário:  #4a7a9b
azul accent:   #3498db / #7ec8e3
```

**Sem emojis** no projeto — decisão de estilo do Sprint 2.

## Modelo 3D (SCADA)

- **Arquivo fonte**: `C:\Users\gel\Downloads\ChallengeForzy-bomba-teste.stp`
- **Tessellação**: `cadquery` com tolerância 0.08mm → 14.932 vértices, 21.674 faces
- **Separação de cores**: faces com Z ≤ -1.8 = base/skid azul `#1e3d5c`; acima = máquina verde
- **Re-geração**:
```python
import cadquery as cq, numpy as np
shape = cq.importers.importStep(r"C:\Users\gel\Downloads\ChallengeForzy-bomba-teste.stp")
verts, faces = shape.val().tessellate(0.08)
V = np.array([[v.x,v.y,v.z] for v in verts]); V -= V.mean(axis=0)
scale = 10.0/(V.max()-V.min()); V *= scale
np.save("data/bomba_verts.npy", V.astype(np.float32))
np.save("data/bomba_faces.npy", np.array(faces).astype(np.int32))
```

## Performance — Regras Importantes

- **Nunca usar `shape="spline"` ou `smoothing`** em gráficos com > 500 pontos
- **Usar `go.Scattergl`** (WebGL) para séries temporais longas
- **Máx 3.000 pontos** nos gráficos — usar downsample
- **Flags de status** com `np.where` vetorizado, nunca `.apply(lambda)`
- **`yaxis` não pode estar tanto no dict compartilhado quanto no `update_layout`** — causa `multiple values for keyword argument`

## Modos de Falha Simulados (`utils/mock_data.py`)

| Modo | Assinatura |
|------|-----------|
| `normal` | 1x RPM pequeno, ruído baixo |
| `desbalanco` | 1x RPM dominante (±12%) |
| `cavitacao` | Banda larga + sub-harmônica |
| `desalinhamento` | 2x RPM dominante |

## Sensor Real

**Pepperl+Fuchs VIM32PL-E1AC8-0RE-IO-1V1401**
- 4 canais IO-Link: velocidade RMS (mm/s), aceleração pico (g), aceleração RMS (g), temperatura (°C)
- Faixa: 0–128 mm/s / 0–10 g / −40–85 °C
- Protocolo: IO-Link 1.1, COM2 (38,4 kBit/s), ciclo mín 5 ms
- Certificado DIN ISO 10816/20816

## ESP32 — Fluxo de Dados Real (ativo)

### Firmware em uso
**`firmware/esp32_mpu6050_rms/`** (sketch do professor) — saída texto 115200 baud:
```
AX (g): 0.012 | AY (g): 0.974 | AZ (g): 0.195 || GX (°/s): -2.3 | GY (°/s): -1.5 | GZ (°/s): 2.1
```
- Placa: **AI Thinker ESP32-CAM** (auto-detecta porta via VID/PID)
- MPU6050 soldado diretamente (I2C nos pinos padrão do ESP32-CAM)
- Taxa: 5 amostras/segundo (`delay(200)` no loop)

### Coletor serial
```powershell
python Armazenamento_Acelerometro_Bytes_Convertido.py
```
- Auto-detecta porta: CH340, CH343, CP210x, FTDI por VID/PID
- Salva em `dados/dados_YYYY-MM-DD_HH-MM-SS.csv`
- **CRITICO**: `rts=False, dtr=False` ao abrir porta — sem isso ESP32 entra em bootloader

### Página IoT (`4_IoT.py`)
- Modo **"ESP32 Real (USB)"**: lê CSV mais recente de `dados/` a cada 2s
- Status ONLINE se arquivo modificado há < 5s
- DC removido antes de calcular RMS dinâmico: `ax_ac = ax - ax.mean()`
- Modo **"Simulacao"**: dados sintéticos

## Dependências Principais

```
streamlit==1.45.1    # NAO atualizar — 1.46+ quebra com starlette
plotly>=5.20.0
pandas>=2.0.0
numpy>=1.26.0
cadquery>=2.7.0
Pillow
streamlit-autorefresh
pyserial
```

> Versões >1.45.1 do streamlit têm incompatibilidade com `starlette` que quebra o servidor.
