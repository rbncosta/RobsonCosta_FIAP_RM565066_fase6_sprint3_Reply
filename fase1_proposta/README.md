> **Observação de submissão – Fase 1**
>
> Esta pasta substitui o repositório privado solicitado na Fase 1.
> Como perdi o prazo de entrega, **incluí a proposta técnica e a arquitetura aqui**
> e **integrei tudo na entrega final (Fase 4)**.
> As referências às Fases 2 e 3 e o encadeamento fim-a-fim estão descritos
> no README principal  e no diagrama em `/docs/arquitetura.png`.

# Fase 1 — Proposta Técnica (Hermes Reply)  
**Projeto:** Prevenção de falhas em linha de produção com IoT + ML  
**Entrega:** Proposta de arquitetura e pipeline de dados (documental, sem obrigatoriedade de código funcional nesta fase)

> Este documento consolida a proposta técnica da **Fase 1** para o mesmo MVP que evolui nas Fases 2–4. Ele está alinhado ao que foi implementado no repositório principal (Sprint 4), mantendo **Oracle** como banco relacional e **ingestão via INSERT/CSV (sem API)**.

---

## 1) Contexto & Problema
Empresas industriais sofrem com **paradas não programadas** e **falhas em equipamentos**. Isso gera perdas de produtividade e custos de manutenção corretiva. A proposta é implantar um fluxo **fim‑a‑fim** que monitore sensores (reais ou simulados), **armazene** leituras historicamente, **treine** um modelo simples de ML e **exponha** indicadores/alertas para apoio à decisão.

## 2) Objetivo da Solução
- **Monitorar** variáveis de processo (ex.: temperatura e vibração/umidade) a partir de um ESP32/simulação.  
- **Persistir** leituras em banco **Oracle**, com integridade e rastreabilidade temporal.  
- **Modelar/Prever** comportamento futuro simples (ex.: temperatura no próximo instante) para suportar alertas.  
- **Visualizar** KPIs e **disparar alertas** por limiar configurável em dashboard web.

## 3) Arquitetura Proposta (alto nível)
Fluxo de dados **ESP32/Sim → CSV/INSERT → Oracle → ML (batch) → Dashboard/Alertas**

- **Coleta (Fase 2)**: ESP32 (Wokwi/PlatformIO) imprime leituras no **Monitor Serial**.  
- **Ingestão (Fase 4)**: usuário copia o log para `ingest/esp32_serial.csv`; script gera `INSERT` para Oracle (**sem API**).  
- **Banco de Dados (Fase 3)**: tabelas **SENSOR** e **LEITURA_SENSOR** com chaves (`SENSOR_ID`, `DATA_HORA`).  
- **ML (Fase 3/4)**: treino e inferência offline (batch) com `RandomForestRegressor` usando séries alinhadas por minuto.  
- **Dashboard (Fase 4)**: Streamlit lê do Oracle, mostra **KPIs/séries** e **alertas** por threshold.

### Diagrama (referência)
O diagrama detalhado está em `/docs/arquitetura/arquitetura.drawio` (e `arquitetura.png`) no repositório principal.

## 4) Tecnologias & Justificativas
- **Linguagem:** Python (ecossistema robusto para dados/ML).  
- **IoT/Simulação:** ESP32 + Wokwi/PlatformIO (baixo custo, agilidade).  
- **Banco relacional:** **Oracle** (requisito do avaliador; integridade, SQL padrão).  
- **Ingestão:** **CSV → script de INSERT** (simples, reprodutível e condizente com o enunciado que dispensa API).  
- **ML:** `scikit-learn` (baseline rápido), `RandomForestRegressor` (bom compromisso viés/variância).  
- **Dashboard:** Streamlit (velocidade de entrega + interatividade básica).  
- **Plot:** Matplotlib/Plotly.

