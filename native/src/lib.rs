use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

const FRAME: usize = 36;
const CH: usize = 8;

fn sign_extend_24(word: u32) -> i32 {
    let mut code = (word & 0x00FF_FFFF) as i32;
    if code & 0x0080_0000 != 0 {
        code -= 0x0100_0000;
    }
    code
}

fn frame_count(buf: &[u8]) -> usize {
    buf.len() / FRAME
}

fn word_at(buf: &[u8], offset: usize) -> u32 {
    u32::from_be_bytes([
        buf[offset],
        buf[offset + 1],
        buf[offset + 2],
        buf[offset + 3],
    ])
}

/// Sign-extended channel codes, little-endian i32, `n * 8` values. Status word dropped.
#[pyfunction]
fn decode_styx_codes<'py>(py: Python<'py>, buf: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
    let n = frame_count(buf);
    PyBytes::new_with(py, n * CH * 4, |out| {
        for i in 0..n {
            let base = i * FRAME;
            for c in 0..CH {
                let code = sign_extend_24(word_at(buf, base + 4 + c * 4));
                let dst = (i * CH + c) * 4;
                out[dst..dst + 4].copy_from_slice(&code.to_le_bytes());
            }
        }
        Ok(())
    })
}

/// One pass from USB bytes to microvolts. Little-endian f64, `n * 8` values.
/// No code matrix and no volts matrix are allocated.
#[pyfunction]
fn decode_styx_uv<'py>(
    py: Python<'py>,
    buf: &[u8],
    vref: f64,
    gain: f64,
) -> PyResult<Bound<'py, PyBytes>> {
    if !vref.is_finite() || !gain.is_finite() || gain == 0.0 {
        return Err(PyValueError::new_err(
            "vref and gain must be finite, gain != 0",
        ));
    }
    let n = frame_count(buf);
    let lsb_uv = (2.0 * vref / gain) / 16_777_216.0 * 1_000_000.0;
    PyBytes::new_with(py, n * CH * 8, |out| {
        for i in 0..n {
            let base = i * FRAME;
            for c in 0..CH {
                let uv = sign_extend_24(word_at(buf, base + 4 + c * 4)) as f64 * lsb_uv;
                let dst = (i * CH + c) * 8;
                out[dst..dst + 8].copy_from_slice(&uv.to_le_bytes());
            }
        }
        Ok(())
    })
}

#[pymodule]
fn sevenbeing_ads1299_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(decode_styx_codes, m)?)?;
    m.add_function(wrap_pyfunction!(decode_styx_uv, m)?)?;
    Ok(())
}
