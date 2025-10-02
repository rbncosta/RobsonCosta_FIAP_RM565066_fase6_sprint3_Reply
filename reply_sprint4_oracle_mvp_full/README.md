# Sprint 4 – Reply (Oracle, sem API) — MVP fim-a-fim

**Pipeline:** `ESP32/Simulação → CSV/INSERT → Oracle → ML → Dashboard/Alertas`  
**Banco alvo:** **Oracle** (sem API; carga via `INSERT` SQL).  
**Pareamento das séries:** por **`SENSOR_ID`** e **`DATA_HORA`** (bucket p/ minuto).

Este repositório consolida as Fases 1–4:
- **Fase 1 (proposta/arquitetura)** – documentada em `/docs/arquitetura` e `/fase1_proposta`.
- **Fase 2 (coleta/simulação)** – ESP32/Monitor Serial gerando leituras.
- **Fase 3 (modelagem + ML)** – DER e treino simples com `RandomForest`.
- **Fase 4 (integração)** – fluxo completo, observabilidade e reprodutibilidade.

---

## 0) Pré-requisitos

- **Python 3.10+** (com `venv`)
- **Oracle** acessível via `host:port/servicename` (ex.: `localhost:1522/ORCLPDB`)
- **sqlplus** ou Oracle SQL Developer para rodar `.sql`
- (Opcional) **VS Code + PlatformIO/Wokwi** para simular o ESP32
- Pacotes Python (em `requirements.txt`):
  ```
  pandas
  numpy
  oracledb
  scikit-learn
  matplotlib
  streamlit
  plotly
  ```

### Ambiente Python (Windows PowerShell)

```powershell
py -3.10 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 1) Estrutura do repositório

```
/docs/arquitetura/           # .drawio/.png com a arquitetura integrada (Fase 1)
/fase1_proposta/             # README da proposta técnica (retro)
/ingest/
  esp32_fase4_log_to_csv_sql.py   # conversor Serial -> CSV + script de INSERT
  plot_from_oracle.py             # gera series_plot.png a partir do Oracle
  plot_from_serial_csv.py         # gera series_plot.png a partir do CSV
  esp32_serial.csv                # (entrada) CSV colado do Monitor Serial
  series_plot.png                 # evidência do item 4.2 (gráfico da série)
/db/
  schema_oracle_*.sql             # DDL (tabelas com DATA_HORA etc.)
  seed_oracle_from_fase4_log.sql  # INSERTs gerados pelo conversor
/ml/
  train_and_infer_oracle.py       # ML (TEMP + AUX por SENSOR_ID)
  metrics.json                    # saída com métrica (MAE)
  pred_vs_real.png                # gráfico real vs previsto
/dashboard/
  app.py                          # Streamlit: KPIs, séries, alertas, bloco do ML
README.md
requirements.txt
```

---

## 2) Variáveis de ambiente (Oracle + sensores)

Defina no **mesmo terminal** em que vai rodar scripts/app:

```powershell
# Oracle
$env:ORA_USER="RCOSTA"
$env:ORA_PASSWORD="SUA_SENHA"
$env:ORA_DSN="localhost:1522/ORCLPDB"

# IDs de sensores (defina conforme sua tabela SENSOR)
# TEMP_ID = sensor de Temperatura | AUX_ID = sensor auxiliar (UMIDADE ou VIBRACAO)
$env:ORA_SENSOR_TEMP_ID="1"
$env:ORA_SENSOR_AUX_ID="2"
$env:ORA_SENSOR_AUX_LABEL="VIBRACAO"   # mude para "UMIDADE" se for o seu caso
```

> **Importante:** o projeto **não depende** de uma coluna `TIPO_SENSOR`. Tudo é feito por **`SENSOR_ID`**.

---

## 3) Coleta & Ingestão (itens 4.2 e 4.3)

### 3.1 Coleta (ESP32/Simulação)
- Rode seu `.ino` (Fase 4).  
- No **Monitor Serial**, garanta linhas no formato:

```
contador,fosforo,potassio,ph,umidade,bomba
21,0,1,6.80,75.0,1
22,1,1,5.50,40.0,0
...
```

- **Copie e cole** as linhas no arquivo `ingest/esp32_serial.csv`.

### 3.2 Conversão → INSERTs (sem API)

Gera o script de carga com base no CSV do Serial:

```powershell
python ingest\esp32_fase4_log_to_csv_sql.py --start-now --log ingest\esp32_serial.csv `
  --sensor-id-temp $env:ORA_SENSOR_TEMP_ID --sensor-id-hum $env:ORA_SENSOR_AUX_ID
```

O conversor:
- normaliza números (vírgula/ponto),
- produz séries de **temperatura** e série **auxiliar** (umidade/vibração),
- gera `db/seed_oracle_from_fase4_log.sql` com `INSERT` para as tabelas do schema.

### 3.3 Carga no Oracle

```powershell
sqlplus $env:ORA_USER/$env:ORA_PASSWORD@$env:ORA_DSN @db\seed_oracle_from_fase4_log.sql
```

### 3.4 Gráfico inicial da série (evidência 4.2)

- A partir do **Oracle** (últimas 24h):
  ```powershell
  python ingest\plot_from_oracle.py --mins 1440
  ```
- (Opcional) Direto do **CSV** do Serial:
  ```powershell
  python ingest\plot_from_serial_csv.py
  ```

Isso atualiza `ingest/series_plot.png`.

---

