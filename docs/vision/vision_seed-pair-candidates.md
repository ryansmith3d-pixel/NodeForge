# Idiograph — Seed Pair Candidates
**Status:** LIVING — working reference, not frozen
**Created:** 2026-04-14
**Purpose:** Candidate seed pairs for validation spikes and demo graph selection

---

## Graph Structure Archetypes

Five distinct structural archetypes emerged from the brainstorm. The demo is most
compelling if it can show graphs that *look* different because the underlying
intellectual structures are different — not just different topics rendering the
same topology.

| Archetype | Description | Visual character |
|---|---|---|
| **Convergence** | Two groups, same conclusion, same time | Two roots, shared ancestry cluster, merging forward |
| **Paradigm collision** | Incompatible premises, same phenomenon | Minimal intersection, diverging forward communities |
| **Hub and spokes** | Single paper, cross-disciplinary radiation | Star topology, spokes into disconnected communities |
| **Sequential build** | Parent-child relationship, explicit dependency | Linear chain, hierarchical depth |
| **Dormant activation** | Modest citations for years, then explosive growth triggered by external event | Flat forward curve, then vertical — temporally distinctive |

---

## Candidate Pairs by Archetype

---

### Convergence

**CRISPR — PRIMARY (validated)**
- Doudna/Charpentier 2012 (W2045435533) + Zhang 2013 (W2064815984)
- Both spikes GREEN. Implementation-ready.
- Story: two labs, same tool, same year, shared foundational ancestry
- OpenAlex coverage: excellent

**AlphaFold + RoseTTAFold (protein structure, 2021)**
- Jumper et al. 2021 (DeepMind) + Baek et al. 2021 (Baker lab)
- Same problem, same year, deep learning approach
- Story: two AI labs solving a 50-year biology problem simultaneously
- Risk: 2021 is recent — counts_by_year accumulation may be thinner than CRISPR
- Status: candidate for pass 1 spike

**Pfizer/Moderna COVID vaccines (2020)**
- Corbett et al. 2020 (Moderna) + Polack et al. 2020 (Pfizer/BioNTech)
- Shared ancestry includes Karikó/Weissman 2005 and McLellan spike stabilization work
- Intersection would span two otherwise disconnected communities: mRNA immunology
  and lipid nanoparticle delivery
- Status: candidate for pass 1 spike

**Plate tectonics (1967-1968)**
- McKenzie & Parker 1967 + Morgan 1968
- Two independent formalizations of plate tectonics, same year
- Risk: 1960s geology journals — OpenAlex reference list completeness uncertain
- Status: lower priority, coverage risk

---

### Paradigm Collision

**Black-Scholes + Mandelbrot (quantitative finance)**
- Black & Scholes 1973 + Mandelbrot 1963
- Gaussian assumptions vs. power law price variation — incompatible premises
- Field chose Black-Scholes and ignored Mandelbrot for thirty years
- Story: LTCM blowup 1998 is the moment the ignored model is vindicated
- Intersection at depth=1 expected to be minimal
- Forward communities would diverge sharply — quant finance vs. complexity science
- Risk: 1963/1973 papers — reference list completeness in OpenAlex uncertain
- Status: high interest, coverage validation needed

**Cladistics vs. Phenetics**
- Hennig 1966 + Sokal & Sneath 1963
- Phylogenetic classification vs. numerical taxonomy — paradigm displacement
- Phenetics citation community largely disappears by 1990s
- Risk: Hennig 1966 is a book — OpenAlex book coverage is spottier than journals
- Status: interesting, book coverage is the blocker

---

### Hub and Spokes

**Shannon 1948 (information theory)**
- Shannon 1948 + Kolmogorov 1965
- Shannon: probabilistic information theory. Kolmogorov: algorithmic complexity.
  Independent formalizations, different mathematical traditions, 17 years apart.
