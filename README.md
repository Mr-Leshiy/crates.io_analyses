# Rust `crates.io` Analysis for Security and Reliability

This project is focused on analyzing Rust packages from [`crates.io`](https://crates.io) to evaluate them based on security, reliability, and other software quality metrics.
The analysis is driven by the [`cargo-deny`](https://github.com/EmbarkStudios/cargo-deny) tool, which provides automated auditing capabilities for Rust dependencies.

## Build and run
```shell
docker build -t crates.io_analysis:latest .
docker run --name crates.io_analysis crates.io_analysis:latest
docker cp crates.io_analysis:app/crates_info.csv .
```
