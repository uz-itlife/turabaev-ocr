# turabaev-ocr

OCR-пайплайн для оцифровки сканированного **русско-каракалпакского словаря
Турабаева** (622 стр., без текстового слоя) в структурированный JSON для
словарных и переводческих приложений.

## Структура репозитория
```
turabaev-ocr/
├── turabaev_pipeline.py            # пайплайн: split → OCR → parse → JSON
├── requirements.txt
├── data/
│   └── samples/
│       └── turabaev_sample_p150-156.json   # 189 статей со стр. 150–156 (пример)
├── .gitignore
└── LICENSE
```
Исходные сканы (PDF и 6 разбитых частей ~244 МБ) **в репозитории не хранятся** —
см. `.gitignore`. Держи их во внешнем хранилище или Git LFS.

## Формат статьи
```json
{
  "headword": "ДОСТИЖЕНИЕ",
  "lemma": "ДОСТИЖЕНИ/Е",
  "gram": "-я, сущ. ср.",
  "translation": "жетискенлик, табыс, ерисиўшилик; ...",
  "body": "...полный текст статьи (без потерь)...",
  "page": 150
}
```

## Установка
```bash
pip install -r requirements.txt
```
Нужны также **tesseract 5.x** и **poppler** (`pdftoppm`) в PATH.

### Языковые модели (один раз)
Положить в папку tessdata и указать `TESSDATA_PREFIX`:
```
https://github.com/tesseract-ocr/tessdata_best/raw/main/rus.traineddata
https://github.com/tesseract-ocr/tessdata_best/raw/main/kaz.traineddata
https://github.com/tesseract-ocr/tessdata_best/raw/main/uzb_cyrl.traineddata
```
`kaz` + `uzb_cyrl` вместе покрывают каракалпакские буквы қ ғ ң ә ө ү ў ҳ і.

### Windows
- tesseract — сборка UB Mannheim: https://github.com/UB-Mannheim/tesseract/wiki
- poppler — https://github.com/oschwartz10612/poppler-windows (добавить `bin` в PATH)

## Запуск
```bash
# весь словарь
python turabaev_pipeline.py "Turabaev...slovar.pdf" --out ./out --dpi 300 --batch 50

# одна часть (для параллельного прогона)
python turabaev_pipeline.py "Turabaev...slovar.pdf" --out ./out --first 105 --last 208
```
Результат: `out/batch_pNNN-NNN.json` по частям + `out/turabaev_merged.json` целиком.
Ориентир: ~27 статей/стр. → ~16–17 тыс. статей со всех 622.

### Весь словарь в параллель (Windows)
6 частей одновременно + автомёрж — самый быстрый путь:
```powershell
powershell -ExecutionPolicy Bypass -File run_all.ps1 `
    -Pdf "D:\...\Turabaev...slovar.pdf" -Tessdata "D:\tools\tessdata" -Dpi 300
```
На многоядерной машине это кратно быстрее последовательного прогона.
Прогон по времени: tessdata_best на 300 DPI — ориентировочно 1–2.5 часа суммарно
на обычном CPU, в параллель — заметно меньше. Для скорости можно `-Dpi 200`.

### Собрать результат из частей вручную
Если части гнались по отдельности в разные папки:
```bash
python merge_batches.py ./out -o ./out/turabaev_merged.json
```
Мёрж дедуплицирует и сортирует по странице — повторный запуск любой части
безопасен (resumable).

## Качество и доводка
OCR ~95% по кириллице. Типичные ошибки: ў↔}, ҳ↔х, ә↔е, н↔ш, переносы.
`body` всегда содержит полный текст — если `gram`/`translation` разделились
неточно, ничего не теряется. Под приложение полезно: словарь автозамен частых
OCR-ошибок, дробление `translation` по значениям `1. 2. 3.` и примерам.

## Лицензия
MIT — культурно-просветительский проект по сохранению каракалпакского языка.
