# Analisi dell'Impatto sul Prompt e sul Frontend — Sezione Analisi

Questo documento descrive l'impatto tecnico, le modifiche suggerite e i potenziali rischi derivanti dall'integrazione della nuova pagina **Analisi** (`/analisi`) con l'assistente a linguaggio naturale (Chat Assistant) dell'applicazione **Intex**.

---

## 1. Analisi dei Requisiti e Mappatura Sezioni

La pagina Analisi (`AnalisiPage.jsx`) è strutturata in 4 schede principali (`TABS`), ciascuna delle quali contiene diverse sezioni e tabelle (`TOC`). Per consentire all'assistente di indirizzare correttamente l'utente, dobbiamo mappare ciascuna richiesta utente a un'area tematica, una scheda target (`target_tab`) e una sezione specifica (`target_section`):

| Tab Principale (`target_tab`) | ID Sezione (`target_section`) | Descrizione UI / Funzionalità | Parole Chiave Tipiche dell'Utente |
| :--- | :--- | :--- | :--- |
| **`clienti`** *(Performance)* | `fatturato-mensile` | Grafico andamento ultimi 24 mesi | *fatturato mensile, vendite mensili, trend fatturato, andamento vendite* |
| | `concentrazione` | Quota fatturato dei top 5 clienti | *concentrazione clienti, quota top 5, impatto grandi clienti, quota fatturato* |
| | `top-clienti` | Classifica dei primi 10 clienti per fatturato | *migliori clienti, classifica clienti, top 10, clienti principali* |
| | `erosione` | Clienti in calo o con allungamento tempi ordini | *clienti a rischio, erosione fatturato, calo ordini, alert clienti* |
| | `dormienti` | Clienti inattivi da oltre 90 giorni | *clienti dormienti, clienti inattivi, non acquistano da 90 giorni* |
| | `nuovi` | Clienti acquisiti negli ultimi 12 mesi | *clienti nuovi, nuovi inserimenti, acquisiti nell'ultimo anno* |
| **`produzione`** | `lead-time-trend` | Media mensile dei giorni tra ordine e consegna | *lead time medio, tempi medi consegna, giorni ordine bolla, trend tempi* |
| | `lead-time-top` | Ordini con i ritardi maggiori nel trimestre | *ritardi maggiori, consegne lente, ordini bloccati, lead time lunghi* |
| | `volumi-mensili` | Picchi mensili di kg e capi consegnati | *volumi mensili, kg consegnati, capi consegnati, picchi produzione* |
| | `volumi-settimanali` | Grafico di confronto settimanale Anno su Anno | *confronto anno scorso, volumi YoY, volumi settimanali* |
| **`controllo`** *(Perdite)* | `totale-sospeso` | Valore totale DDT non fatturati da oltre 60 giorni | *totale sospeso, valore non fatturato, ddt sospesi da fatturare* |
| | `ddt-senza-fattura` | Elenco delle bolle non fatturate con ritardo | *ddt senza fattura, bolle inevase, bolle non fatturate, ritardo fatturazione* |
| | `consegne-non-fatturate`| Stima del sospeso da fatturare raggruppata per cliente | *sospeso cliente, stima da fatturare, consegne non fatturate per cliente* |
| | `fatture-senza-ddt` | Fatture emesse prive di bolla di consegna nel sistema | *fatture senza ddt, disposizioni senza bolla, incoerenze fatture* |
| **`opportunita`** | `stress-test` | Simulatore interattivo di calo ordinato clienti | *stress test, simulatore fatturato, calo ordini top clienti* |
| | `clienti-ideali` | Clienti con alto fatturato e lead time veloci | *clienti ideali, clienti migliori, lead time corti* |
| | `insight-trimestre` | Anomalie di severità rilevate nel trimestre | *insight trimestre, anomalie severe, alert trimestre* |

---

## 2. Impatto sul Prompt Principale (`backend/prompts.txt`)

