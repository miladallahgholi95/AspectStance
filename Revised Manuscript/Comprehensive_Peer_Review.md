# Comprehensive Peer Review: *AspectStance* manuscript

**Manuscript.** *AspectStance: Unsupervised Discovery of Target-Specific Aspects for Stance Detection* (Allahgholi and Rahmani), Springer Nature `sn-jnl` template, two-column (`iicol`), `sn-mathphys-num` reference style.
**Input.** `AspectStance_Paper.zip` (one `.tex`, `.bib`, `.bbl`, class and style files, two vector figures, shipped PDF of 22 pages).
**Output.** `Manuscript_Final_Revised.zip` / `.pdf` (23 pages).

## How this review was conducted

This is not a human review panel. The seven reviewer roles, the Editor-in-Chief and the QA auditor are separately scoped review passes carried out by one AI assistant (Claude). Bibliographic checks were delegated to a separate search agent. The ground rules were:

- **No experiments were run.** No training, evaluation or dataset scripts were executed, and no dataset file was modified. Every number reported by the author was treated as authoritative. Only arithmetic consistency checks on already reported numbers were performed.
- **Known exception, recorded once.** The GitHub copy of the data is incomplete; the author will update the GitHub repository with the complete dataset before final release. It is consistent with what was observed: in the released aspect files, Hillary Clinton has 639 and Legalization of Abortion 603 training rows, against 689 and 653 in the paper, and the other six targets match the paper exactly. It is not treated as a scientific defect.
- **Tooling.** TeX Live 2023 was installed in the environment, the manuscript was compiled with pdfLaTeX and BibTeX, and every page was rendered and inspected at 100 dpi. Defects were re-inspected at 150–250 dpi.
- **Verification limits.** Direct web fetching was blocked by the environment. Reference verification relied on search results that quote primary pages (ACL Anthology, publishers, AAAI OJS, IJCAI, OpenAI). Items that could not be tied to a primary source are marked UNVERIFIED.

Severity levels are P0 (critical), P1 (major), P2 (moderate) and P3 (minor). Each finding is classified as VERIFIED ISSUE, LIKELY ISSUE, EDITORIAL IMPROVEMENT, AUTHOR ACTION REQUIRED, or KNOWN ACCEPTED EXCEPTION.

## Baseline impression

The manuscript was already carefully revised before this review. Its claims are hedged, the limitations are candid, and its controls are well motivated. No P0 defect was found. The main weaknesses were:

1. **Production.** The shipped PDF was built with an engine other than the one the class option declares, which degraded caption typography.
2. **Typography.** Table and figure typography was below the template specification.
3. **One undisclosed confound.** The random-clustering control has an asymmetry in how training and test posts are assigned to clusters.
4. **Informal definitions.** Some quantities used in the method were described only in words.
5. **Bibliography.** A handful of entries had errors or were out of date.

---

## Reviewer 1: Scientific rigour and methodology

**Overall.** The framing is sound. The paper asks a narrow, testable question (does an explicit, unsupervised, target-specific partition help a matched classifier?), answers it with a matched ablation and a strategy control, and limits its conclusions to what those controls show.

### R1-01 · P1 · VERIFIED ISSUE · Confound in the random-clustering control was not disclosed (§5.3, §6.2)

**Evidence.** Under K-means, Eq. (11) reproduces the training assignments (§4.7: "*c_i = k\*(x_i)*"). Under random assignment it does not. Training posts keep their random index, while each test post receives the index of its nearest random centroid. The control therefore changes two things at once: the partition, and the agreement between training-time and test-time cluster indices. The manuscript attributed the whole drop to "how the clusters are formed". That is still a valid description of the control, but the mechanism is confounded.

**Correction.** §6.2 now explains the asymmetry and states that the control does not separate the two effects. §7.3 (*Statistical evaluation*) proposes the fix: route the training posts with the same nearest-centroid rule. No number or conclusion changed. The abstract's factual statement ("lowers the scores by 15.1 and 11.2 points") remains correct.

