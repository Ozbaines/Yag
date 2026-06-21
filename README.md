# YAg — автоматизация вирусного контента

```
[Источники] → [Claude: фильтр+редакт] → [ТГ-бот владельца: accept/reject/edit]
                                                    ↓ accept
                                          [video-factory: нарезка 9:16]
                                                    ↓
                                [ТГ-канал] + [Instagram Reels] + [YouTube Shorts]

[Лендинг] → [ЮKassa / Prodamus] → [ТГ subscriber-bot: прогрев + PRO-доступ]
```

## Быстрый старт

### 1. Заполни `.env`

```bash
cp .env.example .env
# Открой .env и вставь токены
```

Минимум для запуска:
| Переменная | Где взять |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `TG_ADMIN_BOT_TOKEN` | @BotFather — новый бот для тебя лично |
| `TG_ADMIN_USER_ID` | свой Telegram ID (числовой, @userinfobot) |
| `TG_CHANNEL_ID` | `@username` или числовой ID канала |
| `TG_SUBSCRIBER_BOT_TOKEN` | @BotFather — второй бот для подписчиков |
| `YOUTUBE_API_KEY` | console.cloud.google.com → YouTube Data API v3 |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps |

### 2. Запусти

```bash
docker compose up -d
```

Первый запуск поднимет Postgres, Redis и все сервисы.
БД инициализируется автоматически при старте.

### 3. Проверь

```bash
# Логи content-engine (должен начать парсить источники):
docker compose logs -f content_engine

# Логи admin-бота (должен принимать команды):
docker compose logs -f tg_admin_bot

# Платёжный API health-check:
curl http://localhost:8000/health
```

### 4. Лендинг

```
http://localhost:3000
```

---

## Дополнительные API-ключи (для публикации)

| Переменная | Где взять |
|---|---|
| `IG_USER_ID` + `IG_ACCESS_TOKEN` | Meta for Developers → Graph API |
| `YT_CLIENT_ID/SECRET/REFRESH_TOKEN` | Google Cloud Console → OAuth 2.0 |
| `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY` | yookassa.ru |
| `PRODAMUS_SHOP` + `PRODAMUS_SECRET` | prodamus.ru |

## Webhook URLs для платёжных систем

```
ЮKassa:   https://your-domain.com/webhooks/yookassa
Prodamus: https://your-domain.com/webhooks/prodamus
```

Укажи их в личном кабинете соответствующего провайдера.

---

## Архитектура модулей

| Модуль | Что делает |
|---|---|
| `content_engine` | Парсит YouTube / Reddit / RSS каждые 15 мин, Claude даёт скоринг, кладёт в очередь |
| `tg_admin_bot` | Ты получаешь черновики с кнопками ✅/❌/✏️/🔁 |
| `video_factory` | yt-dlp скачивает, Whisper транскрибирует, Claude выбирает лучший момент, ffmpeg режет 9:16 |
| `dub_factory` | Берёт видео с Timeline Channel → Whisper EN → LLM выбирает клипы → XTTS-v2 озвучивает по-русски |
| `publisher` | Отправляет в ТГ-канал, Instagram Reels, YouTube Shorts |
| `tg_subscriber_bot` | Welcome + drip (4 шага), слушает оплаты и выдаёт PRO |
| `payments` | FastAPI: `/checkout` создаёт платёж, `/webhooks/*` принимает события |
| `landing` | Next.js лендинг с формой оплаты |
| `shared` | БД-модели, конфиг, Claude-клиент, Redis-очереди |

---

## Датасет для файн-тюна (dub_factory)

Каждое озвученное видео автоматически сохраняется в таблицу `dub_dataset`:
транскрипт, который ушёл в LLM, ответ LLM с выбранными клипами, русские нарративы по каждому клипу.

**Как оценить видео:**
При ревью каждого озвученного видео внизу сообщения появляются кнопки:
```
[👎 Плохо]  [👍 Хорошо]  [⭐ Отлично]
```
Нажатие сохраняет оценку. Видео файлы можно удалять — для обучения нужен только текст.

**Команды в admin-боте:**
| Команда | Что делает |
|---|---|
| `/dataset_stats` | Сколько видео оценено и с каким рейтингом |
| `/export_dataset` | Скачать `.jsonl` файл для файн-тюна |

**Формат экспорта** — OpenAI chat JSONL (совместим с llama-factory, Axolotl, OpenAI fine-tune API):
```json
{
  "messages": [
    {"role": "system", "content": "...промпт выбора клипов..."},
    {"role": "user", "content": "Длительность: 3540с\n[0s] In 490 BC..."},
    {"role": "assistant", "content": "{\"clips\": [...], \"title\": \"...\"}"}
  ],
  "_meta": {"source_url": "...", "rating": 3, "clip_count": 10}
}
```
В экспорт попадают только записи с оценкой **👍 Хорошо** или **⭐ Отлично**.

> **Примечание:** для файн-тюна нужно накопить ~50–100 оценённых видео.
> При наличии RTX 4060 (8 ГБ VRAM) можно обучить Mistral-7B / Qwen-7B локально
> через llama-factory или Axolotl — конфиги будут добавлены позже.