Per supportare l'analisi e indirizzare l'utente senza interrompere le funzionalità esistenti (ricerca di bolle, fatture, ordini e discrepanze), il file `prompts.txt` deve essere integrato con:
1. Una nuova area denominata `"analisi"`.
2. L'estensione del payload JSON per specificare la destinazione (`target_tab` e `target_section`).
3. Regole chiare per distinguere una ricerca puntuale (es. "mostrami le fatture del cliente X") da una richiesta analitica (es. "mostrami l'andamento del fatturato").

### Modifica dello Schema JSON di Output
Il formato di risposta JSON richiesto all'LLM deve rimanere retrocompatibile. I campi esistenti verranno mantenuti identici, introducendo due nuovi campi facoltativi all'interno dell'oggetto `azione`:
*   `target_tab`: Stringa che indica una delle 4 schede principali (`clienti | produzione | controllo | opportunita`).
*   `target_section`: Stringa corrispondente all'ID HTML della sezione nella pagina.

Ecco lo schema modificato:
```json
{
  "area": "bolle | fatture | offerte | discrepanze | analisi",
  "filtri": {
    "data_inizio": "YYYY-MM-DD oppure stringa vuota",
    "data_fine": "YYYY-MM-DD oppure stringa vuota",
    "cliente": "ragione sociale del cliente oppure stringa vuota",
    "stagione": "codice stagione oppure stringa vuota"
  },
  "azione": {
    "tipo": "nessuna | dettaglio_fattura | dettaglio_bolla | dettaglio_offerta | esporta_csv | apri_discrepanze | apri_analisi",
    "numero_documento": "numero documento quando applicabile",
    "target_tab": "clienti | produzione | controllo | opportunita (obbligatorio se area è 'analisi', altrimenti stringa vuota)",
    "target_section": "ID della sottosezione (obbligatorio se area è 'analisi', altrimenti stringa vuota)"
  },
  "messaggio": "Breve spiegazione in italiano..."
}
```

### Regole per Evitare Regressioni
Per garantire che il prompt mantenga intatto il comportamento standard:
*   **Isolamento delle keyword**: Le keyword relative all'auditing e ai documenti singoli (`bolle`, `fatture`, `offerte`, `discrepanze`) non devono sovrapporsi a quelle sintetiche/aggregative dell'area `analisi`.
    *   *Esempio*: "DDT senza fattura" appartiene all'area `analisi` (sotto-sezione `ddt-senza-fattura`), mentre "mostrami la bolla n. 4761" o "bolle del cliente X" appartengono all'area `bolle`.
*   **Filtri di supporto**: Se l'utente menziona un cliente o una data in una richiesta analitica (es. "mostrami le consegne non fatturate per il cliente TAM"), il prompt deve compilare anche i campi `filtri.cliente` e/o `filtri.data_inizio` per permettere al frontend di applicare il contesto del cliente.
*   **Default non distruttivo**: Se la query non rientra chiaramente in una delle sezioni della pagina Analisi, l'assistente deve ricadere sul comportamento standard (es. ricerca tabellare standard di fatture/bolle/offerte).

### Esempi Aggiunti al Prompt (`prompts.txt`)

Nel file `prompts.txt`, nella sezione degli esempi, vanno aggiunti casi d'uso dedicati all'analisi:

#### Esempio Analisi 1 — Andamento Fatturato
**Utente:** "Voglio vedere l'andamento del fatturato mensile degli ultimi due anni"
```json
{
  "area": "analisi",
  "filtri": { "data_inizio": "", "data_fine": "", "cliente": "", "stagione": "" },
  "azione": {
    "tipo": "apri_analisi",
    "numero_documento": "",
    "target_tab": "clienti",
    "target_section": "fatturato-mensile"
  },
  "messaggio": "Apro il grafico dell'andamento mensile del fatturato per gli ultimi 24 mesi."
}
```

