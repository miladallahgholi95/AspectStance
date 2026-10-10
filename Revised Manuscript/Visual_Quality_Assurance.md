# Visual Quality Assurance Report

## Method

1. **Rendering.** Every page of the shipped PDF (22 pages) and of each intermediate revised build was rendered at 100 dpi into two-page contact sheets and inspected. Suspected defects were re-rendered at 150–250 dpi.
2. **Measurement.** Typographic quantities were measured from the PDFs with `pdfplumber`:
   - caption line pitch
   - font sizes
   - column bottoms
   - the page each float lands on relative to its first mention
3. **Final pass.** The final PDF (23 pages) was inspected page by page after the last change. Any page that reflowed was inspected again.

All builds use TeX Live 2023 (pdfLaTeX + BibTeX), installed in this environment.

## Baseline (shipped PDF) deficiencies

| Area | Observation | Measured evidence |
|---|---|---|
| Captions | Figure captions visibly double-spaced | 8 pt caption text on 12.7–13.7 pt line pitch (the class specifies 9.5 pt); the PDF producer is `xdvipdfmx`, i.e. XeLaTeX, although the class option is `pdflatex` |
| Table type | All tables smaller than the template specifies | `\footnotesize` = 7 pt in `sn-jnl`; the template's table body font is 8 bp |
| Table 3 | ± values hard to read | 5.6 pt |
| Float spacing | Rules nearly touching body text | `\textfloatsep` = 6 pt (class: 15 pt) |
| Float placement | Tables far from their text | Table 5: mentioned p. 11, set p. 13; Table 7: mentioned p. 12, set p. 15 |
| Lines | One overfull line in §2.4 | 1.24 pt |

The following defects appear only when the original source is compiled with pdfLaTeX, the engine its class option declares. The journal's system will most likely use that engine, so they were fixed:

- **Prompt-box braces.** They fell back to math-font glyphs ("Font shape OMS/cmtt/m/n undefined").
- **Table 3.** "Legalization of Abortion" wrapped onto two lines.
- **Table 4.** "AspectStance" was hyphenated in the first column.

## Corrections and results

| Element | After revision |
|---|---|
| Caption leading | Uniform 9.5 pt on all figure and table captions (see `visual_qa/fig1_caption_leading.png`) |
| Table body | 8 bp/9.5 bp in all nine tables (the class's `\tablebodyfont`) |
| Table 3 | Natural-width label column, no wrapping; ± at 6.5 pt; clean rules, no gapped shading (`visual_qa/table3_layout.png`) |
| Table 4 | No hyphenation, no overfull box; fits the 76 mm column |
| Tables 5–6 | Fixed bar column; the longest bar (74.7 %) now sits within the rules; both inventory tables share identical geometry |
| Table 7 | Rows ordered (ours first, then by score); clearer caption |
| Tables 8–9 | Shared float page (p. 15), directly before the Discussion |
| Prompt boxes | Typewriter braces; ragged-right monospace; identical padding and paragraph spacing in all four boxes; no box splits across pages (`visual_qa/fig2_prompt_braces.png`) |
| Equations | 13 numbered equations; the new Eq. (8) is a two-line `gathered` display with its number vertically centred; no equation exceeds the column |
| Float spacing | 10–12 pt with stretch |
| Float proximity | Every float lies on the page of its first substantive mention or the next page |
| Overfull boxes | 0 horizontal, 0 vertical |

## Page-by-page assessment of the final PDF

| Page | Content | Assessment |
|---|---|---|
| 1 | Title, authors, abstract (250 words), keywords, start of §1 | Clean; abstract block balanced |
| 2 | §1 with numbered contributions, start of §2 | Clean |
| 3–4 | §2.3–2.5, §3, start of §4 | Clean; Eqs. (1)–(3) aligned |
| 5 | Table 1 (page-wide), Fig. 1 (page-wide), §4.2 | Two page-wide floats stacked with clear separation; caption leading correct |
| 6 | Fig. 2 prompt box, §4.3–4.4, Eqs. (4)–(8) | New definitions read cleanly; Eq. (8) number aligned |
| 7 | §4.5–4.7, start of §5 | Left column ends about 4 lines early because display Eq. (10) cannot split and moves to the top of the right column (the template uses `\raggedbottom`); acceptable |
| 8 | Table 2 (page-wide), §5.1–5.3 | Table directly follows its first mention on p. 7 |
| 9 | §5.3–5.4 | Clean |
| 10 | §6, §6.1, Table 3 | Table 3 on its first-mention page |
| 11 | Fig. 3 (page-wide), Table 4, §6.2 | Clean |
| 12 | Table 5 (page-wide), §6.2 end, §6.3 | Table 5 on its first-mention page |
| 13 | Table 6 (page-wide), §6.3 | Clean |
| 14 | Table 7 (page-wide), §6.4, §6.5 | Table 7 on its first-mention page |
| 15 | Tables 8–9 (float page) | Balanced float page |
| 16–17 | §7 Discussion, §7.3 Limitations, §8 | Clean |
| 18 | Declarations, start of Appendix A | The right column ends early because the A.1 box is kept whole on p. 19; preferable to splitting the box |
| 19 | A.1–A.3 prompt boxes, start of References | Clean |
| 20–23 | References | Uniform style; DOIs hyperlinked; no "??" |

## Figures

- **Figure 1 (workflow) and Figure 3 (bar chart).** Both are vector PDFs with embedded fonts. Text remains legible at print size, and the colours match the table accents (#2F6DB5).
- **Figure 3.** The bar labels agree with Table 3 and the text.
- **Figure fonts.** Both figures use a sans-serif font (Helvetica/Arial), which differs from the Computer Modern body text. This is conventional for data graphics.
- **Not regenerated.** The figure sources are not in the archive, and redrawing them could alter verified values.

## Residual items, inspected and accepted

- **45 underfull `\hbox` warnings.** Most come from unbreakable DOI URLs in the narrow two-column bibliography. Visual inspection found no conspicuous gaps beyond normal reference-list raggedness.
- **`fixltx2e` notice.** It is raised by `sn-jnl.cls` itself, which was not modified.

## Areas not visually verifiable here

- **Colour rendition** on a physical printer or on the journal's production system.
- **Output from the journal's own LaTeX engine or version.** The class option requests pdfLaTeX, which is what was used here.
