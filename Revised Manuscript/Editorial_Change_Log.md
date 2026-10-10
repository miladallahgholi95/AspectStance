# Editorial Change Log

This log records every substantive change from the original `AspectStance_Paper/AspectStance.tex` to `Manuscript_Final_Revised/AspectStance.tex`. Pure label renames and float moves are grouped together. Finding IDs (R1-01, R6-01, …) are defined in `Comprehensive_Peer_Review.md`.

**Numerical integrity.**
- All numbers inside the nine tables are mechanically identical to the original.
- No number was removed from the prose.
- The prose gained two derived numbers, 7.6 and 10.4 (see C-12).

## A. Scientific content and definitions

| # | Location | Problem | Change | Rationale | Verification |
|---|---|---|---|---|---|
| C-01 | §6.2 ¶3 | Undisclosed confound in the random-clustering control (R1-01) | Added two sentences: under random assignment, Eq. (11) no longer reproduces the training assignments, so the control changes both the partition and train–test agreement and does not separate the two | Reviewers would raise this; disclosing it pre-empts the objection and strengthens credibility | No conclusion or number changed |
| C-02 | §7.3 *Statistical evaluation* | No remedy offered for C-01 | Added: routing the training posts by the same nearest-centroid rule would separate the two effects | Gives reviewers a concrete answer | — |
| C-03 | §4.4 ¶1 | K-means objective, centroid and *K* selection defined only in words (R1-02) | Inline K-means objective and centroid formula; **new Eq. (8)** with the mean cosine silhouette, *s_i*, *a_i* and *b_i* defined | Formal definitions; consistent with the implementation (cosine silhouette over training posts; centroids not renormalised) | Equations renumbered automatically; all `\eqref`s resolve |
| C-04 | §3 | *N_T* used but not defined | "a set of *N_T* labelled posts" | Notation completeness | — |
| C-05 | §4.3, Eq. (5) | Encoder symbol and dimensions implicit | "denoted *E*(·)"; *e*, *ẽ* ∈ ℝ³⁰⁷² | Notation completeness | 3,072 matches the text |
| C-06 | §4.3, Eq. (6) | [·;·] undefined; reduced dimensions implicit | *r*, *r̃* ∈ ℝ²⁰ added; "where [·;·] denotes vector concatenation" | Notation completeness | 20 + 20 = 40 is consistent throughout |
| C-07 | §5.2 ¶2 | *F*-macro_T had no formula | *F*-macro_T = \|𝒯\|⁻¹ Σ_T *F1*_avg(T), with 𝒯 defined | Formal definition | Consistent with the text and Table 3 |
| C-08 | §7.1 | Overclaim: the proposed experiments "would quantify the share of each effect"; untested "stance is expressed differently" (R1-04) | "The present controls do not apportion the gain among these three mechanisms…"; added a size-matched random partition as a future control; "is" → "may be" | Accuracy | — |

## B. Results reporting

| # | Location | Problem | Change | Rationale |
|---|---|---|---|---|
| C-09 | Abstract | "The discovered aspects match recognisable subtopics" overstates §6.3 (R2-05) | "Most discovered aspects correspond to recognisable subtopics, such as impeachment or abortion legislation" | Agrees with §6.3 (5 of 8 largest clusters are broad or miscellaneous) |
| C-10 | Abstract | Unhedged final claim | "…the results indicate that making it explicit provides a useful inductive bias" | Same hedge level as §8 |
| C-11 | Table 7 caption; §6.4 | MPRF's metric ("F-macro") misattributed; BERTweet scores not attributed to KASD's re-run (R2-02, R2-03) | Caption names both exceptions and the BERTweet source; text: "(82.1, as reported by KASD)"; MPRF sentence explains why F-macro coincides with *F1*_avg on binary P-Stance | Accurate attribution; scores unchanged |
| C-12 | §6.1 ¶4 | Margin over the strongest prompting baseline not stated (R2-04) | "AspectStance exceeds the stronger, few-shot baseline by 7.6 and 10.4 points" | 90.8 − 83.2 = 7.6 and 85.3 − 74.9 = 10.4; the supervision-regime caveat is kept in the next sentence |
| C-13 | Table 7 | Rows in arbitrary order (MPRF 88.4 listed after CKD 82.0) | AspectStance first, then the other systems in descending score order (caption says so) | Readability; row-set equality checked mechanically |
| C-14 | Table 7 | MPVStance described as "Zero-shot verification" (setting not confirmed) | "Multi-perspective LLM verification" | Describes the method without asserting an unverified setting |
| C-15 | §6.4 last ¶ | Repeated the first paragraph; "highest value" applied to both benchmarks | "On both benchmarks, AspectStance has the highest score in Table 7, but no row is a controlled comparison…" | Removes redundancy |

