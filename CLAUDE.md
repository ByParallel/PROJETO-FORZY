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

## Arquitetura

```
PROJETO-FORZY/
├── 1_Inicio.py              # Home — landing page, status geral, cards de navegação
├── pages/
│   ├── 2_Monitoramento.py   # Dashboard em tempo real (modo demo ou banco SQLite)
│   ├── 3_Espectral.py       # FFT, espectrograma, cenários de falha
│   ├── 4_Operacional.py     # Análise do dataset histórico Forzy (aba principal)
│   ├── 5_Historico.py       # Player/timelapse do dataset
│   ├── 6_SCADA.py           # Planta 2D (DWG renderizado) + Vista 3D (STP real)
│   └── 7_IoT.py             # Interface de conexão ESP32 + leitura ao vivo real/simulada
├── utils/
│   ├── mock_data.py         # Gerador de dados simulados (4 modos de falha)
│   └── theme.py             # CSS global + sidebar_header() — importar em toda página
├── data/
│   ├── forzy.csv            # Dataset histórico: 2 motores, ~7k linhas brutas
│   ├── bomba.png            # Modelo STP renderizado em vista de perfil (2 bombas)
│   ├── bomba_verts.npy      # Vértices tessellados do STP (float32)
│   ├── bomba_faces.npy      # Faces tesselladas do STP (int32)
│   └── motores.db           # SQLite para leituras do ESP32 (pode estar vazio)
├── dados/                   # CSVs gerados pelo coletor serial (dados_YYYY-MM-DD_HH-MM-SS.csv)
├── firmware/
│   ├── esp32_mpu6050_rms/
│   │   └── esp32_mpu6050_rms.ino        # Firmware binário com timer (300 Hz)
│   └── TIMER_MPU6050_BYTES_STARTBYTE/
│       └── TIMER_MPU6050_BYTES_STARTBYTE.ino  # Firmware binário alternativo
├── Armazenamento_Acelerometro_Bytes_Convertido.py  # Coletor serial ativo (lê COM5, salva CSV)
├── TIMER_MPU6050_BYTES_STARTBYTE/       # Sketch binário (não usado no fluxo atual)
├── database.py              # Camada SQLite (tabelas: ativos, leituras)
└── serial_reader.py         # Leitor USB-Serial legado (não usado ativamente)
```

## Dados

### Dataset Forzy (`data/forzy.csv`)
- Separador `;`, 3 linhas de cabeçalho, `skiprows=3`
- Colunas usadas: `[0,3,4,5,6,7,8]` → `timestamp | m1_vel | m1_acel | m1_temp | m2_vel | m2_acel | m2_temp`
- Unidades: velocidade em **mm/s**, aceleração em **g**, temperatura em **°C**
- Carregado com `@st.cache_data` + resample 1s + oscilação sintética para visualização

### Limiares ISO 10816 (padrão)
| Zona    | Velocidade RMS |
|---------|---------------|
| Normal  | < 1,8 mm/s    |
| Alerta  | 1,8–4,5 mm/s  |
| Alarme  | > 4,5 mm/s    |

## Tema e CSS

**Nunca** adicionar CSS inline em páginas individuais sem antes verificar `utils/theme.py`. O tema global é aplicado chamando:

```python
import sys; sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.theme import apply as _apply_theme, sidebar_header as _sh
_apply_theme(); _sh()
```

Isso deve estar logo após `st.set_page_config()` em **toda** página. Cores base:

```
fundo app:   #060d18
fundo card:  #0a1628
borda card:  #0f2a45
fundo sidebar: #080f1c
texto primário: #e2eaf4
texto secundário: #4a7a9b
azul accent: #3498db / #7ec8e3
```

## Modelo 3D (SCADA)

