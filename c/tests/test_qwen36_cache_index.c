/* Model-free regression for Qwen3.6's expert -> slot index. */
#define COLI_CACHE_INDEX_TEST 1
#define main qwen36_main_unused
#include "../qwen36.c"
#undef main

static int failures;
#define CHECK(cond, ...) do { if (!(cond)) { \
    fprintf(stderr,"FAIL %s:%d: ",__FILE__,__LINE__); \
    fprintf(stderr,__VA_ARGS__); fputc('\n',stderr); failures++; } } while (0)

static void init_cache(Model *m, int experts, int cap) {
    memset(m, 0, sizeof(*m));
    m->c.n_layers = 1; m->c.n_experts = experts;
    m->cache = calloc(1, sizeof(LCache));
    LCache *lc = &m->cache[0]; lc->cap = cap;
    lc->slots = calloc((size_t)cap, sizeof(Slot));
    lc->slot_by_expert = malloc((size_t)experts * sizeof(int));
    for (int e = 0; e < experts; e++) lc->slot_by_expert[e] = -1;
}

static void free_cache(Model *m) {
    free(m->cache[0].slot_by_expert);
    free(m->cache[0].slots);
    free(m->cache);
}

static void check_lookup_scaling(int cap) {
    Model m; init_cache(&m, cap, cap); LCache *lc = &m.cache[0]; lc->n = cap;
    for (int i = 0; i < cap; i++) cache_publish(&m, 0, &lc->slots[i], i);
    g_slot_index_probes = 0;
    CHECK(slot_indexed(&m, 0, cap-1) == &lc->slots[cap-1],
          "last-slot lookup failed at cap %d", cap);
    CHECK(g_slot_index_probes == 1,
          "indexed lookup used %llu probes at cap %d, expected 1",
          (unsigned long long)g_slot_index_probes, cap);
    printf("qwen36 lookup probes: cap=%d indexed=%llu legacy-worst=%d\n",
           cap, (unsigned long long)g_slot_index_probes, cap);
    free_cache(&m);
}

/* The eviction rule the demand path and the PILOT worker share: a slot a moe
 * run is computing from (held) or one being loaded is never given up, and a
 * pinned one only when nothing unpinned is left. */
static void check_victim(void) {
    Model m; init_cache(&m, 6, 3); LCache *lc = &m.cache[0]; lc->n = 3;
    for (int i = 0; i < 3; i++) { cache_publish(&m, 0, &lc->slots[i], i); lc->slots[i].used = (uint64_t)(i + 1); }
    CHECK(slot_victim(lc, 0, 0) == 0, "LRU victim is not the oldest slot");

    Slot *h = expert_hold(&m, 0, 0);      /* a resident expert: the hit path holds too */
    CHECK(h == &lc->slots[0] && slot_busy(h), "expert_hold did not hold the resident slot");
    CHECK(slot_victim(lc, 0, 0) == 1 && slot_victim(lc, 0, 1) == 1, "a held slot was chosen for eviction");

    lc->slots[1].pinned = 1; slot_hold(&lc->slots[2]); slot_hold(&lc->slots[2]);   /* routed twice in one run */
    CHECK(slot_victim(lc, 0, 0) == -1, "an unpinned victim came from pinned and held slots");
    CHECK(slot_victim(lc, 0, 1) == 1, "the pinned fallback missed the one pinned free slot");
    cache_hide(&m, 0, &lc->slots[1]);    /* now being loaded */
    CHECK(slot_victim(lc, 0, 1) == -1, "a slot being loaded was chosen for eviction");

    slot_release(&lc->slots[2]);
    CHECK(slot_victim(lc, 0, 1) == -1, "one release freed a slot held twice");
    slot_release(&lc->slots[2]);
    CHECK(slot_victim(lc, 0, 1) == 2, "a fully released slot stayed unevictable");
    slot_release(h);
    CHECK(slot_victim(lc, 0, 1) == 0, "the released oldest slot is not the victim");
    free_cache(&m);
}

