SQL> 
SQL> SELECT dbms_metadata.get_ddl('VIEW', view_name) || CHR(10) || '/' || CHR(10)
  2  FROM   user_views
  3  WHERE  view_name LIKE 'DDT_PREZZI%'
  4      OR view_name = 'PRINT_DDT_DA_FATTURARE'
  5  ORDER  BY view_name;

  CREATE OR REPLACE FORCE EDITIONABLE VIEW "INTEX2"."DDT_PREZZI_000W" ("D02_KEY", "D02_CD_TIPO_BOLLA", "I01_CD_TIPO_DOCUMENTO", "D02_ANNO_BOLLA", "D02_NR_BOLLA", "D02_DT_BOLLA", "D02_CD_CLIENTE_FATT", "D02_CD_ASS_FISC", "D02_CD_VALUTA", "D02_FLAG_FATTURATA", "D03_ANNO_DISP_CLI", "D03_NR_DISP_CLI", "D03_RIGA_DISP_CLI", "D03_CAPI_IN_USCITA", "D03_KG_IN_USCITA", "D03_CD_IVA", "D03_SCONTO_01", "D03_SCONTO_02", "D03_PROVV_AGENTE", "D03_PROVV_AGENTE_2", "D03_PROVV_AGENTE_3", "D03_PROVV_AGENTE_4", "D03_CD_ARTICOLO", "D03_DS_ARTICOLO", "D03_CD_UNITA_MIS", "D03_QTA_IN_USCITA", "D03_NOTE", "D03_RIGA", "D03_COLORI_IN_USCITA", "D03_ANNO_CARTELLINO", "D03_NR_CARTELLINO", "D02_CD_AGENTE", "D02_CD_AGENTE_2", "D02_CD_AGENTE_3", "D02_CD_AGENTE_4", "D02_CD_ABI", "D02_CD_CAB", "D02_CD_PAGAMENTO") AS
  SELECT                -- ==================================================
         d02_ddt_testata.d02_key,
          d02_ddt_testata.d02_cd_tipo_bolla,
          i01_tipologia_bolle.i01_cd_tipo_documento,
          d02_ddt_testata.d02_anno_bolla,
          TRUNC (d02_ddt_testata.d02_nr_bolla),
          d02_ddt_testata.d02_dt_bolla,
          d02_ddt_testata.d02_cd_cliente_fatt,
          d02_ddt_testata.d02_cd_ass_fisc,
          d02_ddt_testata.d02_cd_valuta,
          d02_ddt_testata.d02_flag_fatturata,
          d03_ddt_righe_art.d03_anno_disp_cli,
          d03_ddt_righe_art.d03_nr_disp_cli,
          d03_ddt_righe_art.d03_riga_disp_cli,
          d03_ddt_righe_art.d03_capi_in_uscita,
          d03_ddt_righe_art.d03_kg_in_uscita,
          d03_ddt_righe_art.d03_cd_iva,
          d03_ddt_righe_art.d03_sconto_01,
          d03_ddt_righe_art.d03_sconto_02,
          d03_ddt_righe_art.d03_provv_agente,
          d03_ddt_righe_art.d03_provv_agente_2,
          d03_ddt_righe_art.d03_provv_agente_3,
          d03_ddt_righe_art.d03_provv_agente_4,
          d03_ddt_righe_art.d03_cd_articolo,
          d03_ddt_righe_art.d03_ds_articolo,
          d03_ddt_righe_art.d03_cd_unita_mis,
          d03_ddt_righe_art.d03_qta_in_uscita,
          --
          d03_ddt_righe_art.d03_note,
          --
          d03_riga,
          D03_DDT_RIGHE_ART.D03_COLORI_IN_USCITA,
          D03_DDT_RIGHE_ART.D03_ANNO_CARTELLINO,
          d03_ddt_righe_art.d03_nr_cartellino,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO
     -- ==================================================
     FROM                -- ==================================================
         d02_ddt_testata, i01_tipologia_bolle, d03_ddt_righe_art
    -- ==================================================
    WHERE                -- ==================================================
         d02_ddt_testata.d02_key = d03_ddt_righe_art.d03_key_d02
          AND d02_ddt_testata.d02_cd_tipo_bolla =
                 i01_tipologia_bolle.i01_cd_tipo_bolla(+)
          AND d02_ddt_testata.d02_flag_fatturata = 'N'
          AND (d03_ddt_righe_art.d03_nr_disp_cli IS NOT NULL
               AND d03_ddt_righe_art.d03_nr_disp_cli > 0)
          AND i01_tipologia_bolle.i01_cd_tipo_documento IS NOT NULL
/


  CREATE OR REPLACE FORCE EDITIONABLE VIEW "INTEX2"."DDT_PREZZI_001W" ("D02_KEY", "D02_CD_TIPO_BOLLA", "I01_CD_TIPO_DOCUMENTO", "D02_ANNO_BOLLA", "D02_NR_BOLLA", "D02_DT_BOLLA", "D02_CD_CLIENTE_FATT", "R07_RAGIONE_SOC", "R07_CD_PAGAMENTO", "R06_DS_PAGAMENTO", "R07_CD_ABI", "R07_CD_CAB", "C06_DENOMINAZIONE_BANCA", "C06_AGENZIA", "D02_CD_ASS_FISC", "C01_DS_IVA", "D02_CD_VALUTA", "D02_FLAG_FATTURATA", "D03_RIGA", "D03_ANNO_DISP_CLI", "D03_NR_DISP_CLI", "D03_RIGA_DISP_CLI", "D03_CAPI_IN_USCITA", "D03_KG_IN_USCITA", "D03_CD_IVA", "C01_PERC_IMPONIBILE", "D03_SCONTO_01", "D03_SCONTO_02", "D03_PROVV_AGENTE", "D03_PROVV_AGENTE_2", "D03_PROVV_AGENTE_3", "D03_PROVV_AGENTE_4", "D03_CD_ARTICOLO", "D03_DS_ARTICOLO", "D03_CD_UNITA_MIS", "G04_DS_UNITA_MIS", "D03_QTA_IN_USCITA", "EW2_CD_LINEA", "CW0_DS_LINEA", "EW2_CD_STAGIONE", "Z11_DS_STAGIONE", "EW2_CD_CLIENTE", "EW2_CD_ARTICOLO_FATTURA", "CWA_DS_ARTICOLO_CLIENTE", "EW2_CD_COMPOSIZIONE", "CW4_DS_COMPOSIZIONE", "EW2_CD_CICLO", "Z09_DS_CICLO", "Z09_FL_FATTURARE", "Z09_FL_PREZZO_ZERO", "EW2_FLAG_TP_PROD", "EW2_NR_CAPI_CARICATI", "EW2_KG_CARICATI", "D03_NOTE", "D03_COLORI_IN_USCITA", "D03_ANNO_CARTELLINO", "D03_NR_CARTELLINO", "CW4_CD_GRUPPO_COMPOSIZIONE", "D02_CD_AGENTE", "D02_CD_AGENTE_2", "D02_CD_AGENTE_3", "D02_CD_AGENTE_4", "D02_CD_ABI", "D02_CD_CAB", "D02_CD_PAGAMENTO", "EW2_CD_STAGIONE_PROD", "EW2_DS_ARTICOLO", "EW2_PRZ_UNITARIO", "EW2_FLAG_TIPO_PREZZO", "EW2_PRZ_UNITARIO_KG", "EW2_FLAG_TIPO_PREZZO_KG", "EW2_FLAG_TP_DDT") AS
  SELECT
    d.d02_key,
    d.d02_cd_tipo_bolla,
    d.i01_cd_tipo_documento,
    d.d02_anno_bolla,
    d.d02_nr_bolla,
    TRUNC(d.d02_dt_bolla) AS d02_dt_bolla,
    d.d02_cd_cliente_fatt,
    r.r07_ragione_soc,
    r.r07_cd_pagamento,
    r.r06_ds_pagamento,
    r.r07_cd_abi,
    r.r07_cd_cab,
    r.c06_denominazione_banca,
    r.c06_agenzia,
    d.d02_cd_ass_fisc,
    iva1.c01_ds_iva,
    d.d02_cd_valuta,
    d.d02_flag_fatturata,
    d.d03_riga,
    d.d03_anno_disp_cli,
    d.d03_nr_disp_cli,
    d.d03_riga_disp_cli,
    d.d03_capi_in_uscita,
    d.d03_kg_in_uscita,
    d.d03_cd_iva,
    iva2.c01_perc_imponibile,
    d.d03_sconto_01,
    d.d03_sconto_02,
    d.d03_provv_agente,
    d.d03_provv_agente_2,
    d.d03_provv_agente_3,
    d.d03_provv_agente_4,
    d.d03_cd_articolo,
    d.d03_ds_articolo,
    d.d03_cd_unita_mis,
    u.g04_ds_unita_mis,
    d.d03_qta_in_uscita,
    ew2.ew2_cd_linea,
    lin.cw0_ds_linea,
    ew2.ew2_cd_stagione,
    st.z11_ds_stagione,
    ew2.ew2_cd_cliente,
    ew2.ew2_cd_articolo_fattura,
    ac.cwa_ds_articolo_cliente,
    ew2.ew2_cd_composizione,
    comp.cw4_ds_composizione,
    ew2.ew2_cd_ciclo,
    z09.z09_ds_ciclo,
    z09.z09_fl_fatturare,
    z09.z09_fl_prezzo_zero,
    ew2.ew2_flag_tp_prod,
    ew2.ew2_nr_capi_caricati,
    ew2.ew2_kg_caricati,
    d.d03_note,
    d.d03_colori_in_uscita,
    d.d03_anno_cartellino,
    d.d03_nr_cartellino,
    comp.cw4_cd_gruppo_composizione,
    d.d02_cd_agente,
    d.d02_cd_agente_2,
    d.d02_cd_agente_3,
    d.d02_cd_agente_4,
    d.d02_cd_abi,
    d.d02_cd_cab,
    d.d02_cd_pagamento,
    ew2.ew2_cd_stagione_prod,
    ew2.ew2_ds_articolo,
    ew2.ew2_prz_unitario,
    ew2.ew2_flag_tipo_prezzo,
    ew2.ew2_prz_unitario_kg,
    ew2.ew2_flag_tipo_prezzo_kg,
    EW2_FLAG_TP_DDT
FROM ddt_prezzi_000w d
LEFT JOIN r07_r0236_c012456789_001w r
       ON d.d02_cd_cliente_fatt = r.r07_cd_cliente
LEFT JOIN c01_codici_iva iva1
       ON d.d02_cd_ass_fisc = iva1.c01_cd_iva
LEFT JOIN c01_codici_iva iva2
       ON d.d03_cd_iva = iva2.c01_cd_iva
LEFT JOIN g04_unita_misura u
       ON d.d03_cd_unita_mis = u.g04_cd_unita_mis
LEFT JOIN EW2_EW1_001W ew2
       ON d.d03_anno_disp_cli = ew2.ew2_anno_disposizione
      AND d.d03_nr_disp_cli   = ew2.ew2_nr_disposizione
      AND d.d03_riga_disp_cli = ew2.ew2_riga_disposizione
LEFT JOIN cw0_linea_tintoria lin
       ON ew2.ew2_cd_cliente = lin.cw0_cd_cliente
      AND ew2.ew2_cd_linea   = lin.cw0_cd_linea
LEFT JOIN z11_stagioni st
       ON ew2.ew2_cd_stagione = st.z11_cd_stagione
LEFT JOIN cwa_articoli_cliente ac
       ON ew2.ew2_cd_cliente          = ac.cwa_cd_cliente
      AND ew2.ew2_cd_articolo_fattura = ac.cwa_cd_articolo_cliente
LEFT JOIN cw4_composizioni comp
       ON ew2.ew2_cd_composizione = comp.cw4_cd_composizione
LEFT JOIN z09_testate_cicli_lavorazione z09
       ON ew2.ew2_cd_cliente           = z09.z09_cd_cliente
      AND ew2.ew2_cd_articolo_fattura  = z09.z09_cd_articolo_cliente
      AND ew2.ew2_cd_ciclo             = z09.z09_cd_ciclo
      AND ew2.EW2_COMP_Z09             = z09.Z09_CD_COMPOSIZIONE
      AND ew2.EW2_CD_LINEA             = z09.Z09_CD_LINEA
      AND ew2.EW2_CD_STAGIONE          = z09.Z09_CD_STAGIONE
WHERE
    (z09.z09_fl_fatturare = 'S' )-- OR (z09.z09_fl_fatturare IS NULL AND EW2_FLAG_TP_DDT  = 'L'));
