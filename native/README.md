# sevenbeing_ads1299_native (Rust / PyO3)

Fast path for live USBStyx `/data` frames (36 bytes: status + 8 big-endian int32).

- `decode_styx_codes` — sign-extended i32, flat `n×8`, status word dropped
- `decode_styx_uv` — one pass to microvolts, flat `n×8` f64

The live driver uses `decode_styx_uv` so a block keeps one float buffer instead of a code matrix plus a volts matrix plus a second microvolt copy.

MIT, same terms as `LICENSE` in this directory.

## Build

```bash
pip install maturin
cd native
maturin develop --release
```

Python falls back to NumPy if the extension is missing (`sevenbeing_ads1299.native_accel`).
