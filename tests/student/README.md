# Own tests

| File | Purpose |
|---|---|
|`cases.json`|54 hand-written fixtures (public-test format plus a `checks` note)|
|`oracle.py`|Independent brute-force reference answers for small inputs|
|`run_tests.py`|Fixtures in one mixed batch run twice, 400 random cases per command against the oracles, and scale batches at the domain limits|
|`SearchBenchmark.java`|naive / KMP / RK timing on identical inputs (seed 2026)|
|`logs/`|Actual output of the final runs|

Run from the repository root:

```sh
python tools/run.py --check
python tests/student/run_tests.py --verbose
python tools/run.py --input tests/student/requests.jsonl
javac -cp Java/build -d Java/build/bench tests/student/SearchBenchmark.java
java -cp Java/build:Java/build/bench SearchBenchmark
```

`requests.jsonl` contains the fixture requests as plain JSON Lines. The ANALYSIS.md section *Own tests* lists the input, expected output, actual output and the defect each case detects.