/


  CREATE OR REPLACE FORCE EDITIONABLE VIEW "INTEX2"."DDT_PREZZI_002W" ("D02_KEY", "D02_CD_TIPO_BOLLA", "I01_CD_TIPO_DOCUMENTO", "D02_ANNO_BOLLA", "D02_NR_BOLLA", "D02_DT_BOLLA", "D02_CD_CLIENTE_FATT", "R07_RAGIONE_SOC", "R07_CD_PAGAMENTO", "R06_DS_PAGAMENTO", "R07_CD_ABI", "R07_CD_CAB", "C06_DENOMINAZIONE_BANCA", "C06_AGENZIA", "D02_CD_ASS_FISC", "C01_DS_IVA", "D02_CD_VALUTA", "D02_FLAG_FATTURATA", "D03_RIGA", "D03_ANNO_DISP_CLI", "D03_NR_DISP_CLI", "D03_RIGA_DISP_CLI", "D03_CAPI_IN_USCITA", "D03_KG_IN_USCITA", "D03_CD_IVA", "C01_PERC_IMPONIBILE", "D03_SCONTO_01", "D03_SCONTO_02", "D03_PROVV_AGENTE", "D03_PROVV_AGENTE_2", "D03_PROVV_AGENTE_3", "D03_PROVV_AGENTE_4", "D03_CD_ARTICOLO", "D03_DS_ARTICOLO", "D03_CD_UNITA_MIS", "G04_DS_UNITA_MIS", "D03_QTA_IN_USCITA", "EW2_CD_LINEA", "CW0_DS_LINEA", "EW2_CD_STAGIONE", "Z11_DS_STAGIONE", "EW2_CD_CLIENTE", "EW2_CD_ARTICOLO_FATTURA", "CWA_DS_ARTICOLO_CLIENTE", "EW2_CD_COMPOSIZIONE", "CW4_DS_COMPOSIZIONE", "EW2_CD_CICLO", "Z09_DS_CICLO", "Z09_FL_FATTURARE", "Z09_FL_PREZZO_ZERO", "EW2_FLAG_TP_PROD", "EW2_NR_CAPI_CARICATI", "EW2_KG_CARICATI", "D03_PREZZO_UNI", "D03_PREZZO_CAPO", "D03_PREZZO_KG", "D03_PREZZO_FORFAIT", "D03_NOTE", "D03_FLAG_PREZZO_FORFAIT", "TIPO", "D03_PREZZO_COLORE", "D03_COLORI_IN_USCITA", "D03_ANNO_CARTELLINO", "D03_NR_CARTELLINO", "P07_NR_BAGNO", "D03_PREZZO_FORFAIT_KG", "D03_PREZZO_FORFAIT_NR", "CAPIUSARE", "P07_KG_PROGRAMMATI", "P07_NR_CAPI_PROGRAMMATI", "CW4_CD_GRUPPO_COMPOSIZIONE", "P06_FLAG_USAKGINRICERCAPREZZI", "CODICERAGGRUPPAMENTO", "D02_CD_AGENTE", "D02_CD_AGENTE_2", "D02_CD_AGENTE_3", "D02_CD_AGENTE_4", "D02_CD_ABI", "D02_CD_CAB", "D02_CD_PAGAMENTO", "EW2_FLAG_TIPO_PREZZO", "EW2_PRZ_UNITARIO", "EW2_FLAG_TIPO_PREZZO_KG", "EW2_PRZ_UNITARIO_KG") AS
  SELECT                               -- Righe cartellini in bolla con bagno
         ddt_prezzi_001w.d02_key,
          ddt_prezzi_001w.d02_cd_tipo_bolla,
          ddt_prezzi_001w.i01_cd_tipo_documento,
          ddt_prezzi_001w.d02_anno_bolla,
          ddt_prezzi_001w.d02_nr_bolla,
          ddt_prezzi_001w.d02_dt_bolla,
          ddt_prezzi_001w.d02_cd_cliente_fatt,
          ddt_prezzi_001w.r07_ragione_soc,
          ddt_prezzi_001w.r07_cd_pagamento,
          ddt_prezzi_001w.r06_ds_pagamento,
          ddt_prezzi_001w.r07_cd_abi,
          ddt_prezzi_001w.r07_cd_cab,
          ddt_prezzi_001w.c06_denominazione_banca,
          ddt_prezzi_001w.c06_agenzia,
          ddt_prezzi_001w.d02_cd_ass_fisc,
          ddt_prezzi_001w.c01_ds_iva,
          ddt_prezzi_001w.d02_cd_valuta,
          ddt_prezzi_001w.d02_flag_fatturata,
          ddt_prezzi_001w.d03_riga,
          ddt_prezzi_001w.d03_anno_disp_cli,
          ddt_prezzi_001w.d03_nr_disp_cli,
          ddt_prezzi_001w.d03_riga_disp_cli,
          ddt_prezzi_001w.d03_capi_in_uscita,
          ddt_prezzi_001w.d03_kg_in_uscita,
          ddt_prezzi_001w.d03_cd_iva,
          ddt_prezzi_001w.c01_perc_imponibile,
          ddt_prezzi_001w.d03_sconto_01,
          ddt_prezzi_001w.d03_sconto_02,
          ddt_prezzi_001w.d03_provv_agente,
          ddt_prezzi_001w.d03_provv_agente_2,
          ddt_prezzi_001w.d03_provv_agente_3,
          ddt_prezzi_001w.d03_provv_agente_4,
          ddt_prezzi_001w.d03_cd_articolo,
          ddt_prezzi_001w.d03_ds_articolo,
          ddt_prezzi_001w.d03_cd_unita_mis,
          ddt_prezzi_001w.g04_ds_unita_mis,
          ddt_prezzi_001w.d03_qta_in_uscita,
          ddt_prezzi_001w.ew2_cd_linea,
          ddt_prezzi_001w.cw0_ds_linea,
          ddt_prezzi_001w.ew2_cd_stagione,
          ddt_prezzi_001w.z11_ds_stagione,
          ddt_prezzi_001w.ew2_cd_cliente,
          ddt_prezzi_001w.ew2_cd_articolo_fattura,
          ddt_prezzi_001w.cwa_ds_articolo_cliente,
          ddt_prezzi_001w.ew2_cd_composizione,
          ddt_prezzi_001w.cw4_ds_composizione,
          ddt_prezzi_001w.ew2_cd_ciclo,
          ddt_prezzi_001w.z09_ds_ciclo,
          ddt_prezzi_001w.z09_fl_fatturare,
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
               'S'
             ELSE
             ddt_prezzi_001w.z09_fl_prezzo_zero
           END,

          ddt_prezzi_001w.ew2_flag_tp_prod,
          ddt_prezzi_001w.ew2_nr_capi_caricati,
          ddt_prezzi_001w.ew2_kg_caricati,
          0,                                                  --D03_PREZZO_UNI
          -------------------------------------------------------------------------------------------------------------------------------------
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO,
                   'C', EW2_PRZ_UNITARIO,
                   'F', 0,
                   getprezzocapo (ddt_prezzi_001w.d02_cd_cliente_fatt,
                                  ddt_prezzi_001w.ew2_cd_linea,
                                  ddt_prezzi_001w.ew2_cd_stagione,
                                  ddt_prezzi_001w.ew2_cd_composizione,
                                  ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                                  ddt_prezzi_001w.ew2_cd_articolo_fattura,
                                  ddt_prezzi_001w.ew2_cd_ciclo,
                                  ddt_prezzi_001w.ew2_flag_tp_prod,
                                  fat_getcapidausare (d02_key, d03_riga))) -- D03_PREZZO_CAPO
          END
             AS D03_PREZZO_CAPO,
          -------------------------------------------------------------------------------------------------------------------------------------
          -- Modifica effettuata: calcolo il prezzo a Kg in base al numero di Kg nella disposizione (se specificati) o, nel caso
          -- fossero a 0 o null, in base al numero di Kg in uscita del DDT
          ---------------------------------------------------
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO_KG,
                   'K', EW2_PRZ_UNITARIO_KG,
                   'G', 0,
                   getprezzokg (ddt_prezzi_001w.d02_cd_cliente_fatt,
                                ddt_prezzi_001w.ew2_cd_linea,
                                ddt_prezzi_001w.ew2_cd_stagione,
                                ddt_prezzi_001w.ew2_cd_composizione,
                                ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                                ddt_prezzi_001w.ew2_cd_articolo_fattura,
                                ddt_prezzi_001w.ew2_cd_ciclo,
                                ddt_prezzi_001w.ew2_flag_tp_prod,
                                fat_getkgdausare (d02_key, d03_riga))) --D03_PREZZO_KG4
          END
             AS D03_PREZZO_KG4,
          -----------------------------------------------------------------------------------------------------
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO,
                   'L', getprezzoforfait (
                           ddt_prezzi_001w.d02_cd_cliente_fatt,
                           ddt_prezzi_001w.ew2_cd_linea,
                           ddt_prezzi_001w.ew2_cd_stagione,
                           ddt_prezzi_001w.ew2_cd_composizione,
                           ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                           ddt_prezzi_001w.ew2_cd_articolo_fattura,
                           ddt_prezzi_001w.ew2_cd_ciclo,
                           ddt_prezzi_001w.ew2_flag_tp_prod,
                           fat_getcapidausare (d02_key, d03_riga),
                           fat_getkgdausare (d02_key, d03_riga)),
                   Forfait_Dispo (P06_ANNO_DISPOSIZIONE,
                                  P06_NR_DISPOSIZIONE,
                                  P06_RIGA_DISPOSIZIONE))
          END,                                            --D03_PREZZO_FORFAIT
          --
          --
          ddt_prezzi_001w.d03_note,
          ----------------------------------------------------------------------------------------------------------------------------------------

          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                'N'
             ELSE
                CASE
                   WHEN (EW2_FLAG_TIPO_PREZZO = 'L')
                        AND (EW2_FLAG_TIPO_PREZZO_KG = 'L')
                   THEN
                      getflagprezzoforfait (
                         ddt_prezzi_001w.d02_cd_cliente_fatt,
                         ddt_prezzi_001w.ew2_cd_linea,
                         ddt_prezzi_001w.ew2_cd_stagione,
                         ddt_prezzi_001w.ew2_cd_composizione,
                         ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                         ddt_prezzi_001w.ew2_cd_articolo_fattura,
                         ddt_prezzi_001w.ew2_cd_ciclo,
                         ddt_prezzi_001w.ew2_flag_tp_prod,
                         fat_getcapidausare (d02_key, d03_riga),
                         fat_getkgdausare (d02_key, d03_riga))
                   ELSE
                      Flag_Forfait_Dispo (P06_ANNO_DISPOSIZIONE,
                                          P06_NR_DISPOSIZIONE,
                                          P06_RIGA_DISPOSIZIONE)
                END
          END,                           --D03_FLAG_PREZZO_FORFAIT          --
          ----------------------------------------------------------------------------------------------------------------------------------------

          'Z08' AS tipo,
          getprezzocolore (ddt_prezzi_001w.d02_cd_cliente_fatt,
                           ddt_prezzi_001w.ew2_cd_linea,
                           ddt_prezzi_001w.ew2_cd_stagione,
                           ddt_prezzi_001w.ew2_cd_composizione,
                           ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                           ddt_prezzi_001w.ew2_cd_articolo_fattura,
                           ddt_prezzi_001w.ew2_cd_ciclo,
                           ddt_prezzi_001w.ew2_flag_tp_prod,
                           FAT_GetColoriDaUsare (d02_key, d03_riga)), --D03_PREZZO_COLORE
          D03_COLORI_IN_USCITA,
          d03_anno_cartellino,
          d03_nr_cartellino,
          P07_NR_BAGNO,
          -------------------------------------------------------------------------------------------------------

          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO_KG,
                   'K', 0,
                   'G', EW2_PRZ_UNITARIO_KG,
                   getprezzoforfaitspecifico (
                      'K',
                      ddt_prezzi_001w.d02_cd_cliente_fatt,
                      ddt_prezzi_001w.ew2_cd_linea,
                      ddt_prezzi_001w.ew2_cd_stagione,
                      ddt_prezzi_001w.ew2_cd_composizione,
                      ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                      ddt_prezzi_001w.ew2_cd_articolo_fattura,
                      ddt_prezzi_001w.ew2_cd_ciclo,
                      ddt_prezzi_001w.ew2_flag_tp_prod,
                      fat_getcapidausare (d02_key, d03_riga),
                      fat_getkgdausare (d02_key, d03_riga)))
          END,                                         --D03_PREZZO_FORFAIT_KG
          ------------------------------------------------------------------------------------------------------

          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO,
                   'C', 0,
                   'F', EW2_PRZ_UNITARIO,
                   getprezzoforfaitspecifico (
                      'C',
                      ddt_prezzi_001w.d02_cd_cliente_fatt,
                      ddt_prezzi_001w.ew2_cd_linea,
                      ddt_prezzi_001w.ew2_cd_stagione,
                      ddt_prezzi_001w.ew2_cd_composizione,
                      ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                      ddt_prezzi_001w.ew2_cd_articolo_fattura,
                      ddt_prezzi_001w.ew2_cd_ciclo,
                      ddt_prezzi_001w.ew2_flag_tp_prod,
                      fat_getcapidausare (d02_key, d03_riga),
                      fat_getkgdausare (d02_key, d03_riga)))
          END,                                         --D03_PREZZO_FORFAIT_NR
          --------------------------
          fat_getcapidausare (d02_key, d03_riga) AS Capiusare,
          -----------------------------
          P07_KG_PROGRAMMATI,
          P07_NR_CAPI_PROGRAMMATI,
          ddt_prezzi_001w.CW4_CD_GRUPPO_COMPOSIZIONE,
          P06.P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          EW2_FLAG_TIPO_PREZZO,
          EW2_PRZ_UNITARIO,
          EW2_FLAG_TIPO_PREZZO_KG,
          EW2_PRZ_UNITARIO_KG
     -- ------------------------------------------------
     FROM ddt_prezzi_001w
          LEFT JOIN p07_cicli_cartellini
             ON (    d03_anno_cartellino = p07_anno_cartellino
                 AND d03_nr_cartellino = p07_nr_cartellino
                 AND P07_NR_BAGNO > 0)
          LEFT JOIN P06_CARTELLINI_PROD P06
             ON (P06_ANNO_CARTELLINO = p07_anno_cartellino
                 AND P06_NR_CARTELLINO = p07_nr_cartellino)
    WHERE p07_sequenza =
             (SELECT MAX (p07_sequenza)
                FROM p07_cicli_cartellini
               WHERE     d03_anno_cartellino = p07_anno_cartellino
                     AND d03_nr_cartellino = p07_nr_cartellino
                     AND P07_NR_BAGNO > 0)
   UNION
   -- ------------------------------------------------
   SELECT                             -- Righe cartellini in bolla senza bagno
         ddt_prezzi_001w.d02_key,
          ddt_prezzi_001w.d02_cd_tipo_bolla,
          ddt_prezzi_001w.i01_cd_tipo_documento,
          ddt_prezzi_001w.d02_anno_bolla,
          ddt_prezzi_001w.d02_nr_bolla,
          ddt_prezzi_001w.d02_dt_bolla,
          ddt_prezzi_001w.d02_cd_cliente_fatt,
          ddt_prezzi_001w.r07_ragione_soc,
          ddt_prezzi_001w.r07_cd_pagamento,
          ddt_prezzi_001w.r06_ds_pagamento,
          ddt_prezzi_001w.r07_cd_abi,
          ddt_prezzi_001w.r07_cd_cab,
          ddt_prezzi_001w.c06_denominazione_banca,
          ddt_prezzi_001w.c06_agenzia,
          ddt_prezzi_001w.d02_cd_ass_fisc,
          ddt_prezzi_001w.c01_ds_iva,
          ddt_prezzi_001w.d02_cd_valuta,
          ddt_prezzi_001w.d02_flag_fatturata,
          ddt_prezzi_001w.d03_riga,
          ddt_prezzi_001w.d03_anno_disp_cli,
          ddt_prezzi_001w.d03_nr_disp_cli,
          ddt_prezzi_001w.d03_riga_disp_cli,
          ddt_prezzi_001w.d03_capi_in_uscita,
          ddt_prezzi_001w.d03_kg_in_uscita,
          ddt_prezzi_001w.d03_cd_iva,
          ddt_prezzi_001w.c01_perc_imponibile,
          ddt_prezzi_001w.d03_sconto_01,
          ddt_prezzi_001w.d03_sconto_02,
          ddt_prezzi_001w.d03_provv_agente,
          ddt_prezzi_001w.d03_provv_agente_2,
          ddt_prezzi_001w.d03_provv_agente_3,
          ddt_prezzi_001w.d03_provv_agente_4,
          ddt_prezzi_001w.d03_cd_articolo,
          ddt_prezzi_001w.d03_ds_articolo,
          ddt_prezzi_001w.d03_cd_unita_mis,
          ddt_prezzi_001w.g04_ds_unita_mis,
          ddt_prezzi_001w.d03_qta_in_uscita,
          ddt_prezzi_001w.ew2_cd_linea,
          ddt_prezzi_001w.cw0_ds_linea,
          ddt_prezzi_001w.ew2_cd_stagione,
          ddt_prezzi_001w.z11_ds_stagione,
          ddt_prezzi_001w.ew2_cd_cliente,
          ddt_prezzi_001w.ew2_cd_articolo_fattura,
          ddt_prezzi_001w.cwa_ds_articolo_cliente,
          ddt_prezzi_001w.ew2_cd_composizione,
          ddt_prezzi_001w.cw4_ds_composizione,
          ddt_prezzi_001w.ew2_cd_ciclo,
          ddt_prezzi_001w.z09_ds_ciclo,
          ddt_prezzi_001w.z09_fl_fatturare,

          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
               'S'
             ELSE
             ddt_prezzi_001w.z09_fl_prezzo_zero
           END,

          ddt_prezzi_001w.ew2_flag_tp_prod,
          ddt_prezzi_001w.ew2_nr_capi_caricati,
          ddt_prezzi_001w.ew2_kg_caricati,
          0,
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO,
                   'C', EW2_PRZ_UNITARIO,
                   'F', 0,
                   getprezzocapo (ddt_prezzi_001w.d02_cd_cliente_fatt,
                                  ddt_prezzi_001w.ew2_cd_linea,
                                  ddt_prezzi_001w.ew2_cd_stagione,
                                  ddt_prezzi_001w.ew2_cd_composizione,
                                  ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                                  ddt_prezzi_001w.ew2_cd_articolo_fattura,
                                  ddt_prezzi_001w.ew2_cd_ciclo,
                                  ddt_prezzi_001w.ew2_flag_tp_prod,
                                  fat_getcapidausare (d02_key, d03_riga)))
          END,                                              -- D03_PREZZO_CAPO
          -----------------------------------------------------------------------------------------------------------------------------------------------
          -- Modifica effettuata: calcolo il prezzo a Kg in base al numero di Kg nella disposizione (se specificati) o, nel caso
          -- fossero a 0 o null, in base al numero di Kg in uscita del DDT
          -- Modifica effettuata: calcolo il prezzo a Kg in base al numero di Kg nella disposizione (se specificati) o, nel caso
          -- fossero a 0 o null, in base al numero di Kg in uscita del DDT
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO_KG,
                   'K', EW2_PRZ_UNITARIO_KG,
                   'G', 0,
                   getprezzokg (ddt_prezzi_001w.d02_cd_cliente_fatt,
                                ddt_prezzi_001w.ew2_cd_linea,
                                ddt_prezzi_001w.ew2_cd_stagione,
                                ddt_prezzi_001w.ew2_cd_composizione,
                                ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                                ddt_prezzi_001w.ew2_cd_articolo_fattura,
                                ddt_prezzi_001w.ew2_cd_ciclo,
                                ddt_prezzi_001w.ew2_flag_tp_prod,
                                fat_getkgdausare (d02_key, d03_riga)))
          END,                                                 --D03_PREZZO_KG
          -----------------------------------------------------------------------------------------------------------------------------------------------
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO,
                   'L', getprezzoforfait (
                           ddt_prezzi_001w.d02_cd_cliente_fatt,
                           ddt_prezzi_001w.ew2_cd_linea,
                           ddt_prezzi_001w.ew2_cd_stagione,
                           ddt_prezzi_001w.ew2_cd_composizione,
                           ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                           ddt_prezzi_001w.ew2_cd_articolo_fattura,
                           ddt_prezzi_001w.ew2_cd_ciclo,
                           ddt_prezzi_001w.ew2_flag_tp_prod,
                           fat_getcapidausare (d02_key, d03_riga),
                           fat_getkgdausare (d02_key, d03_riga)),
                   Forfait_Dispo (D03_ANNO_DISP_CLI,
                                  D03_NR_DISP_CLI,
                                  D03_RIGA_DISP_CLI))
          END,                                            --D03_PREZZO_FORFAIT
          -----------------------------------------------------------------------------------------------------------------------------------------------
          --
          ddt_prezzi_001w.d03_note,
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                'N'
             ELSE
                -----------------------------------------------------------------------------------------------------------------
                CASE
                   WHEN (EW2_FLAG_TIPO_PREZZO = 'L')
                        AND (EW2_FLAG_TIPO_PREZZO_KG = 'L')
                   THEN
                      getflagprezzoforfait (
                         ddt_prezzi_001w.d02_cd_cliente_fatt,
                         ddt_prezzi_001w.ew2_cd_linea,
                         ddt_prezzi_001w.ew2_cd_stagione,
                         ddt_prezzi_001w.ew2_cd_composizione,
                         ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                         ddt_prezzi_001w.ew2_cd_articolo_fattura,
                         ddt_prezzi_001w.ew2_cd_ciclo,
                         ddt_prezzi_001w.ew2_flag_tp_prod,
                         fat_getcapidausare (d02_key, d03_riga),
                         fat_getkgdausare (d02_key, d03_riga))
                   ELSE
                      Flag_Forfait_Dispo (D03_ANNO_DISP_CLI,
                                          D03_NR_DISP_CLI,
                                          D03_RIGA_DISP_CLI)
                END
          END,                                       --D03_FLAG_PREZZO_FORFAIT
          ---------------------------------------------------------------------------------------------------------------------------------------------------------
          --
          'Z08' AS tipo,
          getprezzocolore (ddt_prezzi_001w.d02_cd_cliente_fatt,
                           ddt_prezzi_001w.ew2_cd_linea,
                           ddt_prezzi_001w.ew2_cd_stagione,
                           ddt_prezzi_001w.ew2_cd_composizione,
                           ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                           ddt_prezzi_001w.ew2_cd_articolo_fattura,
                           ddt_prezzi_001w.ew2_cd_ciclo,
                           ddt_prezzi_001w.ew2_flag_tp_prod,
                           FAT_GetColoriDaUsare (d02_key, d03_riga)),
          D03_COLORI_IN_USCITA,
          d03_anno_cartellino,
          d03_nr_cartellino,
          0 AS P07_NR_BAGNO,
          -------------------------------------------------------------------------------------------------------------------
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO_KG,
                   'K', 0,
                   'G', EW2_PRZ_UNITARIO_KG,
                   getprezzoforfaitspecifico (
                      'K',
                      ddt_prezzi_001w.d02_cd_cliente_fatt,
                      ddt_prezzi_001w.ew2_cd_linea,
                      ddt_prezzi_001w.ew2_cd_stagione,
                      ddt_prezzi_001w.ew2_cd_composizione,
                      ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                      ddt_prezzi_001w.ew2_cd_articolo_fattura,
                      ddt_prezzi_001w.ew2_cd_ciclo,
                      ddt_prezzi_001w.ew2_flag_tp_prod,
                      fat_getcapidausare (d02_key, d03_riga),
                      fat_getkgdausare (d02_key, d03_riga)))
          END,                                         --D03_PREZZO_FORFAIT_KG
          ------------------------------------------------------------------------------------------------------------
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (
                   EW2_FLAG_TIPO_PREZZO,
                   'C', 0,
                   'F', EW2_PRZ_UNITARIO,
                   getprezzoforfaitspecifico (
                      'C',
                      ddt_prezzi_001w.d02_cd_cliente_fatt,
                      ddt_prezzi_001w.ew2_cd_linea,
                      ddt_prezzi_001w.ew2_cd_stagione,
                      ddt_prezzi_001w.ew2_cd_composizione,
                      ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                      ddt_prezzi_001w.ew2_cd_articolo_fattura,
                      ddt_prezzi_001w.ew2_cd_ciclo,
                      ddt_prezzi_001w.ew2_flag_tp_prod,
                      fat_getcapidausare (d02_key, d03_riga),
                      fat_getkgdausare (d02_key, d03_riga)))
          END,                                         --D03_PREZZO_FORFAIT_NR
          ----------------------------------------------------------------------------------------------------------
          fat_getcapidausare (d02_key, d03_riga) AS Capiusare,
          --------------------------
          fat_getkgdausare (d02_key, d03_riga),
          fat_getcapidausare (d02_key, d03_riga),
          ddt_prezzi_001w.CW4_CD_GRUPPO_COMPOSIZIONE,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          EW2_FLAG_TIPO_PREZZO,
          EW2_PRZ_UNITARIO,
          EW2_FLAG_TIPO_PREZZO_KG,
          EW2_PRZ_UNITARIO_KG
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         ddt_prezzi_001w
    WHERE (SELECT COUNT (*)
             FROM p07_cicli_cartellini
            WHERE (    d03_anno_cartellino = p07_anno_cartellino
                   AND d03_nr_cartellino = p07_nr_cartellino
                   AND P07_NR_BAGNO > 0)) = 0
   -- ------------------------------------------------
   UNION
   -- ------------------------------------------------
   SELECT                                                        -- Fasi extra
         d02_ddt_testata.d02_key,
          d02_ddt_testata.d02_cd_tipo_bolla,
          i01_tipologia_bolle.i01_cd_tipo_documento,
          d02_ddt_testata.d02_anno_bolla,
          d02_ddt_testata.d02_nr_bolla,
          d02_ddt_testata.d02_dt_bolla,
          d02_ddt_testata.d02_cd_cliente_fatt,
          r07_r0236_c012456789_001w.r07_ragione_soc,
          r07_r0236_c012456789_001w.r07_cd_pagamento,
          r07_r0236_c012456789_001w.r06_ds_pagamento,
          r07_r0236_c012456789_001w.r07_cd_abi,
          r07_r0236_c012456789_001w.r07_cd_cab,
          r07_r0236_c012456789_001w.c06_denominazione_banca,
          r07_r0236_c012456789_001w.c06_agenzia,
          d02_ddt_testata.d02_cd_ass_fisc,
          c01_codici_iva_01.c01_ds_iva,
          d02_ddt_testata.d02_cd_valuta,
          d02_ddt_testata.d02_flag_fatturata,
          d03_ddt_righe_art.d03_riga,
          d03_ddt_righe_art.d03_anno_disp_cli,
          d03_ddt_righe_art.d03_nr_disp_cli,
          d03_ddt_righe_art.d03_riga_disp_cli,
          d03_ddt_righe_art.d03_capi_in_uscita,
          d03_ddt_righe_art.d03_kg_in_uscita,
          d03_ddt_righe_art.d03_cd_iva,
          c01_codici_iva_02.c01_perc_imponibile,
          d03_ddt_righe_art.d03_sconto_01,
          d03_ddt_righe_art.d03_sconto_02,
          d03_ddt_righe_art.d03_provv_agente,
          d03_ddt_righe_art.d03_provv_agente_2,
          d03_ddt_righe_art.d03_provv_agente_3,
          d03_ddt_righe_art.d03_provv_agente_4,
          d03_ddt_righe_art.d03_cd_articolo,
          d03_ddt_righe_art.d03_ds_articolo,
          d03_ddt_righe_art.d03_cd_unita_mis,
          g04_unita_misura.g04_ds_unita_mis,
          d03_ddt_righe_art.d03_qta_in_uscita,
          --
          ew2_righe_disposizioni_001w.ew2_cd_linea,
          ew2_righe_disposizioni_001w.cw0_ds_linea,
          p10_fasi_extra.p10_cd_stagione,
          z11_stagioni.z11_ds_stagione,
          p10_fasi_extra.p10_cd_cliente,
          p10_fasi_extra.p10_cd_articolo_cliente,
          cwa_articoli_cliente.cwa_ds_articolo_cliente,
          ew2_righe_disposizioni_001w.ew2_cd_composizione,
          ew2_righe_disposizioni_001w.cw4_ds_composizione,
          p10_fasi_extra.p10_cd_fase AS ew2_cd_ciclo,
          z02_fasi_di_lavoro.z02_ds_fase AS z09_ds_ciclo,
          z02_fasi_di_lavoro.z02_flag_fattura_a_parte AS z09_fl_fatturare,
          z02_fasi_di_lavoro.z02_fatturare_zero AS z09_fl_prezzo_zero,
          ew2_righe_disposizioni_001w.ew2_flag_tp_prod,
          ew2_righe_disposizioni_001w.ew2_nr_capi_caricati,
          ew2_righe_disposizioni_001w.ew2_kg_caricati,
          0,
          DECODE (
             NVL (P07_PRZ_CAPO_EXTRA, 0),
             0, DECODE (
                   c46listinocapo (p10_fasi_extra.p10_cd_stagione,
                                   p10_fasi_extra.p10_cd_fase,
                                   p10_fasi_extra.p10_cd_cliente,
                                   p10_fasi_extra.p10_cd_articolo_cliente,
                                   p10_fasi_extra.p10_cd_gruppo_composizione),
                   0, c45listinocapo (
                         p10_fasi_extra.p10_cd_stagione,
                         p10_fasi_extra.p10_cd_fase,
                         p10_fasi_extra.p10_cd_cliente,
                         p10_fasi_extra.p10_cd_articolo_cliente,
                         p10_fasi_extra.p10_cd_gruppo_composizione),
                   NULL, c45listinocapo (
                            p10_fasi_extra.p10_cd_stagione,
                            p10_fasi_extra.p10_cd_fase,
                            p10_fasi_extra.p10_cd_cliente,
                            p10_fasi_extra.p10_cd_articolo_cliente,
                            p10_fasi_extra.p10_cd_gruppo_composizione),
                   c46listinocapo (p10_fasi_extra.p10_cd_stagione,
                                   p10_fasi_extra.p10_cd_fase,
                                   p10_fasi_extra.p10_cd_cliente,
                                   p10_fasi_extra.p10_cd_articolo_cliente,
                                   p10_fasi_extra.p10_cd_gruppo_composizione)),
             P07_PRZ_CAPO_EXTRA),
          --
          DECODE (
             NVL (P07_PRZ_KG_EXTRA, 0),
             0, DECODE (
                   c46listinokg (p10_fasi_extra.p10_cd_stagione,
                                 p10_fasi_extra.p10_cd_fase,
                                 p10_fasi_extra.p10_cd_cliente,
                                 p10_fasi_extra.p10_cd_articolo_cliente,
                                 p10_fasi_extra.p10_cd_gruppo_composizione),
                   0, c45listinokg (
                         p10_fasi_extra.p10_cd_stagione,
                         p10_fasi_extra.p10_cd_fase,
                         p10_fasi_extra.p10_cd_cliente,
                         p10_fasi_extra.p10_cd_articolo_cliente,
                         p10_fasi_extra.p10_cd_gruppo_composizione),
                   NULL, c45listinokg (
                            p10_fasi_extra.p10_cd_stagione,
                            p10_fasi_extra.p10_cd_fase,
                            p10_fasi_extra.p10_cd_cliente,
                            p10_fasi_extra.p10_cd_articolo_cliente,
                            p10_fasi_extra.p10_cd_gruppo_composizione),
                   c46listinokg (p10_fasi_extra.p10_cd_stagione,
                                 p10_fasi_extra.p10_cd_fase,
                                 p10_fasi_extra.p10_cd_cliente,
                                 p10_fasi_extra.p10_cd_articolo_cliente,
                                 p10_fasi_extra.p10_cd_gruppo_composizione)),
             P07_PRZ_KG_EXTRA),
          --
          0,
          --
          d03_ddt_righe_art.d03_note,
          --
          'N',
          'P10' AS tipo,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          P10_FASI_EXTRA.P10_CD_GRUPPO_COMPOSIZIONE,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          'L' AS EW2_FLAG_TIPO_PREZZO,
          0 AS EW2_PRZ_UNITARIO,
          'L' AS EW2_FLAG_TIPO_PREZZO_KG,
          0 AS EW2_PRZ_UNITARIO_KG
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         d02_ddt_testata,
          i01_tipologia_bolle,
          d03_ddt_righe_art,
          r07_r0236_c012456789_001w,
          c01_codici_iva c01_codici_iva_01,
          c01_codici_iva c01_codici_iva_02,
          g04_unita_misura,
          z11_stagioni,
          cwa_articoli_cliente,
          ew2_righe_disposizioni_001w,
          p10_fasi_extra,
          p06_cartellini_prod,
          z02_fasi_di_lavoro,
          P07_CICLI_CARTELLINI
    -- ------------------------------------------------
    WHERE                  -- ------------------------------------------------
         d02_ddt_testata.d02_key = d03_ddt_righe_art.d03_key_d02
          AND d02_ddt_testata.d02_cd_tipo_bolla =
                 i01_tipologia_bolle.i01_cd_tipo_bolla(+)
          AND d02_ddt_testata.d02_cd_cliente_fatt =
                 r07_r0236_c012456789_001w.r07_cd_cliente(+)
          AND d02_ddt_testata.d02_cd_ass_fisc =
                 c01_codici_iva_01.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_iva = c01_codici_iva_02.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_unita_mis =
                 g04_unita_misura.g04_cd_unita_mis(+)
          AND d02_ddt_testata.d02_flag_fatturata = 'N'
          AND i01_tipologia_bolle.i01_cd_tipo_documento IS NOT NULL
          AND p10_fasi_extra.p10_cd_stagione =
                 z11_stagioni.z11_cd_stagione(+)
          --
          AND p10_fasi_extra.p10_cd_cliente =
                 cwa_articoli_cliente.cwa_cd_cliente(+)
          AND p10_fasi_extra.p10_cd_articolo_cliente =
                 cwa_articoli_cliente.cwa_cd_articolo_cliente(+)
          AND p10_fasi_extra.p10_cd_fase = z02_fasi_di_lavoro.z02_cd_fase
          --
          AND p10_fasi_extra.p10_anno_cartellino =
                 p06_cartellini_prod.p06_anno_cartellino
          AND p10_fasi_extra.p10_nr_cartellino =
                 p06_cartellini_prod.p06_nr_cartellino
          AND p06_cartellini_prod.p06_anno_disposizione =
                 ew2_righe_disposizioni_001w.ew2_anno_disposizione
          AND p06_cartellini_prod.p06_nr_disposizione =
                 ew2_righe_disposizioni_001w.ew2_nr_disposizione
          AND p06_cartellini_prod.p06_riga_disposizione =
                 ew2_righe_disposizioni_001w.ew2_riga_disposizione
          AND d03_ddt_righe_art.d03_anno_cartellino =
                 p10_fasi_extra.p10_anno_cartellino
          AND d03_ddt_righe_art.d03_nr_cartellino =
                 p10_fasi_extra.p10_nr_cartellino
          AND p10_fasi_extra.p10_anno_cartellino =
                 P07_CICLI_CARTELLINI.P07_ANNO_CARTELLINO
          AND p10_fasi_extra.p10_nr_cartellino =
                 P07_CICLI_CARTELLINI.P07_NR_CARTELLINO
          AND p10_fasi_extra.P10_SEQUENZA = P07_CICLI_CARTELLINI.P07_SEQUENZA
   -- ------------------------------------------------
   UNION
   -- ------------------------------------------------
   SELECT                                               -- Righe bolla manuali
         d02_ddt_testata.d02_key,
          d02_ddt_testata.d02_cd_tipo_bolla,
          i01_tipologia_bolle.i01_cd_tipo_documento,
          d02_ddt_testata.d02_anno_bolla,
          d02_ddt_testata.d02_nr_bolla,
          d02_ddt_testata.d02_dt_bolla,
          d02_ddt_testata.d02_cd_cliente_fatt,
          r07_r0236_c012456789_001w.r07_ragione_soc,
          r07_r0236_c012456789_001w.r07_cd_pagamento,
          r07_r0236_c012456789_001w.r06_ds_pagamento,
          r07_r0236_c012456789_001w.r07_cd_abi,
          r07_r0236_c012456789_001w.r07_cd_cab,
          r07_r0236_c012456789_001w.c06_denominazione_banca,
          r07_r0236_c012456789_001w.c06_agenzia,
          d02_ddt_testata.d02_cd_ass_fisc,
          c01_codici_iva_01.c01_ds_iva,
          d02_ddt_testata.d02_cd_valuta,
          d02_ddt_testata.d02_flag_fatturata,
          d03_ddt_righe_art.d03_riga,
          d03_ddt_righe_art.d03_anno_disp_cli,
          d03_ddt_righe_art.d03_nr_disp_cli,
          d03_ddt_righe_art.d03_riga_disp_cli,
          d03_ddt_righe_art.d03_capi_in_uscita,
          d03_ddt_righe_art.d03_kg_in_uscita,
          d03_ddt_righe_art.d03_cd_iva,
          c01_codici_iva_02.c01_perc_imponibile,
          d03_ddt_righe_art.d03_sconto_01,
          d03_ddt_righe_art.d03_sconto_02,
          d03_ddt_righe_art.d03_provv_agente,
          d03_ddt_righe_art.d03_provv_agente_2,
          d03_ddt_righe_art.d03_provv_agente_3,
          d03_ddt_righe_art.d03_provv_agente_4,
          d03_ddt_righe_art.d03_cd_articolo,
          d03_ddt_righe_art.d03_ds_articolo,
          d03_ddt_righe_art.d03_cd_unita_mis,
          g04_unita_misura.g04_ds_unita_mis,
          d03_ddt_righe_art.d03_qta_in_uscita,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          0,
          0,
          CASE
             WHEN D03_SCONTO_01 = 100
             THEN
                0
             ELSE
                DECODE (NVL (d03_ddt_righe_art.d03_prezzo_uni, 0),
                        0, d03_ddt_righe_art.d03_prezzo_uni_euro,
                        d03_ddt_righe_art.d03_prezzo_uni)
          END,
          0,
          0,
          0,
          --
          d03_note,
          --
          'N',
          'D03' AS tipo,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          NULL,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (D02_CD_CLIENTE_FATT,
                                       SUBSTR (GetTipoProd (d02_key), 0, 1),
                                       GetCdLinea (d02_key))
             AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          'L' AS EW2_FLAG_TIPO_PREZZO,
          0 AS EW2_PRZ_UNITARIO,
          'L' AS EW2_FLAG_TIPO_PREZZO_KG,
          0 AS EW2_PRZ_UNITARIO_KG
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         d02_ddt_testata,
          i01_tipologia_bolle,
          d03_ddt_righe_art,
          r07_r0236_c012456789_001w,
          c01_codici_iva c01_codici_iva_01,
          c01_codici_iva c01_codici_iva_02,
          g04_unita_misura
    -- ------------------------------------------------
    WHERE                  -- ------------------------------------------------
         d02_ddt_testata.d02_key = d03_ddt_righe_art.d03_key_d02
          AND d02_ddt_testata.d02_cd_tipo_bolla =
                 i01_tipologia_bolle.i01_cd_tipo_bolla(+)
          AND d02_ddt_testata.d02_cd_cliente_fatt =
                 r07_r0236_c012456789_001w.r07_cd_cliente(+)
          AND d02_ddt_testata.d02_cd_ass_fisc =
                 c01_codici_iva_01.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_iva = c01_codici_iva_02.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_unita_mis =
                 g04_unita_misura.g04_cd_unita_mis(+)
          AND d02_ddt_testata.d02_flag_fatturata = 'N'
          AND (d03_ddt_righe_art.d03_nr_disp_cli IS NULL
               OR d03_ddt_righe_art.d03_nr_disp_cli = 0)
          AND i01_tipologia_bolle.i01_cd_tipo_documento IS NOT NULL
