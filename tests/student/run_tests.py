"""Own tests: fixtures, randomized brute-force comparison and full-domain scale checks.

Usage: python tests/student/run_tests.py [--language Java] [--verbose]
"""
import argparse
import json
import pathlib
import random
import subprocess
import sys
import time
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'tools'))

from public_validate import check  # noqa: E402
from run import build, execute, select_language  # noqa: E402
import oracle  # noqa: E402

SEED = 2026
RANDOM_CASES = 400
PRINTABLE = ''.join(chr(c) for c in range(32, 127))
BILLION = 10 ** 9


def word(rng, alphabet, low, high):
    return ''.join(rng.choice(alphabet) for _ in range(rng.randint(low, high)))


def random_tree(rng, n, path=False):
    labels = list(range(n))
    rng.shuffle(labels)
    edges = [[labels[i - 1 if path else rng.randrange(i)], labels[i]] for i in range(1, n)]
    edges = [e if rng.random() < 0.5 else e[::-1] for e in edges]
    rng.shuffle(edges)
    return labels, edges


def find_all(text, pattern):
    found, i = [], text.find(pattern)
    while i != -1:
        found.append(i)
        i = text.find(pattern, i + 1)
    return found


def lcs_length(a, b):
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0]
        for j, y in enumerate(b):
            current.append(previous[j] + 1 if x == y else max(previous[j + 1], current[j]))
        previous = current
    return previous[-1]


def merge_cost(sizes):
    n = len(sizes)
    prefix = [0]
    for s in sizes:
        prefix.append(prefix[-1] + s)
    cost = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for l in range(n - length + 1):
            r = l + length - 1
            cost[l][r] = min(cost[l][k] + cost[k + 1][r] for k in range(l, r)) + prefix[r + 1] - prefix[l]
    return cost[0][n - 1] if n > 1 else 0


def path_mwis(weights_in_path_order):
    before, best = 0, 0
    for w in weights_in_path_order:
        before, best = best, max(best, before + w)
    return best


def tree_mwis(n, weights, edges, root):
    adjacent = [[] for _ in range(n)]
    for u, v in edges:
        adjacent[u].append(v)
        adjacent[v].append(u)
    parent, order = [-1] * n, [root]
    parent[root] = root
    for v in order:
        for u in adjacent[v]:
            if parent[u] == -1:
                parent[u] = v
                order.append(u)
    take, skip = list(weights), [0] * n
    for v in reversed(order[1:]):
        take[parent[v]] += skip[v]
        skip[parent[v]] += max(take[v], skip[v])
    return max(take[root], skip[root])


def verify_suffix(text, answer):
    sa, lcp, repeated = answer['sa'], answer['lcp'], answer['repeated']
    n = len(text)
    if sorted(sa) != list(range(n)) or len(lcp) != n or (n and lcp[0] != 0):
        return False
    for r in range(1, n):
        a, b, h = sa[r - 1], sa[r], lcp[r]
        if text[a:a + h] != text[b:b + h]:
            return False
        if a + h < n and (b + h >= n or text[a + h] >= text[b + h]):
            return False
    first = text.find(repeated)
    return len(repeated) == max(lcp, default=0) and (not repeated or text.find(repeated, first + 1) != -1)


def random_requests(rng):
    requests = {task: [] for task in ('lcs', 'merge', 'tree', 'search', 'suffix', 'aho')}
    for _ in range(RANDOM_CASES):
        alphabet = rng.choice(['ab', 'abc', 'aB ,'])
        requests['lcs'].append({'task': 'lcs', 'a': word(rng, alphabet, 0, 10), 'b': word(rng, alphabet, 0, 10)})

        top = rng.choice([0, 3, 20, BILLION])
        requests['merge'].append({'task': 'merge', 'sizes': [rng.randint(0, top) for _ in range(rng.randint(0, 7))]})

        n, bound = rng.randint(0, 12), rng.choice([2, 10, BILLION])
        _, edges = random_tree(rng, n, path=rng.random() < 0.3)
        requests['tree'].append({'task': 'tree', 'n': n, 'weights': [rng.randint(-bound, bound) for _ in range(n)],
                                 'edges': edges})

        alphabet = rng.choice(['ab', 'abdj', 'aA. '])
        text = word(rng, alphabet, 0, 30)
        if text and rng.random() < 0.5:
            i = rng.randrange(len(text))
            pattern = text[i:i + rng.randint(0, 6)]
        else:
            pattern = word(rng, alphabet, 0, 5)
        requests['search'].append((text, pattern))

        requests['suffix'].append({'task': 'suffix', 'text': word(rng, rng.choice(['a', 'ab', 'abc', ' $a']), 0, 25)})

        alphabet = rng.choice(['ab', 'abc'])
        requests['aho'].append({'task': 'aho', 'patterns': [word(rng, alphabet, 1, 4) for _ in range(rng.randint(0, 6))],
                                'texts': [word(rng, alphabet, 0, 20) for _ in range(rng.randint(0, 4))]})
    return requests


