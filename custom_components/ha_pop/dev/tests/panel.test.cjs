const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");

const context = vm.createContext({
  HTMLElement: class { attachShadow() { this.shadowRoot = {}; } addEventListener() {} },
  customElements: { get: name => ["videolink-doorbell", "home-assistant"].includes(name) ? class {} : undefined, define: () => {} },
  window: {},
  URL,
  setTimeout,
  clearTimeout,
});
vm.runInContext(fs.readFileSync(require("node:path").join(__dirname, "../../frontend/ha-pop-panel-card.js"), "utf8") + "\nglobalThis.Panel = HaPopPanel;", context);

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

test("doorbell commands ignore initial and stale state, and open fresh presses once", () => {
  const card = panel({ entities: { doorbell_command: "event.wall_panel_doorbell_command" } });
  let opens = 0;
  card._rendered = true;
  card._openPopup = (key) => { assert.equal(key, "camera"); opens++; };
  card.shadowRoot.querySelector = () => ({ open: false });
  const set = (stamp) => { card.hass = { states: { [card._entities.doorbell_command]: { state: stamp } } }; };
  set(new Date().toISOString());
  assert.equal(opens, 0);
  set(new Date(Date.now() - 60000).toISOString());
  assert.equal(opens, 0);
  const fresh = new Date().toISOString();
  set(fresh);
  set(fresh);
  assert.equal(opens, 1);
  card._activePopup = "camera";
  card.shadowRoot.querySelector = () => ({ open: true });
  set(new Date(Date.now() + 100).toISOString());
  assert.equal(opens, 1);
});


test("camera works with the native HA card when no video/talk card is installed", () => {
  const original = context.customElements.get;
  context.customElements.get = () => undefined;
  try {
    const config = panel()._popupConfig("camera").cards[0];
    assert.equal(config.type, "picture-entity");
    assert.equal(config.camera_view, "live");
  } finally {
    context.customElements.get = original;
  }
});


test("doorbell navigation opens video after rendering and consumes the request without replay", async () => {
  const card = panel();
  let opens = 0;
  card._showDoorbell = () => { opens++; };
  context.window.location = { href: "https://example.test/ha-pop-panel/home?ha_pop_doorbell=" + Date.now() };
  const consumed = new Map();
  context.window.sessionStorage = { getItem: key => consumed.get(key), setItem: (key, value) => consumed.set(key, value) };
  try {
    card._consumeDoorbellNavigation();
    assert.equal(opens, 0);
    card._rendered = true;
    card.isConnected = true;
    card.hass = { states: {} };
    card._consumeDoorbellNavigation();
    assert.equal(opens, 0);
    await new Promise(resolve => setTimeout(resolve, 150));
    assert.equal(opens, 1);
    assert.match(context.window.location.href, /ha_pop_doorbell=/);
    card._consumeDoorbellNavigation();
    assert.equal(opens, 1);
    // HA can replace the initial card during view setup; preserve the request.
    const replacement = panel();
    replacement._rendered = true;
    replacement.isConnected = true;
    replacement._showDoorbell = () => { opens++; };
    replacement.hass = { states: {} };
    await new Promise(resolve => setTimeout(resolve, 150));
    assert.equal(opens, 2);
    replacement._dismissDoorbellNavigation();
    const dismissed = panel();
    dismissed._rendered = true;
    dismissed.isConnected = true;
    dismissed._showDoorbell = () => { opens++; };
    dismissed.hass = { states: {} };
    assert.equal(opens, 2);
    context.window.location.href = "https://example.test/ha-pop-panel/home?ha_pop_doorbell=" + (Date.now() - 60000);
    card._consumeDoorbellNavigation();
    assert.equal(opens, 2);
    card._activePopup = "camera";
    card.shadowRoot.querySelector = () => ({ open: true });
    context.Panel.prototype._showDoorbell.call(card);
    assert.equal(opens, 2);
  } finally {
    clearTimeout(card._doorbellNavigationTimer);
    delete context.window.location;
    delete context.window.sessionStorage;
  }
});


test("sleep dismissal closes the popup, releases media and suppresses pending navigation", () => {
  const card = panel();
  const consumed = new Map();
  let cleared = 0;
  const dialog = { open: true, close() { this.open = false; } };
  context.window.location = { href: "https://example.test/ha-pop-panel/home?ha_pop_doorbell=" + Date.now() };
  context.window.sessionStorage = { getItem: key => consumed.get(key), setItem: (key, value) => consumed.set(key, value) };
  card.shadowRoot.querySelector = selector => selector === "dialog" ? dialog : { replaceChildren() { cleared++; } };
  card._activePopup = "camera";
  card._popupCards = [{}];
  try {
    card._closePopup(true);
    assert.equal(dialog.open, false);
    assert.equal(card._activePopup, undefined);
    assert.equal(card._popupCards.length, 0);
    assert.equal(cleared, 1);
    assert.ok(consumed.get("ha-pop-doorbell:/ha-pop-panel/home"));
  } finally {
    delete context.window.location;
    delete context.window.sessionStorage;
  }
});
