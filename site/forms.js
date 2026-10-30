'use strict';
// Accepted backend API v1: server-only Telegram; no browser credentials or sends.
document.querySelectorAll('.customer-form').forEach(form => {
  const type = form.dataset.kind, key = 'qc-form-' + type;
  const fieldset = form.querySelector('fieldset'), status = form.querySelector('.form-status');
  const check = form.querySelector('.form-check'), fresh = form.querySelector('.form-new');
  const submit = form.querySelector('[type=submit]'), original = submit.textContent;
  let requestId = null, busy = false, locked = false;
  const uuidV4 = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value);
  const points = value => [...value].length;
  const controls = value => /[\u0000-\u0008\u000b-\u001f]/.test(value);
  const save = () => { try { sessionStorage.setItem(key, requestId); return sessionStorage.getItem(key) === requestId; } catch { return false; } };
  const forget = () => { try { sessionStorage.removeItem(key); } catch {} requestId = null; };
  function announce(text) { status.textContent = text; }
  function lock(value) { locked = value; fieldset.disabled = value; }
  function uncertain() {
    lock(true); check.hidden = false;
    const hasDraft = [...form.querySelectorAll('input:not([type=checkbox]),textarea')].some(input => input.value.trim().length > 0);
    const draftNote = hasDraft
      ? 'Введені дані залишаються лише на цій сторінці. Сайт не зберігає їх для відновлення після оновлення.'
      : 'У формі немає введених даних. Збережено лише технічний ідентифікатор звернення, а не текст чи контакти.';
    announce('Доставка ще не підтверджена. ' + draftNote + ' Перевірте стан або зателефонуйте студії; не надсилайте повторно.');
  }
  function retry(message) { lock(false); check.hidden = true; forget(); announce(message); }
  function reconcile(data, code, isSubmit) {
    if (isSubmit && data && data.retry_safe === true && !('request_id' in data) && !('type' in data) &&
        ({400:['request','idempotency_key','proxy_client'],403:['origin','proxy'],413:['size'],415:['content_type'],422:['validation'],429:['rate_limited'],503:['capacity','provider_capacity']})[code]?.includes(data.error)) {
      return retry(code === 429 ? 'Забагато спроб. Зачекайте та спробуйте пізніше.' : 'Звернення не надіслано. Дані збережені; перевірте їх і спробуйте пізніше або зателефонуйте.');
    }
    if (!isSubmit && code === 200 && data?.request_id === requestId && data.type === null && data.status === 'not_found' && data.retry_safe === false) return uncertain();
    if (!data || data.request_id !== requestId || data.type !== type) return uncertain();
    if (code === 200 && data.status === 'delivered' && typeof data.receipt_id === 'string' && data.receipt_id.length > 0) {
      lock(true); check.hidden = true; fresh.hidden = false;
      announce(type === 'callback' ? 'Заявку на дзвінок доставлено студії. Очікуйте зворотного зв’язку; дату запису ще не підтверджено.' : 'Приватний відгук доставлено студії. Він не публікується автоматично.');
    } else if (((isSubmit && code === 502) || (!isSubmit && code === 200)) && data.retry_safe === true && data.status === 'failed') {
      retry('Звернення не доставлено. Введені дані збережені; перевірте їх і спробуйте ще раз або зателефонуйте.');
    } else uncertain();
  }
  function invalid(name, message) {
    const input = form.elements.namedItem(name), error = document.getElementById(type + '-' + name + '-error');
    input.setAttribute('aria-invalid','true'); error.textContent = message; error.hidden = false;
  }
  function payload() {
    form.querySelectorAll('[aria-invalid]').forEach(el => el.removeAttribute('aria-invalid'));
    form.querySelectorAll('.field-error').forEach(el => { el.hidden = true; el.textContent = ''; });
    const name = form.elements.name.value.trim(), consent = form.elements.consent.checked;
    const data = {type,name,consent,source:'qc-web'};
    if (points(name) > 80 || controls(form.elements.name.value)) invalid('name','Ім’я має містити не більше 80 символів без керівних знаків.');
    if (!consent) invalid('consent','Підтвердьте, що розумієте передачу даних у Telegram.');
    if (type === 'callback') {
      let phone = form.elements.phone.value.trim(), digits = phone.replace(/\D/g,'');
      if (!/^[+\d\s()-]+$/.test(phone)) invalid('phone','Телефон може містити лише цифри, плюс, пробіли та дужки.');
      if (/^0\d{9}$/.test(digits)) phone = '+38' + digits;
      else if (/^380\d{9}$/.test(digits)) phone = '+' + digits;
      else if (phone.startsWith('+')) phone = '+' + digits;
      if (!/^\+[1-9]\d{7,14}$/.test(phone)) invalid('phone','Вкажіть дійсний телефон, наприклад +380985601157.');
      data.phone = phone;
    } else {
      data.review = form.elements.review.value.trim();
      if (points(data.review) < 10 || points(data.review) > 2000 || controls(form.elements.review.value)) invalid('review','Відгук має містити від 10 до 2000 символів без керівних знаків.');
    }
    if (form.querySelector('[aria-invalid=true]')) {
      announce('Перевірте позначені поля.'); form.querySelector('[aria-invalid=true]').focus(); return null;
    }
    return data;
  }
  async function exchange(url, options) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(),15000);
    try {
      const response = await fetch(url,{...options,credentials:'same-origin',cache:'no-store',redirect:'error',signal:controller.signal});
      const data = await response.json(); reconcile(data,response.status,options.method === 'POST');
    } catch { uncertain(); }
    finally { clearTimeout(timer); busy = false; form.removeAttribute('aria-busy'); check.disabled = false; submit.textContent = original; }
  }
  form.addEventListener('submit',event => {
    event.preventDefault(); if (busy || locked) return;
    const data = payload(); if (!data) return;
    try { requestId = crypto.randomUUID().toLowerCase(); if (!uuidV4(requestId)) throw new Error('uuid'); } catch { announce('Форма недоступна у цьому браузері. Зателефонуйте студії.'); return; } data.request_id = requestId;
    const body = JSON.stringify(data);
    if (new TextEncoder().encode(body).length > 8192) {
      invalid(type === 'review' ? 'review' : 'name','Звернення завелике. Скоротіть текст.'); announce('Звернення не надіслано: завеликий розмір.'); return;
    }
    if (!save()) { announce('Заявку не надіслано: браузер не дозволяє зберегти технічний ідентифікатор для перевірки доставки. Зателефонуйте студії.'); return; }
    busy = true; lock(true); form.setAttribute('aria-busy','true'); submit.textContent = 'Надсилаємо…'; check.hidden = true; fresh.hidden = true;
    announce('Очікуємо підтвердження доставки…');
    exchange('/api/forms',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':requestId},body});
  });
  check.addEventListener('click',() => {
    if (busy || !requestId) return; busy = true; check.disabled = true; form.setAttribute('aria-busy','true'); announce('Перевіряємо стан…');
    exchange('/api/forms/status?request_id=' + encodeURIComponent(requestId),{method:'GET'});
  });
  fresh.addEventListener('click',() => {
    if (busy) return; forget(); form.reset(); lock(false); fresh.hidden = true; check.hidden = true; announce('Можна створити нове звернення.'); form.querySelector('input,textarea').focus();
  });
  lock(false);
  try { const stored = sessionStorage.getItem(key); if (stored && uuidV4(stored)) requestId = stored; else if (stored) { lock(true); announce('Збережений ідентифікатор некоректний. Не надсилайте звернення повторно; зателефонуйте студії.'); } } catch {}
  if (requestId) { lock(true); check.hidden = false; announce('Є попереднє звернення. Перевіряємо його стан без повторної відправки.'); check.click(); }
});
