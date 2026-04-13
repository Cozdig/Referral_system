# Реферальная система (Referral System)

Реферальная система с авторизацией по номеру телефона, генерацией инвайт-кодов и отслеживанием рефералов.

## Функционал

1. **Авторизация по номеру телефона**
   - Ввод номера телефона
   - Генерация и отправка 4-значного кода (с имитацией задержки 1-2 секунды)
   - Подтверждение кода и создание пользователя

2. **Инвайт-коды**
   - Автоматическая генерация 6-значного инвайт-кода при первой авторизации
   - Возможность активировать чужой инвайт-код (только один раз)
   - Просмотр своего инвайт-кода

3. **Реферальная система**
   - Отслеживание пользователей, активировавших ваш инвайт-код
   - Просмотр списка рефералов в профиле

4. **Веб-интерфейс**
   - Django Templates для тестирования функционала
   - Страницы логина, верификации и профиля

## Технологии

- Python 3.11+
- Django 6.0.4
- Django REST Framework
- PostgreSQL / SQLite
- Redis (кэширование кодов)
- Celery (асинхронная отправка SMS)
- Docker (контейнеризация)
- drf-yasg (автодокументация API)

## API Документация

### Базовый URL

```
http://localhost:8000/users/
```

### Аутентификация

API использует сессионную аутентификацию. После успешной верификации кода пользователь автоматически авторизуется.

### Эндпоинты

#### 1. Запрос кода подтверждения

**POST** `/users/request-api/`

Запрашивает отправку 4-значного кода на указанный номер телефона.

**Пример запроса:**
```json
{
    "phone_number": "79520202290"
}
```

**Пример ответа (200 OK):**
```json
{
    "message": "Verification code sent successfully",
    "phone_number": "79520202290"
}
```

**Ошибка (400 Bad Request):**
```json
{
    "phone_number": ["This field is required."]
}
```

---

#### 2. Подтверждение кода

**POST** `/users/verify-api/`

Подтверждает код и выполняет авторизацию. При первом входе автоматически генерируется инвайт-код.

**Пример запроса:**
```json
{
    "phone_number": "79520202290",
    "code": "8777"
}
```

**Пример ответа (200 OK):**
```json
{
    "message": "Authentication successful",
    "user": {
        "id": 1,
        "phone_number": "79520202290",
        "invite_code": "A1B2C3",
        "activated_invite_code": null,
        "has_activated_invite_code": false,
        "referrals": [],
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

**Ошибка (400 Bad Request):**
```json
{
    "error": "Invalid verification code"
}
```

---

#### 3. Получение профиля

**GET** `/users/profile-api/`

Возвращает информацию о текущем пользователе. Требует авторизации.

**Пример ответа (200 OK):**
```json
{
    "id": 1,
    "phone_number": "79520202290",
    "invite_code": "A1B2C3",
    "activated_invite_code": "X9Y8Z7",
    "has_activated_invite_code": true,
    "referrals": [
        "79521112233",
        "79523334455"
    ],
    "created_at": "2024-01-15T10:30:00Z"
}
```

---

#### 4. Активация инвайт-кода

**POST** `/users/profile-api/`

Активирует инвайт-код другого пользователя. Требует авторизации. Можно активировать только один раз.

**Пример запроса:**
```json
{
    "invite_code": "X9Y8Z7"
}
```

**Пример ответа (200 OK):**
```json
{
    "message": "Invite code activated successfully",
    "activated_invite_code": "X9Y8Z7"
}
```

**Ошибка (400 Bad Request):**
```json
{
    "error": "Вы уже активировали инвайт-код"
}
```

---

#### 5. Выход из системы

**POST** `/users/logout-api/`

Завершает текущую сессию пользователя.

**Пример ответа (200 OK):**
```json
{
    "message": "Logged out successfully"
}
```

### Веб-интерфейс (Django Templates)

Для тестирования доступны страницы:

| URL | Описание |
|-----|----------|
| `/users/login/` | Страница входа (ввод номера телефона) |
| `/users/verify/` | Страница подтверждения кода |
| `/users/profile/` | Профиль пользователя |
| `/users/logout/` | Выход из системы |

### Автодокументация

После запуска сервера документация API доступна:

- **Swagger UI**: http://localhost:8000/swagger/


## Тестирование

### Запуск тестов

```bash
# Запуск всех тестов
python manage.py test

# Запуск с покрытием
coverage run manage.py test
coverage report
```

## Запуск проекта
### Команда для запуска проекта
```bash

# Создать .env файл
cp .env.sample .env

# Запустить проект
docker-compose up -d --build
```
## Проверить работоспособность

### Проверка web

1. Открыть в браузере
http://localhost:8000

2. Проверить логи
```bash
docker-compose logs web
```

### Проверка PostgreSQL

1. Подключиться к БД


2. Посмотреть таблицы (в psql)
```bash
\dt
```

3. Выйти
```bash
\q
```

### Проверка Redis

1. Проверить соединение
```bash
docker-compose exec redis redis-cli ping
```
Должен ответить: PONG

### Проверка Celery Worker

1. Проверить логи
```bash
docker-compose logs celery_worker
```
2. Проверить статус
```bash
docker-compose ps | grep celery_worker
```

### Проверка Celery Beat

1. Проверить логи
```bash
docker-compose logs celery_beat
```

2. Проверить статус
```bash
docker-compose ps | grep celery_beat
```

### Проверить статус всех контейнеров
```bash
docker-compose ps
```

### Проверить логи всех сервисов
```bash
docker-compose logs -f
```

### Проверить использование ресурсов
```bash
docker stats
```

## Остановка проекта
```bash
docker-compose down -v
```