(async () => {
  function find(root, tag) {
    for (const element of root.children || []) {
      if (element.localName === tag) return element;
      const result = (element.shadowRoot && find(element.shadowRoot, tag)) || find(element, tag);
      if (result) return result;
    }
  }
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const wait = () => new Promise(resolve => setTimeout(resolve, 500));
  const card = find(document, "ha-pop-panel");
  assert(card, "Panel must be mounted in Home Assistant");
  assert(innerWidth === 720 && innerHeight === 1280, "Test at the physical portrait viewport");
  const main = card.shadowRoot.querySelector("main");
  assert(document.documentElement.scrollHeight === innerHeight, "Whole page must not scroll vertically");
  assert(document.documentElement.scrollWidth === innerWidth, "Whole page must not scroll horizontally");
  assert(main.scrollHeight === main.clientHeight, "Main panel must fit vertically");
  assert(main.scrollWidth === main.clientWidth, "Main panel must fit horizontally");
  const controls = [...main.querySelectorAll("button")];
  for (const section of main.querySelectorAll(".room,.machines")) {
    const bounds = section.getBoundingClientRect();
    assert(section.scrollHeight <= section.clientHeight + 1, "Section content must fit its allocated height");
    for (const control of section.querySelectorAll("button")) {
      const r = control.getBoundingClientRect();
      assert(r.top >= bounds.top && r.bottom <= bounds.bottom, "Controls must not spill into the next section");
    }
  }
  for (const button of controls) {
    const r = button.getBoundingClientRect();
    assert(r.width >= 44 && r.height >= 44, "Touch controls must be at least 44 pixels");
    assert(r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight, "Control must remain inside the physical screen");
  }
  const popupResults = [];
  for (const key of ["coffee", "climate", "hot_water", "washer", "dryer", "vacuum", "camera"]) {
    const trigger = card.shadowRoot.querySelector(`[data-popup="${key}"]`);
    await card._openPopup(key, trigger);
    await wait();
    const dialog = card.shadowRoot.querySelector("dialog");
    const rect = dialog.getBoundingClientRect();
    assert(dialog.open, `${key}: popup must open`);
    assert(rect.top >= 0 && rect.bottom <= innerHeight, `${key}: popup must fit the screen`);
    assert(dialog.scrollHeight <= dialog.clientHeight + 1, `${key}: popup must not require scrolling`);
    const cards = [...card.shadowRoot.querySelector(".popup-body").children];
    assert(cards.length > 0, `${key}: must load native controls`);
    assert(cards.every(element => customElements.get(element.localName)), `${key}: card classes must load`);
    assert(!find(dialog, "hui-error-card"), `${key}: native controls must not show an error card`);
    popupResults.push({ key, height: Math.round(rect.height), cards: cards.map(element => element.localName) });
    card._closePopup();
    await wait();
    assert(card.shadowRoot.querySelector(".popup-body").children.length === 0, `${key}: popup must release its cards when closed`);
    assert(card.shadowRoot.activeElement === trigger, `${key}: closing must return focus to the trigger`);
  }
  await card._openPopup("camera", card.shadowRoot.querySelector('[data-popup="camera"]'));
  await card._openPopup("coffee", card.shadowRoot.querySelector('[data-popup="coffee"]'));
  await wait();
  assert(card.shadowRoot.querySelector(".popup-body").firstElementChild?.localName === "hui-entities-card", "Switching popups must not clear the new content");
  card._closePopup();
  return { viewport: [innerWidth, innerHeight], page: [document.documentElement.scrollWidth, document.documentElement.scrollHeight], controls: controls.length, popups: popupResults, rapidPopupSwitch: "passed" };
})()
