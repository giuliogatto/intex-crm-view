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

## 5. Valutazione UX ed Evoluzioni Future

### Limite della Redirezione Semplice (Perdita di Contesto)
L'utilizzo di `window.location.href` causa un ricaricamento completo della pagina. Questo comporta:
*   La chiusura del pannello chat.
*   La perdita della cronologia locale dei messaggi scambiati in quella sessione.
*   La necessità di riautenticare implicitamente la sessione o ricaricare tutti i KPI di analisi da zero.

### Soluzioni Raccomandate per il Futuro
1.  **Integrazione della Chat nella Pagina Analisi**:
    *   Renderizzare il componente `ChatPanel` anche all'interno di `AnalisiPage.jsx` (ad esempio in una sidebar collassabile). In questo modo, la navigazione interna tra schede e l'auto-scorrimento possono avvenire senza ricaricare la pagina (modificando semplicemente lo stato `activeTab` del componente a livello locale).
2.  **Routing Client-Side (Single Page Application)**:
    *   Se l'applicazione decidesse di adottare un router di libreria (es. `react-router-dom`), la redirezione da `/` a `/analisi` avverrebbe mantenendo lo stato globale della chat intatto, eliminando la necessità di caricamenti completi del browser.

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
