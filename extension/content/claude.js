// Selectors are best-effort -- claude.ai's DOM changes over time. If the
// badge can't find the composer, open DevTools, inspect the input box, and
// update findComposer() below before the demo.
initMemoryPassport({
  toolLabel: "Claude",
  source: "claude",
  findComposer: () =>
    document.querySelector('div[contenteditable="true"][role="textbox"]') ||
    document.querySelector('div[contenteditable="true"]') ||
    document.querySelector("textarea"),
});
