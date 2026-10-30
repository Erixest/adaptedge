# Real pilot data (LoRa RTT)

These CSVs are derived from the author's dissertation hardware captures, not
from the synthetic replay. They contain only the acknowledged-probe RTT rows
(`LQ,ACK_OK,...,value_us=<rtt>`) extracted from the raw serial logs.

| File | Capture | PHY | Samples | Median RTT |
|---|---|---|---:|---:|
| `lora_pilot_sf7.csv` | `2026-10-06-steady-sf7-bw125.csv` | SF7, BW125, CR4/5, +14 dBm | 46 | 201.262 ms |
| `lora_pilot_sf9.csv` | `2026-10-06-steady-sf9-bw125.csv` | SF9, BW125, CR4/5, +14 dBm | 32 | 637.698 ms |
| `lora_pilot_sf7_minus9dbm.csv` | `2026-10-06-steady-sf7-minus9dbm.csv` | SF7, BW125, CR4/5, -9 dBm | 42 | 201.2425 ms |

Source repository: `dissertation/firmware/heltec-lora-rtt/runs/` (raw logs and
`RESULTS.md`). The original capture is a clean, co-located two-board baseline:
two Heltec WiFi LoRa 32 V3 boards, SX1262, 868 MHz, 46-byte probe and immediate
46-byte ACK, one probe per second. It is **not** a range, interference, or field
result.

The replay harness uses the SF7 median as the anchor for its LoRa regime and
widens the RTT/loss/jitter ranges to model field variability. The shipped CSVs
let CI verify that the published pilot numbers remain reproducible and that the
simulator anchor stays within the measured baseline.

Checksums of the raw source files are recorded in `SOURCE_SHA256.txt`; the
extraction rule is implemented in `src/adaptedge/dataset.py`.
