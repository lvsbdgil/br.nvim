-- Copy to ~/.config/nvim/after/plugin/br-settings.lua
require('br').setup({
  video = vim.fn.expand('~/Movies/test.mp4'),
  columns = 96,
  rows = 64,
  margin_top = 1,
  margin_right = 2,
})