/* COLI_Q36_MISS_QD: expert_hold_batch must decide what n expert_hold calls in
 * order decide -- the same expert in the same slot, the same LRU order, the same
 * hit/miss counts -- and still read the misses concurrently. A stub stands in for
 * the container read: it writes the expert id into the slot's scales and sleeps
 * long enough for loads to overlap. */
static int g_inflight, g_inflight_max;
static int g_expect_held;   /* the batch holds a slot while it loads; the serial path only hides it */
static pthread_mutex_t g_stub_mx = PTHREAD_MUTEX_INITIALIZER;
static void stub_load(Model *m, int layer, int eid, Slot *s) {
    (void)m; (void)layer;
    pthread_mutex_lock(&g_stub_mx);
    if (++g_inflight > g_inflight_max) g_inflight_max = g_inflight;
    int bad = s->eid != -1 || (g_expect_held && !slot_busy(s));
    pthread_mutex_unlock(&g_stub_mx);
    CHECK(!bad, "a miss was read into a slot that was not hidden%s", g_expect_held ? " and held" : "");
    s->gs[0] = (float)eid;
    sleep_ms(2);
    pthread_mutex_lock(&g_stub_mx); g_inflight--; pthread_mutex_unlock(&g_stub_mx);
}

static void init_batch_model(Model *m, int experts, int cap) {
    init_cache(m, experts, cap);
    m->c.inter = 64; m->c.hidden = 64; m->c.topk = 8;
    m->is_pinned = calloc((size_t)experts, 1);
}

static void free_batch_model(Model *m) {
    LCache *lc = &m->cache[0];
    for (int i = 0; i < lc->n; i++) { free(lc->slots[i].pw); free(lc->slots[i].g); free(lc->slots[i].gs); }
    for (int l = 0; m->ehit && l < m->c.n_layers; l++) free(m->ehit[l]);
    free(m->ehit); free(m->is_pinned);
    free_cache(m);
}

static unsigned xorshift(unsigned *s) { *s ^= *s << 13; *s ^= *s >> 17; *s ^= *s << 5; return *s; }

/* slot contents, LRU order and counters: the state the next decision depends on */
static int same_cache_state(Model *a, Model *b) {
    LCache *x = &a->cache[0], *y = &b->cache[0];
    if (x->n != y->n || a->hits != b->hits || a->miss != b->miss) return 0;
    for (int i = 0; i < x->n; i++) {
        Slot *p = &x->slots[i], *q = &y->slots[i];
        if (p->eid != q->eid || p->pinned != q->pinned || p->gs[0] != q->gs[0]) return 0;
        for (int j = 0; j < x->n; j++)
            if ((p->used < x->slots[j].used) != (q->used < y->slots[j].used)) return 0;
    }
    return 1;
}

