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
  const y = window.scrollY || document.documentElement.scrollTop;
  if (header) header.classList.toggle('scrolled', y > 10);
  if (toTop) {
    if (y > 400) { toTop.hidden = false; } else { toTop.hidden = true; }
  }
};
window.addEventListener('scroll', onScroll, { passive: true });
toTop?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

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

// Контакт-форма (Formspree-ready). Замени URL на свой endpoint
const form = document.getElementById('contactForm');
const statusEl = document.getElementById('formStatus');
form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (statusEl) statusEl.textContent = 'Надсилаємо...';
  try {
    // Пример Formspree:
    // const res = await fetch('https://formspree.io/f/XXXXX', { method:'POST', body: new FormData(form) });

    // Заглушка (ваш бекенд):
    const res = await fetch('/', { method: 'POST', body: new FormData(form) });

    if (res.ok) {
      if (statusEl) statusEl.textContent = 'Дякуємо! Ми зв’яжемося з вами.';
      form.reset();
    } else {
      if (statusEl) statusEl.textContent = 'Сталася помилка. Спробуйте ще раз.';
    }
  } catch {
    if (statusEl) statusEl.textContent = 'Сталася помилка мережі.';
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