def scale_cases(rng):
    def case(name, request, verify):
        return {'name': name, 'input': request, 'verify': verify}

    def expect(output):
        return lambda request, answer: check(request, answer, output)

    cases = {task: [] for task in ('lcs', 'merge', 'tree', 'naive', 'kmp', 'rk', 'suffix', 'aho')}

    for a, b, label in [(word(rng, 'ACGT', 1000, 1000), word(rng, 'ACGT', 1000, 1000), 'random ACGT'),
                        ('a' * 1000, 'a' * 1000, 'identical'),
                        ('x' * 1000, 'y' * 1000, 'disjoint'),
                        (word(rng, PRINTABLE, 1000, 1000), word(rng, PRINTABLE, 1000, 1000), 'printable')]:
        request = {'task': 'lcs', 'a': a, 'b': b}
        cases['lcs'].append(case(f'lcs 1000x1000 {label}', request, expect({'length': lcs_length(a, b)})))

    for sizes, label in [([rng.randint(0, BILLION) for _ in range(200)], 'random'),
                         ([BILLION] * 200, 'all 1e9'),
                         ([0] * 200, 'all zero')]:
        request = {'task': 'merge', 'sizes': sizes}
        cases['merge'].append(case(f'merge n=200 {label}', request, expect({'cost': merge_cost(sizes)})))

    n = 100000
    weights = [rng.randint(-BILLION, BILLION) for _ in range(n)]
    cases['tree'].append(case('tree chain 0-1-...-99999', {'task': 'tree', 'n': n, 'weights': weights,
                                                            'edges': [[i, i + 1] for i in range(n - 1)]},
                              expect({'weight': path_mwis(weights)})))
    labels, edges = random_tree(rng, n, path=True)
    cases['tree'].append(case('tree shuffled chain', {'task': 'tree', 'n': n, 'weights': weights, 'edges': edges},
                              expect({'weight': path_mwis([weights[v] for v in labels])})))
    cases['tree'].append(case('tree star, all 1e9', {'task': 'tree', 'n': n, 'weights': [BILLION] * n,
                                                      'edges': [[labels[0], v] for v in range(n) if v != labels[0]]},
                              expect({'weight': (n - 1) * BILLION})))
    _, edges = random_tree(rng, n)
    cases['tree'].append(case('tree random', {'task': 'tree', 'n': n, 'weights': weights, 'edges': edges},
                              expect({'weight': tree_mwis(n, weights, edges, n - 1)})))
    cases['tree'].append(case('tree chain all negative', {'task': 'tree', 'n': n, 'weights': [-1] * n,
                                                           'edges': [[i, i + 1] for i in range(n - 1)]},
                              expect({'weight': 0})))

    def search_case(task, text, pattern, positions, label):
        request = {'task': task, 'text': text, 'pattern': pattern}
        cases[task].append(case(f'{task} n={len(text)} m={len(pattern)} {label}', request,
                                expect({'positions': positions})))

    search_case('naive', 'a' * 3000, 'a' * 1500, list(range(1501)), 'all a')
    search_case('naive', 'a' * 3000, '', list(range(3001)), 'empty pattern')
    text = word(rng, 'ab', 3000, 3000)
    search_case('naive', text, text[1000:1010], find_all(text, text[1000:1010]), 'random ab')

    search_case('kmp', 'a' * 200000, 'a' * 100000, list(range(100001)), 'all a')
    search_case('kmp', 'ab' * 100000, 'ab' * 50000, list(range(0, 100001, 2)), 'period 2')
    search_case('kmp', 'a' * 199999 + 'b', 'a' * 99999 + 'b', [100000], 'one late match')
    search_case('kmp', 'a' * 200000, '', list(range(200001)), 'empty pattern')
    text = word(rng, 'ab', 200000, 200000)
    search_case('kmp', text, text[777:789], find_all(text, text[777:789]), 'random ab')
    text = word(rng, PRINTABLE, 200000, 200000)
    search_case('kmp', text, text[100000:], find_all(text, text[100000:]), 'printable')

    search_case('rk', 'a' * 10000, 'a' * 2000, list(range(8001)), 'every window a candidate')
    search_case('rk', 'a' * 10000, 'a' * 1999 + 'b', [], 'no candidates')
    text = ''.join(rng.choice(['ab', 'dj']) for _ in range(5000))
    search_case('rk', text, 'ab', find_all(text, 'ab'), 'ab/dj collisions')
    text = word(rng, PRINTABLE, 10000, 10000)
    search_case('rk', text, text[5000:7000], find_all(text, text[5000:7000]), 'printable')

    fibonacci = ['b', 'a']
    while len(fibonacci[-1]) < 50000:
        fibonacci.append(fibonacci[-1] + fibonacci[-2])
    n = 50000
    all_a = {'sa': list(range(n - 1, -1, -1)), 'lcp': list(range(n)), 'repeated': 'a' * (n - 1)}
    cases['suffix'].append(case('suffix all a', {'task': 'suffix', 'text': 'a' * n},
                                lambda request, answer: check(request, answer, all_a)))
    for text, label in [(word(rng, 'ab', n, n), 'random ab'), (fibonacci[-1][:n], 'Fibonacci word'),
                        (word(rng, PRINTABLE, n, n), 'printable'), (('abc' * n)[:n], 'period 3')]:
        cases['suffix'].append(case(f'suffix n={n} {label}', {'task': 'suffix', 'text': text},
                                    lambda request, answer: verify_suffix(request['text'], answer)))

    def aho_case(patterns, texts, label):
        lengths = set(map(len, patterns))
        rows = []
        for text in texts:
            windows = Counter(text[i:i + k] for k in lengths for i in range(len(text) - k + 1))
            rows.append([windows[p] for p in patterns])
        cases['aho'].append(case(f'aho {label}', {'task': 'aho', 'patterns': patterns, 'texts': texts},
                                 expect({'counts': rows})))

    dense = ['a' * k for k in range(1, 447)]
    cases['aho'].append(case('aho dense a^k x 100 texts', {'task': 'aho', 'patterns': dense, 'texts': ['a' * 2000] * 100},
                             expect({'counts': [[2001 - k for k in range(1, 447)]] * 100})))
    aho_case([word(rng, 'ab', 10, 10) for _ in range(10000)], [word(rng, 'ab', 2000, 2000) for _ in range(100)],
             '10000 patterns with duplicates')
    text = word(rng, 'abc', 200000, 200000)
    patterns = []
    while sum(map(len, patterns)) < 99980:
        i = rng.randrange(len(text) - 20)
        patterns.append(text[i:i + rng.randint(1, 19)])
    aho_case(patterns[:10000], [text], 'one 200000 text')
    texts = [word(rng, PRINTABLE, 2000, 2000) for _ in range(100)]
    aho_case([t[i:i + 100] for t in texts for i in range(0, 1000, 100)], texts, 'printable length 100')
    return cases


