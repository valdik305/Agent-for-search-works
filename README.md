# 🤖 Job Agent Bot

Телеграм-бот для автоматического поиска удаленной работы. 
Парсит вакансии из Telegram-каналов и hh.ru, оценивает их с помощью нейросети (LLM) и присылает подходящие варианты прямо в чат. Умеет генерировать сопроводительные письма под конкретную вакансию.

## 🚀 Возможности
- Парсинг заданных Telegram-каналов (через Telethon).
- Интеграция с API hh.ru.
- Оценка релевантности вакансии (скоринг от 1 до 10) с помощью LLM (OpenAI-совместимые API: Groq, DeepSeek, Gemini).
- Генерация индивидуальных сопроводительных писем.
- Удобное управление прямо из Телеграма (кнопки: Пропустить, Письмо, Откликнулся).
- Защита от спама и лимиты на API.

## 🛠 Установка и запуск

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/ваш_никнейм/job-agent.git
   cd job-agent
   ```
### Создайте и активируйте виртуальное окружение:

```bash
python -m venv .venv
source .venv/bin/activate  # Для Mac/Linux
```
### Установите зависимости:

```
```bash
pip install -r requirements.txt
```
### Создайте файл .env (на основе .env.example) и заполните свои ключи:

```
env
BOT_TOKEN=ваш_токен_бота
OWNER_ID=ваш_telegram_id
LLM_API_KEY=ваш_ключ_нейросети
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
SCORE_MODEL=openai/gpt-oss-120b
TG_API_ID=...
TG_API_HASH=...
TG_CHANNELS=...
```
### Авторизуйте Telethon (один раз):
```
bash
python tg_login.py
```
### Запустите бота:
```
bash
python bot.py
```
### 📝 Настройка профиля

#### Отредактируйте файл profile.txt, добавив туда информацию о ваших навыках и опыте. Нейросеть будет опираться на него при оценке вакансий и написании писем.


### Шаг 4: Создаем `.env.example`

Чтобы другие люди (или ты на новом компе) знали, какие переменные нужны, создай файл **`.env.example`** (без реальных ключей!):

```env
BOT_TOKEN=
OWNER_ID=
LLM_API_KEY=
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
SCORE_MODEL=openai/gpt-oss-120b
TG_API_ID=
TG_API_HASH=
TG_CHANNELS=
MIN_SCORE=6
DAILY_APPLY_LIMIT=15