#### Esempio Analisi 2 — Clienti a Rischio
**Utente:** "Ci sono clienti a rischio o in erosione?"
```json
{
  "area": "analisi",
  "filtri": { "data_inizio": "", "data_fine": "", "cliente": "", "stagione": "" },
  "azione": {
    "tipo": "apri_analisi",
    "numero_documento": "",
    "target_tab": "clienti",
    "target_section": "erosione"
  },
  "messaggio": "Navigo alla sezione dei clienti a rischio per valutare cali di fatturato o ritardi negli ordini."
}
```

#### Esempio Analisi 3 — Lead Time Produzione
**Utente:** "Quali sono i tempi di consegna medi della produzione?"
```json
{
  "area": "analisi",
  "filtri": { "data_inizio": "", "data_fine": "", "cliente": "", "stagione": "" },
  "azione": {
    "tipo": "apri_analisi",
    "numero_documento": "",
    "target_tab": "produzione",
    "target_section": "lead-time-trend"
  },
  "messaggio": "Apro la sezione con l'andamento del lead time medio aziendale mensile."
}
```

#### Esempio Analisi 4 — DDT Sospesi per Cliente
**Utente:** "Fammi vedere le consegne non fatturate per il cliente TAM"
```json
{
  "area": "analisi",
  "filtri": { "data_inizio": "", "data_fine": "", "cliente": "TAM", "stagione": "" },
  "azione": {
    "tipo": "apri_analisi",
    "numero_documento": "",
    "target_tab": "controllo",
    "target_section": "consegne-non-fatturate"
  },
  "messaggio": "Apro il controllo delle consegne non fatturate per cliente. Puoi cercare TAM direttamente nella tabella."
}
```

---

## 3. Valutazione sulle Dimensioni del Prompt e sulla Scelta Architetturale

La richiesta richiede di valutare se il prompt diventi troppo lungo e se convenga creare un routing a più livelli (con due chiamate LLM sequenziali).

### Analisi Quantitativa (Token)
*   **Prompt Attuale**: ~15.3 KB, equivalente a circa **4.400 token** (incluso il vocabolario di stagioni).
*   **Regole Analisi Aggiuntive**: L'aggiunta delle nuove regole e di ~6-8 esempi completi per l'area `analisi` comporta un aumento stimato di circa 150 linee di testo (~5 KB), equivalenti a circa **1.500 token**.
*   **Prompt Integrato Finale**: Circa **5.900 - 6.000 token**.

### Confronto Soluzioni: Prompt Unico vs Multiplo (Routing)

#### Soluzione A: Prompt Unico Integrato (Scelta Consigliata)
Un unico prompt principale che include sia la ricerca ordinaria sia le regole della pagina Analisi.
*   **Vantaggi**:
    *   **Latenza dimezzata**: Viene eseguita una sola chiamata API all'LLM (Gemini).
    *   **Minore complessità backend**: Nessun codice aggiuntivo per coordinare le chiamate o preservare la cronologia dei messaggi tra contesti diversi.
    *   **Efficacia del Context**: 6.000 token rappresentano meno dell'1% della context window di Gemini 3.5 Flash (1.000.000+ token).
    *   **Prompt Caching**: Il fornitore LLM memorizza nella cache il prompt statico, riducendo i tempi di elaborazione a millisecondi e azzerando quasi il costo di computazione per i token in ingresso.
    *   **Costi irrisori**: A circa $0.075 per milione di token di input, 6.000 token costano circa $0.00045 per richiesta.
*   **Svantaggi**:
    *   Richiede una scrittura accurata dei confini semantici nel prompt per evitare fraintendimenti tra verbi simili (es. "mostrami" un documento vs "mostrami" un andamento grafico).

#### Soluzione B: Router Semantico + Prompt Specialistici (Sconsigliata)
Una prima chiamata LLM determina l'intento dell'utente ("Ricerca Documenti" vs "Analisi Metriche"). La seconda chiamata esegue il parsing con il prompt specifico.
*   **Vantaggi**:
    *   Prompt specialistici più corti.