def run_batch(command, requests):
    started = time.perf_counter()
    try:
        answers = execute(command, requests)
    except (subprocess.TimeoutExpired, OSError, ValueError) as error:
        print(f'      batch failed: {str(error).splitlines()[0]}')
        answers = [{}] * len(requests)
    return answers, time.perf_counter() - started


def passes(verify, request, answer):
    try:
        return bool(verify(request, answer))
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def report(label, passed, total, seconds=None):
    status = 'PASS' if passed == total else 'FAIL'
    timing = f'{seconds:6.2f} s' if seconds is not None else ''
    print(f'{status}  {label:<44} {passed:>4}/{total:<4} {timing}')
    return passed == total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language')
    parser.add_argument('--verbose', action='store_true', help='print actual fixture outputs')
    args = parser.parse_args()
    command = build(select_language(args.language))
    ok = True

    fixtures = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))
    consistent = sum(check(c['input'], c['output'], oracle.expected(c['input'])) for c in fixtures)
    ok &= report('fixture expectations agree with oracle', consistent, len(fixtures))
    requests = [c['input'] for c in fixtures]
    answers, seconds = run_batch(command, requests + requests)
    results = [check(c['input'], a, c['output']) for c, a in zip(fixtures + fixtures, answers)]
    ok &= report('fixtures, mixed batch repeated twice', sum(results), len(results), seconds)
    for name in dict.fromkeys(c['name'] for c, good in zip(fixtures + fixtures, results) if not good):
        print(f'      failed: {name}')
    if args.verbose:
        for c, a in zip(fixtures, answers):
            print(f'  {c["name"]}: {json.dumps(a, separators=(",", ":"))}')

    rng = random.Random(SEED)
    generated = random_requests(rng)
    for task in ('lcs', 'merge', 'tree', 'suffix', 'aho'):
        requests = generated[task]
        answers, seconds = run_batch(command, requests)
        passed = sum(check(r, a, oracle.expected(r)) for r, a in zip(requests, answers))
        ok &= report(f'random {task} vs brute force', passed, len(requests), seconds)
    pairs = generated['search']
    results = {}
    for task in ('naive', 'kmp', 'rk'):
        requests = [{'task': task, 'text': t, 'pattern': p} for t, p in pairs]
        answers, seconds = run_batch(command, requests)
        results[task] = [a.get('positions') for a in answers]
        passed = sum(check(r, a, oracle.expected(r)) for r, a in zip(requests, answers))
        ok &= report(f'random {task} vs brute force', passed, len(requests), seconds)
    same = sum(x == y == z for x, y, z in zip(results['naive'], results['kmp'], results['rk']))
    ok &= report('naive, kmp and rk give identical outputs', same, len(pairs))

    for task, cases in scale_cases(random.Random(SEED)).items():
        answers, seconds = run_batch(command, [c['input'] for c in cases])
        failed = [c['name'] for c, a in zip(cases, answers) if not passes(c['verify'], c['input'], a)]
        ok &= report(f'scale {task} (one batch)', len(cases) - len(failed), len(cases), seconds)
        for name in failed:
            print(f'      failed: {name}')

    print('ALL STUDENT TESTS PASSED' if ok else 'SOME STUDENT TESTS FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
