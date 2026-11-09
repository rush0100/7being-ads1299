# sevenbeing_ads1299_native (Rust / PyO3)

English · [中文](#中文)

## English

Fast path for live USBStyx `/data` frames (36 bytes: status + 8 big-endian int32).

- `decode_styx_codes` — sign-extended i32, flat `n×8`, status word dropped
- `decode_styx_uv` — one pass to microvolts, flat `n×8` f64

The live driver uses `decode_styx_uv` so a block keeps one float buffer instead of a code matrix plus a volts matrix plus a second microvolt copy.

MIT, same terms as `LICENSE` in this directory.

### Build

```bash
pip install maturin
cd native
maturin develop --release
```

Python falls back to NumPy if the extension is missing (`sevenbeing_ads1299.native_accel`).

## 中文

实时 USBStyx `/data` 帧的快速路径（36 字节：status + 8 个大端 int32）。

- `decode_styx_codes` — 符号扩展的 i32，扁平 `n×8`，丢弃 status 字
- `decode_styx_uv` — 一次转换为微伏，扁平 `n×8` f64

实时驱动使用 `decode_styx_uv`，因此一块数据只保留一个浮点缓冲，而不是代码矩阵、伏特矩阵，再加第二份微伏副本。

MIT，条款与本目录的 `LICENSE` 相同。

### 构建

```bash
pip install maturin
cd native
maturin develop --release
```

若扩展不存在，Python 会回退到 NumPy（`sevenbeing_ads1299.native_accel`）。
