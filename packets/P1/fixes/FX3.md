# FX-3: clip-name verification

Listing: `https://huggingface.co/api/datasets/lvhaidong/LAFAN1_Retargeting_Dataset/tree/main/g1` (subdir `g1` from `upstream.dataset_subdir`), fetched 2026-10-25, raw JSON in `fx3-dataset-listing.json` (40 `.csv` entries, single page).

| Config clip | Exists as `g1/<name>.csv` |
|---|---|
| walk1_subject1 | yes |
| run1_subject2 | yes |
| dance1_subject1 | yes |
| jumps1_subject1 | yes |

All 4 verified; none replaced. The "placeholders" comment in `configs/colab_smoke.yaml` was removed (replaced by a pointer to this file).
