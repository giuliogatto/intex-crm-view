import { useState, useEffect, useCallback } from 'react'
import LoadingOverlay from '../components/LoadingOverlay'
import { useAuth } from '../context/AuthContext'
import { authFetch } from '../utils/auth'

const TABS = [
  { id: 'clienti', label: 'Performance Clienti' },
  { id: 'produzione', label: 'Produzione' },
  // Temporarily removed from nav — "Controllo Perdite" and "Simulatore & Opportunità" links hidden; tab logic kept below.
  // { id: 'controllo', label: 'Controllo Perdite' },
  // { id: 'opportunita', label: 'Simulatore & Opportunità' },
]

const CLIENTI_TOC = [
  {
    id: 'fatturato-mensile',
    label: 'Fatturato mensile',
    description: 'Andamento del fatturato negli ultimi 24 mesi, mese per mese.',
  },
  {
    id: 'concentrazione',
    label: 'Concentrazione clienti',
    description: 'Quota di fatturato sui 5 clienti principali, confrontata con il periodo precedente.',
  },
  {
    id: 'top-clienti',
    label: 'Top 10 clienti',
    description: 'Classifica dei clienti per volume di fatturato negli ultimi 12 mesi.',
  },
  {
    id: 'erosione',
    label: 'Clienti a rischio',
    description: 'Segnali di erosione: calo semestrale del fatturato o intervalli tra ordini in aumento.',
  },
  {
    id: 'dormienti',
    label: 'Clienti dormienti',
    description: 'Clienti senza ordini da oltre 90 giorni, con storico di fatturato recente.',
  },
  {
    id: 'nuovi',
    label: 'Clienti nuovi',
    description: 'Clienti acquisiti negli ultimi 12 mesi e relativo contributo al fatturato.',
  },
]

const PRODUZIONE_TOC = [
  {
    id: 'lead-time-trend',
    label: 'Lead time medio mensile',
    description: 'Evoluzione mensile dei giorni medi tra ordine e consegna, a livello aziendale.',
  },
  {
    id: 'lead-time-top',
    label: 'Lead time più lunghi',
    description: 'Ordini con i tempi di consegna più elevati nell\'ultimo trimestre.',
  },
  {
    id: 'volumi-mensili',
    label: 'Volume mensile',
    description: 'Mesi con i picchi di kg e capi consegnati.',
  },
  {
    id: 'volumi-settimanali',
    label: 'Volume settimanale Anno su Anno',
    description: 'Confronto settimanale tra anno corrente e anno precedente.',
  },
]

const CONTROLLO_TOC = [
  {
    id: 'totale-sospeso',
    label: 'Totale sospeso',
    description: 'Valore complessivo dei DDT consegnati ma non ancora fatturati da oltre 60 giorni.',
  },
  {
    id: 'ddt-senza-fattura',
    label: 'DDT senza fattura',
    description: 'Elenco delle bolle di consegna ancora da fatturare, con giorni di ritardo.',
  },
  {
    id: 'consegne-non-fatturate',
    label: 'Consegne non fatturate',
    description: 'Riepilogo per cliente del valore stimato non ancora fatturato.',
  },
  {
    id: 'fatture-senza-ddt',
    label: 'Fatture senza DDT',
    description: 'Fatture emesse senza bolla di consegna collegata nel sistema.',
  },
]

const OPPORTUNITA_TOC = [
  {
    id: 'stress-test',
    label: 'Stress test fatturato',
    description: 'Simula l\'impatto sul fatturato di una riduzione degli ordini dei principali clienti.',
  },
  {
    id: 'clienti-ideali',
    label: 'Clienti ideali',
    description: 'Clienti con buon fatturato e lead time contenuti negli ultimi 12 mesi.',
  },
  {
    id: 'insight-trimestre',
    label: 'Insight del trimestre',
    description: 'Anomalie automatiche del trimestre in corso, con tipo (categoria) e severità (priorità 1–5).',
  },
]

