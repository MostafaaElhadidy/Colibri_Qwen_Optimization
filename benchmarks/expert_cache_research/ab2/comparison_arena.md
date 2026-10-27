# qd8 + arena vs COLI_Q36_MISS_QD=8

A = `qd8`, B = `arena`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.
95% CI: bootstrap over runs. **sig** = the interval excludes 0.

## cold|cold-process|long|cap12|pilot0

| metric | qd8 | arena | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 376 ± 1.1e+02 | 370 ± 74 | -1.8 | [-26.1, +32.3] | n.s. |
| decode tok/s | 0.728 ± 0.13 | 0.77 ± 0.23 | +5.7 | [-22.7, +41.5] | n.s. |
| end-to-end tok/s (engine) | 0.08 ± 0.017 | 0.0767 ± 0.015 | -4.2 | [-25.9, +27.8] | n.s. |
| expert hit rate (%) | 44.2 ± 0 | 44.2 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 1.17e+05 ± 0 | 1.17e+05 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.23e+03 ± 2.4e+02 | 1.1e+03 ± 3.7e+02 | -10.3 | [-36.8, +24.9] | n.s. |
| bytes read by engine (GB) | 283 ± 0.11 | 283 ± 0.13 | -0.1 | [-0.1, -0.0] | sig better |
| peak RSS (GB) | 3.92 ± 0 | 4.01 ± 0.0058 | +2.4 | [+2.3, +2.6] | sig WORSE |
| minor page faults | 3.43e+06 ± 2.1e+04 | 3.06e+06 ± 4.9e+03 | -10.9 | [-11.3, -10.3] | sig better |
| peak VRAM above idle (MiB) | 0.333 ± 0.58 | 0 ± 0 | -100.0 | [-100.0, -100.0] | sig better |

## cold|cold-process|long|cap32|pilot0

| metric | qd8 | arena | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 221 ± 44 | 237 ± 74 | +7.6 | [-21.5, +45.9] | n.s. |
| decode tok/s | 0.672 ± 0.21 | 0.716 ± 0.26 | +6.5 | [-32.9, +65.2] | n.s. |
| end-to-end tok/s (engine) | 0.117 ± 0.015 | 0.117 ± 0.032 | +0.0 | [-29.4, +28.1] | n.s. |
| expert hit rate (%) | 72.9 ± 0 | 72.9 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 5.67e+04 ± 0 | 5.67e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.23e+03 ± 4.3e+02 | 1.25e+03 ± 4.5e+02 | +1.6 | [-36.7, +62.6] | n.s. |
| bytes read by engine (GB) | 141 ± 0.054 | 141 ± 0.075 | +0.0 | [-0.0, +0.1] | n.s. |
| peak RSS (GB) | 6.3 ± 0 | 6.35 ± 0 | +0.8 | [+0.8, +0.8] | sig WORSE |
| minor page faults | 3.96e+06 ± 6.9e+03 | 3.07e+06 ± 4.4e+04 | -22.4 | [-23.2, -21.2] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap12|pilot0

| metric | qd8 | arena | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 117 ± 42 | 108 ± 29 | -8.0 | [-38.3, +40.3] | n.s. |
| decode tok/s | 0.928 ± 0.26 | 1.32 ± 0.55 | +42.4 | [-10.2, +117.4] | n.s. |
| end-to-end tok/s (engine) | 0.223 ± 0.065 | 0.25 ± 0.053 | +11.9 | [-18.7, +57.4] | n.s. |
| expert hit rate (%) | 45.1 ± 0 | 45.1 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 4.04e+04 ± 0 | 4.04e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 949 ± 3e+02 | 693 ± 2.8e+02 | -27.0 | [-56.6, +16.0] | n.s. |
| bytes read by engine (GB) | 102 ± 0.047 | 101 ± 0.018 | -0.1 | [-0.1, -0.0] | sig better |
| peak RSS (GB) | 3.85 ± 0 | 3.96 ± 0.0058 | +2.8 | [+2.6, +2.9] | sig WORSE |
| minor page faults | 2.6e+06 ± 1.1e+04 | 2.11e+06 ± 2.5e+02 | -18.8 | [-19.2, -18.5] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap32|pilot0

