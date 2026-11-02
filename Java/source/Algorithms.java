import java.util.*;

public final class Algorithms {
    private static final int FIRST_CHAR = 32, ALPHABET = 95;
    private static final long BASE = 31, MOD = 101;

    private Algorithms() {}

    private interface Matcher {
        void find(String text, String pattern, List<Integer> positions);
    }

    static Map<String, Object> lcs(Map<String, Object> input) {
        String a = (String) input.get("a"), b = (String) input.get("b");
        int n = a.length(), m = b.length();
        int[][] dp = new int[n + 1][m + 1];
        for (int i = 1; i <= n; i++)
            for (int j = 1; j <= m; j++)
                dp[i][j] = a.charAt(i - 1) == b.charAt(j - 1)
                        ? dp[i - 1][j - 1] + 1
                        : Math.max(dp[i - 1][j], dp[i][j - 1]);

        char[] sequence = new char[dp[n][m]];
        for (int i = n, j = m, k = sequence.length; k > 0; ) {
            if (a.charAt(i - 1) == b.charAt(j - 1)) {
                sequence[--k] = a.charAt(i - 1);
                i--;
                j--;
            } else if (dp[i - 1][j] >= dp[i][j - 1]) {
                i--;
            } else {
                j--;
            }
        }
        return object("length", sequence.length, "sequence", new String(sequence));
    }

    static Map<String, Object> merge(Map<String, Object> input) {
        long[] sizes = longs(input.get("sizes"));
        int n = sizes.length;
        List<List<Integer>> plan = new ArrayList<>();
        if (n <= 1) return object("cost", 0L, "plan", plan);

        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) prefix[i + 1] = prefix[i] + sizes[i];

