import java.util.*;

public final class SearchBenchmark {
    private static final long SEED = 2026;
    private static final int[] SIZES = {750, 1500, 3000};
    private static final String[] METHODS = {"naive", "kmp", "rk"};
    private static final int WARMUP_CALLS = 500, RUNS = 5;
    private static final double RUN_NANOS = 20e6;
    private static long blackhole;

    private record Case(String label, String text, String pattern, List<Integer> expected, int candidates) {}

    public static void main(String[] args) {
        List<Case> cases = cases(new Random(SEED));
        for (Case c : cases)
            for (String method : METHODS)
                if (!positions(invoke(method, c)).equals(c.expected()))
                    throw new IllegalStateException(method + " is wrong on " + c.label());

        for (int i = 0; i < WARMUP_CALLS; i++)
            for (Case c : cases)
                for (String method : METHODS) blackhole += positions(invoke(method, c)).size();

        System.out.printf("Java %s, %s %s, %d CPUs, seed %d%n", System.getProperty("java.version"),
                System.getProperty("os.name"), System.getProperty("os.arch"),
                Runtime.getRuntime().availableProcessors(), SEED);
        System.out.printf("Microseconds per call; each run lasts about %.0f ms; %d warm-up rounds over all cases.%n%n",
                RUN_NANOS / 1e6, WARMUP_CALLS);
        System.out.println("|Case|n|m|Algorithm|Calls/run|Run 1|Run 2|Run 3|Run 4|Run 5|Median|Matches|RK candidates|Outputs identical|");
        System.out.println("|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|");
        for (Case c : cases) {
            int[] calls = new int[METHODS.length];
            for (int k = 0; k < METHODS.length; k++) calls[k] = calibrate(METHODS[k], c);
            double[][] runs = new double[METHODS.length][RUNS];
            for (int run = 0; run < RUNS; run++)
                for (int k = 0; k < METHODS.length; k++) runs[k][run] = timeCalls(METHODS[k], c, calls[k]);
            for (int k = 0; k < METHODS.length; k++) printRow(c, METHODS[k], calls[k], runs[k]);
        }
        System.out.println();
        System.out.println("checksum " + blackhole);
    }

    private static List<Case> cases(Random random) {
        List<Case> cases = new ArrayList<>();
        for (int n : SIZES) {
            String text = randomText(random, "acgt", n);
            int start = random.nextInt(n - n / 10 + 1);
            cases.add(newCase("random acgt, pattern cut from text", text, text.substring(start, start + n / 10)));
        }
        for (int n : SIZES) cases.add(newCase("repetitive hit a^n / a^m", "a".repeat(n), "a".repeat(n / 10)));
        for (int n : SIZES)
            cases.add(newCase("repetitive miss a^n / a^(m-1)b", "a".repeat(n), "a".repeat(n / 10 - 1) + "b"));
        return cases;
    }

    private static Case newCase(String label, String text, String pattern) {
        List<Integer> expected = new ArrayList<>();
        for (int i = 0; i + pattern.length() <= text.length(); i++)
            if (text.startsWith(pattern, i)) expected.add(i);
        int candidates = 0;
        for (int i = 0; i + pattern.length() <= text.length(); i++)
            if (hash(text, i, pattern.length()) == hash(pattern, 0, pattern.length())) candidates++;
        return new Case(label, text, pattern, expected, candidates);
    }

    private static long hash(String s, int from, int length) {
        long h = 0;
        for (int i = from; i < from + length; i++) h = (h * 31 + s.charAt(i)) % 101;
        return h;
    }

    private static int calibrate(String method, Case c) {
        double perCall = timeCalls(method, c, 20) * 1000.0;
        return (int) Math.max(20, Math.ceil(RUN_NANOS / perCall));
    }

    private static double timeCalls(String method, Case c, int calls) {
        long begin = System.nanoTime();
        for (int i = 0; i < calls; i++) blackhole += positions(invoke(method, c)).size();
        return (System.nanoTime() - begin) / 1000.0 / calls;
    }

    private static Map<String, Object> invoke(String method, Case c) {
        Map<String, Object> request = Map.of("task", method, "text", c.text(), "pattern", c.pattern());
        switch (method) {
            case "naive": return Algorithms.naive(request);
            case "kmp": return Algorithms.kmp(request);
            default: return Algorithms.rk(request);
        }
    }

    @SuppressWarnings("unchecked")
    private static List<Integer> positions(Map<String, Object> result) {
        return (List<Integer>) result.get("positions");
    }

    private static void printRow(Case c, String method, int calls, double[] runs) {
        double[] sorted = runs.clone();
        Arrays.sort(sorted);
        StringBuilder row = new StringBuilder(String.format("|%s|%d|%d|%s|%d", c.label(), c.text().length(),
                c.pattern().length(), method, calls));
        for (double t : runs) row.append(String.format("|%.1f", t));
        row.append(String.format("|**%.1f**|%d|%d|yes|", sorted[RUNS / 2], c.expected().size(), c.candidates()));
        System.out.println(row);
    }

    private static String randomText(Random random, String alphabet, int length) {
        StringBuilder text = new StringBuilder(length);
        for (int i = 0; i < length; i++) text.append(alphabet.charAt(random.nextInt(alphabet.length())));
        return text.toString();
    }
}
