-- Chunckxel core: cleanup for AI-generated pixel animation frames (RGBA, true 1:1 pixels).
-- Lua port of ArtSource/tools/pixel_cleanup2.py (clean_frames) and ArtSource/tools/downscale2x.py.
-- Pure Lua 5.4, no Aseprite API, so it runs anywhere (the extension and headless tests share it).
--
-- Frame format: { w = W, h = H, px = { [y*W + x + 1] = key } }
--   key = -1 for transparent, otherwise 0xRRGGBB (alpha is always 255 after hard alpha).
-- Every step returns a NEW frame; inputs are never modified.

local M = {}

local floor, sqrt, abs = math.floor, math.sqrt, math.abs

-- ------------------------------------------------------------------ colour helpers
local function to_lin(c)
  if c <= 0.04045 then return c / 12.92 end
  return ((c + 0.055) / 1.055) ^ 2.4
end

-- numpy's cbrt is the C library cbrt; Lua has none. pow(x, 1/3) plus one Newton step lands on
-- the same double in practice (checked against numpy in the parity test).
local THIRD = 1 / 3
local function cbrt(x)
  if x == 0 then return 0.0 end
  if x < 0 then return -cbrt(-x) end
  local y = x ^ THIRD
  return y - (y * y * y - x) / (3 * y * y)
end
M.cbrt = cbrt

local lab_cache = {}
-- OKLab of a key; returns L, a, b. Same operation order as pixel_cleanup2.oklab.
local function oklab(k)
  local t = lab_cache[k]
  if t then return t[1], t[2], t[3] end
  local r = to_lin(((k >> 16) & 255) / 255.0)
  local g = to_lin(((k >> 8) & 255) / 255.0)
  local b = to_lin((k & 255) / 255.0)
  local l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
  local m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
  local s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
  l, m, s = cbrt(l), cbrt(m), cbrt(s)
  local L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
  local A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
  local B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
  lab_cache[k] = { L, A, B }
  return L, A, B
end
M.oklab = oklab

local function lab_dist(k1, k2)
  local L1, a1, b1 = oklab(k1)
  local L2, a2, b2 = oklab(k2)
  local dL, da, db = L1 - L2, a1 - a2, b1 - b2
  return sqrt(dL * dL + da * da + db * db)
end
M.lab_dist = lab_dist

local lum_cache = {}
-- relative luminance 0..1 (sRGB weights on gamma values), as pixel_cleanup2.lum
local function lum(k)
  if k < 0 then return 0.0 end
  local v = lum_cache[k]
  if v then return v end
  v = (0.2126 * ((k >> 16) & 255) + 0.7152 * ((k >> 8) & 255) + 0.0722 * (k & 255)) / 255
  lum_cache[k] = v
  return v
end
M.lum = lum

local function is_grey(k)
  if k < 0 then return false end
  local r, g, b = (k >> 16) & 255, (k >> 8) & 255, k & 255
  local mx = r > g and r or g; if b > mx then mx = b end
  local mn = r < g and r or g; if b < mn then mn = b end
  return (mx - mn) <= 30 and mx >= 110 and mx <= 250
end

local function copy_frame(f)
  local px = {}
  local s = f.px
  for i = 1, f.w * f.h do px[i] = s[i] end
  return { w = f.w, h = f.h, px = px }
end
M.copy_frame = copy_frame

local function new_frame(w, h, fill)
  local px = {}
  for i = 1, w * h do px[i] = fill end
  return { w = w, h = h, px = px }
end
M.new_frame = new_frame

-- ------------------------------------------------------------------ RGBA bytes <-> frame
-- bytes: string of W*H*4 bytes in R,G,B,A order (Aseprite Image.bytes for RGB images).
-- Hard alpha (step 1) happens here: alpha >= cut -> opaque, else transparent.
function M.from_rgba(bytes, w, h, cut)
  cut = cut or 128
  local px = {}
  local byte = string.byte
  local n = w * h
  local CH = 4096 -- pixels per chunk (string.byte returns at most a few thousand values safely)
  local i = 1
  while i <= n do
    local last = i + CH - 1
    if last > n then last = n end
    local t = { byte(bytes, (i - 1) * 4 + 1, last * 4) }
    local j = 1
    for p = i, last do
      local r, g, b, a = t[j], t[j + 1], t[j + 2], t[j + 3]
      if a >= cut then px[p] = (r << 16) | (g << 8) | b else px[p] = -1 end
      j = j + 4
    end
    i = last + 1
  end
  return { w = w, h = h, px = px }
end

