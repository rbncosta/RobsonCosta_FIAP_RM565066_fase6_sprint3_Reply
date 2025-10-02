-- consultas_demo.sql
-- Hermes Reply – Fase 5 • RM 565066
-- Consultas de demonstração para o schema (Oracle).
-- Observação: as views V_LEITURAS_24H, V_RESUMO_ATIVO_HORA e V_ANOMALIAS
--             são criadas pelo script db/schema_oracle_ptbr.sql

------------------------------------------------------------------------
-- 0) Sanidade geral (contagem por tabela)
------------------------------------------------------------------------
SELECT 'PLANTA' TABELA, COUNT(*) QTD FROM PLANTA
UNION ALL SELECT 'ATIVO', COUNT(*) FROM ATIVO
UNION ALL SELECT 'SENSOR', COUNT(*) FROM SENSOR
UNION ALL SELECT 'LEITURA_SENSOR', COUNT(*) FROM LEITURA_SENSOR
UNION ALL SELECT 'EVENTO_MANUTENCAO', COUNT(*) FROM EVENTO_MANUTENCAO;

------------------------------------------------------------------------
-- 1) Amostra de leituras (com JOINs)
------------------------------------------------------------------------
SELECT a.NOME AS ATIVO, s.TIPO_SENSOR, l.DATA_HORA, l.VALOR
FROM LEITURA_SENSOR l
JOIN SENSOR s ON s.SENSOR_ID = l.SENSOR_ID
JOIN ATIVO  a ON a.ATIVO_ID  = s.ATIVO_ID
ORDER BY l.DATA_HORA DESC
FETCH FIRST 10 ROWS ONLY;

------------------------------------------------------------------------
-- 2) Faixa temporal do dataset
------------------------------------------------------------------------
SELECT MIN(DATA_HORA) AS INICIO, MAX(DATA_HORA) AS FIM
FROM LEITURA_SENSOR;

------------------------------------------------------------------------
-- 3) Janela “últimas 24h” relativa ao fim do dataset
------------------------------------------------------------------------
SELECT l.*
FROM LEITURA_SENSOR l
WHERE l.DATA_HORA >= (SELECT MAX(DATA_HORA) - INTERVAL '24' HOUR FROM LEITURA_SENSOR)
ORDER BY l.DATA_HORA DESC
FETCH FIRST 50 ROWS ONLY;

------------------------------------------------------------------------
-- 4) Médias por hora e ativo (agregado)
------------------------------------------------------------------------
SELECT a.ATIVO_ID,
       TRUNC(l.DATA_HORA) AS DIA,
       EXTRACT(HOUR FROM l.DATA_HORA) AS HORA,
       AVG(l.VALOR) AS MEDIA_VALOR
FROM LEITURA_SENSOR l
JOIN SENSOR s ON s.SENSOR_ID = l.SENSOR_ID
JOIN ATIVO  a ON a.ATIVO_ID  = s.ATIVO_ID
GROUP BY a.ATIVO_ID, TRUNC(l.DATA_HORA), EXTRACT(HOUR FROM l.DATA_HORA)
ORDER BY DIA, HORA, a.ATIVO_ID;

------------------------------------------------------------------------
-- 5) Usando a VIEW V_RESUMO_ATIVO_HORA
------------------------------------------------------------------------
SELECT *
FROM V_RESUMO_ATIVO_HORA
WHERE ATIVO_ID = 1
ORDER BY DIA, HORA
FETCH FIRST 24 ROWS ONLY;

------------------------------------------------------------------------
-- 6) Top 3 ativos por vibração média no último dia do dataset
------------------------------------------------------------------------
WITH MAXD AS (SELECT TRUNC(MAX(DATA_HORA)) AS DIA_MAX FROM LEITURA_SENSOR)
SELECT *
FROM (
  SELECT a.ATIVO_ID, a.NOME, AVG(l.VALOR) AS MEDIA_VIBRACAO
  FROM LEITURA_SENSOR l
  JOIN SENSOR s ON s.SENSOR_ID = l.SENSOR_ID AND s.TIPO_SENSOR = 'VIBRACAO'
  JOIN ATIVO  a ON a.ATIVO_ID  = s.ATIVO_ID
  WHERE TRUNC(l.DATA_HORA) = (SELECT DIA_MAX FROM MAXD)
  GROUP BY a.ATIVO_ID, a.NOME
  ORDER BY MEDIA_VIBRACAO DESC
)
FETCH FIRST 3 ROWS ONLY;

