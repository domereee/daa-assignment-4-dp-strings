# Assignment 4 — Analysis

## Environment and commands

| | |
|---|---|
|Language|Java — `submission.json` → `"language": "Java"`; compiled with `javac --release 17`|
|JDK used for all runs below|OpenJDK 21.0.12.1|
|Launcher|Python 3.13.18|
|Machine|Ubuntu 24.04.5 LTS (Linux 6.18, x86-64), Intel Xeon @ 2.80 GHz, 4 vCPU, 15 GiB RAM (cloud container)|

All commands run from the repository root (`py -3` instead of `python` on Windows):

```sh
python tools/run.py --setup                  # compile + ping
python tools/run.py --check                  # 44 public cases + both batches in one process
python tools/run.py --input examples/lcs.jsonl
python tests/student/run_tests.py            # own tests: fixtures, brute-force comparison, scale
python tests/student/run_tests.py --verbose  # also prints the actual fixture outputs

javac -cp Java/build -d Java/build/bench tests/student/SearchBenchmark.java
java -cp Java/build:Java/build/bench SearchBenchmark     # Windows: Java/build;Java/build/bench
```

Results: `--setup` passes; `--check` passes all 44 public cases and the repeated mixed batch; every student test passes (see [Own tests](#own-tests)).

All code is in `Java/source/Algorithms.java`; the provided `Main.java` and `Json.java` transport is unchanged. Each request allocates its own arrays and the class has no mutable static fields, so consecutive requests in one process cannot share state.

---

## lcs — longest common subsequence

**State.** `dp[i][j]` is the LCS length of the prefixes `a[0..i)` and `b[0..j)`; `0 ≤ i ≤ |a|`, `0 ≤ j ≤ |b|`.

**Base cases.** `dp[0][j] = dp[i][0] = 0`: an empty prefix has only the empty common subsequence.

**Transition.**
- `a[i-1] == b[j-1]` → `dp[i][j] = dp[i-1][j-1] + 1`
- otherwise → `dp[i][j] = max(dp[i-1][j], dp[i][j-1])`

**Order.** Rows `i = 1..n`, columns `j = 1..m`. The three cells read (up, left, diagonal) are already filled.

**Correctness.** If the last characters are equal, some optimal LCS ends with this pair: in any LCS that does not, we can replace its last matched pair with `(i-1, j-1)` without losing length. If they differ, they cannot both be the final matched pair, so an optimum ignores `a[i-1]` or `b[j-1]`. That is why the mismatch transition takes the larger of the two subproblems and loses nothing.

**Reconstruction.** Start at `(n, m)` with `k = dp[n][m]` characters left to output. On a match, write the character at position `k-1` and move diagonally, so the dp value falls by exactly 1. On a mismatch, move to a neighbour that holds the same value, preferring up when both do. The invariant "`dp[i][j]` = characters still to write" keeps every move optimal. The result is a common subsequence of optimal length, built back to front. Ties: for `ABCA` / `BAC` the program returns `AC`; `BC` is also optimal and would be accepted.

**Complexity.** Time `O((|a|+1)(|b|+1))`, plus `O(|a|+|b|)` for reconstruction. The `int` table needs `O((|a|+1)(|b|+1))` memory, about 4 MB at 1000 × 1000. Output is `O(L)`. With empty input the table has a single row or column and the result is `0` / `""`.

**Boundary test.** `axbyc` / `abc` (public) must give 3. A substring DP (longest common *substring*) would give 1. `aaab` / `abab` → `aab` catches matching one character twice.

## merge — ordered adjacent-block merging (interval DP)

**State.** `cost[l][r]` is the minimum total cost of turning the original blocks `l..r` into the single block `[l, r]`. `split[l][r]` stores the best last split `k`.

**Base cases.** `cost[i][i] = 0`. If `n ≤ 1`, the result is cost 0 with an empty plan, in `O(1)`.

**Transition.** `cost[l][r] = min over l ≤ k < r of (cost[l][k] + cost[k+1][r]) + S(l, r)`, where `S(l, r) = prefix[r+1] − prefix[l]`.

**Why the last split works.** Blocks are always contiguous intervals of the original order. So the final merge that creates `[l, r]` must join two adjacent current blocks `[l, k]` and `[k+1, r]`. That merge costs `S(l, r)` no matter which `k` is used or what order came before. The merges inside `[l, k]` never touch `[k+1, r]`, so each side can be optimised on its own. Unlike matrix-chain multiplication, where the split cost `p[l-1]·p[k]·p[r]` depends on `k`, here the added cost is fixed for each interval and only the children's costs vary.

**Order.** By increasing interval length, so both children (shorter intervals) are ready.

**Reconstruction.** A recursive post-order `emit(l, r)` outputs `emit(l, k)`, then `emit(k+1, r)`, then `[l, k, r]`. Children must come before their parent: `[l, k, r]` is legal only once `[l, k]` and `[k+1, r]` exist as current blocks. The split tree is a binary tree with `n` leaves, so the plan has exactly `n − 1` merges. Recursion depth is at most `n − 1 = 199`. Ties take the smallest `k` (strict `<`).

**Large values.** Prefix sums are at most 2·10¹¹. Each size is paid at most once per tree level, so the total is below 200 · 2·10¹¹ = 4·10¹³. Everything is stored as `long`.

**Complexity.** `O(n³)` time (about 1.3·10⁶ inner steps at `n = 200`) and `O(n²)` auxiliary memory (one `long` table and one `int` table).

**Boundary tests.** `[1, 100, 1]`: an arbitrary "two smallest" greedy merges blocks 0 and 2, which are not adjacent (illegal). The correct answer is 203. `[3, 1, 2]` needs the plan `[[1,1,2],[0,0,2]]`. Printing the parent first breaks validation, and the mutation test below confirms this.

## tree — maximum-weight independent set on a tree

**State.** Root the tree at vertex 0. Any root gives the same optimum, because the problem is defined on the undirected tree.
- `take[v]` = best weight in `v`'s subtree with `v` selected.
- `skip[v]` = best weight in `v`'s subtree with `v` not selected.

**Transitions.**
- `take[v] = w[v] + Σ skip[c]`
- `skip[v] = Σ max(take[c], skip[c])`

Only the edge `v–c` connects a child's subtree to the rest, so subtrees are independent once `v`'s decision is fixed.

**Base cases.** A leaf has `take = w`, `skip = 0`. The empty set is allowed, so `skip ≥ 0` and the answer `max(take[root], skip[root]) ≥ 0`; all-negative input gives 0 with `[]`. `n = 0` gives `0` / `[]`.

**Order.** Adjacency is stored as CSR arrays (offsets plus one flat neighbour array). An iterative BFS from the root records `parent` and an order where every parent comes before its children. Scanning that order backwards visits children before parents, which is a valid post-order. There is no recursion, so a 100 000-vertex chain cannot overflow the stack.

**Reconstruction.** Walk the BFS order forwards (parents first) and set `chosen[v] = (v is root or parent not chosen) and take[v] > skip[v]`.
- If the parent is chosen, the parent's `take` used `skip[v]`, so `v` must be skipped.
- If the parent is skipped, the parent's `skip` used `max(take[v], skip[v])`, so `v` follows the larger value.

By induction, the selected weight equals the optimum. Each vertex is visited once, so there are no duplicates. Ties (`take == skip`) are skipped, so zero-gain vertices are not added.

**Complexity.** `O(n + 1)` time and auxiliary memory, including reconstruction. Sums reach at most 10⁵ · 10⁹ = 10¹⁴ and are stored as `long`.

**Boundary tests.** `weights [5, -2, 4]` with root 0 gives `take = 5`, `skip = max(0, −2) + max(0, 4) = 4`, so the answer is `{0}`. The `tree-root-choice` fixture makes vertex 0 a leaf and reverses edge orientation. Scale tests include a 100 000-vertex chain, a shuffled chain, a star and a random tree.

## Shared search contract (naive, kmp, rk)

One wrapper handles the contract for all three methods. If `m = 0`, the result is all `n + 1` boundaries `0..n`, decided before any pattern indexing. If `m > n`, the result is `[]`. Otherwise the selected algorithm runs with `1 ≤ m ≤ n`. Starts are appended in increasing order, overlaps included. No built-in search routine is used; the only character access is `charAt`.

## naive

**Invariant.** Before start `i`, `positions` holds every match start `< i`.

**Update.** For `i = 0..n−m`, compare `j = 0..m−1` and stop at the first mismatch. The last valid start is `n − m`, whose window `[n−m, n)` ends exactly at the end of the text. Each start is tested on its own, so overlapping matches are found automatically.

**Complexity.** `O((n−m+1)·m) ⊆ O(n·m + n + 1)` time, `O(1)` auxiliary memory and `O(z + 1)` output.

**Boundary tests.** `abc` / `abc` → `[0]` (a loop bound of `i < n − m` would miss it). `aaaa` / `aa` → `[0,1,2]`. Empty text with a non-empty pattern → `[]`.

## kmp

**Prefix function.** `pi[i]` is the length of the longest proper border of `pattern[0..i]`, i.e. the longest prefix that is also a suffix but not the whole string. It is built incrementally: try to extend `k = pi[i−1]`; on a mismatch, fall back with `k = pi[k−1]`. `k` grows by at most 1 per step and every fallback shrinks it, so construction is `O(m)` amortised.

**Search invariant.** After reading `text[i]`, `k` is the length of the longest pattern prefix that is a suffix of `text[0..i]`.
- **Mismatch:** `k = pi[k−1]`. This is the next-longest prefix that is still a suffix of the matched text. Any shift in between would imply a longer border, which contradicts the definition of `pi`.
- **Full match** (`k = m`): report `i − m + 1`, then set `k = pi[m−1]`, not 0. That keeps overlapping matches, for example `abababa` / `aba` → `[0, 2, 4]`.

**Complexity.** `O(n + m + z + 1)` time: `i` advances `n` times and total fallbacks are bounded by total increments. Auxiliary memory is `O(m + 1)` for `pi`; output is `O(z + 1)`.

**Boundary tests.** `abababab` / `abab` → `[0,2,4]`. A version that resets to `k = 0` after a full match returns `[0, 4]`, and the mutation test shows this is caught. `aaab` / `aab` → `[1]` checks fallback after a partial match.

## rk — exact Rabin–Karp (base 31, modulus 101)

**Hash.** `H(s) = Σ s[i]·31^(m−1−i) mod 101` over ASCII codes; the leftmost character has the highest power. The pattern hash and the first window hash are computed with Horner's rule. `lead = 31^(m−1) mod 101`.

**Rolling update.** `H' = ((H − t[i−1]·lead) mod 101 · 31 + t[i+m−1]) mod 101`. Java's `%` can return a negative value, so the subtraction step uses `Math.floorMod` to keep the value in `0..100`. Example: for `zab` / `ab`, the raw rolled value is −26. Without normalisation the window `ab` would never equal the pattern hash 75. All intermediate values are below 10⁴, so 64-bit arithmetic is more than enough.

**Verification.** An equal hash only makes a window a candidate. The program compares all `m` characters before reporting it. Equal strings always have equal hashes, so no match is missed; verification removes collisions, so no false start is reported. Example: `ab` and `dj` both hash to 75, and `bc` and `ek` both hash to 6.

**Complexity.** For `1 ≤ m ≤ n`: `O(n + m + c·m)`, where `c` counts candidate windows (true matches plus collisions). In the worst case `c = n − m + 1`. For example, with `aⁿ` / `aᵐ` every window is a real match and must be verified, giving `Θ((n−m+1)·m)`. The bound over all inputs is `O(n·m + n + m + 1)`. This is **not** linear in the worst case. Auxiliary memory is `O(1)` (rolling window); output is `O(z + 1)`.

## suffix — suffix array by prefix doubling

**Invariant.** After the round that uses length `k`, `rank[i]` identifies the first `min(k, n−i)` characters of suffix `i`. Equal ranks mean equal prefixes, and `sa` is sorted by those prefixes.

**Round k → 2k.** Suffix `i` gets the pair key `(rank[i], rank[i+k])`, with `−1` when `i + k ≥ n`. Using `−1` puts a suffix that has ended before every longer suffix with the same first half, which is exactly lexicographic order (a proper prefix comes first). No sentinel is added to the text or to the output.

**Sorting the pairs (LSD radix, linear per round).**
1. **By second key:** first the suffixes with `i + k ≥ n` (second key −1), then, for each `j` in the current `sa` with `j ≥ k`, append `j − k`. Because `sa` is already sorted by rank, this lists `i = j − k` in order of `rank[i+k]`. Suffixes with an empty second half all have different first ranks, so their relative order does not matter. A mutation that reverses them still passes every test, as expected.
2. **By first key:** a stable counting sort on `rank[i]` over `0..classes−1`.

**Re-rank.** Scan `sa` and open a new class whenever the pair differs from the previous one. The first round is a counting sort on character codes.

**Termination.** Stop when `classes = n`, i.e. all suffixes are distinct. This takes at most `⌈log₂ n⌉` rounds; a one-character text needs none.

**Complexity.** Each round is `O(n + classes) = O(n)`, so the total is `O(n log(n+1))` time and `O(n + 1)` memory (`sa`, `rank`, one buffer, counts). Empty text returns `[]`, `[]`, `""` in `O(1)`.

## suffix — Kasai LCP and the longest repeat

**Algorithm.** `position` is the inverse of `sa`. Process suffixes in text order `i = 0..n−1`. Compare suffix `i` with its predecessor in `sa`, `j = sa[position[i]−1]`, starting from the carried value `h`. Then store `lcp[position[i]] = h` and decrease `h` by 1 for the next `i`. `lcp[0] = 0` by convention, and `h` is reset there.

**Why `h` can be reused.** Suppose suffix `i` shares `h > 0` characters with its predecessor `j`. Then `j + 1` precedes `i + 1` in `sa` and shares `h − 1` characters with it. Every suffix between them in `sa` also shares at least `h − 1`. So the next comparison can start at `h − 1`. `h` rises at most `2n` times in total, which gives `O(n)` time and `O(n)` auxiliary memory.

**Why the maximum adjacent LCP is the longest repeat.**
- Any substring that starts at two distinct positions `p` and `q` is a common prefix of suffixes `p` and `q`. The LCP of two suffixes equals the minimum adjacent LCP between them in `sa`, so it is at most `max(lcp)`.
- Conversely, `lcp[r]` is a common prefix of the two distinct suffixes `sa[r−1]` and `sa[r]`, so a repeat of length `max(lcp)` exists.

The program returns `text.substring(sa[r], sa[r] + lcp[r])` for the first `r` that reaches the maximum. Overlapping occurrences are allowed (`aaaa` → `aaa`). If the maximum is 0, it returns `""`.

**Boundary tests.** `a$a`: `$` (code 36) is a real character, so an implementation that adds or strips a `$` sentinel gives the wrong order. Also tested: `mississippi` (full `sa`/`lcp`), `aabb` (tied repeats `a` and `b`), `aaaa` (public, overlapping repeat), and scale cases at `n = 50 000` (all `a`, random, Fibonacci word, printable, period 3).

## aho — Aho–Corasick dictionary counting

**Trie.** The goto table is a dense `int` array `next[state·95 + (c − 32)]` for the fixed ASCII alphabet 32..126, with capacity `1 + L` states. `terminal[p]` is the state where dictionary entry `p` ends. Duplicate patterns share one terminal state but keep their own output columns, so they get equal counts.

**Failure links.** `fail[v]` is the state of the longest proper suffix of `v`'s string that is also a trie prefix. The links are built in BFS (depth) order. For a real child `u = next[v][c]`, `fail[u] = next[fail[v]][c]`; that row is already complete because `fail[v]` is shallower than `v`. A missing transition is filled with `next[fail[v]][c]`. The result is a complete automaton: a query makes exactly one table lookup per character, with no fallback loop.

**Query, for each text separately.**
1. Clear `visits`.
2. Walk the text and add 1 to `visits[state]` after each character. After reading `text[0..i]`, the state is the longest suffix of the text read so far that is a trie prefix. Every pattern that ends at `i` is a suffix of that string, so it lies on the state's failure chain.
3. Propagate in reverse BFS order: `visits[fail[v]] += visits[v]`. Afterwards `visits[s]` is the number of positions where the string of `s` ends, which is its number of occurrences.
4. Set `count[p] = visits[terminal[p]]`.

This counts overlaps (each end position once) and suffix patterns (`he` inside `she`) without listing individual matches. The automaton is built once per request; `visits` is cleared for every text, and nothing is static.

**Edge cases.** `patterns = []` gives one empty row per text. `texts = []` gives `[]`. An empty text gives a row of zeros.

**Complexity.** Construction takes `O(L + 95·S + p)` time and `O(95·S + p)` memory (at most 100 001 · 95 ints ≈ 38 MB). Each text takes `O(|text| + S + p)`. Output is `O(q·(p+1) + 1)`. Counts are stored as `long`.

**Boundary tests.**
- `ushers` with `he, she, his, hers` → `[1, 1, 0, 1]`.
- `a, ab, bab, b, a` checks duplicates and the chain `bab → ab → b`.
- Repeating the same text checks the reset.
- A dense scale case uses patterns `a, aa, …, a⁴⁴⁶` against 100 texts of `a²⁰⁰⁰`. Output-link traversal would visit about 8.9·10⁷ matches; propagation needs `O(|text| + S)` per text.

---

## Own tests

| File | Contents |
|---|---|
|`tests/student/cases.json`|54 hand-written fixtures in the `tests/public.json` format, plus a `checks` field|
|`tests/student/oracle.py`|Independent brute-force oracles: subsequence enumeration (lcs), all chronological merge orders (merge), subset enumeration (tree), slicing (search), sorting suffix slices plus direct LCP and pairwise repeats (suffix), `startswith` counting (aho)|
|`tests/student/run_tests.py`|Runner. Uses the official `public_validate.check`, so any optimal witness is accepted.|
|`tests/student/SearchBenchmark.java`|naive / KMP / RK comparison (next section)|

The runner:
1. Checks that each hand-written expectation agrees with the oracle.
2. Sends all fixtures as one mixed-task batch, **twice in one process**, to catch stale state.
3. Compares 400 random small requests per command with the oracles (seed 2026, small alphabets for many ties and overlaps).
4. Checks that naive, kmp and rk give identical outputs on the same 400 pairs.
5. Runs one batch per command at the domain limits.

Actual output of `python tests/student/run_tests.py` (full logs, including every fixture output, are in `tests/student/logs/`):

```text
PASS  fixture expectations agree with oracle         54/54
PASS  fixtures, mixed batch repeated twice          108/108    0.10 s
PASS  random lcs vs brute force                     400/400    0.12 s
PASS  random merge vs brute force                   400/400    0.12 s
PASS  random tree vs brute force                    400/400    0.16 s
PASS  random suffix vs brute force                  400/400    0.13 s
PASS  random aho vs brute force                     400/400    0.12 s
PASS  random naive vs brute force                   400/400    0.11 s
PASS  random kmp vs brute force                     400/400    0.10 s
PASS  random rk vs brute force                      400/400    0.14 s
PASS  naive, kmp and rk give identical outputs      400/400
PASS  scale lcs (one batch)                           4/4      0.13 s
PASS  scale merge (one batch)                         3/3      0.11 s
PASS  scale tree (one batch)                          5/5      0.93 s
PASS  scale naive (one batch)                         3/3      0.11 s
PASS  scale kmp (one batch)                           6/6      0.34 s
PASS  scale rk (one batch)                            4/4      0.13 s
PASS  scale suffix (one batch)                        5/5      0.41 s
PASS  scale aho (one batch)                           4/4      0.64 s
ALL STUDENT TESTS PASSED
```

Batch times include JVM start-up and JSON transport. Pinned to one CPU (`taskset -c 0`), the slowest scale batch took 1.25 s, against a 20 s limit.

### Fixtures (expected vs actual)

Each search fixture runs under all three commands; one row is shown per scenario. Actual output is from `--verbose`.

|Command|Input|Expected (one optimum)|Actual|What it checks|
|---|---|---|---|---|
|lcs|`{"a":"","b":""}`|`{"length":0,"sequence":""}`|`{"length":0,"sequence":""}`|both strings empty|
|lcs|`{"a":"abc","b":""}`|`{"length":0,"sequence":""}`|`{"length":0,"sequence":""}`|empty b with nonempty a|
|lcs|`{"a":"abc","b":"xyz"}`|`{"length":0,"sequence":""}`|`{"length":0,"sequence":""}`|no shared characters|
|lcs|`{"a":"aaab","b":"abab"}`|`{"length":3,"sequence":"aab"}`|`{"length":3,"sequence":"aab"}`|repeated characters are matched once each|
|lcs|`{"a":"AGGTAB","b":"GXTXAYB"}`|`{"length":4,"sequence":"GTAB"}`|`{"length":4,"sequence":"GTAB"}`|non-contiguous witness|
|lcs|`{"a":"A b,C","b":"a b,c"}`|`{"length":3,"sequence":" b,"}`|`{"length":3,"sequence":" b,"}`|case-sensitive, spaces and punctuation are characters|
|lcs|`{"a":"ABCA","b":"BAC"}`|`{"length":2,"sequence":"BC"}`|`{"length":2,"sequence":"AC"}`|BC and AC tie; different optimal witness, accepted|
|merge|`{"sizes":[5,7]}`|`{"cost":12,"plan":[[0,0,1]]}`|`{"cost":12,"plan":[[0,0,1]]}`|single merge|
|merge|`{"sizes":[1,100,1]}`|`{"cost":203,"plan":[[0,0,1],[0,1,2]]}`|`{"cost":203,"plan":[[1,1,2],[0,0,2]]}`|merging the two smallest non-adjacent blocks is illegal; different optimal witness, accepted|
|merge|`{"sizes":[1,1,1,1]}`|`{"cost":8,"plan":[[0,0,1],[2,2,3],[0,1,3]]}`|`{"cost":8,"plan":[[0,0,1],[2,2,3],[0,1,3]]}`|balanced split beats left-to-right|
|merge|`{"sizes":[3,1,2]}`|`{"cost":9,"plan":[[1,1,2],[0,0,2]]}`|`{"cost":9,"plan":[[1,1,2],[0,0,2]]}`|child [1,2] must be merged before parent [0,2]|
|merge|`{"sizes":[1000000000,1000000000,1000000000,1000000000]}`|`{"cost":8000000000,"plan":[[0,0,1],[2,2,3],[0,1,3]]}`|`{"cost":8000000000,"plan":[[0,0,1],[2,2,3],[0,1,3]]}`|cost exceeds 32-bit range|
|tree|`{"n":1,"weights":[7],"edges":[]}`|`{"weight":7,"selected":[0]}`|`{"weight":7,"selected":[0]}`|one positive vertex|
|tree|`{"n":5,"weights":[10,3,3,3,3],"edges":[[0,1],[0,2],[0,3],[0,4]]}`|`{"weight":12,"selected":[1,2,3,4]}`|`{"weight":12,"selected":[1,2,3,4]}`|skipping the centre is better|
|tree|`{"n":4,"weights":[4,4,9,4],"edges":[[2,0],[2,1],[2,3]]}`|`{"weight":12,"selected":[0,1,3]}`|`{"weight":12,"selected":[0,1,3]}`|vertex 0 is a leaf; reversed edge orientation|
|tree|`{"n":5,"weights":[3,-1,4,-1,5],"edges":[[0,1],[1,2],[2,3],[3,4]]}`|`{"weight":12,"selected":[0,2,4]}`|`{"weight":12,"selected":[0,2,4]}`|negative vertices separate positive ones|
|tree|`{"n":3,"weights":[5,-2,4],"edges":[[0,1],[0,2]]}`|`{"weight":5,"selected":[0]}`|`{"weight":5,"selected":[0]}`|take=5, skip=max(0,-2)+max(0,4)=4|
|tree|`{"n":3,"weights":[1000000000,-1000000000,1000000000],"edges":[[0,1],[1,2]]}`|`{"weight":2000000000,"selected":[0,2]}`|`{"weight":2000000000,"selected":[0,2]}`|total exceeds 32-bit range|
|naive / kmp / rk|`{"text":"","pattern":"a"}`|`{"positions":[]}`|`{"positions":[]}`|nonempty pattern in empty text|
|naive / kmp / rk|`{"text":"abc","pattern":"abc"}`|`{"positions":[0]}`|`{"positions":[0]}`|pattern equals text; last valid start n-m|
|naive / kmp / rk|`{"text":"a.b a.b","pattern":"a.b"}`|`{"positions":[0,4]}`|`{"positions":[0,4]}`|spaces and dots are ordinary characters|
|naive / kmp / rk|`{"text":"aAaA","pattern":"aA"}`|`{"positions":[0,2]}`|`{"positions":[0,2]}`|case-sensitive comparison|
|naive / kmp / rk|`{"text":"abababab","pattern":"abab"}`|`{"positions":[0,2,4]}`|`{"positions":[0,2,4]}`|overlaps after a full match|
|naive / kmp / rk|`{"text":"aaab","pattern":"aab"}`|`{"positions":[1]}`|`{"positions":[1]}`|mismatch after partial match must not skip a start|
|naive / kmp / rk|`{"text":"abacabab","pattern":"abab"}`|`{"positions":[4]}`|`{"positions":[4]}`|match after several partial matches|
|rk|`{"text":"djab","pattern":"ab"}`|`{"positions":[2]}`|`{"positions":[2]}`|dj hashes like ab; verify characters|
|rk|`{"text":"abdjab","pattern":"dj"}`|`{"positions":[2]}`|`{"positions":[2]}`|pattern dj, colliding window ab rejected|
|rk|`{"text":"zab","pattern":"ab"}`|`{"positions":[1]}`|`{"positions":[1]}`|rolling subtraction goes negative and must be normalized|
|suffix|`{"text":"abc"}`|`{"sa":[0,1,2],"lcp":[0,0,0],"repeated":""}`|`{"sa":[0,1,2],"lcp":[0,0,0],"repeated":""}`|all distinct characters: no repeat|
|suffix|`{"text":"mississippi"}`|`{"sa":[10,7,4,1,0,9,8,6,3,5,2],"lcp":[0,1,1,4,0,0,1,0,2,1,3],"repeated":"issi"}`|`{"sa":[10,7,4,1,0,9,8,6,3,5,2],"lcp":[0,1,1,4,0,0,1,0,2,1,3],"repeated":"issi"}`|classic order and adjacent LCP|
|suffix|`{"text":"aabb"}`|`{"sa":[0,1,3,2],"lcp":[0,1,0,1],"repeated":"a"}`|`{"sa":[0,1,3,2],"lcp":[0,1,0,1],"repeated":"a"}`|a and b tie as longest repeats|
|suffix|`{"text":"a$a"}`|`{"sa":[1,2,0],"lcp":[0,0,1],"repeated":"a"}`|`{"sa":[1,2,0],"lcp":[0,0,1],"repeated":"a"}`|$ is a real character, no sentinel added|
|suffix|`{"text":"b a"}`|`{"sa":[1,2,0],"lcp":[0,0,0],"repeated":""}`|`{"sa":[1,2,0],"lcp":[0,0,0],"repeated":""}`|space sorts before letters|
|aho|`{"patterns":["he","she","his","hers"],"texts":["ushers"]}`|`{"counts":[[1,1,0,1]]}`|`{"counts":[[1,1,0,1]]}`|he/she end together; hers ends later|
|aho|`{"patterns":["aa"],"texts":["aaaa"]}`|`{"counts":[[3]]}`|`{"counts":[[3]]}`|overlapping occurrences|
|aho|`{"patterns":["x","y"],"texts":[""]}`|`{"counts":[[0,0]]}`|`{"counts":[[0,0]]}`|empty text gives one zero per pattern|
|aho|`{"patterns":["a","ab","bab","b","a"],"texts":["abab","xyz",""]}`|`{"counts":[[2,2,1,2,2],[0,0,0,0,0],[0,0,0,0,0]]}`|`{"counts":[[2,2,1,2,2],[0,0,0,0,0],[0,0,0,0,0]]}`|duplicates and suffix chain bab -> ab -> b|
|aho|`{"patterns":["abc"],"texts":["ab"]}`|`{"counts":[[0]]}`|`{"counts":[[0]]}`|pattern longer than text|
|aho|`{"patterns":[" ","a b"],"texts":["a b a b"]}`|`{"counts":[[3,2]]}`|`{"counts":[[3,2]]}`|space is an ordinary alphabet symbol|
|aho|`{"patterns":["ab","b"],"texts":["abb","abb"]}`|`{"counts":[[1,2],[1,2]]}`|`{"counts":[[1,2],[1,2]]}`|state and counts reset between equal texts|

### Scale cases (domain limits)

|Command|Cases in the batch|How the result is verified|
|---|---|---|
|lcs|1000 × 1000: random ACGT, identical, disjoint, printable|Length from an independent rolling-row DP; witness checked as a subsequence of both|
|merge|n = 200: random sizes ≤ 10⁹, all 10⁹, all 0|Cost from a Python interval DP; plan replayed by the validator|
|tree|n = 10⁵: chain 0-1-…, shuffled chain, star of 10⁹ weights, random tree, all-negative chain|Chains: linear "house robber" DP along the path. Star: closed form. Random tree: DP rooted at n−1.|
|naive|3000 / 1500 all `a`, empty pattern, random|Closed form or a `find` loop|
|kmp|`a²⁰⁰⁰⁰⁰` / `a¹⁰⁰⁰⁰⁰`, `(ab)¹⁰⁰⁰⁰⁰` / `(ab)⁵⁰⁰⁰⁰`, late single match, empty pattern, random, printable 200 000 / 100 000|Closed form or a `find` loop|
|rk|`a¹⁰⁰⁰⁰` / `a²⁰⁰⁰` (8001 verified candidates), `a¹⁰⁰⁰⁰` / `a¹⁹⁹⁹b`, ab/dj collision text, printable|Closed form or a `find` loop|
|suffix|n = 50 000: all `a`, random ab, Fibonacci word, printable, period 3|All `a`: closed form. Others: `sa` is a permutation; for every adjacent pair the stated LCP characters are equal and the next character is strictly smaller (or the first suffix ends); repeat length equals max LCP and occurs twice.|
|aho|dense `a¹..a⁴⁴⁶` × 100 texts; 10 000 duplicated length-10 patterns × 100 texts; 10 000 mixed-length patterns × one 200 000 text; printable length-100 patterns|Closed form or counting all text windows with `Counter`|

### Mutation check: which defect each test detects

A copy of the program was modified with one typical defect at a time, and the student suite was run against it. Results are actual runs.

|Injected defect|Detected by|
|---|---|
|rk: `%` instead of `floorMod` (no negative-remainder normalisation)|`rk-negative-remainder`, `rk-collision-dj`, `rk-case`, `rk-punctuation`, `rk-fallback`; random rk 266/400; scale 2/4|
|rk: report equal hashes without comparing characters|`rk-collision-dj`, `rk-collision-pattern-dj`; random rk 384/400; scale 2/4 (ab/dj collisions, printable)|
|kmp: reset `k = 0` after a full match|`kmp-periodic`; random kmp 383/400; scale 3/6 (all `a`, period 2, random ab)|
|lcs: on a mismatch, move to the smaller neighbour|Index −1 crashes the process; every lcs batch fails|
|lcs: wrong witness characters|`lcs-repeated-chars`, `lcs-classic`, `lcs-case-punctuation`, `lcs-practice`; random lcs 160/400; scale 2/4|
|merge: parent merge printed before its children|`merge-adjacency`, `merge-balanced`, `merge-chronological`, `merge-64bit`; random merge 123/400; scale 0/3|
|tree: reconstruction ignores the parent's decision|`tree-root-choice`, `tree-negative-child`; random tree 304/400; scale 2/5|
|aho: no propagation along failure links|`aho-ushers`, `aho-failure-chain`, `aho-spaces`, `aho-repeated-texts`; random aho 274/400; scale 2/4|
|aho: counts not reset between texts|`aho-repeated-texts`, `aho-failure-chain`; random aho 230/400; scale 1/4|
|doubling: ignore the second rank|Classes stop growing and the index goes out of range: every suffix batch fails|
|doubling: missing second rank `0` instead of `−1`|Fixtures still pass, but the random batch (0/400) and every scale case (0/5) fail|
|Kasai: reset `h = 0` every step instead of `h − 1`|*Not detected*: still correct, only `O(n²)` in the worst case, and the all-`a` case at n = 50 000 still finishes in time|
|doubling: reverse the order of suffixes with an empty second half|*Not a defect*: their first ranks are all different, which confirms the claim in the doubling section|

---

## Search comparison

**Inputs.** Identical text/pattern pairs for all three methods. Sizes `n = 750, 1500, 3000` with `m = n / 10`, all inside the common domain (`n, m ≤ 3000`, `n·m ≤ 2·10⁷`).
- **Random:** `java.util.Random(2026)`. The text is uniform over `{a, c, g, t}`, and the pattern is a substring cut at a random start, so there is at least one match.
- **Repetitive hit:** text `aⁿ`, pattern `aᵐ`, so every window matches.
- **Repetitive miss:** text `aⁿ`, pattern `aᵐ⁻¹b`, so there are no matches but every window shares a long prefix with the pattern.

**Correctness before timing.** The outputs of all three methods are compared with an independent `String.startsWith` scan. The benchmark throws if any output differs.

**RK candidates.** The "RK candidates" column counts windows whose hash equals the pattern hash. It is computed directly per window, independently of the rolling code.

**Timing scope.** One call to `Algorithms.naive / kmp / rk` on a prebuilt request map, i.e. after JSON parsing. It includes building the `positions` list and excludes compilation and JVM start-up. Times come from `System.nanoTime`. After warm-up, a calibration step chooses how many consecutive calls make one run last about 20 ms (column *Calls/run*); a run reports the mean time per call. There are 5 runs per method and case, interleaved across methods (run 1 of naive, kmp, rk, then run 2, …). The median of the 5 runs is reported.

**Warm-up / JIT.** 500 untimed rounds over every case and method run before any measurement, so all three methods are JIT-compiled before timing starts. Hardware is listed in the first section. Unit: **microseconds per call**.

|Case|n|m|Algorithm|Calls/run|Run 1|Run 2|Run 3|Run 4|Run 5|Median|Matches|RK candidates|Outputs identical|
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
|random acgt, pattern cut from text|750|75|naive|3016|4.5|4.3|4.3|4.3|4.5|**4.3**|1|7|yes|
|random acgt, pattern cut from text|750|75|kmp|3194|2.9|2.8|2.7|2.9|2.7|**2.8**|1|7|yes|
|random acgt, pattern cut from text|750|75|rk|2350|7.5|7.4|7.5|7.4|7.3|**7.4**|1|7|yes|
|random acgt, pattern cut from text|1500|150|naive|2370|8.7|9.1|8.8|8.4|8.3|**8.7**|1|13|yes|
|random acgt, pattern cut from text|1500|150|kmp|2879|5.4|5.6|5.4|5.1|5.2|**5.4**|1|13|yes|
|random acgt, pattern cut from text|1500|150|rk|1412|14.8|14.9|14.6|14.3|14.3|**14.6**|1|13|yes|
|random acgt, pattern cut from text|3000|300|naive|1111|16.3|17.0|21.1|16.4|17.5|**17.0**|1|34|yes|
|random acgt, pattern cut from text|3000|300|kmp|1728|10.8|10.7|15.2|10.4|20.2|**10.8**|1|34|yes|
|random acgt, pattern cut from text|3000|300|rk|685|29.7|28.7|30.9|28.3|35.3|**29.7**|1|34|yes|
|repetitive hit a^n / a^m|750|75|naive|264|43.6|43.8|43.7|46.7|45.7|**43.8**|676|676|yes|
|repetitive hit a^n / a^m|750|75|kmp|2766|8.8|7.2|8.1|7.4|9.8|**8.1**|676|676|yes|
|repetitive hit a^n / a^m|750|75|rk|481|42.7|41.6|56.6|41.3|78.2|**42.7**|676|676|yes|
|repetitive hit a^n / a^m|1500|150|naive|67|268.7|172.3|166.9|162.9|162.5|**166.9**|1351|1351|yes|
|repetitive hit a^n / a^m|1500|150|kmp|861|15.8|15.9|19.3|15.1|15.4|**15.8**|1351|1351|yes|
|repetitive hit a^n / a^m|1500|150|rk|69|151.3|149.7|146.3|145.9|145.3|**146.3**|1351|1351|yes|
|repetitive hit a^n / a^m|3000|300|naive|34|600.4|600.3|652.2|637.1|1291.8|**637.1**|2701|2701|yes|
|repetitive hit a^n / a^m|3000|300|kmp|609|32.6|29.4|42.8|45.2|57.7|**42.8**|2701|2701|yes|
|repetitive hit a^n / a^m|3000|300|rk|37|604.3|598.1|655.0|851.7|723.2|**655.0**|2701|2701|yes|
|repetitive miss a^n / a^(m-1)b|750|75|naive|503|40.7|46.1|46.5|45.1|40.3|**45.1**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|750|75|kmp|4098|4.9|6.0|5.1|8.0|4.4|**5.1**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|750|75|rk|2773|7.2|7.7|8.0|6.9|6.9|**7.2**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|1500|150|naive|138|149.3|145.5|145.4|148.6|149.2|**148.6**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|1500|150|kmp|2363|8.9|9.3|8.7|15.0|9.0|**9.0**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|1500|150|rk|1329|14.0|13.8|13.5|15.0|15.3|**14.0**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|3000|300|naive|20|751.8|568.8|611.2|1026.6|587.7|**611.2**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|3000|300|kmp|594|17.8|17.9|36.5|22.1|20.5|**20.5**|0|0|yes|
|repetitive miss a^n / a^(m-1)b|3000|300|rk|612|28.1|27.7|31.9|27.7|27.8|**27.8**|0|0|yes|

**Observations**

- **Random text.** All three methods roughly double their time when `n` doubles (naive 4.3 → 8.7 → 17.0 µs, KMP 2.8 → 5.4 → 10.8 µs, RK 7.4 → 14.6 → 29.7 µs). Naive is fast: on random 4-letter text a mismatch usually happens after about 1.3 comparisons, so its `O(n·m)` worst case is never reached. RK is the slowest here because it does modular arithmetic for every window and also verifies false candidates. It saw 7, 13 and 34 candidates for one true match, which is about `(n−m+1)/101` collisions, each checked character by character.
- **Repetitive hit (`aⁿ` / `aᵐ`).** Here `z = n − m + 1`. Naive and RK both do `Θ((n−m+1)·m)` work: each doubling of `n` multiplied the median time by about 3.4–4.5 (naive 43.8 → 166.9 → 637.1 µs; RK 42.7 → 146.3 → 655.0 µs), consistent with quadratic growth because `m` grows with `n`. For RK, `c = z`: when the windows really are equal, hashing cannot save the verification. KMP stays far lower (8.1 → 15.8 → 42.8 µs). Its last step is inflated by noisy runs (29.4–57.7 µs); the fastest runs grow about 2× per doubling, consistent with linear time.
- **Repetitive miss (`aⁿ` / `aᵐ⁻¹b`).** Naive still compares `m` characters per start (45.1 → 148.6 → 611.2 µs). RK has zero candidates, because the pattern hash differs from every window hash by exactly 1 mod 101, so it behaves linearly (7.2 → 14.0 → 27.8 µs), close to KMP (5.1 → 9.0 → 20.5 µs).
- These medians come from one shared cloud machine and include visible noise (single slow runs). They illustrate the bounds proved above but do not prove asymptotic complexity. Rerunning the command on another machine gives different absolute times.

**About modulus 101.** A modulus of 101 has only 101 possible hash values, so on random text roughly 1 in 101 windows is a false candidate. The measured candidate counts show this. The small modulus was chosen to make collisions easy to construct and test (`ab`/`dj`, `bc`/`ek`). Production Rabin–Karp implementations usually use a large modulus such as 2⁶¹−1, often with a random base or two moduli. That makes accidental collisions negligible, so their expected time is close to `O(n + m)`. Even so, a fixed hash can be attacked with crafted inputs, and genuinely equal windows (the repetitive-hit case) always need verification. Some implementations also skip verification and accept a small error probability. The collision rate measured here therefore describes this exact, deliberately weak lab configuration, not production hashing in general. The known collision pairs are correctness tests: public `rk-collision`, plus `rk-collision-dj`, `rk-collision-pattern-dj` and the scale case with 5000 `ab`/`dj` blocks.

---

## Sources and AI assistance

- **Course material:** lectures 8–10, `docs/Assignment_4_EN.md`, `docs/guide/*` and `docs/LECTURE_CLARIFICATIONS_EN_RU.md` in this repository.
- **Standard algorithm references:** Cormen et al., *Introduction to Algorithms* (LCS, interval DP, KMP, Rabin–Karp); Manber & Myers (1993) for prefix doubling; Kasai et al. (2001) for linear-time LCP; Aho & Corasick (1975).
- **AI assistance:** Claude (Anthropic), used through Claude Code, wrote the Java implementation in `Algorithms.java`, the test runner, oracles and fixtures, the benchmark, and the draft of this analysis.
- **Verification performed:**
  - public checks: 44/44 plus the repeated mixed batch;
  - 54 fixtures whose expectations were cross-checked by brute force;
  - 3200 random requests compared with independently written brute-force oracles;
  - 34 scale cases at the domain limits, also with one CPU;
  - the mutation check above.

  All numbers in this document come from actual runs of the commands listed at the top.
