/**
 * LaclauGPT Brazil Collector — content script: window scrolling.
 * Small helper called by the background tour to scroll the visited
 * account page (lazy-feed pagination trigger).
 */

browser.runtime.onMessage.addListener((msg) => {
  if (msg && msg.action === "scroll") {
    window.scrollTo(0, document.body.scrollHeight);
    return Promise.resolve("scrolled");
  }
  return undefined;
});