------------------------------------------------------------------------
-- 7) Catálogo: tipos de sensores por ativo
------------------------------------------------------------------------
SELECT a.ATIVO_ID, a.NOME,
       LISTAGG(s.TIPO_SENSOR, ', ') WITHIN GROUP (ORDER BY s.TIPO_SENSOR) AS TIPOS
FROM SENSOR s
JOIN ATIVO a ON a.ATIVO_ID = s.ATIVO_ID
GROUP BY a.ATIVO_ID, a.NOME
ORDER BY a.ATIVO_ID;

------------------------------------------------------------------------
-- 8) Últimas N leituras por sensor (analítico)
------------------------------------------------------------------------
SELECT SENSOR_ID, DATA_HORA, VALOR
FROM (
  SELECT l.*,
         ROW_NUMBER() OVER (PARTITION BY SENSOR_ID ORDER BY DATA_HORA DESC) AS RN
  FROM LEITURA_SENSOR l
)
WHERE RN <= 5
ORDER BY SENSOR_ID, DATA_HORA DESC;

------------------------------------------------------------------------
-- 9) Média móvel de 5 leituras para um sensor
------------------------------------------------------------------------
SELECT SENSOR_ID, DATA_HORA, VALOR,
       AVG(VALOR) OVER (
         PARTITION BY SENSOR_ID
         ORDER BY DATA_HORA
         ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
       ) AS MEDIA_MOVEL_5
FROM LEITURA_SENSOR
WHERE SENSOR_ID = 1
ORDER BY DATA_HORA
FETCH FIRST 20 ROWS ONLY;

------------------------------------------------------------------------
-- 10) Demonstração da VIEW V_ANOMALIAS
--     (define um limite e consulta as leituras fora do range)
------------------------------------------------------------------------
UPDATE SENSOR
   SET VALOR_MAX = 72
 WHERE TIPO_SENSOR = 'TEMPERATURA';
COMMIT;

SELECT *
FROM V_ANOMALIAS
ORDER BY DATA_HORA DESC
FETCH FIRST 20 ROWS ONLY;

-- (Opcional) Restaurar os limites:
-- UPDATE SENSOR SET VALOR_MAX = NULL WHERE TIPO_SENSOR = 'TEMPERATURA';
-- COMMIT;

------------------------------------------------------------------------
-- 11) Distribuição por tipo de sensor
------------------------------------------------------------------------
SELECT s.TIPO_SENSOR, COUNT(*) AS QTD
FROM LEITURA_SENSOR l
JOIN SENSOR s ON s.SENSOR_ID = l.SENSOR_ID
GROUP BY s.TIPO_SENSOR
ORDER BY QTD DESC;

------------------------------------------------------------------------
-- 12) Janela temporal explícita (filtrar por período)
------------------------------------------------------------------------
SELECT a.NOME AS ATIVO, s.TIPO_SENSOR, l.DATA_HORA, l.VALOR
FROM LEITURA_SENSOR l
JOIN SENSOR s ON s.SENSOR_ID = l.SENSOR_ID
JOIN ATIVO  a ON a.ATIVO_ID  = s.ATIVO_ID
WHERE l.DATA_HORA BETWEEN TIMESTAMP '2025-07-02 08:00:00'
                      AND     TIMESTAMP '2025-07-02 12:00:00'
ORDER BY l.DATA_HORA;

------------------------------------------------------------------------
-- 13) Usando a VIEW V_LEITURAS_24H (pode retornar 0 linhas se o relógio atual
--     não coincide com o período do dataset; use a consulta #3 para janela relativa)
------------------------------------------------------------------------
SELECT * FROM V_LEITURAS_24H
ORDER BY DATA_HORA DESC
FETCH FIRST 50 ROWS ONLY;