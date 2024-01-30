# code-samples

Collection of Paradex code samples, snippets and benchmarks

## Examples

* [Go](go/README.md)
* [Java](java/README.md)
* [Python](python/README.md)

## Benchmarks

### Order signing benchmarks

On MacBook Pro 2021, M1 Pro

```bash
Python: 27 signs/sec - C extension enabled
Python: 13 signs/sec - C extension disabled
Go: 590 signs/sec
```

### Running on your machine

Examples and benchmarks for signing orders.

#### Python

To run it directly, you will need [Python 3.9+](https://www.python.org/downloads/).

```bash
cd python
python3.9 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python bench_order_sign.py
```

#### Go

```bash
cd go
go test -bench .
```
