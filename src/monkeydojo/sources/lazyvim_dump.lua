-- Run inside `nvim --headless`. Writes LazyVim keymaps as JSON to $MONKEYDOJO_OUT.

local done = false

local function dump()
  if done then
    return
  end
  done = true

  local data = { lazyvim = _G.LazyVim ~= nil, maps = {}, lsp = {} }

  for _, map in ipairs(vim.api.nvim_get_keymap("n")) do
    if map.desc and map.desc ~= "" then
      table.insert(data.maps, { lhs = map.lhs, desc = map.desc })
    end
  end

  -- LSP keymaps only exist once a server attaches, so read them from the config
  if data.lazyvim then
    local ok, opts = pcall(LazyVim.opts, "nvim-lspconfig")
    local keys = ok and opts.servers and opts.servers["*"] and opts.servers["*"].keys or {}
    for _, key in ipairs(keys) do
      local mode = key.mode or "n"
      local normal = mode == "n" or (type(mode) == "table" and vim.tbl_contains(mode, "n"))
      if key.desc and normal then
        table.insert(data.lsp, { lhs = key[1], desc = key.desc })
      end
    end
  end

  local file = io.open(os.getenv("MONKEYDOJO_OUT"), "w")
  file:write(vim.json.encode(data))
  file:close()
  vim.cmd("qa!")
end

-- LazyVim sets its core keymaps on VeryLazy, which needs UIEnter (never fired in headless mode)
vim.api.nvim_create_autocmd("User", {
  pattern = "VeryLazy",
  callback = function()
    vim.defer_fn(dump, 100)
  end,
})
vim.defer_fn(dump, 5000) -- fallback if VeryLazy never fires (not LazyVim)
vim.api.nvim_exec_autocmds("UIEnter", {})
