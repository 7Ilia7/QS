// Приготовить body для плавного появления
window.addEventListener('DOMContentLoaded', () => document.body.classList.add('ready'));

// Mobile menu: переключаем класс, а не inline-стили (меньше reflow)
const hamburger = document.getElementById('hamburger');
const nav = document.getElementById('nav');
const overlay = document.getElementById('mobile-overlay');
const mobileMedia = window.matchMedia('(max-width: 780px)');

function syncNavAria(isOpen) {
  if (!nav) return;
  const isMobile = mobileMedia.matches;
  nav.setAttribute('aria-hidden', isMobile && !isOpen ? 'true' : 'false');
}

function toggleOverlay(isOpen) {
  if (!overlay) return;
  if (isOpen) {
    overlay.hidden = false;
    requestAnimationFrame(() => overlay.classList.add('active'));
  } else {
    overlay.classList.remove('active');
    const hide = () => {
      overlay.hidden = true;
      overlay.removeEventListener('transitionend', hide);
    };
    overlay.addEventListener('transitionend', hide, { once: true });
    setTimeout(hide, 320); // fallback if transitionend not fired
  }
}

function toggleNav(force) {
  if (!hamburger || !nav) return;
  const shouldOpen = typeof force === 'boolean' ? force : !nav.classList.contains('open');
  nav.classList.toggle('open', shouldOpen);
  hamburger.classList.toggle('is-active', shouldOpen);
  hamburger.setAttribute('aria-expanded', String(shouldOpen));
  document.body.style.overflow = shouldOpen ? 'hidden' : '';
  syncNavAria(shouldOpen);
  toggleOverlay(shouldOpen);
}

if (hamburger && nav) {
  hamburger.addEventListener('click', () => toggleNav());
}

overlay?.addEventListener('click', () => toggleNav(false));

const handleMediaChange = (event) => {
  if (!event.matches) {
    toggleNav(false);
    document.body.style.overflow = '';
    syncNavAria(false);
  } else {
    syncNavAria(nav?.classList.contains('open'));
  }
};
mobileMedia.addEventListener?.('change', handleMediaChange);
mobileMedia.addListener?.(handleMediaChange);
handleMediaChange(mobileMedia);

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && nav?.classList.contains('open')) {
    toggleNav(false);
  }
});

// Sticky header compact on scroll + кнопка toTop
const header = document.querySelector('.header');
const toTop = document.getElementById('toTop');
const onScroll = () => {
  const scrollRoot = document.scrollingElement || document.documentElement;
  const y = window.scrollY || scrollRoot.scrollTop || document.body.scrollTop || 0;
  if (header) header.classList.toggle('scrolled', y > 10);
  if (toTop) {
    if (y > 400) { toTop.hidden = false; } else { toTop.hidden = true; }
  }
};
function scrollToPageTop() {
  const scrollRoot = document.scrollingElement || document.documentElement;
  window.scrollTo({ top: 0, behavior: 'smooth' });
  scrollRoot?.scrollTo?.({ top: 0, behavior: 'smooth' });
  document.body?.scrollTo?.({ top: 0, behavior: 'smooth' });
  setTimeout(() => {
    const y = window.scrollY || scrollRoot.scrollTop || document.body.scrollTop || 0;
    if (y > 8) {
      window.scrollTo(0, 0);
      scrollRoot.scrollTop = 0;
      document.body.scrollTop = 0;
    }
    onScroll();
  }, 450);
}

window.addEventListener('scroll', () => requestAnimationFrame(onScroll), { passive: true });
onScroll();
toTop?.addEventListener('click', (event) => {
  event.preventDefault();
  event.stopPropagation();
  scrollToPageTop();
});
toTop?.addEventListener('touchend', (event) => {
  event.preventDefault();
  event.stopPropagation();
  scrollToPageTop();
}, { passive: false });

document.addEventListener('click', (event) => {
  if (event.target.closest?.('#toTop')) {
    event.preventDefault();
    scrollToPageTop();
  }
});

