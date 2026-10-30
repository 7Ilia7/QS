'use strict';
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

// Preserve the existing studio model and label it as an estimate.
const calc = document.getElementById('calcForm');
const length = document.getElementById('calc-length');
const strands = document.getElementById('calc-strands');
const presets = document.querySelectorAll('.calc__presets button');
const rates = new Map([[35,48],[40,55],[45,62],[50,70],[55,78],[60,86],[65,92]]);
function updateEstimate() {
  if (!calc) return;
  const lengthCm = Number(length.value), count = Number(strands.value);
  const extra = [...calc.querySelectorAll('input[name="extra"]:checked')].reduce((sum, input) => sum + Number(input.dataset.price), 0);
  const total = rates.get(lengthCm) * count + extra;
  document.getElementById('calc-length-value').textContent = `${lengthCm} см`;
  document.getElementById('calc-strands-value').textContent = `${count} шт`;
  document.getElementById('calc-price').textContent = `${new Intl.NumberFormat('uk-UA').format(total)} ₴`;
  presets.forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.length) === lengthCm && Number(button.dataset.strands) === count)));
  document.getElementById('whatsapp-booking').href = `https://wa.me/380985601157?text=${encodeURIComponent(`Добрий день! Хочу консультацію щодо нарощування: ${lengthCm} см, ${count} пасм. Орієнтир калькулятора: ${total} грн. Підкажіть, будь ласка, варіанти та вільні дати.`)}`;
}
calc?.addEventListener('input', updateEstimate);
calc?.addEventListener('submit', event => event.preventDefault());
presets.forEach(button => button.addEventListener('click', () => {
  length.value = button.dataset.length;
  strands.value = button.dataset.strands;
  updateEstimate();
}));
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
