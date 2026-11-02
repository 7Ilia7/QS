'use strict';
// A new root visit starts at the introduction. Hashes, reload and history retain
// native browser restoration; never reset scroll after user interaction.
let interactedBeforeLoad = false;
['pointerdown', 'wheel', 'touchmove', 'keydown'].forEach(type => {
  window.addEventListener(type, () => { interactedBeforeLoad = true; }, {once: true, passive: true});
});
window.addEventListener('pageshow', event => {
  const navigation = performance.getEntriesByType('navigation')[0];
  if (!event.persisted && !interactedBeforeLoad && navigation?.type === 'navigate' && !location.hash) {
    window.scrollTo({top: 0, left: 0, behavior: 'instant'});
  }
}, {once: true});
// Booking is a conversation with the studio, not an automatic API submission.
document.documentElement.classList.add('js');
const menuButton = document.getElementById('hamburger');
const nav = document.getElementById('nav');
const overlay = document.getElementById('mobile-overlay');
const mobile = window.matchMedia('(max-width: 760px)');
function setMenu(open, restoreFocus = false) {
  if (!nav || !menuButton) return;
  const expanded = Boolean(open && mobile.matches);
  nav.classList.toggle('open', expanded);
  nav.inert = mobile.matches && !expanded;
  menuButton.setAttribute('aria-expanded', String(expanded));
  menuButton.setAttribute('aria-label', expanded ? 'Закрити меню' : 'Відкрити меню');
  document.body.classList.toggle('menu-open', expanded);
  if (overlay) overlay.hidden = !expanded;
  if (restoreFocus) menuButton.focus();
}
menuButton?.addEventListener('click', () => setMenu(menuButton.getAttribute('aria-expanded') !== 'true'));
overlay?.addEventListener('click', () => setMenu(false, true));
nav?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
mobile.addEventListener('change', () => setMenu(false));
setMenu(false);
document.addEventListener('keydown', event => {
  if (menuButton?.getAttribute('aria-expanded') !== 'true') return;
  if (event.key === 'Escape') { setMenu(false, true); return; }
  if (event.key !== 'Tab') return;
  const controls = [menuButton, ...nav.querySelectorAll('a')];
  const index = controls.indexOf(document.activeElement);
  event.preventDefault();
  const next = index < 0 ? 0 : (index + (event.shiftKey ? -1 : 1) + controls.length) % controls.length;
  controls[next].focus();
});

// Native modal provides Escape handling and focus restoration.
const lightbox = document.getElementById('lightbox');
const lightboxImage = document.getElementById('lightboxImg');
document.getElementById('gallery')?.addEventListener('click', event => {
  const link = event.target.closest('a');
  if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || !lightbox?.showModal) return;
  event.preventDefault();
  lightboxImage.src = link.getAttribute('href');
  lightboxImage.alt = link.querySelector('img').alt;
  document.getElementById('lightbox-caption').textContent = link.querySelector('figcaption span').textContent;
  lightbox.showModal();
});
lightbox?.querySelector('button').addEventListener('click', () => lightbox.close());
lightbox?.addEventListener('click', event => {
  const box = lightbox.getBoundingClientRect();
  if (event.target === lightbox && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) lightbox.close();
});

// Published work-only tariffs use half-open intervals at 50, 100 and 200 g.
const calc = document.getElementById('calcForm');
const grams = document.getElementById('calc-grams');
const master = document.getElementById('calc-master');
const removal = document.getElementById('calc-removal');
const money = value => new Intl.NumberFormat('uk-UA').format(value) + ' ₴';
const workRates = {master: [3100, 5300, 7500, 9700], olena: [4400, 6600, 8800, 11000]};
function updateEstimate() {
  if (!calc) return;
  const weight = grams.valueAsNumber, rates = workRates[master.value];
  const valid = grams.value.trim() !== '' && Number.isFinite(weight) && weight > 0 && rates;
  const whatsapp = document.getElementById('whatsapp-booking');
  if (!valid) {
    grams.setAttribute('aria-invalid', 'true');
    document.getElementById('calc-price').textContent = '—';
    document.getElementById('calc-breakdown').textContent = 'Введіть додатну вагу волосся в грамах.';
    document.getElementById('calc-explanation').textContent = 'Розрахунок недоступний до введення ваги. Волосся оплачується окремо.';
    if (whatsapp) whatsapp.href = 'https://wa.me/380985601157?text=' + encodeURIComponent('Добрий день! Хочу консультацію щодо нарощування. Допоможіть підібрати вагу волосся та майстра.');
    return;
  }
  grams.removeAttribute('aria-invalid');
  const bracket = weight < 50 ? 0 : weight < 100 ? 1 : weight < 200 ? 2 : 3;
  const work = rates[bracket], extra = removal.checked ? 1300 : 0, total = work + extra;
  const label = master.selectedOptions[0].textContent;
  document.getElementById('calc-price').textContent = money(total);
  document.getElementById('calc-breakdown').textContent = 'Робота: ' + money(work) + (extra ? ' + зняття: ' + money(extra) + ' = ' + money(total) : '. Зняття не додано.');
  document.getElementById('calc-explanation').textContent = 'Волосся оплачується окремо. Остаточний підбір узгоджуємо на консультації.';
  if (whatsapp) whatsapp.href = 'https://wa.me/380985601157?text=' + encodeURIComponent('Добрий день! Хочу консультацію щодо нарощування: ' + weight + ' г, ' + label + '. Розрахунок роботи: ' + money(work) + (extra ? ', зняття: ' + money(extra) : '') + '. Разом за роботу: ' + money(total) + ', без вартості волосся. Підкажіть варіанти та вільні дати.');
}
calc?.addEventListener('input', updateEstimate);
calc?.addEventListener('change', updateEstimate);
calc?.addEventListener('submit', event => event.preventDefault());
updateEstimate();

// Large local videos load after explicit interaction; the map is inline/lazy.
document.querySelectorAll('.video-load').forEach((button, index) => {
  const video = button.closest('figure').querySelector('video');
  const source = video.querySelector('source');
  const status = document.createElement('p');
  status.className = 'video-status';
  status.id = `video-status-${index}`;
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  button.after(status);
  button.setAttribute('aria-describedby', status.id);
  video.setAttribute('aria-describedby', status.id);
  let requested = false, timer;
  function failed() {
    if (!requested) return;
    clearTimeout(timer);
    status.textContent = 'Не вдалося завантажити відео. Перевірте з’єднання та спробуйте ще раз.';
    button.textContent = 'Спробувати ще раз';
    button.hidden = false;
    button.removeAttribute('aria-disabled');
    video.removeAttribute('aria-busy');
  }
  function ready() {
    clearTimeout(timer);
    status.textContent = '';
    video.removeAttribute('aria-busy');
    // Keep keyboard focus reachable when the activated retry becomes hidden.
    if (document.activeElement === button) video.focus();
    button.hidden = true;
    button.removeAttribute('aria-disabled');
  }
  // Failed <source> selection can leave video.error null; listen to both.
  source.addEventListener('error', failed);
  video.addEventListener('error', failed);
  video.addEventListener('loadeddata', ready);
  video.addEventListener('canplay', ready);
  button.addEventListener('click', () => {
    if (video.getAttribute('aria-busy') === 'true') return;
    requested = true;
    clearTimeout(timer);
    status.textContent = 'Завантажуємо відео…';
    button.setAttribute('aria-disabled', 'true');
    video.setAttribute('aria-busy', 'true');
    video.preload = 'auto';
    source.src = source.dataset.src;
    video.load();
    timer = setTimeout(failed, 30000);
  });
});
