# COLI_Q36_PREFILL_GROUPED=1 vs waves alone

A = `gwaves`, B = `grouped`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.
95% CI: bootstrap over runs. **sig** = the interval excludes 0.

## cold|cold-process|long|cap12|pilot0

| metric | gwaves | grouped | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 27.6 ± 1.3 | 26.9 ± 2.1 | -2.8 | [-10.5, +5.5] | n.s. |
| decode tok/s | 0.7 ± 0.14 | 0.606 ± 0.12 | -13.5 | [-33.6, +15.6] | n.s. |
| end-to-end tok/s (engine) | 0.443 ± 0.06 | 0.41 ± 0.062 | -7.5 | [-23.4, +12.5] | n.s. |
| expert hit rate (%) | 94.1 ± 0 | 94.1 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 1.23e+04 ± 0 | 1.23e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.2e+03 ± 1.7e+02 | 1.28e+03 ± 88 | +6.5 | [-8.2, +22.5] | n.s. |
| bytes read by engine (GB) | 34.7 ± 0.038 | 34.8 ± 0.045 | +0.3 | [+0.1, +0.4] | sig WORSE |
| peak RSS (GB) | 3.97 ± 0.0058 | 3.97 ± 0.0058 | +0.0 | [-0.2, +0.2] | n.s. |
| minor page faults | 3.28e+06 ± 5.2e+03 | 3.28e+06 ± 1.7e+04 | +0.1 | [-0.5, +0.5] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|long|cap32|pilot0

| metric | gwaves | grouped | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 49.8 ± 7.3 | 49.9 ± 25 | +0.1 | [-35.6, +57.0] | n.s. |
| decode tok/s | 0.556 ± 0.088 | 0.531 ± 0.057 | -4.5 | [-19.1, +14.8] | n.s. |
| end-to-end tok/s (engine) | 0.3 ± 0.01 | 0.303 ± 0.06 | +1.1 | [-19.1, +18.7] | n.s. |
| expert hit rate (%) | 96 ± 0 | 96 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 8.36e+03 ± 0 | 8.36e+03 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.63e+03 ± 2.7e+02 | 1.42e+03 ± 2.6e+02 | -12.6 | [-30.9, +8.7] | n.s. |
| bytes read by engine (GB) | 25.8 ± 0.19 | 25.8 ± 0.13 | -0.2 | [-1.0, +0.6] | n.s. |
| peak RSS (GB) | 6.34 ± 0 | 6.34 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 3.87e+06 ± 1.3e+04 | 3.87e+06 ± 1.1e+04 | +0.2 | [-0.2, +0.5] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap12|pilot0

| metric | gwaves | grouped | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 19 ± 5.3 | 30.1 ± 7.8 | +58.4 | [+11.4, +126.3] | sig WORSE |
| decode tok/s | 0.703 ± 0.22 | 0.751 ± 0.31 | +6.9 | [-32.0, +63.5] | n.s. |
| end-to-end tok/s (engine) | 0.513 ± 0.14 | 0.427 ± 0.06 | -16.9 | [-37.3, +9.4] | n.s. |
| expert hit rate (%) | 84.8 ± 0 | 84.8 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 1.12e+04 ± 0 | 1.12e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.23e+03 ± 3.1e+02 | 1.18e+03 ± 4.8e+02 | -4.3 | [-45.8, +43.6] | n.s. |
| bytes read by engine (GB) | 32.2 ± 0.095 | 32.1 ± 0.0096 | -0.2 | [-0.4, +0.1] | n.s. |
| peak RSS (GB) | 3.87 ± 0 | 3.87 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 2.56e+06 ± 5.9e+03 | 2.55e+06 ± 4.3e+03 | -0.2 | [-0.5, +0.0] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap32|pilot0

| metric | gwaves | grouped | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 56.7 ± 23 | 56.7 ± 12 | -0.0 | [-30.6, +77.1] | n.s. |
| decode tok/s | 0.8 ± 0.44 | 1.06 ± 0.35 | +32.8 | [-22.2, +144.1] | n.s. |
| end-to-end tok/s (engine) | 0.32 ± 0.062 | 0.363 ± 0.012 | +13.5 | [-1.8, +45.3] | n.s. |
| expert hit rate (%) | 89.9 ± 0 | 89.9 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 7.43e+03 ± 0 | 7.43e+03 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.3e+03 ± 6.2e+02 | 888 ± 3.7e+02 | -31.6 | [-61.3, +38.0] | n.s. |
| bytes read by engine (GB) | 23.4 ± 0.19 | 23.4 ± 0.13 | -0.1 | [-0.9, +0.8] | n.s. |
| peak RSS (GB) | 6.24 ± 0 | 6.24 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 3.16e+06 ± 8.6e+03 | 3.16e+06 ± 3.5e+03 | +0.1 | [-0.1, +0.4] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |
