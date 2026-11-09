import React from 'react'

const LIVELLO_HINT = {
  1: 'ampio (≥30%)',
  2: 'medio (≥50%)',
  3: 'alto (≥70%)',
  4: 'molto alto (≥90%)',
  5: 'equivalenti (100%)',
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

function formatVal(v) {
  if (v == null || v === '') return '—'
  if (Array.isArray(v)) return v.filter(Boolean).join(' → ') || '—'
  return String(v)
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

function CompatPct({ value }) {
  const v = Number(value) || 0
  let tone = 'low'
  if (v >= 90) tone = 'high'
  else if (v >= 70) tone = 'mid'
  return (
    <span className={`pm-compat-pct pm-compat-pct--${tone}`} title={`${v}%`}>
      {v.toLocaleString('it-IT', { maximumFractionDigits: 1 })}%
    </span>
  )
}

function PrezziCiclo({ prezzi, compact = false }) {
  if (!prezzi) {
    return compact ? null : <span className="pm-compat-empty">nessun prezzo</span>
  }
  const capo = formatPrezzo(prezzi.prezzo_capo)
  const kg = formatPrezzo(prezzi.prezzo_kg)
  const stato = flagOffertaLabel(prezzi)
  const fasce = (prezzi.fasce || []).filter((f) => Number(f.prezzo) > 0)
  const parts = []
  if (capo != null && Number(prezzi.prezzo_capo) > 0) parts.push(`Capo ${capo}`)
  if (kg != null && Number(prezzi.prezzo_kg) > 0) parts.push(`Kg ${kg}`)
  if (!parts.length && fasce.length) {
    const f0 = fasce[0]
    parts.push(`Fascia ${f0.n}: ${formatPrezzo(f0.prezzo)}`)
  }

  if (compact) {
    if (!parts.length) return null
    return (
      <span
        className="pm-compat-card__prezzi"
        title={[
          prezzi.codice_univoco ? `Cod. univoco ${prezzi.codice_univoco}` : null,
          stato,
          ...parts,
        ]
          .filter(Boolean)
          .join(' · ')}
      >
        {parts.join(' · ')}
      </span>
    )
  }

  return (
    <div className="pm-prezzi-detail">
      <div className="pm-prezzi-detail__main">
        {prezzi.codice_univoco != null ? (
          <span>
            <em>Cod. univoco</em> {prezzi.codice_univoco}
          </span>
        ) : null}
        {stato ? (
          <span className={`pm-prezzi-flag pm-prezzi-flag--${String(stato).toLowerCase()}`}>
            {stato}
          </span>
        ) : null}
        {capo != null ? (
          <span>
            <em>Capo</em> {capo}
          </span>
        ) : null}
        {kg != null ? (
          <span>
            <em>Kg</em> {kg}
          </span>
        ) : null}
        {prezzi.valuta ? (
          <span>
            <em>Valuta</em> {prezzi.valuta}
          </span>
        ) : null}
      </div>
      {fasce.length ? (
        <ul className="pm-prezzi-fasce">
          {fasce.map((f) => (
            <li key={String(f.n)}>
              Fascia {f.n}
              {f.qta != null ? ` (≥${formatQty(f.qta)}${f.tq || ''})` : ''}
              {': '}
              <strong>{formatPrezzo(f.prezzo)}</strong>
              {f.tp ? ` (${f.tp})` : ''}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function DiffList({ items }) {
  if (!items?.length) return <span className="pm-compat-empty">nessuna</span>
  return (
    <ul className="pm-compat-chips pm-compat-chips--diff">
      {items.map((d, i) => (
        <li key={`${d.campo}-${i}`}>
          <span className="pm-compat-chip__field">{campoLabel(d.campo)}</span>
          {d.tipo ? <span className="pm-compat-chip__tipo">{d.tipo}</span> : null}
          <span className="pm-compat-chip__vals">
            {formatVal(d.input)}
            <span aria-hidden="true"> → </span>
            {formatVal(d.candidato)}
          </span>
          {d.penalita != null && Number(d.penalita) > 0 ? (
            <span className="pm-compat-chip__pen">−{d.penalita}</span>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

function SimiliList({ items }) {
  if (!items?.length) return <span className="pm-compat-empty">nessuna</span>
  return (
    <ul className="pm-compat-chips pm-compat-chips--simili">
      {items.map((s, i) => (
        <li key={`${s.campo}-${i}`}>
          <span className="pm-compat-chip__field">{campoLabel(s.campo)}</span>
          <span className="pm-compat-chip__vals">{formatVal(s.valore)}</span>
          {s.dettaglio ? <span className="pm-compat-chip__note">{s.dettaglio}</span> : null}
        </li>
      ))}
    </ul>
  )
}

/**
 * Lista risultati cicli compatibili + slider livello (stile prezzi mancanti).
 */
export default function CicliCompatibiliResults({
  loading,
  error,
  compatibili = [],
  livello,
  soglia,
  onLivelloChange,
}) {
  return (
    <div className="pm-compat">
      <div className="pm-compat__head">
        <div className="pm-compat__title">
          <span className="pm-compat__badge">Cicli compatibili</span>
          <span className="pm-compat__meta">
            livello {livello} · {LIVELLO_HINT[livello] || ''}
            {soglia != null ? ` · soglia ${soglia}%` : ''}
            {!loading && !error ? ` · ${compatibili.length} risultati` : ''}
          </span>
        </div>
        <label className="pm-compat__slider">
          <span>Livello ricerca</span>
          <input
            type="range"
            min={1}
            max={5}
            step={1}
            value={livello}
            disabled={loading}
            onChange={(e) => onLivelloChange(Number(e.target.value))}
            aria-label="Livello compatibilità"
          />
          <span className="pm-compat__slider-value">{livello}</span>
        </label>
      </div>

      {loading ? (
        <div className="pm-compat__loading">
          <div className="spinner spinner--sm" />
          <span>Aggiornamento cicli compatibili…</span>
        </div>
      ) : error ? (
        <p className="pm-compat__error">{error}</p>
      ) : compatibili.length === 0 ? (
        <p className="pm-compat__empty-msg">
          Nessun ciclo compatibile a questo livello. Abbassa lo slider per ampliare la ricerca.
        </p>
      ) : (
        <div className="pm-compat__list">
          {compatibili.map((item, i) => {
            const c = item.ciclo || {}
            const prezzi = item.prezzi || c.prezzi || null
            const label = [
              c.codice_ciclo,
              c.ds_ciclo || c.ds_articolo,
              c.codice_stagione || c.ds_stagione,
            ]
              .filter(Boolean)
              .join(' · ')
            return (
              <details
                key={`${c.codice_cliente}-${c.codice_ciclo}-${c.codice_articolo}-${i}`}
                className="pm-compat-card"
              >
                <summary>
                  <CompatPct value={item.compatibilita} />
                  <span className="pm-compat-card__label" title={label}>
                    {label || 'Ciclo'}
                  </span>
                  <PrezziCiclo prezzi={prezzi} compact />
                  <span className="pm-compat-card__keys">
                    {[
                      c.ragione_sociale || c.codice_cliente,
                      c.codice_articolo,
                      c.codice_linea,
                      c.codice_composizione,
                    ]
                      .filter(Boolean)
                      .join(' / ')}
                  </span>
                </summary>
                <div className="pm-compat-card__body">
                  <div className="pm-compat-card__block">
                    <h4>Prezzi offerta</h4>
                    <PrezziCiclo prezzi={prezzi} />
                  </div>
                  <div className="pm-compat-card__block">
                    <h4>Differenze</h4>
                    <DiffList items={item.differenze} />
                  </div>
                  <div className="pm-compat-card__block">
                    <h4>Similarità</h4>
                    <SimiliList items={item.simili} />
                  </div>
                  {c.fasi?.length ? (
                    <div className="pm-compat-card__block">
                      <h4>Fasi candidato</h4>
                      <ol className="pm-compat-fasi">
                        {c.fasi.map((f, fi) => (
                          <li key={fi}>{f}</li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
                </div>
              </details>
            )
          })}
        </div>
      )}
    </div>
  )
}

export { LIVELLO_HINT }
