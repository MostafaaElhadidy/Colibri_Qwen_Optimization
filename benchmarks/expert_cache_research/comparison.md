# COLI_Q36_MISS_QD=8 vs original colibri (cold, PILOT=0, 3 interleaved reps)

A = `baseline`, B = `optimized`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.
95% CI: bootstrap over runs. **sig** = the interval excludes 0.

## cold|cold-process|medium|cap12|pilot0

| metric | baseline | optimized | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 135 ± 2.8 | 74.6 ± 1.6 | -44.6 | [-46.0, -43.1] | sig better |
| decode tok/s | 0.783 ± 0.26 | 1.3 ± 0.17 | +65.8 | [+22.6, +124.3] | sig better |
| end-to-end tok/s (engine) | 0.18 ± 0.01 | 0.323 ± 0.012 | +79.6 | [+69.6, +90.4] | sig better |
| expert hit rate (%) | 45.1 ± 0 | 45.1 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 4.04e+04 ± 0 | 4.04e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.25e+03 ± 3.6e+02 | 640 ± 88 | -48.7 | [-60.3, -25.9] | sig better |
| bytes read by engine (GB) | 102 ± 0.019 | 102 ± 0.03 | -0.2 | [-0.2, -0.1] | sig better |
| peak RSS (GB) | 3.83 ± 0 | 3.85 ± 0 | +0.5 | [+0.5, +0.5] | sig WORSE |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap32|pilot0

| metric | baseline | optimized | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 131 ± 19 | 79.9 ± 11 | -38.8 | [-48.5, -26.3] | sig better |
| decode tok/s | 1.03 ± 0.58 | 1.61 ± 0.84 | +55.8 | [-20.9, +220.7] | n.s. |
| end-to-end tok/s (engine) | 0.197 ± 0.047 | 0.313 ± 0.0058 | +59.3 | [+25.3, +95.8] | sig better |
| expert hit rate (%) | 74.4 ± 0 | 74.4 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 1.88e+04 ± 0 | 1.88e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 989 ± 5.2e+02 | 554 ± 2.3e+02 | -44.0 | [-71.1, +8.6] | n.s. |
| bytes read by engine (GB) | 50.5 ± 0.0078 | 50.5 ± 0.016 | -0.1 | [-0.1, -0.1] | sig better |
| peak RSS (GB) | 6.21 ± 0 | 6.22 ± 0 | +0.2 | [+0.2, +0.2] | sig WORSE |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap12|pilot0

| metric | baseline | optimized | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 52.6 ± 39 | 17 ± 2.2 | -67.6 | [-81.9, -36.7] | sig better |
| decode tok/s | 1.13 ± 0.0053 | 1.57 ± 0.52 | +38.4 | [-12.3, +76.7] | n.s. |
| end-to-end tok/s (engine) | 0.46 ± 0.18 | 0.847 ± 0.14 | +84.1 | [+32.2, +210.3] | sig better |
| expert hit rate (%) | 44.8 ± 0 | 44.8 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 1.17e+04 ± 0 | 1.17e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 812 ± 3 | 589 ± 2.6e+02 | -27.4 | [-51.1, +9.6] | n.s. |
| bytes read by engine (GB) | 32.9 ± 0.019 | 32.8 ± 0.048 | -0.4 | [-0.5, -0.2] | sig better |
| peak RSS (GB) | 3.81 ± 0 | 3.82 ± 0 | +0.3 | [+0.3, +0.3] | sig WORSE |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap32|pilot0

| metric | baseline | optimized | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 59.8 ± 8.2 | 29.3 ± 3.2 | -51.1 | [-57.8, -42.3] | sig better |
| decode tok/s | 0.855 ± 0.55 | 1.01 ± 0.38 | +18.2 | [-32.9, +132.4] | n.s. |
| end-to-end tok/s (engine) | 0.313 ± 0.065 | 0.52 ± 0.079 | +66.0 | [+31.8, +111.1] | sig better |
| expert hit rate (%) | 68.6 ± 0 | 68.6 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 6.63e+03 ± 0 | 6.63e+03 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.35e+03 ± 6.4e+02 | 835 ± 2.5e+02 | -37.9 | [-61.5, +29.2] | n.s. |
| bytes read by engine (GB) | 21 ± 0.0033 | 21 ± 0.012 | -0.1 | [-0.1, -0.0] | sig better |
| peak RSS (GB) | 6.18 ± 0 | 6.2 ± 0 | +0.3 | [+0.3, +0.3] | sig WORSE |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |
