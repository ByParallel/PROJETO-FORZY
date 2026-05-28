# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMS · Forzy Industrial Monitoring System

Sistema de monitoramento industrial de bombas centrífugas construído com Python e Streamlit. Exibe dados históricos de 2 motores via CSV, análise espectral FFT, visualização SCADA 2D/3D com modelo STP real, interface de conexão IoT/ESP32 e gestão completa de ativos industriais (Sprint 3).

## Como Rodar

```powershell
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

Aplicação Streamlit multi-página. A navegação lateral é **customizada** — o nav padrão do Streamlit está oculto. Toda página deve chamar:

```python
from utils.theme import apply as _apply_theme, sidebar_nav as _snav
_apply_theme(); _snav("inicio")  # ou "dashboard", "scada", "iot", "navegacao", "cadastro", "rpa", "pipeline"
```

**Nunca** usar `sidebar_header()` — substituída por `sidebar_nav()`.

Ordem das seções na sidebar: **Principal → Gestão → Análise → Planta & Sensores**

Páginas (em `pages/`):
- `2_Dashboard.py` — Dashboard consolidado com 4 tabs
- `3_SCADA.py` — Planta 2D + Vista 3D interativa
- `4_IoT.py` — Interface ESP32 ao vivo (real ou simulado)
- `5_Navegacao.py` — Drill-down Planta > Área > Ativo + mapa
- `6_Cadastro.py` — CRUD de ativos industriais
- `7_RPA.py` — Automação: associação TAG, status em lote, coleta, auditoria
- `8_Pipeline.py` — Pipeline completo, mapeamento geral, simulação OCR

Arquivos com prefixo `_` são backups do Sprint 1 — ocultos do nav, não editar.

## Dashboard (`pages/2_Dashboard.py`)

4 tabs em uma única página. Troca de tab via `st.query_params["tab"]` + injeção de JS click. Sub-itens da sidebar usam `st.session_state["_dash_tab"]` + `st.switch_page`.

- **Tab 0 — Monitoramento**: Player por frames do Dataset Forzy ou Simulado. Autorefresh só ativo quando `_active_tab == 0`. Motor 1 e Motor 2 lado a lado com gauges e histórico deslizante (120 frames).
- **Tab 1 — Espectral**: FFT sintética (fs=1000 Sa/s) com amplitude parametrizada pelo RMS real. Espectrograma por janelas. Harmônicas e bandas de falha configuráveis.
- **Tab 2 — Operacional**: Análise completa do dataset. Sub-tabs: Timeline, Análise, Comparação, Eventos, Estatísticas.
- **Tab 3 — Histórico**: Player/timelapse animado do dataset.

## Home (`1_Inicio.py`)

Atualiza em tempo real via `streamlit_autorefresh`. Modos: Dataset Forzy (player por frames, +5 frames/tick) ou Simulado (acumula histórico em `session_state`). Intervalo suave: 2s / 5s / 10s — não frenético. Sparklines mostram janela deslizante dos últimos 120 frames, não waveform ao vivo.

## Banco de Dados (`database.py`)

SQLite em `data/motores.db`. Duas camadas:

**Sprint 2 — IoT/ESP32:**
- `ativos` — ativos rastreados pelo ESP32 (`ativo_id` TEXT)
- `leituras` — leituras brutas do MPU6050 com hash de deduplicação

**Sprint 3 — Gestão Industrial:**
- `plantas`, `areas` — hierarquia da planta
- `ativos_industrial` — cadastro completo (specs, GPS, status)
- `log_execucoes` — log de automações RPA
- `historico_atualizacoes` — auditoria de mudanças

O banco **não tem seed automático** — dados criados pelo usuário via Cadastro. Funções públicas: `get_plantas()`, `get_areas()`, `get_ativos_industrial()`, `get_ativo_por_codigo()`, `criar_ativo_industrial()`, `editar_ativo_industrial()`, `log_execucao()`, `get_logs()`, `get_historico()`.

## Módulos RPA (`rpa/`)

- `tag_association.py` — associa TAG + área em lote, registra log
- `record_updater.py` — atualiza status em lote, simula coleta de sensores
- `nameplate_pipeline.py` — gera imagem de plaqueta (Pillow), simula OCR, valida campos

## Dados

### Dataset Forzy (`data/forzy.csv`)
- Separador `;`, 3 linhas de cabeçalho → `skiprows=3`
- Colunas usadas: `[0,3,4,5,6,7,8]` → `timestamp | m1_vel | m1_acel | m1_temp | m2_vel | m2_acel | m2_temp`
- Unidades: velocidade em **mm/s**, aceleração em **g**, temperatura em **°C**
- Valores são **RMS agregados** (~1 Sa/s) — **não fazer FFT direta neles**

### Limiares ISO 10816
| Zona   | Velocidade RMS |
|--------|---------------|
| Normal | < 1,8 mm/s    |
| Alerta | 1,8–4,5 mm/s  |
| Alarme | > 4,5 mm/s    |

## Tema e CSS

**Nunca** adicionar CSS inline em páginas individuais sem antes verificar `utils/theme.py`. Sem emojis — decisão de estilo do Sprint 2.

Cores base:
```
fundo app:      #060d18
fundo card:     #0a1628
borda card:     #0f2a45
fundo sidebar:  #080f1c
texto primário: #e2eaf4
texto secundário: #4a7a9b
azul accent:    #3498db / #7ec8e3
```

Cores de status:
```
Normal / Ativo:     #2ecc71
Alerta / Manutenção: #f39c12
Alarme / Inativo:   #e74c3c
```

## Mapa

Páginas `5_Navegacao.py` e `8_Pipeline.py` usam `st.map()` nativo do Streamlit com colunas `lat`, `lon`, `color` (RGBA como lista `[R,G,B,A]`), `size`. Não usar `plotly scatter_mapbox` — estava causando problema visual.

## Modelo 3D (SCADA)

Tessellado a partir do arquivo STP original com `cadquery`. Os arrays pré-computados estão em `data/bomba_verts.npy` (float32, 14.932 vértices) e `data/bomba_faces.npy` (int32, 21.674 faces). Faces com Z ≤ -1.8 = base/skid azul `#1e3d5c`; acima = máquina verde.

