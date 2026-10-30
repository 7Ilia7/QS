# Agent Notes

<!-- brainy-context-navigation:v1:start -->
## Локальний контекст

Навігація: `python3 "/Users/a1/Documents/Codex/Brainy Ag Agent/scripts/brainy_context.py" orient --project qs`.
Далі `search --project qs --query <text>` повертає bounded metadata;
`read --project qs --ref <ctx-ref>` розкриває точне локальне джерело.
Не завантажуйте всю історію. Вибраний обов'язковий SKILL.md читати повністю.
Чинний контракт: `/Users/a1/Documents/Codex/Brainy Ag Agent/docs/effective-runtime-contract.uk.md`.
Lifecycle guard та domain QA/owner scope чинні; disabled custom gates не блокують.
Resume projection потребує exact handoff/role/thread і не надає authority.
Local hash не доводить live freshness; missing не дозволяє auto-sync чи ширший scope.
<!-- brainy-context-navigation:v1:end -->


## Проект

Статический лендинг салона Quality Service Hair: наращивание волос в Киеве. Основной язык интерфейса сейчас украинский, комментарии в коде смешаны RU/UA. Проект без сборщика: открывается как обычный `index.html`.

## Структура

- `index.html` - вся разметка лендинга: SEO, шапка, hero, видео-работы, услуги, калькулятор, портфолио, отзывы, цены, преимущества, контакты, карта и footer.
- `styles.css` - все стили, адаптив, мобильное меню, карточки, галерея, калькулятор, анимации.
- `script.js` - мобильное меню, плавный скролл, видео-слайдер, lightbox, калькулятор, форма заявки через Telegram Bot API, маска телефона, анимация карты.
- `img/` - локальные изображения и логотип.

## Как запускать

Так как сборки нет, можно открыть `index.html` в браузере. Для проверки как сайт лучше запускать локальный сервер:

```powershell
python -m http.server 8000
```

Потом открыть `http://localhost:8000`.

## Важные текущие риски

- В `script.js` Telegram Bot token и `chat_id` находятся в клиентском коде. Это небезопасно: токен виден любому посетителю. Нужно вынести отправку заявки на backend/serverless endpoint.
- В `index.html` стоят заглушки `https://example.com/` в canonical, Open Graph и JSON-LD.
- В `index.html` preloaded hero image указывает на `img/hero-dark.jpg` и `img/hero-dark@2x.jpg`, которых нет в проекте.
- Open Graph image указывает на `img/og-cover.jpg`, которого нет в проекте.
- В `srcset` услуг есть ссылки на несуществующие `.jpg` файлы и опечатка `img/poslugi/.IMG_1931.webp`.
- Телефон в JSON-LD и `tel:` отличается от видимого номера: нужно привести к реальному номеру.
- `img/masteronwork.jpg` весит около 7 MB. Это сильно бьет по скорости, особенно на мобильных.
- В репозитории отслеживаются `.DS_Store`. Лучше удалить из git и добавить в `.gitignore`.
- Видео в секции работ грузятся с внешнего сайта `nkstudio.com.ua`; нужно подтвердить права, стабильность ссылок и соответствие бренду Quality Service.

## Правила работы

### Независимое реальное QA

После каждой feature/extension разработчик предоставляет READY_FOR_QA по
`operations/qa/ready-for-qa-template.md`; координатор передаёт точный build
каноническому `qs-quality-reviewer` через существующий durable lifecycle.
Полный workflow: `operations/qa/real-functional-qa.md`. Mocked/unit результаты
не заменяют реальное UI/HTTP QA; fix требует retest и affected regression.
Это инструкция передачи, не автоматический trigger/gate и не расширение прав.
Текущее чужое задание не заменять; реальные submissions требуют отдельного scope.

- Не менять бизнес-контент без явной причины: услуги, цены, тексты, номер телефона, Instagram, карту.
- Перед правками проверять реальные файлы изображений, чтобы не добавлять битые пути.
- Для ручных правок использовать `apply_patch`.
- Сохранять стиль проекта: темная премиальная эстетика, золото как акцент, украинский текст интерфейса.
- Не добавлять тяжелые библиотеки без необходимости. Сейчас лендинг легкий и статический.
- При работе с формой не хранить секреты во frontend.
- Обновлять файл Readmde после каждой сесии


## Приоритеты ближайших улучшений

1. Безопасность формы: убрать Telegram token из `script.js`, добавить backend/serverless обработчик.
2. SEO и доверие: заменить `example.com`, добавить реальный домен, адрес, телефон, корректный `og:image`, privacy page.
3. Производительность: сжать `masteronwork.jpg`, привести изображения к WebP/AVIF, убрать битые preloads и srcset.
4. Конверсия: сделать понятный путь записи, добавить реальные отзывы/кейсы, FAQ, блок гарантий и противопоказаний.
5. Масштабирование: перейти к структуре полноценного сайта с отдельными страницами услуг, портфолио, цен, блога и контактов.