static void check_batch_matches_serial(void) {
    enum { E = 24, CAP = 10, RUNS = 500 };
    Model a, b; init_batch_model(&a, E, CAP); init_batch_model(&b, E, CAP);
    a.is_pinned[3] = b.is_pinned[3] = 1;             /* one pinned expert in the mix */
    g_test_load = stub_load;
    unsigned rng = 20261026u;
    int ids[8]; Slot *ha[8], *hb[8];
    for (int r = 0; r < RUNS; r++) {
        int n = 1 + (int)(xorshift(&rng) % 8);
        for (int i = 0; i < n; i++) {                /* a hot set, a cold tail, repeats, unrouted */
            unsigned v = xorshift(&rng) % 40;
            ids[i] = v >= 36 ? -1 : (int)(v < 20 ? v % 6 : v % E);
        }
        for (int i = 0; i < n; i++) ha[i] = ids[i] >= 0 ? expert_hold(&a, 0, ids[i]) : NULL;
        g_expect_held = 1; expert_hold_batch(&b, 0, ids, n, hb, 4); g_expect_held = 0;
        for (int i = 0; i < n; i++) {
            if (ids[i] < 0) { CHECK(hb[i] == NULL, "run %d: an unrouted pair got a slot", r); continue; }
            CHECK(hb[i] && hb[i]->eid == ids[i] && hb[i]->gs[0] == (float)ids[i] && slot_busy(hb[i]),
                  "run %d pair %d: batch did not hold expert %d", r, i, ids[i]);
            CHECK(hb[i] - b.cache[0].slots == ha[i] - a.cache[0].slots,
                  "run %d pair %d: batch put expert %d in another slot than the serial path", r, i, ids[i]);
        }
        for (int i = 0; i < n; i++) { if (ha[i]) slot_release(ha[i]); if (hb[i]) slot_release(hb[i]); }
        CHECK(same_cache_state(&a, &b), "run %d: batch and serial caches diverged", r);
        if (failures) break;
    }
    printf("qwen36 miss batch: %d runs, hits=%llu miss=%llu, identical to the serial path\n", RUNS,
           (unsigned long long)b.hits, (unsigned long long)b.miss);
    free_batch_model(&a); free_batch_model(&b);

    /* eight cold experts, qd=4: the reads must overlap */
    Model c; init_batch_model(&c, E, CAP);
    int cold[8] = {10, 11, 12, 13, 14, 15, 16, 17}; Slot *hc[8];
    g_inflight_max = 0;
    g_expect_held = 1; expert_hold_batch(&c, 0, cold, 8, hc, 4); g_expect_held = 0;
    CHECK(g_inflight_max >= 2, "misses were read one at a time (max in flight %d)", g_inflight_max);
    CHECK(c.miss == 8 && c.hits == 0, "8 cold experts counted hits=%llu miss=%llu",
          (unsigned long long)c.hits, (unsigned long long)c.miss);
    for (int i = 0; i < 8; i++) slot_release(hc[i]);
    printf("qwen36 miss batch: max reads in flight %d at qd=4\n", g_inflight_max);
    free_batch_model(&c);
    g_test_load = NULL;
}


/* COLI_Q36_PREFILL_WAVES: a prompt chunk computed expert by expert must give the
 * token-at-a-time path's bits, compute every routed (token, k) pair exactly once,
 * and read no expert twice in one layer pass. Real expert_ffn kernels on synthetic
 * int4 experts: the stub writes each expert's bytes from its id. */