/


  CREATE OR REPLACE FORCE EDITIONABLE VIEW "INTEX2"."DDT_PREZZI_003W" ("D02_KEY", "D02_CD_TIPO_BOLLA", "I01_CD_TIPO_DOCUMENTO", "D02_ANNO_BOLLA", "D02_NR_BOLLA", "D02_DT_BOLLA", "D02_CD_CLIENTE_FATT", "R07_RAGIONE_SOC", "R07_CD_PAGAMENTO", "R06_DS_PAGAMENTO", "R07_CD_ABI", "R07_CD_CAB", "C06_DENOMINAZIONE_BANCA", "C06_AGENZIA", "D02_CD_ASS_FISC", "C01_DS_IVA", "D02_CD_VALUTA", "D02_FLAG_FATTURATA", "D03_RIGA", "D03_ANNO_DISP_CLI", "D03_NR_DISP_CLI", "D03_RIGA_DISP_CLI", "D03_CAPI_IN_USCITA", "D03_KG_IN_USCITA", "D03_CD_IVA", "C01_PERC_IMPONIBILE", "D03_SCONTO_01", "D03_SCONTO_02", "D03_PROVV_AGENTE", "D03_PROVV_AGENTE_2", "D03_PROVV_AGENTE_3", "D03_PROVV_AGENTE_4", "D03_CD_ARTICOLO", "D03_DS_ARTICOLO", "D03_CD_UNITA_MIS", "G04_DS_UNITA_MIS", "D03_QTA_IN_USCITA", "EW2_CD_LINEA", "CW0_DS_LINEA", "EW2_CD_STAGIONE", "Z11_DS_STAGIONE", "EW2_CD_CLIENTE", "EW2_CD_ARTICOLO_FATTURA", "CWA_DS_ARTICOLO_CLIENTE", "EW2_CD_COMPOSIZIONE", "CW4_DS_COMPOSIZIONE", "EW2_CD_CICLO", "Z09_DS_CICLO", "Z09_FL_FATTURARE", "Z09_FL_PREZZO_ZERO", "EW2_FLAG_TP_PROD", "EW2_NR_CAPI_CARICATI", "EW2_KG_CARICATI", "D03_PREZZO_UNI", "D03_PREZZO_CAPO", "D03_PREZZO_KG", "D03_PREZZO_FORFAIT", "D03_NOTE", "D03_FLAG_PREZZO_FORFAIT", "TIPO", "D03_PREZZO_COLORE", "D03_COLORI_IN_USCITA", "D03_ANNO_CARTELLINO", "D03_NR_CARTELLINO", "P07_NR_BAGNO", "D03_PREZZO_FORFAIT_KG", "D03_PREZZO_FORFAIT_NR", "CAPIUSARE", "P07_KG_PROGRAMMATI", "P07_NR_CAPI_PROGRAMMATI", "CW4_CD_GRUPPO_COMPOSIZIONE", "P06_FLAG_USAKGINRICERCAPREZZI", "CODICERAGGRUPPAMENTO", "D02_CD_AGENTE", "D02_CD_AGENTE_2", "D02_CD_AGENTE_3", "D02_CD_AGENTE_4", "D02_CD_ABI", "D02_CD_CAB", "D02_CD_PAGAMENTO", "EW2_CD_STAGIONE_PROD", "DS_STAGIONE_PROD", "EW2_DS_ARTICOLO") AS
  SELECT                               -- Righe cartellini in bolla con bagno
         ddt_prezzi_001w.d02_key,
          ddt_prezzi_001w.d02_cd_tipo_bolla,
          ddt_prezzi_001w.i01_cd_tipo_documento,
          ddt_prezzi_001w.d02_anno_bolla,
          ddt_prezzi_001w.d02_nr_bolla,
          ddt_prezzi_001w.d02_dt_bolla,
          ddt_prezzi_001w.d02_cd_cliente_fatt,
          ddt_prezzi_001w.r07_ragione_soc,
          ddt_prezzi_001w.r07_cd_pagamento,
          ddt_prezzi_001w.r06_ds_pagamento,
          ddt_prezzi_001w.r07_cd_abi,
          ddt_prezzi_001w.r07_cd_cab,
          ddt_prezzi_001w.c06_denominazione_banca,
          ddt_prezzi_001w.c06_agenzia,
          ddt_prezzi_001w.d02_cd_ass_fisc,
          ddt_prezzi_001w.c01_ds_iva,
          ddt_prezzi_001w.d02_cd_valuta,
          ddt_prezzi_001w.d02_flag_fatturata,
          ddt_prezzi_001w.d03_riga,
          ddt_prezzi_001w.d03_anno_disp_cli,
          ddt_prezzi_001w.d03_nr_disp_cli,
          ddt_prezzi_001w.d03_riga_disp_cli,
          ddt_prezzi_001w.d03_capi_in_uscita,
          ddt_prezzi_001w.d03_kg_in_uscita,
          ddt_prezzi_001w.d03_cd_iva,
          ddt_prezzi_001w.c01_perc_imponibile,
          ddt_prezzi_001w.d03_sconto_01,
          ddt_prezzi_001w.d03_sconto_02,
          ddt_prezzi_001w.d03_provv_agente,
          ddt_prezzi_001w.d03_provv_agente_2,
          ddt_prezzi_001w.d03_provv_agente_3,
          ddt_prezzi_001w.d03_provv_agente_4,
          ddt_prezzi_001w.d03_cd_articolo,
          ddt_prezzi_001w.d03_ds_articolo,
          ddt_prezzi_001w.d03_cd_unita_mis,
          ddt_prezzi_001w.g04_ds_unita_mis,
          ddt_prezzi_001w.d03_qta_in_uscita,
          ddt_prezzi_001w.ew2_cd_linea,
          ddt_prezzi_001w.cw0_ds_linea,
          ddt_prezzi_001w.ew2_cd_stagione,
          ddt_prezzi_001w.z11_ds_stagione,
          ddt_prezzi_001w.ew2_cd_cliente,
          ddt_prezzi_001w.ew2_cd_articolo_fattura,
          ddt_prezzi_001w.cwa_ds_articolo_cliente,
          ddt_prezzi_001w.ew2_cd_composizione,
          ddt_prezzi_001w.cw4_ds_composizione,
          ddt_prezzi_001w.ew2_cd_ciclo,
          ddt_prezzi_001w.z09_ds_ciclo,
          ddt_prezzi_001w.z09_fl_fatturare,
          ddt_prezzi_001w.z09_fl_prezzo_zero,
          ddt_prezzi_001w.ew2_flag_tp_prod,
          ddt_prezzi_001w.ew2_nr_capi_caricati,
          ddt_prezzi_001w.ew2_kg_caricati,
          0,                                                  --D03_PREZZO_UNI
          DECODE (EW2_FLAG_TIPO_PREZZO,
                  'C', EW2_PRZ_UNITARIO,
                  'F', 0,
                  getprezzocapo (ddt_prezzi_001w.d02_cd_cliente_fatt,
                                 ddt_prezzi_001w.ew2_cd_linea,
                                 ddt_prezzi_001w.ew2_cd_stagione,
                                 ddt_prezzi_001w.ew2_cd_composizione,
                                 ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                                 ddt_prezzi_001w.ew2_cd_articolo_fattura,
                                 ddt_prezzi_001w.ew2_cd_ciclo,
                                 ddt_prezzi_001w.ew2_flag_tp_prod,
                                 fat_getcapidausare (d02_key, d03_riga))), -- D03_PREZZO_CAPO
          -- Modifica effettuata: calcolo il prezzo a Kg in base al numero di Kg nella disposizione (se specificati) o, nel caso
          -- fossero a 0 o null, in base al numero di Kg in uscita del DDT
          DECODE (EW2_FLAG_TIPO_PREZZO_KG,
                  'K', EW2_PRZ_UNITARIO_KG,
                  'G', 0,
                  getprezzokg (ddt_prezzi_001w.d02_cd_cliente_fatt,
                               ddt_prezzi_001w.ew2_cd_linea,
                               ddt_prezzi_001w.ew2_cd_stagione,
                               ddt_prezzi_001w.ew2_cd_composizione,
                               ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                               ddt_prezzi_001w.ew2_cd_articolo_fattura,
                               ddt_prezzi_001w.ew2_cd_ciclo,
                               ddt_prezzi_001w.ew2_flag_tp_prod,
                               fat_getkgdausare (d02_key, d03_riga))), --D03_PREZZO_KG
          -----------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO,
             'L', getprezzoforfait (
                     ddt_prezzi_001w.d02_cd_cliente_fatt,
                     ddt_prezzi_001w.ew2_cd_linea,
                     ddt_prezzi_001w.ew2_cd_stagione,
                     ddt_prezzi_001w.ew2_cd_composizione,
                     ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                     ddt_prezzi_001w.ew2_cd_articolo_fattura,
                     ddt_prezzi_001w.ew2_cd_ciclo,
                     ddt_prezzi_001w.ew2_flag_tp_prod,
                     fat_getcapidausare (d02_key, d03_riga),
                     fat_getkgdausare (d02_key, d03_riga)),
             Forfait_Dispo (P06_ANNO_DISPOSIZIONE,
                            P06_NR_DISPOSIZIONE,
                            P06_RIGA_DISPOSIZIONE)),      --D03_PREZZO_FORFAIT
          --
          ddt_prezzi_001w.d03_note,
          ----------------------------------------------------------------------------------------------------------------------------------
          CASE
             WHEN (EW2_FLAG_TIPO_PREZZO = 'L')
                  OR (EW2_FLAG_TIPO_PREZZO_KG = 'L')
             THEN
                getflagprezzoforfait (
                   ddt_prezzi_001w.d02_cd_cliente_fatt,
                   ddt_prezzi_001w.ew2_cd_linea,
                   ddt_prezzi_001w.ew2_cd_stagione,
                   ddt_prezzi_001w.ew2_cd_composizione,
                   ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                   ddt_prezzi_001w.ew2_cd_articolo_fattura,
                   ddt_prezzi_001w.ew2_cd_ciclo,
                   ddt_prezzi_001w.ew2_flag_tp_prod,
                   fat_getcapidausare (d02_key, d03_riga),
                   fat_getkgdausare (d02_key, d03_riga))
             WHEN (EW2_FLAG_TIPO_PREZZO = 'C')
                  AND (EW2_FLAG_TIPO_PREZZO_KG = 'K')
             THEN
                'N'
             ELSE
                Flag_Forfait_Dispo (P06_ANNO_DISPOSIZIONE,
                                    P06_NR_DISPOSIZIONE,
                                    P06_RIGA_DISPOSIZIONE)
          END,
          --D03_FLAG_PREZZO_FORFAIT
          --
          --
          'Z08' AS tipo,
          getprezzocolore (ddt_prezzi_001w.d02_cd_cliente_fatt,
                           ddt_prezzi_001w.ew2_cd_linea,
                           ddt_prezzi_001w.ew2_cd_stagione,
                           ddt_prezzi_001w.ew2_cd_composizione,
                           ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                           ddt_prezzi_001w.ew2_cd_articolo_fattura,
                           ddt_prezzi_001w.ew2_cd_ciclo,
                           ddt_prezzi_001w.ew2_flag_tp_prod,
                           FAT_GetColoriDaUsare (d02_key, d03_riga)), --D03_PREZZO_COLORE
          D03_COLORI_IN_USCITA,
          d03_anno_cartellino,
          d03_nr_cartellino,
          P07_NR_BAGNO,
          -------------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO_KG,
             'K', 0,
             'G', EW2_PRZ_UNITARIO_KG,
             getprezzoforfaitspecifico (
                'K',
                ddt_prezzi_001w.d02_cd_cliente_fatt,
                ddt_prezzi_001w.ew2_cd_linea,
                ddt_prezzi_001w.ew2_cd_stagione,
                ddt_prezzi_001w.ew2_cd_composizione,
                ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                ddt_prezzi_001w.ew2_cd_articolo_fattura,
                ddt_prezzi_001w.ew2_cd_ciclo,
                ddt_prezzi_001w.ew2_flag_tp_prod,
                fat_getcapidausare (d02_key, d03_riga),
                fat_getkgdausare (d02_key, d03_riga))), --D03_PREZZO_FORFAIT_KG
          -------------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO,
             'C', 0,
             'F', EW2_PRZ_UNITARIO,
             getprezzoforfaitspecifico (
                'C',
                ddt_prezzi_001w.d02_cd_cliente_fatt,
                ddt_prezzi_001w.ew2_cd_linea,
                ddt_prezzi_001w.ew2_cd_stagione,
                ddt_prezzi_001w.ew2_cd_composizione,
                ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                ddt_prezzi_001w.ew2_cd_articolo_fattura,
                ddt_prezzi_001w.ew2_cd_ciclo,
                ddt_prezzi_001w.ew2_flag_tp_prod,
                fat_getcapidausare (d02_key, d03_riga),
                fat_getkgdausare (d02_key, d03_riga))), --D03_PREZZO_FORFAIT_NR
          -------------------------------------------------------------------------------------------------------
          fat_getcapidausare (d02_key, d03_riga) AS Capiusare,
          -----------------------------
          P07_KG_PROGRAMMATI,
          P07_NR_CAPI_PROGRAMMATI,
          ddt_prezzi_001w.CW4_CD_GRUPPO_COMPOSIZIONE,
          P06.P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          EW2_CD_STAGIONE_PROD,
          STAG_PROD.Z11_DS_STAGIONE AS DS_STAGIONE_PROD,
          EW2_DS_ARTICOLO
     -- ------------------------------------------------
     FROM ddt_prezzi_001w
          LEFT JOIN p07_cicli_cartellini
             ON (    d03_anno_cartellino = p07_anno_cartellino
                 AND d03_nr_cartellino = p07_nr_cartellino
                 AND P07_NR_BAGNO > 0)
          LEFT JOIN P06_CARTELLINI_PROD P06
             ON (P06_ANNO_CARTELLINO = p07_anno_cartellino
                 AND P06_NR_CARTELLINO = p07_nr_cartellino)
          LEFT JOIN z11_stagioni STAG_PROD
             ON (ddt_prezzi_001w.EW2_CD_STAGIONE_PROD =
                    STAG_PROD.z11_cd_stagione)
    WHERE p07_sequenza =
             (SELECT MAX (p07_sequenza)
                FROM p07_cicli_cartellini
               WHERE     d03_anno_cartellino = p07_anno_cartellino
                     AND d03_nr_cartellino = p07_nr_cartellino
                     AND P07_NR_BAGNO > 0)
   UNION
   -- ------------------------------------------------
   SELECT                             -- Righe cartellini in bolla senza bagno
         ddt_prezzi_001w.d02_key,
          ddt_prezzi_001w.d02_cd_tipo_bolla,
          ddt_prezzi_001w.i01_cd_tipo_documento,
          ddt_prezzi_001w.d02_anno_bolla,
          ddt_prezzi_001w.d02_nr_bolla,
          ddt_prezzi_001w.d02_dt_bolla,
          ddt_prezzi_001w.d02_cd_cliente_fatt,
          ddt_prezzi_001w.r07_ragione_soc,
          ddt_prezzi_001w.r07_cd_pagamento,
          ddt_prezzi_001w.r06_ds_pagamento,
          ddt_prezzi_001w.r07_cd_abi,
          ddt_prezzi_001w.r07_cd_cab,
          ddt_prezzi_001w.c06_denominazione_banca,
          ddt_prezzi_001w.c06_agenzia,
          ddt_prezzi_001w.d02_cd_ass_fisc,
          ddt_prezzi_001w.c01_ds_iva,
          ddt_prezzi_001w.d02_cd_valuta,
          ddt_prezzi_001w.d02_flag_fatturata,
          ddt_prezzi_001w.d03_riga,
          ddt_prezzi_001w.d03_anno_disp_cli,
          ddt_prezzi_001w.d03_nr_disp_cli,
          ddt_prezzi_001w.d03_riga_disp_cli,
          ddt_prezzi_001w.d03_capi_in_uscita,
          ddt_prezzi_001w.d03_kg_in_uscita,
          ddt_prezzi_001w.d03_cd_iva,
          ddt_prezzi_001w.c01_perc_imponibile,
          ddt_prezzi_001w.d03_sconto_01,
          ddt_prezzi_001w.d03_sconto_02,
          ddt_prezzi_001w.d03_provv_agente,
          ddt_prezzi_001w.d03_provv_agente_2,
          ddt_prezzi_001w.d03_provv_agente_3,
          ddt_prezzi_001w.d03_provv_agente_4,
          ddt_prezzi_001w.d03_cd_articolo,
          ddt_prezzi_001w.d03_ds_articolo,
          ddt_prezzi_001w.d03_cd_unita_mis,
          ddt_prezzi_001w.g04_ds_unita_mis,
          ddt_prezzi_001w.d03_qta_in_uscita,
          ddt_prezzi_001w.ew2_cd_linea,
          ddt_prezzi_001w.cw0_ds_linea,
          ddt_prezzi_001w.ew2_cd_stagione,
          ddt_prezzi_001w.z11_ds_stagione,
          ddt_prezzi_001w.ew2_cd_cliente,
          ddt_prezzi_001w.ew2_cd_articolo_fattura,
          ddt_prezzi_001w.cwa_ds_articolo_cliente,
          ddt_prezzi_001w.ew2_cd_composizione,
          ddt_prezzi_001w.cw4_ds_composizione,
          ddt_prezzi_001w.ew2_cd_ciclo,
          ddt_prezzi_001w.z09_ds_ciclo,
          ddt_prezzi_001w.z09_fl_fatturare,
          ddt_prezzi_001w.z09_fl_prezzo_zero,
          ddt_prezzi_001w.ew2_flag_tp_prod,
          ddt_prezzi_001w.ew2_nr_capi_caricati,
          ddt_prezzi_001w.ew2_kg_caricati,
          0,                                                  --D03_PREZZO_UNI
          DECODE (EW2_FLAG_TIPO_PREZZO,
                  'C', EW2_PRZ_UNITARIO,
                  'F', 0,
                  getprezzocapo (ddt_prezzi_001w.d02_cd_cliente_fatt,
                                 ddt_prezzi_001w.ew2_cd_linea,
                                 ddt_prezzi_001w.ew2_cd_stagione,
                                 ddt_prezzi_001w.ew2_cd_composizione,
                                 ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                                 ddt_prezzi_001w.ew2_cd_articolo_fattura,
                                 ddt_prezzi_001w.ew2_cd_ciclo,
                                 ddt_prezzi_001w.ew2_flag_tp_prod,
                                 fat_getcapidausare (d02_key, d03_riga))), -- D03_PREZZO_CAPO
          -- Modifica effettuata: calcolo il prezzo a Kg in base al numero di Kg nella disposizione (se specificati) o, nel caso
          -- fossero a 0 o null, in base al numero di Kg in uscita del DDT
          DECODE (EW2_FLAG_TIPO_PREZZO_KG,
                  'K', EW2_PRZ_UNITARIO_KG,
                  'G', 0,
                  getprezzokg (ddt_prezzi_001w.d02_cd_cliente_fatt,
                               ddt_prezzi_001w.ew2_cd_linea,
                               ddt_prezzi_001w.ew2_cd_stagione,
                               ddt_prezzi_001w.ew2_cd_composizione,
                               ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                               ddt_prezzi_001w.ew2_cd_articolo_fattura,
                               ddt_prezzi_001w.ew2_cd_ciclo,
                               ddt_prezzi_001w.ew2_flag_tp_prod,
                               fat_getkgdausare (d02_key, d03_riga))), --D03_PREZZO_KG
          --LG
          DECODE (
             EW2_FLAG_TIPO_PREZZO,
             'L', getprezzoforfait (
                     ddt_prezzi_001w.d02_cd_cliente_fatt,
                     ddt_prezzi_001w.ew2_cd_linea,
                     ddt_prezzi_001w.ew2_cd_stagione,
                     ddt_prezzi_001w.ew2_cd_composizione,
                     ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                     ddt_prezzi_001w.ew2_cd_articolo_fattura,
                     ddt_prezzi_001w.ew2_cd_ciclo,
                     ddt_prezzi_001w.ew2_flag_tp_prod,
                     fat_getcapidausare (d02_key, d03_riga),
                     fat_getkgdausare (d02_key, d03_riga)),
             Forfait_Dispo (D03_ANNO_DISP_CLI,
                            D03_NR_DISP_CLI,
                            D03_RIGA_DISP_CLI)),          --D03_PREZZO_FORFAIT
          --
          ddt_prezzi_001w.d03_note,
          ---------------------------------------------------------------------------------------------------------------------------------------------------------
          CASE
             WHEN (EW2_FLAG_TIPO_PREZZO = 'L')
                  OR (EW2_FLAG_TIPO_PREZZO_KG = 'L')
             THEN
                getflagprezzoforfait (
                   ddt_prezzi_001w.d02_cd_cliente_fatt,
                   ddt_prezzi_001w.ew2_cd_linea,
                   ddt_prezzi_001w.ew2_cd_stagione,
                   ddt_prezzi_001w.ew2_cd_composizione,
                   ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                   ddt_prezzi_001w.ew2_cd_articolo_fattura,
                   ddt_prezzi_001w.ew2_cd_ciclo,
                   ddt_prezzi_001w.ew2_flag_tp_prod,
                   fat_getcapidausare (d02_key, d03_riga),
                   fat_getkgdausare (d02_key, d03_riga))
             WHEN (EW2_FLAG_TIPO_PREZZO = 'C')
                  AND (EW2_FLAG_TIPO_PREZZO_KG = 'K')
             THEN
                'N'
             ELSE
                Flag_Forfait_Dispo (D03_ANNO_DISP_CLI,
                                    D03_NR_DISP_CLI,
                                    D03_RIGA_DISP_CLI)
          END,                                       --D03_FLAG_PREZZO_FORFAIT
          ---------------------------------------------------------------------------------------------------------------------------------------------------------
          --
          'Z08' AS tipo,
          getprezzocolore (ddt_prezzi_001w.d02_cd_cliente_fatt,
                           ddt_prezzi_001w.ew2_cd_linea,
                           ddt_prezzi_001w.ew2_cd_stagione,
                           ddt_prezzi_001w.ew2_cd_composizione,
                           ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                           ddt_prezzi_001w.ew2_cd_articolo_fattura,
                           ddt_prezzi_001w.ew2_cd_ciclo,
                           ddt_prezzi_001w.ew2_flag_tp_prod,
                           FAT_GetColoriDaUsare (d02_key, d03_riga)),
          D03_COLORI_IN_USCITA,
          d03_anno_cartellino,
          d03_nr_cartellino,
          0 AS P07_NR_BAGNO,
          -------------------------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO_KG,
             'K', 0,
             'G', EW2_PRZ_UNITARIO_KG,
             getprezzoforfaitspecifico (
                'K',
                ddt_prezzi_001w.d02_cd_cliente_fatt,
                ddt_prezzi_001w.ew2_cd_linea,
                ddt_prezzi_001w.ew2_cd_stagione,
                ddt_prezzi_001w.ew2_cd_composizione,
                ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                ddt_prezzi_001w.ew2_cd_articolo_fattura,
                ddt_prezzi_001w.ew2_cd_ciclo,
                ddt_prezzi_001w.ew2_flag_tp_prod,
                fat_getcapidausare (d02_key, d03_riga),
                fat_getkgdausare (d02_key, d03_riga))), --D03_PREZZO_FORFAIT_KG
          ------------------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO,
             'C', 0,
             'F', EW2_PRZ_UNITARIO,
             getprezzoforfaitspecifico (
                'C',
                ddt_prezzi_001w.d02_cd_cliente_fatt,
                ddt_prezzi_001w.ew2_cd_linea,
                ddt_prezzi_001w.ew2_cd_stagione,
                ddt_prezzi_001w.ew2_cd_composizione,
                ddt_prezzi_001w.cw4_cd_gruppo_composizione,
                ddt_prezzi_001w.ew2_cd_articolo_fattura,
                ddt_prezzi_001w.ew2_cd_ciclo,
                ddt_prezzi_001w.ew2_flag_tp_prod,
                fat_getcapidausare (d02_key, d03_riga),
                fat_getkgdausare (d02_key, d03_riga))), --D03_PREZZO_FORFAIT_NR
          ----------------------------------------------------------------------------------------------------------
          fat_getcapidausare (d02_key, d03_riga) AS Capiusare,
          --------------------------
          fat_getkgdausare (d02_key, d03_riga),
          fat_getcapidausare (d02_key, d03_riga),
          ddt_prezzi_001w.CW4_CD_GRUPPO_COMPOSIZIONE,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          EW2_CD_STAGIONE_PROD,
          STAG_PROD.Z11_DS_STAGIONE AS DS_STAGIONE_PROD,
          EW2_DS_ARTICOLO
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         ddt_prezzi_001w
          LEFT JOIN
             z11_stagioni STAG_PROD
          ON (ddt_prezzi_001w.EW2_CD_STAGIONE_PROD =
                 STAG_PROD.z11_cd_stagione)
    WHERE (SELECT COUNT (*)
             FROM p07_cicli_cartellini
            WHERE (    d03_anno_cartellino = p07_anno_cartellino
                   AND d03_nr_cartellino = p07_nr_cartellino
                   AND P07_NR_BAGNO > 0)) = 0
   -- ------------------------------------------------
   UNION
   -- ------------------------------------------------
   SELECT                                                        -- Fasi extra
         d02_ddt_testata.d02_key,
          d02_ddt_testata.d02_cd_tipo_bolla,
          i01_tipologia_bolle.i01_cd_tipo_documento,
          d02_ddt_testata.d02_anno_bolla,
          d02_ddt_testata.d02_nr_bolla,
          d02_ddt_testata.d02_dt_bolla,
          d02_ddt_testata.d02_cd_cliente_fatt,
          r07_r0236_c012456789_001w.r07_ragione_soc,
          r07_r0236_c012456789_001w.r07_cd_pagamento,
          r07_r0236_c012456789_001w.r06_ds_pagamento,
          r07_r0236_c012456789_001w.r07_cd_abi,
          r07_r0236_c012456789_001w.r07_cd_cab,
          r07_r0236_c012456789_001w.c06_denominazione_banca,
          r07_r0236_c012456789_001w.c06_agenzia,
          d02_ddt_testata.d02_cd_ass_fisc,
          c01_codici_iva_01.c01_ds_iva,
          d02_ddt_testata.d02_cd_valuta,
          d02_ddt_testata.d02_flag_fatturata,
          d03_ddt_righe_art.d03_riga,
          d03_ddt_righe_art.d03_anno_disp_cli,
          d03_ddt_righe_art.d03_nr_disp_cli,
          d03_ddt_righe_art.d03_riga_disp_cli,
          d03_ddt_righe_art.d03_capi_in_uscita,
          d03_ddt_righe_art.d03_kg_in_uscita,
          d03_ddt_righe_art.d03_cd_iva,
          c01_codici_iva_02.c01_perc_imponibile,
          d03_ddt_righe_art.d03_sconto_01,
          d03_ddt_righe_art.d03_sconto_02,
          d03_ddt_righe_art.d03_provv_agente,
          d03_ddt_righe_art.d03_provv_agente_2,
          d03_ddt_righe_art.d03_provv_agente_3,
          d03_ddt_righe_art.d03_provv_agente_4,
          d03_ddt_righe_art.d03_cd_articolo,
          d03_ddt_righe_art.d03_ds_articolo,
          d03_ddt_righe_art.d03_cd_unita_mis,
          g04_unita_misura.g04_ds_unita_mis,
          d03_ddt_righe_art.d03_qta_in_uscita,
          --
          ew2_righe_disposizioni_001w.ew2_cd_linea,
          ew2_righe_disposizioni_001w.cw0_ds_linea,
          p10_fasi_extra.p10_cd_stagione,
          z11_stagioni.z11_ds_stagione,
          p10_fasi_extra.p10_cd_cliente,
          p10_fasi_extra.p10_cd_articolo_cliente,
          cwa_articoli_cliente.cwa_ds_articolo_cliente,
          ew2_righe_disposizioni_001w.ew2_cd_composizione,
          ew2_righe_disposizioni_001w.cw4_ds_composizione,
          p10_fasi_extra.p10_cd_fase AS ew2_cd_ciclo,
          z02_fasi_di_lavoro.z02_ds_fase AS z09_ds_ciclo,
          z02_fasi_di_lavoro.z02_flag_fattura_a_parte AS z09_fl_fatturare,
          z02_fasi_di_lavoro.z02_fatturare_zero AS z09_fl_prezzo_zero,
          ew2_righe_disposizioni_001w.ew2_flag_tp_prod,
          ew2_righe_disposizioni_001w.ew2_nr_capi_caricati,
          ew2_righe_disposizioni_001w.ew2_kg_caricati,
          0,
          DECODE (
             NVL (P07_PRZ_CAPO_EXTRA, 0),
             0, DECODE (
                   c46listinocapo (p10_fasi_extra.p10_cd_stagione,
                                   p10_fasi_extra.p10_cd_fase,
                                   p10_fasi_extra.p10_cd_cliente,
                                   p10_fasi_extra.p10_cd_articolo_cliente,
                                   p10_fasi_extra.p10_cd_gruppo_composizione),
                   0, c45listinocapo (
                         p10_fasi_extra.p10_cd_stagione,
                         p10_fasi_extra.p10_cd_fase,
                         p10_fasi_extra.p10_cd_cliente,
                         p10_fasi_extra.p10_cd_articolo_cliente,
                         p10_fasi_extra.p10_cd_gruppo_composizione),
                   NULL, c45listinocapo (
                            p10_fasi_extra.p10_cd_stagione,
                            p10_fasi_extra.p10_cd_fase,
                            p10_fasi_extra.p10_cd_cliente,
                            p10_fasi_extra.p10_cd_articolo_cliente,
                            p10_fasi_extra.p10_cd_gruppo_composizione),
                   c46listinocapo (p10_fasi_extra.p10_cd_stagione,
                                   p10_fasi_extra.p10_cd_fase,
                                   p10_fasi_extra.p10_cd_cliente,
                                   p10_fasi_extra.p10_cd_articolo_cliente,
                                   p10_fasi_extra.p10_cd_gruppo_composizione)),
             P07_PRZ_CAPO_EXTRA),
          --
          DECODE (
             NVL (P07_PRZ_KG_EXTRA, 0),
             0, DECODE (
                   c46listinokg (p10_fasi_extra.p10_cd_stagione,
                                 p10_fasi_extra.p10_cd_fase,
                                 p10_fasi_extra.p10_cd_cliente,
                                 p10_fasi_extra.p10_cd_articolo_cliente,
                                 p10_fasi_extra.p10_cd_gruppo_composizione),
                   0, c45listinokg (
                         p10_fasi_extra.p10_cd_stagione,
                         p10_fasi_extra.p10_cd_fase,
                         p10_fasi_extra.p10_cd_cliente,
                         p10_fasi_extra.p10_cd_articolo_cliente,
                         p10_fasi_extra.p10_cd_gruppo_composizione),
                   NULL, c45listinokg (
                            p10_fasi_extra.p10_cd_stagione,
                            p10_fasi_extra.p10_cd_fase,
                            p10_fasi_extra.p10_cd_cliente,
                            p10_fasi_extra.p10_cd_articolo_cliente,
                            p10_fasi_extra.p10_cd_gruppo_composizione),
                   c46listinokg (p10_fasi_extra.p10_cd_stagione,
                                 p10_fasi_extra.p10_cd_fase,
                                 p10_fasi_extra.p10_cd_cliente,
                                 p10_fasi_extra.p10_cd_articolo_cliente,
                                 p10_fasi_extra.p10_cd_gruppo_composizione)),
             P07_PRZ_KG_EXTRA),
          --
          0,
          --
          d03_ddt_righe_art.d03_note,
          --
          'N',
          'P10' AS tipo,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          P10_FASI_EXTRA.P10_CD_GRUPPO_COMPOSIZIONE,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          ew2_righe_disposizioni_001w.EW2_CD_STAGIONE_PROD,
          ew2_righe_disposizioni_001w.DS_STAGIONE_PROD,
          EW2_DS_ARTICOLO
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         d02_ddt_testata,
          i01_tipologia_bolle,
          d03_ddt_righe_art,
          r07_r0236_c012456789_001w,
          c01_codici_iva c01_codici_iva_01,
          c01_codici_iva c01_codici_iva_02,
          g04_unita_misura,
          z11_stagioni,
          cwa_articoli_cliente,
          ew2_righe_disposizioni_001w,
          p10_fasi_extra,
          p06_cartellini_prod,
          z02_fasi_di_lavoro,
          P07_CICLI_CARTELLINI
    -- ------------------------------------------------
    WHERE                  -- ------------------------------------------------
         d02_ddt_testata.d02_key = d03_ddt_righe_art.d03_key_d02
          AND d02_ddt_testata.d02_cd_tipo_bolla =
                 i01_tipologia_bolle.i01_cd_tipo_bolla(+)
          AND d02_ddt_testata.d02_cd_cliente_fatt =
                 r07_r0236_c012456789_001w.r07_cd_cliente(+)
          AND d02_ddt_testata.d02_cd_ass_fisc =
                 c01_codici_iva_01.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_iva = c01_codici_iva_02.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_unita_mis =
                 g04_unita_misura.g04_cd_unita_mis(+)
          AND d02_ddt_testata.d02_flag_fatturata = 'N'
          AND i01_tipologia_bolle.i01_cd_tipo_documento IS NOT NULL
          AND p10_fasi_extra.p10_cd_stagione =
                 z11_stagioni.z11_cd_stagione(+)
          --
          AND p10_fasi_extra.p10_cd_cliente =
                 cwa_articoli_cliente.cwa_cd_cliente(+)
          AND p10_fasi_extra.p10_cd_articolo_cliente =
                 cwa_articoli_cliente.cwa_cd_articolo_cliente(+)
          AND p10_fasi_extra.p10_cd_fase = z02_fasi_di_lavoro.z02_cd_fase
          --
          AND p10_fasi_extra.p10_anno_cartellino =
                 p06_cartellini_prod.p06_anno_cartellino
          AND p10_fasi_extra.p10_nr_cartellino =
                 p06_cartellini_prod.p06_nr_cartellino
          AND p06_cartellini_prod.p06_anno_disposizione =
                 ew2_righe_disposizioni_001w.ew2_anno_disposizione
          AND p06_cartellini_prod.p06_nr_disposizione =
                 ew2_righe_disposizioni_001w.ew2_nr_disposizione
          AND p06_cartellini_prod.p06_riga_disposizione =
                 ew2_righe_disposizioni_001w.ew2_riga_disposizione
          AND d03_ddt_righe_art.d03_anno_cartellino =
                 p10_fasi_extra.p10_anno_cartellino
          AND d03_ddt_righe_art.d03_nr_cartellino =
                 p10_fasi_extra.p10_nr_cartellino
          AND p10_fasi_extra.p10_anno_cartellino =
                 P07_CICLI_CARTELLINI.P07_ANNO_CARTELLINO
          AND p10_fasi_extra.p10_nr_cartellino =
                 P07_CICLI_CARTELLINI.P07_NR_CARTELLINO
          AND p10_fasi_extra.P10_SEQUENZA = P07_CICLI_CARTELLINI.P07_SEQUENZA
   -- ------------------------------------------------
   UNION
   -- ------------------------------------------------
   SELECT                                               -- Righe bolla manuali
         d02_ddt_testata.d02_key,
          d02_ddt_testata.d02_cd_tipo_bolla,
          i01_tipologia_bolle.i01_cd_tipo_documento,
          d02_ddt_testata.d02_anno_bolla,
          d02_ddt_testata.d02_nr_bolla,
          d02_ddt_testata.d02_dt_bolla,
          d02_ddt_testata.d02_cd_cliente_fatt,
          r07_r0236_c012456789_001w.r07_ragione_soc,
          r07_r0236_c012456789_001w.r07_cd_pagamento,
          r07_r0236_c012456789_001w.r06_ds_pagamento,
          r07_r0236_c012456789_001w.r07_cd_abi,
          r07_r0236_c012456789_001w.r07_cd_cab,
          r07_r0236_c012456789_001w.c06_denominazione_banca,
          r07_r0236_c012456789_001w.c06_agenzia,
          d02_ddt_testata.d02_cd_ass_fisc,
          c01_codici_iva_01.c01_ds_iva,
          d02_ddt_testata.d02_cd_valuta,
          d02_ddt_testata.d02_flag_fatturata,
          d03_ddt_righe_art.d03_riga,
          d03_ddt_righe_art.d03_anno_disp_cli,
          d03_ddt_righe_art.d03_nr_disp_cli,
          d03_ddt_righe_art.d03_riga_disp_cli,
          d03_ddt_righe_art.d03_capi_in_uscita,
          d03_ddt_righe_art.d03_kg_in_uscita,
          d03_ddt_righe_art.d03_cd_iva,
          c01_codici_iva_02.c01_perc_imponibile,
          d03_ddt_righe_art.d03_sconto_01,
          d03_ddt_righe_art.d03_sconto_02,
          d03_ddt_righe_art.d03_provv_agente,
          d03_ddt_righe_art.d03_provv_agente_2,
          d03_ddt_righe_art.d03_provv_agente_3,
          d03_ddt_righe_art.d03_provv_agente_4,
          d03_ddt_righe_art.d03_cd_articolo,
          d03_ddt_righe_art.d03_ds_articolo,
          d03_ddt_righe_art.d03_cd_unita_mis,
          g04_unita_misura.g04_ds_unita_mis,
          d03_ddt_righe_art.d03_qta_in_uscita,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          0,
          0,
          d03_ddt_righe_art.d03_prezzo_uni,
          0,
          0,
          0,
          --
          d03_note,
          --
          'N',
          'D03' AS tipo,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          NULL,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          NULL AS CodiceRaggruppamento,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          NULL AS EW2_CD_STAGIONE_PROD,
          NULL AS DS_STAGIONE_PROD,
          D03_DS_ARTICOLO
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         d02_ddt_testata,
          i01_tipologia_bolle,
          d03_ddt_righe_art,
          r07_r0236_c012456789_001w,
          c01_codici_iva c01_codici_iva_01,
          c01_codici_iva c01_codici_iva_02,
          g04_unita_misura
    -- ------------------------------------------------
    WHERE                  -- ------------------------------------------------
         d02_ddt_testata.d02_key = d03_ddt_righe_art.d03_key_d02
          AND d02_ddt_testata.d02_cd_tipo_bolla =
                 i01_tipologia_bolle.i01_cd_tipo_bolla(+)
          AND d02_ddt_testata.d02_cd_cliente_fatt =
                 r07_r0236_c012456789_001w.r07_cd_cliente(+)
          AND d02_ddt_testata.d02_cd_ass_fisc =
                 c01_codici_iva_01.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_iva = c01_codici_iva_02.c01_cd_iva(+)
          AND d03_ddt_righe_art.d03_cd_unita_mis =
                 g04_unita_misura.g04_cd_unita_mis(+)
          AND d02_ddt_testata.d02_flag_fatturata = 'N'
          AND (d03_ddt_righe_art.d03_nr_disp_cli IS NULL
               OR d03_ddt_righe_art.d03_nr_disp_cli = 0)
          AND i01_tipologia_bolle.i01_cd_tipo_documento IS NOT NULL
   --------------------------------------------------------------------------------------------------
   -- ------------------------------------------------
   UNION
   -- ------------------------------------------------
   SELECT                                                --disposizioni aperte
         EW1_NR_DISPOSIZIONE AS d02_key,
          NULL AS d02_cd_tipo_bolla,
          NULL AS i01_cd_tipo_documento,
          0 AS d02_anno_bolla,
          0 AS d02_nr_bolla,
          EW1_DATA_BOLLA_CLI AS d02_dt_bolla,
          EW1_CD_CLIENTE AS d02_cd_cliente_fatt,
          r07_r0236_c012456789_001w.r07_ragione_soc,
          r07_r0236_c012456789_001w.r07_cd_pagamento,
          r07_r0236_c012456789_001w.r06_ds_pagamento,
          r07_r0236_c012456789_001w.r07_cd_abi,
          r07_r0236_c012456789_001w.r07_cd_cab,
          r07_r0236_c012456789_001w.c06_denominazione_banca,
          r07_r0236_c012456789_001w.c06_agenzia,
          R07_R0236_C012456789_001W.R07_CD_IVA AS d02_cd_ass_fisc,
          R07_R0236_C012456789_001W.C01_DS_IVA,
          R07_R0236_C012456789_001W.R07_CD_VALUTA AS d02_cd_valuta,
          'N' AS d02_flag_fatturata,
          EW2_RIGA_DISPOSIZIONE AS d03_riga,
          EW2_RIGHE_DISPOSIZIONI.EW2_ANNO_DISPOSIZIONE,
          EW2_RIGHE_DISPOSIZIONI.EW2_NR_DISPOSIZIONE,
          EW2_RIGHE_DISPOSIZIONI.EW2_RIGA_DISPOSIZIONE,
          EW2_NR_CAPI_CARICATI AS d03_capi_in_uscita,
          EW2_KG_CARICATI AS d03_kg_in_uscita,
          R07_R0236_C012456789_001W.R07_CD_IVA AS d03_cd_iva,
          0 AS c01_perc_imponibile,
          NULL AS d03_sconto_01,
          NULL AS d03_sconto_02,
          0 AS d03_provv_agente,
          0 AS d03_provv_agente_2,
          0 AS d03_provv_agente_3,
          0 AS d03_provv_agente_4,
          NULL AS d03_cd_articolo,
          NULL AS d03_ds_articolo,
          NULL AS d03_cd_unita_mis,
          NULL AS g04_ds_unita_mis,
          0 AS d03_qta_in_uscita,
          EW2_CD_LINEA ew2_cd_linea,
          cw0_ds_linea,
          ew2_cd_stagione,
          z11_stagioni.z11_ds_stagione,
          ew2_cd_cliente,
          ew2_cd_articolo_fattura,
          cwa_ds_articolo_cliente,
          ew2_cd_composizione,
          cw4_ds_composizione,
          ew2_cd_ciclo,
          z09_ds_ciclo,
          z09_fl_fatturare,
          z09_fl_prezzo_zero,
          ew2_flag_tp_prod,
          ew2_nr_capi_caricati,
          ew2_kg_caricati,
          0,                                                  --D03_PREZZO_UNI
          --------------------------------------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO,
             'C', EW2_PRZ_UNITARIO,
             'F', 0,
             getprezzocapo (EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE,
                            EW2_RIGHE_DISPOSIZIONI.ew2_cd_linea,
                            EW2_RIGHE_DISPOSIZIONI.ew2_cd_stagione,
                            EW2_RIGHE_DISPOSIZIONI.ew2_cd_composizione,
                            CW4_COMPOSIZIONI.cw4_cd_gruppo_composizione,
                            EW2_RIGHE_DISPOSIZIONI.ew2_cd_articolo_fattura,
                            EW2_RIGHE_DISPOSIZIONI.ew2_cd_ciclo,
                            EW2_RIGHE_DISPOSIZIONI.ew2_flag_tp_prod,
                            EW2_RIGHE_DISPOSIZIONI.EW2_NR_CAPI_CARICATI)), -- D03_PREZZO_CAPO
          --------------------------------------------------------------------------------------------------------------------------------
          -- Modifica effettuata: calcolo il prezzo a Kg in base al numero di Kg nella disposizione (se specificati) o, nel caso
          -- fossero a 0 o null, in base al numero di Kg in uscita del DDT
          DECODE (
             EW2_FLAG_TIPO_PREZZO_KG,
             'K', EW2_PRZ_UNITARIO_KG,
             'G', 0,
             getprezzokg (EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE,
                          EW2_RIGHE_DISPOSIZIONI.ew2_cd_linea,
                          EW2_RIGHE_DISPOSIZIONI.ew2_cd_stagione,
                          EW2_RIGHE_DISPOSIZIONI.ew2_cd_composizione,
                          CW4_COMPOSIZIONI.cw4_cd_gruppo_composizione,
                          EW2_RIGHE_DISPOSIZIONI.ew2_cd_articolo_fattura,
                          EW2_RIGHE_DISPOSIZIONI.ew2_cd_ciclo,
                          EW2_RIGHE_DISPOSIZIONI.ew2_flag_tp_prod,
                          EW2_RIGHE_DISPOSIZIONI.EW2_KG_CARICATI)), --D03_PREZZO_KG
          --------------------------------------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO,
             'L', getprezzoforfait (
                     EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE,
                     EW2_RIGHE_DISPOSIZIONI.ew2_cd_linea,
                     EW2_RIGHE_DISPOSIZIONI.ew2_cd_stagione,
                     EW2_RIGHE_DISPOSIZIONI.ew2_cd_composizione,
                     CW4_COMPOSIZIONI.cw4_cd_gruppo_composizione,
                     EW2_RIGHE_DISPOSIZIONI.ew2_cd_articolo_fattura,
                     EW2_RIGHE_DISPOSIZIONI.ew2_cd_ciclo,
                     EW2_RIGHE_DISPOSIZIONI.ew2_flag_tp_prod,
                     EW2_RIGHE_DISPOSIZIONI.EW2_NR_CAPI_CARICATI,
                     EW2_RIGHE_DISPOSIZIONI.EW2_KG_CARICATI),
             Forfait_Dispo (EW2_ANNO_DISPOSIZIONE,
                            EW2_NR_DISPOSIZIONE,
                            EW2_RIGA_DISPOSIZIONE)),      --D03_PREZZO_FORFAIT
          --
          NULL AS d03_note,
          -----------------------------------------------------------------------------------------------------------------------------------------------------
          CASE
             WHEN (EW2_FLAG_TIPO_PREZZO = 'L')
                  OR (EW2_FLAG_TIPO_PREZZO_KG = 'L')
             THEN
                getflagprezzoforfait (
                   EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE,
                   EW2_RIGHE_DISPOSIZIONI.ew2_cd_linea,
                   EW2_RIGHE_DISPOSIZIONI.ew2_cd_stagione,
                   EW2_RIGHE_DISPOSIZIONI.ew2_cd_composizione,
                   CW4_COMPOSIZIONI.cw4_cd_gruppo_composizione,
                   EW2_RIGHE_DISPOSIZIONI.ew2_cd_articolo_fattura,
                   EW2_RIGHE_DISPOSIZIONI.ew2_cd_ciclo,
                   EW2_RIGHE_DISPOSIZIONI.ew2_flag_tp_prod,
                   EW2_RIGHE_DISPOSIZIONI.EW2_NR_CAPI_CARICATI,
                   EW2_RIGHE_DISPOSIZIONI.EW2_KG_CARICATI)
             WHEN (EW2_FLAG_TIPO_PREZZO = 'C')
                  AND (EW2_FLAG_TIPO_PREZZO_KG = 'K')
             THEN
                'N'
             ELSE
                Flag_Forfait_Dispo (EW2_ANNO_DISPOSIZIONE,
                                    EW2_NR_DISPOSIZIONE,
                                    EW2_RIGA_DISPOSIZIONE)
          END,                                       --D03_FLAG_PREZZO_FORFAIT
          -------------------------------------------------------------------------------------------------------------------------------------------------------------
          'EW2' AS tipo,
          getprezzocolore (EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE,
                           EW2_RIGHE_DISPOSIZIONI.ew2_cd_linea,
                           EW2_RIGHE_DISPOSIZIONI.ew2_cd_stagione,
                           EW2_RIGHE_DISPOSIZIONI.ew2_cd_composizione,
                           CW4_COMPOSIZIONI.cw4_cd_gruppo_composizione,
                           EW2_RIGHE_DISPOSIZIONI.ew2_cd_articolo_fattura,
                           EW2_RIGHE_DISPOSIZIONI.ew2_cd_ciclo,
                           EW2_RIGHE_DISPOSIZIONI.ew2_flag_tp_prod,
                           EW2_RIGHE_DISPOSIZIONI.EW2_NR_CAMP_NUOVI_COL), --D03_PREZZO_COLORE
          EW2_NR_CAMP_NUOVI_COL,
          0 AS,
          0 AS d03_nr_cartellino,
          0 AS P07_NR_BAGNO,
          ----------------------------------------------------------------------------------------------------------------------------------------------------

          DECODE (
             EW2_FLAG_TIPO_PREZZO_KG,
             'K', 0,
             'G', EW2_PRZ_UNITARIO_KG,
             getprezzoforfaitspecifico (
                'K',
                EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_linea,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_stagione,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_composizione,
                CW4_COMPOSIZIONI.cw4_cd_gruppo_composizione,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_articolo_fattura,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_ciclo,
                EW2_RIGHE_DISPOSIZIONI.ew2_flag_tp_prod,
                EW2_RIGHE_DISPOSIZIONI.EW2_NR_CAPI_CARICATI,
                EW2_RIGHE_DISPOSIZIONI.EW2_KG_CARICATI)), --D03_PREZZO_FORFAIT_KG
          ----------------------------------------------------------------------------------------------------------------------
          DECODE (
             EW2_FLAG_TIPO_PREZZO,
             'C', 0,
             'F', EW2_PRZ_UNITARIO,
             getprezzoforfaitspecifico (
                'C',
                EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_linea,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_stagione,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_composizione,
                CW4_COMPOSIZIONI.cw4_cd_gruppo_composizione,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_articolo_fattura,
                EW2_RIGHE_DISPOSIZIONI.ew2_cd_ciclo,
                EW2_RIGHE_DISPOSIZIONI.ew2_flag_tp_prod,
                EW2_RIGHE_DISPOSIZIONI.EW2_NR_CAPI_CARICATI,
                EW2_RIGHE_DISPOSIZIONI.EW2_KG_CARICATI)), --D03_PREZZO_FORFAIT_NR
          -------------------------------------------------------------------------------------------------------------------------
          --------------------------
          EW2_NR_CAPI_CARICATI AS Capiusare,
          -----------------------------
          0 AS P07_KG_PROGRAMMATI,
          0 AS P07_NR_CAPI_PROGRAMMATI,
          CW4_COMPOSIZIONI.CW4_CD_GRUPPO_COMPOSIZIONE,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CodicePerRaggrBolleFattureF (EW1_CD_CLIENTE,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CodiceRaggruppamento,
          NULL AS D02_CD_AGENTE,
          NULL AS D02_CD_AGENTE_2,
          NULL AS D02_CD_AGENTE_3,
          NULL AS D02_CD_AGENTE_4,
          NULL AS D02_CD_ABI,
          NULL AS D02_CD_CAB,
          NULL AS D02_CD_PAGAMENTO,
          EW2_RIGHE_DISPOSIZIONI.EW2_CD_STAGIONE_PROD,
          STAG_PROD.Z11_DS_STAGIONE AS DS_STAGIONE_PROD,
          EW2_DS_ARTICOLO
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         EW1_TESTATA_DISPOSIZIONI,
          EW2_RIGHE_DISPOSIZIONI,
          CW4_COMPOSIZIONI,
          r07_r0236_c012456789_001w,
          z09_testate_cicli_lavorazione,
          cwa_articoli_cliente,
          cw0_linea_tintoria,
          z11_stagioni,
          z11_stagioni STAG_PROD
    -- ------------------------------------------------
    WHERE EW1_TESTATA_DISPOSIZIONI.EW1_ANNO_DISPOSIZIONE =
             EW2_RIGHE_DISPOSIZIONI.EW2_ANNO_DISPOSIZIONE
          AND EW1_TESTATA_DISPOSIZIONI.EW1_NR_DISPOSIZIONE =
                 EW2_RIGHE_DISPOSIZIONI.EW2_NR_DISPOSIZIONE
          AND EW1_TESTATA_DISPOSIZIONI.EW1_CD_CLIENTE =
                 r07_r0236_c012456789_001w.r07_cd_cliente(+)
          AND ew2_righe_disposizioni.ew2_cd_cliente =
                 z09_testate_cicli_lavorazione.z09_cd_cliente(+)
          AND ew2_righe_disposizioni.ew2_cd_articolo_fattura =
                 z09_testate_cicli_lavorazione.z09_cd_articolo_cliente(+)
          AND ew2_righe_disposizioni.ew2_cd_ciclo =
                 z09_testate_cicli_lavorazione.z09_cd_ciclo(+)
         AND EW2_RIGHE_DISPOSIZIONI.ew2_CD_LINEA = Z09_TESTATE_CICLI_LAVORAZIONE.Z09_CD_LINEA(+)
          AND EW2_RIGHE_DISPOSIZIONI.EW2_CD_STAGIONE = Z09_TESTATE_CICLI_LAVORAZIONE.Z09_CD_STAGIONE(+)
          AND GET_COMP_PER_CICLO(ew2_cd_cliente,ew2_cd_articolo_fattura,ew2_cd_ciclo,EW2_CD_STAGIONE,ew2_CD_LINEA,EW2_CD_COMPOSIZIONE) = Z09_TESTATE_CICLI_LAVORAZIONE.Z09_CD_COMPOSIZIONE(+)
          AND ew2_righe_disposizioni.ew2_cd_cliente =
                 cwa_articoli_cliente.cwa_cd_cliente(+)
          AND ew2_righe_disposizioni.ew2_cd_articolo_fattura =
                 cwa_articoli_cliente.cwa_cd_articolo_cliente(+)
          AND ew2_righe_disposizioni.ew2_cd_cliente =
                 cw0_linea_tintoria.cw0_cd_cliente(+)
          AND ew2_righe_disposizioni.ew2_cd_linea =
                 cw0_linea_tintoria.cw0_cd_linea(+)
          AND ew2_righe_disposizioni.ew2_cd_stagione =
                 z11_stagioni.z11_cd_stagione(+)
          AND ew2_righe_disposizioni.ew2_cd_composizione =
                 cw4_composizioni.cw4_cd_composizione(+)
          AND ew2_righe_disposizioni.EW2_CD_STAGIONE_PROD =
                 STAG_PROD.z11_cd_stagione
          AND ew2_righe_disposizioni.EW2_FLAG_TP_DDT = 'L'
          AND NVL (ew2_righe_disposizioni.EW2_FLAG_CHIUSO, 'N') = 'N'
          AND ( (SELECT COUNT (*)
                   FROM D03_DDT_RIGHE_ART
                  WHERE     D03_ANNO_DISP_CLI = EW2_ANNO_DISPOSIZIONE
                        AND D03_NR_DISP_CLI = EW2_NR_DISPOSIZIONE
                        AND D03_RIGA_DISP_CLI = EW2_RIGA_DISPOSIZIONE) = 0)
/


  CREATE OR REPLACE FORCE EDITIONABLE VIEW "INTEX2"."DDT_PREZZI_005W" ("D02_KEY", "D02_CD_TIPO_BOLLA", "I01_CD_TIPO_DOCUMENTO", "D02_ANNO_BOLLA", "D02_NR_BOLLA", "D02_DT_BOLLA", "D02_CD_CLIENTE_FATT", "R07_RAGIONE_SOC", "R07_CD_PAGAMENTO", "R06_DS_PAGAMENTO", "R07_CD_ABI", "R07_CD_CAB", "C06_DENOMINAZIONE_BANCA", "C06_AGENZIA", "D02_CD_ASS_FISC", "C01_DS_IVA", "D02_CD_VALUTA", "D02_FLAG_FATTURATA", "D03_RIGA", "D03_ANNO_DISP_CLI", "D03_NR_DISP_CLI", "D03_RIGA_DISP_CLI", "D03_CAPI_IN_USCITA", "D03_KG_IN_USCITA", "D03_CD_IVA", "C01_PERC_IMPONIBILE", "D03_SCONTO_01", "D03_SCONTO_02", "D03_PROVV_AGENTE", "D03_PROVV_AGENTE_2", "D03_PROVV_AGENTE_3", "D03_PROVV_AGENTE_4", "D03_CD_ARTICOLO", "D03_DS_ARTICOLO", "D03_CD_UNITA_MIS", "G04_DS_UNITA_MIS", "D03_QTA_IN_USCITA", "EW2_CD_LINEA", "CW0_DS_LINEA", "EW2_CD_STAGIONE", "Z11_DS_STAGIONE", "EW2_CD_CLIENTE", "EW2_CD_ARTICOLO_FATTURA", "CWA_DS_ARTICOLO_CLIENTE", "EW2_CD_COMPOSIZIONE", "CW4_DS_COMPOSIZIONE", "EW2_CD_CICLO", "Z09_DS_CICLO", "Z09_FL_FATTURARE", "Z09_FL_PREZZO_ZERO", "EW2_FLAG_TP_PROD", "EW2_NR_CAPI_CARICATI", "EW2_KG_CARICATI", "D03_PREZZO_UNI", "D03_NOTE", "TIPO", "D03_COLORI_IN_USCITA", "D03_ANNO_CARTELLINO", "D03_NR_CARTELLINO", "P07_NR_BAGNO", "CAPIUSARE", "P07_KG_PROGRAMMATI", "P07_NR_CAPI_PROGRAMMATI", "CW4_CD_GRUPPO_COMPOSIZIONE", "P06_FLAG_USAKGINRICERCAPREZZI", "CODICERAGGRUPPAMENTO", "D02_CD_AGENTE", "D02_CD_AGENTE_2", "D02_CD_AGENTE_3", "D02_CD_AGENTE_4", "D02_CD_ABI", "D02_CD_CAB", "D02_CD_PAGAMENTO", "P07_ANNO_CARTELLINO", "P07_NR_CARTELLINO", "EW2_PRZ_UNITARIO", "EW2_FLAG_TIPO_PREZZO", "EW2_PRZ_UNITARIO_KG", "EW2_FLAG_TIPO_PREZZO_KG") AS
  SELECT                               -- Righe cartellini in bolla con bagno
         DDT_PREZZI_001W.D02_KEY,
          DDT_PREZZI_001W.D02_CD_TIPO_BOLLA,
          DDT_PREZZI_001W.I01_CD_TIPO_DOCUMENTO,
          DDT_PREZZI_001W.D02_ANNO_BOLLA,
          DDT_PREZZI_001W.D02_NR_BOLLA,
          DDT_PREZZI_001W.D02_DT_BOLLA,
          DDT_PREZZI_001W.D02_CD_CLIENTE_FATT,
          DDT_PREZZI_001W.R07_RAGIONE_SOC,
          DDT_PREZZI_001W.R07_CD_PAGAMENTO,
          DDT_PREZZI_001W.R06_DS_PAGAMENTO,
          DDT_PREZZI_001W.R07_CD_ABI,
          DDT_PREZZI_001W.R07_CD_CAB,
          DDT_PREZZI_001W.C06_DENOMINAZIONE_BANCA,
          DDT_PREZZI_001W.C06_AGENZIA,
          DDT_PREZZI_001W.D02_CD_ASS_FISC,
          DDT_PREZZI_001W.C01_DS_IVA,
          DDT_PREZZI_001W.D02_CD_VALUTA,
          DDT_PREZZI_001W.D02_FLAG_FATTURATA,
          DDT_PREZZI_001W.D03_RIGA,
          DDT_PREZZI_001W.D03_ANNO_DISP_CLI,
          DDT_PREZZI_001W.D03_NR_DISP_CLI,
          DDT_PREZZI_001W.D03_RIGA_DISP_CLI,
          DDT_PREZZI_001W.D03_CAPI_IN_USCITA,
          DDT_PREZZI_001W.D03_KG_IN_USCITA,
          DDT_PREZZI_001W.D03_CD_IVA,
          DDT_PREZZI_001W.C01_PERC_IMPONIBILE,
          DDT_PREZZI_001W.D03_SCONTO_01,
          DDT_PREZZI_001W.D03_SCONTO_02,
          DDT_PREZZI_001W.D03_PROVV_AGENTE,
          DDT_PREZZI_001W.D03_PROVV_AGENTE_2,
          DDT_PREZZI_001W.D03_PROVV_AGENTE_3,
          DDT_PREZZI_001W.D03_PROVV_AGENTE_4,
          DDT_PREZZI_001W.D03_CD_ARTICOLO,
          DDT_PREZZI_001W.D03_DS_ARTICOLO,
          DDT_PREZZI_001W.D03_CD_UNITA_MIS,
          DDT_PREZZI_001W.G04_DS_UNITA_MIS,
          DDT_PREZZI_001W.D03_QTA_IN_USCITA,
          DDT_PREZZI_001W.EW2_CD_LINEA,
          DDT_PREZZI_001W.CW0_DS_LINEA,
          DDT_PREZZI_001W.EW2_CD_STAGIONE,
          DDT_PREZZI_001W.Z11_DS_STAGIONE,
          DDT_PREZZI_001W.EW2_CD_CLIENTE,
          DDT_PREZZI_001W.EW2_CD_ARTICOLO_FATTURA,
          DDT_PREZZI_001W.CWA_DS_ARTICOLO_CLIENTE,
          DDT_PREZZI_001W.EW2_CD_COMPOSIZIONE,
          DDT_PREZZI_001W.CW4_DS_COMPOSIZIONE,
          DDT_PREZZI_001W.EW2_CD_CICLO,
          DDT_PREZZI_001W.Z09_DS_CICLO,
          DDT_PREZZI_001W.Z09_FL_FATTURARE,
          DDT_PREZZI_001W.Z09_FL_PREZZO_ZERO,
          DDT_PREZZI_001W.EW2_FLAG_TP_PROD,
          DDT_PREZZI_001W.EW2_NR_CAPI_CARICATI,
          DDT_PREZZI_001W.EW2_KG_CARICATI,
          0,
          DDT_PREZZI_001W.D03_NOTE,
          'Z08' AS TIPO,
          D03_COLORI_IN_USCITA,
          D03_ANNO_CARTELLINO,
          D03_NR_CARTELLINO,
          P07_NR_BAGNO,
          --------------------------
          FAT_GETCAPIDAUSARE (D02_KEY, D03_RIGA) AS CAPIUSARE,
          -----------------------------
          P07_KG_PROGRAMMATI,
          P07_NR_CAPI_PROGRAMMATI,
          DDT_PREZZI_001W.CW4_CD_GRUPPO_COMPOSIZIONE,
          P06.P06_FLAG_USAKGINRICERCAPREZZI,
          CODICEPERRAGGRBOLLEFATTUREF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CODICERAGGRUPPAMENTO,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          P07_ANNO_CARTELLINO,
          P07_NR_CARTELLINO,
          EW2_PRZ_UNITARIO,
          EW2_FLAG_TIPO_PREZZO,
          EW2_PRZ_UNITARIO_KG,
          EW2_FLAG_TIPO_PREZZO_KG
     -- ------------------------------------------------
     FROM DDT_PREZZI_001W
          LEFT JOIN P07_CICLI_CARTELLINI
             ON (    D03_ANNO_CARTELLINO = P07_ANNO_CARTELLINO
                 AND D03_NR_CARTELLINO = P07_NR_CARTELLINO
                 AND P07_NR_BAGNO > 0)
          LEFT JOIN P06_CARTELLINI_PROD P06
             ON (P06_ANNO_CARTELLINO = P07_ANNO_CARTELLINO
                 AND P06_NR_CARTELLINO = P07_NR_CARTELLINO)
    WHERE P07_SEQUENZA =
             (SELECT MAX (P07_SEQUENZA)
                FROM P07_CICLI_CARTELLINI
               WHERE     D03_ANNO_CARTELLINO = P07_ANNO_CARTELLINO
                     AND D03_NR_CARTELLINO = P07_NR_CARTELLINO
                     AND P07_NR_BAGNO > 0)
   UNION
   -- ------------------------------------------------
   SELECT                             -- Righe cartellini in bolla senza bagno
         DDT_PREZZI_001W.D02_KEY,
          DDT_PREZZI_001W.D02_CD_TIPO_BOLLA,
          DDT_PREZZI_001W.I01_CD_TIPO_DOCUMENTO,
          DDT_PREZZI_001W.D02_ANNO_BOLLA,
          DDT_PREZZI_001W.D02_NR_BOLLA,
          DDT_PREZZI_001W.D02_DT_BOLLA,
          DDT_PREZZI_001W.D02_CD_CLIENTE_FATT,
          DDT_PREZZI_001W.R07_RAGIONE_SOC,
          DDT_PREZZI_001W.R07_CD_PAGAMENTO,
          DDT_PREZZI_001W.R06_DS_PAGAMENTO,
          DDT_PREZZI_001W.R07_CD_ABI,
          DDT_PREZZI_001W.R07_CD_CAB,
          DDT_PREZZI_001W.C06_DENOMINAZIONE_BANCA,
          DDT_PREZZI_001W.C06_AGENZIA,
          DDT_PREZZI_001W.D02_CD_ASS_FISC,
          DDT_PREZZI_001W.C01_DS_IVA,
          DDT_PREZZI_001W.D02_CD_VALUTA,
          DDT_PREZZI_001W.D02_FLAG_FATTURATA,
          DDT_PREZZI_001W.D03_RIGA,
          DDT_PREZZI_001W.D03_ANNO_DISP_CLI,
          DDT_PREZZI_001W.D03_NR_DISP_CLI,
          DDT_PREZZI_001W.D03_RIGA_DISP_CLI,
          DDT_PREZZI_001W.D03_CAPI_IN_USCITA,
          DDT_PREZZI_001W.D03_KG_IN_USCITA,
          DDT_PREZZI_001W.D03_CD_IVA,
          DDT_PREZZI_001W.C01_PERC_IMPONIBILE,
          DDT_PREZZI_001W.D03_SCONTO_01,
          DDT_PREZZI_001W.D03_SCONTO_02,
          DDT_PREZZI_001W.D03_PROVV_AGENTE,
          DDT_PREZZI_001W.D03_PROVV_AGENTE_2,
          DDT_PREZZI_001W.D03_PROVV_AGENTE_3,
          DDT_PREZZI_001W.D03_PROVV_AGENTE_4,
          DDT_PREZZI_001W.D03_CD_ARTICOLO,
          DDT_PREZZI_001W.D03_DS_ARTICOLO,
          DDT_PREZZI_001W.D03_CD_UNITA_MIS,
          DDT_PREZZI_001W.G04_DS_UNITA_MIS,
          DDT_PREZZI_001W.D03_QTA_IN_USCITA,
          DDT_PREZZI_001W.EW2_CD_LINEA,
          DDT_PREZZI_001W.CW0_DS_LINEA,
          DDT_PREZZI_001W.EW2_CD_STAGIONE,
          DDT_PREZZI_001W.Z11_DS_STAGIONE,
          DDT_PREZZI_001W.EW2_CD_CLIENTE,
          DDT_PREZZI_001W.EW2_CD_ARTICOLO_FATTURA,
          DDT_PREZZI_001W.CWA_DS_ARTICOLO_CLIENTE,
          DDT_PREZZI_001W.EW2_CD_COMPOSIZIONE,
          DDT_PREZZI_001W.CW4_DS_COMPOSIZIONE,
          DDT_PREZZI_001W.EW2_CD_CICLO,
          DDT_PREZZI_001W.Z09_DS_CICLO,
          DDT_PREZZI_001W.Z09_FL_FATTURARE,
          DDT_PREZZI_001W.Z09_FL_PREZZO_ZERO,
          DDT_PREZZI_001W.EW2_FLAG_TP_PROD,
          DDT_PREZZI_001W.EW2_NR_CAPI_CARICATI,
          DDT_PREZZI_001W.EW2_KG_CARICATI,
          0,
          DDT_PREZZI_001W.D03_NOTE,
          --
          'Z08' AS TIPO,
          D03_COLORI_IN_USCITA,
          D03_ANNO_CARTELLINO,
          D03_NR_CARTELLINO,
          0 AS P07_NR_BAGNO,
          FAT_GETCAPIDAUSARE (D02_KEY, D03_RIGA) AS CAPIUSARE,
          --------------------------
          FAT_GETKGDAUSARE (D02_KEY, D03_RIGA),
          FAT_GETCAPIDAUSARE (D02_KEY, D03_RIGA),
          DDT_PREZZI_001W.CW4_CD_GRUPPO_COMPOSIZIONE,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CODICEPERRAGGRBOLLEFATTUREF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CODICERAGGRUPPAMENTO,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          0 AS P07_ANNO_CARTELLINO,
          0 AS P07_NR_CARTELLINO,
          EW2_PRZ_UNITARIO,
          EW2_FLAG_TIPO_PREZZO,
          EW2_PRZ_UNITARIO_KG,
          EW2_FLAG_TIPO_PREZZO_KG
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         DDT_PREZZI_001W
    WHERE (SELECT COUNT (*)
             FROM P07_CICLI_CARTELLINI
            WHERE (    D03_ANNO_CARTELLINO = P07_ANNO_CARTELLINO
                   AND D03_NR_CARTELLINO = P07_NR_CARTELLINO
                   AND P07_NR_BAGNO > 0)) = 0
   -- ------------------------------------------------
   UNION
   -- ------------------------------------------------
   SELECT                                                        -- Fasi extra
         D02_DDT_TESTATA.D02_KEY,
          D02_DDT_TESTATA.D02_CD_TIPO_BOLLA,
          I01_TIPOLOGIA_BOLLE.I01_CD_TIPO_DOCUMENTO,
          D02_DDT_TESTATA.D02_ANNO_BOLLA,
          D02_DDT_TESTATA.D02_NR_BOLLA,
          D02_DDT_TESTATA.D02_DT_BOLLA,
          D02_DDT_TESTATA.D02_CD_CLIENTE_FATT,
          R07_R0236_C012456789_001W.R07_RAGIONE_SOC,
          R07_R0236_C012456789_001W.R07_CD_PAGAMENTO,
          R07_R0236_C012456789_001W.R06_DS_PAGAMENTO,
          R07_R0236_C012456789_001W.R07_CD_ABI,
          R07_R0236_C012456789_001W.R07_CD_CAB,
          R07_R0236_C012456789_001W.C06_DENOMINAZIONE_BANCA,
          R07_R0236_C012456789_001W.C06_AGENZIA,
          D02_DDT_TESTATA.D02_CD_ASS_FISC,
          C01_CODICI_IVA_01.C01_DS_IVA,
          D02_DDT_TESTATA.D02_CD_VALUTA,
          D02_DDT_TESTATA.D02_FLAG_FATTURATA,
          D03_DDT_RIGHE_ART.D03_RIGA,
          D03_DDT_RIGHE_ART.D03_ANNO_DISP_CLI,
          D03_DDT_RIGHE_ART.D03_NR_DISP_CLI,
          D03_DDT_RIGHE_ART.D03_RIGA_DISP_CLI,
          D03_DDT_RIGHE_ART.D03_CAPI_IN_USCITA,
          D03_DDT_RIGHE_ART.D03_KG_IN_USCITA,
          D03_DDT_RIGHE_ART.D03_CD_IVA,
          C01_CODICI_IVA_02.C01_PERC_IMPONIBILE,
          D03_DDT_RIGHE_ART.D03_SCONTO_01,
          D03_DDT_RIGHE_ART.D03_SCONTO_02,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE_2,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE_3,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE_4,
          D03_DDT_RIGHE_ART.D03_CD_ARTICOLO,
          D03_DDT_RIGHE_ART.D03_DS_ARTICOLO,
          D03_DDT_RIGHE_ART.D03_CD_UNITA_MIS,
          G04_UNITA_MISURA.G04_DS_UNITA_MIS,
          D03_DDT_RIGHE_ART.D03_QTA_IN_USCITA,
          --
          EW2_RIGHE_DISPOSIZIONI_001W.EW2_CD_LINEA,
          EW2_RIGHE_DISPOSIZIONI_001W.CW0_DS_LINEA,
          P10_FASI_EXTRA.P10_CD_STAGIONE,
          Z11_STAGIONI.Z11_DS_STAGIONE,
          P10_FASI_EXTRA.P10_CD_CLIENTE,
          P10_FASI_EXTRA.P10_CD_ARTICOLO_CLIENTE,
          CWA_ARTICOLI_CLIENTE.CWA_DS_ARTICOLO_CLIENTE,
          EW2_RIGHE_DISPOSIZIONI_001W.EW2_CD_COMPOSIZIONE,
          EW2_RIGHE_DISPOSIZIONI_001W.CW4_DS_COMPOSIZIONE,
          P10_FASI_EXTRA.P10_CD_FASE AS EW2_CD_CICLO,
          Z02_FASI_DI_LAVORO.Z02_DS_FASE AS Z09_DS_CICLO,
          Z02_FASI_DI_LAVORO.Z02_FLAG_FATTURA_A_PARTE AS Z09_FL_FATTURARE,
          Z02_FASI_DI_LAVORO.Z02_FATTURARE_ZERO AS Z09_FL_PREZZO_ZERO,
          EW2_RIGHE_DISPOSIZIONI_001W.EW2_FLAG_TP_PROD,
          EW2_RIGHE_DISPOSIZIONI_001W.EW2_NR_CAPI_CARICATI,
          EW2_RIGHE_DISPOSIZIONI_001W.EW2_KG_CARICATI,
          0,                                                     -- prezzo uni
          --
          D03_DDT_RIGHE_ART.D03_NOTE,
          'P10' AS TIPO,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          P10_FASI_EXTRA.P10_CD_GRUPPO_COMPOSIZIONE,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          CODICEPERRAGGRBOLLEFATTUREF (D02_CD_CLIENTE_FATT,
                                       EW2_FLAG_TP_PROD,
                                       EW2_CD_LINEA)
             AS CODICERAGGRUPPAMENTO,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          0 AS P07_ANNO_CARTELLINO,
          0 AS P07_NR_CARTELLINO,
          0 AS EW2_PRZ_UNITARIO,
          'L' AS EW2_FLAG_TIPO_PREZZO,
          0 AS EW2_PRZ_UNITARIO_KG,
          'L' AS EW2_FLAG_TIPO_PREZZO_KG
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         D02_DDT_TESTATA,
          I01_TIPOLOGIA_BOLLE,
          D03_DDT_RIGHE_ART,
          R07_R0236_C012456789_001W,
          C01_CODICI_IVA C01_CODICI_IVA_01,
          C01_CODICI_IVA C01_CODICI_IVA_02,
          G04_UNITA_MISURA,
          Z11_STAGIONI,
          CWA_ARTICOLI_CLIENTE,
          EW2_RIGHE_DISPOSIZIONI_001W,
          P10_FASI_EXTRA,
          P06_CARTELLINI_PROD,
          Z02_FASI_DI_LAVORO
    -- ------------------------------------------------
    WHERE                  -- ------------------------------------------------
         D02_DDT_TESTATA.D02_KEY = D03_DDT_RIGHE_ART.D03_KEY_D02
          AND D02_DDT_TESTATA.D02_CD_TIPO_BOLLA =
                 I01_TIPOLOGIA_BOLLE.I01_CD_TIPO_BOLLA(+)
          AND D02_DDT_TESTATA.D02_CD_CLIENTE_FATT =
                 R07_R0236_C012456789_001W.R07_CD_CLIENTE(+)
          AND D02_DDT_TESTATA.D02_CD_ASS_FISC =
                 C01_CODICI_IVA_01.C01_CD_IVA(+)
          AND D03_DDT_RIGHE_ART.D03_CD_IVA = C01_CODICI_IVA_02.C01_CD_IVA(+)
          AND D03_DDT_RIGHE_ART.D03_CD_UNITA_MIS =
                 G04_UNITA_MISURA.G04_CD_UNITA_MIS(+)
          AND D02_DDT_TESTATA.D02_FLAG_FATTURATA = 'N'
          AND I01_TIPOLOGIA_BOLLE.I01_CD_TIPO_DOCUMENTO IS NOT NULL
          AND P10_FASI_EXTRA.P10_CD_STAGIONE =
                 Z11_STAGIONI.Z11_CD_STAGIONE(+)
          --
          AND P10_FASI_EXTRA.P10_CD_CLIENTE =
                 CWA_ARTICOLI_CLIENTE.CWA_CD_CLIENTE(+)
          AND P10_FASI_EXTRA.P10_CD_ARTICOLO_CLIENTE =
                 CWA_ARTICOLI_CLIENTE.CWA_CD_ARTICOLO_CLIENTE(+)
          AND P10_FASI_EXTRA.P10_CD_FASE = Z02_FASI_DI_LAVORO.Z02_CD_FASE
          --
          AND P10_FASI_EXTRA.P10_ANNO_CARTELLINO =
                 P06_CARTELLINI_PROD.P06_ANNO_CARTELLINO
          AND P10_FASI_EXTRA.P10_NR_CARTELLINO =
                 P06_CARTELLINI_PROD.P06_NR_CARTELLINO
          AND P06_CARTELLINI_PROD.P06_ANNO_DISPOSIZIONE =
                 EW2_RIGHE_DISPOSIZIONI_001W.EW2_ANNO_DISPOSIZIONE
          AND P06_CARTELLINI_PROD.P06_NR_DISPOSIZIONE =
                 EW2_RIGHE_DISPOSIZIONI_001W.EW2_NR_DISPOSIZIONE
          AND P06_CARTELLINI_PROD.P06_RIGA_DISPOSIZIONE =
                 EW2_RIGHE_DISPOSIZIONI_001W.EW2_RIGA_DISPOSIZIONE
          AND D03_DDT_RIGHE_ART.D03_ANNO_CARTELLINO =
                 P10_FASI_EXTRA.P10_ANNO_CARTELLINO
          AND D03_DDT_RIGHE_ART.D03_NR_CARTELLINO =
                 P10_FASI_EXTRA.P10_NR_CARTELLINO
   -- ------------------------------------------------
   UNION
   -- ------------------------------------------------
   SELECT                                               -- Righe bolla manuali
         D02_DDT_TESTATA.D02_KEY,
          D02_DDT_TESTATA.D02_CD_TIPO_BOLLA,
          I01_TIPOLOGIA_BOLLE.I01_CD_TIPO_DOCUMENTO,
          D02_DDT_TESTATA.D02_ANNO_BOLLA,
          D02_DDT_TESTATA.D02_NR_BOLLA,
          D02_DDT_TESTATA.D02_DT_BOLLA,
          D02_DDT_TESTATA.D02_CD_CLIENTE_FATT,
          R07_R0236_C012456789_001W.R07_RAGIONE_SOC,
          R07_R0236_C012456789_001W.R07_CD_PAGAMENTO,
          R07_R0236_C012456789_001W.R06_DS_PAGAMENTO,
          R07_R0236_C012456789_001W.R07_CD_ABI,
          R07_R0236_C012456789_001W.R07_CD_CAB,
          R07_R0236_C012456789_001W.C06_DENOMINAZIONE_BANCA,
          R07_R0236_C012456789_001W.C06_AGENZIA,
          D02_DDT_TESTATA.D02_CD_ASS_FISC,
          C01_CODICI_IVA_01.C01_DS_IVA,
          D02_DDT_TESTATA.D02_CD_VALUTA,
          D02_DDT_TESTATA.D02_FLAG_FATTURATA,
          D03_DDT_RIGHE_ART.D03_RIGA,
          D03_DDT_RIGHE_ART.D03_ANNO_DISP_CLI,
          D03_DDT_RIGHE_ART.D03_NR_DISP_CLI,
          D03_DDT_RIGHE_ART.D03_RIGA_DISP_CLI,
          D03_DDT_RIGHE_ART.D03_CAPI_IN_USCITA,
          D03_DDT_RIGHE_ART.D03_KG_IN_USCITA,
          D03_DDT_RIGHE_ART.D03_CD_IVA,
          C01_CODICI_IVA_02.C01_PERC_IMPONIBILE,
          D03_DDT_RIGHE_ART.D03_SCONTO_01,
          D03_DDT_RIGHE_ART.D03_SCONTO_02,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE_2,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE_3,
          D03_DDT_RIGHE_ART.D03_PROVV_AGENTE_4,
          D03_DDT_RIGHE_ART.D03_CD_ARTICOLO,
          D03_DDT_RIGHE_ART.D03_DS_ARTICOLO,
          D03_DDT_RIGHE_ART.D03_CD_UNITA_MIS,
          G04_UNITA_MISURA.G04_DS_UNITA_MIS,
          D03_DDT_RIGHE_ART.D03_QTA_IN_USCITA,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          NULL,
          0,
          0,
          D03_DDT_RIGHE_ART.D03_PREZZO_UNI,
          D03_NOTE,
          'D03' AS TIPO,
          0,
          0,
          0,
          0,
          0,
          0,
          0,
          NULL,
          'N' AS P06_FLAG_USAKGINRICERCAPREZZI,
          NULL AS CODICERAGGRUPPAMENTO,
          D02_CD_AGENTE,
          D02_CD_AGENTE_2,
          D02_CD_AGENTE_3,
          D02_CD_AGENTE_4,
          D02_CD_ABI,
          D02_CD_CAB,
          D02_CD_PAGAMENTO,
          0 AS P07_ANNO_CARTELLINO,
          0 AS P07_NR_CARTELLINO,
          0 AS EW2_PRZ_UNITARIO,
          'L' AS EW2_FLAG_TIPO_PREZZO,
          0 AS EW2_PRZ_UNITARIO_KG,
          'L' AS EW2_FLAG_TIPO_PREZZO_KG
     -- ------------------------------------------------
     FROM                  -- ------------------------------------------------
         D02_DDT_TESTATA,
          I01_TIPOLOGIA_BOLLE,
          D03_DDT_RIGHE_ART,
          R07_R0236_C012456789_001W,
          C01_CODICI_IVA C01_CODICI_IVA_01,
          C01_CODICI_IVA C01_CODICI_IVA_02,
          G04_UNITA_MISURA
    -- ------------------------------------------------
    WHERE                  -- ------------------------------------------------
         D02_DDT_TESTATA.D02_KEY = D03_DDT_RIGHE_ART.D03_KEY_D02
          AND D02_DDT_TESTATA.D02_CD_TIPO_BOLLA =
                 I01_TIPOLOGIA_BOLLE.I01_CD_TIPO_BOLLA(+)
          AND D02_DDT_TESTATA.D02_CD_CLIENTE_FATT =
                 R07_R0236_C012456789_001W.R07_CD_CLIENTE(+)
          AND D02_DDT_TESTATA.D02_CD_ASS_FISC =
                 C01_CODICI_IVA_01.C01_CD_IVA(+)
          AND D03_DDT_RIGHE_ART.D03_CD_IVA = C01_CODICI_IVA_02.C01_CD_IVA(+)
          AND D03_DDT_RIGHE_ART.D03_CD_UNITA_MIS =
                 G04_UNITA_MISURA.G04_CD_UNITA_MIS(+)
          AND D02_DDT_TESTATA.D02_FLAG_FATTURATA = 'N'
          AND (D03_DDT_RIGHE_ART.D03_NR_DISP_CLI IS NULL
               OR D03_DDT_RIGHE_ART.D03_NR_DISP_CLI = 0)
          AND I01_TIPOLOGIA_BOLLE.I01_CD_TIPO_DOCUMENTO IS NOT NULL
/


  CREATE OR REPLACE FORCE EDITIONABLE VIEW "INTEX2"."PRINT_DDT_DA_FATTURARE" ("D02_CD_CLIENTE_FATT", "R07_RAGIONE_SOC", "D02_DT_BOLLA", "D03_CAPI_IN_USCITA", "D03_KG_IN_USCITA", "D03_PREZZO_CAPO", "ELENCO_DDT") AS
  SELECT D02_CD_CLIENTE_FATT,
            R07_RAGIONE_SOC,
            D02_DT_BOLLA,
            SUM (D03_CAPI_IN_USCITA) AS D03_CAPI_IN_USCITA,
            SUM (D03_KG_IN_USCITA) AS D03_KG_IN_USCITA,
            SUM (CALC_PREZZO (Z09_FL_PREZZO_ZERO,
                              D03_PREZZO_FORFAIT,
                              D03_PREZZO_UNI,
                              D03_PREZZO_CAPO,
                              D03_PREZZO_KG,
                              D03_CAPI_IN_USCITA,
                              D03_KG_IN_USCITA))
               AS D03_PREZZO_CAPO,
            GetNrDataDDT (D02_CD_CLIENTE_FATT) AS ELENCO_DDT
       FROM DDT_PREZZI_002W
      WHERE D02_FLAG_FATTURATA = 'N'
   GROUP BY D02_CD_CLIENTE_FATT,
            R07_RAGIONE_SOC,
            D02_DT_BOLLA,
            D03_PREZZO_CAPO
   ORDER BY D02_CD_CLIENTE_FATT
/

SQL> 
SQL> SPOOL OFF
