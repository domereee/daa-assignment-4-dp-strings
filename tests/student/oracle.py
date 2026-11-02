"""Independent brute-force reference answers for small inputs."""
from functools import cache


def is_subsequence(s, text):
    it = iter(text)
    return all(c in it for c in s)


def lcs(a, b):
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    best = ''
    for mask in range(1 << len(short)):
        candidate = ''.join(c for i, c in enumerate(short) if mask >> i & 1)
        if len(candidate) > len(best) and is_subsequence(candidate, long):
            best = candidate
    return {'length': len(best), 'sequence': best}


def merge(sizes):
    @cache
    def cheapest(blocks):
        if len(blocks) <= 1:
            return 0
        return min(blocks[i] + blocks[i + 1] +
                   cheapest(blocks[:i] + (blocks[i] + blocks[i + 1],) + blocks[i + 2:])
                   for i in range(len(blocks) - 1))
    return {'cost': cheapest(tuple(sizes))}


def tree(n, weights, edges):
    best = 0
    for mask in range(1 << n):
        if not any(mask >> u & 1 and mask >> v & 1 for u, v in edges):
            best = max(best, sum(weights[v] for v in range(n) if mask >> v & 1))
    return {'weight': best}


def search(text, pattern):
    m = len(pattern)
    return {'positions': [i for i in range(len(text) - m + 1) if text[i:i + m] == pattern]}


def suffix(text):
    n = len(text)
    sa = sorted(range(n), key=lambda i: text[i:])
    lcp = [0] * n
    for r in range(1, n):
        a, b = text[sa[r - 1]:], text[sa[r]:]
        while lcp[r] < min(len(a), len(b)) and a[lcp[r]] == b[lcp[r]]:
            lcp[r] += 1
    repeated = ''
    for i in range(n):
        for j in range(i + 1, n):
            k = 0
            while j + k < n and text[i + k] == text[j + k]:
                k += 1
            if k > len(repeated):
                repeated = text[i:i + k]
    return {'sa': sa, 'lcp': lcp, 'repeated': repeated}


def aho(patterns, texts):
    return {'counts': [[sum(text.startswith(p, i) for i in range(len(text))) for p in patterns]
                       for text in texts]}


def expected(request):
    task = request['task']
    if task == 'lcs':
        return lcs(request['a'], request['b'])
    if task == 'merge':
        return merge(request['sizes'])
    if task == 'tree':
        return tree(request['n'], request['weights'], request['edges'])
    if task in ('naive', 'kmp', 'rk'):
        return search(request['text'], request['pattern'])
    if task == 'suffix':
        return suffix(request['text'])
    if task == 'aho':
        return aho(request['patterns'], request['texts'])
    raise ValueError(task)
