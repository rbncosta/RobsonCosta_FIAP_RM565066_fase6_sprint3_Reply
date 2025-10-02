#!/usr/bin/env python3
"""
esp32_fase4_log_to_csv_sql.py
--------------------------------
Converte um log/CSV do Serial (gerado pelo seu .ino da Fase 4 no formato:
  #contador,fosforo,potassio,ph,umidade,bomba
  1,0,1,6.80,75.0,1
  2,1,1,7.00,55.0,0
...)
em:
  1) data/leituras_sensores.csv   (colunas: ts,temperature,humidity)
  2) db/seed_oracle_from_fase4_log.sql  (INSERTs para Oracle)
Uso:
  python esp32_fase4_log_to_csv_sql.py --start-now --log ingest/esp32_serial.csv \
    --sensor-id-temp 1 --sensor-id-hum 2
"""

import argparse, csv, re, sys
from pathlib import Path
from datetime import datetime, timedelta
import random

HEADER_NAMES = ["contador","fosforo","potassio","ph","umidade","bomba"]
HEADER_LINE  = "#contador,fosforo,potassio,ph,umidade,bomba"

row_re = re.compile(
    r'^\s*(\d+)\s*,\s*([01])\s*,\s*([01])\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*,\s*([01])\s*$'
)

def derive_temperature(ph: float, umid: float) -> float:
    """Temperatura sintética coerente com pH e umidade (apenas para alimentar o pipeline)."""
    base = 25 + (umid - 50) / 2 + (ph - 7) * 4
    noise = random.uniform(-1.0, 1.5)
    val = max(18.0, min(90.0, base + noise))
    return round(val, 2)

def parse_serial_log(path: Path):
    rows = []
    if not path.exists():
        raise FileNotFoundError(f"Não encontrei o arquivo: {path}")
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Terminal on "):
                continue
            if line.lstrip("#").strip().lower() == ",".join(HEADER_NAMES):
                continue  # cabeçalho
            m = row_re.match(line)
            if not m:
                continue  # ignora linhas não-CSV
            contador  = int(m.group(1))
            fosforo   = int(m.group(2))
            potassio  = int(m.group(3))
            ph        = float(m.group(4))
            umidade   = float(m.group(5))
            bomba     = int(m.group(6))
            rows.append((contador, fosforo, potassio, ph, umidade, bomba))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="ingest/esp32_serial.csv", help="arquivo de entrada (log/CSV do serial)")
    ap.add_argument("--csv", default="data/leituras_sensores.csv", help="arquivo CSV de saída (ts,temperature,humidity)")
    ap.add_argument("--sql", default="db/seed_oracle_from_fase4_log.sql", help="script SQL de saída para Oracle")
    ap.add_argument("--sensor-id-temp", type=int, default=1, help="SENSOR_ID de TEMPERATURA no Oracle")
    ap.add_argument("--sensor-id-hum", type=int, default=2, help="SENSOR_ID de UMIDADE no Oracle")
    ap.add_argument("--interval-sec", type=int, default=120, help="intervalo entre amostras (segundos)")
    ap.add_argument("--start-now", action="store_true", help="usar timestamps a partir de agora (senão, começa no passado)")
    args = ap.parse_args()

    in_path = Path(args.log)
    out_csv = Path(args.csv)
    out_sql = Path(args.sql)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_sql.parent.mkdir(parents=True, exist_ok=True)

    rows = parse_serial_log(in_path)
    if not rows:
        print("ERRO: o arquivo não contém linhas CSV válidas no formato esperado.", file=sys.stderr)
        print(f"Dica: copie do monitor começando pelo cabeçalho: {HEADER_LINE}", file=sys.stderr)
        sys.exit(2)

    # Gerar timestamps
    if args.start_now:
        start_dt = datetime.now()
    else:
        start_dt = datetime.now() - timedelta(seconds=args.interval_sec * len(rows))
    interval = timedelta(seconds=args.interval_sec)

    # 1) CSV final
    with out_csv.open("w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(["ts","temperature","humidity"])
        for i, (_, _, _, ph, umid, _) in enumerate(rows):
            ts = start_dt + i * interval
            temp = derive_temperature(ph, umid)
            w.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"), f"{temp:.2f}", f"{umid:.2f}"])

    # 2) SQL para Oracle
    with out_sql.open("w", encoding="utf-8") as fsql:
        fsql.write("-- Script gerado automaticamente a partir do log do ESP32\n")
        fsql.write("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';\n")
        with out_csv.open("r", encoding="utf-8") as fcsv:
            reader = csv.DictReader(fcsv)
            for r in reader:
                ts = r["ts"]
                t  = str(r["temperature"]).replace(",", ".")
                h  = str(r["humidity"]).replace(",", ".")
                fsql.write(f"INSERT INTO LEITURA_SENSOR (SENSOR_ID, DATA_HORA, VALOR) VALUES ({args.sensor_id_temp}, TO_TIMESTAMP('{ts}','YYYY-MM-DD HH24:MI:SS'), {t});\n")
                fsql.write(f"INSERT INTO LEITURA_SENSOR (SENSOR_ID, DATA_HORA, VALOR) VALUES ({args.sensor_id_hum},  TO_TIMESTAMP('{ts}','YYYY-MM-DD HH24:MI:SS'), {h});\n")
        fsql.write("COMMIT;\n")

    print(f"OK: {len(rows)} linhas lidas de {in_path}")
    print(f"Gerado: {out_csv} e {out_sql}")
    print(f"Dica: rode no Oracle ->  @db/seed_oracle_from_fase4_log.sql")

if __name__ == "__main__":
    main()