enum { WV_D = 64, WV_F = 64, WV_K = 8, WV_E = 24 };
static int g_wv_loads[WV_E];
static void wv_fill(int eid, Slot *s) {
    unsigned h = 2166136261u ^ (unsigned)eid * 16777619u;
    size_t nw = (size_t)3 * WV_F * WV_D / 2;
    for (size_t i = 0; i < nw; i++) { h ^= h << 13; h ^= h >> 17; h ^= h << 5; s->pw[i] = (uint8_t)h; }
    for (int i = 0; i < 3 * WV_F; i++) { h ^= h << 13; h ^= h >> 17; h ^= h << 5; s->gs[i] = 0.002f + (h % 1000) * 1e-5f; }
}
static void wv_stub_load(Model *m, int layer, int eid, Slot *s) {
    (void)m; (void)layer;
    pthread_mutex_lock(&g_stub_mx); g_wv_loads[eid]++; pthread_mutex_unlock(&g_stub_mx);
    CHECK(s->eid == -1, "a wave miss was read into a slot that was not hidden");
    wv_fill(eid, s);
}
static void wv_model(Model *m, int cap) {
    init_cache(m, WV_E, cap);
    m->c.hidden = WV_D; m->c.inter = WV_F; m->c.topk = WV_K; m->c.expert_gs = 64;
    m->is_pinned = calloc(WV_E, 1);
    LCache *lc = &m->cache[0];
    for (int i = 0; i < cap; i++) {   /* the planar slots slot_ensure_allocated gives a real container */
        Slot *s = &lc->slots[i];
        s->pw = malloc((size_t)3 * WV_F * WV_D / 2); s->gs = malloc(sizeof(float) * 3 * WV_F);
        s->us = s->gs + WV_F; s->ds = s->gs + 2 * WV_F; s->is_int4 = 1;
    }
}
static void wv_free(Model *m) {
    LCache *lc = &m->cache[0];
    for (int i = 0; i < lc->cap; i++) { free(lc->slots[i].pw); free(lc->slots[i].gs); }
    for (int l = 0; m->ehit && l < m->c.n_layers; l++) free(m->ehit[l]);
    free(m->ehit); free(m->is_pinned); free_cache(m);
}
static void check_waves_case(int S, int cap, int chunk, int headroom, int qd, int passes, unsigned seed) {
    float *x = malloc(sizeof(float) * S * WV_D), *val = malloc(sizeof(float) * S * WV_K);
    int *idx = malloc(sizeof(int) * S * WV_K);
    float *oa = calloc((size_t)S * WV_D, sizeof(float)), *ob = calloc((size_t)S * WV_D, sizeof(float));
    Model a, b; wv_model(&a, cap); wv_model(&b, cap);
    g_test_load = wv_stub_load; g_q36_miss_qd = qd;
    unsigned rng = seed;
    for (int pass = 0; pass < passes; pass++) {
        for (int i = 0; i < S * WV_D; i++) x[i] = (float)((int)(xorshift(&rng) % 2001) - 1000) / 250.f;
        for (int s = 0; s < S; s++) {                /* distinct experts, a hot set and a tail */
            float sum = 0;
            for (int k = 0; k < WV_K; k++) {
                int e, dup;
                do { unsigned v = xorshift(&rng) % 40; e = v < 24 ? (int)(v % 10) : (int)(v % WV_E);
                     dup = 0; for (int j = 0; j < k; j++) if (idx[s * WV_K + j] == e) dup = 1; } while (dup);
                idx[s * WV_K + k] = e; val[s * WV_K + k] = 0.05f + (xorshift(&rng) % 1000) / 1000.f; sum += val[s * WV_K + k];
            }
            for (int k = 0; k < WV_K; k++) val[s * WV_K + k] /= sum;
        }
        memset(oa, 0, sizeof(float) * S * WV_D); memset(ob, 0, sizeof(float) * S * WV_D);
        g_q36_waves = 0;
        moe_xf_run(&a, 0, x, S, oa, idx, val);
        memset(g_wv_loads, 0, sizeof g_wv_loads);
        int *seen = calloc((size_t)S * WV_K, sizeof(int)); g_test_pair_seen = seen;
        g_q36_waves = 1; g_q36_waves_chunk = chunk; g_q36_waves_headroom = headroom;
        uint64_t h0 = b.hits + b.miss;
        moe_xf_run(&b, 0, x, S, ob, idx, val);
        g_test_pair_seen = NULL;
        CHECK(!memcmp(oa, ob, sizeof(float) * S * WV_D),
              "S=%d cap=%d chunk=%d qd=%d pass %d: waves output differs from the token path", S, cap, chunk, qd, pass);
        for (int i = 0; i < S * WV_K; i++)
            CHECK(seen[i] == 1, "S=%d cap=%d chunk=%d pass %d: pair %d computed %d times", S, cap, chunk, pass, i, seen[i]);
        if (chunk == 0)
            for (int e = 0; e < WV_E; e++)
                CHECK(g_wv_loads[e] <= 1, "S=%d cap=%d pass %d: expert %d read %d times in one layer pass", S, cap, pass, e, g_wv_loads[e]);
        CHECK(b.hits + b.miss - h0 == (uint64_t)S * WV_K, "hits+miss %llu for %d routed pairs",
              (unsigned long long)(b.hits + b.miss - h0), S * WV_K);
        for (int i = 0; i < cap; i++) CHECK(!slot_busy(&b.cache[0].slots[i]), "a wave left slot %d held", i);
        if (g_q36_waves_last && pass == 0 && chunk == 0 && cap - headroom >= WV_K)   /* cold cache: the last token's experts stay */
            for (int k = 0; k < WV_K; k++)
                CHECK(slot_indexed(&b, 0, idx[(S - 1) * WV_K + k]) != NULL,
                      "ORDER=last: expert %d of the final token is not resident", idx[(S - 1) * WV_K + k]);
        free(seen);
        if (failures) break;
    }
    printf("qwen36 prefill waves%s: S=%d cap=%d chunk=%d headroom=%d qd=%d, %d passes: token path %llu miss, waves %llu miss, identical bits\n",
           g_q36_waves_last ? " (order=last)" : " (order=first)", S, cap, chunk, headroom, qd, passes, (unsigned long long)a.miss, (unsigned long long)b.miss);
    g_q36_waves = 0; g_q36_waves_chunk = 0; g_q36_waves_headroom = -1; g_test_load = NULL; g_q36_miss_qd = 0;
    wv_free(&a); wv_free(&b); free(x); free(val); free(idx); free(oa); free(ob);
}
static void check_waves(void) {
    g_q36_waves_last = 0;                             /* ORDER=first: first-seen order */
    check_waves_case(37, 10, 0, 0, 0, 6, 11u);    /* serial loads */
    check_waves_case(37, 10, 0, 1, 0, 6, 12u);    /* one slot of headroom */
    check_waves_case(37, 10, 5, 0, 0, 6, 13u);    /* planned 5 tokens at a time */
    check_waves_case(64, 9, 0, 0, 0, 4, 14u);     /* cap just above K */
    check_waves_case(300, 12, 0, 0, 0, 2, 15u);   /* more pairs than one kernel call takes */
    check_waves_case(9, 5, 0, 0, 0, 6, 16u);      /* cap < K: the token path runs pair by pair */
    check_waves_case(37, 10, 0, 0, 4, 6, 17u);    /* misses through expert_hold_batch, qd=4 */
    check_waves_case(300, 12, 64, 0, 8, 2, 18u);  /* batched, planned 64 tokens at a time */
    g_q36_waves_last = 1;                             /* the default, last use: same bits, last token's experts resident */
    check_waves_case(37, 10, 0, 0, 0, 6, 21u);
    check_waves_case(300, 12, 0, 0, 8, 2, 22u);
    check_waves_case(37, 10, 5, 1, 4, 6, 23u);
}

