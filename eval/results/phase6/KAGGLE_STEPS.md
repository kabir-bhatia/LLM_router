# Phase 6: Kaggle steps for Kabir

Files (already copied to `C:\Users\Kabir\Downloads`): `phase6_bundle.zip` (code, policies, models, test prompts; no gold, no keys) and `phase6_router_kaggle.ipynb`.

1. **New dataset:** kaggle.com > Datasets > New Dataset, upload `phase6_bundle.zip`, name it `phase6-bundle`, keep it **Private**. (Kaggle unpacks the zip; the notebook finds it by itself.)
2. **New notebook:** File > Import Notebook > `phase6_router_kaggle.ipynb`.
3. **Settings (right panel):** Accelerator **GPU T4 x2**, Internet **On**, Persistence **Files only**.
4. **Add Input:** the `phase6-bundle` dataset.
5. **Add-ons > Secrets**, three secrets, each attached to this notebook (toggle on): `FIREWORKS_API_KEY`, `HYDE_API_KEY`, `HYDE_BASE_URL` (same values as in your local `.env`).
6. **Run All** (or Save Version > Save & Run All for a background run). It installs Ollama, pulls the local models (6 for the main policy, 3 more 12-14B models later for the GPU-server run; about 35 GB in total, so it uses `/kaggle/temp`), then runs: main policy on GPU x3, CPU-deployment check, GPU-server run.
7. **Time:** roughly 2-3 h, mostly unattended (the CPU check is the slowest, ~1 h). It is restart-safe: if the session drops, start it again with the same cells and finished runs are skipped, partial runs resume.
8. **Spend guard:** if Fireworks spend in the notebook passes $1.50 it stops, saves and zips; tell me before re-running anything.
9. **Result:** download `/kaggle/working/phase6_results.zip` (Output panel; also refreshed after every run) and put it in `D:\LLM_Router\eval\results\phase6\`. Then tell me and I run step 5 (grading).

Note: Fireworks cost of the router runs is paid from your key via Kaggle, so it is in addition to the B1/B2 laptop runs (phase cap $3).
