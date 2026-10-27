# qd8 + waves vs COLI_Q36_MISS_QD=8

A = `qd8`, B = `waves`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.
95% CI: bootstrap over runs. **sig** = the interval excludes 0.

## cold|cold-process|long|cap12|pilot0

| metric | qd8 | waves | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 376 ± 1.1e+02 | 30 ± 3.5 | -92.0 | [-94.0, -89.7] | sig better |
| decode tok/s | 0.728 ± 0.13 | 1.08 ± 0.39 | +47.7 | [-4.4, +105.1] | n.s. |
| end-to-end tok/s (engine) | 0.08 ± 0.017 | 0.537 ± 0.12 | +570.8 | [+407.4, +794.4] | sig better |
| expert hit rate (%) | 44.2 ± 0 | 94.1 ± 0 | +112.9 | [+112.9, +112.9] | sig better |
| expert misses | 1.17e+05 ± 0 | 1.23e+04 ± 0 | -89.5 | [-89.5, -89.5] | sig better |
| decode expert fetch (ms/token) | 1.23e+03 ± 2.4e+02 | 775 ± 3e+02 | -36.8 | [-57.6, -9.9] | sig better |
| bytes read by engine (GB) | 283 ± 0.11 | 34.8 ± 0.034 | -87.7 | [-87.7, -87.7] | sig better |
| peak RSS (GB) | 3.92 ± 0 | 3.96 ± 0.0058 | +1.1 | [+1.0, +1.3] | sig WORSE |
| minor page faults | 3.43e+06 ± 2.1e+04 | 3.28e+06 ± 1.2e+04 | -4.3 | [-4.8, -3.6] | sig better |
| peak VRAM above idle (MiB) | 0.333 ± 0.58 | 0 ± 0 | -100.0 | [-100.0, -100.0] | sig better |

## cold|cold-process|long|cap32|pilot0

| metric | qd8 | waves | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 221 ± 44 | 47 ± 15 | -78.7 | [-84.8, -70.8] | sig better |
| decode tok/s | 0.672 ± 0.21 | 0.619 ± 0.11 | -7.9 | [-31.8, +27.6] | n.s. |
| end-to-end tok/s (engine) | 0.117 ± 0.015 | 0.333 ± 0.06 | +185.7 | [+131.4, +250.0] | sig better |
| expert hit rate (%) | 72.9 ± 0 | 96 ± 0 | +31.7 | [+31.7, +31.7] | sig better |
| expert misses | 5.67e+04 ± 0 | 8.36e+03 ± 0 | -85.3 | [-85.3, -85.3] | sig better |
| decode expert fetch (ms/token) | 1.23e+03 ± 4.3e+02 | 1.4e+03 ± 2.7e+02 | +13.3 | [-17.9, +63.8] | n.s. |
| bytes read by engine (GB) | 141 ± 0.054 | 25.8 ± 0.25 | -81.7 | [-81.8, -81.5] | sig better |
| peak RSS (GB) | 6.3 ± 0 | 6.34 ± 0 | +0.6 | [+0.6, +0.6] | sig WORSE |
| minor page faults | 3.96e+06 ± 6.9e+03 | 3.87e+06 ± 1.3e+04 | -2.3 | [-2.7, -2.1] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap12|pilot0

| metric | qd8 | waves | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 117 ± 42 | 18 ± 3.7 | -84.6 | [-89.2, -77.3] | sig better |
| decode tok/s | 0.928 ± 0.26 | 1.4 ± 0.73 | +50.6 | [-28.7, +146.0] | n.s. |
| end-to-end tok/s (engine) | 0.223 ± 0.065 | 0.787 ± 0.33 | +252.2 | [+101.5, +452.1] | sig better |
| expert hit rate (%) | 45.1 ± 0 | 84.8 ± 0 | +88.0 | [+88.0, +88.0] | sig better |
| expert misses | 4.04e+04 ± 0 | 1.12e+04 ± 0 | -72.3 | [-72.3, -72.3] | sig better |
| decode expert fetch (ms/token) | 949 ± 3e+02 | 753 ± 5.5e+02 | -20.7 | [-63.6, +45.4] | n.s. |
| bytes read by engine (GB) | 102 ± 0.047 | 32.2 ± 0.065 | -68.3 | [-68.4, -68.2] | sig better |
| peak RSS (GB) | 3.85 ± 0 | 3.87 ± 0 | +0.5 | [+0.5, +0.5] | sig WORSE |
| minor page faults | 2.6e+06 ± 1.1e+04 | 2.55e+06 ± 6.9e+03 | -1.8 | [-2.2, -1.3] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap32|pilot0