int main(void) {
    Model m; init_cache(&m, 6, 2); LCache *lc = &m.cache[0]; lc->n = 2;
    cache_publish(&m, 0, &lc->slots[0], 1);
    cache_publish(&m, 0, &lc->slots[1], 2);
    CHECK(slot_indexed(&m, 0, 1) == &lc->slots[0] &&
          slot_indexed(&m, 0, 2) == &lc->slots[1], "initial publication mismatch");

    cache_hide(&m, 0, &lc->slots[0]);
    CHECK(lc->slot_by_expert[1] == -1 && slot_indexed(&m, 0, 1) == NULL,
          "in-flight slot retained the evicted mapping");
    cache_publish(&m, 0, &lc->slots[0], 3);
    CHECK(slot_indexed(&m, 0, 2) == &lc->slots[1] &&
          slot_indexed(&m, 0, 3) == &lc->slots[0], "reuse damaged the index");

    lc->slot_by_expert[4] = 1;
    CHECK(slot_indexed(&m, 0, 4) == NULL, "stale entry served wrong weights");
    CHECK(slot_indexed(&m, 0, -1) == NULL && slot_indexed(&m, 0, 6) == NULL,
          "out-of-range lookup was accepted");

    free_cache(&m);
    check_victim();
    check_batch_matches_serial();
    check_waves();
    check_lookup_scaling(44);
    check_lookup_scaling(219);
    if (failures) { fprintf(stderr,"qwen36 cache index: %d failure(s)\n", failures); return 1; }
    puts("qwen36 cache index: ok");
    return 0;
}
