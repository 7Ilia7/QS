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

// Work-only estimate is a live draft; the backend derives its own monetary totals.
const calc = document.getElementById('calcForm');
const grams = document.getElementById('calc-grams');
const master = document.getElementById('calc-master');
const removal = document.getElementById('calc-removal');
const money = value => new Intl.NumberFormat('uk-UA').format(value) + ' ₴';
const workRates = {master: [3100, 5300, 7500, 9700], olena: [4400, 6600, 8800, 11000]};
const rangeLabels = ['Менше 50 г', 'Від 50 до менш ніж 100 г', 'Від 100 до менш ніж 200 г', 'Від 200 г'];
let currentEstimate = null;
window.qsCalculation = {get: () => currentEstimate ? {...currentEstimate} : null};
function updateEstimate() {
  if (!calc) return;
  const weight = grams.valueAsNumber, rates = workRates[master.value];
  const valid = grams.value.trim() !== '' && Number.isFinite(weight) && weight > 0 && rates;
  const whatsapp = document.getElementById('whatsapp-booking');
  currentEstimate = null;
  const values = {master: master.selectedOptions[0]?.textContent || '—', weight: '—', range: '—', work: '—', removal: '—'};
  if (!valid) {
    grams.setAttribute('aria-invalid', 'true');
    document.getElementById('calc-price').textContent = '—';
    document.getElementById('calc-breakdown').textContent = 'Введіть додатну вагу волосся в грамах.';
    document.getElementById('calc-explanation').textContent = 'Введіть додатну вагу для розрахунку. Волосся оплачується окремо.';
    if (whatsapp) whatsapp.href = 'https://wa.me/380985601157?text=' + encodeURIComponent('Добрий день! Хочу консультацію щодо нарощування. Допоможіть підібрати вагу волосся та майстра.');
  } else {
    grams.removeAttribute('aria-invalid');
    const bracket = weight < 50 ? 0 : weight < 100 ? 1 : weight < 200 ? 2 : 3;
    const work = rates[bracket], extra = removal.checked ? 1300 : 0, total = work + extra;
    currentEstimate = {version:1, master:master.value, grams:weight, removal:removal.checked, masterLabel:values.master, range:rangeLabels[bracket], work, extra, total};
    Object.assign(values,{weight:String(weight).replace('.',',')+' г',range:rangeLabels[bracket],work:money(work),removal:extra?money(extra):'Не додано'});
    document.getElementById('calc-price').textContent = money(total);
    document.getElementById('calc-breakdown').textContent = 'Робота: ' + money(work) + '; зняття: ' + money(extra) + '; разом: ' + money(total);
    document.getElementById('calc-explanation').textContent = 'Волосся оплачується окремо. Остаточний підбір узгоджуємо на консультації.';
    if (whatsapp) whatsapp.href = 'https://wa.me/380985601157?text=' + encodeURIComponent('Добрий день! Хочу консультацію щодо нарощування: '+weight+' г, '+values.master+'. Робота: '+money(work)+', зняття: '+money(extra)+', разом за роботу: '+money(total)+', без вартості волосся.');
  }
  for (const [key,value] of Object.entries(values)) document.getElementById('estimate-'+key).textContent = value;
  document.getElementById('calc-booking').disabled = !currentEstimate;
  document.dispatchEvent(new CustomEvent('qs:estimate-change'));
}
calc?.addEventListener('input', updateEstimate);
calc?.addEventListener('change', updateEstimate);
calc?.addEventListener('submit', event => event.preventDefault());
calc?.addEventListener('reset', () => requestAnimationFrame(updateEstimate));
document.getElementById('calc-booking')?.addEventListener('click', () => openCallback(true));
updateEstimate();

// Start metadata requests on page load; playback remains a native user action.
document.querySelectorAll('.video-grid video').forEach((video,index) => {
  const source = video.querySelector('source');
  const retry = document.createElement('button');
  retry.className = 'video-retry text-link';
  retry.type = 'button';
  retry.textContent = 'Повторити завантаження';
  retry.hidden = true;
  const status = document.createElement('p');
  status.className = 'video-status';
  status.id = 'video-status-' + index;
  status.setAttribute('role','status');
  status.setAttribute('aria-live','polite');
  video.after(retry,status);
  retry.setAttribute('aria-describedby',status.id);
  video.setAttribute('aria-describedby',status.id);
  function failed() {
    status.textContent = 'Не вдалося підготувати відео. Перевірте з’єднання та спробуйте ще раз.';
    retry.hidden = false;
    retry.disabled = false;
    video.dataset.mediaState = 'error';
  }
  function ready() {
    status.textContent = '';
    if (document.activeElement === retry) video.focus({preventScroll:true});
    retry.hidden = true;
    retry.disabled = false;
    video.dataset.mediaState = 'metadata-ready';
  }
  source.addEventListener('error',failed);
  video.addEventListener('error',failed);
  video.addEventListener('loadedmetadata',ready);
  video.addEventListener('canplay',ready);
  retry.addEventListener('click',() => {
    retry.disabled = true;
    status.textContent = 'Готуємо відео до перегляду…';
    video.load(); // retry preparation only; never initiate playback
  });
  if (video.error || video.networkState === 3) failed();
});