| metric | qd8 | waves | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 82.8 ± 18 | 27.2 ± 4.9 | -67.2 | [-74.3, -57.6] | sig better |
| decode tok/s | 1.17 ± 0.33 | 0.839 ± 0.2 | -28.4 | [-48.4, -0.8] | sig WORSE |
| end-to-end tok/s (engine) | 0.29 ± 0.03 | 0.5 ± 0.1 | +72.4 | [+35.4, +109.9] | sig better |
| expert hit rate (%) | 74.4 ± 0 | 89.9 ± 0 | +20.8 | [+20.8, +20.8] | sig better |
| expert misses | 1.88e+04 ± 0 | 7.43e+03 ± 0 | -60.6 | [-60.6, -60.6] | sig better |
| decode expert fetch (ms/token) | 684 ± 1.7e+02 | 875 ± 2.9e+02 | +27.9 | [-11.0, +80.9] | n.s. |
| bytes read by engine (GB) | 50.5 ± 0.042 | 23.3 ± 0.11 | -53.8 | [-54.0, -53.6] | sig better |
| peak RSS (GB) | 6.22 ± 0 | 6.24 ± 0 | +0.3 | [+0.3, +0.3] | sig WORSE |
| minor page faults | 3.18e+06 ± 6.9e+03 | 3.16e+06 ± 4.7e+03 | -0.8 | [-1.0, -0.5] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap12|pilot0

| metric | qd8 | waves | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 24.3 ± 11 | 8.98 ± 1.4 | -63.0 | [-75.4, -43.9] | sig better |
| decode tok/s | 1.28 ± 0.67 | 1.53 ± 0.72 | +19.7 | [-44.2, +146.3] | n.s. |
| end-to-end tok/s (engine) | 0.683 ± 0.28 | 1.08 ± 0.43 | +57.6 | [-12.2, +180.4] | n.s. |
| expert hit rate (%) | 44.8 ± 0 | 55.6 ± 0 | +24.1 | [+24.1, +24.1] | sig better |
| expert misses | 1.17e+04 ± 0 | 9.38e+03 ± 0 | -19.6 | [-19.6, -19.6] | sig better |
| decode expert fetch (ms/token) | 811 ± 5e+02 | 673 ± 4.5e+02 | -17.0 | [-63.4, +92.0] | n.s. |
| bytes read by engine (GB) | 32.9 ± 0.029 | 27.6 ± 0.023 | -16.2 | [-16.3, -16.1] | sig better |
| peak RSS (GB) | 3.82 ± 0 | 3.83 ± 0 | +0.3 | [+0.3, +0.3] | sig WORSE |
| minor page faults | 2.44e+06 ± 6e+02 | 2.43e+06 ± 3e+02 | -0.3 | [-0.3, -0.2] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap32|pilot0

| metric | qd8 | waves | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 40.8 ± 18 | 20.9 ± 6.3 | -48.8 | [-67.7, -6.6] | sig better |
| decode tok/s | 0.684 ± 0.1 | 0.583 ± 0.1 | -14.8 | [-31.0, +5.1] | n.s. |
| end-to-end tok/s (engine) | 0.383 ± 0.091 | 0.43 ± 0.062 | +12.2 | [-12.0, +45.4] | n.s. |
| expert hit rate (%) | 68.6 ± 0 | 70.2 ± 0 | +2.3 | [+2.3, +2.3] | sig better |
| expert misses | 6.63e+03 ± 0 | 6.29e+03 ± 0 | -5.1 | [-5.1, -5.1] | sig better |
| decode expert fetch (ms/token) | 1.11e+03 ± 1.9e+02 | 1.27e+03 ± 3.2e+02 | +14.0 | [-18.3, +45.4] | n.s. |
| bytes read by engine (GB) | 21 ± 0.014 | 20.3 ± 0.083 | -3.5 | [-3.9, -3.2] | sig better |
| peak RSS (GB) | 6.2 ± 0 | 6.2 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 3.05e+06 ± 1.1e+03 | 3.05e+06 ± 1.9e+03 | -0.1 | [-0.2, -0.0] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |
