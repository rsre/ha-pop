const HA_POP_VERSION = "0.1.2";

const HA_POP_ENTITIES = Object.freeze({
  kitchen_1: "switch.kitchen_light_1",
  kitchen_2: "switch.kitchen_light_2",
  coffee: "switch.coffee_maker",
  coffee_schedule: "input_boolean.coffee_schedule",
  coffee_time: "input_datetime.coffee_time",
  nave: "switch.garage_lights",
  spotlight: "switch.spotlight",
  exterior: "switch.exterior_lights",
  camera: "camera.doorbell",
  washer: "sensor.washer_status",
  dryer: "sensor.dryer_status",
  climate: "climate.heating",
  hot_water: "sensor.hot_water_setpoint",
  vacuum: "vacuum.robot",
  doorbell_command: "input_button.ha_panel_doorbell",
});

class HaPopPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._pending = new Set();
    this._popupCards = [];
    this._generation = 0;
    // Native entity cards can open HA's own detail dialog; release our modal first.
    this.addEventListener("hass-more-info", () => this._closePopup());
  }

  setConfig(config) {
    this._config = { title: "Home", ...config };
    this._entities = { ...HA_POP_ENTITIES, ...config.entities };
    for (const [key, entity] of Object.entries(this._entities)) {
      if (typeof entity !== "string" || !/^[a-z_]+\.[a-z0-9_]+$/.test(entity)) {
        throw new Error(`Invalid entity for ${key}`);
      }
    }
    if (this.isConnected) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._rendered) this._update();
    for (const card of this._popupCards) card.hass = hass;
    this._handleDoorbellCommand();
  }

  get hass() { return this._hass; }

  _handleDoorbellCommand() {
    const stamp = this._state("doorbell_command")?.state;
    const previous = this._doorbellStamp;
    this._doorbellStamp = stamp;
    // Establish a baseline on initial connection; never replay an old press.
    if (!previous || stamp === previous || !this._rendered) return;
    const age = Date.now() - Date.parse(stamp);
    if (!Number.isFinite(age) || age < -5000 || age > 30000) return;
    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog?.open && this._activePopup === "camera") return;
    this._openPopup("camera", this.shadowRoot.querySelector('[data-popup="camera"]'));
  }
  getCardSize() { return 16; }
  getGridOptions() { return { rows: "auto", columns: "full" }; }

  connectedCallback() {
    if (!this._config) this.setConfig({});
    this._render();
    this._clockTimer = setInterval(() => this._updateClock(), 1000);
    this._cameraTimer = setInterval(() => this._updateCamera(), 30000);
  }

  disconnectedCallback() {
    clearInterval(this._clockTimer);
    clearInterval(this._cameraTimer);
    this._closePopup();
  }

  _icon(name) { return `<ha-icon icon="mdi:${name}" aria-hidden="true"></ha-icon>`; }

  _row(key, label, icon, popup) {
    return `<button class="control" data-key="${key}" ${popup ? `data-popup="${popup}"` : `data-toggle="${key}"`}>
      <span class="control-icon">${this._icon(icon)}</span>
      <span class="control-copy"><span class="label">${label}</span><span class="state" data-state="${key}">—</span></span>
      ${popup ? this._icon("chevron-right") : '<span class="switch" aria-hidden="true"></span>'}
    </button>`;
  }

  _summary(key, label, icon, popup) {
    return `<button class="summary" data-key="${key}" data-popup="${popup}">
      <span class="summary-icon">${this._icon(icon)}</span>
      <span class="label">${label}</span><span class="value" data-state="${key}">—</span>
      <span class="summary-arrow">${this._icon("chevron-right")}</span>
    </button>`;
  }

  _render() {
    this._closePopup();
    this.shadowRoot.innerHTML = `<style>${HA_POP_STYLES}</style>
      <main class="panel" aria-label="Panel de casa">
        <header class="masthead">
          <div><div class="eyebrow">EN CASA</div><h1></h1><p class="date"></p></div>
          <div class="clock"><time></time><span class="connection"><i></i><span>Conectado</span></span></div>
        </header>

        <button class="camera" data-popup="camera" aria-label="Abrir cámara y portero del portón">
          <img alt="Vista del portón" draggable="false" hidden>
          <div class="camera-fallback">${this._icon("cctv")}</div>
          <div class="camera-shade"></div>
          <span class="camera-badge">${this._icon("camera-outline")} PORTÓN</span>
          <span class="camera-bottom"><span><strong>Una mirada fuera</strong><span>Ver cámara y hablar</span></span><span class="camera-open">${this._icon("arrow-top-right")}</span></span>
        </button>

        <div class="rooms">
          <section class="room" aria-label="Cocina"><h2>${this._icon("countertop-outline")} Cocina</h2>
            ${this._row("kitchen_1", "Luz 1", "lightbulb-outline")}
            ${this._row("kitchen_2", "Luz 2", "lightbulb-outline")}
            ${this._row("coffee", "Cafetera", "coffee-outline", "coffee")}
          </section>
          <section class="room" aria-label="Nave y exterior"><h2>${this._icon("warehouse")} Nave y exterior</h2>
            ${this._row("nave", "Luces nave", "ceiling-light-outline")}
            ${this._row("spotlight", "Foco", "spotlight-beam")}
            ${this._row("exterior", "Luz exterior", "outdoor-lamp")}
          </section>
        </div>

        <section class="machines" aria-label="Sala de máquinas"><h2>${this._icon("home-thermometer-outline")} Sala de máquinas <span>Detalles al tocar</span></h2>
          <div class="summaries">
            ${this._summary("climate", "Calefacción", "radiator", "climate")}
            ${this._summary("hot_water", "Agua caliente", "water-thermometer-outline", "hot_water")}
            ${this._summary("washer", "Lavadora", "washing-machine", "washer")}
            ${this._summary("dryer", "Secadora", "tumble-dryer", "dryer")}
          </div>
        </section>

        <button class="robot" data-popup="vacuum" aria-label="Abrir controles de Robot">
          <span class="robot-icon">${this._icon("robot-vacuum")}</span>
          <span class="robot-copy"><span class="eyebrow">ASPIRADORA</span><strong>Robot</strong><span data-state="vacuum">—</span></span>
          <span class="robot-battery" hidden></span><span class="round-arrow">${this._icon("chevron-right")}</span>
        </button>
        <footer><span>Toca para controlar · Detalles en ventanas</span><span class="notice" role="status" aria-live="polite"></span></footer>
      </main>
      <dialog aria-labelledby="popup-title">
        <div class="popup-head"><div><div class="eyebrow">HOME</div><h2 id="popup-title"></h2></div><button class="close" aria-label="Cerrar ventana">${this._icon("close")}</button></div>
        <div class="popup-body"></div>
      </dialog>`;
    this.shadowRoot.querySelector("h1").textContent = this._config.title;
    this.shadowRoot.addEventListener("click", this._onClick ??= (event) => {
      const button = event.target.closest("button");
      if (!button || button.disabled) return;
      if (button.classList.contains("close")) this._closePopup();
      else if (button.dataset.popup) this._openPopup(button.dataset.popup, button);
      else if (button.dataset.toggle) this._toggle(button.dataset.toggle);
    });
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.addEventListener("close", () => { if (!dialog.open) this._clearPopup(); });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) {
        const r = dialog.getBoundingClientRect();
        if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) this._closePopup();
      }
    });
    const image = this.shadowRoot.querySelector(".camera img");
    image.addEventListener("load", () => { image.hidden = false; });
    image.addEventListener("error", () => { image.hidden = true; });
    this._rendered = true;
    this._updateClock();
    this._update();
    this._updateCamera();
  }

  _state(key) { return this._hass?.states?.[this._entities[key]]; }

  _available(key) {
    const s = this._state(key);
    return Boolean(s && !["unavailable", "unknown"].includes(s.state));
  }

  _stateText(key) {
    const s = this._state(key);
    if (!this._available(key)) return "No disponible";
    if (key === "hot_water") return `${Number(s.state).toLocaleString("es-ES", { maximumFractionDigits: 1 })} °C`;
    if (key === "climate") {
      const temperature = s.attributes.current_temperature;
      return temperature != null ? `${temperature} °C · ${s.state === "off" ? "Apagada" : "Activa"}` : (s.state === "off" ? "Apagada" : "Activa");
    }
    const names = { on: "Encendida", off: "Apagada", docked: "En la base", cleaning: "Limpiando", returning: "Volviendo a casa", paused: "En pausa", idle: "En reposo", unavailable: "No disponible" };
    return names[s.state] || s.state;
  }

  _update() {
    if (!this._rendered) return;
    for (const element of this.shadowRoot.querySelectorAll("[data-state]")) {
      element.textContent = this._stateText(element.dataset.state);
    }
    for (const button of this.shadowRoot.querySelectorAll("[data-toggle]")) {
      const key = button.dataset.toggle;
      button.classList.toggle("on", this._state(key)?.state === "on");
      button.disabled = !this._available(key) || this._hass?.connection?.connected === false || this._pending.has(key);
      button.setAttribute("aria-pressed", String(this._state(key)?.state === "on"));
      button.setAttribute("aria-busy", String(this._pending.has(key)));
    }
    const coffee = this.shadowRoot.querySelector('[data-popup="coffee"]');
    coffee.classList.toggle("on", this._state("coffee")?.state === "on");
    const battery = this._state("vacuum")?.attributes.battery_level;
    const badge = this.shadowRoot.querySelector(".robot-battery");
    badge.hidden = battery == null;
    badge.textContent = `${battery ?? ""}%`;
    const connected = this._hass?.connection?.connected !== false;
    const connection = this.shadowRoot.querySelector(".connection");
    connection.classList.toggle("offline", !connected);
    connection.querySelector("span").textContent = connected ? "Conectado" : "Sin conexión";
  }

  _updateClock() {
    if (!this._rendered) return;
    const now = new Date();
    this.shadowRoot.querySelector("time").textContent = now.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
    this.shadowRoot.querySelector(".date").textContent = now.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  }

  _updateCamera() {
    if (!this._rendered || this._hass?.connection?.connected === false) return;
    const path = this._state("camera")?.attributes.entity_picture;
    const image = this.shadowRoot.querySelector(".camera img");
    if (!path) { image.hidden = true; return; }
    const url = new URL(this._hass.hassUrl(path));
    url.searchParams.set("ha_pop_snapshot", String(Math.floor(Date.now() / 30000)));
    image.src = url.href;
  }

  async _toggle(key) {
    if (!this._available(key) || this._pending.has(key) || this._hass?.connection?.connected === false) return;
    const entity = this._entities[key];
    const domain = entity.split(".")[0];
    if (!["switch", "light", "input_boolean"].includes(domain)) return;
    this._pending.add(key);
    this._update();
    try {
      await this._hass.callService(domain, this._state(key).state === "on" ? "turn_off" : "turn_on", { entity_id: entity });
    } catch (_error) {
      this.shadowRoot.querySelector(".notice").textContent = "No se pudo completar la acción";
    } finally {
      this._pending.delete(key);
      this._update();
    }
  }

  _popupConfig(key) {
    const e = this._entities;
    const entities = (title, rows) => ({ title, cards: [{ type: "entities", show_header_toggle: false, entities: rows }] });
    switch (key) {
      case "camera": return { title: "Portón", cards: [{ type: "custom:videolink-doorbell", entity: e.camera, title: "", video_fit: "contain", talk_mode: "native", enable_popup: false, ...this._config.camera_card, entity: e.camera }] };
      case "coffee": return entities("Cafetera", [{ entity: e.coffee, name: "Encendida" }, { entity: e.coffee_schedule, name: "Encendido automático" }, { entity: e.coffee_time, name: "Encender a las" }]);
      case "climate": return { title: "Calefacción", cards: [{ type: "thermostat", entity: e.climate }] };
      case "hot_water": return entities("Agua caliente", [{ entity: e.hot_water, name: "Temperatura de consigna" }]);
      case "washer": return entities("Lavadora", [{ entity: e.washer, name: "Estado" }]);
      case "dryer": return entities("Secadora", [{ entity: e.dryer, name: "Estado" }]);
      case "vacuum": return { title: "Robot", cards: [{ type: "tile", entity: e.vacuum, name: "Robot", features: [{ type: "vacuum-commands", commands: ["start_pause", "return_home"] }] }] };
      default: throw new Error("Unknown popup");
    }
  }

  async _openPopup(key, trigger) {
    this._closePopup();
    const generation = ++this._generation;
    const config = this._popupConfig(key);
    const dialog = this.shadowRoot.querySelector("dialog");
    this._trigger = trigger;
    this.shadowRoot.querySelector("#popup-title").textContent = config.title;
    const body = this.shadowRoot.querySelector(".popup-body");
    body.textContent = "Cargando…";
    dialog.showModal();
    this._activePopup = key;
    this.shadowRoot.querySelector(".close").focus();
    try {
      const helpers = await window.loadCardHelpers();
      if (generation !== this._generation || !dialog.open) return;
      const cards = config.cards.map((cardConfig) => {
        const card = helpers.createCardElement(cardConfig);
        card.hass = this._hass;
        return card;
      });
      this._popupCards = cards;
      body.replaceChildren(...cards);
    } catch (_error) {
      if (generation === this._generation) body.textContent = "No se pudieron cargar los controles. Cierra y vuelve a intentarlo.";
    }
  }

  _clearPopup() {
    this._activePopup = undefined;
    ++this._generation;
    this._popupCards = [];
    this.shadowRoot.querySelector(".popup-body")?.replaceChildren();
  }

  _closePopup() {
    this._clearPopup();
    const dialog = this.shadowRoot.querySelector("dialog");
    if (dialog?.open) dialog.close();
    this._trigger?.focus();
    this._trigger = undefined;
  }
}