function M.to_rgba(f)
  local parts = {}
  local char = string.char
  local px = f.px
  local n = f.w * f.h
  local CH = 1024
  local i = 1
  while i <= n do
    local last = i + CH - 1
    if last > n then last = n end
    local t = {}
    local j = 1
    for p = i, last do
      local k = px[p]
      if k < 0 then
        t[j], t[j + 1], t[j + 2], t[j + 3] = 0, 0, 0, 0
      else
        t[j], t[j + 1], t[j + 2], t[j + 3] = (k >> 16) & 255, (k >> 8) & 255, k & 255, 255
      end
      j = j + 4
    end
    parts[#parts + 1] = char(table.unpack(t))
    i = last + 1
  end
  return table.concat(parts)
end

-- ------------------------------------------------------------------ mask helpers
-- connected components of a boolean mask (array 1..W*H), 8-neighbour by default
local function comps(mask, w, h, diag)
  local seen = {}
  local out = {}
  local nb
  if diag == false then
    nb = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }
  else
    nb = { { -1, -1 }, { -1, 0 }, { -1, 1 }, { 0, -1 }, { 0, 1 }, { 1, -1 }, { 1, 0 }, { 1, 1 } }
  end
  for y = 0, h - 1 do
    for x = 0, w - 1 do
      local i = y * w + x + 1
      if mask[i] and not seen[i] then
        seen[i] = true
        local st, comp = { i }, {}
        local sp = 1
        while sp > 0 do
          local c = st[sp]; st[sp] = nil; sp = sp - 1
          comp[#comp + 1] = c
          local cy, cx = (c - 1) // w, (c - 1) % w
          for _, d in ipairs(nb) do
            local ny, nx = cy + d[1], cx + d[2]
            if ny >= 0 and ny < h and nx >= 0 and nx < w then
              local ni = ny * w + nx + 1
              if mask[ni] and not seen[ni] then
                seen[ni] = true
                sp = sp + 1; st[sp] = ni
              end
            end
          end
        end
        out[#out + 1] = comp
      end
    end
  end
  return out
end
M.comps = comps

-- square dilation with radius r; out-of-bounds counts as false (pixel_cleanup2._shift_any)
local function dilate(m, w, h, r)
  local tmp, out = {}, {}
  for y = 0, h - 1 do
    local row = y * w
    for x = 0, w - 1 do
      local v = false
      local x0, x1 = x - r, x + r
      if x0 < 0 then x0 = 0 end
      if x1 > w - 1 then x1 = w - 1 end
      for xx = x0, x1 do
        if m[row + xx + 1] then v = true; break end
      end
      tmp[row + x + 1] = v
    end
  end
  for y = 0, h - 1 do
    local y0, y1 = y - r, y + r
    if y0 < 0 then y0 = 0 end
    if y1 > h - 1 then y1 = h - 1 end
    for x = 0, w - 1 do
      local v = false
      for yy = y0, y1 do
        if tmp[yy * w + x + 1] then v = true; break end
      end
      out[y * w + x + 1] = v
    end
  end
  return out
end

-- silhouette edge: opaque pixel with an N4 neighbour that is transparent or out of bounds
local function edge_mask(px, w, h)
  local e = {}
  for y = 0, h - 1 do
    for x = 0, w - 1 do
      local i = y * w + x + 1
      local v = false
      if px[i] >= 0 then
        if y == 0 or y == h - 1 or x == 0 or x == w - 1 then
          v = true
        elseif px[i - w] < 0 or px[i + w] < 0 or px[i - 1] < 0 or px[i + 1] < 0 then
          v = true
        end
      end
      e[i] = v
    end
  end
  return e
end

local N4 = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } }

-- ------------------------------------------------------------------ steps
-- 2a. light low-saturation groups that barely touch the sprite (motion trails, dust)
function M.remove_smears(f, max_ratio, min_size)
  max_ratio = max_ratio or 0.13
  min_size = min_size or 3
  local w, h, src = f.w, f.h, f.px
  local g = copy_frame(f)
  local grey, other = {}, {}
  for i = 1, w * h do
    local k = src[i]
    local gr = is_grey(k)
    grey[i] = gr
    other[i] = (k >= 0) and not gr
  end
  for _, comp in ipairs(comps(grey, w, h, true)) do
    if #comp >= min_size then
      local touch = 0
      for _, i in ipairs(comp) do
        local cy, cx = (i - 1) // w, (i - 1) % w
        for _, d in ipairs(N4) do
          local ny, nx = cy + d[1], cx + d[2]
          if ny >= 0 and ny < h and nx >= 0 and nx < w and other[ny * w + nx + 1] then
            touch = touch + 1
            break
          end
        end
      end
      if touch / #comp <= max_ratio then
        for _, i in ipairs(comp) do g.px[i] = -1 end
      end
    end
  end
  return g
end

