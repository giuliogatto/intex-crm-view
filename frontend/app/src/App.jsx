import React, { useState, useEffect, useRef } from 'react'
import Filters from './components/Filters'
import DocumentTable from './components/DocumentTable'
import DiscrepancyPanel from './components/DiscrepancyPanel'
import AnalisiPage from './pages/AnalisiPage'
import ChatPanel from './components/ChatPanel'
import UserMenu from './components/UserMenu'
import AdminNav from './components/AdminNav'
import Pagination from './components/Pagination'
import LoadingOverlay from './components/LoadingOverlay'
import { useAuth } from './context/AuthContext'
import { authFetch, downloadAuthFile } from './utils/auth'
import {
  matchCliente,
  appendClienteNotFoundMessage,
  replaceOggiPlaceholder,
  extractClienteHint,
  isDocumentDetailAction,
  tabForDocumentDetailAction
} from './utils/llm'

const LIST_PAGE_SIZE = 50

const ANALISI_QUESTION_SHORTCUTS = [
  { num: 10, target_tab: 'clienti', target_section: 'fatturato-mensile', question: 'Qual è l\'andamento del fatturato negli ultimi 24 mesi?' },
  { num: 11, target_tab: 'clienti', target_section: 'concentrazione', question: 'Quanto incidono i 5 clienti principali sul fatturato totale?' },
  { num: 12, target_tab: 'clienti', target_section: 'top-clienti', question: 'Chi sono i 10 clienti con il fatturato più alto nell\'ultimo anno?' },
  { num: 13, target_tab: 'clienti', target_section: 'erosione', question: 'Quali clienti mostrano segnali di erosione o calo degli ordini?' },
  { num: 14, target_tab: 'clienti', target_section: 'dormienti', question: 'Quali clienti non ordinano da oltre 90 giorni?' },
  { num: 15, target_tab: 'clienti', target_section: 'nuovi', question: 'Quali clienti abbiamo acquisito negli ultimi 12 mesi?' },
  { num: 16, target_tab: 'produzione', target_section: 'lead-time-trend', question: 'Come è evoluto il lead time medio mensile negli ultimi mesi?' },
  { num: 17, target_tab: 'produzione', target_section: 'lead-time-top', question: 'Quali ordini hanno avuto i tempi di consegna più lunghi nell\'ultimo trimestre?' },
  { num: 18, target_tab: 'produzione', target_section: 'volumi-mensili', question: 'Quali sono stati i picchi di volume mensile in kg e capi consegnati?' },
  { num: 19, target_tab: 'produzione', target_section: 'volumi-settimanali', question: 'Come si confrontano i volumi settimanali con l\'anno scorso?' },
]

