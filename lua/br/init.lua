local M = {}
local root = debug.getinfo(1, 'S').source:sub(2):match('^(.*)/lua/br/init.lua$')
local state
local config = { video = vim.fn.expand('~/Movies/test.mp4'), columns = 96, rows = 64, margin_top = 1, margin_right = 2 }
local esc = string.char(27)
local image_id = 1000000 + vim.fn.getpid()
local function graphics(args, data)
  return esc .. '_G' .. args .. ';' .. (data or '') .. esc .. '\\'
end
local function write(data)
  -- nvim writes its own screen first; keep cursor and graphics in one UI write.
  vim.api.nvim_ui_send(data)
end
function M.setup(opts)
  config = vim.tbl_extend('force', config, opts or {})
end
function M.stop()
  local old = state
  if not old then return end
  state = nil
  vim.fn.jobstop(old.job)
  write(graphics('a=d,d=I,i=' .. image_id .. ',q=2'))
  vim.cmd('redraw!')
end
function M.start()
  if state then return end
  if not vim.api.nvim_ui_send then
    vim.notify('br: требуется Neovim 0.12 или новее', vim.log.levels.ERROR)
    return
  end
  if not vim.env.KITTY_WINDOW_ID or vim.env.TMUX or #vim.api.nvim_list_uis() == 0 then
    vim.notify('br: запустите Neovim непосредственно в Kitty, без tmux', vim.log.levels.ERROR)
    return
  end
  for _, executable in ipairs({ 'python3', 'ffmpeg', 'ffprobe' }) do
    if vim.fn.executable(executable) == 0 then
      vim.notify('br: не найден ' .. executable, vim.log.levels.ERROR)
      return
    end
  end
  if vim.fn.filereadable(config.video) == 0 then
    vim.notify('br: файл не найден: ' .. config.video, vim.log.levels.ERROR)
    return
  end
  local s = { partial = '', errors = '', frames = 0 }
  state = s
  local dir = vim.fn.tempname() .. '-tty-graphics-protocol'
  vim.fn.mkdir(dir, 'p', 448)
  s.job = vim.fn.jobstart({ 'python3', root .. '/scripts/frames.py', config.video, dir }, {
    on_stdout = function(_, data)
      if state ~= s then return end
      s.partial = s.partial .. table.concat(data, '\n')
      while true do
        local line, rest = s.partial:match('^([^\n]*)\n(.*)$')
        if not line then break end
        s.partial = rest
        local ok, frame = pcall(vim.json.decode, line)
        if ok and frame.path then
          local right = math.min(config.margin_right, vim.o.columns - 1)
          local top = math.min(config.margin_top, vim.o.lines - 2)
          local columns = math.max(1, math.min(config.columns, vim.o.columns - right))
          local rows = math.max(1, math.min(config.rows, vim.o.lines - top - 1))
          -- Specify only width: Kitty derives height from the original aspect ratio.
          columns = math.max(1, math.min(columns, math.floor(rows * frame.cell_height
            * frame.width / frame.height / frame.cell_width)))
          vim.cmd('redraw')
          local args = string.format('a=T,t=t,f=24,s=%d,v=%d,i=%d,p=1,q=2,C=1,z=1000,c=%d',
            frame.width, frame.height, image_id, columns)
          write(esc .. '7' .. string.format(esc .. '[%d;%dH', top + 1, vim.o.columns - right - columns + 1)
            .. graphics(args, vim.base64.encode(frame.path)) .. esc .. '8')
          s.frames = s.frames + 1
          vim.fn.chansend(s.job, '\n')
        end
      end
    end,
    on_stderr = function(_, data) s.errors = (s.errors .. table.concat(data, '\n')):sub(-4000) end,
    on_exit = function(_, code)
      if state == s then
        state = nil
        write(graphics('a=d,d=I,i=' .. image_id .. ',q=2'))
        vim.notify('br: декодер остановлен (' .. code .. ') ' .. s.errors, vim.log.levels.ERROR)
      end
    end,
  })
  if s.job <= 0 then
    state = nil
    vim.fn.delete(dir, 'd')
    vim.notify('br: не удалось запустить декодер', vim.log.levels.ERROR)
  end
end
function M.toggle() if state then M.stop() else M.start() end end
function M.status() return { running = state ~= nil, frames = state and state.frames or 0 } end
return M
