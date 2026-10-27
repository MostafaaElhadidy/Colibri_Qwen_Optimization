# qd8 + both vs COLI_Q36_MISS_QD=8

A = `qd8`, B = `both`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.
95% CI: bootstrap over runs. **sig** = the interval excludes 0.

## cold|cold-process|long|cap12|pilot0

| metric | qd8 | both | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 376 ± 1.1e+02 | 28.6 ± 2.2 | -92.4 | [-94.1, -90.4] | sig better |
| decode tok/s | 0.728 ± 0.13 | 1.34 ± 0.65 | +84.2 | [+10.2, +182.1] | sig better |
| end-to-end tok/s (engine) | 0.08 ± 0.017 | 0.603 ± 0.15 | +654.2 | [+463.0, +905.6] | sig better |
| expert hit rate (%) | 44.2 ± 0 | 94.1 ± 0 | +112.9 | [+112.9, +112.9] | sig better |
| expert misses | 1.17e+05 ± 0 | 1.23e+04 ± 0 | -89.5 | [-89.5, -89.5] | sig better |
| decode expert fetch (ms/token) | 1.23e+03 ± 2.4e+02 | 685 ± 3.6e+02 | -44.1 | [-69.2, -11.9] | sig better |
| bytes read by engine (GB) | 283 ± 0.11 | 34.8 ± 0.051 | -87.7 | [-87.7, -87.7] | sig better |
| peak RSS (GB) | 3.92 ± 0 | 4.06 ± 0 | +3.6 | [+3.6, +3.6] | sig WORSE |
| minor page faults | 3.43e+06 ± 2.1e+04 | 2.89e+06 ± 1.2e+04 | -15.8 | [-16.4, -15.2] | sig better |
| peak VRAM above idle (MiB) | 0.333 ± 0.58 | 0 ± 0 | -100.0 | [-100.0, -100.0] | sig better |

## cold|cold-process|long|cap32|pilot0

| metric | qd8 | both | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 221 ± 44 | 51.3 ± 27 | -76.7 | [-85.7, -62.9] | sig better |
| decode tok/s | 0.672 ± 0.21 | 0.978 ± 0.3 | +45.4 | [-5.6, +113.6] | n.s. |
| end-to-end tok/s (engine) | 0.117 ± 0.015 | 0.42 ± 0.16 | +260.0 | [+111.8, +384.4] | sig better |
| expert hit rate (%) | 72.9 ± 0 | 96 ± 0 | +31.7 | [+31.7, +31.7] | sig better |
| expert misses | 5.67e+04 ± 0 | 8.36e+03 ± 0 | -85.3 | [-85.3, -85.3] | sig better |
| decode expert fetch (ms/token) | 1.23e+03 ± 4.3e+02 | 923 ± 3.7e+02 | -25.2 | [-54.2, +20.8] | n.s. |
| bytes read by engine (GB) | 141 ± 0.054 | 25.7 ± 0.061 | -81.7 | [-81.7, -81.7] | sig better |
| peak RSS (GB) | 6.3 ± 0 | 6.4 ± 0 | +1.6 | [+1.6, +1.6] | sig WORSE |
| minor page faults | 3.96e+06 ± 6.9e+03 | 2.89e+06 ± 2.9e+04 | -27.0 | [-27.5, -26.2] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap12|pilot0

| metric | qd8 | both | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 117 ± 42 | 16 ± 0.87 | -86.4 | [-90.3, -81.1] | sig better |
| decode tok/s | 0.928 ± 0.26 | 0.893 ± 0.22 | -3.8 | [-31.3, +35.5] | n.s. |
| end-to-end tok/s (engine) | 0.223 ± 0.065 | 0.623 ± 0.11 | +179.1 | [+107.5, +289.6] | sig better |
| expert hit rate (%) | 45.1 ± 0 | 84.8 ± 0 | +88.0 | [+88.0, +88.0] | sig better |
| expert misses | 4.04e+04 ± 0 | 1.12e+04 ± 0 | -72.3 | [-72.3, -72.3] | sig better |
| decode expert fetch (ms/token) | 949 ± 3e+02 | 881 ± 2.4e+02 | -7.2 | [-35.4, +41.7] | n.s. |
| bytes read by engine (GB) | 102 ± 0.047 | 32.1 ± 0.0065 | -68.4 | [-68.4, -68.4] | sig better |
| peak RSS (GB) | 3.85 ± 0 | 3.97 ± 0 | +3.1 | [+3.1, +3.1] | sig WORSE |
| minor page faults | 2.6e+06 ± 1.1e+04 | 2.06e+06 ± 6.7e+02 | -20.6 | [-21.0, -20.3] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap32|pilot0