-- 2b. thin light wisps outside the dark outline; solid grey blocks are protected, gaps get
-- the frame's outline colour.
function M.remove_outside_ghosts(f, dark_lum, solid_r)
  dark_lum = dark_lum or 0.24
  solid_r = solid_r or 2
  local w, h, src = f.w, f.h, f.px
  local n = w * h
  local ghost, notghost, dark = {}, {}, {}
  for i = 1, n do
    local k = src[i]
    local gr = is_grey(k)
    ghost[i] = gr
    notghost[i] = not gr
    dark[i] = (k >= 0) and lum(k) <= dark_lum
  end
  local a = dilate(notghost, w, h, solid_r)
  local inv = {}
  for i = 1, n do inv[i] = not a[i] end
  local opened = dilate(inv, w, h, solid_r)
  local dd = dilate(dark, w, h, 1)
  local passable = {}
  for i = 1, n do
    passable[i] = ghost[i] and not dd[i] and not (opened[i] and ghost[i])
  end
  local reach = {}
  local st, sp = {}, 0
  local any = false
  for y = 0, h - 1 do
    for x = 0, w - 1 do
      local i = y * w + x + 1
      if passable[i] then
        local seed = false
        for _, d in ipairs(N4) do
          local ny, nx = y + d[1], x + d[2]
          if ny < 0 or ny >= h or nx < 0 or nx >= w or src[ny * w + nx + 1] < 0 then
            seed = true; break
          end
        end
        if seed then
          reach[i] = true; any = true
          sp = sp + 1; st[sp] = i
        end
      end
    end
  end
  while sp > 0 do
    local i = st[sp]; st[sp] = nil; sp = sp - 1
    local y, x = (i - 1) // w, (i - 1) % w
    for _, d in ipairs(N4) do
      local ny, nx = y + d[1], x + d[2]
      if ny >= 0 and ny < h and nx >= 0 and nx < w then
        local ni = ny * w + nx + 1
        if passable[ni] and not reach[ni] then
          reach[ni] = true
          sp = sp + 1; st[sp] = ni
        end
      end
    end
  end
  if not any then return copy_frame(f) end
  -- outline colour = most common dark pixel on the silhouette edge (ties: smallest key)
  local edge = edge_mask(src, w, h)
  local cnt = {}
  local has_de = false
  for i = 1, n do
    if edge[i] and dark[i] then
      cnt[src[i]] = (cnt[src[i]] or 0) + 1
      has_de = true
    end
  end
  local g = copy_frame(f)
  local px = g.px
  for i = 1, n do if reach[i] then px[i] = -1 end end
  if has_de then
    local oc, best = nil, -1
    for k, c in pairs(cnt) do
      if c > best or (c == best and k < oc) then oc, best = k, c end
    end
    local rest = {}
    for i = 1, n do
      local k = px[i]
      rest[i] = (k >= 0) and not (lum(k) <= dark_lum)
    end
    for y = 0, h - 1 do
      for x = 0, w - 1 do
        local i = y * w + x + 1
        if reach[i] then
          if (y > 0 and rest[i - w]) or (y < h - 1 and rest[i + w])
              or (x > 0 and rest[i - 1]) or (x < w - 1 and rest[i + 1]) then
            px[i] = oc
          end
        end
      end
    end
  end
  return g
end

