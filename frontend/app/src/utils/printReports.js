import { authFetch } from './auth'
import { escapeHtml, openPrintDocument, printCell } from './printDocument'

function formatDateIso(iso) {
  if (!iso) return '—'
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return String(iso)
  return `${m[3]}/${m[2]}/${m[1]}`
}

function formatNrDisposizione(item) {
  if (item == null || item.nr_disposizione == null) return '—'
  return item.anno_disposizione
    ? `${item.anno_disposizione}/${item.nr_disposizione}`
    : String(item.nr_disposizione)
}

function formatQty(n) {
  const v = Number(n) || 0
  return v.toLocaleString('it-IT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 3,
  })
}

function formatPrezzo(n) {
  if (n == null || n === '') return null
  const v = Number(n)
  if (!Number.isFinite(v)) return null
  return v.toLocaleString('it-IT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function flagOffertaLabel(prezzi) {
  if (!prezzi) return null
  const vis = String(prezzi.flag_visibile || '').toUpperCase()
  if (vis === 'S') return 'Accettata'
  if (vis === 'P') return 'Prototipo'
  if (prezzi.flag_prototipo === 'S' || prezzi.flag_prototipo === true) return 'Prototipo'
  return vis || null
}

function formatVal(v) {
  if (v == null || v === '') return '—'
  if (Array.isArray(v)) return v.filter(Boolean).join(' → ') || '—'
  return String(v)
}

const CAMPO_LABELS = {
  codice_articolo: 'Articolo',
  codice_stagione: 'Stagione',
  codice_ciclo: 'Cod. ciclo',
  codice_ciclo_cli: 'Ciclo cliente',
  codice_composizione: 'Composizione',
  codice_linea: 'Linea',
  ds_ciclo: 'Descrizione ciclo',
  ds_ciclo_bolle_fat: 'Desc. bolle/fatt.',
  note: 'Note',
  ds_applicazione: 'Applicazione',
  ds_ricamo: 'Ricamo',
  ds_stampa: 'Stampa',
  codice_reparto: 'Reparto',
  codice_gruppo: 'Gruppo',
  fase: 'Fase',
  nota_fase: 'Nota fase',
  unita_misura_fase: 'U.M. fase',
  macrofase: 'Macrofase',
}

function campoLabel(campo) {
  return CAMPO_LABELS[campo] || campo
}

export function cicloKey(item) {
  return [
    item.codice_cliente,
    item.codice_articolo,
    item.codice_ciclo,
    item.codice_linea,
    item.codice_stagione,
    item.codice_composizione,
  ].join('|')
}

function kv(label, value) {
  return `<div><span>${escapeHtml(label)}</span><strong>${printCell(value)}</strong></div>`
}

function tableHtml(headers, rows) {
  if (!rows.length) return '<p class="empty">Nessun dato.</p>'
  return `<table>
    <thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join('')}</tr></thead>
    <tbody>${rows
      .map(
        (cells) =>
          `<tr>${cells.map((c) => `<td>${c}</td>`).join('')}</tr>`
      )
      .join('')}</tbody>
  </table>`
}

function prezziHtml(prezzi) {
  if (!prezzi) return '<p class="empty">nessun prezzo</p>'
  const capo = formatPrezzo(prezzi.prezzo_capo)
  const kg = formatPrezzo(prezzi.prezzo_kg)
  const stato = flagOffertaLabel(prezzi)
  const fasce = (prezzi.fasce || []).filter((f) => Number(f.prezzo) > 0)
  const bits = []
  if (prezzi.codice_univoco != null) bits.push(`Cod. univoco ${prezzi.codice_univoco}`)
  if (stato) bits.push(stato)
  if (capo != null) bits.push(`Capo ${capo}`)
  if (kg != null) bits.push(`Kg ${kg}`)
  if (prezzi.valuta) bits.push(`Valuta ${prezzi.valuta}`)
  const fasceHtml = fasce.length
    ? `<ul class="plain">${fasce
        .map((f) => {
          const q =
            f.qta != null ? ` (≥${formatQty(f.qta)}${f.tq || ''})` : ''
          const tp = f.tp ? ` (${f.tp})` : ''
          return `<li>Fascia ${escapeHtml(f.n)}${escapeHtml(q)}: <strong>${escapeHtml(
            formatPrezzo(f.prezzo)
          )}</strong>${escapeHtml(tp)}</li>`
        })
        .join('')}</ul>`
    : ''
  return `<div>${escapeHtml(bits.join(' · ') || '—')}${fasceHtml}</div>`
}

function diffHtml(items) {
  if (!items?.length) return '<p class="empty">nessuna</p>'
  return `<ul class="plain">${items
    .map((d) => {
      const pen =
        d.penalita != null && Number(d.penalita) > 0 ? ` (−${d.penalita})` : ''
      return `<li><strong>${escapeHtml(campoLabel(d.campo))}</strong>${
        d.tipo ? ` [${escapeHtml(d.tipo)}]` : ''
      }: ${escapeHtml(formatVal(d.input))} → ${escapeHtml(formatVal(d.candidato))}${escapeHtml(
        pen
      )}</li>`
    })
    .join('')}</ul>`
}

function similiHtml(items) {
  if (!items?.length) return '<p class="empty">nessuna</p>'
  return `<ul class="plain">${items
    .map((s) => {
      const note = s.dettaglio ? ` — ${s.dettaglio}` : ''
      return `<li><strong>${escapeHtml(campoLabel(s.campo))}</strong>: ${escapeHtml(
        formatVal(s.valore)
      )}${escapeHtml(note)}</li>`
    })
    .join('')}</ul>`
}

function compatItemHtml(item, i) {
  const c = item.ciclo || {}
  const prezzi = item.prezzi || c.prezzi || null
  const pct = Number(item.compatibilita) || 0
  const label = [
    c.codice_ciclo,
    c.ds_ciclo || c.ds_articolo,
    c.codice_stagione || c.ds_stagione,
  ]
    .filter(Boolean)
    .join(' · ')
  const keys = [
    c.ragione_sociale || c.codice_cliente,
    c.codice_articolo,
    c.codice_linea,
    c.codice_composizione,
  ]
    .filter(Boolean)
    .join(' / ')
  const fasi =
    c.fasi?.length > 0
      ? `<h3>Fasi candidato</h3><ol class="fasi">${c.fasi
          .map((f) => `<li>${escapeHtml(f)}</li>`)
          .join('')}</ol>`
      : ''
  return `<div class="compat">
    <div class="compat__head">
      <span class="pct">${escapeHtml(
        pct.toLocaleString('it-IT', { maximumFractionDigits: 1 })
      )}%</span>
      · ${escapeHtml(label || `Candidato ${i + 1}`)}
      ${keys ? `<span class="muted"> · ${escapeHtml(keys)}</span>` : ''}
    </div>
    <h3>Prezzi offerta</h3>
    ${prezziHtml(prezzi)}
    <h3>Differenze</h3>
    ${diffHtml(item.differenze)}
    <h3>Similarità</h3>
    ${similiHtml(item.simili)}
    ${fasi}
  </div>`
}

async function fetchJson(url) {
  const res = await authFetch(url)
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
  return data
}

/**
 * Prefetch fasi + utilizzi for all visible cicli rows (uses cache when present).
 * Returns updated maps; does not mutate expand UI state.
 */
export async function prefetchCicliNested(items, fasiByKey, utilizziByKey, filters = {}) {
  const nextFasi = { ...fasiByKey }
  const nextUtilizzi = { ...utilizziByKey }

  await Promise.all(
    items.map(async (item) => {
      const key = cicloKey(item)
      const base = {
        codice_cliente: item.codice_cliente,
        codice_articolo: item.codice_articolo,
        codice_ciclo: item.codice_ciclo,
        codice_linea: item.codice_linea,
        codice_stagione: item.codice_stagione,
        codice_composizione: item.codice_composizione,
      }

      const jobs = []
      if (!nextFasi[key]) {
        jobs.push(
          (async () => {
            const params = new URLSearchParams(base)
            try {
              const resData = await fetchJson(`/api/cicli/fasi?${params}`)
              nextFasi[key] = resData.data || []
            } catch (_) {
              nextFasi[key] = []
            }
          })()
        )
      }
      if (!nextUtilizzi[key]) {
        jobs.push(
          (async () => {
            const params = new URLSearchParams(base)
            if (filters.colore) params.append('colore', filters.colore)
            if (filters.tessuto) params.append('tessuto', filters.tessuto)
            if (filters.commessa) params.append('commessa', filters.commessa)
            if (filters.modello) params.append('modello', filters.modello)
            if (filters.articolo_fiscale) {
              params.append('articolo_fiscale', filters.articolo_fiscale)
            }
            if (filters.data_bolla_da) params.append('data_bolla_da', filters.data_bolla_da)
            if (filters.data_bolla_a) params.append('data_bolla_a', filters.data_bolla_a)
            try {
              const resData = await fetchJson(`/api/cicli/utilizzi?${params}`)
              nextUtilizzi[key] = resData.data || []
            } catch (_) {
              nextUtilizzi[key] = []
            }
          })()
        )
      }
      await Promise.all(jobs)
    })
  )

  return { fasiByKey: nextFasi, utilizziByKey: nextUtilizzi }
}

function fasiTable(fasi) {
  return tableHtml(
    ['Seq', 'Fase', 'Descrizione', 'UM', 'Note'],
    (fasi || []).map((f) => [
      printCell(f.sequenza),
      printCell(f.codice_fase),
      printCell(f.ds_fase),
      printCell(f.codice_unita_mis),
      printCell(f.note),
    ])
  )
}

function utilizziTable(utilizzi) {
  return tableHtml(
    [
      'Data bolla',
      'N. disposizione',
      'N. bolla',
      'Commessa',
      'Colore',
      'Modello',
      'Descrizione / Articolo',
      'Tessuto',
      'Art. fiscale',
      'Capi',
      'Kg',
      'Note',
    ],
    (utilizzi || []).map((u) => [
      printCell(u.data_bolla),
      printCell(formatNrDisposizione(u)),
      printCell(u.nr_bolla),
      printCell(u.commessa),
      printCell(u.ds_colore || u.cd_colore),
      printCell(u.modello),
      printCell(u.ds_articolo),
      printCell(u.tessuto),
      printCell(u.articolo_fiscale),
      printCell(u.capi_caricati ?? '—', '—'),
      printCell(u.kg_caricati ?? '—', '—'),
      printCell(u.note),
    ])
  )
}

export function printCicliVistaCicli({
  items,
  fasiByKey,
  utilizziByKey,
  page,
  pages,
  total,
}) {
  const bodyHtml = items
    .map((item) => {
      const key = cicloKey(item)
      const fasi = fasiByKey[key] || []
      const utilizzi = utilizziByKey[key] || []
      return `<section class="block">
        <h2>${printCell(item.codice_ciclo)} — ${printCell(item.ds_ciclo || 'Ciclo')}</h2>
        <div class="kv">
          ${kv('Inserito il', formatDateIso(item.data_ins))}
          ${kv('Ultimo utilizzo', formatDateIso(item.ultima_bolla))}
          ${kv('Righe storico', item.n_righe_storico ?? '—')}
          ${kv('Ciclo cliente', item.codice_ciclo_cli || '—')}
          ${kv(
            'Cliente',
            `${item.ragione_sociale || '—'} (${item.codice_cliente || '—'})`
          )}
          ${kv(
            'Articolo',
            item.ds_articolo
              ? `${item.ds_articolo} (${item.codice_articolo})`
              : item.codice_articolo
          )}
          ${kv('Stagione', item.ds_stagione || item.codice_stagione || '—')}
          ${kv('Composizione', item.ds_composizione || item.codice_composizione || '—')}
        </div>
        <h3>Fasi (${fasi.length})</h3>
        ${fasi.length ? fasiTable(fasi) : '<p class="empty">Nessuna fase.</p>'}
        <h3>Utilizzi (${utilizzi.length})</h3>
        ${
          utilizzi.length
            ? utilizziTable(utilizzi)
            : '<p class="empty">Nessun utilizzo nello storico.</p>'
        }
      </section>`
    })
    .join('')

  openPrintDocument({
    title: 'Risultati cicli (vista cicli)',
    meta: escapeHtml(
      `Pagina ${page}/${pages || 1} · ${items.length} di ${total} risultati · fasi e utilizzi espansi`
    ),
    bodyHtml: bodyHtml || '<p class="empty">Nessun risultato.</p>',
  })
}

export function printCicliVistaUtilizzi({ items, page, pages, total }) {
  const bodyHtml = tableHtml(
    [
      'Data bolla',
      'N. disposizione',
      'N. bolla',
      'Ciclo',
      'Cliente',
      'Commessa',
      'Modello',
      'Descrizione / Articolo',
      'Colore',
      'Tessuto',
      'Art. fiscale',
      'Capi / Kg',
    ],
    items.map((item) => [
      printCell(item.data_bolla),
      printCell(formatNrDisposizione(item)),
      printCell(item.nr_bolla),
      printCell(
        item.codice_ciclo_cli
          ? `${item.codice_ciclo} (${item.codice_ciclo_cli})`
          : item.codice_ciclo
      ),
      printCell(`${item.ragione_sociale || '—'} (${item.codice_cliente || '—'})`),
      printCell(item.commessa),
      printCell(item.modello),
      printCell(item.ds_articolo),
      printCell(
        item.ds_colore && item.cd_colore
          ? `${item.ds_colore} (${item.cd_colore})`
          : item.ds_colore || item.cd_colore
      ),
      printCell(item.tessuto),
      printCell(item.articolo_fiscale),
      printCell(`${item.capi_caricati ?? '—'} / ${item.kg_caricati ?? '—'}`),
    ])
  )

  openPrintDocument({
    title: 'Risultati cicli (vista utilizzi)',
    meta: escapeHtml(`Pagina ${page}/${pages || 1} · ${items.length} di ${total} risultati`),
    bodyHtml,
  })
}

export function printPrezziMancanti({
  rows,
  compatByRow,
  livelloByRow,
  defaultLivello,
  page,
  pages,
  total,
  range,
  prezziPresenti,
  rowKeyFn,
  livelloHint,
}) {
  const period =
    range?.da && range?.a
      ? `Periodo ${formatDateIso(range.da)} – ${formatDateIso(range.a)}`
      : ''
  const bodyHtml = rows
    .map((row, idx) => {
      const id = rowKeyFn(row, idx)
      const stato = compatByRow[id] || {}
      const livello = livelloByRow[id] ?? defaultLivello
      const hint = livelloHint?.[livello] || ''
      const compatibili = stato.compatibili || []
      const loadingNote = stato.loading
        ? '<p class="empty">Cicli compatibili ancora in caricamento al momento della stampa.</p>'
        : ''
      const errorNote = stato.error
        ? `<p class="empty">Errore compatibili: ${escapeHtml(stato.error)}</p>`
        : ''
      const list =
        !stato.loading && !stato.error
          ? compatibili.length
            ? compatibili.map((c, i) => compatItemHtml(c, i)).join('')
            : '<p class="empty">Nessun ciclo compatibile a questo livello.</p>'
          : ''
      return `<section class="block">
        <h2>DDT ${printCell(row.ns_ddt)} · ciclo ${printCell(row.ciclo)}</h2>
        <div class="kv">
          ${kv('Cliente', row.cliente)}
          ${kv('Data DDT', row.data_ddt)}
          ${kv('Tipo', row.tipo)}
          ${kv('Articolo', row.articolo)}
          ${kv('Linea', row.linea || '—')}
          ${kv('Stag. listino', row.stagione_listino || '—')}
          ${kv('Stag. prod.', row.stagione_produzione || '—')}
          ${kv('Composizione', row.composizione || '—')}
          ${kv('Ns. disposiz.', row.ns_disposiz)}
          ${kv('Ciclo lavoro', row.ciclo_lavoro || '—')}
          ${kv('Capi', formatQty(row.capi_sped))}
          ${kv('Kg', formatQty(row.kg_sped))}
        </div>
        <h3>Cicli compatibili — livello ${escapeHtml(livello)}${
          hint ? ` (${escapeHtml(hint)})` : ''
        }${stato.soglia != null ? ` · soglia ${escapeHtml(stato.soglia)}%` : ''}</h3>
        ${loadingNote}${errorNote}${list}
      </section>`
    })
    .join('')

  openPrintDocument({
    title: 'Lista controllo prezzi mancanti',
    meta: escapeHtml(
      [
        period,
        `Pagina ${page}/${pages || 1}`,
        `${rows.length} di ${total} righe`,
        prezziPresenti ? 'solo cicli con prezzo' : 'tutti i compatibili',
        'dettagli compatibili espansi',
      ]
        .filter(Boolean)
        .join(' · ')
    ),
    bodyHtml: bodyHtml || '<p class="empty">Nessuna riga.</p>',
  })
}

export function printCicliCompatibili({
  compatibili,
  livello,
  soglia,
  livelloHint,
  inputSummary,
}) {
  const hint = livelloHint?.[livello] || ''
  const refBits = []
  if (inputSummary?.codice_ciclo) refBits.push(`riferimento ${inputSummary.codice_ciclo}`)
  if (inputSummary?.fasi?.length) refBits.push(`fasi: ${inputSummary.fasi.join(', ')}`)
  const bodyHtml = compatibili.length
    ? compatibili.map((c, i) => compatItemHtml(c, i)).join('')
    : '<p class="empty">Nessun ciclo compatibile.</p>'

  openPrintDocument({
    title: 'Ricerca cicli compatibili',
    meta: escapeHtml(
      [
        ...refBits,
        `livello ${livello}${hint ? ` (${hint})` : ''}`,
        soglia != null ? `soglia ${soglia}%` : null,
        `${compatibili.length} risultati`,
        'dettagli espansi',
      ]
        .filter(Boolean)
        .join(' · ')
    ),
    bodyHtml,
  })
}