function App() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState(() => {
    const pathname = window.location.pathname
    if (pathname === '/analisi') return 'analisi'
    return 'bolle'
  })
  const [analisiSubTab, setAnalisiSubTab] = useState(null)
  const [analisiScrollTarget, setAnalisiScrollTarget] = useState(null)
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [exportingPDF, setExportingPDF] = useState(false)
  const [selectedInvoice, setSelectedInvoice] = useState(null)
  const [invoiceDetail, setInvoiceDetail] = useState(null)
  const [selectedBollaId, setSelectedBollaId] = useState(null)
  const [bollaDetail, setBollaDetail] = useState(null)
  const [selectedOffertaId, setSelectedOffertaId] = useState(null)
  const [offertaDetail, setOffertaDetail] = useState(null)
  const [currentFilters, setCurrentFilters] = useState({
    data_inizio: '',
    data_fine: '',
    codice_cliente: '',
    stagione: ''
  })
  const [initialQuery] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    const q = params.get('query') || ''
    if (q) {
      const newUrl = window.location.pathname + window.location.hash
      window.history.replaceState({}, document.title, newUrl)
    }
    return q
  })
  const [discrepancyCustomer, setDiscrepancyCustomer] = useState('')
  const [pendingExport, setPendingExport] = useState(false)
  const [pendingInvoice, setPendingInvoice] = useState(null)
  const [pendingBollaId, setPendingBollaId] = useState(null)
  const [pendingOffertaId, setPendingOffertaId] = useState(null)
  const [listPage, setListPage] = useState(1)
  const [listTotal, setListTotal] = useState(0)
  const [listPages, setListPages] = useState(1)
  const [listTotals, setListTotals] = useState(null)
  const clientiCache = useRef(null)
  const skipNextTabFetch = useRef(false)

  const clearDocumentDetails = () => {
    setSelectedInvoice(null)
    setInvoiceDetail(null)
    setSelectedBollaId(null)
    setBollaDetail(null)
    setSelectedOffertaId(null)
    setOffertaDetail(null)
  }

  // Fetch standard listings based on tab and filters
  const fetchData = (tab, filters = currentFilters, page = 1) => {
    if (tab === 'discrepanze') return
    setLoading(true)
    clearDocumentDetails()

    const params = new URLSearchParams()
    if (filters.data_inizio) params.append('data_inizio', filters.data_inizio)
    if (filters.data_fine) params.append('data_fine', filters.data_fine)
    if (filters.codice_cliente) params.append('codice_cliente', filters.codice_cliente)
    if (filters.stagione) params.append('stagione', filters.stagione)

    params.append('page', page)
    params.append('limit', LIST_PAGE_SIZE)

    authFetch(`/api/${tab}?${params.toString()}`)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.data) {
          setData(resData.data)
          setListTotal(resData.total ?? resData.data.length)
          setListPage(resData.page ?? page)
          setListPages(resData.pages ?? 1)
          setListTotals(resData.totals ?? null)
        }
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching list data:', err)
        setLoading(false)
      })
  }

  const handleTabChange = (tab) => {
    clearDocumentDetails()

    if (tab === 'analisi') {
      window.history.replaceState({}, document.title, '/analisi')
      setActiveTab(tab)
      setAnalisiSubTab(null)
      setAnalisiScrollTarget(null)
      return
    }

    window.history.replaceState({}, document.title, '/')

    if (tab === 'discrepanze') {
      setData([])
      setListPage(1)
      setListTotal(0)
      setListPages(1)
      setListTotals(null)
      setLoading(false)
      setActiveTab(tab)
      return
    }

    const tabFilters = currentFilters

    setData([])
    setListPage(1)
    if (tab !== activeTab) {
      setCurrentFilters(tabFilters)
    }
    skipNextTabFetch.current = true
    fetchData(tab, tabFilters, 1)
    setActiveTab(tab)
  }

  // Fetch list data when activeTab changes
  useEffect(() => {
    if (activeTab !== 'discrepanze' && activeTab !== 'analisi') {
      if (skipNextTabFetch.current) {
        skipNextTabFetch.current = false
        return
      }
      fetchData(activeTab)
    }
  }, [activeTab])

  useEffect(() => {
    if (pendingInvoice && !loading) {
      setSelectedInvoice(pendingInvoice)
      setPendingInvoice(null)
    }
  }, [pendingInvoice, loading])

  useEffect(() => {
    if (pendingBollaId && !loading) {
      setSelectedBollaId(pendingBollaId)
      setPendingBollaId(null)
    }
  }, [pendingBollaId, loading])

  useEffect(() => {
    if (pendingOffertaId && !loading) {
      setSelectedOffertaId(pendingOffertaId)
      setPendingOffertaId(null)
    }
  }, [pendingOffertaId, loading])

  // Fetch invoice details when selectedInvoice changes
  useEffect(() => {
    if (!selectedInvoice) {
      setInvoiceDetail(null)
      return
    }
    setLoading(true)
    const params = new URLSearchParams()
    if (selectedInvoice.codice_cliente) {
      params.append('codice_cliente', selectedInvoice.codice_cliente)
    }
    const query = params.toString()
    authFetch(`/api/fatture/${selectedInvoice.numero_disposizione}${query ? `?${query}` : ''}`)
      .then(async (res) => {
        const resData = await res.json()
        if (!res.ok || !resData.header) {
          console.error('Error fetching invoice details:', resData.error || res.status)
          setSelectedInvoice(null)
          setInvoiceDetail(null)
          return
        }
        setInvoiceDetail(resData)
      })
      .catch((err) => {
        console.error('Error fetching invoice details:', err)
        setSelectedInvoice(null)
        setInvoiceDetail(null)
      })
      .finally(() => setLoading(false))
  }, [selectedInvoice])

  useEffect(() => {
    if (!selectedBollaId) {
      setBollaDetail(null)
      return
    }
    setLoading(true)
    authFetch(`/api/bolle/${selectedBollaId}`)
      .then(async (res) => {
        const resData = await res.json()
        if (!res.ok || !resData.header) {
          console.error('Error fetching bolla details:', resData.error || res.status)
          setSelectedBollaId(null)
          setBollaDetail(null)
          return
        }
        setBollaDetail(resData)
      })
      .catch((err) => {
        console.error('Error fetching bolla details:', err)
        setSelectedBollaId(null)
        setBollaDetail(null)
      })
      .finally(() => setLoading(false))
  }, [selectedBollaId])

  useEffect(() => {
    if (!selectedOffertaId) {
      setOffertaDetail(null)
      return
    }
    setLoading(true)
    authFetch(`/api/offerte/${selectedOffertaId}`)
      .then(async (res) => {
        const resData = await res.json()
        if (!res.ok || !resData.header) {
          console.error('Error fetching offerta details:', resData.error || res.status)
          setSelectedOffertaId(null)
          setOffertaDetail(null)
          return
        }
        setOffertaDetail(resData)
      })
      .catch((err) => {
        console.error('Error fetching offerta details:', err)
        setSelectedOffertaId(null)
        setOffertaDetail(null)
      })
      .finally(() => setLoading(false))
  }, [selectedOffertaId])

  const handleSearch = (filters) => {
    setCurrentFilters(filters)
    setListPage(1)
    fetchData(activeTab, filters, 1)
  }

  const handleListPageChange = (page) => {
    setListPage(page)
    fetchData(activeTab, currentFilters, page)
  }

  const buildExportParams = (tab, filters) => {
    const params = new URLSearchParams()
    if (filters.data_inizio) params.append('data_inizio', filters.data_inizio)
    if (filters.data_fine) params.append('data_fine', filters.data_fine)
    if (filters.codice_cliente) params.append('codice_cliente', filters.codice_cliente)
    if (filters.stagione) params.append('stagione', filters.stagione)
    return params
  }

  const exportPDF = async () => {
    if (data.length === 0) return
    setExportingPDF(true)
    try {
      const params = buildExportParams(activeTab, currentFilters)
      await downloadAuthFile(`/api/${activeTab}/export/pdf?${params}`, `${activeTab}_esportazione.pdf`)
    } catch (err) {
      console.error('Error exporting PDF:', err)
    } finally {
      setExportingPDF(false)
    }
  }

  const exportCSV = () => {
    if (data.length === 0) return

    let csvContent = 'data:text/csv;charset=utf-8,'
    
    if (activeTab === 'bolle') {
      csvContent += 'N. bolla,Data,Cliente,Codice Cliente,Righe collegate\n'
      data.forEach((row) => {
        csvContent += `"${row.numero_bolla}","${row.data}","${row.cliente}","${row.codice_cliente}","${row.righe_collegate}"\n`
      })
    } else if (activeTab === 'fatture') {
      csvContent += 'N. disp.,Periodo riferimento,Cliente,Codice Cliente,Importo documento\n'
      data.forEach((row) => {
        csvContent += `"${row.numero_disposizione}","${row.data}","${row.cliente}","${row.codice_cliente}",${row.importo_documento}\n`
      })
    } else if (activeTab === 'offerte') {
      csvContent += 'N. Ordine/Cartellino,Data,Cliente,Codice Cliente,Stagione,Importo\n'
      data.forEach((row) => {
        csvContent += `"${row.numero_offerta}","${row.data}","${row.cliente}","${row.codice_cliente}","${row.stagione}",${row.importo}\n`
      })
    }

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `${activeTab}_esportazione.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  useEffect(() => {
    if (pendingExport && !loading && data.length > 0) {
      exportCSV()
      setPendingExport(false)
    }
  }, [pendingExport, loading, data])

  const getClienti = async () => {
    if (clientiCache.current) return clientiCache.current
    const res = await authFetch('/api/clienti')
    const resData = await res.json()
    clientiCache.current = resData.data || []
    return clientiCache.current
  }

  const applyPendingDocumentDetail = (azione, filters = {}) => {
    const numero = String(azione.numero_documento || '').trim()
    if (!numero) return

    if (azione.tipo === 'dettaglio_fattura') {
      setPendingInvoice({
        numero_disposizione: numero,
        codice_cliente: filters.codice_cliente || ''
      })
    } else if (azione.tipo === 'dettaglio_bolla') {
      setPendingBollaId(numero)
    } else if (azione.tipo === 'dettaglio_offerta') {
      setPendingOffertaId(numero)
    }
  }

  const openDocumentDetailFromLlm = (tab, filters, azione, messaggio) => {
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(filters)
    setData([])
    setListPage(1)
    clearDocumentDetails()
    setLoading(false)
    applyPendingDocumentDetail(azione, filters)
    return { messaggio: messaggio || 'Richiesta elaborata.' }
  }

  const applyLlmResponse = async (llmJson, userMessage = '') => {
    const { area, messaggio } = llmJson || {}
    const filtri = llmJson?.filtri || {}
    const azione = llmJson?.azione || {}
    const tab = area || 'bolle'

    const newFilters = {
      data_inizio: replaceOggiPlaceholder(filtri.data_inizio || ''),
      data_fine: replaceOggiPlaceholder(filtri.data_fine || ''),
      codice_cliente: '',
      stagione: filtri.stagione || ''
    }

    if (isDocumentDetailAction(azione)) {
      const llmCliente = filtri.cliente?.trim() || ''
      const userHint = extractClienteHint(userMessage)
      const clienti = await getClienti()

      const llmMatch = llmCliente ? matchCliente(llmCliente, clienti) : null
      const userMatch = userHint ? matchCliente(userHint, clienti) : null

      let matchResult = { codice: '', matched: true, ambiguous: false, candidates: [] }
      if (userMatch?.ambiguous) {
        matchResult = userMatch
      } else if (llmMatch) {
        matchResult = llmMatch
      } else if (userMatch) {
        matchResult = userMatch
      }

      newFilters.codice_cliente = matchResult.ambiguous ? '' : matchResult.codice

      const clienteQuery = userHint || llmCliente
      const finalMessaggio = appendClienteNotFoundMessage(
        messaggio,
        clienteQuery,
        matchResult
      )

      const detailTab = tabForDocumentDetailAction(azione, tab)
      return openDocumentDetailFromLlm(detailTab, newFilters, azione, finalMessaggio)
    }

    if (tab === 'analisi' || azione.tipo === 'apri_analisi') {
      setData([])
      setLoading(false)
      clearDocumentDetails()
      skipNextTabFetch.current = true
      const targetTab = azione.target_tab || 'clienti'
      const targetSection = azione.target_section || ''

      setActiveTab('analisi')
      setAnalisiSubTab(targetTab)
      setAnalisiScrollTarget(targetSection)

      const hash = targetSection ? `#${targetSection}` : ''
      window.history.replaceState({}, document.title, `/analisi?tab=${targetTab}${hash}`)
      return { messaggio: messaggio || 'Navigazione alla pagina Analisi...' }
    }

    const llmCliente = filtri.cliente?.trim() || ''
    const userHint = extractClienteHint(userMessage)
    const clienti = await getClienti()

    const llmMatch = llmCliente ? matchCliente(llmCliente, clienti) : null
    const userMatch = userHint ? matchCliente(userHint, clienti) : null

    let matchResult = { codice: '', matched: true, ambiguous: false, candidates: [] }
    if (userMatch?.ambiguous) {
      matchResult = userMatch
    } else if (llmMatch) {
      matchResult = llmMatch
    } else if (userMatch) {
      matchResult = userMatch
    }

    newFilters.codice_cliente = matchResult.codice

    const clienteQuery = userHint || llmCliente
    const finalMessaggio = appendClienteNotFoundMessage(
      messaggio,
      clienteQuery,
      matchResult
    )

    const disambiguationContext = { tab, filtri: newFilters, azione }

    if (matchResult.ambiguous) {
      setData([])
      setLoading(false)
      clearDocumentDetails()
      skipNextTabFetch.current = true
      setActiveTab(tab)
      setCurrentFilters(newFilters)

      return {
        messaggio: finalMessaggio || 'Richiesta elaborata.',
        disambiguation: {
          prompt: 'Molteplici clienti trovati, quale desideri?',
          candidates: matchResult.candidates,
          context: disambiguationContext
        }
      }
    }

    if (tab === 'discrepanze') {
      setDiscrepancyCustomer(matchResult.codice || '')
      setData([])
      setLoading(false)
      clearDocumentDetails()
      setActiveTab('discrepanze')
      return { messaggio: finalMessaggio || 'Apertura pannello auditing discrepanze.' }
    }

    setData([])
    setLoading(true)
    setListPage(1)
    clearDocumentDetails()
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(newFilters)
    fetchData(tab, newFilters)

    if (azione.tipo === 'esporta_csv') {
      setPendingExport(true)
    }

    return { messaggio: finalMessaggio || 'Richiesta elaborata.' }
  }

  const applyClienteSelection = (codice, context) => {
    const { tab, filtri, azione = {} } = context
    const newFilters = { ...filtri, codice_cliente: codice }

    if (tab === 'discrepanze') {
      setDiscrepancyCustomer(codice)
      setCurrentFilters(newFilters)
      setActiveTab('discrepanze')
      return
    }

    setData([])
    setLoading(true)
    setListPage(1)
    clearDocumentDetails()
    skipNextTabFetch.current = true
    setActiveTab(tab)
    setCurrentFilters(newFilters)
    fetchData(tab, newFilters)

    if (isDocumentDetailAction(azione)) {
      applyPendingDocumentDetail(azione, newFilters)
    } else if (azione.tipo === 'esporta_csv') {
      setPendingExport(true)
    }
  }

  // Pre-load filter inputs for interactive Q&A shortcuts
  const applyQuestionShortcut = (tab, qFilters) => {
    setData([])
    setListPage(1)
    clearDocumentDetails()
    skipNextTabFetch.current = true

    if (tab === 'discrepanze') {
      setLoading(false)
      setDiscrepancyCustomer(qFilters.codice_cliente || '')
      setCurrentFilters((prev) => ({ ...prev, ...qFilters }))
      setActiveTab('discrepanze')
      return
    }

    setLoading(true)
    setActiveTab(tab)
    setCurrentFilters((prev) => {
      const merged = { ...prev, ...qFilters }
      fetchData(tab, merged)
      return merged
    })
  }

  const applyAnalisiShortcut = (targetTab, targetSection) => {
    setData([])
    setLoading(false)
    clearDocumentDetails()
    skipNextTabFetch.current = true
    setActiveTab('analisi')
    setAnalisiSubTab(targetTab)
    setAnalisiScrollTarget(targetSection)
    window.history.replaceState({}, document.title, `/analisi?tab=${targetTab}#${targetSection}`)
  }

  const handleViewInvoiceDetail = (id, codiceCliente) => {
    setSelectedBollaId(null)
    setBollaDetail(null)
    setSelectedOffertaId(null)
    setOffertaDetail(null)
    setSelectedInvoice({ numero_disposizione: id, codice_cliente: codiceCliente })
  }

  const handleViewBollaDetail = (id) => {
    setSelectedInvoice(null)
    setInvoiceDetail(null)
    setSelectedOffertaId(null)
    setOffertaDetail(null)
    setSelectedBollaId(id)
  }

  const handleViewOffertaDetail = (id) => {
    setSelectedInvoice(null)
    setInvoiceDetail(null)
    setSelectedBollaId(null)
    setBollaDetail(null)
    setSelectedOffertaId(id)
  }

  const formatEuro = (num) => {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR'
    }).format(num)
  }

  return (
    <div className="app-container">
      {exportingPDF && <LoadingOverlay />}
      <header className="app-header">
        <div className="app-title-group">
          <img src="/logo.webp" alt="Intex" className="app-logo" />
        </div>
        <div className="app-header__actions">
          <UserMenu />
          {user?.role === 'admin' && <AdminNav />}
        </div>
      </header>

      <nav className="nav-primary">
        <button
          className={`nav-tab ${activeTab === 'bolle' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('bolle')}
        >
          📦 Bolle / DDT
        </button>
        <button
          className={`nav-tab ${activeTab === 'fatture' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('fatture')}
        >
          🧾 Fatture
        </button>
        <button
          className={`nav-tab ${activeTab === 'offerte' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('offerte')}
        >
          📋 Ordini / Cartellino
        </button>
        <button
          className={`nav-tab ${activeTab === 'discrepanze' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('discrepanze')}
        >
          ⚖️ Auditing Confronto
        </button>
        <button
          className={`nav-tab ${activeTab === 'analisi' ? 'is-active' : ''}`}
          onClick={() => handleTabChange('analisi')}
        >
          📊 Analisi
        </button>
      </nav>

      <div className="dashboard-grid">
        <div className="dashboard-chat">
          <ChatPanel onResponse={applyLlmResponse} onClienteSelect={applyClienteSelection} initialQuery={initialQuery} />
        </div>

        <div className="dashboard-main">
          {activeTab === 'analisi' ? (
            <AnalisiPage 
              subTabOverride={analisiSubTab} 
              scrollTargetOverride={analisiScrollTarget} 
            />
          ) : activeTab === 'discrepanze' ? (
            <DiscrepancyPanel
              selectedCustomer={discrepancyCustomer}
              onCustomerChange={setDiscrepancyCustomer}
            />
          ) : (
            <>
              <div className="panel">
                <div className="panel__head">Filtri di Ricerca</div>
                <div className="panel__body">
                  <Filters
                    activeTab={activeTab}
                    onSearch={handleSearch}
                    onExport={exportCSV}
                    onExportPDF={exportPDF}
                    filterValues={currentFilters}
                  />
                </div>
              </div>

              {/* Detailed Invoice Rows Panel */}
              {selectedInvoice && invoiceDetail?.header && (
                <div className="panel">
                  <div className="panel__head">
                    <span>Dettaglio Documento — Riga Disposition N. {invoiceDetail.header.numero_disposizione}</span>
                    <button className="btn" onClick={() => setSelectedInvoice(null)}>Chiudi Dettaglio</button>
                  </div>
                  <div className="panel__body">
                    <div className="detail-header-info">
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Cliente</span>
                        <span className="detail-info-item__value">{invoiceDetail.header.cliente} ({invoiceDetail.header.codice_cliente})</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Data Fattura</span>
                        <span className="detail-info-item__value">{invoiceDetail.header.data}</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Totale Documento</span>
                        <span className="detail-info-item__value">{formatEuro(invoiceDetail.header.importo_totale)}</span>
                      </div>
                    </div>

                    <div className="table-wrap">
                      <table className="data">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Data bolla</th>
                            <th>N. bolla</th>
                            <th>Articolo</th>
                            <th>Colore</th>
                            <th>Kg fatturati</th>
                            <th>Capi fatturati</th>
                            <th>Importo riga</th>
                          </tr>
                        </thead>
                        <tbody>
                          {invoiceDetail.lines.map((line) => (
                            <tr key={line.riga_disposizione}>
                              <td>{line.riga_disposizione}</td>
                              <td>{line.data_bolla}</td>
                              <td>{line.numero_bolla || '—'}</td>
                              <td><strong>{line.articolo}</strong></td>
                              <td>{line.colore}</td>
                              <td>{line.kg_fatturati}</td>
                              <td>{line.capi_fatturati}</td>
                              <td>{formatEuro(line.importo_riga)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {selectedBollaId && bollaDetail?.header && (
                <div className="panel">
                  <div className="panel__head">
                    <span>Dettaglio Bolla — N. {bollaDetail.header.numero_bolla}</span>
                    <button className="btn" onClick={() => setSelectedBollaId(null)}>Chiudi Dettaglio</button>
                  </div>
                  <div className="panel__body">
                    <div className="detail-header-info">
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Cliente</span>
                        <span className="detail-info-item__value">{bollaDetail.header.cliente} ({bollaDetail.header.codice_cliente})</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Data Bolla</span>
                        <span className="detail-info-item__value">{bollaDetail.header.data}</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Totale Documento</span>
                        <span className="detail-info-item__value">{formatEuro(bollaDetail.header.importo_totale)}</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Righe</span>
                        <span className="detail-info-item__value">{bollaDetail.lines.length}</span>
                      </div>
                    </div>

                    <div className="table-wrap">
                      <table className="data">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>N. disp.</th>
                            <th>Riga disp.</th>
                            <th>N. offerta</th>
                            <th>Articolo</th>
                            <th>Colore</th>
                            <th>Kg consegnati</th>
                            <th>Capi consegnati</th>
                            <th>Importo riga</th>
                          </tr>
                        </thead>
                        <tbody>
                          {bollaDetail.lines.map((line) => (
                            <tr key={line.riga_num}>
                              <td>{line.riga_num}</td>
                              <td>{line.numero_disposizione}</td>
                              <td>{line.riga_disposizione}</td>
                              <td>{line.numero_offerta}</td>
                              <td><strong>{line.articolo}</strong></td>
                              <td>{line.colore}</td>
                              <td>{line.kg_consegnati}</td>
                              <td>{line.capi_consegnati}</td>
                              <td>{formatEuro(line.importo_riga)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {selectedOffertaId && offertaDetail?.header && (
                <div className="panel">
                  <div className="panel__head">
                    <span>Dettaglio Ordine/Cartellino — N. {offertaDetail.header.numero_offerta}</span>
                    <button className="btn" onClick={() => setSelectedOffertaId(null)}>Chiudi Dettaglio</button>
                  </div>
                  <div className="panel__body">
                    <div className="detail-header-info">
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Cliente</span>
                        <span className="detail-info-item__value">{offertaDetail.header.cliente} ({offertaDetail.header.codice_cliente})</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Data Ordine</span>
                        <span className="detail-info-item__value">{offertaDetail.header.data}</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Stagione</span>
                        <span className="detail-info-item__value">{offertaDetail.header.stagione}</span>
                      </div>
                      <div className="detail-info-item">
                        <span className="detail-info-item__label">Totale Documento</span>
                        <span className="detail-info-item__value">{formatEuro(offertaDetail.header.importo_totale)}</span>
                      </div>
                    </div>

                    <div className="table-wrap">
                      <table className="data">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Articolo</th>
                            <th>Colore</th>
                            <th>Quantità</th>
                            <th>Prezzo unitario</th>
                            <th>Importo riga</th>
                          </tr>
                        </thead>
                        <tbody>
                          {offertaDetail.lines.map((line) => (
                            <tr key={line.riga_num}>
                              <td>{line.riga_num}</td>
                              <td><strong>{line.articolo}</strong></td>
                              <td>{line.colore}</td>
                              <td>{line.quantita}</td>
                              <td>{formatEuro(line.prezzo_unitario)}</td>
                              <td>{formatEuro(line.importo_riga)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              <div className="panel">
                <div className="panel__head">
                  <span>Risultati ({listTotal} record)</span>
                </div>
                {loading ? (
                  <div className="loading-indicator">
                    <div className="spinner"></div>
                    <span>Recupero dati in corso...</span>
                  </div>
                ) : (
                  <>
                    <DocumentTable
                      activeTab={activeTab}
                      data={data}
                      totals={listTotals}
                      onViewDetail={handleViewInvoiceDetail}
                      onViewBollaDetail={handleViewBollaDetail}
                      onViewOffertaDetail={handleViewOffertaDetail}
                    />
                    <Pagination
                      page={listPage}
                      pages={listPages}
                      total={listTotal}
                      onPageChange={handleListPageChange}
                      label="Record"
                    />
                  </>
                )}
              </div>
            </>
          )}
        </div>

        {/* Sidebar Questions Suggestions */}
        <div className="dashboard-sidebar">
          <div className="sidebar-panel">
            <div className="chat-suggestions">
              <h3 className="chat-suggestions__title">💬 Scorciatoie Domande</h3>
              <div className="chat-suggestions__list">
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('fatture', {
                      codice_cliente: '2618',
                      data_inizio: '2026-01-01',
                      data_fine: '2026-03-31'
                    })
                  }
                >
                  <span className="chat-suggestion-num">1</span>
                  “Mostrami tutte le fatture del cliente PRIMA SRL emesse tra gennaio e marzo.”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('fatture', {
                      codice_cliente: '2618',
                      data_inizio: '',
                      data_fine: ''
                    })
                  }
                >
                  <span className="chat-suggestion-num">2</span>
                  “Mostrami tutte le fatture di PRIMA SRL.”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('bolle', {
                      codice_cliente: '2618',
                      data_inizio: '2026-03-01',
                      data_fine: '2026-03-31'
                    })
                  }
                >
                  <span className="chat-suggestion-num">5</span>
                  “Quali bolle/DDT sono state emesse per PRIMA SRL nel mese di marzo?”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('offerte', {
                      codice_cliente: '1071',
                      stagione: 'PE2026',
                      data_inizio: '',
                      data_fine: ''
                    })
                  }
                >
                  <span className="chat-suggestion-num">7</span>
                  “Cerca i cartellini di Zanuso per la stagione PE2026.”
                </button>
                <button
                  className="chat-suggestion-btn"
                  onClick={() =>
                    applyQuestionShortcut('discrepanze', {
                      codice_cliente: '2618'
                    })
                  }
                >
                  <span className="chat-suggestion-num">9</span>
                  “Confrontami ordine, bolla e fattura per verificare differenze di Prima Srl.”
                </button>
                {ANALISI_QUESTION_SHORTCUTS.map((shortcut) => (
                  <button
                    key={shortcut.target_section}
                    className="chat-suggestion-btn"
                    onClick={() => applyAnalisiShortcut(shortcut.target_tab, shortcut.target_section)}
                  >
                    <span className="chat-suggestion-num">{shortcut.num}</span>
                    “{shortcut.question}”
                  </button>
                ))}
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
