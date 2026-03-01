# fix-gold-price: Замена источника цены золота в update_report

## Контекст
- Сайт suissegold.eu перестал отдавать данные — редиректит на антибот-страницу
  `suissegold.com/hello-there-human.php`, HTML больше не содержит `"offers":`/`"price"`.
- `scripts/update_report.py:119-126` падает с `ValueError: could not convert string to float: ''`.
- Ячейка D6 (`autodata_config`) используется для AUM-расчётов — ожидает цену ~1400-1500 EUR
  (цена 10г слитка золота в EUR).

## Источник-замена
**Kitco** (`proxy.kitco.com/getPM?symbol=AU&currency=EUR&unit=gram`)
- Бесплатный, без API-ключа, без специальных headers.
- CSV-ответ: `AU,EUR,GRAM,2026-02-27 17:00:00,143.66,143.69,143.71,2.37,1.67,140.62,143.76`
- Поле [6] = mid price EUR/грамм. Умножаем на 10 → цена за 10г.
- Разница со слитком: ~4-5% (спред дилера), допустимо для отслеживания динамики.

## План изменений
1. [ ] Заменить блок `# aum` (строки 118-126) в `scripts/update_report.py`:
       suissegold HTML-парсинг → Kitco CSV API, `mid_price * 10`.
2. [ ] Добавить защиту: try/except + logger.warning при ошибке парсинга,
       чтобы скрипт не падал если Kitco тоже временно недоступен.
3. [ ] Проверка: `just lint`, `just format`, `just types` на изменённый файл.

## Риски и открытые вопросы
- Kitco может в будущем заблокировать запросы — защитный try/except не даст скрипту упасть.
- Разница в цене (~4-5% ниже чем слиток) — допустимо, динамика та же.
- Fallback: Swissquote API (`forex-data-feed.swissquote.com`) если Kitco упадёт (не реализуем сейчас).

## Верификация
- `curl "https://proxy.kitco.com/getPM?symbol=AU&currency=EUR&unit=gram"` должен вернуть CSV.
- В D6 должно записываться число ~1400-1500 (цена 10г золота в EUR).
- Скрипт не должен падать если Kitco недоступен — логирует warning и пропускает.
