/**
 * The test suite does not get a network.
 *
 * The builds carry a live sync endpoint as of v0.1.38, and Node has a global
 * fetch. Four tests boot a whole build and play it, so without this every run
 * of run.sh posted its stubbed kindles and banishes to the production table —
 * junk from a device that does not exist, filed beside real handwriting.
 *
 * Preloaded by run.sh through NODE_OPTIONS, so it covers every test and any
 * added later. A test that wants a fetch passes its own (sync.test.mjs does).
 * Rejecting is the right stub: to the outbox, offline is Tuesday.
 */
let attempts = 0;
globalThis.fetch = () => { attempts++; return Promise.reject(new Error('the test suite is offline')); };
globalThis.__offline = { get attempts(){ return attempts; } };