**Status.** Fixed (disclosed). Confidence: high.

### R1-02 · P2 · EDITORIAL IMPROVEMENT · Clustering objective and model-selection rule were not defined formally (§4.4)

**Evidence.** The K-means objective, the centroid definition and the silhouette-based choice of *K_T* were given only in prose. A reviewer cannot tell from the text whether the silhouette is averaged over posts or over clusters, or which distance it uses.

**Correction.** The K-means objective and centroid are now stated inline. A new Eq. (8) defines *K_T* = argmax over *K* of the mean cosine silhouette, with per-post terms *s_i*, *a_i* and *b_i* defined. The equation matches the implementation's documented rule (cosine silhouette over training posts).

**Status.** Fixed.

### R1-03 · P2 · VERIFIED ISSUE · Notation gaps (§3, §4.3, §5.2)

**Evidence.** Several symbols were used without definition:
- *N_T* was never introduced.
- *E(·)* was not identified with the embedding model.
- The concatenation operator [·;·] was undefined.
- The dimensions of *e* and *r* were implicit.
- *F*-macro_T had no formula.

**Correction.** Each symbol is now defined where it first appears. Eq. (5) now states dimensions and Eq. (6) defines concatenation. §5.2 gives *F*-macro_T = |𝒯|⁻¹ Σ_T *F1*_avg(T).

**Status.** Fixed.

### R1-04 · P2 · VERIFIED ISSUE · §7.1 promised more than the proposed controls can deliver

**Evidence.** The original text said that an enrichment-free variant and a per-member ablation "would quantify the share of each effect". Neither experiment isolates the *geometry-aligned groups* mechanism. The text also stated as fact that "stance is expressed differently" across clusters, which was not tested.

**Correction.** The section now says the present controls do not apportion the gain among the three mechanisms. It names the experiments that would help, adding a random partition matched to the K-means cluster sizes. "is expressed" is now "may be expressed".

**Status.** Fixed.

### R1-05 · P3 · EDITORIAL IMPROVEMENT · Feature-based methods framed as historical (§2.1)

**Evidence.** "Early stance detectors represented…" presented the feature-based approach as purely historical.

**Correction.** Rephrased to the present tense ("Feature-based stance detectors represent…").

**Status.** Fixed.

### Remaining limitations, not correctable without new experiments (already disclosed in §7.3)

- No significance tests across test posts.
- Glosses were generated once, so variation in the language model's outputs is not sampled.
- No enrichment-free variant.
- Library defaults were used throughout.
- Possible contamination of *GPT-6 Luna* with the benchmarks was not tested.

Disclosure is adequate. No experiments were requested.

---

## Reviewer 2: Results interpretation and technical consistency

### R2-01 · VERIFIED: internal arithmetic is consistent (no correction needed)

All checks were made on reported values only.