-- 3. one palette for all frames: merge near-duplicate colours in OKLab; each group keeps its
-- most-used real colour; rare colours fold into the nearest bigger group.
-- Returns frames, assign (key -> key), palette (sorted list of kept keys).
-- opts.target_palette (list of keys, optional): after merging, every group colour is mapped
-- to the nearest colour of that palette (palette mode "map").
function M.unify_palette(frames, thr, rare, rare_thr, target_palette)
  thr = thr or 0.045
  rare = rare or 3
  rare_thr = rare_thr or 0.12
  local counts, order, idx = {}, {}, {}
  for _, f in ipairs(frames) do
    local fc = {}
    local px = f.px
    for i = 1, f.w * f.h do
      local k = px[i]
      if k >= 0 then fc[k] = (fc[k] or 0) + 1 end
    end
    local ks = {}
    for k in pairs(fc) do ks[#ks + 1] = k end
    table.sort(ks)
    for _, k in ipairs(ks) do
      if not counts[k] then
        counts[k] = 0
        order[#order + 1] = k
        idx[k] = #order
      end
      counts[k] = counts[k] + fc[k]
    end
  end
  -- stable sort by count, descending (Python's sorted keeps insertion order on ties)
  local keys = {}
  for i, k in ipairs(order) do keys[i] = k end
  table.sort(keys, function(p, q)
    if counts[p] ~= counts[q] then return counts[p] > counts[q] end
    return idx[p] < idx[q]
  end)
  local centers, assign = {}, {}
  for _, k in ipairs(keys) do
    local merged = false
    if #centers > 0 then
      local bj, bd = nil, math.huge
      for j, c in ipairs(centers) do
        local d = lab_dist(c, k)
        if d < bd then bd, bj = d, j end
      end
      if bd <= thr then
        assign[k] = centers[bj]
        merged = true
      end
    end
    if not merged then
      centers[#centers + 1] = k
      assign[k] = k
    end
  end
  local tot = {}
  for k, v in pairs(assign) do tot[v] = (tot[v] or 0) + counts[k] end
  local big = {}
  for _, c in ipairs(centers) do
    if tot[c] > rare then big[#big + 1] = c end
  end
  if #big > 0 then
    for _, c in ipairs(centers) do
      if tot[c] <= rare then
        local bj, bd = nil, math.huge
        for j, bc in ipairs(big) do
          local d = lab_dist(bc, c)
          if d < bd then bd, bj = d, j end
        end
        if bd <= rare_thr then
          local tgt = big[bj]
          for k, v in pairs(assign) do
            if v == c then assign[k] = tgt end
          end
        end
      end
    end
  end
  if target_palette and #target_palette > 0 then
    local near = {}
    for k, v in pairs(assign) do
      local m = near[v]
      if m == nil then
        m = M.nearest(v, target_palette)
        near[v] = m
      end
      assign[k] = m
    end
  end
  local out = {}
  for fi, f in ipairs(frames) do
    local g = copy_frame(f)
    local px = g.px
    for i = 1, f.w * f.h do
      local k = px[i]
      if k >= 0 then px[i] = assign[k] end
    end
    out[fi] = g
  end
  local set, pal = {}, {}
  for _, v in pairs(assign) do
    if not set[v] then set[v] = true; pal[#pal + 1] = v end
  end
  table.sort(pal)
  return out, assign, pal
end

-- nearest colour (OKLab) of key k in a list of keys
function M.nearest(k, list)
  local best, bd = list[1], math.huge
  for _, c in ipairs(list) do
    if c == k then return c end
    local d = lab_dist(c, k)
    if d < bd then bd, best = d, c end
  end
  return best
end

-- 4. isolated pixel: all 8 neighbours share one other colour -> take it (unless high contrast)
function M.remove_lonely(f, keep_dl)
  keep_dl = keep_dl or 0.30
  local w, h, src = f.w, f.h, f.px
  local g = copy_frame(f)
  local px = g.px
  for y = 1, h - 2 do
    for x = 1, w - 2 do
      local i = y * w + x + 1
      local c = src[i]
      if c >= 0 then
        local n0 = src[i - w - 1]
        if n0 >= 0 and n0 ~= c
            and src[i - w] == n0 and src[i - w + 1] == n0
            and src[i - 1] == n0 and src[i + 1] == n0
            and src[i + w - 1] == n0 and src[i + w] == n0 and src[i + w + 1] == n0 then
          local Lc = oklab(c)
          local Lu = oklab(src[i - w])
          if abs(Lc - Lu) < keep_dl then px[i] = src[i - w] end
        end
      end
    end
  end
  return g
end

-- 5. detached groups (8-connected) smaller than `speck` px are dropped
function M.drop_specks(f, speck)
  speck = speck or 4
  local w, h, src = f.w, f.h, f.px
  local g = copy_frame(f)
  if speck <= 1 then return g end
  local op = {}
  for i = 1, w * h do op[i] = src[i] >= 0 end
  for _, comp in ipairs(comps(op, w, h, true)) do
    if #comp < speck then
      for _, i in ipairs(comp) do g.px[i] = -1 end
    end
  end
  return g
end

-- 6. outline to 1px: silhouette-edge dark run of exactly 2 px followed by fill -> inner dark
-- pixel takes the fill colour, only along bands >= `band` px long.
function M.thin_outline(f, dark_lum, band)
  dark_lum = dark_lum or 0.24
  band = band or 3
  local w, h, src = f.w, f.h, f.px
  local n = w * h
  local dark = {}
  for i = 1, n do
    local k = src[i]
    dark[i] = (k >= 0) and lum(k) <= dark_lum
  end
  local edge = edge_mask(src, w, h)
  local marks = {}
  for di, d in ipairs(N4) do
    local dy, dx = d[1], d[2]
    local m, fill, ford = {}, {}, {}
    for y = 0, h - 1 do
      for x = 0, w - 1 do
        local qy, qx = y + 2 * dy, x + 2 * dx
        if qy >= 0 and qy < h and qx >= 0 and qx < w then
          local i = y * w + x + 1
          local pi = (y + dy) * w + (x + dx) + 1
          local qi = qy * w + qx + 1
          local by, bx = y - dy, x - dx
          local outside_tr = by < 0 or by >= h or bx < 0 or bx >= w or src[by * w + bx + 1] < 0
          if outside_tr and dark[i] and dark[pi] and not edge[pi]
              and src[qi] >= 0 and not dark[qi] then
            m[pi] = true
            if fill[pi] == nil then ford[#ford + 1] = pi end
            fill[pi] = src[qi]
          end
        end
      end
    end
    marks[di] = { m, fill, ford, dy, dx }
  end
  local cand, cord = {}, {}
  for _, mk in ipairs(marks) do
    local m, fill, ford, dy = mk[1], mk[2], mk[3], mk[4]
    local ay, ax
    if dy ~= 0 then ay, ax = 0, 1 else ay, ax = 1, 0 end
    for _, pi in ipairs(ford) do
      local py, px_ = (pi - 1) // w, (pi - 1) % w
      local run = 1
      for s = 1, -1, -2 do
        local t = 1
        while true do
          local yy, xx = py + s * t * ay, px_ + s * t * ax
          if yy >= 0 and yy < h and xx >= 0 and xx < w and m[yy * w + xx + 1] then
            run = run + 1; t = t + 1
          else
            break
          end
        end
      end
      if run >= band and cand[pi] == nil then
        cand[pi] = fill[pi]
        cord[#cord + 1] = pi
      end
    end
  end
  local g = copy_frame(f)
  for _, pi in ipairs(cord) do g.px[pi] = cand[pi] end
  return g
end

-- 7. neighbour-frame match: prev and next frame agree and this frame is only slightly
-- different -> follow them (removes colour flicker)
function M.match_neighbours(frames, thr, loop)
  thr = thr or 0.08
  if loop == nil then loop = true end
  local n = #frames
  if n < 3 then return frames end
  local out = {}
  for i = 1, n do out[i] = copy_frame(frames[i]) end
  for i = 1, n do
    if loop or (i ~= 1 and i ~= n) then
      local a = frames[((i - 2) % n) + 1].px
      local b = frames[(i % n) + 1].px
      local c = frames[i].px
      local o = out[i].px
      for p = 1, frames[i].w * frames[i].h do
        local ka, kb, kc = a[p], b[p], c[p]
        if ka >= 0 and kc >= 0 and ka == kb and kc ~= ka then
          if lab_dist(kc, ka) <= thr then o[p] = ka end
        end
      end
    end
  end
  return out
end

-- ------------------------------------------------------------------ pipeline
M.DEFAULTS = {
  smear = true,        -- step 2 (remove_smears + remove_outside_ghosts)
  pal_thr = 0.045,     -- step 3 OKLab merge threshold (0 = off)
  lonely = true,       -- step 4 (+ final pass)
  speck = 4,           -- step 5 (groups smaller than this are dropped; 1 = off)
  outline = true,      -- step 6
  match = true,        -- step 7
  match_thr = 0.08,
  loop = true,
  target_palette = nil, -- list of keys: palette mode "map to sprite palette"
}

local function opt(o, k)
  if o and o[k] ~= nil then return o[k] end
  return M.DEFAULTS[k]
end

-- frames: list of frames (already hard-alpha'd by from_rgba). Returns a new list.
function M.clean_frames(frames, o)
  local fs = {}
  for i, f in ipairs(frames) do fs[i] = f end
  local speck = opt(o, "speck")
  if opt(o, "smear") then
    for i, f in ipairs(fs) do fs[i] = M.remove_outside_ghosts(M.remove_smears(f)) end
  end
  local pal_thr = opt(o, "pal_thr")
  local tp = opt(o, "target_palette")
  if pal_thr > 0 or tp then
    fs = M.unify_palette(fs, pal_thr, nil, nil, tp)
  end
  local lonely = opt(o, "lonely")
  for i, f in ipairs(fs) do
    if lonely then f = M.remove_lonely(f) end
    fs[i] = M.drop_specks(f, speck)
  end
  if opt(o, "outline") then
    for i, f in ipairs(fs) do fs[i] = M.thin_outline(f) end
  end
  if opt(o, "match") then
    fs = M.match_neighbours(fs, opt(o, "match_thr"), opt(o, "loop"))
  end
  for i, f in ipairs(fs) do
    if lonely then f = M.remove_lonely(f) end
    fs[i] = M.drop_specks(f, speck)
  end
  return fs
end

-- ------------------------------------------------------------------ 2x -> 1x downscale
-- Port of downscale2x.py. Each 2x2 cell becomes one colour:
--   alpha    >= 2 opaque px; a single-pixel cell stays only if it bridges 2 opaque groups
--   priority dark (lum <= dark_lum) px on the silhouette edge or in a small dark group
--            (<= feat px: eyes) win: most frequent, then darker, then smaller key
--   tone     else the OKLab mean of the opaque px snapped to the nearest palette colour
local RING = { { -1, 0 }, { -1, 1 }, { 0, 1 }, { 1, 1 }, { 1, 0 }, { 1, -1 }, { 0, -1 }, { -1, -1 } }
local EPS = 1e-9

function M.downscale2x(f, palette, dark_lum, feat)
  dark_lum = dark_lum or 0.24
  feat = feat or 6
  local W, H, src = f.w, f.h, f.px
  local W2, H2 = W // 2, H // 2
  local n = W * H
  local dark = {}
  for i = 1, n do
    local k = src[i]
    dark[i] = (k >= 0) and lum(k) <= dark_lum
  end
  local edge = edge_mask(src, W, H)
  local prio = {}
  for i = 1, n do prio[i] = edge[i] and dark[i] end
  for _, comp in ipairs(comps(dark, W, H, true)) do
    if #comp <= feat then
      for _, i in ipairs(comp) do prio[i] = true end
    end
  end
  local out = new_frame(W2, H2, -1)
  local o = out.px
  local single = {}
  local cell, pc = {}, {}
  for y = 0, H2 - 1 do
    for x = 0, W2 - 1 do
      local i0 = (2 * y) * W + 2 * x + 1
      cell[1], cell[2], cell[3], cell[4] = src[i0], src[i0 + 1], src[i0 + W], src[i0 + W + 1]
      pc[1], pc[2], pc[3], pc[4] = prio[i0], prio[i0 + 1], prio[i0 + W], prio[i0 + W + 1]
      local ks = {}
      for j = 1, 4 do
        if cell[j] >= 0 then ks[#ks + 1] = cell[j] end
      end
      local oi = y * W2 + x + 1
      if #ks == 1 then single[#single + 1] = { y, x, ks[1] } end
      if #ks >= 2 then
        local cnt, any = {}, false
        for j = 1, 4 do
          if pc[j] then
            cnt[cell[j]] = (cnt[cell[j]] or 0) + 1
            any = true
          end
        end
        if any then
          local best, bc, bl = nil, -1, 0
          for c, m in pairs(cnt) do
            local l = oklab(c)
            if m > bc or (m == bc and (l < bl or (l == bl and c < best))) then
              best, bc, bl = c, m, l
            end
          end
          o[oi] = best
        else
          local same = true
          for j = 2, #ks do
            if ks[j] ~= ks[1] then same = false; break end
          end
          if same then
            o[oi] = ks[1]
          else
            local mL, ma, mb = 0.0, 0.0, 0.0
            local ccnt = {}
            for _, c in ipairs(ks) do
              local l, a, b = oklab(c)
              mL = mL + l; ma = ma + a; mb = mb + b
              ccnt[c] = (ccnt[c] or 0) + 1
            end
            local cn = #ks
            mL = mL / cn; ma = ma / cn; mb = mb / cn
            -- nearest palette colour; near-ties go to the colour more frequent in the cell,
            -- then the darker one (keeps Lua == Python despite last-bit float differences)
            local best, bd, bcnt, bl = nil, math.huge, 0, 0
            for _, p in ipairs(palette) do
              local l, a, b = oklab(p)
              local dL, da, db = l - mL, a - ma, b - mb
              local d = sqrt(dL * dL + da * da + db * db)
              local pc_ = ccnt[p] or 0
              if best == nil or d < bd - EPS then
                bd, best, bcnt, bl = d, p, pc_, l
              elseif d <= bd + EPS and (pc_ > bcnt or (pc_ == bcnt and l < bl)) then
                if d < bd then bd = d end
                best, bcnt, bl = p, pc_, l
              end
            end
            o[oi] = best
          end
        end
      end
    end
  end
  local add = {}
  for _, s in ipairs(single) do
    local y, x = s[1], s[2]
    local ring = {}
    for r = 1, 8 do
      local ny, nx = y + RING[r][1], x + RING[r][2]
      ring[r] = ny >= 0 and ny < H2 and nx >= 0 and nx < W2 and o[ny * W2 + nx + 1] >= 0
    end
    local groups = 0
    for r = 1, 8 do
      local prev = r == 1 and ring[8] or ring[r - 1]
      if ring[r] and not prev then groups = groups + 1 end
    end
    if groups >= 2 then add[#add + 1] = s end
  end
  for _, s in ipairs(add) do o[s[1] * W2 + s[2] + 1] = s[3] end
  return out
end

-- palette of all opaque colours in the frames (sorted keys)
function M.frames_palette(frames)
  local set, pal = {}, {}
  for _, f in ipairs(frames) do
    local px = f.px
    for i = 1, f.w * f.h do
      local k = px[i]
      if k >= 0 and not set[k] then set[k] = true; pal[#pal + 1] = k end
    end
  end
  table.sort(pal)
  return pal
end

-- 2x frames -> cleaned 1x frames (pre-clean at 2x, shared palette, downscale, full cleanup)
function M.downscale_frames(frames, o)
  local fs = {}
  for i, f in ipairs(frames) do fs[i] = f end
  if opt(o, "smear") then
    for i, f in ipairs(fs) do fs[i] = M.remove_outside_ghosts(M.remove_smears(f)) end
  end
  local pal
  local pal_thr, tp = opt(o, "pal_thr"), opt(o, "target_palette")
  if pal_thr > 0 or tp then
    local _assign
    fs, _assign, pal = M.unify_palette(fs, pal_thr, nil, nil, tp)
  else
    pal = M.frames_palette(fs)
  end
  if #pal == 0 then pal = { 0 } end
  if opt(o, "method") == "mode" then
    for i, f in ipairs(fs) do fs[i] = M.mode_downscale2x(f) end
  else
    for i, f in ipairs(fs) do fs[i] = M.downscale2x(f, pal, nil, opt(o, "feat")) end
  end
  return M.clean_frames(fs, o)
end

M.DEFAULTS.feat = 6
M.DEFAULTS.method = "tone" -- 2x -> 1x: "tone" (downscale2x) or "mode" (plain 2x2 mode)

-- ------------------------------------------------------------------ input helpers
-- most common opaque colour on the borders of all frames (nil when the borders are transparent)
function M.border_colour(frames)
  local cnt, best, bc = {}, nil, 0
  local function add(k)
    if k >= 0 then
      local c = (cnt[k] or 0) + 1
      cnt[k] = c
      if c > bc or (c == bc and k < best) then best, bc = k, c end
    end
  end
  for _, f in ipairs(frames) do
    local w, h, px = f.w, f.h, f.px
    for x = 0, w - 1 do
      add(px[x + 1])
      if h > 1 then add(px[(h - 1) * w + x + 1]) end
    end
    for y = 1, h - 2 do
      add(px[y * w + 1])
      if w > 1 then add(px[y * w + w]) end
    end
  end
  return best
end

local function close_to(k, bg, tol)
  if k < 0 then return false end
  return abs(((k >> 16) & 255) - ((bg >> 16) & 255)) <= tol
     and abs(((k >> 8) & 255) - ((bg >> 8) & 255)) <= tol
     and abs((k & 255) - (bg & 255)) <= tol
end
M.close_to = close_to

-- background removal: pixels within `tol` (per RGB channel, 0..255) of `bg` become transparent.
-- contiguous = true: only the region flood-filled (4-neighbour) from the frame border, so
-- same-coloured pixels inside the sprite (white eyes on a white background) survive.
function M.remove_background(frames, bg, tol, contiguous)
  local out = {}
  tol = tol or 0
  for fi, f in ipairs(frames) do
    local g = copy_frame(f)
    if bg ~= nil then
      local w, h, px = f.w, f.h, g.px
      if contiguous == false then
        for i = 1, w * h do
          if close_to(px[i], bg, tol) then px[i] = -1 end
        end
      else
        local seen, st, sp = {}, {}, 0
        local function push(i)
          if not seen[i] and close_to(f.px[i], bg, tol) then
            seen[i] = true
            sp = sp + 1; st[sp] = i
          end
        end
        for x = 0, w - 1 do push(x + 1); push((h - 1) * w + x + 1) end
        for y = 0, h - 1 do push(y * w + 1); push(y * w + w) end
        while sp > 0 do
          local i = st[sp]; st[sp] = nil; sp = sp - 1
          px[i] = -1
          local y, x = (i - 1) // w, (i - 1) % w
          if y > 0 then push(i - w) end
          if y < h - 1 then push(i + w) end
          if x > 0 then push(i - 1) end
          if x < w - 1 then push(i + 1) end
        end
      end
    end
    out[fi] = g
  end
  return out
end

-- crop a w x h region at (x0, y0) of frame f (outside = transparent)
local function crop(f, x0, y0, w, h)
  local g = new_frame(w, h, -1)
  for y = 0, h - 1 do
    local sy = y0 + y
    if sy >= 0 and sy < f.h then
      for x = 0, w - 1 do
        local sx = x0 + x
        if sx >= 0 and sx < f.w then g.px[y * w + x + 1] = f.px[sy * f.w + sx + 1] end
      end
    end
  end
  return g
end
M.crop = crop

-- fixed grid: cols x rows cells, row-major order
function M.split_grid(f, cols, rows)
  cols = math.max(1, cols); rows = math.max(1, rows)
  local cw, ch = f.w // cols, f.h // rows
  local out = {}
  for r = 0, rows - 1 do
    for c = 0, cols - 1 do out[#out + 1] = crop(f, c * cw, r * ch, cw, ch) end
  end
  return out
end

-- opaque pixels that match (each channel within 24) the pixel one pitch to the left
local function pitch_similarity(f, P)
  local w, h, px = f.w, f.h, f.px
  local s = 0
  for y = 0, h - 1 do
    local row = y * w
    for x = P, w - 1 do
      local k, q = px[row + x + 1], px[row + x - P + 1]
      if k >= 0 and q >= 0 and abs(((k >> 16) & 255) - ((q >> 16) & 255)) <= 24
          and abs(((k >> 8) & 255) - ((q >> 8) & 255)) <= 24 and abs((k & 255) - (q & 255)) <= 24 then
        s = s + 1
      end
    end
  end
  return s
end

-- split a one-row sheet on fully transparent columns (= fakepixel.split_columns in Python).
-- Tries the largest frame count first; a pitch P (>= widest group) and a cell origin o <= 0 are
-- valid when every group sits in one cell [o + i*P, o + (i+1)*P) and every cell holds a group
-- (a frame may contain gaps of its own). Among valid pitches the one where neighbouring frames
-- overlap best (animation frames look alike) wins, ties -> smaller pitch; o is the valid origin
-- closest to centring the sheet. Otherwise groups are cropped and centred (narrow groups merged).
-- Returns frames, info, pitch, origins (x of each frame in the sheet).
function M.split_columns(f)
  local w, h, px = f.w, f.h, f.px
  local used = {}
  for x = 0, w - 1 do
    local u = false
    for y = 0, h - 1 do
      if px[y * w + x + 1] >= 0 then u = true; break end
    end
    used[x] = u
  end
  local groups, x = {}, 0
  while x < w do
    if used[x] then
      local s = x
      while x < w and used[x] do x = x + 1 end
      groups[#groups + 1] = { s, x - 1 }
    else
      x = x + 1
    end
  end
  local n = #groups
  if n == 0 then return {}, "empty sheet", 0, {} end
  if n == 1 then return { copy_frame(f) }, "1 frame (no empty column gap)", w, { 0 } end
  local maxgw = 0
  for _, g in ipairs(groups) do maxgw = math.max(maxgw, g[2] - g[1] + 1) end
  for cells = n, 2, -1 do
    local best_sim, best_P, best_o = nil, nil, nil
    for P = maxgw, w // (cells - 1) do
      if cells * P >= w then
        local oc = -((cells * P - w) // 2)
        local found = nil
        for d = 0, P - 1 do
          local opts = (d == 0) and { oc } or { oc + d, oc - d }
          for _, o in ipairs(opts) do
            if found == nil and o <= 0 and o > -P then
              local filled, nf, ok = {}, 0, true
              for _, g in ipairs(groups) do
                local c1, c2 = (g[1] - o) // P, (g[2] - o) // P
                if c1 ~= c2 or c1 >= cells then ok = false; break end
                if not filled[c1] then filled[c1] = true; nf = nf + 1 end
              end
              if ok and nf == cells then found = o end
            end
          end
          if found ~= nil then break end
        end
        if found ~= nil then
          local sim = pitch_similarity(f, P)
          if best_sim == nil or sim > best_sim then best_sim, best_P, best_o = sim, P, found end
        end
      end
    end
    if best_sim ~= nil then
      local out, org = {}, {}
      for c = 0, cells - 1 do
        org[#org + 1] = best_o + c * best_P
        out[#out + 1] = crop(f, best_o + c * best_P, 0, best_P, h)
      end
      return out, string.format("%d frames, pitch %dpx", cells, best_P), best_P, org
    end
  end
  -- uneven: fold narrow groups (< 1/4 of the widest) into the nearer neighbour, then centre
  -- every group in the widest group's width
  local mw = 0
  for _, g in ipairs(groups) do mw = math.max(mw, g[2] - g[1] + 1) end
  local merged = {}
  for _, g in ipairs(groups) do merged[#merged + 1] = { g[1], g[2] } end
  local changed = true
  while changed and #merged > 1 do
    changed = false
    for i, g in ipairs(merged) do
      if (g[2] - g[1] + 1) * 4 < mw then
        local left = merged[i - 1]
        local right = merged[i + 1]
        local gl = left and (g[1] - left[2]) or math.huge
        local gr = right and (right[1] - g[2]) or math.huge
        if gl <= gr then left[2] = g[2] else right[1] = g[1] end
        table.remove(merged, i)
        changed = true
        break
      end
    end
  end
  mw = 0
  for _, g in ipairs(merged) do mw = math.max(mw, g[2] - g[1] + 1) end
  local out, org = {}, {}
  for _, g in ipairs(merged) do
    local gw = g[2] - g[1] + 1
    org[#org + 1] = g[1] - (mw - gw) // 2
    out[#out + 1] = crop(f, org[#org], 0, mw, h)
  end
  return out, string.format("%d frames, uneven groups centred in %dpx", #out, mw), 0, org
end

-- plain 2x2 mode (downscale variant): >= 2 opaque, most frequent colour, ties smaller key
function M.mode_downscale2x(f)
  local W, H, src = f.w, f.h, f.px
  local W2, H2 = W // 2, H // 2
  local out = new_frame(W2, H2, -1)
  for y = 0, H2 - 1 do
    for x = 0, W2 - 1 do
      local i0 = (2 * y) * W + 2 * x + 1
      local cnt, n = {}, 0
      for _, i in ipairs{ i0, i0 + 1, i0 + W, i0 + W + 1 } do
        local k = src[i]
        if k >= 0 then cnt[k] = (cnt[k] or 0) + 1; n = n + 1 end
      end
      if n >= 2 then
        local best, bc = nil, -1
        for k, c in pairs(cnt) do
          if c > bc or (c == bc and k < best) then best, bc = k, c end
        end
        out.px[y * W2 + x + 1] = best
      end
    end
  end
  return out
end

return M
