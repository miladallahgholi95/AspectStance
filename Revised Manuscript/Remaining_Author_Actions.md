# Remaining Author Actions

This list contains only items that need the author's knowledge or decision. Nothing here asks for experiments to be rerun.

## Before submission

### A-01 · Known exception: upload the complete dataset to GitHub

The author will update the GitHub repository with the complete dataset before final release. No further action is needed from this review.

### A-02 · Reconcile the repository's root `README.md` with the manuscript (high priority)

The paper's Code-availability statement sends reviewers to this repository, and its root `README.md` currently contradicts the manuscript on several points:

| Root `README.md` says | Manuscript says |
|---|---|
| Glosses and names from OpenAI **`o4-mini`** | **GPT-6 Luna** (`gpt-6-luna`) |
| "Results are from a **single run**. No variability across seeds" | Ten seeded runs with across-run standard deviations |
| "per-target scores for the ablation are **not available**" | Table 3 reports per-target ablation scores |
| "K-Means under cosine similarity (**spherical** K-Means)" | Euclidean K-means on normalised inputs, explicitly "rather than spherical K-means" (§4.4) |
| "No hyperparameter search … **All components run at library defaults**" | UMAP `n_components` and `metric` depart from the defaults (§5.4) |
| SemEval-2016 result **85.31**; "Tables 4 and 5" for the inventories | 85.3; Tables 5 and 6 |
| Title "*Aspect-Oriented Stance Detection through Target-Specific Fine-Grained Clustering*" | "*AspectStance: Unsupervised Discovery of Target-Specific Aspects for Stance Detection*" |
| Lists a `Datasets/` folder | The folder is not present in the repository |

**Action.** Only the author knows which model and protocol were actually used, so this review did not edit the root README. Update it to match the manuscript; the `AspectStance Implementation/README.md` already does. A reviewer who finds `o4-mini` in the README and GPT-6 Luna in the paper will raise a reproducibility concern.

### A-03 · Redistribution of tweet text (decision needed)

The released files in `Clustering Results (Aspects)/` contain the full **tweet text** of the training posts (the `Tweet` column).

**Change already made.** The original Ethics statement said "Tweet texts are not redistributed", which contradicted the repository, so that sentence was removed. The Data-availability statement now says that the aspect assignments are released in the code repository.

**Decide one of the following:**
- **(a)** Confirm that the P-Stance and SemEval-2016 licences, and the X/Twitter developer terms, allow text redistribution.
- **(b)** Replace the text in the released files with post IDs. After doing so, you may restore the sentence "Tweet texts are not redistributed" to the Ethics statement.

### A-04 · Verify two published scores against the primary papers

| Score | Status | What to check |
|---|---|---|
| **MPVStance 82.2** (Table 7, SemEval-2016) | Stated in the paper as the mean of six per-target scores; the per-target values could not be retrieved | Recompute from Table 1 of Zhang et al. (ACL 2025, https://aclanthology.org/2025.acl-long.53.pdf) and confirm which backbone row was used |
| **CKD 82.0** (Table 7, P-Stance) | Two secondary sources reprint CKD's P-Stance average as 82.05 and 81.97 (both round to 82.0); CKD's own table was not retrieved | Confirm against https://aclanthology.org/2023.findings-acl.393.pdf |

**Optional.** Confirm whether MPRF's P-Stance evaluation is in-target or zero-shot (https://aclanthology.org/2025.emnlp-main.24.pdf). The manuscript's current wording ("rather than a classifier trained for each target") holds in either case.

### A-05 · Bibliographic details that could not be independently resolved

- **`allahgholi2025conspro`.** Add the DOI if it resolves. It is likely `10.22044/jadm.2025.15250.2629`, but this was not confirmed.
- **`yu2026dimabsa`.** Confirm the DOI `10.18653/v1/2026.semeval-1.452` on the ACL Anthology page.
- **`pu2025integrating`.** The fourth author appears as "Jieyao Wei" in one source and "Jie Wei" in another. Check the MDPI page.
- **`gera2025deep`.** Published online in 2025 as Article 26 of vol. 58(1); the issue may be dated 2026. Consider adding `articleno = 26`.

## At submission

### A-06 · Journal-specific settings

- **Target journal.** It is not named in the source. Confirm that the reference style option (`sn-mathphys-num`) and the two-column layout (`iicol`) match its instructions. Many Springer Nature journals ask for single-column review manuscripts: delete `iicol` if so (the source header explains this).
- **Abstract length.** The abstract is now 250 words on a conservative count. Check the journal's limit.
- **Nature Portfolio journals using eJP.** These require the reference list to be pasted into the `.tex` file. The template comment explains how; the `.bbl` file is included in the ZIP for this purpose.

### A-07 · Build with pdfLaTeX

Compile as documented in the source header:

```
pdflatex → bibtex → pdflatex → pdflatex
```

The shipped PDF was produced with XeLaTeX, which mis-sets caption leading in this class.

## Optional strengthening (no action required for submission)

These are already disclosed as limitations. Each would require new experiments, which were out of scope for this review:

- a random-clustering control that routes the training posts with the same nearest-centroid rule (§6.2, §7.3)
- a random partition matched to the K-means cluster sizes (§7.1)
- an enrichment-free variant and a per-member ablation (§7.1, §7.3)
- paired significance tests over test posts (§7.3)
