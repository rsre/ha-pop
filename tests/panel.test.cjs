const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");

const context = vm.createContext({
  HTMLElement: class { attachShadow() { this.shadowRoot = {}; } addEventListener() {} },
  customElements: { get: () => undefined, define: () => {} },
  window: {},
  URL,
});
vm.runInContext(fs.readFileSync("frontend/ha-pop-panel.js", "utf8") + "\nglobalThis.Panel = HaPopPanel;", context);

function panel(overrides = {}) {
  const card = new context.Panel();
  card.setConfig(overrides);
  card._update = () => {};
  return card;
}

test("switches use their actual state and configured entity", async () => {
  const card = panel({ entities: { kitchen_1: "light.counter" } });
  const calls = [];
  card._hass = { states: { "light.counter": { state: "off" } }, callService: async (...args) => calls.push(args) };
  await card._toggle("kitchen_1");
  assert.equal(calls[0][0], "light");
  assert.equal(calls[0][1], "turn_on");
  assert.equal(calls[0][2].entity_id, "light.counter");
  card._hass.states["light.counter"].state = "on";
  await card._toggle("kitchen_1");
  assert.equal(calls[1][1], "turn_off");
});

test("missing, unavailable, and offline controls never send a command", async () => {
  const card = panel();
  card._hass = { states: {}, callService: () => { throw Error("Must not call a service"); } };
  await card._toggle("kitchen_1");
  card._hass.states[card._entities.kitchen_1] = { state: "unavailable" };
  await card._toggle("kitchen_1");
  card._hass.states[card._entities.kitchen_1].state = "off";
  card._hass.connection = { connected: false };
  await card._toggle("kitchen_1");
});

test("repeated taps cannot send duplicate pending commands", async () => {
  const card = panel();
  let calls = 0;
  let resolve;
  card._hass = { states: { [card._entities.kitchen_1]: { state: "off" } }, callService: () => { calls++; return new Promise(r => { resolve = r; }); } };
  const first = card._toggle("kitchen_1");
  await card._toggle("kitchen_1");
  assert.equal(calls, 1);
  resolve();
  await first;
  assert.equal(card._pending.size, 0);
});

test("failed commands release pending state and show feedback", async () => {
  const card = panel();
  const notice = {};
  card.shadowRoot.querySelector = () => notice;
  card._hass = { states: { [card._entities.kitchen_1]: { state: "off" } }, callService: async () => { throw Error("Disconnected"); } };
  await card._toggle("kitchen_1");
  assert.equal(card._pending.size, 0);
  assert.match(notice.textContent, /No se pudo/);
});

test("opening details uses the existing entities without actions on open", () => {
  const card = panel({ entities: { camera: "camera.test", coffee: "switch.test" } });
  const camera = card._popupConfig("camera").cards[0];
  assert.equal(camera.type, "custom:videolink-doorbell");
  assert.equal(camera.entity, "camera.test");
  assert.equal(camera.enable_popup, false);
  assert.equal(camera.video_fit, "contain");
  assert.equal(card._popupConfig("coffee").cards[0].entities[0].entity, "switch.test");
  assert.equal(card._popupConfig("climate").cards[0].type, "thermostat");
  assert.equal(card._popupConfig("vacuum").cards[0].features[0].commands.join(","), "start_pause,return_home");
});

test("configuration rejects malformed entity IDs", () => {
  assert.throws(() => panel({ entities: { camera: '<img src=x onerror="alert(1)">' } }), /Invalid entity/);
});