// Smooth scroll для якорей (закрываем меню на мобиле)
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const id = a.getAttribute('href');
    if (id && id.length > 1) {
      e.preventDefault();
      document.querySelector(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (nav?.classList.contains('open')) {
        toggleNav(false);
      }
    }
  });
});

// Lightweight slider for video секції
document.querySelectorAll('[data-slider]').forEach(slider => {
  const track = slider.querySelector('[data-slider-track]');
  if (!track) return;
  const items = Array.from(track.children);
  if (!items.length) return;

  const prevBtn = slider.querySelector('[data-slider-prev]');
  const nextBtn = slider.querySelector('[data-slider-next]');
  const dotsHost = slider.querySelector('[data-slider-dots]');
  const dots = [];
  let activeIndex = 0;
  let rafId = 0;

  if (dotsHost) {
    if (!dotsHost.children.length) {
      items.forEach((_, idx) => {
        const dot = document.createElement('button');
        dot.type = 'button';
        dot.className = 'extensions__dot';
        dot.dataset.index = String(idx);
        dot.setAttribute('aria-label', `Переглянути відео ${idx + 1}`);
        dotsHost.appendChild(dot);
      });
    }
    dotsHost.querySelectorAll('button').forEach((dot, idx) => {
      dot.addEventListener('click', () => goTo(idx));
      dots.push(dot);
    });
  }

  function setActive(index) {
    activeIndex = index;
    items.forEach((item, i) => item.classList.toggle('is-active', i === index));
    dots.forEach((dot, i) => {
      const isCurrent = i === index;
      dot.classList.toggle('is-active', isCurrent);
      dot.setAttribute('aria-current', isCurrent ? 'true' : 'false');
    });
    if (prevBtn) prevBtn.disabled = index === 0;
    if (nextBtn) nextBtn.disabled = index === items.length - 1;
  }

  function goTo(index, behavior = 'smooth') {
    const bounded = Math.max(0, Math.min(index, items.length - 1));
    const target = items[bounded];
    if (!target) return;
    const left = target.offsetLeft - track.offsetLeft;
    track.scrollTo({ left, behavior });
  }

  function handleScroll() {
    const viewportCenter = track.scrollLeft + track.clientWidth / 2;
    let bestIndex = activeIndex;
    let bestDistance = Number.POSITIVE_INFINITY;
    items.forEach((item, idx) => {
      const itemCenter = item.offsetLeft + item.offsetWidth / 2;
      const distance = Math.abs(itemCenter - viewportCenter);
      if (distance < bestDistance) {
        bestDistance = distance;
        bestIndex = idx;
      }
    });
    setActive(bestIndex);
  }

  prevBtn?.addEventListener('click', () => goTo(activeIndex - 1));
  nextBtn?.addEventListener('click', () => goTo(activeIndex + 1));

  track.addEventListener('scroll', () => {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(handleScroll);
  }, { passive: true });

  window.addEventListener('resize', () => {
    setActive(activeIndex);
    goTo(activeIndex, 'auto');
  });

  // Ініціалізація
  setActive(0);
  goTo(0, 'auto');
});

// IntersectionObserver для плавного появления секций
const io = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (e.isIntersecting) {
      e.target.classList.add('visible');
      io.unobserve(e.target);
    }
  }
}, { threshold: 0.12 }) : null;
document.querySelectorAll('.reveal').forEach(el => io?.observe(el));

// Ленивая инициализация лайтбокса (только при первом клике)
let lightboxInited = false;
function initLightbox() {
  if (lightboxInited) return;
  lightboxInited = true;
  const gallery = document.getElementById('gallery');
  const lightbox = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightboxImg');
  const closeBtn = document.querySelector('.lightbox__close');
  if (!gallery || !lightbox || !lightboxImg || !closeBtn) return;

  gallery.addEventListener('click', (e) => {
    const a = e.target.closest('a');
    if (!a) return;
    e.preventDefault();
    lightboxImg.src = a.getAttribute('href');
    lightbox.classList.add('open');
    lightbox.hidden = false;
    lightbox.setAttribute('aria-hidden', 'false');
  });
  closeBtn.addEventListener('click', () => {
    lightbox.classList.remove('open');
    lightbox.setAttribute('aria-hidden', 'true');
    setTimeout(() => { lightbox.hidden = true; }, 150);
  });
  lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) closeBtn.click();
  });
}
document.getElementById('gallery')?.addEventListener('click', initLightbox, { once: true });

// Калькулятор наращування: вартість + час
const calcFormEl = document.getElementById('calcForm');
const calcLength = document.getElementById('calc-length');
const calcStrands = document.getElementById('calc-strands');
const calcLengthValue = document.getElementById('calc-length-value');
const calcStrandsValue = document.getElementById('calc-strands-value');
const calcStrandsLabel = document.getElementById('calc-strands-label');
const calcPrice = document.getElementById('calc-price');
const calcTime = document.getElementById('calc-time');
const calcNote = document.getElementById('calc-note');
const calcPresets = document.querySelectorAll('.calc__preset');

if (calcFormEl && calcLength && calcStrands && calcPrice) {
  // Розцінка за 1 пасмо в залежності від довжини (грн)
  const lengthRates = [
    { len: 35, rate: 48 },
    { len: 40, rate: 55 },
    { len: 45, rate: 62 },
    { len: 50, rate: 70 },
    { len: 55, rate: 78 },
    { len: 60, rate: 86 },
    { len: 65, rate: 92 }
  ];

  const nf = new Intl.NumberFormat('uk-UA');

  function interpolateRate(lengthCm) {
    for (let i = 0; i < lengthRates.length - 1; i++) {
      const current = lengthRates[i];
      const next = lengthRates[i + 1];
      if (lengthCm === current.len) return current.rate;
      if (lengthCm > current.len && lengthCm < next.len) {
        const progress = (lengthCm - current.len) / (next.len - current.len);
        return current.rate + (next.rate - current.rate) * progress;
      }
    }
    return lengthRates[lengthRates.length - 1].rate;
  }

  function estimateTime(lengthCm, strandsCount) {
    const base = 1.4;
    const byLength = ((lengthCm - 35) / 30) * 0.35;
    const byVolume = ((strandsCount - 80) / 120) * 1.05;
    return Math.max(1.3, base + byLength + byVolume);
  }

  function updateCalc() {
    const lengthCm = Number(calcLength.value);
    const strandsCount = Number(calcStrands.value);
    const extras = Array.from(calcFormEl.querySelectorAll('input[name="extra"]:checked'));

    const rate = interpolateRate(lengthCm);
    const extrasCost = extras.reduce((sum, el) => sum + Number(el.dataset.price || 0), 0);
    const total = Math.round(rate * strandsCount + extrasCost);
    const time = estimateTime(lengthCm, strandsCount);

    calcLengthValue.textContent = `${lengthCm} см`;
    calcStrandsValue.textContent = `${strandsCount} шт`;
    calcStrandsLabel.textContent = strandsCount;
    calcPrice.textContent = `${nf.format(total)} ₴`;
    calcTime.textContent = `~${time.toFixed(1)} год`;

    if (calcNote) {
      const extrasText = extras.length
        ? `Враховані опції: ${extras.map(el => el.closest('label')?.querySelector('span')?.textContent || '').filter(Boolean).join(', ')}.`
        : 'Без додаткових опцій — можна додати на консультації.';
      calcNote.textContent = `${extrasText} Фінальна сума залежить від відтінку та стану волосся.`;
    }
  }

  calcFormEl.addEventListener('input', updateCalc);
  calcPresets.forEach(btn => {
    btn.addEventListener('click', () => {
      calcPresets.forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      const presetLength = btn.dataset.length;
      const presetStrands = btn.dataset.strands;
      if (presetLength) calcLength.value = presetLength;
      if (presetStrands) calcStrands.value = presetStrands;
      updateCalc();
    });
  });

  updateCalc();
}

// Контакт-форма: інтеграція з Telegram Bot API
const form = document.getElementById('contactForm');
const statusEl = document.getElementById('formStatus');

/**
 * Показує pop-up повідомлення у правому нижньому куті
 * @param {string} message
 * @param {boolean} success
 */
function showPopup(message, success = true) {
  let popup = document.createElement('div');
  popup.textContent = message;
  popup.style.position = 'fixed';
  popup.style.right = '24px';
  popup.style.bottom = '24px';
  popup.style.zIndex = '9999';
  popup.style.background = success ? '#2ecc40' : '#ff4136';
  popup.style.color = '#fff';
  popup.style.padding = '16px 24px';
  popup.style.borderRadius = '8px';
  popup.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';
  popup.style.fontSize = '1rem';
  popup.style.opacity = '0';
  popup.style.transition = 'opacity 0.2s';
  document.body.appendChild(popup);
  // trigger opacity transition
  requestAnimationFrame(() => { popup.style.opacity = '1'; });
  setTimeout(() => {
    popup.style.opacity = '0';
    setTimeout(() => popup.remove(), 350);
  }, 4000);
}

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (statusEl) statusEl.textContent = 'Надсилаємо...';
  // === Вставте ваш токен і chat_id нижче ===
  const TELEGRAM_TOKEN = '7982658921:AAEJEHS_LKn2-uquieIX8pqOtB8JbHxv2oc'; // <-- ВСТАВИТИ СВІЙ ТОКЕН
  const CHAT_ID = '-4907639564';      // <-- ВСТАВИТИ СВІЙ chat_id
  // =========================================
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
  // Збираємо дані форми
  const formData = new FormData(form);
  let message = '📩 <b>Нове повідомлення з сайту:</b>\n';
  for (const [key, value] of formData.entries()) {
    message += `<b>${key}:</b> ${value}\n`;
  }
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        chat_id: CHAT_ID,
        text: message,
        parse_mode: 'HTML'
      })
    });
    if (res.ok) {
      if (statusEl) statusEl.textContent = '';
      form.reset();
      showPopup('✅ Дякуємо! Ми звʼяжемося з вами протягом 10 хвилин.', true);
    } else {
      if (statusEl) statusEl.textContent = '';
      showPopup('❌ Не вдалося надіслати. Спробуйте пізніше.', false);
    }
  } catch {
    if (statusEl) statusEl.textContent = '';
    showPopup('❌ Не вдалося надіслати. Спробуйте пізніше.', false);
  }
});

// Анімація появи карти при скролі
const mapSection = document.querySelector('.mapwrap');
if (mapSection) {
  const mapObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        mapSection.classList.add('visible');
        mapObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });
  mapObserver.observe(mapSection);
}

// === Phone Mask + Validation ===
const phoneInput = document.getElementById('phone');

if (phoneInput) {
  // Встановлюємо початкове значення
  phoneInput.value = '+380';

  // Коли користувач вводить — дозволяємо лише цифри після +380
  phoneInput.addEventListener('input', (e) => {
    let value = e.target.value;

    // Примусово зберігаємо префікс +380
    if (!value.startsWith('+380')) {
      value = '+380' + value.replace(/[^0-9]/g, '');
    }

    // Видаляємо зайвий нуль одразу після +380
    value = value.replace(/^\+3800/, '+380');

    // Залишаємо лише цифри після +380, максимум 9
    const numericPart = value.slice(4).replace(/\D/g, '').slice(0, 9);
    e.target.value = '+380' + numericPart;
  });

  // Перевірка валідності при втраті фокусу
  phoneInput.addEventListener('blur', () => {
    const phone = phoneInput.value.trim();
    const regex = /^\+380\d{9}$/;

    if (!regex.test(phone)) {
      phoneInput.setCustomValidity('Введіть номер у форматі +380XXXXXXXXX');
      phoneInput.reportValidity();
    } else {
      phoneInput.setCustomValidity('');
    }
  });
}
