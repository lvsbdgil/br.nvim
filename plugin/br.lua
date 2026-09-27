if vim.g.loaded_br_video then return end
vim.g.loaded_br_video = true
vim.api.nvim_create_user_command('BR', function() require('br').toggle() end, {})
-- Exact command-line alias; leave :bremove, searches and command arguments alone.
vim.cmd([[cnoreabbrev <expr> br getcmdtype() == ':' && getcmdline() ==# 'br' ? 'BR' : 'br']])
vim.api.nvim_create_autocmd('VimLeavePre', { callback = function() require('br').stop() end })