Para re-gerar se o arquivo STP mudar:
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
- **`fillcolor` no Plotly** não aceita hex com alpha (`#2ecc7115`) — usar `rgba(r,g,b,a)` sempre

## Modos de Falha Simulados (`utils/mock_data.py`)

| Modo            | Assinatura                      |
|-----------------|---------------------------------|
| `normal`        | 1x RPM pequeno, ruído baixo     |
| `desbalanco`    | 1x RPM dominante (±12%)         |
| `cavitacao`     | Banda larga + sub-harmônica     |
| `desalinhamento`| 2x RPM dominante                |

## ESP32 — Fluxo de Dados Real

### Firmware em uso
**`firmware/esp32_mpu6050_rms/`** — saída texto 115200 baud:
```
AX (g): 0.012 | AY (g): 0.974 | AZ (g): 0.195 || GX (°/s): -2.3 | GY (°/s): -1.5 | GZ (°/s): 2.1
```
Placa: AI Thinker ESP32-CAM, MPU6050 em I2C, 5 amostras/segundo (`delay(200)`).

### Coletor serial (`Armazenamento_Acelerometro_Bytes_Convertido.py`)
- Auto-detecta porta via VID/PID: CH340, CH343, CP210x, FTDI
- Salva em `dados/dados_YYYY-MM-DD_HH-MM-SS.csv`
- **CRITICO**: `rts=False, dtr=False` ao abrir porta — sem isso o ESP32 entra em bootloader

### Página IoT (`4_IoT.py`)
- Modo **"ESP32 Real (USB)"**: lê o CSV mais recente de `dados/` a cada 2s. Status ONLINE se modificado há < 5s. DC removido antes do RMS: `ax_ac = ax - ax.mean()`
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
