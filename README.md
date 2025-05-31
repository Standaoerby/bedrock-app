# Bedrock 2.1 Starter Architecture

- `main.py`: запуск приложения, подключение ScreenManager, событий, тем
- `app_state.py`: глобальное состояние приложения
- `event_bus.py`: шина событий
- `theme_manager.py`: централизованная работа с темами и стилями
- `audio_service.py`: проигрывание звука через отдельный сервис (Voice Bonnet/I2S и др.)
- `/pages/home.py` — пример экрана (смотри архив pages)
- `/themes/minecraft/light/theme.json` — всё оформление только из темы

**Сетка позиционирования — строго 8px**

---