const HA_POP_STYLES = `
  :host { display:block; width:100%; height:calc(100dvh - var(--header-height,56px)); box-sizing:border-box; color:#ecf1f5; font-family:var(--paper-font-body1_-_font-family,Roboto,Arial,sans-serif); font-size:16px; line-height:1.35; --primary-text-color:#ecf1f5; --secondary-text-color:#a0afbd; --primary-color:#79d6c6; --card-background-color:#18232f; --ha-card-background:#18232f; --secondary-background-color:#233140; --ha-card-border-radius:18px; --ha-card-border-width:0; color-scheme:dark; }
  *,*::before,*::after { box-sizing:border-box; }
  [hidden] { display:none !important; }
  button { font:inherit; line-height:1.25; color:inherit; cursor:pointer; -webkit-tap-highlight-color:transparent; touch-action:manipulation; }
  button:focus-visible { outline:3px solid #a8f0df; outline-offset:-3px; }
  button:disabled { opacity:.5; cursor:default; }
  ha-icon { --mdc-icon-size:25px; flex:none; }
  .panel { height:100%; width:100%; overflow:clip; padding:18px 22px 12px; display:grid; grid-template-rows:82px minmax(160px,1fr) 276px 214px 128px 22px; gap:14px; background:#0d141e; }
  .masthead { display:flex; align-items:center; justify-content:space-between; min-width:0; }
  .eyebrow { color:#8fa1b2; font-size:11px; font-weight:700; letter-spacing:2px; }
  h1 { margin:3px 0; font-size:29px; font-weight:550; letter-spacing:-.7px; }
  .date { margin:0; font-size:14px; color:#94a4b6; }
  .clock { display:flex; flex-direction:column; align-items:flex-end; gap:5px; }
  time { font-size:34px; font-weight:350; letter-spacing:-1px; font-variant-numeric:tabular-nums; }
  .connection { color:#9aafbb; font-size:11px; display:flex; align-items:center; gap:5px; }
  .connection i { width:6px; height:6px; background:#79d6c6; border-radius:50%; }
  .connection.offline i { background:#e5a174; }
  .camera { position:relative; padding:0; border:1px solid #354452; border-radius:22px; overflow:hidden; background:#182530; text-align:left; min-height:0; }
  .camera img,.camera-fallback,.camera-shade { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
  .camera-fallback { display:grid; place-items:center; color:#506879; background:radial-gradient(at 70% 20%,#25414b,#16232f 70%); }
  .camera-fallback ha-icon { --mdc-icon-size:70px; }
  .camera img { z-index:1; }
  .camera-shade { z-index:2; background:linear-gradient(180deg,rgba(3,10,15,.25),transparent 40%,rgba(3,10,15,.9)); }
  .camera-badge { position:absolute; top:16px; left:18px; z-index:3; display:flex; gap:7px; align-items:center; font-size:11px; letter-spacing:1.5px; font-weight:700; padding:7px 11px; border-radius:30px; background:#0d1823c9; }
  .camera-badge ha-icon { --mdc-icon-size:17px; }
  .camera-bottom { position:absolute; inset:auto 20px 20px; display:flex; align-items:center; justify-content:space-between; z-index:3; }
  .camera-bottom strong { display:block; font-size:25px; font-weight:550; letter-spacing:-.5px; }
  .camera-bottom span span { display:block; font-size:14px; color:#c8d3da; margin-top:6px; }
  .camera-open,.round-arrow { display:grid; place-items:center; width:46px; height:46px; border-radius:50%; background:#ffffff16; }
  .rooms { display:grid; grid-template-columns:1fr 1fr; gap:14px; min-height:0; }
  .room,.machines { border:1px solid #263442; border-radius:20px; background:#121d29; padding:16px; min-width:0; }
  h2 { display:flex; align-items:center; gap:8px; margin:0 0 12px; font-size:17px; font-weight:550; }
  h2 ha-icon { --mdc-icon-size:21px; color:#8196a7; }
  .room { display:grid; grid-template-rows:26px repeat(3,minmax(0,1fr)); gap:8px; }
  .room h2 { margin:0; }
  .control { display:flex; align-items:center; gap:10px; min-height:0; background:#1b2835; border:1px solid #283846; border-radius:13px; padding:10px; width:100%; text-align:left; }
  .control-icon { display:grid; place-items:center; width:32px; height:38px; color:#a2b3c2; flex:none; }
  .control-copy { min-width:0; flex:1; display:flex; flex-direction:column; gap:5px; }
  .label { font-size:16px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .state { color:#96a8b8; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .switch { width:33px; height:21px; border-radius:20px; background:#40505c; flex:none; position:relative; }
  .switch::after { content:""; width:15px; height:15px; position:absolute; top:3px; left:3px; border-radius:50%; background:#c0ccd4; transition:transform .15s; }
  .control.on { background:#25352e; border-color:#4e6651; }
  .on .control-icon { color:#e4d58f; }
  .on .switch { background:#b9dcb6; }
  .on .switch::after { transform:translateX(12px); background:#213c2b; }
  .control>ha-icon { --mdc-icon-size:18px; color:#8da7b7; }
  .machines { display:grid; grid-template-rows:24px minmax(0,1fr); gap:12px; }
  .machines h2 { margin:0; }
  .machines h2 span { margin-left:auto; color:#778fa0; font-size:11px; font-weight:400; }
  .summaries { display:grid; grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr; gap:10px; min-height:0; }
  .summary { display:grid; grid-template-columns:34px 1fr 16px; grid-template-rows:auto auto; column-gap:8px; align-content:center; text-align:left; padding:10px; background:#1b2835; border:1px solid #283846; border-radius:13px; min-width:0; }
  .summary-icon { grid-row:1/3; align-self:center; color:#91c8cd; }
  .summary .label { font-size:15px; }
  .summary .value { grid-column:2; margin-top:5px; color:#9fb4c3; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .summary-arrow { grid-row:1/3; grid-column:3; align-self:center; color:#6f8b9a; }
  .summary-arrow ha-icon { --mdc-icon-size:17px; }
  .robot { display:flex; align-items:center; gap:18px; text-align:left; border:1px solid #30434b; border-radius:20px; padding:16px 20px; background:linear-gradient(110deg,#192c32,#14232d); min-height:0; }
  .robot-icon { display:grid; place-items:center; width:66px; height:66px; border:1px solid #41606a; border-radius:22px; color:#9fe0d3; background:#253c41; }
  .robot-icon ha-icon { --mdc-icon-size:38px; }
  .robot-copy { display:flex; flex-direction:column; gap:6px; flex:1; }
  .robot-copy strong { font-size:24px; font-weight:500; }
  .robot-copy>[data-state] { font-size:14px; color:#b0c3ca; }
  .robot-battery { color:#a3c7bd; border:1px solid #3b5859; border-radius:9px; padding:7px 9px; font-size:13px; }
  footer { display:flex; align-items:center; justify-content:space-between; gap:12px; font-size:11px; color:#718b9d; min-width:0; }
  .notice { color:#f1bb96; text-align:right; }
  dialog { padding:0; width:min(650px,calc(100vw - 36px)); max-height:calc(100dvh - 40px); border:1px solid #3b5060; border-radius:24px; background:#111e2a; color:#ecf1f5; box-shadow:0 24px 100px #0008; overflow:auto; overscroll-behavior:contain; --ha-card-border-radius:16px; }
  dialog::backdrop { background:#02080ed9; backdrop-filter:blur(7px); }
  .popup-head { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:22px 22px 18px; position:sticky; top:0; background:#111e2a; z-index:2; border-bottom:1px solid #293b49; }
  .popup-head h2 { margin:6px 0 0; font-size:26px; }
  .close { display:grid; place-items:center; min-width:52px; height:52px; border-radius:50%; border:1px solid #3b5060; background:#233544; }
  .popup-body { padding:18px; display:grid; gap:14px; min-height:100px; }
  @media(max-width:600px) { .panel { padding:12px; gap:10px; grid-template-rows:72px minmax(140px,1fr) 260px 200px 112px 20px; } .room,.machines { padding:12px; } .rooms { gap:10px; } .control { gap:5px; padding:8px; } .control-icon { width:24px; } .label { font-size:14px; } .control .switch { width:28px; } .on .switch::after { transform:translateX(7px); } h2 { font-size:15px; } .machines h2 span { display:none; } .robot { padding:12px; } }
`;

if (!customElements.get("ha-pop-panel")) customElements.define("ha-pop-panel", HaPopPanel);
window.customCards ??= [];
if (!window.customCards.some((card) => card.type === "ha-pop-panel")) {
  window.customCards.push({ type: "ha-pop-panel", name: "Home touchscreen panel", description: `Portrait wall panel with pop-up controls · ${HA_POP_VERSION}`, preview: false });
}