| metric | qd8 | arena | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 82.8 ± 18 | 82.6 ± 19 | -0.2 | [-24.9, +32.7] | n.s. |
| decode tok/s | 1.17 ± 0.33 | 0.994 ± 0.26 | -15.1 | [-40.4, +18.0] | n.s. |
| end-to-end tok/s (engine) | 0.29 ± 0.03 | 0.287 ± 0.067 | -1.1 | [-25.0, +21.0] | n.s. |
| expert hit rate (%) | 74.4 ± 0 | 74.4 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 1.88e+04 ± 0 | 1.88e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 684 ± 1.7e+02 | 790 ± 2.3e+02 | +15.5 | [-18.0, +63.1] | n.s. |
| bytes read by engine (GB) | 50.5 ± 0.042 | 50.4 ± 0.02 | -0.1 | [-0.2, -0.1] | sig better |
| peak RSS (GB) | 6.22 ± 0 | 6.29 ± 0.0058 | +1.2 | [+1.1, +1.3] | sig WORSE |
| minor page faults | 3.18e+06 ± 6.9e+03 | 2.11e+06 ± 1.9e+04 | -33.6 | [-34.0, -33.0] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap12|pilot0

| metric | qd8 | arena | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 24.3 ± 11 | 16.2 ± 1.6 | -33.2 | [-54.3, -0.8] | sig better |
| decode tok/s | 1.28 ± 0.67 | 1.27 ± 0.55 | -1.0 | [-48.5, +107.3] | n.s. |
| end-to-end tok/s (engine) | 0.683 ± 0.28 | 0.773 ± 0.26 | +13.2 | [-29.2, +95.5] | n.s. |
| expert hit rate (%) | 44.8 ± 0 | 44.8 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 1.17e+04 ± 0 | 1.17e+04 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 811 ± 5e+02 | 729 ± 4.2e+02 | -10.0 | [-57.4, +99.3] | n.s. |
| bytes read by engine (GB) | 32.9 ± 0.029 | 32.9 ± 0.023 | +0.0 | [-0.1, +0.1] | n.s. |
| peak RSS (GB) | 3.82 ± 0 | 3.92 ± 0 | +2.6 | [+2.6, +2.6] | sig WORSE |
| minor page faults | 2.44e+06 ± 6e+02 | 2.05e+06 ± 6.8 | -16.1 | [-16.1, -16.1] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap32|pilot0

| metric | qd8 | arena | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 40.8 ± 18 | 37.5 ± 16 | -8.1 | [-51.6, +75.5] | n.s. |
| decode tok/s | 0.684 ± 0.1 | 0.928 ± 0.36 | +35.7 | [-6.6, +96.1] | n.s. |
| end-to-end tok/s (engine) | 0.383 ± 0.091 | 0.45 ± 0.11 | +17.4 | [-14.3, +60.8] | n.s. |
| expert hit rate (%) | 68.6 ± 0 | 68.6 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| expert misses | 6.63e+03 ± 0 | 6.63e+03 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| decode expert fetch (ms/token) | 1.11e+03 ± 1.9e+02 | 890 ± 3.2e+02 | -20.0 | [-44.5, +11.7] | n.s. |
| bytes read by engine (GB) | 21 ± 0.014 | 21 ± 0.012 | -0.1 | [-0.1, +0.0] | n.s. |
| peak RSS (GB) | 6.2 ± 0 | 6.26 ± 0 | +1.0 | [+1.0, +1.0] | sig WORSE |
| minor page faults | 3.05e+06 ± 1.1e+03 | 2.06e+06 ± 9.3e+02 | -32.5 | [-32.5, -32.5] | sig better |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |
