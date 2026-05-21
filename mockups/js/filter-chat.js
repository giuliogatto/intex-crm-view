/**
 * Assistente mock: suggerisce come impostare i filtri in base alla richiesta utente.
 */
(function () {
  const area = document.body.dataset.filterArea;
  if (!area) return;

  const FILTER_HELP = {
    fatture: {
      areaLabel: "Fatture",
      fields: [
        "Data da / Data a — periodo di emissione",
        "Codice cliente — codice numerico anagrafica",
        "Ragione sociale — testo parziale (es. «Rossi», «TAM»)",
        "Stagione — es. PE 2026, AI 25-26",
        "Stato pagamento — Tutte / Aperte / Pagate",
        "N. fattura — ricerca puntuale su un solo documento",
      ],
      welcome:
        "Descrivi cosa vuoi cercare (es. «fatture aperte di TAM a marzo»). Ti indico quali filtri impostare, poi premi **Cerca**.",
    },
    bolle: {
      areaLabel: "Bolle / DDT",
      fields: [
        "Data da / Data a — periodo emissione bolla",
        "Codice cliente e Ragione sociale",
        "Stagione — opzionale",
        "Collegamento documento — N. fattura o offerta per bolle collegate",
      ],
      welcome:
        "Descrivi la ricerca bolle (es. «DDT di TAM a marzo» o «bolle collegate alla fattura 1909»). Ti guido sui filtri.",
    },
    ordini: {
      areaLabel: "Ordini / offerte",
      fields: [
        "Data da / Data a — periodo offerta",
        "Codice cliente e Ragione sociale",
        "Stagione — es. PE 2026",
        "Stato trattativa — Tutti / Accettata / Rifiutata / Aperta",
      ],
      welcome:
        "Descrivi le offerte che ti servono (es. «offerte aperte PE 2026 per Maglificio Rossi»). Ti spiego i filtri da usare.",
    },
  };

  const cfg = FILTER_HELP[area];
  if (!cfg) return;

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function formatReply(html) {
    return escapeHtml(html).replace(/\n/g, "<br>");
  }

  function matchRules(text, rules) {
    const t = text.toLowerCase();
    for (const rule of rules) {
      if (rule.test.some((p) => t.includes(p))) return rule.reply;
    }
    return null;
  }

  function buildFattureReply(text) {
    const rules = [
      {
        test: ["apert", "non pagat", "scadenz", "incass"],
        reply:
          "Per fatture **aperte / non pagate**:\n• **Stato pagamento** → «Aperte»\n• **Codice cliente** o **Ragione sociale** → cliente indicato\n• Periodo opzionale con **Data da** / **Data a**\nPoi **Cerca**.",
      },
      {
        test: ["pagat", "saldate", "chiuse"],
        reply:
          "Per fatture **pagate**:\n• **Stato pagamento** → «Pagate»\n• Aggiungi cliente e/o periodo se serve\nPoi **Cerca**.",
      },
      {
        test: ["dettaglio", "numero", "n.", "n°", "fattura n"],
        reply:
          "Per il **dettaglio di una fattura**:\n• Compila **N. fattura** con il numero documento\n• Lascia gli altri filtri vuoti se cerchi solo quel documento\n• **Cerca**, poi apri **Dettaglio** dalla lista se compaion più risultati.",
      },
      {
        test: ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
          "trimestre", "periodo", "2024", "2025", "2026", "mese"],
        reply:
          "Per un **periodo**:\n• **Data da** → primo giorno (es. 01/03/2026)\n• **Data a** → ultimo giorno del periodo\n• Aggiungi **cliente** se l’hai citato\nPoi **Cerca**.",
      },
      {
        test: ["stagion", "pe ", "ai ", "p/e", "a/i"],
        reply:
          "Per **stagione moda**:\n• **Stagione** → es. «PE 2026» o «AI 25-26»\n• Combina con **cliente** e/o **date** se necessario\nPoi **Cerca**.",
      },
      {
        test: ["tam", "rossi", "serigrafia", "tessitura", "maglificio", "cliente"],
        reply:
          "Per **cliente**:\n• **Ragione sociale** → testo parziale (es. «Rossi», «TAM»)\n• oppure **Codice cliente** se lo conosci (es. 1439, 1392, 1283, XXX)\n• Se compaion più omonimi, scegli dall’elenco che propone il gestionale\nPoi **Cerca**.",
      },
      {
        test: ["tutte", "elenco", "lista", "mostrami", "fatture"],
        reply:
          "Per **elenco fatture**:\n• **Data da** / **Data a** per il periodo\n• **Cliente** (codice o ragione sociale)\n• **Stato pagamento** se ti interessano solo aperte o pagate\nPoi **Cerca** e usa **Esporta CSV** per la domanda 10.",
      },
      {
        test: ["esport", "csv", "tabella", "riepilogo"],
        reply:
          "Per **export tabella** (domanda 10):\n• Imposta prima i filtri corretti\n• **Cerca** per ottenere la lista\n• Pulsante **Esporta CSV** sulla schermata risultati",
      },
      {
        test: ["totale", "fatturato", "somma", "aggregat"],
        reply:
          "Per **totali fatturati** (domanda 3) questi mockup mostrano solo liste/dettaglio.\nIn produzione servirebbe una vista **Riepilogo** con cliente + periodo/stagione; qui usa filtri periodo + cliente e consulta i totali restituiti dal gestionale.",
      },
    ];
    return matchRules(text, rules);
  }

  function buildBolleReply(text) {
    const rules = [
      {
        test: ["collegat", "fattura", "offerta", "disp", "documento"],
        reply:
          "Per **bolle collegate** a un documento:\n• **Collegamento documento** → numero fattura o offerta\n• oppure filtra per **cliente** + **periodo**\nPoi **Cerca**.",
      },
      {
        test: ["ddt", "bolla", "bolle", "spediz", "consegn"],
        reply:
          "Per **bolle in un periodo**:\n• **Data da** / **Data a**\n• **Ragione sociale** o **Codice cliente**\n• **Stagione** solo se serve\nPoi **Cerca**.",
      },
      {
        test: ["tam", "rossi", "cliente"],
        reply:
          "Per **cliente**:\n• **Ragione sociale** (parziale) o **Codice cliente**\n• **Date** per limitare il periodo\nPoi **Cerca**.",
      },
      {
        test: ["esport", "csv"],
        reply:
          "Dopo aver impostato i filtri e premuto **Cerca**, usa **Esporta CSV** sulla tabella risultati.",
      },
    ];
    return matchRules(text, rules);
  }

  function buildOrdiniReply(text) {
    const rules = [
      {
        test: ["accettat", "rifiutat", "apert", "stato", "pipeline"],
        reply:
          "Per **stato offerta**:\n• **Stato trattativa** → Accettata / Rifiutata / Aperta\n• Aggiungi **cliente** e/o **stagione** se serve\nPoi **Cerca**.",
      },
      {
        test: ["stagion", "pe ", "ai "],
        reply:
          "Per **stagione**:\n• **Stagione** → es. «PE 2026», «PE 2026 LAB»\n• **Cliente** se indicato\n• **Date** opzionali per restringere il periodo\nPoi **Cerca**.",
      },
      {
        test: ["offert", "preventiv", "commess"],
        reply:
          "Per **cercare offerte**:\n• **Cliente** (codice o ragione sociale)\n• **Stagione** e/o **periodo** (Data da / Data a)\n• **Stato trattativa** se ti interessa solo un esito\nPoi **Cerca**.",
      },
      {
        test: ["rossi", "tam", "maglificio", "cliente"],
        reply:
          "Per **cliente**:\n• **Ragione sociale** parziale o **Codice cliente** (es. 1283 per Maglificio Rossi)\nPoi **Cerca**.",
      },
      {
        test: ["esport", "csv"],
        reply:
          "Imposta i filtri, **Cerca**, poi **Esporta CSV** per il riepilogo tabellare.",
      },
    ];
    return matchRules(text, rules);
  }

  function getReply(userText) {
    const t = userText.trim();
    if (!t) return "Scrivi cosa vuoi cercare: ti indico i filtri da compilare.";

    let specific =
      area === "fatture"
        ? buildFattureReply(t)
        : area === "bolle"
          ? buildBolleReply(t)
          : buildOrdiniReply(t);

    if (specific) return specific;

    const fieldList = cfg.fields.map((f) => "• " + f).join("\n");
    return (
      "Non ho riconosciuto una richiesta precisa. Nell’area **" +
      cfg.areaLabel +
      "** puoi usare:\n" +
      fieldList +
      "\n\nRiformula con cliente, periodo, stato o numero documento."
    );
  }

  function init() {
    const wrapper = document.querySelector(".page-with-chat");
    if (!wrapper) return;

    const aside = document.createElement("aside");
    aside.className = "filter-chat";
    aside.setAttribute("aria-label", "Assistente filtri");
    aside.innerHTML =
      '<div class="filter-chat__head">' +
      "<h2>Assistente filtri</h2>" +
      "<p>Solo guida ai filtri · " +
      cfg.areaLabel +
      "</p>" +
      "</div>" +
      '<div class="filter-chat__messages" id="filter-chat-messages" role="log" aria-live="polite"></div>' +
      '<form class="filter-chat__form" id="filter-chat-form">' +
      '<label class="visually-hidden" for="filter-chat-input">Descrivi cosa cerchi</label>' +
      '<textarea id="filter-chat-input" rows="2" placeholder="Es. fatture aperte di TAM a marzo 2026…"></textarea>' +
      '<button type="submit" class="btn btn--primary">Invia</button>' +
      "</form>";

    wrapper.appendChild(aside);

    const messagesEl = aside.querySelector("#filter-chat-messages");
    const form = aside.querySelector("#filter-chat-form");
    const input = aside.querySelector("#filter-chat-input");

    function addMessage(role, text) {
      const div = document.createElement("div");
      div.className =
        "filter-chat__msg filter-chat__msg--" + (role === "user" ? "user" : "bot");
      const label = role === "user" ? "Tu" : "Assistente";
      div.innerHTML =
        "<strong>" +
        label +
        "</strong> " +
        formatReply(text);
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    addMessage("bot", cfg.welcome);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      addMessage("user", text);
      addMessage("bot", getReply(text));
      input.value = "";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
