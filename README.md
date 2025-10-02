# Sprint 4 – Reply - FLuxo Completo

**Pipeline:** `ESP32/Simulação → CSV → INSERT → Oracle → ML → Dashboard/Alertas`  
**Banco alvo:** **Oracle** (sem API; carga via `INSERT`)  
**Pareamento das séries:** por **`SENSOR_ID`** e **`DATA_HORA`** (bucket p/ minuto).

## Mapa das Fases
- **Fase 1 (Proposta Técnica)**: `/fase1_proposta/README.md` (retro, integrada à Sprint 4)  
- **Fase 2 (Coleta/Simulação)**: https://github.com/rbncosta/FIAP/tree/3168e318779a00cf0699acb998784f334342bfd6/fase4-Enterprise%20Challenge  
- **Fase 3 (Banco + ML base)**: https://github.com/rbncosta/RobsonCosta_FIAP_RM565066_fase5_sprint3_Reply  
- **Fase 4 (Integração fim‑a‑fim)**: este repositório (Oracle + ML + Dashboard)

---

> 📌 **Nota sobre a Enterprise Challenge - Sprint 1 - Reply (justificativa de submissão)**
>
> A Enterprise Challenge - Sprint 1 - Reply pedia um repositório específico (privado) entregue no prazo.
> Eu perdi o prazo de submissão e, para manter a rastreabilidade e a
> reprodutibilidade, **consolidei a Enterprise Challenge - Sprint 1 - Reply dentro deste repositório**.
>
> - A proposta técnica e a arquitetura estão em **/fase1_proposta/**
>   e **/docs/arquitetura.png**.
> - O fluxo completo foi integrado aqui: **ESP32/Sim → CSV/INSERT → Oracle → ML → Dashboard**.
> - Esta organização garante a visualização de fim-a-fim
>   com as referências exigidas no item **4.6** do enunciado.

## 1) Pré-requisitos

- **Python 3.10+** (com `venv`)
- **Oracle** acessível via `host:port/servicename` (ex.: `localhost:1522/ORCLPDB`)
- **sqlplus** ou Oracle SQL Developer para rodar `.sql`
- **VS Code + PlatformIO/Wokwi** para simular o ESP32
- Pacotes Python:
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
py -3.13 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

---

## 2) Estrutura do repositório

```
/docs/
   arquitetura.png                # Fluxo da arquitetura integrada
/ingest/
  esp32_csv_to_sql.py             # conversor Serial de CSV para script SQL de INSERT no banco de dados
  esp32_serial.csv                # (entrada) CSV colado do terminal de simulação do ESP32
/db/
  schema_oracle_rm565066.sql      # Script para criação das tabelas do banco de dados
  consultas_demo_rm565066.sql     # Script SQL de consulta das tabelas do banco de dados
  seed_oracle_from_fase4_log.sql  # Script SQL inserir os registros no banco de dados (convertidos do arquivo CSV)
  select_evidencia                # Evidência de execução do SELECT
/ml/
  train_and_infer_oracle.py       # Código do Machine Learning em Python
  metrics.json                    # saída com métrica (MAE) do modelo de treinamento
  pred_vs_real.png                # gráfico real vs previsto  do modelo de treinamento
/dashboard/
  app.py                          # Streamlit: KPIs, séries, alertas, bloco do Machine Learning em Python
  Relatorio_KPIs.pdf              # Evidência do Dashboard
README.md

```

---

## 3) Variáveis de ambiente (Oracle + sensores)

Defina no **mesmo terminal** em que vai rodar scripts/app:

```powershell
# Oracle
$env:ORA_USER="SEU_USER"
$env:ORA_PASSWORD="SUA_SENHA"
$env:ORA_DSN="SEU_DNS"

# IDs de sensores (defina conforme sua tabela SENSOR)
# TEMP_ID = sensor de Temperatura | AUX_ID = sensor auxiliar (UMIDADE ou VIBRACAO)
$env:ORA_SENSOR_TEMP_ID="1"
$env:ORA_SENSOR_AUX_ID="2"
$env:ORA_SENSOR_AUX_LABEL="VIBRACAO"   # mude para "UMIDADE" se for o seu caso
```

---

## 4) Coleta & Ingestão

