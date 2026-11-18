-- Chunckxel: Aseprite extension that turns AI-generated pixel animation frames into clean pixel
-- art. Sprite > Chunckxel... opens a dialog with a live before/after preview; Apply runs as one
-- undo step (fake-pixel mode makes a new sprite instead). The algorithms live in
-- chunckxel_core.lua and chunckxel_fake.lua (pure Lua, shared with the headless tests).

local core = nil
local fakem = nil -- chunckxel_fake.lua (option C)
local api = {}

local BG_OPTIONS = { "None", "Auto (border colour)", "Picked colour" }
local SPLIT_OPTIONS = { "Empty columns", "Grid" }
local SCALE_OPTIONS = { "1x", "2x -> 1x (tone)", "2x -> 1x (2x2 mode)" }
local PAL_OPTIONS = { "Keep colours", "Map to sprite palette" }
local TARGET_OPTIONS = { "Current frame", "Selected frames", "Current tag", "All frames" }
local FAKE_OPTIONS = { "Off", "Auto", "Manual size" }
local SAMPLER_OPTIONS = { "Dominant", "Centre pixel" }

-- ------------------------------------------------------------------ image <-> frame
local function color_key(c)
  return (c.red << 16) | (c.green << 8) | c.blue
end

-- palette lookups for indexed / map mode
local function palette_info(spr)
  local pal = spr.palettes[1]
  local tr = spr.transparentColor
  local lut, keys, rev, seen = {}, {}, {}, {}
  for i = 0, #pal - 1 do
    local c = pal:getColor(i)
    local k = color_key(c)
    local usable = c.alpha >= 128 and not (spr.colorMode == ColorMode.INDEXED and i == tr)
    lut[i] = usable and k or -1
    if usable then
      if rev[k] == nil then rev[k] = i end
      if not seen[k] then seen[k] = true; keys[#keys + 1] = k end
    end
  end
  return { lut = lut, keys = keys, rev = rev, transparent = tr }
end

-- decode an Aseprite image into a frame (hard alpha at 128)
local function decode_image(img, pinfo)
  local w, h = img.width, img.height
  local bytes, stride = img.bytes, img.rowStride
  local mode = img.colorMode
  if mode == ColorMode.RGB then
    if stride ~= w * 4 then
      local rows = {}
      for y = 0, h - 1 do rows[#rows + 1] = bytes:sub(y * stride + 1, y * stride + w * 4) end
      bytes = table.concat(rows)
    end
    return core.from_rgba(bytes, w, h, 128)
  end
  local f = core.new_frame(w, h, -1)
  local byte = string.byte
  for y = 0, h - 1 do
    if mode == ColorMode.INDEXED then
      local t = { byte(bytes, y * stride + 1, y * stride + w) }
      for x = 0, w - 1 do f.px[y * w + x + 1] = pinfo.lut[t[x + 1]] or -1 end
    elseif mode == ColorMode.GRAY then
      local t = { byte(bytes, y * stride + 1, y * stride + w * 2) }
      for x = 0, w - 1 do
        local v, a = t[2 * x + 1], t[2 * x + 2]
        if a >= 128 then f.px[y * w + x + 1] = (v << 16) | (v << 8) | v end
      end
    end
  end
  return f
end

-- full-canvas frame of a cel (cel = nil -> empty)
local function cel_frame(spr, cel, pinfo)
  local W, H = spr.width, spr.height
  if not cel then return core.new_frame(W, H, -1) end
  local sub = decode_image(cel.image, pinfo)
  local f = core.new_frame(W, H, -1)
  local ox, oy = cel.position.x, cel.position.y
  for y = 0, sub.h - 1 do
    local ty = oy + y
    if ty >= 0 and ty < H then
      for x = 0, sub.w - 1 do
        local tx = ox + x
        if tx >= 0 and tx < W then f.px[ty * W + tx + 1] = sub.px[y * sub.w + x + 1] end
      end
    end
  end
  return f
end

local function rgb_image(f)
  local img = Image(f.w, f.h, ColorMode.RGB)
  img.bytes = core.to_rgba(f)
  return img
end

-- encode a frame for the sprite's colour mode
local function encode_image(f, mode, pinfo)
  if mode == ColorMode.RGB then return rgb_image(f) end
  local img = Image(f.w, f.h, mode)
  local stride = img.rowStride
  local rows = {}
  local char = string.char
  local near = {}
  for y = 0, f.h - 1 do
    local t = {}
    for x = 0, f.w - 1 do
      local k = f.px[y * f.w + x + 1]
      if mode == ColorMode.INDEXED then
        local idx
        if k < 0 then
          idx = pinfo.transparent
        else
          idx = pinfo.rev[k]
          if idx == nil then
            idx = near[k]
            if idx == nil then
              idx = (#pinfo.keys > 0) and pinfo.rev[core.nearest(k, pinfo.keys)] or 0
              near[k] = idx
            end
          end
        end
        t[#t + 1] = idx
      else -- GRAY: value, alpha
        if k < 0 then
          t[#t + 1] = 0; t[#t + 1] = 0
        else
          local r, g, b = (k >> 16) & 255, (k >> 8) & 255, k & 255
          local v = (r == g and g == b) and r or math.floor(0.299 * r + 0.587 * g + 0.114 * b + 0.5)
          t[#t + 1] = v; t[#t + 1] = 255
        end
      end
    end
    local row = char(table.unpack(t))
    if #row < stride then row = row .. string.rep("\0", stride - #row) end
    rows[#rows + 1] = row
  end
  img.bytes = table.concat(rows)
  return img
end

local function frame_empty(f)
  for i = 1, f.w * f.h do
    if f.px[i] >= 0 then return false end
  end
  return true
end

-- ------------------------------------------------------------------ targets / options
local function current_tag(spr, cur)
  local ok, t = pcall(function() return app.tag end)
  if ok and t then return t end
  for _, tag in ipairs(spr.tags) do
    if tag.fromFrame.frameNumber <= cur and cur <= tag.toFrame.frameNumber then return tag end
  end
  return nil
end

function api.target_frames(spr, which)
  local cur = app.frame and app.frame.frameNumber or 1
  local list = {}
  if which == "Current frame" then
    list = { cur }
  elseif which == "Selected frames" then
    local r = app.range
    if r and not r.isEmpty and #r.frames > 0 then
      for _, fr in ipairs(r.frames) do list[#list + 1] = fr.frameNumber end
    else
      list = { cur }
    end
  elseif which == "Current tag" then
    local tag = current_tag(spr, cur)
    if tag then
      for i = tag.fromFrame.frameNumber, tag.toFrame.frameNumber do list[#list + 1] = i end
    end
  end
  if #list == 0 then
    for i = 1, #spr.frames do list[#list + 1] = i end
  end
  table.sort(list)
  return list
end

-- dialog data -> normalized options (shared by core, chunckxel_fake.lua and the tests)
function api.options_from(d, spr)
  local bgmap = { [BG_OPTIONS[1]] = "none", [BG_OPTIONS[2]] = "auto", [BG_OPTIONS[3]] = "pick" }
  local o = {
    smear = d.smear,
    pal_thr = d.palthr / 1000,
    lonely = d.lonely,
    speck = d.speck,
    outline = d.outline,
    match = d.match,
    match_thr = d.matchthr / 1000,
    loop = d.loop,
    bg = bgmap[d.bg] or "none",
    bgkey = d.bgcolor and color_key(d.bgcolor) or 0,
    bgtol = d.bgtol,
    bgcont = d.bgcont,
    scale = (d.scale == SCALE_OPTIONS[1]) and 1 or 2,
    method = (d.scale == SCALE_OPTIONS[3]) and "mode" or "tone",
    target = d.target,
    fake = (d.fake == FAKE_OPTIONS[2]) and "auto" or ((d.fake == FAKE_OPTIONS[3]) and "manual" or "off"),
    cell = (d.cell and d.cell >= 2) and d.cell or nil,
    sampler = (d.sampler == SAMPLER_OPTIONS[2]) and "centre" or "dominant",
    split = d.fsplit,
  }
  if o.fake ~= "off" then
    -- fake pixels always lose their flat background (border colour unless one is picked)
    if o.bg == "none" then o.bg = "auto" end
    if o.fake == "manual" and not o.cell then o.fake = "auto" end
  end
  if d.palmode == PAL_OPTIONS[2] and spr then
    local keys = palette_info(spr).keys
    if #keys > 0 then o.target_palette = keys end
  end
  return o
end

function api.default_data()
  return {
    bg = BG_OPTIONS[1], bgcolor = Color{ r = 255, g = 255, b = 255 }, bgtol = 16, bgcont = true,
    split = SPLIT_OPTIONS[1], gcols = 4, grows = 1,
    fake = FAKE_OPTIONS[1], cell = 8, sampler = SAMPLER_OPTIONS[1], fsplit = true,
    smear = true, palthr = 45, lonely = true, speck = 4, outline = true,
    match = true, matchthr = 80, loop = true,
    scale = SCALE_OPTIONS[1], palmode = PAL_OPTIONS[1], target = TARGET_OPTIONS[4], ncand = 8,
  }
end

local function apply_background(fs, o)
  if o.bg == "auto" then
    return core.remove_background(fs, core.border_colour(fs), o.bgtol, o.bgcont)
  elseif o.bg == "pick" then
    return core.remove_background(fs, o.bgkey, o.bgtol, o.bgcont)
  end
  return fs
end

-- frames in -> frames out (background, then cleanup or 2x downscale + cleanup)
function api.run(fs, o)
  local _, out = fakem.run_frames(fs, o)
  return out
end

local function check_layer(layer)
  if not layer then return "No active layer." end
  if layer.isGroup then return "The active layer is a group. Select an image layer." end
  if layer.isTilemap then return "Tilemap layers are not supported." end
  if layer.isReference then return "Reference layers are not supported." end
  return nil
end

-- read the target frames of the active layer: frames, original images (for the preview)
function api.read_targets(spr, layer, nums)
  local pinfo = palette_info(spr)
  local fs = {}
  for i, n in ipairs(nums) do fs[i] = cel_frame(spr, layer:cel(n), pinfo) end
  return fs, pinfo
end

-- Apply: one transaction = one undo step
function api.apply(spr, layer, o)
  local err = check_layer(layer)
  if err then return false, err end
  if o.scale == 2 and (spr.width < 2 or spr.height < 2) then return false, "Sprite too small for 2x -> 1x." end
  local nums = api.target_frames(spr, o.target)
  local fs, pinfo = api.read_targets(spr, layer, nums)
  local out = api.run(fs, o)
  local mode = spr.colorMode
  app.transaction("Chunckxel", function()
    if layer.isBackground then
      app.layer = layer
      app.command.LayerFromBackground()
    end
    if o.scale == 2 then spr:resize(spr.width // 2, spr.height // 2) end
    for i, n in ipairs(nums) do
      local f = out[i]
      local cel = layer:cel(n)
      if frame_empty(f) then
        if cel then spr:deleteCel(cel) end
      else
        local img = encode_image(f, mode, pinfo)
        if cel then
          cel.image = img
          cel.position = Point(0, 0)
        else
          spr:newCel(layer, n, img, Point(0, 0))
        end
      end
    end
  end)
  app.refresh()
  return true, string.format("Chunckxel: %d frame(s) done.", #nums)
end

-- new RGB sprite from frames (all the same size), palette copied from `from`
local function sprite_from_frames(frames, from, name)
  local fw, fh = frames[1].w, frames[1].h
  local ns = Sprite(fw, fh, ColorMode.RGB)
  if from then pcall(function() ns:setPalette(from.palettes[1]) end) end
  local lay = ns.layers[1]
  for i, fr in ipairs(frames) do
    if i > 1 then ns:newEmptyFrame() end
    if not frame_empty(fr) then ns:newCel(lay, i, rgb_image(fr), Point(0, 0)) end
  end
  ns.filename = name
  return ns
end

-- Split the current cel (a sprite sheet) into a NEW sprite, one frame per cell
function api.split_sheet(spr, layer, cur, o, split_mode, cols, rows)
  local err = check_layer(layer)
  if err then return nil, err end
  local pinfo = palette_info(spr)
  local f = cel_frame(spr, layer:cel(cur), pinfo)
  f = apply_background({ f }, o)[1]
  local frames, info
  if split_mode == SPLIT_OPTIONS[2] then
    frames = core.split_grid(f, cols, rows)
    info = string.format("%d frames (grid %dx%d)", #frames, cols, rows)
  else
    frames, info = core.split_columns(f)
  end
  if #frames == 0 then return nil, "Nothing to split (" .. info .. ")." end
  if frames[1].w < 1 or frames[1].h < 1 then return nil, "Grid cells are empty." end
  return sprite_from_frames(frames, spr, "chunckxel_split"), info
end

-- ---------------------------------------------------------------- option C (fake pixels)
-- the current cel as one full-canvas frame (a fake-pixel image or a sheet of them)
function api.fake_source(spr, layer, frame_number)
  local err = check_layer(layer)
  if err then return nil, err end
  return cel_frame(spr, layer:cel(frame_number), palette_info(spr))
end

function api.run_fake(src, o, cache)
  return fakem.fake_to_pixels(src, o, cache)
end

function api.fake_info(res)
  local g = res.grid
  return string.format("cell %.2f x %.2f px -> %d frame(s) %dx%d (%s)", g.size_x, g.size_y, #res.frames,
    res.frames[1] and res.frames[1].w or 0, res.frames[1] and res.frames[1].h or 0, res.info)
end

-- Apply in fake mode: the result becomes a NEW sprite at the detected size
function api.apply_fake(spr, layer, o, frame_number, res)
  if not res then
    local src, err = api.fake_source(spr, layer, frame_number)
    if not src then return nil, err end
    res = api.run_fake(src, o)
  end
  if #res.frames == 0 then return nil, "Nothing left after background removal." end
  local ns = sprite_from_frames(res.frames, spr, "chunckxel_fake")
  return ns, "Chunckxel: new sprite, " .. api.fake_info(res)
end

-- candidates for the current settings: fake mode -> on the current cel, else on the target frames
function api.candidates(spr, layer, o, n, frame_number)
  local err = check_layer(layer)
  if err then return nil, err end
  if o.fake ~= "off" then
    local src = api.fake_source(spr, layer, frame_number)
    return fakem.run_candidates(src, o, "fake", n)
  end
  local nums = api.target_frames(spr, o.target)
  local fs = api.read_targets(spr, layer, nums)
  return fakem.run_candidates(fs, o, (o.scale == 2) and "down2x" or "clean", n)
end

-- ------------------------------------------------------------------ dialog
local function open_dialog()
  local spr = app.sprite
  if not spr then return app.alert("Chunckxel: open a sprite first.") end
  local dd = api.default_data()
  local state = { before = {}, after = {}, nums = {}, info = "", cands = {}, thumbs = {}, sel = nil,
    override = nil, cache = {}, cache_key = nil, fake_res = nil }
  local dlg

  local function site_key(s, layer)
    return tostring(s and s.filename) .. "|" .. tostring(layer and layer.name) .. "|" ..
      tostring(app.frame and app.frame.frameNumber)
  end

  local function current_opts(s)
    if state.override then return state.override end
    return api.options_from(dlg.data, s)
  end

  local function compute()
    local s, layer = app.sprite, app.layer
    state.before, state.after, state.nums, state.fake_res = {}, {}, {}, nil
    if not s then state.info = "No sprite."; return end
    local err = check_layer(layer)
    if err then state.info = err; return end
    local o = current_opts(s)
    local t0 = os.clock()
    local key = site_key(s, layer)
    if key ~= state.cache_key then state.cache, state.cache_key = {}, key end
    if o.fake ~= "off" then
      local fnum = app.frame and app.frame.frameNumber or 1
      local res
      if state.sel and state.cands[state.sel] and state.cands[state.sel].res then
        res = state.cands[state.sel].res
      else
        res = api.run_fake(api.fake_source(s, layer, fnum), o, state.cache)
      end
      state.fake_res = res
      local cel = layer:cel(fnum)
      local b = Image(s.spec)
      if cel then b:drawImage(cel.image, cel.position) end
      state.before = { b }
      for i, f in ipairs(res.frames) do
        state.after[i] = rgb_image(f)
        state.nums[i] = i
      end
      state.info = string.format("%s, %.2fs", api.fake_info(res), os.clock() - t0)
      return
    end
    local nums = api.target_frames(s, o.target)
    local fs = api.read_targets(s, layer, nums)
    local out
    if state.sel and state.cands[state.sel] and state.cands[state.sel].frames then
      out = state.cands[state.sel].frames
    else
      out = api.run(fs, o)
    end
    for i, n in ipairs(nums) do
      local cel = layer:cel(n)
      local b = Image(s.spec)
      if cel then b:drawImage(cel.image, cel.position) end
      state.before[i] = b
      if out[i] then state.after[i] = rgb_image(out[i]) end
    end
    state.nums = nums
    local colours, nc = {}, 0
    for _, f in ipairs(out) do
      for p = 1, f.w * f.h do
        local k = f.px[p]
        if k >= 0 and not colours[k] then colours[k] = true; nc = nc + 1 end
      end
    end
    state.info = string.format("%d frame(s), %dx%d -> %dx%d, %d colours, %.2fs", #nums, s.width, s.height,
      out[1] and out[1].w or 0, out[1] and out[1].h or 0, nc, os.clock() - t0)
  end

  local function preview_index()
    local v = dlg.data.pframe or 1
    if v > #state.nums then v = #state.nums end
    if v < 1 then v = 1 end
    return v
  end

  -- recompute the preview; the preview-frame slider starts at the timeline's current frame and
  -- keeps the user's choice afterwards (reset when the frame count changes)
  local function refresh(force)
    if not force and not dlg.data.live then return end
    local prev_n = #state.nums
    local ok, err = pcall(compute)
    if not ok then state.info = "Error: " .. tostring(err) end
    local n = math.max(1, #state.nums)
    local v = dlg.data.pframe or 1
    if #state.nums ~= prev_n or v > n then
      v = 1
      local cur = app.frame and app.frame.frameNumber or 1
      for i, fnum in ipairs(state.nums) do
        if fnum == cur then v = i end
      end
    end
    dlg:modify{ id = "pframe", min = 1, max = n, value = v }
    dlg:modify{ id = "info", text = state.info }
    dlg:repaint()
  end

  local text_colour = Color{ r = 255, g = 255, b = 255 }
  pcall(function()
    local c = app.theme.color.text
    if c then text_colour = c end
  end)

  local function checker(gc, x0, y0, w, h)
    local cs = 6
    for yy = 0, h - 1, cs do
      for xx = 0, w - 1, cs do
        local light = ((xx // cs) + (yy // cs)) % 2 == 0
        gc.color = light and Color{ r = 170, g = 170, b = 170 } or Color{ r = 140, g = 140, b = 140 }
        gc:fillRect(Rectangle(x0 + xx, y0 + yy, math.min(cs, w - xx), math.min(cs, h - yy)))
      end
    end
  end

  local function draw_fit(gc, img, x0, y0, w, h)
    if not img then return end
    local s = math.max(1, math.min(w // img.width, h // img.height))
    local dw, dh = img.width * s, img.height * s
    if dw > w or dh > h then -- larger than the box: shrink to fit
      local f = math.min(w / img.width, h / img.height)
      dw, dh = math.max(1, math.floor(img.width * f)), math.max(1, math.floor(img.height * f))
    end
    gc:drawImage(img, Rectangle(0, 0, img.width, img.height), Rectangle(x0 + (w - dw) // 2, y0 + (h - dh) // 2, dw, dh))
  end

  local function paint(ev)
    local gc = ev.context
    local W, H = gc.width, gc.height
    gc.antialias = false
    local pad, head = 4, 14
    local pw = (W - 3 * pad) // 2
    local ph = H - head - pad
    local idx = preview_index()
    local before = state.before[idx] or state.before[1]
    local panes = { { "Before", before }, { "After", state.after[idx] } }
    for p, pane in ipairs(panes) do
      local x0 = pad + (p - 1) * (pw + pad)
      checker(gc, x0, head, pw, ph)
      gc.color = text_colour
      local label = pane[1]
      if p == 2 and state.nums[idx] then
        label = label .. "  (frame " .. state.nums[idx] .. (state.sel and (", cand. " .. state.sel) or "") .. ")"
      end
      gc:fillText(label, x0, 1)
      draw_fit(gc, pane[2], x0, head, pw, ph)
    end
  end

  -- candidate thumbnails: 4 per row
  local CAND_COLS = 4
  local function cand_rect(i, W, H)
    local rows = math.max(1, math.ceil(#state.cands / CAND_COLS))
    local cw = (W - (CAND_COLS + 1) * 3) // CAND_COLS
    local ch = (H - (rows + 1) * 3) // rows
    local c, r = (i - 1) % CAND_COLS, (i - 1) // CAND_COLS
    return 3 + c * (cw + 3), 3 + r * (ch + 3), cw, ch
  end

  local function paint_cands(ev)
    local gc = ev.context
    local W, H = gc.width, gc.height
    state.cw, state.ch = W, H
    gc.antialias = false
    if #state.cands == 0 then
      gc.color = text_colour
      gc:fillText("Generate candidates to compare settings (scores 0-100).", 4, 4)
      return
    end
    local best = 1
    for i, c in ipairs(state.cands) do
      if c.score > state.cands[best].score then best = i end
    end
    for i, c in ipairs(state.cands) do
      local x, y, w, h = cand_rect(i, W, H)
      checker(gc, x, y + 11, w, h - 11)
      draw_fit(gc, state.thumbs[i], x, y + 11, w, h - 11)
      gc.color = text_colour
      gc:fillText(string.format("%s%d %.1f", (i == best) and "*" or "#", i, c.score), x, y)
      if i == state.sel then
        gc.color = Color{ r = 255, g = 200, b = 0 }
        gc:strokeRect(Rectangle(x, y + 11, w, h - 11))
      end
    end
  end

  -- widget values that a candidate's options map onto (cell +-1 stays in the override only)
  local function show_opts(o)
    dlg:modify{ id = "palthr", value = math.floor(o.pal_thr * 1000 + 0.5) }
    dlg:modify{ id = "outline", selected = o.outline }
    dlg:modify{ id = "smear", selected = o.smear }
    dlg:modify{ id = "lonely", selected = o.lonely }
    dlg:modify{ id = "match", selected = o.match }
    dlg:modify{ id = "speck", value = o.speck }
    dlg:modify{ id = "matchthr", value = math.floor(o.match_thr * 1000 + 0.5) }
    dlg:modify{ id = "sampler", option = (o.sampler == "centre") and SAMPLER_OPTIONS[2] or SAMPLER_OPTIONS[1] }
    if o.scale == 2 then
      dlg:modify{ id = "scale", option = (o.method == "mode") and SCALE_OPTIONS[3] or SCALE_OPTIONS[2] }
    end
  end

  local function pick_cand(ev)
    if #state.cands == 0 then return end
    local W, H = state.cw or 360, state.ch or 132
    for i = 1, #state.cands do
      local x, y, w, h = cand_rect(i, W, H)
      if ev.x >= x and ev.x < x + w and ev.y >= y and ev.y < y + h then
        state.sel = i
        state.override = state.cands[i].opts
        show_opts(state.override)
        local c = state.cands[i]
        local p = c.parts
        dlg:modify{ id = "candinfo", text = string.format(
          "#%d %s: %.1f (fid %.2f grid %.2f outl %.2f lonely %.2f col %d flick %.2f)",
          i, c.name, c.score, p.fidelity, p.grid, p.outline, p.lonely, p.n_colours, p.flicker) }
        refresh(true)
        return
      end
    end
  end

  -- any manual change drops the picked candidate
  local function on_change()
    state.sel, state.override = nil, nil
    refresh(false)
  end

  local function on_fake_change()
    if dlg.data.fake ~= FAKE_OPTIONS[1] then
      -- smear removal targets PixelLab motion trails; on a resampled drawing it eats light-grey parts
      dlg:modify{ id = "smear", selected = false }
    end
    state.cands, state.thumbs = {}, {}
    on_change()
  end

  local function generate()
    local s = app.sprite
    if not s then return end
    state.sel, state.override = nil, nil
    local o = api.options_from(dlg.data, s)
    local t0 = os.clock()
    local ok, cands, err = pcall(api.candidates, s, app.layer, o, dlg.data.ncand, app.frame and app.frame.frameNumber or 1)
    if not ok then app.alert("Chunckxel candidates failed: " .. tostring(cands)); return end
    if not cands then app.alert(tostring(err)); return end
    state.cands, state.thumbs = cands, {}
    local best = 1
    for i, c in ipairs(cands) do
      if c.frames[1] then state.thumbs[i] = rgb_image(c.frames[1]) end
      if c.score > cands[best].score then best = i end
    end
    dlg:modify{ id = "candinfo", text = string.format("%d candidates in %.1fs, best #%d %s (%.1f). Click one.",
      #cands, os.clock() - t0, best, cands[best] and cands[best].name or "-", cands[best] and cands[best].score or 0) }
    dlg:repaint()
  end

  dlg = Dialog{ title = "Chunckxel", onclose = function() state = nil end }
  dlg:separator{ text = "Input" }
  dlg:combobox{ id = "bg", label = "Background", options = BG_OPTIONS, option = dd.bg, onchange = on_change }
  dlg:color{ id = "bgcolor", label = "Picked colour", color = dd.bgcolor, onchange = on_change }
  dlg:slider{ id = "bgtol", label = "BG tolerance", min = 0, max = 128, value = dd.bgtol, onrelease = on_change }
  dlg:check{ id = "bgcont", text = "Only connected to the border", selected = dd.bgcont, onclick = on_change }
  dlg:combobox{ id = "split", label = "Sheet split", options = SPLIT_OPTIONS, option = dd.split }
  dlg:number{ id = "gcols", label = "Grid cols / rows", text = tostring(dd.gcols), decimals = 0 }
  dlg:number{ id = "grows", text = tostring(dd.grows), decimals = 0 }
  dlg:button{ id = "dosplit", text = "Split current cel -> new sprite", onclick = function()
    local s = app.sprite
    if not s then return end
    local d = dlg.data
    local ok, ns, info = pcall(api.split_sheet, s, app.layer, app.frame.frameNumber,
      api.options_from(d, s), d.split, math.max(1, math.floor(d.gcols)), math.max(1, math.floor(d.grows)))
    if not ok then app.alert("Chunckxel split failed: " .. tostring(ns)); return end
    if not ns then app.alert(info); return end
    dlg:modify{ id = "info", text = "Split: " .. info .. " -> new sprite" }
    on_change()
  end }

  dlg:separator{ text = "Fake pixels (image-model 'pixel art')" }
  dlg:combobox{ id = "fake", label = "Fake pixels", options = FAKE_OPTIONS, option = dd.fake, onchange = on_fake_change }
  dlg:number{ id = "cell", label = "Manual cell size", text = tostring(dd.cell), decimals = 2, onchange = on_change }
  dlg:combobox{ id = "sampler", label = "Cell colour", options = SAMPLER_OPTIONS, option = dd.sampler, onchange = on_change }
  dlg:check{ id = "fsplit", text = "Split frames on empty columns", selected = dd.fsplit, onclick = on_change }

  dlg:separator{ text = "Cleanup" }
  dlg:check{ id = "smear", text = "Remove smears / outside ghosts", selected = dd.smear, onclick = on_change }
  dlg:slider{ id = "palthr", label = "Palette merge (x0.001)", min = 0, max = 120, value = dd.palthr, onrelease = on_change }
  dlg:check{ id = "lonely", text = "Fix lonely pixels", selected = dd.lonely, onclick = on_change }
  dlg:slider{ id = "speck", label = "Drop specks smaller than", min = 1, max = 16, value = dd.speck, onrelease = on_change }
  dlg:check{ id = "outline", text = "Outline 2px -> 1px", selected = dd.outline, onclick = on_change }
  dlg:check{ id = "match", text = "Frame match (anti-flicker)", selected = dd.match, onclick = on_change }
  dlg:slider{ id = "matchthr", label = "Match threshold (x0.001)", min = 0, max = 200, value = dd.matchthr, onrelease = on_change }
  dlg:check{ id = "loop", text = "Animation loops (first <-> last)", selected = dd.loop, onclick = on_change }

  dlg:separator{ text = "Output" }
  dlg:combobox{ id = "scale", label = "Downscale", options = SCALE_OPTIONS, option = dd.scale, onchange = on_change }
  dlg:combobox{ id = "palmode", label = "Palette", options = PAL_OPTIONS, option = dd.palmode, onchange = on_change }
  dlg:combobox{ id = "target", label = "Frames", options = TARGET_OPTIONS, option = dd.target, onchange = on_change }

  dlg:separator{ text = "Preview" }
  dlg:canvas{ id = "canvas", width = 360, height = 200, onpaint = paint }
  dlg:slider{ id = "pframe", label = "Preview frame", min = 1, max = 1, value = 1, onchange = function() dlg:repaint() end }
  dlg:check{ id = "live", text = "Live preview", selected = true, onclick = function() refresh(false) end }
  dlg:button{ id = "update", text = "Update preview", onclick = function()
    state.cache, state.cache_key = {}, nil
    refresh(true)
  end }
  dlg:newrow()
  dlg:label{ id = "info", text = "" }

  dlg:separator{ text = "Candidates" }
  dlg:slider{ id = "ncand", label = "Count", min = 1, max = 12, value = dd.ncand }
  dlg:button{ id = "gencand", text = "Generate candidates", onclick = generate }
  dlg:canvas{ id = "cands", width = 360, height = 132, onpaint = paint_cands, onmousedown = pick_cand }
  dlg:newrow()
  dlg:label{ id = "candinfo", text = "" }

  dlg:newrow()
  dlg:button{ id = "apply", text = "Apply", focus = true, onclick = function()
    local s = app.sprite
    if not s then return end
    local o = current_opts(s)
    if o.fake ~= "off" then
      -- a picked candidate is applied as shown; otherwise recompute with the current settings
      local ok, ns, msg = pcall(api.apply_fake, s, app.layer, o, app.frame and app.frame.frameNumber or 1,
        state.sel and state.fake_res or nil)
      if not ok then app.alert("Chunckxel failed: " .. tostring(ns)); return end
      if not ns then app.alert(msg); return end
      dlg:modify{ id = "info", text = msg }
      state.sel, state.override, state.cands, state.thumbs = nil, nil, {}, {}
      dlg:modify{ id = "fake", option = FAKE_OPTIONS[1] }
      refresh(false)
      return
    end
    local ok, done, msg = pcall(api.apply, s, app.layer, o)
    if not ok then app.alert("Chunckxel failed: " .. tostring(done)); return end
    if not done then app.alert(msg); return end
    dlg:modify{ id = "info", text = msg .. " (Ctrl+Z undoes it)" }
    state.sel, state.override, state.cands, state.thumbs = nil, nil, {}, {}
    refresh(false)
  end }
  dlg:button{ id = "close", text = "Close", onclick = function() dlg:close() end }
  dlg:show{ wait = false }
  refresh(true)
end
api.open_dialog = open_dialog

-- ------------------------------------------------------------------ plugin entry points
function init(plugin)
  core = dofile(app.fs.joinPath(plugin.path, "chunckxel_core.lua"))
  fakem = dofile(app.fs.joinPath(plugin.path, "chunckxel_fake.lua"))(core)
  api.core = core
  api.fake = fakem
  plugin:newCommand{
    id = "Chunckxel",
    title = "Chunckxel...",
    group = "sprite_crop",
    onclick = open_dialog,
    onenabled = function() return app.sprite ~= nil end,
  }
end

function exit(plugin)
end

-- for headless tests (tests/batch_smoke.lua)
chunckxel_api = api