*   **Svantaggi**:
    *   **Latenza doppia**: Due chiamate sequenziali introducono un ritardo percepibile dall'utente (da ~800ms a ~1.8s).
    *   **Costo raddoppiato**: Si pagano i token di input per entrambe le chiamate.
    *   **Maggiore tasso di errore**: Se il router iniziale sbaglia classificazione, il secondo prompt produrrà una risposta totalmente errata (moltiplicazione degli errori).

**Raccomandazione**: Sulla base dei dati di latenza, costi e capacità dei modelli correnti, la **Soluzione A (Prompt Unico Integrato)** è nettamente preferibile.

---

## 4. Impatto sul Frontend e Integrazione

Attualmente, la chat è contenuta nel componente `ChatPanel.jsx` all'interno della pagina principale (`App.jsx`). La pagina di analisi (`AnalisiPage.jsx`) è una rotta separata del browser gestita tramite `window.location.pathname`.

Se l'assistente riceve una richiesta analitica, il frontend deve:
1.  Riconoscere che l'area restituita è `"analisi"`.
2.  Estrarre `target_tab` e `target_section` dalla risposta.
3.  Modificare la rotta e portare l'utente su `/analisi`, selezionando automaticamente la scheda corretta e scorrendo fino all'elemento visualizzato.

### Modifiche Necessarie in `App.jsx`
All'interno del metodo `applyLlmResponse` in `App.jsx`, occorre intercettare l'area `"analisi"` per impedire al client di effettuare una chiamata fallimentare all'endpoint `/api/analisi` (che non esiste come API di ricerca standard):