- Shannon forward graph radiates into genetics, linguistics, physics, neuroscience,
  computer science, cryptography, economics — disconnected communities all citing
  the same paper
- Star topology visually distinctive from all other archetypes
- Risk: 1948 paper — reference list may be very sparse in OpenAlex
- Status: high interest for essay/demo, coverage validation needed

**Ioannidis 2005 (replication crisis)**
- Ioannidis 2005 + Simmons, Nelson & Simonsohn 2011
- "Why Most Published Research Findings Are False" + "False-Positive Psychology"
- Forward graph cross-disciplinary: medicine, psychology, economics, neuroscience
- Direct connection to essay thesis: hidden researcher degrees of freedom =
  hidden LLM nondeterminism. Same structural problem, different domain.
- OpenAlex coverage: excellent — both papers are open access, heavily cited
- Status: strong candidate, essay connection is explicit

---

### Sequential Build

**Transformer + BERT (NLP)**
- Vaswani et al. 2017 ("Attention Is All You Need") + Devlin et al. 2018 (BERT)
- BERT explicitly builds on transformer architecture — direct parent-child
- Tests hierarchical structure rather than convergence
- OpenAlex coverage: excellent — arXiv papers, heavily indexed
- Status: candidate, structurally different from all others

**Felsenstein 1981 + Felsenstein 1985 (phylogenetics)**
- Maximum likelihood trees + bootstrap confidence values
- Same author, four years apart, both standard methodology citations
- Tests whether pipeline handles explicit methodological lineage correctly
- Status: lower priority — same-author pair is less narratively interesting

---

### Dormant Activation

**Karikó & Weissman 2005 (mRNA vaccines)**
- Karikó & Weissman 2005 + Corbett et al. 2020 (Moderna)
- 15 years of modest citations, then vertical spike in 2020
- Nobel Prize 2023 — story widely known, immediately legible to general audience
- The counts_by_year curve for Karikó 2005 is one of the most visually dramatic
  in modern science — flat line, then hockey stick at March 2020
- This is what Node 4 acceleration ranking was designed to detect in its early phase
- OpenAlex coverage: excellent for all papers
- Status: strong candidate — archetype is unique, temporal drama is data

---

## Priority for Next Spike

If a second validation spike is warranted, candidates in priority order:

1. **Ioannidis 2005 + Simmons et al. 2011** — best OpenAlex coverage, direct essay
   connection, hub-and-spokes topology distinct from CRISPR convergence

2. **Karikó/Weissman 2005 + Corbett 2020** — dormant activation archetype unique
   in the list, temporal drama visible directly in counts_by_year data, Nobel story
   is publicly legible

3. **Vaswani 2017 + Devlin 2018** — sequential build archetype, excellent coverage,
   directly relevant to AI domain of the essay

4. **Black-Scholes 1973 + Mandelbrot 1963** — most intellectually interesting
   paradigm collision, highest coverage risk given paper age

---

## Notes on OpenAlex Coverage Risk

Coverage risk increases significantly for papers before ~1990. The risk is not
whether the paper *resolves* (DOI lookup usually works) but whether the
*reference list* is complete. A paper that resolves with `referenced_works: []`
is not useful for backward traversal.

Rough coverage reliability by era:
- Post-2000: excellent
- 1990-2000: good
- 1980-1990: moderate
- Pre-1980: uncertain — validate before committing

All pre-1980 candidates (Shannon, Mandelbrot, Black-Scholes, Hennig, plate
tectonics) require a pass 1 coverage check before any spike design.

---

## Cladistics Note

The cladistics domain has a unique recursive property worth preserving for the
essay: the field itself is about finding the correct graph structure underlying
observed data. A citation graph tool analyzing the intellectual history of the
people who invented phylogenetic tree-building is the thesis argument made
literal — the tool and the subject matter are doing the same thing at different
scales. Worth a sentence in the essay regardless of whether a cladistics spike
is run.