const INSIGHT_TIPO_LABELS = {
  ddt_non_fatturato_60g: 'DDT non fatturato (>60 gg)',
  fattura_senza_ddt: 'Fattura senza DDT',
  consegne_non_fatturate: 'Consegne non fatturate',
  prezzo_articolo_spostamento: 'Variazione prezzo articolo',
}

function formatTipoAnomalia(tipo) {
  return INSIGHT_TIPO_LABELS[tipo] || tipo
}

function formatEuro(num) {
  if (num == null || Number.isNaN(num)) return '—'
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(num)
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('it-IT')
}

function DataTable({ columns, rows, emptyMessage = 'Nessun dato.' }) {
  if (!rows?.length) {
    return <p className="meta">{emptyMessage}</p>
  }
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id || i}>
              {columns.map((col) => (
                <td key={col.key}>{col.render ? col.render(row) : (row[col.key] ?? '—')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function KpiCard({ label, value, hint }) {
  return (
    <div className="analisi-kpi">
      <div className="analisi-kpi__label">{label}</div>
      <div className="analisi-kpi__value">{value}</div>
      {hint && <div className="analisi-kpi__hint">{hint}</div>}
    </div>
  )
}

function AnalisiToc({ items }) {
  return (
    <nav className="analisi-toc" aria-label="Indice delle sezioni">
      <div className="analisi-toc__title">Indice</div>
      <ol className="analisi-toc__list">
        {items.map((item) => (
          <li key={item.id} className="analisi-toc__item">
            <a href={`#${item.id}`} className="analisi-toc__link">
              {item.label}
            </a>
            <span className="analisi-toc__desc">{item.description}</span>
          </li>
        ))}
      </ol>
    </nav>
  )
}

export default function AnalisiPage({ subTabOverride, scrollTargetOverride }) {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('clienti')
  const [loading, setLoading] = useState(true)
  const [meta, setMeta] = useState(null)
  const [ranking, setRanking] = useState([])
  const [fatturatoMensile, setFatturatoMensile] = useState([])
  const [concentrazione, setConcentrazione] = useState(null)
  const [erosione, setErosione] = useState([])
  const [dormienti, setDormienti] = useState([])
  const [nuovi, setNuovi] = useState([])
  const [leadTimeTrend, setLeadTimeTrend] = useState([])
  const [leadTimeTop, setLeadTimeTop] = useState([])
  const [volumiMensili, setVolumiMensili] = useState([])
  const [volumiSettimanali, setVolumiSettimanali] = useState([])
  const [anomalie, setAnomalie] = useState(null)
  const [qualita, setQualita] = useState([])
  const [insights, setInsights] = useState([])
  const [stressTopN, setStressTopN] = useState(3)
  const [stressPct, setStressPct] = useState(20)
  const [stressResult, setStressResult] = useState(null)
  const [stressLoading, setStressLoading] = useState(false)

  // Gestione deep-linking da Chat Assistant (tab e anchor scrolling)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlTab = params.get('tab')
    const validTabs = ['clienti', 'produzione', 'controllo', 'opportunita']
    
    if (urlTab && validTabs.includes(urlTab)) {
      setActiveTab(urlTab)
    } else {
      const hash = window.location.hash.replace('#', '')
      if (hash) {
        const sectionToTabMap = {
          'fatturato-mensile': 'clienti',
          'concentrazione': 'clienti',
          'top-clienti': 'clienti',
          'erosione': 'clienti',
          'dormienti': 'clienti',
          'nuovi': 'clienti',
          'lead-time-trend': 'produzione',
          'lead-time-top': 'produzione',
          'volumi-mensili': 'produzione',
          'volumi-settimanali': 'produzione',
          'totale-sospeso': 'controllo',
          'ddt-senza-fattura': 'controllo',
          'consegne-non-fatturate': 'controllo',
          'fatture-senza-ddt': 'controllo',
          'stress-test': 'opportunita',
          'clienti-ideali': 'opportunita',
          'insight-trimestre': 'opportunita',
        }
        const deducedTab = sectionToTabMap[hash]
        if (deducedTab) {
          setActiveTab(deducedTab)
        }
      }
    }
    // Clean query parameters from URL after parsing
    if (urlTab) {
      const newUrl = window.location.pathname + window.location.hash
      window.history.replaceState({}, document.title, newUrl)
    }
  }, [])

  // Esegue lo scroll all'ancora desiderata una volta caricati i dati
  useEffect(() => {
    const hash = window.location.hash
    if (hash && !loading) {
      const timer = setTimeout(() => {
        const element = document.querySelector(hash)
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 200)
      return () => clearTimeout(timer)
    }
  }, [activeTab, loading])

  // Supporto per i prop overrides da parte dell'applicazione genitore (App.jsx)
  useEffect(() => {
    if (subTabOverride) {
      setActiveTab(subTabOverride)
    }
  }, [subTabOverride])

  useEffect(() => {
    if (scrollTargetOverride && !loading) {
      const timer = setTimeout(() => {
        const element = document.getElementById(scrollTargetOverride)
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 150)
      return () => clearTimeout(timer)
    }
  }, [scrollTargetOverride, loading])

  const loadClienti = useCallback(async () => {
    const [metaRes, rankRes, fatRes, concRes, erosRes, dormRes, nuoviRes] = await Promise.all([
      authFetch('/api/analisi/meta'),
      authFetch('/api/analisi/clienti/ranking?limit=10'),
      authFetch('/api/analisi/fatturato/mensile?mesi=24'),
      authFetch('/api/analisi/clienti/concentrazione?top_n=5'),
      authFetch('/api/analisi/clienti/erosione'),
      authFetch('/api/analisi/clienti/dormienti'),
      authFetch('/api/analisi/clienti/nuovi'),
    ])
    const [metaJ, rankJ, fatJ, concJ, erosJ, dormJ, nuoviJ] = await Promise.all([
      metaRes.json(), rankRes.json(), fatRes.json(), concRes.json(),
      erosRes.json(), dormRes.json(), nuoviRes.json(),
    ])
    setMeta(metaJ.data)
    setRanking(rankJ.data || [])
    setFatturatoMensile((fatJ.data || []).reverse())
    setConcentrazione(concJ.data)
    setErosione(erosJ.data || [])
    setDormienti(dormJ.data || [])
    setNuovi(nuoviJ.data || [])
  }, [])

  const loadProduzione = useCallback(async () => {
    const [trendRes, topRes, volMRes, volSRes] = await Promise.all([
      authFetch('/api/analisi/produzione/lead-time?tipo=trend&mesi=24'),
      authFetch('/api/analisi/produzione/lead-time?tipo=top'),
      authFetch('/api/analisi/produzione/volumi?granularita=mensile'),
      authFetch('/api/analisi/produzione/volumi?granularita=settimanale'),
    ])
    const [trendJ, topJ, volMJ, volSJ] = await Promise.all([
      trendRes.json(), topRes.json(), volMRes.json(), volSRes.json(),
    ])
    setLeadTimeTrend(trendJ.data || [])
    setLeadTimeTop(topJ.data || [])
    setVolumiMensili(volMJ.data || [])
    setVolumiSettimanali(volSJ.data || [])
  }, [])

  const loadControllo = useCallback(async () => {
    const res = await authFetch('/api/analisi/controllo/anomalie?tipo=tutte')
    const json = await res.json()
    setAnomalie(json.data || {})
  }, [])

  const loadOpportunita = useCallback(async () => {
    const [qualRes, insRes] = await Promise.all([
      authFetch('/api/analisi/clienti/qualita?limit=15'),
      authFetch('/api/analisi/opportunita/trimestre?limit=3'),
    ])
    const [qualJ, insJ] = await Promise.all([qualRes.json(), insRes.json()])
    setQualita(qualJ.data || [])
    setInsights(insJ.data || [])
  }, [])

  useEffect(() => {
    setLoading(true)
    const loaders = {
      clienti: loadClienti,
      produzione: loadProduzione,
      controllo: loadControllo,
      opportunita: loadOpportunita,
    }
    loaders[activeTab]()
      .catch((err) => console.error('Analisi load error:', err))
      .finally(() => setLoading(false))
  }, [activeTab, loadClienti, loadProduzione, loadControllo, loadOpportunita])

  const runStressTest = () => {
    setStressLoading(true)
    authFetch('/api/analisi/simulazioni/stress-test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ top_n: stressTopN, riduzione_pct: stressPct }),
    })
      .then((r) => r.json())
      .then((j) => setStressResult(j.data))
      .catch((err) => console.error(err))
      .finally(() => setStressLoading(false))
  }

  const maxFatturato = Math.max(...fatturatoMensile.map((r) => r.fatturato_mensile || 0), 1)

  return (
    <div className="analisi-dashboard-tab">
      {loading && <LoadingOverlay />}

      {meta?.last_success && (
        <p className="meta analisi-meta">
          Dati analitici aggiornati al {formatDate(meta.last_success)}
          {meta.elapsed_seconds != null && ` (refresh ${Number(meta.elapsed_seconds).toFixed(1)}s)`}
        </p>
      )}
      {meta?.last_error && (
        <p className="meta analisi-meta analisi-meta--error">
          Ultimo errore analytics: {meta.last_error}
        </p>
      )}

      <nav className="nav-primary">
            {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`nav-tab ${activeTab === tab.id ? 'is-active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === 'clienti' && (
        <div className="analisi-grid">
          <AnalisiToc items={CLIENTI_TOC} />

          <div id="fatturato-mensile" className="analisi-section panel">
            <div className="panel__head">Fatturato mensile (ultimi 24 mesi)</div>
            <div className="panel__body">
              <div className="analisi-bar-chart">
                {fatturatoMensile.map((row) => (
                  <div key={`${row.anno}-${row.mese}`} className="analisi-bar-row">
                    <span className="analisi-bar-label">{row.mese}/{row.anno}</span>
                    <div className="analisi-bar-track">
                      <div
                        className="analisi-bar-fill"
                        style={{ width: `${(100 * (row.fatturato_mensile || 0)) / maxFatturato}%` }}
                      />
                    </div>
                    <span className="analisi-bar-value">{formatEuro(row.fatturato_mensile)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {concentrazione && (
            <div id="concentrazione" className="analisi-section analisi-kpi-row">
              <KpiCard
                label="Quota top 5 (ultimi 12 mesi)"
                value={`${concentrazione.quota_top_n_ultimi_12m ?? '—'}%`}
              />
              <KpiCard
                label="Quota top 5 (periodo precedente)"
                value={`${concentrazione.quota_top_n_periodo_precedente ?? '—'}%`}
              />
              <KpiCard
                label="Fatturato totale 12m"
                value={formatEuro(concentrazione.fatturato_totale_12m)}
              />
            </div>
          )}

          <div id="top-clienti" className="analisi-section panel">
            <div className="panel__head">Top 10 clienti per fatturato (12 mesi)</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'rank', label: '#' },
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'fatturato', label: 'Fatturato', render: (r) => formatEuro(r.fatturato) },
                  { key: 'percentuale', label: '% totale', render: (r) => `${r.percentuale ?? '—'}%` },
                ]}
                rows={ranking}
              />
            </div>
          </div>

          <div id="erosione" className="analisi-section panel">
            <div className="panel__head">Clienti a rischio (erosione / intervalli)</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'calo_percentuale', label: 'Calo semestrale %', render: (r) => r.calo_percentuale != null ? `${r.calo_percentuale}%` : '—' },
                  { key: 'allungamento_giorni', label: 'Δ giorni tra ordini' },
                ]}
                rows={erosione}
                emptyMessage="Nessun segnale di erosione."
              />
            </div>
          </div>

          <div id="dormienti" className="analisi-section panel">
            <div className="panel__head">Clienti dormienti (&gt;90 gg)</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'data_ultimo_ordine', label: 'Ultimo ordine', render: (r) => formatDate(r.data_ultimo_ordine) },
                  { key: 'giorni_dall_ultimo_ordine', label: 'Giorni' },
                  { key: 'fatturato_rolling_12m', label: 'Fatt. 12m', render: (r) => formatEuro(r.fatturato_rolling_12m) },
                ]}
                rows={dormienti}
                emptyMessage="Nessun cliente dormiente."
              />
            </div>
          </div>

          <div id="nuovi" className="analisi-section panel">
            <div className="panel__head">Clienti nuovi (ultimi 12 mesi)</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'data_primo_ordine', label: 'Primo ordine', render: (r) => formatDate(r.data_primo_ordine) },
                  { key: 'fatturato_rolling_12m', label: 'Fatturato', render: (r) => formatEuro(r.fatturato_rolling_12m) },
                ]}
                rows={nuovi}
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'produzione' && (
        <div className="analisi-grid">
          <AnalisiToc items={PRODUZIONE_TOC} />

          <div id="lead-time-trend" className="analisi-section panel">
            <div className="panel__head">Lead time medio mensile</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'mese', label: 'Mese', render: (r) => `${r.mese}/${r.anno}` },
                  { key: 'lead_time_medio_aziendale', label: 'Giorni medi' },
                  { key: 'numero_ordini', label: 'Ordini' },
                ]}
                rows={leadTimeTrend}
              />
            </div>
          </div>
          <div id="lead-time-top" className="analisi-section panel">
            <div className="panel__head">Ordini con lead time più lungo (ultimo trimestre)</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'numero_offerta', label: 'Cartellino' },
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'lead_time_giorni', label: 'Giorni' },
                ]}
                rows={leadTimeTop}
              />
            </div>
          </div>
          <div id="volumi-mensili" className="analisi-section panel">
            <div className="panel__head">Picchi volume mensile (kg consegnati)</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'mese', label: 'Mese', render: (r) => `${r.mese}/${r.anno}` },
                  { key: 'kg_totali', label: 'Kg' },
                  { key: 'capi_totali', label: 'Capi' },
                ]}
                rows={volumiMensili}
              />
            </div>
          </div>
          <div id="volumi-settimanali" className="analisi-section panel">
            <div className="panel__head">Volume settimanale Anno su Anno</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'settimana', label: 'Sett.' },
                  { key: 'kg_quest_anno', label: 'Kg anno corr.' },
                  { key: 'kg_anno_scorso', label: 'Kg anno prec.' },
                ]}
                rows={volumiSettimanali}
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'controllo' && anomalie && (
        <div className="analisi-grid">
          <AnalisiToc items={CONTROLLO_TOC} />

          <div id="totale-sospeso" className="analisi-section">
            <KpiCard
              label="Valore totale DDT non fatturati >60 gg"
              value={formatEuro(anomalie.totale_sospeso)}
            />
          </div>
          <div id="ddt-senza-fattura" className="analisi-section panel">
            <div className="panel__head">DDT senza fattura</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'numero_bolla', label: 'Bolla' },
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'giorni_ritardo', label: 'Giorni' },
                  { key: 'valore_stimato', label: 'Valore', render: (r) => formatEuro(r.valore_stimato) },
                ]}
                rows={anomalie.ddt_non_fatturati || []}
              />
            </div>
          </div>
          <div id="consegne-non-fatturate" className="analisi-section panel">
            <div className="panel__head">Consegne non fatturate per cliente</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'valore_stimato_non_fatturato', label: 'Valore', render: (r) => formatEuro(r.valore_stimato_non_fatturato) },
                ]}
                rows={anomalie.consegne_non_fatturate || []}
              />
            </div>
          </div>
          <div id="fatture-senza-ddt" className="analisi-section panel">
            <div className="panel__head">Fatture senza DDT collegato</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'numero_disposizione', label: 'Disp.' },
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'valore_stimato', label: 'Importo', render: (r) => formatEuro(r.valore_stimato) },
                ]}
                rows={anomalie.fatture_senza_ddt || []}
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'opportunita' && (
        <div className="analisi-grid">
          <AnalisiToc items={OPPORTUNITA_TOC} />

          <div id="stress-test" className="analisi-section panel">
            <div className="panel__head">Stress test fatturato</div>
            <div className="panel__body">
              <div className="analisi-stress-controls">
                <label>
                  Top N clienti
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={stressTopN}
                    onChange={(e) => setStressTopN(Number(e.target.value))}
                  />
                </label>
                <label>
                  Riduzione %
                  <input
                    type="range"
                    min={0}
                    max={50}
                    value={stressPct}
                    onChange={(e) => setStressPct(Number(e.target.value))}
                  />
                  <span>{stressPct}%</span>
                </label>
                <button type="button" className="btn btn--primary" onClick={runStressTest} disabled={stressLoading}>
                  Simula
                </button>
              </div>
              {stressResult && (
                <div className="analisi-stress-result">
                  <p>
                    <strong>Perdita stimata:</strong> {formatEuro(stressResult.perdita_totale)}
                  </p>
                  {stressResult.mesi_piu_colpiti?.length > 0 && (
                    <DataTable
                      columns={[
                        { key: 'mese', label: 'Mese', render: (r) => `${r.mese}/${r.anno}` },
                        { key: 'perdita_stimata', label: 'Perdita', render: (r) => formatEuro(r.perdita_stimata) },
                      ]}
                      rows={stressResult.mesi_piu_colpiti}
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          <div id="clienti-ideali" className="analisi-section panel">
            <div className="panel__head">Clienti ideali (fatturato + lead time)</div>
            <div className="panel__body" style={{ padding: 0 }}>
              <DataTable
                columns={[
                  { key: 'ragione_sociale', label: 'Cliente' },
                  { key: 'fatturato_rolling_12m', label: 'Fatturato', render: (r) => formatEuro(r.fatturato_rolling_12m) },
                  { key: 'lead_time_medio_giorni', label: 'Lead time (gg)' },
                ]}
                rows={qualita}
              />
            </div>
          </div>

          <div id="insight-trimestre" className="analisi-section panel">
            <div className="panel__head">Insight del trimestre</div>
            <div className="panel__body">
              <div className="analisi-section-note">
                <p>
                  Segnali rilevati automaticamente a fine sincronizzazione nel trimestre corrente,
                  ordinati per severità e valore stimato.
                </p>
                <p>
                  <strong>Tipo</strong> — codice che identifica la categoria di anomalia:
                </p>
                <ul className="analisi-section-note__list">
                  <li>
                    <code>ddt_non_fatturato_60g</code> — bolla di consegna senza fattura collegata da oltre 60 giorni
                  </li>
                  <li>
                    <code>fattura_senza_ddt</code> — fattura emessa senza bolla di consegna associata
                  </li>
                  <li>
                    <code>consegne_non_fatturate</code> — valore stimato di consegne ancora da fatturare per cliente
                  </li>
                  <li>
                    <code>prezzo_articolo_spostamento</code> — prezzo unitario di un articolo variato di oltre il 10%
                    rispetto alla media storica dello stesso cliente
                  </li>
                </ul>
                <p>
                  <strong>Severità</strong> — priorità da 1 (bassa) a 5 (critica), assegnata in base all'impatto:
                </p>
                <ul className="analisi-section-note__list">
                  <li>
                    <code>prezzo_articolo_spostamento</code>: 2 (alert informativo)
                  </li>
                  <li>
                    <code>fattura_senza_ddt</code>: 3
                  </li>
                  <li>
                    <code>ddt_non_fatturato_60g</code>: 3 se ≤90 giorni, 4 se &gt;90 giorni, 5 se &gt;120 giorni
                  </li>
                  <li>
                    <code>consegne_non_fatturate</code>: 3 fino a €5.000, 4 oltre €5.000, 5 oltre €10.000
                  </li>
                </ul>
              </div>
              <DataTable
                columns={[
                  {
                    key: 'tipo_anomalia',
                    label: 'Tipo',
                    render: (r) => (
                      <span title={r.tipo_anomalia}>
                        {formatTipoAnomalia(r.tipo_anomalia)}
                      </span>
                    ),
                  },
                  { key: 'descrizione', label: 'Descrizione' },
                  { key: 'valore_stimato', label: 'Valore', render: (r) => formatEuro(r.valore_stimato) },
                  { key: 'severita', label: 'Severità' },
                ]}
                rows={insights}
                emptyMessage="Nessuna anomalia rilevata nel trimestre corrente."
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