## C. Language, register and structure

| # | Location | Change |
|---|---|---|
| C-16 | Abstract | "input text" / "text" → "post" throughout; "Over ten seeded runs" → "Averaged over ten seeded runs"; trimmed to 250 words (the Springer limit) with every number kept |
| C-17 | §1 | The three contributions are now an enumerated list (wording preserved); added citations [7–10] to the unsupported "Topic-aware stance methods approximate this missing layer…" |
| C-18 | §2.1 | "Early stance detectors represented…" → "Feature-based stance detectors represent…" |
| C-19 | §2.2 | "research studies transfer" → "studies examine transfer" (removes a garden-path parse) |
| C-20 | §2.4 | "cluster contextual representations … with K-means" → "apply K-means to contextual representations…" (also removes an overfull line) |
| C-21 | §4.2 | Semicolon chain split: "…explain its connection to the post. Generated glosses can exceed this range: two of the seven reproduced in Section 6.5 contain 59 words each." |
| C-22 | §5.2 | Wordy sentence about non-interchangeable metrics shortened |
| C-23 | §5.1, §5.3, §6.1, App. A | "SemEval-2016 Task 6" → "SemEval-2016" after the abbreviation is defined in §5.1 |
| C-23b | §7.3 *Baselines, scope, and contamination* | "All estimators use library defaults" contradicted §5.4, where UMAP departs from its defaults → "All K-means and classifier settings are library defaults (Section 5.4)" |
| C-24 | §6.2 | Two invariance-check sentences merged into one |
| C-25 | §6.4 | Heading "Comparison with published systems" → "Comparison with prior work" (no longer wraps in the narrow column); "Like AspectStance, KASD also…" → "Like AspectStance, KASD…" |
| C-26 | §8 ¶2 | "is a useful inductive bias …, more than an interpretability layer" → "acts as a useful inductive bias … rather than only as an interpretability layer"; "the part of the target's discourse it concerns" → "a recurring region of the target's discourse" (matches §4.4's definition) |
| C-27 | Declarations | Removed "Tweet texts are not redistributed" from the Ethics statement (the released aspect files contain tweet text); Data availability now states that the training-post aspect assignments are released in the code repository. See `Remaining_Author_Actions.md` A-03 |

## D. Typography, layout and production

| # | Change | Finding |
|---|---|---|
| C-28 | Build engine documented: pdfLaTeX + BibTeX (header comment), which removes the 13 pt caption leading of the XeLaTeX-built shipped PDF | R6-01 / R7-01 |
| C-29 | Table text `\footnotesize` (7 pt) → class `\tablebodyfont` (8 bp/9.5 bp) in all nine tables | R6-02 |
| C-30 | Standard-deviation size 5.6 pt → 6.5 pt (`\sd` macro) | R6-03 |
| C-31 | Table 3: `tabularx` → `tabular*`; gapped row shading removed. Table 4: fixed `L{0.40\linewidth}` → natural `l` column, so "AspectStance" is no longer hyphenated | R6-04, R6-08 |
| C-32 | Tables 5–6: bar column `l` → `p{1.75cm}` (bars no longer overrun the rules) | R6-07 |
| C-33 | Prompt boxes: typewriter braces (`\ttlbrace`, `\ttrbrace`), ragged-right, consistent paragraph spacing; Fig. 2 padding matched to the appendix boxes; appendix boxes made unbreakable | R6-05 |
| C-34 | Float spacing 6 pt → 10–12 pt; duplicated spacing block and dead display-skip overrides removed; `\dblfloatpagefraction` 0.95 → 0.7 so the example tables can share a float page | R6-06, R7-03 |
| C-35 | Float definitions for Tables 2, 5, 6, 7, 8 and 9 moved next to their first mention; Tables 8–9 set as `[p]` floats | R4-02 |
| C-36 | Unused packages removed (`multirow`, `amsthm`, `listings`) along with the redundant `\tcbuselibrary` | R7-02 |
| C-37 | Section labels `subsec61/62/63/64/6rc` → `sec:inventories/main/published/qualitative/random` | R7-04 |

## E. Bibliography (`references.bib`)

| # | Entry | Change |
|---|---|---|
| C-38 | `deraedt2023idas` | `Fr{'e}deric` → `Fr{\'e}deric` |
| C-39 | `cheng2024cosd` | arXiv preprint → *Knowledge-Based Systems* 317 (2025) 113399, doi:10.1016/j.knosys.2025.113399 |
| C-40 | `ma2024chain` | Proper booktitle; LNCS 15363; publisher; doi:10.1007/978-981-97-9443-0_7 |
| C-41 | `du2017tan` | Official title (no "Networks"); doi:10.24963/ijcai.2017/557 |
| C-42 | `coates2012kmeans` | doi:10.1007/978-3-642-35289-8_30 |
| C-43 | `allahgholi2025conspro` | Journal: "Journal of Artificial Intelligence and Data Mining" |

## F. Outside the manuscript (repository consistency)

| # | File | Change |
|---|---|---|
| C-44 | `AspectStance Implementation/README.md` and docstrings in `aspectstance/{classifier,clustering,data,experiment,metrics,model,report,representation}.py` | Equation references re-synchronised with the revised paper's Eqs. (1)–(13). They previously cited Eqs. 6–7, 12 and 14, which matched neither the shipped paper nor the revision. Comment and documentation only; `py_compile` passes; no code was run |

## Not changed (by decision)

- Any table value, reported score, standard deviation, count, or model name.
- The figures (`workflow.pdf`, `main_results.pdf`). They are legible vector graphics, their sources are not in the archive, and redrawing them could alter verified values.
- The dataset and the root `README.md`. See `Remaining_Author_Actions.md`.
- The journal class `sn-jnl.cls` and the style file `sn-mathphys-num.bst`.


## G. Final rounds: simplification, five-reviewer review, abstract panel

Numbers C-01 to C-44 above refer to the manuscript at the first editorial pass. The final manuscript also includes the following changes.

| # | Location | Change |
|---|---|---|
| C-45 | §3 | Problem restated in a framed box with two functions: aspect assignment h_T : x ↦ c and an aspect-conditioned classifier f_T : (x, c) ↦ y. The old aspect-set notation (𝒜_T, a_{T,k}, k*) was replaced throughout |
| C-46 | §4 | "Overview" subsection removed at the author's request; §4 opens directly with its paragraphs, and the subsections are now 4.1–4.6 |
| C-47 | §4.2 | Embedding and reduction equations merged into one: v = [U(E(x)); U(E(x̃))]. The paper now has Eqs. (1)–(12) |
| C-48 | §4.3 | K-means stated in words, with a corrected cosine argument (2−2cosθ holds between unit vectors); the silhouette selection rule, Eq. (7), fits on one line |
| C-49 | §4.5–4.6 | f_T(x, c) used consistently; the asymmetry between training and test UMAP coordinates made explicit; μ_{T,k} defined |
| C-50 | §1 | Gap and puzzle stated: prior methods combine topics with other components, and the cluster feature carries no new information yet helps. The gloss is motivated, with its lineage cited. The output is clarified as a target-level label returned with its aspect |
| C-51 | §2 | New §2.5 "LLM-augmented clustering and cluster features". §2.6 repositioned against Allaway and McKeown, and its claimed differences limited to the defensible ones |
| C-52 | Table 1 | Column "Uses stance labels" renamed "Stance labels in induction"; topic-guided transformer entry changed to "No" |
| C-53 | Throughout | Terminology aligned on "cluster feature". Aspect claims qualified as "judged by their generated names". Repeated caveats and figures cut |
| C-54 | Tables 4, 7 | Captions made self-contained: test-split selection bias (Table 4); three-target coverage with AspectStance's 85.8, and the comparability warning (Table 7) |
| C-55 | §6.1 | Feminist Movement sentence no longer implies a cause; it adds that the Base Method trails both prompting baselines |
| C-56 | §7.1–7.2 | Mechanism stated precisely (indicator columns, +2 squared distance, cone-shaped regions); §7.2 rewritten as "Implications for topic-aware stance detection" |
| C-57 | §8 | Conclusion reordered to end on the takeaway; wording no longer copies the abstract |
| C-58 | Abstract | Rewritten through a ten-reviewer panel and a final adversarial check (see Comprehensive_Peer_Review.md, Round 4): stronger motivation, precise gap, contribution stated as the answer, surprise placed with the results, prompting comparison added, hedged takeaway; 249 words |
| C-59 | Layout | Inline definitions kept on one line; the gap at the foot of p. 7 closed; all 23 pages re-inspected |
| C-60 | Implementation docs | Section and equation references re-synchronised again (Eqs. 1–12, §4.1–4.6) and the h_T(x) notation adopted. Comments only |

**Integrity check after the final rounds.** The nine tables are numerically identical to the original. The only numbers added to the prose are taken from the tables: 80.7, 69.6 and 16.3. Duplicated mentions of 10.1, 15.7, 15.1, 11.2, 9.5 and 0.55 were removed; each still appears elsewhere.