- **Arquivo fonte**: `C:\Users\gel\Downloads\ChallengeForzy-bomba-teste.stp`
- **Tessellação**: `cadquery` com tolerância 0.08mm → 14.932 vértices, 21.674 faces
- **Separação de cores**: faces com Z ≤ -1.8 (unidades normalizadas) = base/skid azul `#1e3d5c`; faces acima = máquina verde (muda com status)
- **Filtro de artefatos**: base `area_max=None`, máquina `area_max=2.0` (remove triângulos voadores)
- **Re-geração do modelo**:
```python
import cadquery as cq, numpy as np
shape = cq.importers.importStep(r"C:\Users\gel\Downloads\ChallengeForzy-bomba-teste.stp")
verts, faces = shape.val().tessellate(0.08)
V = np.array([[v.x,v.y,v.z] for v in verts]); V -= V.mean(axis=0)
scale = 10.0/(V.max()-V.min()); V *= scale
np.save("data/bomba_verts.npy", V.astype(np.float32))
np.save("data/bomba_faces.npy", np.array(faces).astype(np.int32))
```

## Imagem 2D SCADA (`data/bomba.png`)

Renderização isométrica de perfil lateral (rz=90°, rx=15°) dos 2 motores lado a lado, gerada por painter's algorithm com PIL. Para regenerar, rodar o script interno em `6_SCADA.py` ou ver sessão anterior do chat.

## Performance — Regras Importantes

- **Nunca usar `shape="spline"` ou `smoothing`** em gráficos com > 500 pontos — muito lento
- **Usar `go.Scattergl`** (WebGL) em vez de `go.Scatter` para séries temporais longas
- **Máx 3.000 pontos** nos gráficos — usar `downsample()` definido em `4_Operacional.py`
- **Flags de status** devem ser calculadas com `np.where` vetorizado, nunca `.apply(lambda)`
- O `load_data` já faz resample a 1s (não 200ms) para balancear qualidade × velocidade

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
**`C:\Users\gel\Downloads\MPU6050.ino`** (sketch do professor) — saída texto 115200 baud:
```
AX (g): 0.012 | AY (g): 0.974 | AZ (g): 0.195 || GX (°/s): -2.3 | GY (°/s): -1.5 | GZ (°/s): 2.1
```
- Placa: **AI Thinker ESP32-CAM** na **COM5**
- MPU6050 soldado diretamente (I2C nos pinos padrão do ESP32-CAM)
- Taxa: 5 amostras/segundo (`delay(200)` no loop)

### Coletor serial
```powershell
python Armazenamento_Acelerometro_Bytes_Convertido.py
```
- Salva em `dados/dados_YYYY-MM-DD_HH-MM-SS.csv` com colunas: `timestamp, AX_g, AY_g, AZ_g, GX_dps, GY_dps, GZ_dps`
- **IMPORTANTE**: abrir a porta com `rts=False, dtr=False` — caso contrário o ESP32 entra em modo bootloader e não envia dados

### Página IoT (`7_IoT.py`)
- Modo **"🟢 ESP32 Real (USB)"**: lê o CSV mais recente de `dados/` a cada 2s (autorefresh)
- Exibe gráficos de AX/AY/AZ e magnitude de aceleração
- Modo **"🔴 Simulação"**: dados sintéticos, não requer hardware

### Como rodar com hardware real
```powershell
# Terminal 1 — coletor serial (deixar rodando)
python Armazenamento_Acelerometro_Bytes_Convertido.py

# Terminal 2 — site
python -m streamlit run 1_Inicio.py
```
Depois selecionar "🟢 ESP32 Real (USB)" na sidebar da página IoT.

## Dependências Principais

```
streamlit>=1.35.0 (usar 1.45.1 — versões >1.45 têm incompatibilidade com starlette)
plotly>=5.20.0
pandas>=2.0.0
numpy>=1.26.0
cadquery>=2.7.0      # para re-tessellação do STP
Pillow               # para processamento de imagens
streamlit-autorefresh
pyserial             # para leitura serial (quando ESP32 ativo)
```

> ⚠️ Não atualizar `streamlit` além de 1.45.1 sem testar — versões 1.46+ têm
> incompatibilidade com `starlette` que quebra o servidor.
