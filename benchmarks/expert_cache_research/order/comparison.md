# COLI_Q36_PREFILL_WAVES_ORDER=last vs first-seen order

A = `first`, B = `last`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.
95% CI: bootstrap over runs. **sig** = the interval excludes 0.

## cold|cold-process|long|cap12|pilot0

| metric | first | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 31.4 ± 9 | 33.7 ± 10 | +7.0 | [-25.1, +53.8] | n.s. |
| decode tok/s | 0.74 ± 0.11 | 1.01 ± 0.52 | +36.0 | [-31.6, +106.3] | n.s. |
| end-to-end tok/s (engine) | 0.433 ± 0.021 | 0.46 ± 0.1 | +6.2 | [-18.6, +26.9] | n.s. |
| expert hit rate (%) | 94.1 ± 0 | 94.3 ± 0 | +0.2 | [+0.2, +0.2] | sig better |
| expert misses | 1.23e+04 ± 0 | 1.2e+04 ± 0 | -2.0 | [-2.0, -2.0] | sig better |
| expert misses in decode | 6.65e+03 ± 0 | 6.41e+03 ± 0 | -3.7 | [-3.7, -3.7] | sig better |
| decode expert fetch (ms/token) | 1.18e+03 ± 1.4e+02 | 1.06e+03 ± 6.5e+02 | -10.7 | [-57.5, +50.0] | n.s. |
| bytes read by engine (GB) | 34.9 ± 0.087 | 34.3 ± 0.073 | -1.6 | [-1.9, -1.3] | sig better |
| peak RSS (GB) | 3.96 ± 0.0058 | 3.96 ± 0 | -0.1 | [-0.3, +0.0] | n.s. |
| minor page faults | 3.3e+06 ± 1.2e+04 | 3.28e+06 ± 7.8e+03 | -0.3 | [-0.7, +0.1] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|long|cap32|pilot0

| metric | first | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 62.9 ± 6 | 40.4 ± 9.2 | -35.8 | [-47.5, -19.3] | sig better |
| decode tok/s | 1.28 ± 0.62 | 0.764 ± 0.18 | -40.2 | [-61.7, -1.7] | sig WORSE |
| end-to-end tok/s (engine) | 0.353 ± 0.021 | 0.393 ± 0.042 | +11.3 | [+0.0, +24.5] | n.s. |
| expert hit rate (%) | 96 ± 0 | 96.3 ± 0 | +0.3 | [+0.3, +0.3] | sig better |
| expert misses | 8.36e+03 ± 0 | 7.77e+03 ± 0 | -7.1 | [-7.1, -7.1] | sig better |
| expert misses in decode | 2.76e+03 ± 0 | 2.16e+03 ± 0 | -21.5 | [-21.5, -21.5] | sig better |
| decode expert fetch (ms/token) | 729 ± 3e+02 | 982 ± 4e+02 | +34.8 | [-18.6, +153.4] | n.s. |
| bytes read by engine (GB) | 25.6 ± 0.04 | 24.2 ± 0.019 | -5.5 | [-5.6, -5.3] | sig better |
| peak RSS (GB) | 6.34 ± 0 | 6.34 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 3.89e+06 ± 1.2e+04 | 3.89e+06 ± 2.1e+04 | +0.1 | [-0.5, +0.7] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap12|pilot0

| metric | first | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 17.3 ± 2.8 | 21.8 ± 11 | +25.7 | [-22.8, +99.5] | n.s. |
| decode tok/s | 0.861 ± 0.03 | 1.28 ± 0.5 | +48.7 | [+9.2, +115.1] | sig better |
| end-to-end tok/s (engine) | 0.603 ± 0.032 | 0.667 ± 0.072 | +10.5 | [+0.0, +23.6] | n.s. |
| expert hit rate (%) | 84.8 ± 0 | 85.1 ± 0 | +0.4 | [+0.4, +0.4] | sig better |
| expert misses | 1.12e+04 ± 0 | 1.1e+04 ± 0 | -2.2 | [-2.2, -2.2] | sig better |
| expert misses in decode | 6.3e+03 ± 0 | 6.05e+03 ± 0 | -4.0 | [-4.0, -4.0] | sig better |
| decode expert fetch (ms/token) | 968 ± 48 | 744 ± 2.7e+02 | -23.1 | [-54.9, -1.1] | sig better |
| bytes read by engine (GB) | 32.2 ± 0.06 | 31.4 ± 0.12 | -2.4 | [-2.8, -2.0] | sig better |
| peak RSS (GB) | 3.87 ± 0 | 3.87 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 2.56e+06 ± 2.1e+03 | 2.56e+06 ± 4.3e+03 | +0.0 | [-0.1, +0.2] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap32|pilot0

| metric | first | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 28.7 ± 7.8 | 31.2 ± 9.4 | +8.5 | [-29.3, +53.0] | n.s. |
| decode tok/s | 0.935 ± 0.3 | 0.821 ± 0.22 | -12.2 | [-39.0, +30.2] | n.s. |
| end-to-end tok/s (engine) | 0.507 ± 0.075 | 0.46 ± 0.052 | -9.2 | [-22.8, +7.3] | n.s. |
| expert hit rate (%) | 89.9 ± 0 | 90.8 ± 0 | +1.0 | [+1.0, +1.0] | sig better |
| expert misses | 7.43e+03 ± 0 | 6.77e+03 ± 0 | -8.9 | [-8.9, -8.9] | sig better |
| expert misses in decode | 2.53e+03 ± 0 | 1.87e+03 ± 0 | -26.1 | [-26.1, -26.1] | sig better |
| decode expert fetch (ms/token) | 940 ± 3.4e+02 | 919 ± 2.8e+02 | -2.3 | [-36.3, +48.9] | n.s. |
| bytes read by engine (GB) | 23.5 ± 0.085 | 21.7 ± 0.11 | -7.4 | [-7.9, -6.9] | sig better |
| peak RSS (GB) | 6.24 ± 0 | 6.24 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 3.16e+06 ± 3.8e+03 | 3.17e+06 ± 2.3e+03 | +0.1 | [-0.1, +0.2] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap12|pilot0

| metric | first | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 19.2 ± 12 | 16.4 ± 7.8 | -14.9 | [-58.4, +102.5] | n.s. |
| decode tok/s | 1.27 ± 0.69 | 1.14 ± 0.75 | -10.3 | [-60.2, +87.2] | n.s. |
| end-to-end tok/s (engine) | 0.673 ± 0.064 | 0.64 ± 0.15 | -5.0 | [-25.0, +17.3] | n.s. |
| expert hit rate (%) | 55.6 ± 0 | 56.3 ± 0 | +1.3 | [+1.3, +1.3] | sig better |
| expert misses | 9.38e+03 ± 0 | 9.23e+03 ± 0 | -1.6 | [-1.6, -1.6] | sig better |
| expert misses in decode | 6.53e+03 ± 0 | 6.38e+03 ± 0 | -2.2 | [-2.2, -2.2] | sig better |
| decode expert fetch (ms/token) | 813 ± 3.8e+02 | 1e+03 ± 5.8e+02 | +23.5 | [-47.9, +163.8] | n.s. |
| bytes read by engine (GB) | 27.6 ± 0.11 | 27.2 ± 0.029 | -1.3 | [-1.6, -0.9] | sig better |
| peak RSS (GB) | 3.83 ± 0 | 3.83 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 2.43e+06 ± 1e+03 | 2.43e+06 ± 8.4e+02 | -0.0 | [-0.1, +0.0] | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap32|pilot0

| metric | first | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 15.4 ± 2.5 | 30.9 ± 13 | +100.5 | [+2.0, +180.3] | sig WORSE |
| decode tok/s | 0.687 ± 0.16 | 0.769 ± 0.27 | +11.9 | [-24.7, +61.3] | n.s. |
| end-to-end tok/s (engine) | 0.527 ± 0.1 | 0.437 ± 0.051 | -17.1 | [-32.0, +2.2] | n.s. |
| expert hit rate (%) | 70.2 ± 0 | 71 ± 0 | +1.1 | [+1.1, +1.1] | sig better |
| expert misses | 6.29e+03 ± 0 | 6.12e+03 ± 0 | -2.7 | [-2.7, -2.7] | sig better |
| expert misses in decode | 3.44e+03 ± 0 | 3.27e+03 ± 0 | -4.9 | [-4.9, -4.9] | sig better |
| decode expert fetch (ms/token) | 1.18e+03 ± 2.8e+02 | 1.19e+03 ± 3.3e+02 | +0.5 | [-31.2, +40.5] | n.s. |
| bytes read by engine (GB) | 20.3 ± 0.05 | 19.9 ± 0.094 | -1.8 | [-2.3, -1.4] | sig better |
| peak RSS (GB) | 6.2 ± 0 | 6.2 ± 0 | +0.0 | [+0.0, +0.0] | n.s. |
| minor page faults | 3.05e+06 ± 6.9e+02 | 3.05e+06 ± 8.5e+02 | +0.0 | [+0.0, +0.1] | sig WORSE |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |
