# Before/after comparison

A = `token`, B = `last`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.
95% CI: bootstrap over runs. **sig** = the interval excludes 0.

## cold|cold-process|long|cap12|pilot0

| metric | token | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 413 ± 0 | 33.7 ± 10 | -91.8 | – | n.s. |
| decode tok/s | 0.643 ± 0 | 1.01 ± 0.52 | +56.5 | – | n.s. |
| end-to-end tok/s (engine) | 0.07 ± 0 | 0.46 ± 0.1 | +557.1 | – | n.s. |
| expert hit rate (%) | 44.2 ± 0 | 94.3 ± 0 | +113.3 | – | n.s. |
| expert misses | 1.17e+05 ± 0 | 1.2e+04 ± 0 | -89.7 | – | n.s. |
| expert misses in decode | 6.41e+03 ± 0 | 6.41e+03 ± 0 | +0.0 | – | n.s. |
| decode expert fetch (ms/token) | 1.38e+03 ± 0 | 1.06e+03 ± 6.5e+02 | -23.6 | – | n.s. |
| bytes read by engine (GB) | 282 ± 0 | 34.3 ± 0.073 | -87.9 | – | n.s. |
| peak RSS (GB) | 3.92 ± 0 | 3.96 ± 0 | +1.0 | – | n.s. |
| minor page faults | 3.45e+06 ± 0 | 3.28e+06 ± 7.8e+03 | -4.7 | – | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|long|cap32|pilot0

| metric | token | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 282 ± 0 | 40.4 ± 9.2 | -85.7 | – | n.s. |
| decode tok/s | 0.629 ± 0 | 0.764 ± 0.18 | +21.6 | – | n.s. |
| end-to-end tok/s (engine) | 0.1 ± 0 | 0.393 ± 0.042 | +293.3 | – | n.s. |
| expert hit rate (%) | 72.9 ± 0 | 96.3 ± 0 | +32.1 | – | n.s. |
| expert misses | 5.67e+04 ± 0 | 7.77e+03 ± 0 | -86.3 | – | n.s. |
| expert misses in decode | 2.16e+03 ± 0 | 2.16e+03 ± 0 | +0.0 | – | n.s. |
| decode expert fetch (ms/token) | 892 ± 0 | 982 ± 4e+02 | +10.1 | – | n.s. |
| bytes read by engine (GB) | 141 ± 0 | 24.2 ± 0.019 | -82.8 | – | n.s. |
| peak RSS (GB) | 6.3 ± 0 | 6.34 ± 0 | +0.6 | – | n.s. |
| minor page faults | 3.98e+06 ± 0 | 3.89e+06 ± 2.1e+04 | -2.2 | – | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap12|pilot0

| metric | token | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 144 ± 0 | 21.8 ± 11 | -84.9 | – | n.s. |
| decode tok/s | 1.78 ± 0 | 1.28 ± 0.5 | -28.1 | – | n.s. |
| end-to-end tok/s (engine) | 0.2 ± 0 | 0.667 ± 0.072 | +233.3 | – | n.s. |
| expert hit rate (%) | 45.1 ± 0 | 85.1 ± 0 | +88.7 | – | n.s. |
| expert misses | 4.04e+04 ± 0 | 1.1e+04 ± 0 | -72.9 | – | n.s. |
| expert misses in decode | 6.05e+03 ± 0 | 6.05e+03 ± 0 | +0.0 | – | n.s. |
| decode expert fetch (ms/token) | 452 ± 0 | 744 ± 2.7e+02 | +64.7 | – | n.s. |
| bytes read by engine (GB) | 102 ± 0 | 31.4 ± 0.12 | -69.1 | – | n.s. |
| peak RSS (GB) | 3.85 ± 0 | 3.87 ± 0 | +0.5 | – | n.s. |
| minor page faults | 2.6e+06 ± 0 | 2.56e+06 ± 4.3e+03 | -1.7 | – | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|medium|cap32|pilot0

| metric | token | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 96.6 ± 0 | 31.2 ± 9.4 | -67.7 | – | n.s. |
| decode tok/s | 1.02 ± 0 | 0.821 ± 0.22 | -19.3 | – | n.s. |
| end-to-end tok/s (engine) | 0.25 ± 0 | 0.46 ± 0.052 | +84.0 | – | n.s. |
| expert hit rate (%) | 74.4 ± 0 | 90.8 ± 0 | +22.0 | – | n.s. |
| expert misses | 1.88e+04 ± 0 | 6.77e+03 ± 0 | -64.1 | – | n.s. |
| expert misses in decode | 1.87e+03 ± 0 | 1.87e+03 ± 0 | +0.0 | – | n.s. |
| decode expert fetch (ms/token) | 789 ± 0 | 919 ± 2.8e+02 | +16.5 | – | n.s. |
| bytes read by engine (GB) | 50.5 ± 0 | 21.7 ± 0.11 | -56.9 | – | n.s. |
| peak RSS (GB) | 6.22 ± 0 | 6.24 ± 0 | +0.3 | – | n.s. |
| minor page faults | 3.18e+06 ± 0 | 3.17e+06 ± 2.3e+03 | -0.5 | – | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap12|pilot0

| metric | token | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 16.2 ± 0 | 16.4 ± 7.8 | +0.8 | – | n.s. |
| decode tok/s | 0.864 ± 0 | 1.14 ± 0.75 | +32.0 | – | n.s. |
| end-to-end tok/s (engine) | 0.61 ± 0 | 0.64 ± 0.15 | +4.9 | – | n.s. |
| expert hit rate (%) | 44.8 ± 0 | 56.3 ± 0 | +25.7 | – | n.s. |
| expert misses | 1.17e+04 ± 0 | 9.23e+03 ± 0 | -20.8 | – | n.s. |
| expert misses in decode | 6.38e+03 ± 0 | 6.38e+03 ± 0 | +0.0 | – | n.s. |
| decode expert fetch (ms/token) | 1.03e+03 ± 0 | 1e+03 ± 5.8e+02 | -2.7 | – | n.s. |
| bytes read by engine (GB) | 32.8 ± 0 | 27.2 ± 0.029 | -17.1 | – | n.s. |
| peak RSS (GB) | 3.82 ± 0 | 3.83 ± 0 | +0.3 | – | n.s. |
| minor page faults | 2.44e+06 ± 0 | 2.43e+06 ± 8.4e+02 | -0.2 | – | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |

## cold|cold-process|short|cap32|pilot0

| metric | token | last | Δ % | 95% CI | verdict |
|---|---|---|---|---|---|
| TTFT (s) | 28.6 ± 0 | 30.9 ± 13 | +8.2 | – | n.s. |
| decode tok/s | 0.572 ± 0 | 0.769 ± 0.27 | +34.6 | – | n.s. |
| end-to-end tok/s (engine) | 0.39 ± 0 | 0.437 ± 0.051 | +12.0 | – | n.s. |
| expert hit rate (%) | 68.6 ± 0 | 71 ± 0 | +3.5 | – | n.s. |
| expert misses | 6.63e+03 ± 0 | 6.12e+03 ± 0 | -7.7 | – | n.s. |
| expert misses in decode | 3.27e+03 ± 0 | 3.27e+03 ± 0 | +0.0 | – | n.s. |
| decode expert fetch (ms/token) | 1.42e+03 ± 0 | 1.19e+03 ± 3.3e+02 | -16.3 | – | n.s. |
| bytes read by engine (GB) | 21 ± 0 | 19.9 ± 0.094 | -5.0 | – | n.s. |
| peak RSS (GB) | 6.2 ± 0 | 6.2 ± 0 | +0.0 | – | n.s. |
| minor page faults | 3.05e+06 ± 0 | 3.05e+06 ± 8.5e+02 | -0.1 | – | n.s. |
| peak VRAM above idle (MiB) | 0 ± 0 | 0 ± 0 | – | – | – |