```javascript
// Esempio di implementazione logica in App.jsx (applyLlmResponse)
if (tab === 'analisi') {
  setData([])
  setLoading(false)
  clearDocumentDetails()
  skipNextTabFetch.current = true
  
  const targetTab = azione.target_tab || 'clienti'
  const targetSection = azione.target_section || ''
  
  // Costruisce l'URL di redirezione comprensivo di query parameter e hash
  const hash = targetSection ? `#${targetSection}` : ''
  const redirectUrl = `/analisi?tab=${targetTab}${hash}`
  
  // Naviga alla pagina di analisi
  window.location.href = redirectUrl
  
  return { messaggio: finalMessaggio || 'Navigazione verso la pagina Analisi...' }
}
```

### Modifiche Necessarie in `AnalisiPage.jsx`
Attualmente `AnalisiPage.jsx` inizializza lo stato con la scheda `'clienti'` e non legge i parametri dell'URL o l'ancora (`hash`) per posizionarsi. Per gestire la redirezione in modo fluido, occorre:
1.  **Leggere l'URL all'avvio** per impostare lo stato `activeTab`.
2.  **Scorrere alla sezione corretta** una volta che i dati asincroni sono stati caricati e il DOM è stabile.

```javascript
// 1. All'avvio del componente AnalisiPage, parse dei parametri URL
useEffect(() => {
  const params = new URLSearchParams(window.location.search)
  const urlTab = params.get('tab')
  const validTabs = ['clienti', 'produzione', 'controllo', 'opportunita']
  
  if (urlTab && validTabs.includes(urlTab)) {
    setActiveTab(urlTab)
  } else {
    // Se non c'è il parametro tab, tenta di dedurlo dall'ancora
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
}, [])

// 2. Scroll morbido (smooth scroll) alla sezione una volta che il caricamento è completato
useEffect(() => {
  const hash = window.location.hash
  if (hash && !loading) {
    // Un piccolo timeout garantisce che il DOM del tab attivo sia completamente disegnato
    const timer = setTimeout(() => {
      const element = document.querySelector(hash)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }, 200)
    return () => clearTimeout(timer)
  }
}, [activeTab, loading])
```

---

## 5. Dettaglio di Implementazione: Integrazione della Chat nella Pagina Analisi

Invece di affidarsi a un rinvio distruttivo via `window.location.href` (che costringe al ricaricamento totale per le query analitiche), la soluzione ottimale è integrare direttamente il `ChatPanel` all'interno della pagina `/analisi`. Questo garantisce continuità conversazionale e permette una navigazione intra-pagina fluida.

Di seguito viene spiegato passo-passo come implementare questa integrazione a livello di layout e di logica.

### A. Modifiche al Layout di `AnalisiPage.jsx`
Dobbiamo allineare il layout di `AnalisiPage.jsx` a quello di `App.jsx` importando `ChatPanel` e inserendolo nella griglia CSS a due colonne (`dashboard-grid`).

```jsx
// AnalisiPage.jsx - Importazione del componente
import ChatPanel from '../components/ChatPanel'

export default function AnalisiPage() {
  // ... stati esistenti ...

  return (
    <div className="app-container">
      {loading && <LoadingOverlay />}
      <header className="app-header">
        {/* ... intestazione esistente ... */}
      </header>

      {/* Griglia a due colonne identica alla Home Page per consistenza UI */}
      <div className="dashboard-grid">
        
        {/* Colonna di sinistra: Chat Assistente */}
        <div className="dashboard-chat">
          <ChatPanel 
            onResponse={applyLlmResponse} 
            onClienteSelect={applyClienteSelection} 
          />
        </div>

        {/* Colonna di destra: Contenuti ed Elenchi dell'Analisi */}
        <div className="dashboard-main">
          {meta?.last_success && (
            <p className="meta analisi-meta">
              Dati analitici aggiornati al {formatDate(meta.last_success)}
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

          {/* ... rendering dei tab esistenti (clienti, produzione, controllo, opportunita) ... */}
        </div>
      </div>
    </div>
  )
}
```

### B. Logica di Risposta della Chat (`applyLlmResponse` in `AnalisiPage.jsx`)
Nella pagina Analisi, la chat deve comportarsi in due modi diversi a seconda del tipo di richiesta dell'utente:
1.  **Se la richiesta è analitica (`area === 'analisi'`)**: cambia il tab attivo locale ed effettua uno scroll smooth alla sezione desiderata in modo puramente client-side, senza ricaricare la pagina.
2.  **Se la richiesta è di ricerca ordinaria (es. "mostrami la bolla n. 4761")**: effettua un reindirizzamento alla homepage (`/`) passando la query originale come parametro URL.

```javascript
// AnalisiPage.jsx - Gestione risposte LLM
const applyLlmResponse = async (llmJson, userMessage = '') => {
  const { area, messaggio } = llmJson || {}
  const azione = llmJson?.azione || {}

  if (area === 'analisi') {
    const targetTab = azione.target_tab
    const targetSection = azione.target_section

    // Cambia la scheda attiva localmente
    if (targetTab) {
      setActiveTab(targetTab)
    }

    // Scroll morbido alla sezione di analisi desiderata
    if (targetSection) {
      setTimeout(() => {
        const element = document.getElementById(targetSection)
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 150)
    }

    return { messaggio: messaggio || 'Sezione aperta correttamente.' }
  }

  // Se l'utente chiede dati al di fuori dell'analisi (es. dettaglio bolle o fatture)
  // lo reindirizziamo alla Consultazione passando la richiesta in querystring per non interrompere il flusso
  const redirectUrl = `/?query=${encodeURIComponent(userMessage)}`
  window.location.href = redirectUrl

  return { messaggio: 'Reindirizzamento alla consultazione documenti...' }
}

const applyClienteSelection = (codice, context) => {
  // Nel contesto dell'analisi, se l'utente seleziona un cliente da un menù di disambiguazione,
  // possiamo memorizzarlo localmente per filtrare le tabelle nella pagina o evidenziare righe.
  console.log('Cliente selezionato nell\'analisi:', codice, context)
}
```

### C. Gestione della Query Automatica all'Avvio in `App.jsx`
Per far sì che l'utente che viene reindirizzato dalla pagina Analisi alla homepage non debba riscrivere la richiesta, dobbiamo fare in modo che `App.jsx` intercetti il parametro `query` all'avvio e lo inoltri alla chat.

1.  **In `App.jsx`**:
    Estraiamo il parametro `query` dalla querystring dell'URL e lo passiamo al `ChatPanel` come prop `initialQuery`:
    ```javascript
    // Estrazione del parametro all'avvio di App.jsx
    const params = new URLSearchParams(window.location.search)
    const initialQuery = params.get('query') || ''
    ```
    Nel rendering del layout:
    ```jsx
    <ChatPanel 
      onResponse={applyLlmResponse} 
      onClienteSelect={applyClienteSelection} 
      initialQuery={initialQuery}
    />
    ```

2.  **In `ChatPanel.jsx`**:
    Intercettiamo la prop `initialQuery` ed eseguiamo automaticamente l'invio al caricamento del componente:
    ```javascript
    export default function ChatPanel({ onResponse, onClienteSelect, initialQuery }) {
      const [input, setInput] = useState('')
      const [messages, setMessages] = useState([])
      const [sending, setSending] = useState(false)
      // ... altri stati ...

      useEffect(() => {
        if (initialQuery) {
          // Imposta l'input visibile
          setInput(initialQuery)
          
          // Eseguiamo l'invio automatico dopo un breve ritardo per garantire che la chat sia montata
          const timer = setTimeout(() => {
            handleSendQuery(initialQuery)
          }, 300)
          return () => clearTimeout(timer)
        }
      }, [initialQuery])

      const handleSendQuery = async (queryText) => {
        if (!queryText.trim() || sending) return
        setSending(true)
        
        // Aggiunge il messaggio utente all'elenco
        setMessages((prev) => [...prev, { role: 'user', text: queryText }])
        setInput('')

        try {
          const res = await authFetch('/llmrequest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: queryText })
          })
          const data = await res.json()
          if (!res.ok) throw new Error(data.error)

          const parsed = parseLlmJson(data.response)
          const result = await onResponse(parsed, queryText)
          const messaggio = typeof result === 'string' ? result : result.messaggio

          setMessages((prev) => [
            ...prev,
            { role: 'assistant', text: messaggio, disambiguation: result.disambiguation || null }
          ])
        } catch (err) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', text: `Errore: ${err.message}`, isError: true }
          ])
        } finally {
          setSending(false)
        }
      }
      
      // ... rendering esistente ...
    }
    ```

---

## 6. Piano di Verifica e Test

Per validare le modifiche senza introdurre bug regressivi nelle ricerche ordinarie:
1.  **Test di Non-Regressione (Query Storiche)**:
    *   Inviare query quali "mostrami le fatture TAM 2026" e verificare che l'area rimanga `"fatture"`, i filtri rimangano valorizzati e `target_tab` sia vuoto.
    *   Inviare "dettaglio bolla 1234" e verificare che venga aperto il pannello dettaglio.
2.  **Test di Routing Analisi**:
    *   Inviare "voglio fare uno stress test sul fatturato" e validare che il JSON contenga `area: "analisi"`, `azione.tipo: "apri_analisi"`, `target_tab: "opportunita"`, `target_section: "stress-test"`.
    *   Verificare che l'URL finale generato corrisponda a `/analisi?tab=opportunita#stress-test`.
3.  **Test di Caricamento Asincrono (Scorrimento)**:
    *   Simulare una connessione lenta e verificare che l'auto-scorrimento si attivi solo *dopo* il termine del caricamento della tabella dati (quando `loading === false`), altrimenti l'ancora si posizionerebbe su coordinate errate.

---

## 7. Analisi dell'Impatto di GPT-4o-Mini (OpenAI) rispetto a Gemini

È possibile configurare l'applicazione per utilizzare **`gpt-4o-mini`** di OpenAI in sostituzione del modello Gemini. Di seguito si esaminano la compatibilità con il nuovo prompt esteso, le differenze prestazionali, i costi e la facilità di integrazione.

### A. Compatibilità del Prompt Esteso con `gpt-4o-mini`
*   **Finestra di Contesto**: `gpt-4o-mini` supporta fino a **128.000 token** di input. Il nostro prompt principale esteso per la sezione Analisi (~6.000 token complessivi) occupa solo il **4.7%** della finestra di contesto disponibile.
*   **Token di Output**: Il modello supporta fino a 16.384 token in uscita. La risposta del nostro parser è un oggetto JSON compatto che richiede meno di 250 token.
*   **Conclusione**: **Sì, il nuovo prompt esteso funzionerà perfettamente e senza alcuna limitazione fisica.**

