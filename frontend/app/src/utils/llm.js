export function parseLlmJson(raw) {
  let text = raw.trim()
  if (text.startsWith('```')) {
    text = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  }
  text = replaceOggiPlaceholder(text)
  return JSON.parse(text)
}

export function replaceOggiPlaceholder(value) {
  if (typeof value !== 'string' || !value) return value || ''
  const today = new Date().toLocaleDateString('en-CA')
  return value.replace(/\{\{?\s*oggi\s*\}?\}/gi, today)
}

function normalizeClienteString(value) {
  return value
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[.'",\-&()]/g, ' ')
    .replace(/\b(s\.?\s*r\.?\s*l\.?|s\.?\s*p\.?\s*a\.?|s\.?\s*a\.?\s*s\.?|s\.?\s*n\.?\s*c\.?|srl|spa|sas|snc|unipersonale)\b/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function startsAtWordBoundary(name, query) {
  const lowerName = name.toLowerCase()
  const lowerQuery = query.toLowerCase()
  if (!lowerName.startsWith(lowerQuery)) return false
  const next = lowerName[lowerQuery.length]
  return !next || /[\s&\-,(./]/.test(next)
}

function sortCandidates(candidates) {
  return [...candidates].sort((a, b) => {
    const lenDiff = a.ragione_sociale.length - b.ragione_sociale.length
    if (lenDiff !== 0) return lenDiff
    return a.ragione_sociale.localeCompare(b.ragione_sociale, 'it')
  })
}

function uniqueCandidates(candidates) {
  const seen = new Set()
  return candidates.filter((c) => {
    if (seen.has(c.codice)) return false
    seen.add(c.codice)
    return true
  })
}

function narrowToBestTier(candidates, query) {
  if (candidates.length <= 1) return candidates

  const wordBoundary = candidates.filter((c) =>
    startsAtWordBoundary(c.ragione_sociale, query)
  )
  if (wordBoundary.length === 1) return wordBoundary
  if (wordBoundary.length > 1) return sortCandidates(wordBoundary)

  const startsWith = candidates.filter((c) =>
    c.ragione_sociale.toLowerCase().startsWith(query.toLowerCase())
  )
  if (startsWith.length === 1) return startsWith
  if (startsWith.length > 1) return sortCandidates(startsWith)

  return sortCandidates(candidates)
}

function resolveTier(matches, query) {
  const unique = uniqueCandidates(matches)
  if (unique.length === 0) return null
  if (unique.length === 1) {
    return { type: 'single', candidates: unique }
  }
  const narrowed = narrowToBestTier(unique, query)
  if (narrowed.length === 1) {
    return { type: 'single', candidates: narrowed }
  }
  return { type: 'ambiguous', candidates: narrowed }
}

function findClienteCandidates(query, clienti) {
  const q = query.trim()
  const qLower = q.toLowerCase()
  const qNorm = normalizeClienteString(q)

  const tiers = [
    clienti.filter((c) => String(c.codice).toLowerCase() === qLower),
    clienti.filter((c) => c.ragione_sociale.toLowerCase() === qLower),
    clienti.filter((c) => normalizeClienteString(c.ragione_sociale) === qNorm),
    clienti.filter((c) => c.ragione_sociale.toLowerCase().includes(qLower)),
    clienti
      .filter((c) => qLower.includes(c.ragione_sociale.toLowerCase()))
      .sort((a, b) => b.ragione_sociale.length - a.ragione_sociale.length),
    clienti.filter((c) => {
      const nameNorm = normalizeClienteString(c.ragione_sociale)
      return nameNorm.includes(qNorm) || qNorm.includes(nameNorm)
    })
  ]

  const qWords = qNorm.split(' ').filter((w) => w.length >= 2)
  if (qWords.length > 0) {
    tiers.push(
      clienti.filter((c) => {
        const nameNorm = normalizeClienteString(c.ragione_sociale)
        return qWords.every((word) => nameNorm.includes(word))
      })
    )
  }

  tiers.push(clienti.filter((c) => qLower.includes(String(c.codice).toLowerCase())))

  for (const tier of tiers) {
    const result = resolveTier(tier, q)
    if (result) return result
  }

  return { type: 'none', candidates: [] }
}

const MAX_DISAMBIGUATION_CANDIDATES = 8

/**
 * Match an LLM-returned cliente string against the local /api/clienti list.
 * Returns a single codice, multiple ambiguous candidates, or no match.
 */
export function matchCliente(query, clienti) {
  if (!query?.trim()) {
    return { codice: '', matched: true, ambiguous: false, candidates: [] }
  }
  if (!clienti?.length) {
    return { codice: '', matched: false, ambiguous: false, candidates: [] }
  }

  const result = findClienteCandidates(query, clienti)

  if (result.type === 'single') {
    return {
      codice: result.candidates[0].codice,
      matched: true,
      ambiguous: false,
      candidates: []
    }
  }

  if (result.type === 'ambiguous') {
    return {
      codice: '',
      matched: false,
      ambiguous: true,
      candidates: result.candidates.slice(0, MAX_DISAMBIGUATION_CANDIDATES)
    }
  }

  return { codice: '', matched: false, ambiguous: false, candidates: [] }
}

export function appendClienteNotFoundMessage(messaggio, clienteQuery, matchResult) {
  if (!clienteQuery?.trim() || matchResult.matched || matchResult.ambiguous) {
    return messaggio
  }
  const base = messaggio?.trim() || ''
  const suffix = 'Non è stato possibile individuare il cliente.'
  return base ? `${base} ${suffix}` : suffix
}
