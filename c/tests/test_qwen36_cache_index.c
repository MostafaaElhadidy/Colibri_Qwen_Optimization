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
    check_lookup_scaling(44);
    check_lookup_scaling(219);
    if (failures) { fprintf(stderr,"qwen36 cache index: %d failure(s)\n", failures); return 1; }
    puts("qwen36 cache index: ok");
    return 0;
}