### B. Confronto tra i Modelli

| Caratteristica | Gemini (2.0-flash / 3.5-flash) | GPT-4o-Mini (OpenAI) | Impatto sull'Applicazione |
| :--- | :--- | :--- | :--- |
| **Context Window** | 1.000.000+ token | 128.000 token | Entrambi sono ampiamente sovradimensionati per il nostro prompt di ~6k token. |
| **Structured Outputs** | Supporto per JSON schema nativo. | Supporto nativo per **Structured Outputs** (JSON Schema rigido). | OpenAI garantisce al 100% che l'output sia JSON valido conforme allo schema, eliminando errori di sintassi. |
| **Prompt Caching** | Supportato (automatico per blocchi >32k token). | Supportato ( automatico per richieste frequenti, con sconto del 50% sui token di input). | Il caching riduce drasticamente latenza e costi di input su OpenAI per richieste ripetute. |
| **Costi (Input / Output)** | ~$0.075 / $0.30 per 1M token | $0.150 / $0.60 per 1M token ($0.075 input con cache) | I costi per singola richiesta rimangono inferiori a $0.0005. La differenza economica è irrilevante. |
| **Latenza di Risposta** | Estremamente veloce (tipicamente <800ms) | Molto veloce (tipicamente 600ms - 1s) | Esperienza utente fluida e risposte quasi istantanee in entrambi i casi. |

### C. Vantaggi Specifici di `gpt-4o-mini`
1.  **Garanzia di Formato (Structured Outputs)**:
    OpenAI permette di forzare l'output affinché rispetti esattamente uno schema JSON definito. Questo previene qualsiasi anomalia in cui il modello risponde con testo libero o include i delimitatori ```json ... ```, facilitando il parsing lato client.
2.  **Affidabilità dell'Instruction Following**:
    `gpt-4o-mini` dimostra un'elevata precisione nel comprendere vincoli complessi e negazioni (es. distinguere rigidamente quando una parola chiave fa riferimento a un documento specifico rispetto a un report aggregato di analisi).

### D. Impatto sull'Infrastruttura Esistente (`backend/LLMservice.py`)
L'infrastruttura backend di Intex è già predisposta per supportare entrambi i provider tramite la classe/funzioni definite in [LLMservice.py](file:///Users/globalbit/Code/intex/backend/LLMservice.py):
*   Il provider di default è controllato dalla variabile d'ambiente `LLM_PROVIDER` (righe 13-14).
*   Se `LLM_PROVIDER="OPENAI"`, il sistema utilizza automaticamente `gpt-4o-mini` come modello predefinito (riga 9) e invoca la chiamata Responses API (`_call_openai`).

Per passare a `gpt-4o-mini` è quindi sufficiente aggiornare le configurazioni nel file di ambiente `.env` del backend:
```env
LLM_PROVIDER=OPENAI
OPENAI_APIKEY=sk-proj-tuachiaveapi...
OPENAI_MODEL=gpt-4o-mini
```
Non è richiesta alcuna modifica al codice sorgente del backend o del frontend.
