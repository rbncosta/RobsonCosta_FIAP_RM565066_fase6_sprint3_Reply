import os, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import oracledb
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# ===== Paths fixos =====
BASE_DIR = Path(__file__).resolve().parents[1]
ML_DIR   = BASE_DIR / "ml"
ML_DIR.mkdir(parents=True, exist_ok=True)
METRICS_PATH = ML_DIR / "metrics.json"
PLOT_PATH    = ML_DIR / "pred_vs_real.png"

# ===== Credenciais (ambiente) =====
ORA_USER = os.environ.get("ORA_USER", "RCOSTA")
ORA_PASSWORD = os.environ.get("ORA_PASSWORD", "")
ORA_DSN = os.environ.get("ORA_DSN", "localhost:1522/ORCLPDB")

# ===== IDs dos sensores (defina no seu terminal) =====
TEMP_ID = int(os.environ.get("ORA_SENSOR_TEMP_ID", "1"))   # ex.: 1
AUX_ID  = int(os.environ.get("ORA_SENSOR_AUX_ID",  "2"))   # ex.: 2
AUX_LABEL = os.environ.get("ORA_SENSOR_AUX_LABEL", "VIBRACAO")  # só rótulos

def _read_series(conn, sensor_id, colname):
    q = """
        SELECT l.data_hora AS data_hora, l.valor AS valor
        FROM leitura_sensor l
        WHERE l.sensor_id = :sid
        ORDER BY l.data_hora
    """
    df = pd.read_sql(q, conn, params={"sid": sensor_id})
    if df.empty:
        raise RuntimeError(f"Sem dados para SENSOR_ID={sensor_id}.")
    df.columns = [c.upper() for c in df.columns]   # DATA_HORA, VALOR
    df["DATA_HORA"] = pd.to_datetime(df["DATA_HORA"])
    df["VALOR"] = pd.to_numeric(df["VALOR"].astype(str).str.replace(",", "."), errors="coerce")
    # bucket por minuto para facilitar o pareamento
    df["T_MIN"] = df["DATA_HORA"].dt.floor("min")
    df = df.groupby("T_MIN", as_index=False)["VALOR"].mean().rename(columns={"VALOR": colname})
    return df

def load_df():
    print(f"[INFO] Conectando em {ORA_USER}@{ORA_DSN} ...")
    conn = oracledb.connect(user=ORA_USER, password=ORA_PASSWORD, dsn=ORA_DSN)
    try:
        dft = _read_series(conn, TEMP_ID, "TEMP")
        dfa = _read_series(conn, AUX_ID,  "AUX")
    finally:
        conn.close()

    # join exato por minuto
    wide = dft.merge(dfa, on="T_MIN", how="outer").sort_values("T_MIN")

    # se ainda houver buracos, alinhar por proximidade (2 min)
    if wide[["TEMP","AUX"]].dropna().empty:
        dft2 = dft[["T_MIN","TEMP"]].rename(columns={"T_MIN":"TS"}).sort_values("TS")
        dfa2 = dfa[["T_MIN","AUX"]].rename(columns={"T_MIN":"TS"}).sort_values("TS")
        wide = pd.merge_asof(dft2, dfa2, on="TS", direction="nearest",
                             tolerance=pd.Timedelta("2min")).rename(columns={"TS":"T_MIN"})

    wide = wide.dropna(subset=["TEMP","AUX"]).reset_index(drop=True)
    if wide.empty:
        raise RuntimeError("Não consegui formar pares TEMP/AUX mesmo com tolerância de 2min.")

    # alvo = temperatura no próximo instante
    wide["temp_next"] = wide["TEMP"].shift(-1)
    wide = wide.dropna(subset=["temp_next"]).reset_index(drop=True)
    print(f"[INFO] Amostras após preparo: {len(wide)}")
    return wide

if __name__ == "__main__":
    df = load_df()
    N = len(df)

    if N < 10:
        print(f"[AVISO] Poucos dados ({N}). Treinando e avaliando no próprio conjunto.")
        X = df[["TEMP","AUX"]].values
        y = df["temp_next"].values
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(X, y)
        ypred = model.predict(X)
        mae = float(mean_absolute_error(y, ypred))
        y_real_plot = y
    else:
        X = df[["TEMP","AUX"]].values
        y = df["temp_next"].values
        test_size = max(1, int(round(N*0.25)))
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=test_size, shuffle=False, random_state=42)
        model = RandomForestRegressor(n_estimators=200, random_state=42)
        model.fit(Xtr, ytr)
        ypred = model.predict(Xte)
        mae = float(mean_absolute_error(yte, ypred))
        y_real_plot = yte

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump({"model":"RandomForestRegressor","metric":"MAE","value":mae,
                   "aux_sensor_id": AUX_ID, "aux_label": AUX_LABEL}, f, ensure_ascii=False, indent=2)

    last = min(150, len(ypred))
    plt.figure(figsize=(10,4))
    plt.plot(range(last), y_real_plot[-last:], label="real")
    plt.plot(range(last), ypred[-last:], label="previsto")
    plt.title(f"Previsão de Temperatura (AUX={AUX_LABEL}, MAE={mae:.3f})")
    plt.xlabel("amostras (finais)")
    plt.ylabel("temperatura (°C)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_PATH, dpi=130)

    print(f"[OK] MAE={mae:.4f} | AUX={AUX_LABEL}")
    print(f"[OK] metrics.json  -> {METRICS_PATH.resolve()}")
    print(f"[OK] pred_vs_real -> {PLOT_PATH.resolve()}")