## 4) ML Básico Integrado (item 4.4)

Treine/inira:

```powershell
python ml\train_and_infer_oracle.py
```

O script:
- lê séries por **`SENSOR_ID`** (Temperatura = `ORA_SENSOR_TEMP_ID`, Auxiliar = `ORA_SENSOR_AUX_ID`);
- alinha por **minuto** e, se necessário, por **proximidade (2 min)**;
- cria alvo `temp_next` (prever próxima temperatura);
- treina `RandomForestRegressor` (holdout temporal quando há dados suficientes);
- gera:
  - `ml/metrics.json` (contém `MAE` e `aux_label`)
  - `ml/pred_vs_real.png` (real vs previsto nas últimas amostras)

> Com poucos dados o treino/avaliação ocorre no próprio conjunto (o script avisa).

---

## 5) Dashboard & Alertas (item 4.5)

```powershell
# se faltar plotly:
pip install plotly

streamlit run dashboard\app.py
```

**No app**:
- Ajuste **Janela (min)** para cobrir a faixa de dados.
- Use o **Threshold de temperatura (°C)**; o KPI **Alertas** muda conforme o limite.
- **KPIs:** Leituras (janela), Temp média (°C), **AUX média** (Vibração/Umidade), Alertas.
- **Séries temporais:** Temperatura e a série Auxiliar.
- **Bloco do modelo:** mostra `ml/metrics.json` (MAE) e `ml/pred_vs_real.png`.
- **Debug:** *expander* com `count`, `min_temp`, `max_temp` e `threshold` atuais.

> Se aparecer “Sem dados na janela”, aumente `Janela (min)` ou insira novas leituras.

---

## 6) Arquitetura Integrada (item 4.1)

- `/docs/arquitetura/` contém o diagrama `.drawio/.png` do fluxo:  
  **ESP32/Sim → CSV → INSERT (Oracle) → ML (batch) → Streamlit (KPIs/alertas)**  
- Evidencie no diagrama:
  - Formatos (CSV, INSERT), periodicidade (janela do dashboard),
  - Tabelas com **`DATA_HORA`**, chaves e integridade,
  - Bloco de ML (treino/inferência simples),
  - Visualização/alertas (threshold).

---

## 7) Ordem de execução (resumo para a banca)

```powershell
# 1) Variáveis
$env:ORA_USER="RCOSTA"
$env:ORA_PASSWORD="SUA_SENHA"
$env:ORA_DSN="localhost:1522/ORCLPDB"
$env:ORA_SENSOR_TEMP_ID="1"
$env:ORA_SENSOR_AUX_ID="2"
$env:ORA_SENSOR_AUX_LABEL="VIBRACAO"

# 2) Coleta -> CSV -> Conversão -> Carga
python ingest\esp32_fase4_log_to_csv_sql.py --start-now --log ingest\esp32_serial.csv `
  --sensor-id-temp $env:ORA_SENSOR_TEMP_ID --sensor-id-hum $env:ORA_SENSOR_AUX_ID
sqlplus $env:ORA_USER/$env:ORA_PASSWORD@$env:ORA_DSN @db\seed_oracle_from_fase4_log.sql

# 3) ML
python ml\train_and_infer_oracle.py

# 4) Dashboard/alertas
streamlit run dashboard\app.py

# 5) Gráfico de série (evidência 4.2)
python ingest\plot_from_oracle.py --mins 1440
```

---

## 8) Entregáveis (checklist)

- **/docs/arquitetura/**: diagrama integrado (PNG + `.drawio`).
- **/ingest/**: `esp32_serial.csv` + `series_plot.png`.
- **/db/**: DDL + `seed_oracle_from_fase4_log.sql`.
- **/ml/**: `metrics.json` + `pred_vs_real.png`.
- **/dashboard/**: prints do app com KPIs, séries e **alertas variando** com threshold.
- **README**: este passo-a-passo + link do **vídeo (≤ 5 min)**.

---

## 9) Roteiro do vídeo (≤ 5 min)

1. **Arquitetura** (30–40s).  
2. **Coleta**: mostrar Serial e `esp32_serial.csv` (40s).  
3. **Ingestão**: converter → abrir `seed_oracle_from_fase4_log.sql` → `SELECT COUNT(*)` (50s).  
4. **ML**: rodar script, abrir `metrics.json` e `pred_vs_real.png` (60s).  
5. **Dashboard**: séries e KPIs; **mudar Threshold** e mostrar **Alertas** mudando (2 min).

---

## 10) Troubleshooting

- **ORA-01017 (usuário/senha)** – confira `ORA_USER/ORA_PASSWORD/ORA_DSN` (use *service name*, ex.: `ORCLPDB`).  
- **Aviso do pandas sobre SQLAlchemy** – é inofensivo; para silenciar, instale `sqlalchemy` e crie um `engine`.  
- **`No module named 'plotly'`** – `pip install plotly`.  
- **Alertas não mudam** – veja `Debug` para `min_temp`/`max_temp` e ajuste o threshold entre esses valores; aumente **Janela (min)**.  
- **“Sem pares TEMP/AUX” no ML** – confirme que `ORA_SENSOR_TEMP_ID` e `ORA_SENSOR_AUX_ID` apontam para **sensores diferentes** e existem leituras para ambos dentro da janela de tempo.

---

## 11) Licença

Uso acadêmico (FIAP – Challenge Reply). Componentes open-source respeitam suas respectivas licenças.