### 4.1 Coleta (ESP32/Simulação)
- Rode o simulador ESP32.  
- No **Monitor Serial**, aguarde a execução por alguns minutos, localize as linhas no formato abaixo:

```
contador,fosforo,potassio,ph,umidade,bomba
21,0,1,6.80,75.0,1
22,1,1,5.50,40.0,0
...
```

- **Copie e cole** as linhas no arquivo `ingest/esp32_serial.csv`.

### 4.2 Conversão → INSERTs (sem API)

Gera o script de carga com base no CSV do Serial:

```powershell
python ingest\esp32_csv_to_sql.py --start-now --log ingest\esp32_serial.csv `
  --sensor-id-temp $env:ORA_SENSOR_TEMP_ID --sensor-id-hum $env:ORA_SENSOR_AUX_ID
```

O conversor:
- normaliza números (vírgula/ponto),
- produz séries de **temperatura** e série **auxiliar** (umidade/vibração),
- gera `db/seed_oracle_from_fase4_log.sql` com `INSERT` para as tabelas do schema.

### 4.3 Carga no Oracle

```SQL Developer
Abra o script `db/seed_oracle_from_fase4_log.sql` e execute.
```

---

## 5) ML Básico Integrado (item 4.4)

Treine o modelo do Marchine Learning:

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

> Mesmo com poucos dados o treino/avaliação ocorre no próprio conjunto (o script gera o alerta de poucos dados).

---

## 6) Dashboard & Alertas

```powershell
streamlit run dashboard\app.py
```

**No app**:
- Ajuste **Janela (min)** para cobrir a faixa de dados.
- Use o **Threshold de temperatura (°C)**; o KPI **Alertas** muda conforme o limite.
- **KPIs:** Leituras (janela), Temp média (°C), **AUX média** (Vibração), Alertas.
- **Séries temporais:** Temperatura e a série Auxiliar.
- **Bloco do modelo:** mostra `ml/metrics.json` (MAE) e `ml/pred_vs_real.png`.
- **Debug:** *expander* com `count`, `min_temp`, `max_temp` e `threshold` atuais.

> Se aparecer “Sem dados na janela”, aumente `Janela (min)` ou insira novas leituras.

---

## 7) Arquitetura Integrada

- `/docs/arquitetura.png/` contém o diagrama do fluxo completo:  
  **ESP32/Sim → CSV → INSERT (Oracle) → ML (batch) → Streamlit (KPIs/alertas)**  
- Evidencie no diagrama:
  - Formatos (CSV, INSERT), periodicidade (janela do dashboard),
  - Tabelas com **`DATA_HORA`**, chaves e integridade,
  - Bloco de ML (treino/inferência simples),
  - Visualização/alertas (threshold).

---

## 8) Ordem de execução (resumo)

```powershell
# 8.1 Variáveis
$env:ORA_USER="SEU_USER"
$env:ORA_PASSWORD="SUA_SENHA"
$env:ORA_DSN="SEU_DNS"
$env:ORA_SENSOR_TEMP_ID="1"
$env:ORA_SENSOR_AUX_ID="2"
$env:ORA_SENSOR_AUX_LABEL="VIBRACAO"

# 8.2 Coleta -> CSV -> Conversão -> Carga
python ingest\esp32_fase4_log_to_csv_sql.py --start-now --log ingest\esp32_serial.csv `
  --sensor-id-temp $env:ORA_SENSOR_TEMP_ID --sensor-id-hum $env:ORA_SENSOR_AUX_ID
sqlplus $env:ORA_USER/$env:ORA_PASSWORD@$env:ORA_DSN @db\seed_oracle_from_fase4_log.sql

# 8.3 ML
python ml\train_and_infer_oracle.py

# 8.4 Dashboard/alertas
streamlit run dashboard\app.py

```

---

## 9) Entregáveis (checklist)

- **/docs/**: diagrama integrado (PNG + `.drawio`).
- **/ingest/**: `esp32_serial.csv` + `series_plot.png`.
- **/db/**: DDL + `seed_oracle_from_fase4_log.sql`.
- **/ml/**: `metrics.json` + `pred_vs_real.png`.
- **/dashboard/**: prints do app com KPIs, séries e **alertas variando** com threshold.
- **/vídeo/**: link do vídeo ?
- **README**: este passo-a-passo**.

---

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
