// HA installs its custom-element registry and HTMLElement shim during startup.
// Define the card only after that setup, including on a full dashboard navigation.
await customElements.whenDefined("home-assistant");
const cardUrl = new URL("./ha-pop-panel-card.js", import.meta.url);
cardUrl.search = new URL(import.meta.url).search;
await import(cardUrl.href);
