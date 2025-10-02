import os, json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import oracledb

# --- Oracle ---
ORA_USER = os.environ.get("ORA_USER", "RCOSTA")
ORA_PASSWORD = os.environ.get("ORA_PASSWORD", "")
ORA_DSN = os.environ.get("ORA_DSN", "localhost:1522/ORCLPDB")

# --- Sensores (defina no terminal) ---
TEMP_ID   = int(os.environ.get("ORA_SENSOR_TEMP_ID", "1"))
AUX_ID    = int(os.environ.get("ORA_SENSOR_AUX_ID",  "2"))
AUX_LABEL = os.environ.get("ORA_SENSOR_AUX_LABEL", "VIBRACAO")  # rótulo da série auxiliar

st.set_page_config(page_title="Reply Sprint 4", layout="wide")
st.title("Reply Sprint 4 - Dashboard & Alertas (Oracle)")

# Sidebar
thresh = st.sidebar.number_input("Threshold de temperatura (°C)", value=28.0, step=0.5, format="%.2f")
mins = st.sidebar.number_input("Janela (min)", value=180, step=10)

# Consulta
q = """
SELECT l.data_hora AS data_hora, l.sensor_id AS sensor_id, l.valor AS valor
FROM leitura_sensor l
WHERE l.data_hora >= SYSTIMESTAMP - NUMTODSINTERVAL(:minutos, 'MINUTE')
  AND l.sensor_id IN (:temp_id, :aux_id)
ORDER BY l.data_hora
"""

conn = oracledb.connect(user=ORA_USER, password=ORA_PASSWORD, dsn=ORA_DSN)
df = pd.read_sql(q, conn, params={"minutos": mins, "temp_id": TEMP_ID, "aux_id": AUX_ID})
conn.close()

if df.empty:
    st.info("Sem dados na janela atual. Aumente a janela ou insira novas leituras.")
    st.stop()

# Normalização
df["DATA_HORA"] = pd.to_datetime(df["DATA_HORA"])
df["VALOR"] = pd.to_numeric(df["VALOR"].astype(str).str.replace(",", "."), errors="coerce")
df["T_MIN"] = df["DATA_HORA"].dt.floor("min")

wide = (
    df.groupby(["T_MIN","SENSOR_ID"], as_index=False)["VALOR"].mean()
      .pivot(index="T_MIN", columns="SENSOR_ID", values="VALOR")
      .sort_index()
)

# renomeia colunas por rótulo
rename_map = {}
if TEMP_ID in wide.columns: rename_map[TEMP_ID] = "TEMPERATURA"
if AUX_ID  in wide.columns: rename_map[AUX_ID]  = AUX_LABEL
wide = wide.rename(columns=rename_map)

with st.expander("🔎 Debug (faixa de valores na janela)"):
    st.json({
        "count": int(wide.shape[0]),
        "min_temp": None if "TEMPERATURA" not in wide else float(np.nanmin(wide["TEMPERATURA"])),
        "max_temp": None if "TEMPERATURA" not in wide else float(np.nanmax(wide["TEMPERATURA"])),
        "threshold": float(thresh)
    })

# KPIs
cols = st.columns(4)
cols[0].metric("Leituras (janela)", int(wide.shape[0]))
cols[1].metric("Temp média (°C)", "-" if "TEMPERATURA" not in wide else f"{np.nanmean(wide['TEMPERATURA']):.2f}")
cols[2].metric(f"{AUX_LABEL.title()} média", "-" if AUX_LABEL not in wide else f"{np.nanmean(wide[AUX_LABEL]):.2f}")
alerts = int((wide.get("TEMPERATURA", pd.Series(dtype=float)) > thresh).sum())
cols[3].metric("Alertas (temp > thresh)", alerts)

# Série temperatura
if "TEMPERATURA" in wide:
    fig1 = px.line(wide.reset_index(), x="T_MIN", y="TEMPERATURA", title="Série Temporal - Temperatura")
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.warning("Não há série de TEMPERATURA nesta janela.")

# Feed de alertas + histograma  (CORRIGIDO: máscara no mesmo DF após reset_index)
if "TEMPERATURA" in wide:
    df_w = wide.reset_index()
    alerts_df = df_w.loc[df_w["TEMPERATURA"] > thresh, ["T_MIN","TEMPERATURA"]]
    with st.expander("⚠️ Alertas recentes (temp > threshold)"):
        if alerts_df.empty:
            st.write("Sem alertas na janela.")
        else:
            st.dataframe(
                alerts_df.rename(columns={"T_MIN":"Data/Hora","TEMPERATURA":"Temperatura (°C)"}),
                use_container_width=True
            )

    hist = px.histogram(df_w, x="TEMPERATURA", nbins=20, title="Distribuição da Temperatura (janela)")
    st.plotly_chart(hist, use_container_width=True)

# Série auxiliar (ex.: VIBRACAO)
if AUX_LABEL in wide:
    fig2 = px.line(wide.reset_index(), x="T_MIN", y=AUX_LABEL, title=f"Série Temporal - {AUX_LABEL.title()}")
    st.plotly_chart(fig2, use_container_width=True)

# Bloco de métrica do modelo
metrics_path = Path("ml/metrics.json")
plot_path = Path("ml/pred_vs_real.png")
with st.expander("🤖 Modelo (treino/inferência)"):
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        cols_m = st.columns(3)
        cols_m[0].metric("Modelo", m.get("model","-"))
        cols_m[1].metric("Métrica", m.get("metric","MAE"))
        cols_m[2].metric("Valor", f"{m.get("value", 0):.3f}")
    else:
        st.info("Treine o modelo para ver as métricas (ml/metrics.json).")

    if plot_path.exists():
        st.image(str(plot_path), caption="Real vs Previsto (últimas amostras)", use_container_width=True)
