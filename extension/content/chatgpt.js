// Selectors are best-effort -- ChatGPT's DOM changes over time. If the badge
// can't find the composer, open DevTools, inspect the input box, and update
// findComposer() below before the demo.
initMemoryPassport({
  toolLabel: "ChatGPT",
  source: "chatgpt",
  findComposer: () =>
    document.querySelector("#prompt-textarea") ||
    document.querySelector('div[contenteditable="true"]') ||
    document.querySelector("textarea"),
});
