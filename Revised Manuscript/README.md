# Revised Manuscript

This folder holds the editorial review and the revised version of `AspectStance_Paper.zip`, which is kept unchanged at the repository root.

| File | Contents |
|---|---|
| `Manuscript_Final_Revised.zip` | Revised LaTeX project: source, bibliography, `.bbl`, class and style files, figures, compiled PDF |
| `Manuscript_Final_Revised.pdf` | Compiled PDF (23 pages) built from that source |
| `Comprehensive_Peer_Review.md` | Seven reviewer reports, cross-review, Editor-in-Chief decisions, second-round review |
| `Editorial_Change_Log.md` | Every substantive change, with its location and rationale |
| `Visual_Quality_Assurance.md` | Visual and typographic audit, with a page-by-page assessment |
| `visual_qa/` | Before/after images |
| `Final_Editorial_Assessment.md` | Quality scores, QA audit and verdict |
| `Remaining_Author_Actions.md` | Items that need the author's decision |

Build with pdfLaTeX:

```
pdflatex AspectStance && bibtex AspectStance && pdflatex AspectStance && pdflatex AspectStance
```

No experiments were rerun, and no reported number was changed.