| metric | qd8 | both | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 82.8 ± 18 | 34.3 ± 15 | -58.6 | [-73.4, -37.4] | sig better |
| decode tok/s | 1.17 ± 0.33 | 1.04 ± 0.21 | -11.1 | [-34.6, +22.2] | n.s. |
| end-to-end tok/s (engine) | 0.29 ± 0.03 | 0.513 ± 0.13 | +77.0 | [+34.5, +124.1] | sig better |
| expert hit rate (%) | 74.4 ± 0 | 89.9 ± 0 | +20.8 | [+20.8, +20.8] | sig better |
| expert misses | 1.88e+04 ± 0 | 7.43e+03 ± 0 | -60.6 | [-60.6, -60.6] | sig better |
| decode expert fetch (ms/token) | 684 ± 1.7e+02 | 789 ± 1.1e+02 | +15.3 | [-8.2, +61.3] | n.s. |
| bytes read by engine (GB) | 50.5 ± 0.042 | 23.3 ± 0.034 | -53.8 | [-53.9, -53.7] | sig better |
| peak RSS (GB) | 6.22 ± 0 | 6.32 ± 0.0058 | +1.6 | [+1.4, +1.6] | sig WORSE |
| minor page faults | 3.18e+06 ± 6.9e+03 | 2.07e+06 ± 1.8e+04 | -34.9 | [-35.4, -34.3] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap12|pilot0

| metric | qd8 | both | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 24.3 ± 11 | 8.37 ± 0.4 | -65.5 | [-76.7, -49.1] | sig better |
| decode tok/s | 1.28 ± 0.67 | 1.43 ± 0.59 | +11.9 | [-39.6, +134.3] | n.s. |
| end-to-end tok/s (engine) | 0.683 ± 0.28 | 1.05 ± 0.33 | +53.7 | [-3.1, +170.6] | n.s. |
| expert hit rate (%) | 44.8 ± 0 | 55.6 ± 0 | +24.1 | [+24.1, +24.1] | sig better |
| expert misses | 1.17e+04 ± 0 | 9.38e+03 ± 0 | -19.6 | [-19.6, -19.6] | sig better |
| decode expert fetch (ms/token) | 811 ± 5e+02 | 676 ± 3.4e+02 | -16.6 | [-59.6, +82.7] | n.s. |
| bytes read by engine (GB) | 32.9 ± 0.029 | 27.6 ± 0.06 | -16.2 | [-16.4, -16.0] | sig better |
| peak RSS (GB) | 3.82 ± 0 | 3.92 ± 0 | +2.6 | [+2.6, +2.6] | sig WORSE |
| minor page faults | 2.44e+06 ± 6e+02 | 2.04e+06 ± 1e+02 | -16.3 | [-16.3, -16.3] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap32|pilot0

| metric | qd8 | both | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 40.8 ± 18 | 22.4 ± 4 | -45.2 | [-61.9, +3.6] | n.s. |
| decode tok/s | 0.684 ± 0.1 | 0.888 ± 0.23 | +29.9 | [-0.7, +68.9] | n.s. |
| end-to-end tok/s (engine) | 0.383 ± 0.091 | 0.557 ± 0.085 | +45.2 | [+12.8, +89.7] | sig better |
| expert hit rate (%) | 68.6 ± 0 | 70.2 ± 0 | +2.3 | [+2.3, +2.3] | sig better |
| expert misses | 6.63e+03 ± 0 | 6.29e+03 ± 0 | -5.1 | [-5.1, -5.1] | sig better |
| decode expert fetch (ms/token) | 1.11e+03 ± 1.9e+02 | 933 ± 2.1e+02 | -16.2 | [-36.5, +5.9] | n.s. |
| bytes read by engine (GB) | 21 ± 0.014 | 20.3 ± 0.083 | -3.4 | [-3.7, -3.0] | sig better |
| peak RSS (GB) | 6.2 ± 0 | 6.27 ± 0.0058 | +1.1 | [+1.0, +1.1] | sig WORSE |
| minor page faults | 3.05e+06 ± 1.1e+03 | 2.06e+06 ± 1.1e+04 | -32.4 | [-32.7, -32.0] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |
