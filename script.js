// Приготовить body для плавного появления
window.addEventListener('DOMContentLoaded', () => document.body.classList.add('ready'));

// Mobile menu: переключаем класс, а не inline-стили (меньше reflow)
const hamburger = document.getElementById('hamburger');
const nav = document.getElementById('nav');
if (hamburger && nav) {
  hamburger.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', String(isOpen));
    document.body.style.overflow = isOpen ? 'hidden' : '';
  });
}

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
        nav.classList.remove('open');
        document.body.style.overflow = '';
        hamburger?.setAttribute('aria-expanded', 'false');
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