## 5) Pipeline de Dados (detalhado)
1. **Coleta (Serial)** – ESP32 gera linhas com leituras (ex.: contador,fosforo,potassio,ph,umidade,bomba).  
2. **CSV brutos** – Usuário salva o log em `ingest/esp32_serial.csv`.  
3. **Conversão para INSERT** – `ingest/esp32_fase4_csv_to_sql.py` normaliza números e cria `db/seed_oracle_from_fase4_log.sql`.  
4. **Carga** – Executar script no Oracle (DDL já disponível em `/db/schema_oracle_*.sql`).  
5. **ML batch** – `ml/train_and_infer_oracle.py` consulta **TEMPERATURA** (`SENSOR_ID` TEMP) e **AUX** (`SENSOR_ID` VIBRAÇÃO/UMIDADE), alinha por minuto (com tolerância), define `temp_next` e treina modelo.  
6. **Dashboard/Alertas** – `dashboard/app.py` consulta por janela (min), calcula KPIs, exibe séries e **conta alertas** `TEMPERATURA > threshold`.

## 6) Modelagem de Dados (DER – referência Fase 3)
- **SENSOR**(`SENSOR_ID`, `NOME`, …)  
- **LEITURA_SENSOR**(`LEITURA_ID`, `SENSOR_ID`, `DATA_HORA`, `VALOR`, …)  
Chaves e restrições garantem integridade e facilitam consultas por janela temporal. A solução **não exige `TIPO_SENSOR`**; o pareamento é feito por **`SENSOR_ID`**.

## 7) Plano de ML
- **Tarefa:** regressão de **temperatura no próximo instante**.  
- **Features:** `TEMPERATURA_t`, `AUX_t` (AUX = vibração/umidade).  
- **Alinhamento temporal:** bucketing por minuto; tolerância de proximidade até 2 min.  
- **Métrica:** `MAE` (erro absoluto médio).  
- **Saídas:** `ml/metrics.json` e `ml/pred_vs_real.png` (para o dashboard).  
- **Evoluções futuras:** janelas deslizantes, novos sensores, classificação de falhas, alertas inteligentes.

## 8) Observabilidade & Reprodutibilidade
- **Evidências versionadas:** `ingest/esp32_serial.csv`, `db/seed_oracle_from_fase4_log.sql`, `ml/metrics.json`, `ml/pred_vs_real.png`.  
- **README raiz** com passo a passo de execução.  
- **Sem dependência de API**; tudo reproduzível com scripts e SQL.

## 9) Entregáveis (Fase 1)
- **Este documento** (`/fase1_proposta/README.md`) com metodologia e tecnologias.  
- **Diagrama** (`/docs/arquitetura/*.png`).  
- **Plano de pipeline** (seções 3 e 5).  
- **Plano de ML** (seção 7).  
- **Organização & referências** às fases (seção 10).

## 10) Ligações com as Fases 2–4
- **Fase 2 (Coleta/ESP32):** repositório com o projeto do microcontrolador/serial  
  https://github.com/rbncosta/FIAP/tree/3168e318779a00cf0699acb998784f334342bfd6/fase4-Enterprise%20Challenge
- **Fase 3 (Modelagem/ML):** base de dados e experimentos de ML  
  https://github.com/rbncosta/RobsonCosta_FIAP_RM565066_fase5_sprint3_Reply
- **Fase 4 (Integração/MVP):** este repositório principal (Oracle + ML + Dashboard).

## 11) Escopo & Limitações (nesta fase)
- Sem obrigatoriedade de “código funcional” — foco no **planejamento e coerência**.  
- Ingestão **sem API** por decisão de simplicidade e adequação ao enunciado.  
- Modelo inicial (baseline) — performance não é objetivo principal da fase.

## 12) Próximos Passos (resumo)
1) Validar DER/DDL no Oracle.  
2) Exercitar coleta no ESP32 e produzir amostra CSV.  
3) Testar conversor **CSV → INSERT** e **carga**.  
4) Executar ML com dados reais/simulados.  
5) Montar dashboard com KPIs/alertas e prints para evidência.

---

### Anexo – Guia mínimo de execução (pós‑fase 1)
Para executar o MVP integrado, siga o **README** da raiz do repositório (Sprint 4): variáveis de ambiente; conversão e carga no Oracle; treino; e dashboard/alertas.
