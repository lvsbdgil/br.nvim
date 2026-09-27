# Установка Neovim + Kitty + видео по команде :br

Гайд для macOS. Репозиторий приватный: для скачивания нужен доступ к нему через GitHub.
Видео хранится локально и не включено в репозиторий.

## 1. Установи Homebrew, если его ещё нет

Открой приложение «Терминал» и выполни:

```sh
brew --version
```

Если команда найдена, переходи к шагу 2. Иначе выполни официальную команду установки:

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Дождись завершения. Выполни команды из раздела `Next steps`, которые покажет установщик:
они добавят Homebrew в PATH. Затем заново открой терминал и проверь `brew --version`.
На Apple Silicon Homebrew обычно находится в `/opt/homebrew`, на Intel — в `/usr/local`.

Источник: [установка Homebrew](https://docs.brew.sh/Installation).

## 2. Установи программы

```sh
brew install neovim ffmpeg python
brew install --cask kitty
```

Если Neovim уже установлен, но его версия ниже 0.12:

```sh
brew update
brew upgrade neovim
```

Этот плагин требует **Neovim 0.12 или новее**: он использует `nvim_ui_send()`.
Если доступная в твоём окружении сборка старее, сначала установи совместимую версию.

Источники: [Neovim](https://formulae.brew.sh/formula/neovim),
[FFmpeg](https://formulae.brew.sh/formula/ffmpeg),
[Kitty](https://formulae.brew.sh/cask/kitty).

## 3. Открой Kitty и проверь зависимости

Открой Kitty через Spotlight (`Cmd+Space` → `kitty`) или выполни:

```sh
open -a kitty
```

Все следующие команды вводи внутри Kitty:

```sh
nvim --version
kitty --version
python3 --version
ffmpeg -version
ffprobe -version
```

Проверка нужной функции Neovim:

```sh
nvim --headless '+lua print(vim.api.nvim_ui_send ~= nil)' +qa
```

Ожидаемый ответ: `true`. Также проверь:

```sh
printenv KITTY_WINDOW_ID
```

Должен появиться номер окна. Запускай Neovim непосредственно в Kitty, без tmux и SSH.
В текущей реализации Ghostty не поддерживается; mpv не требуется.

## 4. Установи плагин из GitHub

Установи GitHub CLI и войди в аккаунт с доступом к репозиторию:

```sh
brew install gh
gh auth login
mkdir -p "$HOME/.local/share/nvim/site/pack/local/start"
gh repo clone lvsbdgil/br.nvim "$HOME/.local/share/nvim/site/pack/local/start/br.nvim"
```

Если каталог `br.nvim` уже существует, сначала закрой Neovim и перенеси прежнюю
копию в резервную папку за пределами `pack/local/start`. Затем повтори клонирование.

Проверь структуру:

```sh
ls "$HOME/.local/share/nvim/site/pack/local/start/br.nvim/plugin/br.lua"
```

Менеджер плагинов и изменение основного `init.lua` не нужны.
Пути рассчитаны на стандартную конфигурацию Neovim, без переопределения XDG/NVIM_APPNAME.

Для обновления копии, установленной через Git:

```sh
git -C "$HOME/.local/share/nvim/site/pack/local/start/br.nvim" pull --ff-only
```

После обновления перезапусти Neovim. Настройки храни в `after/plugin`, чтобы не
изменять файлы репозитория.

## 5. Положи видео в постоянное место

Рекомендуемый путь:

```text
~/Movies/test.mp4
```

Создай папку, если нужно:

```sh
mkdir -p "$HOME/Movies"
```

Скопируй видео туда через Finder и назови `test.mp4`. Плагин по умолчанию ищет файл в папке Movies текущего пользователя.

Проверка:

```sh
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,avg_frame_rate -of json "$HOME/Movies/test.mp4"
```

Для нашего тестового видео: 480×1066, 25 кадров/с. Оно не содержит звуковой дорожки.

## 6. Настрой путь для своего пользователя и размер

По умолчанию используется `~/Movies/test.mp4`; путь автоматически учитывает имя пользователя.
Следующая настройка необязательна и позволяет изменить файл, размер и отступы. Создай каталог и открой файл настроек:

```sh
mkdir -p "$HOME/.config/nvim/after/plugin"
nvim "$HOME/.config/nvim/after/plugin/br-settings.lua"
```

Если файл новый: нажми `i`, вставь код ниже, нажми `Esc`, введи `:wq` и нажми Enter.
Если файл уже существует, отредактируй существующие настройки.

```lua
require('br').setup({
  video = vim.fn.expand('~/Movies/test.mp4'),
  columns = 96,
  rows = 64,
  margin_top = 1,
  margin_right = 2,
})
```

Файл в `after/plugin` выполняется после подключения плагина.
`columns` и `rows` — максимальная область отображения в ячейках терминала.
Видео вписывается в неё с сохранением пропорций, а при маленьком окне уменьшается.
`margin_top` задаётся в строках, `margin_right` — в столбцах.

Для уменьшения размера вдвое поставь `columns = 48, rows = 32`.
Для другого постоянного видео измени только `video`, например:

```lua
video = vim.fn.expand('~/Movies/My Videos/clip.mp4'),
```

Пробелы в пути допустимы. Исходный видеофайл плагин не изменяет.

## 7. Проверь воспроизведение

Закрой и снова открой Neovim внутри Kitty:

```sh
nvim
```

В английской раскладке нажми `Esc`, введи `:br`, затем Enter.
Видео должно появиться справа сверху с отступами и воспроизводиться по кругу.
Повтори `:br` — видео исчезнет. Повтори ещё раз — воспроизведение начнётся заново.

Дополнительная проверка:

```vim
:lua print(vim.inspect(require('br').status()))
```

Во время воспроизведения `running` равно `true`, а `frames` увеличивается.
Попробуй прокрутить текст, изменить размер окна Kitty и выполнить `:redraw!`.
После полной перерисовки изображение восстанавливается на следующем кадре.

`:br` — сокращение, работающее при ручном вводе в командной строке.
Для скриптов используй `:BR` или `require('br').toggle()`.

## Если что-то не работает

### :br не запускает видео или переключает буфер

Проверь загрузку плагина:

```vim
:echo exists(':BR')
```

Ожидается `2`. Если результат `0`, проверь расположение `plugin/br.lua` из шага 4
и перезапусти Neovim. Не запускай его с `--clean`, `-u NONE` или `--noplugin`.
Если `:BR` работает, а `:br` нет, другое сокращение могло переопределить команду:

```vim
:verbose cabbrev br
```

### Ошибка «не найден ffmpeg / ffprobe / python3»

Внутри Kitty проверь:

```sh
command -v nvim ffmpeg ffprobe python3
```

Исправь PATH по инструкции Homebrew, заново открой Kitty и Neovim.

### Ошибка «требуется Neovim 0.12 или новее»

Проверь `nvim --version` и `command -v nvim`. Возможно, запускается старая копия,
стоящая в PATH раньше версии Homebrew.

### Ошибка «файл не найден»

Проверь путь в `br-settings.lua` и существование файла:

```sh
ls -l "$HOME/Movies/test.mp4"
```

### Декодер остановился / изображения нет

Посмотри `:messages`. Проверь, что работаешь локально в Kitty, и запусти проверку
`ffprobe` из шага 5. Плагин передаёт кадры через локальные временные файлы.

### Видео слишком большое

Уменьши `columns` и `rows` в настройках и перезапусти Neovim.
Для применения без перезапуска:

```vim
:lua require('br').setup({ columns = 48, rows = 32 })
```

### Видео без звука

Текущая версия выводит только видеокадры. Аудио не воспроизводится.

## Что проверено

При разработке на macOS проверены Neovim 0.12.5 и Kitty 0.49.1, воспроизведение тестового
видео поверх текста, сохранение пропорций, отступы, остановка и повторный запуск.
Чистая установка на другом Mac в этой сессии не выполнялась.
Кадры передаются как RGB24 без дополнительного сжатия; масштабируется отображение.
При высокой нагрузке воспроизведение может замедляться.

## Удаление

Закрой Neovim. В Finder нажми `Cmd+Shift+G` и открой:

```text
~/.local/share/nvim/site/pack/local/start
```

Перемести каталог `br.nvim` в корзину. Удали также созданный файл
`~/.config/nvim/after/plugin/br-settings.lua`, чтобы его настройки не обращались
к удалённому плагину. Видео и другие настройки Neovim останутся на месте.