- **Table 3, P-Stance means.** (91.6+90.9+89.9)/3 = 90.80 and (82.1+80.7+79.3)/3 = 80.70, giving Δ = 10.1 ✓.
- **Table 3, SemEval-2016 means.** (88.9+87.4+85.9+84.2+80.2)/5 = 85.32 → 85.3, and the Base mean = 69.60. The mean of the per-target Δ is 15.72 → 15.7 ✓.
- **Per-target Δ.** Every per-target Δ equals AspectStance − Base exactly. The ranges are 9.5–10.6 (spread 1.1) and 14.7–16.3 (spread 1.6) ✓.
- **Table 4.** 90.8 − 75.7 = 15.1 and 85.3 − 74.1 = 11.2. Against the Base Method the random control is −5.0 on P-Stance and +4.5 on SemEval-2016 ✓.
- **Tables 5 and 6, cluster sizes.** For all eight targets the cluster sizes sum exactly to the training totals of Table 2 (6,362; 5,806; 5,056; 513; 395; 664; 689; 653). Every share matches *n*/*N* to ±0.05. The clusters total 63, and every list is sorted by size ✓.
- **Prose claims.** All checked against the tables:
  - 496/664 posts in the largest Feminist Movement cluster.
  - 39 % / 75 % largest-cluster shares.
  - 583 vs 5,741 mean training posts per target (ratio 0.10, "about one tenth").
  - 85.8 on the three KASD targets: (85.9+84.2+87.4)/3 = 85.83.
  - Spans 1.7 and 8.7.
  - The 5.6-point benchmark gap.
  - 11 vs 123 Climate Change test posts.
  - 169–295 test posts per target ✓.
- **Gloss lengths.** The claim "two of the seven glosses contain 59 words" was verified by counting (59, 59, 47, 48, 48, 46, 49) ✓.
- **Figure 3.** The bar labels, extracted from the vector PDF (90.8, 80.7, 83.2, 81.4 / 85.3, 69.6, 74.9, 72.4), match the text ✓.
- **Abstract, Introduction and Conclusion.** Every number in them matches the Results ✓.

### R2-02 · P2 · VERIFIED ISSUE · Table 7 caption misstated MPRF's metric

**Evidence.** The caption said all scores are target-averaged *F1*_avg except the topic-guided transformer's. MPRF actually reports "F macro" (88.41). On binary P-Stance this coincides with *F1*_avg on each target, but the paper should say so instead of asserting identity.

**Correction.** The caption and §6.4 now name MPRF's metric and explain why it is comparable.

**Status.** Fixed.

### R2-03 · P2 · VERIFIED ISSUE · BERTweet scores were not attributed to their source

**Evidence.** The BERTweet scores (82.1 and 63.6) are KASD's re-run. The original P-Stance paper reports 80.5 for BERTweet. Citing only BERTweet's own paper implies the scores come from there.

**Correction.** Attributed to KASD in the Table 7 caption and in §6.4.

**Status.** Fixed.

### R2-04 · P3 · EDITORIAL IMPROVEMENT · Margin over the strongest prompting baseline was not stated (§6.1)

**Correction.** Added: AspectStance exceeds the few-shot baseline by 7.6 and 10.4 points. These are derived arithmetically from 90.8 − 83.2 and 85.3 − 74.9. Both are within-study comparisons, and the sentence that follows already qualifies the different supervision regimes.

**Status.** Fixed.

### R2-05 · P2 · VERIFIED ISSUE · Abstract overstated the qualitative finding

**Evidence.** The abstract said "the discovered aspects match recognisable subtopics". §6.3 itself says *most* clusters correspond to subtopics: five of eight largest clusters are named as broad or miscellaneous, and 12 of 63 names describe stance orientation.

**Correction.** Now reads "Most discovered aspects correspond to recognisable subtopics, such as impeachment or abortion legislation". The inductive-bias sentence is hedged to "the results indicate that…", in line with §8.

**Status.** Fixed.

### R2-06 · Published scores checked against KASD's Table 4 (via search snippets of the primary paper)

| System | Per-target scores | Average | Manuscript |
|---|---|---|---|
| KASD-BERT, P-Stance | 85.66 / 80.39 / 85.35 | 83.80 | 83.8 ✓ |
| KASD-ChatGPT, P-Stance | 84.59 / 79.96 / 85.06 | 83.20 | 83.2 ✓ |
| BERTweet, P-Stance | 82.90 / 79.00 / 84.41 | 82.10 | 82.1 ✓ |
| KASD-BERT, SemEval HC / FM / LA | 77.60 / 70.38 / 72.29 | 73.42 | 73.4 ✓ |
| KASD-ChatGPT, SemEval HC / FM / LA | 80.92 / 70.37 / 63.26 | 71.52 | 71.5 ✓ |
| BERTweet, SemEval HC / FM / LA | 62.31 / 64.20 / 64.14 | 63.55 | 63.6 ✓ (round-half-up) |

Other published scores:
- **MPRF 88.41 → 88.4** ✓. The paper's text confirms it.
- **Topic-guided transformer 78.4 macro-F1** ✓. Its abstract confirms it.
- **CKD 82.0.** Supported only by two secondary reprints (82.05 and 81.97). CKD's own table was not retrieved: AUTHOR ACTION.
- **MPVStance 82.2 (six-target mean).** The per-target values could not be retrieved: AUTHOR ACTION.

---

## Reviewer 3: Academic English, grammar and style

**Overall.** The prose is precise, restrained and mostly idiomatic. It avoids promotional language. Editing was deliberately light; correct sentences were not rewritten.

| ID | Sev. | Location | Issue | Correction |
|---|---|---|---|---|
| R3-01 | P2 | Abstract | Terminology drift between "input text", "text" and "post" for the same object; "Over ten seeded runs" | Standardised on "post"; "Averaged over ten seeded runs" |
| R3-02 | P2 | §8 ¶2 | "is a useful inductive bias for this classifier, more than an interpretability layer added after…" is a dangling comparative | "acts as a useful inductive bias … rather than only as an interpretability layer …" |
| R3-03 | P3 | §2.2 | "Cross-target and zero-shot research studies transfer…" could parse "studies" as a noun | "Cross-target and zero-shot studies examine transfer…" |
| R3-04 | P3 | §4.2 | Semicolon chain packing two claims into one sentence | Split into two sentences |
| R3-05 | P3 | §6.2, §6.4 | Two-sentence invariance-check statement; redundant "Like …, KASD also …" | Merged; "also" removed |
| R3-06 | P3 | §5.3, §6.1, App. A | "SemEval-2016 Task 6" used after "hereafter SemEval-2016" was defined | Abbreviation applied consistently after its definition |
| R3-07 | P3 | §8 ¶2 | "linking the prediction to the part of the target's discourse it concerns" overstates what a cluster is | "links the prediction to a recurring region of the target's discourse" (matches §4.4's own definition) |

**Spelling.** British spelling (normalise, recognise, labelled, modelling) is consistent across the authors' prose. US spellings appear only in text reproduced verbatim: the prompts in Appendix A, which the paper itself notes, and the model-generated aspect names in Tables 5 and 6. Those were deliberately left as they are.

---

## Reviewer 4: Structure, argumentation and coherence

**Overall.** The architecture is strong. RQ1–RQ4 are posed in §1 and answered in order, the positioning table makes the novelty claim checkable, and the Discussion is clearly separate from the Results.

### R4-01 · P2 · EDITORIAL IMPROVEMENT · Contributions were packed into a dense paragraph (§1)

**Correction.** The three contributions are now an enumerated list, which is the norm for Q1 venues. The wording is otherwise preserved.

### R4-02 · P2 · VERIFIED ISSUE · Floats appeared far from their first mention

**Evidence.** In the source, Tables 5–9 were defined after later subsections. Positions measured in the shipped PDF:

| Table | First mention | Float |
|---|---|---|
| Table 5 | p. 11 | p. 13 |
| Table 7 | p. 12 | p. 15 |

**Correction.** The float definitions for Tables 2 and 5–9 were moved next to their first substantive mention; the numbering is unchanged. Positions in the revised PDF:

| Float | First mention | Float |
|---|---|---|
| Table 2 | p. 7 | p. 8 |
| Table 5 | p. 12 | p. 12 |
| Table 7 | p. 14 | p. 14 |
| Tables 8–9 | p. 14 | p. 15 (shared float page directly before the Discussion) |

**Status.** Fixed. A line-set comparison confirmed that no content changed.

### R4-03 · P2 · EDITORIAL IMPROVEMENT · Redundant closing paragraph in §6.4

**Evidence.** The paragraph opened "For SemEval-2016, Table 7 records the metric…", which repeated the first paragraph, while its "highest value" claim actually applied to both benchmarks.

**Correction.** It now reads: "On both benchmarks, AspectStance has the highest score in Table 7, but no row is a controlled comparison … The evidence for cluster conditioning therefore rests on the controlled ablations…".

### R4-04 · P3 · EDITORIAL IMPROVEMENT · §6.4 heading wrapped to two lines

**Correction.** The heading "Comparison with published systems" wrapped in the narrow column, so it is now "Comparison with prior work".

### Considered and rejected

Large-scale reorganisation was considered and rejected. The section order is conventional and logically sound, and moving material would add risk without benefit.

---

## Reviewer 5: References, scholarly standards and positioning

### Corrections applied

| ID | Sev. | Entry | Issue | Correction |
|---|---|---|---|---|
| R5-01 | P2 | `deraedt2023idas` | `Fr{'e}deric` (missing backslash) printed a literal apostrophe | `Fr{\'e}deric` |
| R5-02 | P2 | `cheng2024cosd` | Cited as an arXiv preprint, but now published | *Knowledge-Based Systems* 317 (2025) 113399, doi:10.1016/j.knosys.2025.113399 |
| R5-03 | P3 | `ma2024chain` | Generic booktitle; no volume or DOI | NLPCC 2024, LNCS 15363, pp. 82–94, doi:10.1007/978-981-97-9443-0_7 |
| R5-04 | P3 | `du2017tan` | Official IJCAI title has no "Networks"; no DOI | Title corrected; doi:10.24963/ijcai.2017/557 |
| R5-05 | P3 | `coates2012kmeans` | No DOI | doi:10.1007/978-3-642-35289-8_30 |
| R5-06 | P3 | `allahgholi2025conspro` | Journal name abbreviated informally | "Journal of Artificial Intelligence and Data Mining" |
| R5-07 | P2 | §1 ¶2 | "Topic-aware stance methods approximate this missing layer in several ways" had no citation | Cites [7–10] (Gómez-Suta et al., KASD, CoSD, topic-guided transformer) |

### Verified entries

The following were confirmed against primary sources (search snippets):
- MPRF and MPVStance (pages, DOIs, authors)
- MSME and Induce–Align–Predict (AAAI 2026, 40(41))
- the SemEval-2026 DimABSA proceedings entry
- the OpenAI "Introducing GPT-6 Sol and Luna" page and the API identifier `gpt-6-luna`
- the four MDPI/Springer journal articles
- *Time Travel in LLMs* (ICLR 2024)
- KASD, CKD (bibliographic entry), Sucu et al., Gambini et al., Gera & Neal

### UNVERIFIED (author actions)

- The ConSPro DOI: likely `10.22044/jadm.2025.15250.2629`, not independently resolved, so not added.
- The DimABSA DOI: it follows the Anthology pattern but was not confirmed.
- The 4th author of `pu2025integrating`: "Jieyao Wei" vs "Jie Wei".
- The issue year of `gera2025deep`: online 2025; the issue may be dated 2026.

### Positioning

Positioning is strong:
- Table 1 contrasts the method with KASD, CoSD and the topic-guided transformer on six concrete design axes.
- §2.4 concedes the closest precedents explicitly ("Target-specific topic induction and a data-driven rule for inventory size already exist in this literature, most clearly in KASD"), which pre-empts a common reviewer objection.
- The novelty claim is correctly narrowed to the combination of three things: a target-conditioned second view, a silhouette-selected inventory, and a returned conditioning feature.

---

## Reviewer 6: Visual design, typography and presentation

All 22 pages of the shipped PDF and all 23 pages of the revised PDF were rendered and inspected. Before and after images are in `visual_qa/`.

### R6-01 · P1 · VERIFIED ISSUE · Caption leading wrong in the shipped PDF

**Evidence.** The shipped PDF was produced by XeLaTeX (`xdvipdfmx`), although the class option is `pdflatex`. Measured on the PDF, figure captions are 8 pt type set on 12.7–13.7 pt leading (Fig. 1, Fig. 2), against the class's 9.5 pt. The result is visibly double-spaced captions.

**Correction.** The document is built with pdfLaTeX (instructions are in the source header). Caption leading is now a uniform 9.5 pt.

**Evidence image.** `visual_qa/fig1_caption_leading.png`.

### R6-02 · P2 · VERIFIED ISSUE · Table text below the template specification

**Evidence.** Tables used `\footnotesize`, which `sn-jnl` redefines to 7 pt. The template's table body font is 8 bp.

**Correction.** All tables now use the class's own `\tablebodyfont` (8 bp/9.5 bp).

### R6-03 · P2 · VERIFIED ISSUE · Standard deviations set at 5.6 pt (Table 3)

**Evidence.** At 5.6 pt the ± values are below comfortable print legibility.

**Correction.** Raised to 6.5 pt, which remains subordinate to the 8 bp means.

**Evidence image.** `visual_qa/table3_layout.png`.

### R6-04 · P2 · VERIFIED ISSUE · Table column layout under pdfLaTeX (Tables 3 and 4)

**Evidence.** In the pdfLaTeX build, "Legalization of Abortion" wrapped in Table 3's flexible `Y` column, and Table 4's fixed-width first column hyphenated "*Aspect-Stance*".

**Correction.** Both tables now use `tabular*` with natural-width label columns. No wrapping or hyphenation remains, and there is no overfull box.

### R6-05 · P3 · VERIFIED ISSUE · Prompt boxes (Figure 2, Appendix A)

**Evidence.** Under pdfLaTeX, `\{` and `\}` inside `\ttfamily` fell back to math-symbol braces, and the log reported "Font shape OMS/cmtt/m/n undefined". Figure 2 also used `\\` followed by a blank line, which left an oversized gap, and justified monospace text stretched inter-word spaces.

**Correction.** Braces now come from the typewriter font, paragraph spacing is consistent across all four prompt boxes, and the text is ragged-right.

**Evidence image.** `visual_qa/fig2_prompt_braces.png`.

### R6-06 · P2 · VERIFIED ISSUE · Floats crowded the text

**Evidence.** Float-to-text separation was set to 6 pt (the class default is 15–20 pt), so table rules nearly touched body text.

**Correction.** Separation is restored to 10–12 pt. The duplicated settings and the display-skip overrides that the class silently discarded were removed.

### R6-07 · P3 · VERIFIED ISSUE · Share bars overran the table rule (Tables 5 and 6)

**Evidence.** The bar column had natural width, so the longest bar (74.7 %) protruded past the bottom rule.

**Correction.** The column now has a fixed 1.75 cm width, and every bar sits within the table's rules.

### R6-08 · P3 · VERIFIED ISSUE · Gapped shading in Table 3's average rows

**Evidence.** The average-row shading had white gaps between cells.

**Correction.** Shading removed. A `\cmidrule` already separates those rows, which is consistent with the other tables.

### R6-09 · P2 · VERIFIED ISSUE · Overfull boxes

**Evidence.** There was a 1.24 pt overfull line in §2.4. During revision, a 7.7 pt overfull Table 4 and a 26.5 pt vertical overflow on page 15 also appeared.

**Correction.** All were resolved. The final build has **zero** overfull boxes.

### Figures

- **Figure 1** (workflow) and **Figure 3** (bar chart) are vector PDFs with embedded fonts. Their labels are legible at print size and their colours are consistent with the table accents. They were not regenerated: their source files are not in the archive, and redrawing them would risk altering verified values.
- **Figure 3.** The bar labels match Table 3 and the text.
- **Figure fonts.** The sans-serif figure font (Helvetica/Arial) differs from the Computer Modern body text. This is common practice and was accepted.

---

## Reviewer 7: LaTeX, document engineering and production

| ID | Sev. | Issue | Correction |
|---|---|---|---|
| R7-01 | P1 | Engine mismatch (same root cause as R6-01); no build instructions | Build sequence and the XeLaTeX caveat documented in the source header; verified clean build from the packaged ZIP |
| R7-02 | P3 | Unused packages (`multirow`, `amsthm`, `listings`) and a redundant `\tcbuselibrary` | Removed; the build is unaffected |
| R7-03 | P3 | Float-spacing block duplicated in the preamble and `\AtBeginDocument`; display-skip assignments overwritten by the class's `\normalsize` | Consolidated into one documented block |
| R7-04 | P3 | Misleading internal labels (`subsec62` labelled §6.1, `subsec61` labelled §6.3, …) | Renamed to semantic labels (`sec:main`, `sec:random`, `sec:inventories`, `sec:published`, `sec:qualitative`) |
| R7-05 | P2 | Pre-existing inconsistency: the implementation's README and code docstrings cited Eqs. (6–7), (12), (14), etc., which did not match the shipped paper's numbering (12 equations) | Synchronised with the revised paper (13 equations) in `AspectStance Implementation/README.md` and docstrings; comment-only changes, Python syntax verified, no code executed |
| R7-06 | — | Audit | No undefined references, no duplicate labels, no "??" in the PDF; BibTeX reported 0 warnings |
| R7-07 | — | Residual warnings | 45 underfull `\hbox` warnings (mostly unbreakable DOI URLs in narrow bibliography columns) and one `fixltx2e` notice raised by the journal class itself; no visible defect on inspection; class not modified |

---

## Adversarial cross-review: disputes and resolutions

1. **R6 (visual) vs R2 (results): keep the shaded "Target average" rows?**
   - R6 wanted them removed because of the white gaps between cells. R2 wanted the averages to stay visually prominent.
   - **Resolution:** the shading was removed. Prominence is kept through bold means and a rule above each average row.
2. **R3 (language) vs R2 (results): the abstract was over the 250-word Springer norm (262 words after the first edits).**
   - R3 proposed cutting a results sentence. R2 objected: every number in the abstract is load-bearing.
   - **Resolution:** all numbers were kept and connective phrasing was trimmed instead, bringing the abstract to 250 words on a conservative count.
3. **R1 (rigour) vs R4 (structure): should the confound in R1-01 also qualify the abstract and contribution 2?**
   - **Resolution:** no. The abstract's statement that random clustering "lowers the scores" is a factual description of the reported control. The caveat about mechanism belongs in §6.2 and §7.3, where it was placed.
4. **R5 (references): add ConSPro's likely DOI?**
   - **Resolution:** rejected. The DOI could not be independently resolved, and adding an unverified DOI risks a fabricated identifier. It is listed as an author action.
5. **R6 (visual): regenerate the figures in a serif font to match the body text?**
   - **Resolution:** rejected. The figure sources are not in the archive, and redrawing them risks altering verified results. The current figures are legible vector graphics.
6. **R1 vs R4: soften "useful inductive bias"?**
   - **Resolution:** kept as the paper's thesis. It is supported by two controlled comparisons, and it is now phrased as "the results indicate" in the abstract, consistent with §8.

## Editor-in-Chief: decisions

- **Approved:** every correction listed above.
- **Rejected:**
  - wholesale restructuring
  - figure regeneration
  - adding unverified DOIs
  - any change to tables or reported numbers
  - any edit to the dataset or the stale root `README.md`, whose content only the author can reconcile (see `Remaining_Author_Actions.md`)

## Second-round review (fresh pass on the revised artifact)

Each role re-read the final source and the rendered PDF, which was re-inspected after every reflow.

- **R1.** No new issues. The remaining limitations are experimental and already disclosed.
- **R2.** All tables are numerically identical to the original (verified mechanically, 9 of 9). No prose number was removed. The added numbers (7.6, 10.4) are correct derivations.
- **R3.** No grammatical errors found. A few long sentences remain in §5.3 (Base Method paragraph); they are clear and were deliberately kept.
- **R4.** Every float now lies on the page of its first substantive mention or the next page. The appendix prompt boxes were made unbreakable after the A.1 box was seen splitting across pp. 18–19.
- **R5.** The UNVERIFIED items are carried to the author actions.
- **R6.** All 23 pages are clean: zero overfull boxes, consistent caption leading, columns balanced on body pages.
- **R7.** A clean build from the packaged ZIP reproduces the inspected PDF (identical extracted text).