        long[][] cost = new long[n][n];
        int[][] split = new int[n][n];
        for (int len = 2; len <= n; len++) {
            for (int l = 0, r = len - 1; r < n; l++, r++) {
                cost[l][r] = Long.MAX_VALUE;
                for (int k = l; k < r; k++) {
                    long candidate = cost[l][k] + cost[k + 1][r];
                    if (candidate < cost[l][r]) {
                        cost[l][r] = candidate;
                        split[l][r] = k;
                    }
                }
                cost[l][r] += prefix[r + 1] - prefix[l];
            }
        }
        addMerges(split, 0, n - 1, plan);
        return object("cost", cost[0][n - 1], "plan", plan);
    }

    private static void addMerges(int[][] split, int l, int r, List<List<Integer>> plan) {
        if (l == r) return;
        int k = split[l][r];
        addMerges(split, l, k, plan);
        addMerges(split, k + 1, r, plan);
        plan.add(List.of(l, k, r));
    }

    static Map<String, Object> tree(Map<String, Object> input) {
        int n = Math.toIntExact((Long) input.get("n"));
        long[] weight = longs(input.get("weights"));
        List<?> edges = (List<?>) input.get("edges");
        if (n == 0) return object("weight", 0L, "selected", List.of());

        int[] from = new int[edges.size()], to = new int[edges.size()], start = new int[n + 1];
        for (int e = 0; e < edges.size(); e++) {
            long[] uv = longs(edges.get(e));
            from[e] = (int) uv[0];
            to[e] = (int) uv[1];
            start[from[e] + 1]++;
            start[to[e] + 1]++;
        }
        for (int v = 0; v < n; v++) start[v + 1] += start[v];
        int[] adjacent = new int[2 * edges.size()], fill = start.clone();
        for (int e = 0; e < edges.size(); e++) {
            adjacent[fill[from[e]]++] = to[e];
            adjacent[fill[to[e]]++] = from[e];
        }

        int root = 0;
        int[] order = new int[n], parent = new int[n];
        order[0] = root;
        parent[root] = -1;
        for (int head = 0, tail = 1; head < tail; head++) {
            int v = order[head];
            for (int i = start[v]; i < start[v + 1]; i++) {
                int u = adjacent[i];
                if (u != parent[v]) {
                    parent[u] = v;
                    order[tail++] = u;
                }
            }
        }

        long[] take = new long[n], skip = new long[n];
        for (int i = n - 1; i >= 0; i--) {
            int v = order[i];
            take[v] += weight[v];
            if (parent[v] >= 0) {
                take[parent[v]] += skip[v];
                skip[parent[v]] += Math.max(take[v], skip[v]);
            }
        }

        boolean[] chosen = new boolean[n];
        List<Integer> selected = new ArrayList<>();
        for (int v : order) {
            chosen[v] = (parent[v] < 0 || !chosen[parent[v]]) && take[v] > skip[v];
            if (chosen[v]) selected.add(v);
        }
        return object("weight", Math.max(take[root], skip[root]), "selected", selected);
    }

    static Map<String, Object> naive(Map<String, Object> input) {
        return search(input, Algorithms::naiveSearch);
    }

    static Map<String, Object> kmp(Map<String, Object> input) {
        return search(input, Algorithms::kmpSearch);
    }

    static Map<String, Object> rk(Map<String, Object> input) {
        return search(input, Algorithms::rabinKarpSearch);
    }

    private static Map<String, Object> search(Map<String, Object> input, Matcher matcher) {
        String text = (String) input.get("text"), pattern = (String) input.get("pattern");
        List<Integer> positions = new ArrayList<>();
        if (pattern.isEmpty()) {
            for (int i = 0; i <= text.length(); i++) positions.add(i);
        } else if (pattern.length() <= text.length()) {
            matcher.find(text, pattern, positions);
        }
        return object("positions", positions);
    }

    private static void naiveSearch(String text, String pattern, List<Integer> positions) {
        for (int i = 0; i + pattern.length() <= text.length(); i++)
            if (matchesAt(text, pattern, i)) positions.add(i);
    }

    private static boolean matchesAt(String text, String pattern, int start) {
        for (int j = 0; j < pattern.length(); j++)
            if (text.charAt(start + j) != pattern.charAt(j)) return false;
        return true;
    }

    private static void kmpSearch(String text, String pattern, List<Integer> positions) {
        int[] pi = prefixFunction(pattern);
        int m = pattern.length();
        for (int i = 0, k = 0; i < text.length(); i++) {
            while (k > 0 && text.charAt(i) != pattern.charAt(k)) k = pi[k - 1];
            if (text.charAt(i) == pattern.charAt(k)) k++;
            if (k == m) {
                positions.add(i - m + 1);
                k = pi[k - 1];
            }
        }
    }

    private static int[] prefixFunction(String pattern) {
        int[] pi = new int[pattern.length()];
        for (int i = 1, k = 0; i < pattern.length(); i++) {
            while (k > 0 && pattern.charAt(i) != pattern.charAt(k)) k = pi[k - 1];
            if (pattern.charAt(i) == pattern.charAt(k)) k++;
            pi[i] = k;
        }
        return pi;
    }

    private static void rabinKarpSearch(String text, String pattern, List<Integer> positions) {
        int n = text.length(), m = pattern.length();
        long target = 0, window = 0, lead = 1;
        for (int i = 0; i < m; i++) {
            target = (target * BASE + pattern.charAt(i)) % MOD;
            window = (window * BASE + text.charAt(i)) % MOD;
            if (i > 0) lead = lead * BASE % MOD;
        }
        for (int i = 0; i + m <= n; i++) {
            if (i > 0) {
                window = Math.floorMod(window - text.charAt(i - 1) * lead, MOD);
                window = (window * BASE + text.charAt(i + m - 1)) % MOD;
            }
            if (window == target && matchesAt(text, pattern, i)) positions.add(i);
        }
    }

    static Map<String, Object> suffix(Map<String, Object> input) {
        String text = (String) input.get("text");
        int[] sa = suffixArray(text);
        int[] lcp = kasai(text, sa);
        int best = 0;
        for (int i = 1; i < lcp.length; i++)
            if (lcp[i] > lcp[best]) best = i;
        String repeated = lcp.length == 0 ? "" : text.substring(sa[best], sa[best] + lcp[best]);
        return object("sa", boxed(sa), "lcp", boxed(lcp), "repeated", repeated);
    }

    private static int[] suffixArray(String s) {
        int n = s.length();
        int[] sa = new int[n], rank = new int[n], buffer = new int[n];
        if (n == 0) return sa;

        int[] count = new int[FIRST_CHAR + ALPHABET];
        for (int i = 0; i < n; i++) count[s.charAt(i)]++;
        for (int c = 1; c < count.length; c++) count[c] += count[c - 1];
        for (int i = n - 1; i >= 0; i--) sa[--count[s.charAt(i)]] = i;

        int classes = 1;
        for (int i = 1; i < n; i++) {
            if (s.charAt(sa[i]) != s.charAt(sa[i - 1])) classes++;
            rank[sa[i]] = classes - 1;
        }

        for (int k = 1; classes < n; k <<= 1) {
            int filled = 0;
            for (int i = n - k; i < n; i++) buffer[filled++] = i;
            for (int i : sa) if (i >= k) buffer[filled++] = i - k;

            count = new int[classes];
            for (int i = 0; i < n; i++) count[rank[i]]++;
            for (int c = 1; c < classes; c++) count[c] += count[c - 1];
            for (int i = n - 1; i >= 0; i--) sa[--count[rank[buffer[i]]]] = buffer[i];

            buffer[sa[0]] = 0;
            classes = 1;
            for (int i = 1; i < n; i++) {
                int a = sa[i - 1], b = sa[i];
                if (rank[a] != rank[b] || secondRank(rank, a + k) != secondRank(rank, b + k)) classes++;
                buffer[b] = classes - 1;
            }
            int[] swap = rank;
            rank = buffer;
            buffer = swap;
        }
        return sa;
    }

    private static int secondRank(int[] rank, int i) {
        return i < rank.length ? rank[i] : -1;
    }

    private static int[] kasai(String s, int[] sa) {
        int n = s.length();
        int[] position = new int[n], lcp = new int[n];
        for (int i = 0; i < n; i++) position[sa[i]] = i;
        for (int i = 0, h = 0; i < n; i++) {
            if (position[i] == 0) {
                h = 0;
                continue;
            }
            int j = sa[position[i] - 1];
            while (i + h < n && j + h < n && s.charAt(i + h) == s.charAt(j + h)) h++;
            lcp[position[i]] = h;
            if (h > 0) h--;
        }
        return lcp;
    }

    static Map<String, Object> aho(Map<String, Object> input) {
        List<?> patterns = (List<?>) input.get("patterns"), texts = (List<?>) input.get("texts");
        int capacity = 1;
        for (Object pattern : patterns) capacity += ((String) pattern).length();

        int[] next = new int[capacity * ALPHABET], terminal = new int[patterns.size()];
        int states = 1;
        for (int p = 0; p < patterns.size(); p++) {
            int v = 0;
            for (char c : ((String) patterns.get(p)).toCharArray()) {
                int slot = v * ALPHABET + c - FIRST_CHAR;
                if (next[slot] == 0) next[slot] = states++;
                v = next[slot];
            }
            terminal[p] = v;
        }

        int[] fail = new int[states], order = new int[states];
        for (int head = 0, tail = 1; head < tail; head++) {
            int v = order[head];
            for (int c = 0; c < ALPHABET; c++) {
                int slot = v * ALPHABET + c, child = next[slot];
                int viaFail = v == 0 ? 0 : next[fail[v] * ALPHABET + c];
                if (child == 0) {
                    next[slot] = viaFail;
                } else {
                    fail[child] = viaFail;
                    order[tail++] = child;
                }
            }
        }

        List<List<Long>> counts = new ArrayList<>();
        long[] visits = new long[states];
        for (Object text : texts) {
            Arrays.fill(visits, 0);
            int v = 0;
            for (char c : ((String) text).toCharArray()) {
                v = next[v * ALPHABET + c - FIRST_CHAR];
                visits[v]++;
            }
            for (int i = states - 1; i > 0; i--) visits[fail[order[i]]] += visits[order[i]];
            List<Long> row = new ArrayList<>(terminal.length);
            for (int state : terminal) row.add(visits[state]);
            counts.add(row);
        }
        return object("counts", counts);
    }

    private static long[] longs(Object value) {
        List<?> list = (List<?>) value;
        long[] result = new long[list.size()];
        for (int i = 0; i < result.length; i++) result[i] = ((Number) list.get(i)).longValue();
        return result;
    }

    private static List<Integer> boxed(int[] values) {
        return Arrays.stream(values).boxed().toList();
    }

    private static Map<String, Object> object(Object... entries) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = 0; i < entries.length; i += 2) result.put((String) entries[i], entries[i + 1]);
        return result;
    }
}