// Native horizontal scrolling gives touch swipe and scroll-snap without blocking taps.
const galleryTrack = document.getElementById('gallery');
const galleryItems = [...galleryTrack.querySelectorAll('.work')];
const galleryPrev = document.getElementById('gallery-prev');
const galleryNext = document.getElementById('gallery-next');
let galleryIndex = 0, galleryFrame = 0;
function galleryStep() {
  return galleryItems[0].getBoundingClientRect().width + (parseFloat(getComputedStyle(galleryTrack).gap) || 0);
}
function updateGallery() {
  galleryFrame = 0;
  const step = galleryStep();
  const visible = Math.max(1,Math.round((galleryTrack.clientWidth + 1) / step));
  galleryIndex = Math.min(galleryItems.length-1,Math.max(0,Math.round(galleryTrack.scrollLeft / step)));
  galleryPrev.disabled = galleryTrack.scrollLeft < 2;
  galleryNext.disabled = galleryTrack.scrollLeft >= galleryTrack.scrollWidth-galleryTrack.clientWidth-2;
  const last = Math.min(galleryItems.length,galleryIndex+visible);
  const label = 'Фото ' + (galleryIndex+1) + (last>galleryIndex+1?'–'+last:'') + ' з ' + galleryItems.length;
  const position = document.getElementById('gallery-position');
  if(position.textContent!==label)position.textContent=label;
}
function moveGallery(index,focusSlide=false) {
  const max = galleryTrack.scrollWidth-galleryTrack.clientWidth;
  const left = Math.min(max,Math.max(0,index*galleryStep()));
  galleryTrack.scrollTo({left,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  if(focusSlide) galleryItems[Math.min(galleryItems.length-1,Math.max(0,index))].focus({preventScroll:true});
}
galleryPrev.addEventListener('click',() => moveGallery(galleryIndex-1));
galleryNext.addEventListener('click',() => moveGallery(galleryIndex+1));
galleryTrack.addEventListener('keydown',event => {
  let next;
  const focusedIndex = galleryItems.indexOf(event.target.closest('.work'));
  const from = focusedIndex>=0?focusedIndex:galleryIndex;
  if(event.key==='ArrowLeft')next=from-1;
  else if(event.key==='ArrowRight')next=from+1;
  else if(event.key==='Home')next=0;
  else if(event.key==='End')next=galleryItems.length-1;
  if(next===undefined)return;
  event.preventDefault();
  moveGallery(next,event.target.matches('.work'));
});
function scheduleGallery() { if(!galleryFrame)galleryFrame=requestAnimationFrame(updateGallery); }
galleryTrack.addEventListener('scroll',scheduleGallery,{passive:true});
window.addEventListener('resize',scheduleGallery);
updateGallery();

// Booking opens the existing callback without sending a request.
function openCallback(attach = false, phoneFocus = false) {
  const form = document.getElementById('callback-form');
  if (!form) return;
  document.dispatchEvent(new CustomEvent('qs:callback-open',{detail:{attach}}));
  const locked = form.querySelector('fieldset').disabled;
  const recovery = [...form.querySelectorAll('.form-check,.form-new')].find(el => !el.hidden);
  const target = locked ? (recovery || form.querySelector('.form-status')) : (phoneFocus ? document.getElementById('callback-phone') : document.getElementById('callback-title'));
  form.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  target?.focus({preventScroll:true});
  scheduleBooking();
}
document.querySelectorAll('[data-open-callback]').forEach(link => link.addEventListener('click',event => {
  event.preventDefault(); openCallback(false,link.id === 'mobile-booking');
}));

// A compact mobile action yields space to prices, calculator, contact and keyboard.
const bookingBar = document.getElementById('mobile-booking');
let bookingFrame = 0;
function scheduleBooking() {
  if (bookingFrame) return;
  bookingFrame = requestAnimationFrame(() => {
    bookingFrame = 0;
    if (!bookingBar) return;
    const viewport = window.visualViewport;
    const keyboard = Boolean(document.activeElement?.matches('input,textarea,select,[contenteditable=true]')) || (viewport && innerHeight - viewport.height > 120);
    const overlaps = ['services','calculator','contact'].some(id => {
      const rect=document.getElementById(id)?.getBoundingClientRect();
      return rect && rect.top < innerHeight && rect.bottom > 0;
    }) || (() => {const r=document.querySelector('footer').getBoundingClientRect();return r.top < innerHeight;})();
    bookingBar.hidden = innerWidth > 760 || keyboard || overlaps || document.body.classList.contains('menu-open') || Boolean(lightbox?.open);
  });
}
['scroll','resize','focusin','focusout'].forEach(type => window.addEventListener(type,scheduleBooking,{passive:true}));
window.visualViewport?.addEventListener('resize',scheduleBooking);
scheduleBooking();

// Content slots use text nodes and local images, never HTML from supplied content.
const text = (value, max=600) => typeof value === 'string' ? value.trim().slice(0,max) : '';
const node = (tag, cls, value) => {const el=document.createElement(tag);if(cls)el.className=cls;if(value)el.textContent=value;return el;};
const validPhoto = photo => photo && /^img\/[a-zA-Z0-9/_-]+\.(webp|avif|jpe?g|png)$/.test(photo.src || '') && Number.isInteger(photo.width) && Number.isInteger(photo.height) && photo.width>0 && photo.height>0 && text(photo.alt);
function contentImage(photo) {
  const img=node('img');img.src=photo.src;img.alt=text(photo.alt,180);img.width=photo.width;img.height=photo.height;img.loading='lazy';img.decoding='async';return img;
}
function draftBadge(label='Матеріали очікуються') {return node('span','preview-badge',label);}
function renderCases(entries) {
  const list=document.getElementById('case-list');list.replaceChildren();
  const cases=Array.isArray(entries)&&entries.length?entries.slice(0,6):[{}];
  cases.forEach((item,index) => {
    item=item&&typeof item==='object'?item:{};
    const paired=item.status==='ready'&&validPhoto(item.before)&&validPhoto(item.after)&&item.before.width===item.after.width&&item.before.height===item.after.height;
    const card=node('article','case-card');
    card.append(draftBadge(paired?'Погоджені матеріали кейсу':'Макет кейсу · очікуємо пару фото'));
    card.append(node('h3','case-title',paired?(text(item.title,120)||'Порівняння до / після'):'Ваша наступна історія.'));
    const frame=node('div','comparison-frame');frame.style.setProperty('--comparison','50%');frame.dataset.paired=String(Boolean(paired));
    const after=node('div','comparison-layer comparison-after'),before=node('div','comparison-layer comparison-before');
    if(paired){before.append(contentImage(item.before));after.append(contentImage(item.after));}
    else{before.append(node('span','comparison-placeholder','Місце для фото «до»'));after.append(node('span','comparison-placeholder','Місце для фото «після»'));}
    frame.append(after,before,node('span','comparison-label comparison-label-before','ДО'),node('span','comparison-label comparison-label-after','ПІСЛЯ'));
    const divider=node('span','comparison-divider');divider.setAttribute('aria-hidden','true');divider.append(node('span','','↔'));frame.append(divider);
    const label=node('label','comparison-control','Положення межі порівняння');
    const range=node('input');range.type='range';range.min='0';range.max='100';range.step='1';range.value='50';range.id='case-range-'+index;label.htmlFor=range.id;
    const position=node('output','comparison-value','50%');position.htmlFor=range.id;
    function compare(value){const v=Math.max(0,Math.min(100,value));range.value=String(v);frame.style.setProperty('--comparison',v+'%');range.setAttribute('aria-valuetext',v+'% фото до');position.textContent=v+'%';}
    range.addEventListener('input',()=>compare(Number(range.value)));
    const move=event=>{const r=frame.getBoundingClientRect();compare(Math.round((event.clientX-r.left)/r.width*100));};
    frame.addEventListener('pointerdown',event=>{if(event.button!==0)return;frame.setPointerCapture(event.pointerId);move(event);});
    frame.addEventListener('pointermove',event=>{if(frame.hasPointerCapture(event.pointerId))move(event);});
    frame.addEventListener('pointerup',event=>{if(frame.hasPointerCapture(event.pointerId))frame.releasePointerCapture(event.pointerId);});
    card.append(frame,label,range,position);
    if(!paired)card.append(node('p','case-disclosure','Це місце для майбутнього кейсу, а не результат клієнта. Наявні роботи студії — нижче.'));
    const meta=node('dl','case-meta');
    const masterLabel=item.master==='olena'?'Тімлідер Олена':item.master==='master'?'Майстер':'Очікуємо дані';
    for(const [key,value] of [['Процедура',text(item.procedure,160)||'Очікуємо дані'],['Вага',Number.isFinite(item.grams)&&item.grams>0?item.grams+' г':'Очікуємо дані'],['Майстер',masterLabel]]){
      const row=node('div');row.append(node('dt','',key),node('dd','',paired?value:'Очікуємо дані'));meta.append(row);
    }
    card.append(meta);list.append(card);
    if(paired){const imgs=[...frame.querySelectorAll('img')];Promise.all(imgs.map(img=>img.decode())).then(()=>{if(imgs.some(img=>Math.abs(img.naturalWidth/img.naturalHeight-item.before.width/item.before.height)>.001))throw Error('frame');}).catch(()=>{frame.dataset.paired='false';frame.replaceChildren(node('p','comparison-error','Пару фото не вдалося показати з однаковим кадруванням. Потрібно уточнити матеріали.'));range.disabled=true;});}
  });
}
function renderTeam(entries) {
  const list=document.getElementById('team-profiles');list.replaceChildren();
  const fallback=[{id:'olena',name:'Олена',role:'Тімлідер'},{id:'master',role:'Майстер'}];
  (Array.isArray(entries)&&entries.length?entries.slice(0,6):fallback).forEach((person,index)=>{
    person=person&&typeof person==='object'?person:{};
    const known=person.id==='olena',name=text(person.name,100)||(known?'Олена':'Ім’я майстра додамо'),role=text(person.role,100)||(known?'Тімлідер':'Майстер');
    const card=node('article','team-profile'),portrait=node('div','team-portrait');
    function portraitPlaceholder(unavailable = false) {
      portrait.replaceChildren(node('span','portrait-number','0'+(index+1)),node('span','portrait-caption',unavailable?'Фото поки недоступне. Очікуємо погоджений портрет.':'Місце для погодженого портрета'));
    }
    if(person.status==='ready'&&validPhoto(person.portrait)) {
      const image = contentImage(person.portrait);
      const unavailable = () => { if (portrait.contains(image)) portraitPlaceholder(true); };
      image.addEventListener('error',unavailable,{once:true});
      image.addEventListener('load',() => image.decode().catch(unavailable),{once:true});
      portrait.append(image);
    } else portraitPlaceholder();
    const copy=node('div','team-copy');copy.append(draftBadge(person.status==='ready'?'Команда студії':'Профіль очікує матеріалів'),node('p','team-role',role),node('h3','',name));
    const specialties=Array.isArray(person.specialties)?person.specialties.map(s=>text(s,100)).filter(Boolean).slice(0,5):[];
    if(person.status==='ready'&&specialties.length)copy.append(node('p','team-specialties',specialties.join(' · ')));
    else copy.append(node('p','team-slot','Спеціалізацію додамо після погодження.'));
    copy.append(node('p','team-bio',person.status==='ready'&&text(person.bio)?text(person.bio):'Коротку розповідь про майстра готуємо. Досвід, відзнаки та кваліфікації без підтвердження не зазначаємо.'));
    card.append(portrait,copy);list.append(card);
  });
}
function renderReviews(entries) {
  const list=document.getElementById('review-list');
  const valid=Array.isArray(entries)?entries.filter(r=>r&&r.status==='ready'&&text(r.quote)&&text(r.author,100)&&(()=>{try{return new URL(r.source_url).protocol==='https:';}catch{return false;}})()).slice(0,8):[];
  if(!valid.length)return;
  list.replaceChildren();
  valid.forEach(review=>{const card=node('article','review-card');card.append(node('blockquote','',text(review.quote,1200)),node('p','review-author',text(review.author,100)));const link=node('a','text-link','Прочитати оригінал ↗');link.href=review.source_url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);list.append(card);});
}
function renderFAQ(entries) {
  const valid=Array.isArray(entries)?entries.filter(item=>item&&text(item.question,180)).slice(0,12):[];
  if(!valid.length)return;
  const list=document.getElementById('content-faq');list.replaceChildren();
  valid.forEach(item=>{const d=node('details');d.append(node('summary','',text(item.question,180)));const approved=['ready','existing-facts'].includes(item.status)&&text(item.answer,1600);if(!approved)d.append(draftBadge('Відповідь готується'));d.append(node('p','',approved?text(item.answer,1600):'Відповідь студії додамо після погодження. Конкретні деталі можна уточнити під час консультації.'));list.append(d);});
}
renderCases([]);renderTeam([]);
try {
  const content = window.qsStudioContent;
  if(content?.schema!=='qs.content.v1')throw Error('schema');
  renderCases(content.cases);renderTeam(content.team);renderReviews(content.reviews);renderFAQ(content.faq);scheduleBooking();
} catch {
  document.getElementById('content-load-status').textContent='Нові матеріали поки недоступні. Поточні роботи, прайс та контакти залишаються доступними.';
}
document.querySelectorAll('[data-studio-lightbox]').forEach(link=>link.addEventListener('click',event=>{
  if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||!lightbox?.showModal)return;
  event.preventDefault();lightboxImage.src=link.getAttribute('href');lightboxImage.alt=link.querySelector('img').alt;
  document.getElementById('lightbox-caption').textContent=link.dataset.caption||'';lightbox.showModal();
}));
