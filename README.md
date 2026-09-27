# br.nvim

Видео поверх текста Neovim в правом верхнем углу Kitty. Команда `:br` включает
и выключает воспроизведение. Видео зациклено; отступы и пропорции сохраняются.

## Требования

- Linux или macOS, Kitty и Neovim **0.12+** (`nvim_ui_send`).
- Python 3.9+ (`python3`), `ffmpeg` и `ffprobe` в PATH.
- Локальный запуск Neovim непосредственно в Kitty, без tmux и SSH.

## Установка на Linux

[Полный гайд для Linux](docs/INSTALL.linux.ru.md) — Debian/Ubuntu, Fedora,
Arch/Manjaro и openSUSE. Сначала скачай этот приватный репозиторий через GitHub CLI
или Git с настроенным SSH, затем из его каталога:

```sh
bash scripts/linux-deps.sh --dry-run
bash scripts/linux-deps.sh
# Если пакетный Neovim старее 0.12:
python3 scripts/install-neovim.py
export PATH="$HOME/.local/bin:$PATH"
python3 scripts/br.py install --video "$HOME/Videos/test.mp4"
# Следующую команду выполняй внутри Kitty:
python3 scripts/br.py doctor --video "$HOME/Videos/test.mp4"
nvim
```

`linux-deps.sh` устанавливает системные пакеты через sudo; на Arch также обновляет систему.
Остальные скрипты запускаются без sudo. Каталог репозитория должен оставаться на месте:
установщик создаёт на него ссылку. Пользовательский `init.lua` не меняется.
Видео нужно заранее положить по указанному пути.

## Установка на macOS

```sh
brew install neovim ffmpeg python gh
brew install --cask kitty
gh auth login
mkdir -p "$HOME/.local/share/nvim/site/pack/local/start"
gh repo clone lvsbdgil/br.nvim "$HOME/.local/share/nvim/site/pack/local/start/br.nvim"
```

Для приватного репозитория аккаунту нужен доступ. Если каталог установки уже
существует, сначала перенеси его в резервную папку за пределами `pack/local/start`.

Положи видео в `~/Movies/test.mp4`. Открой Kitty, запусти `nvim`, введи `:br` и Enter.
Повтори команду для остановки. Видео не включено в репозиторий.

[Гайд macOS и устранение ошибок](docs/INSTALL.ru.md).

## Настройки

Скопируй [пример](examples/br-settings.lua) в
`~/.config/nvim/after/plugin/br-settings.lua` или создай этот файл:

```lua
require('br').setup({
  video = vim.fn.expand('~/Movies/test.mp4'),
  columns = 96,
  rows = 64,
  margin_top = 1,
  margin_right = 2,
})
```

`columns` / `rows` ограничивают область отображения в ячейках терминала.
Ширина рассчитывается с учётом высоты, а Kitty сохраняет пропорции исходного кадра.
Отступ сверху измеряется в строках, справа — в столбцах.
Настройки применяются к следующему кадру; изменение пути — при следующем запуске видео.

## Команды и Lua API

- `:br` — точное сокращение при ручном вводе команды.
- `:BR` — полная пользовательская команда, подходящая также для скриптов.
- `require('br').toggle()`, `.start()`, `.stop()` — управление.
- `require('br').status()` — `{ running = boolean, frames = number }`.

Вызов `vim.cmd('br')` не раскрывает сокращение: используй `vim.cmd('BR')`.
При выходе из Neovim плагин останавливает декодер.

## Как это работает

FFmpeg декодирует исходное видео в RGB24. Кадры без дополнительного сжатия
передаются через временные файлы по
[Kitty Graphics Protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/).
Положительный z-index помещает изображение поверх текста. Исходное видео не
изменяется; масштабируется только отображение. Символьная графика не используется.

`plugin/br.lua` регистрирует команды, `lua/br/init.lua` управляет выводом,
`scripts/frames.py` декодирует видео и очищает временные файлы.

## Проверка и ограничения

При разработке проверены Neovim 0.12.5, Kitty 0.49.1, видео 480×1066 при 25 кадрах/с:
вывод поверх текста, отступы, пропорции, остановка и повторный запуск.
Чистая установка на другом Mac не проверялась.

Аудио не воспроизводится. Ориентация берётся из закодированных кадров без применения
метаданных поворота; предполагаются квадратные пиксели. Частота воспроизведения
основана на средней частоте кадров, поэтому точные временные интервалы VFR не сохраняются.
При перегрузке воспроизведение может замедлиться. Полная перерисовка Neovim может
временно убрать изображение до следующего кадра. Маленькое окно ограничивает размер видео.

## Скрипты управления

Запускай из корня репозитория:

| Команда | Назначение |
|---|---|
| `bash scripts/linux-deps.sh [--dry-run]` | Установка пакетов Linux / просмотр команд |
| `python3 scripts/install-neovim.py [--dry-run]` | Официальный stable Neovim для Linux с проверкой SHA256 |
| `python3 scripts/br.py install --video /путь/видео.mp4` | Подключить плагин и создать настройки |
| `python3 scripts/br.py configure --video /путь/видео.mp4 --columns 48 --rows 32` | Изменить настройки с резервной копией |
| `python3 scripts/br.py doctor --video /путь/видео.mp4` | Проверить зависимости, файл, установку и сеанс Kitty |
| `python3 scripts/br.py update` | Обновить чистую Git-копию через fast-forward |
| `python3 scripts/br.py uninstall` | Удалить управляемую ссылку, сохранить настройки в резервной копии |

Пути с пробелами заключай в кавычки. Настройки учитывают XDG и `NVIM_APPNAME`.
Для статической диагностики вне Kitty добавь `--no-terminal` к `doctor`.
`configure` записывает все параметры: передавай свой `--video` при каждом вызове.

## Проверки автоматизации

```sh
python3 -m unittest discover -s tests -v
bash -n scripts/linux-deps.sh
```

Тесты проверяют установку в изолированный профиль, повторную установку, резервные копии,
защиту чужих файлов, пути с кавычками, tty Linux/macOS и реальное декодирование FFmpeg в PTY
с очисткой временных кадров. GitHub Actions запускает их на Ubuntu 24.04 и проверяет
установку официальной сборки Neovim. Графический вывод на Linux требует отдельной
ручной проверки в Kitty; CI не заменяет эту проверку.

## Обновление

```sh
git -C "$HOME/.local/share/nvim/site/pack/local/start/br.nvim" pull --ff-only
```

Перезапусти Neovim после обновления.

## Удаление

Закрой Neovim и удали каталог `br.nvim` из `site/pack/local/start`.
Также удали файл `after/plugin/br-settings.lua`, если создавал его.
