-- Chunckxel option C: fake-pixel grid detection + resample (C1) and candidates + score (C2).
-- Lua port of ArtSource/tools/fakepixel.py and ArtSource/tools/candidates.py; parity with Python
-- is pixel-exact (scores to 1e-6). Pure Lua 5.4. Usage: local fake = dofile(path)(core)
return function(core)
  local M = {}
  local floor, abs, sqrt, fmod = math.floor, math.abs, math.sqrt, math.fmod

  local NOISE, PEAK_DIV, WIN, INLIER, COL_TOL = 30, 50, 2.0, 1.5, 20
  local P_MIN, P_MAX = 3.0, 64.0

  M.DEFAULTS = {
    fake = "auto", cell = nil, sampler = "dominant", snap = true, split = true,
    bg = "auto", bgkey = 0xFFFFFF, bgtol = 16, bgcont = true,
    pal_thr = 0.045, speck = 4, smear = false, lonely = true, outline = true,
    match = true, match_thr = 0.08, loop = true,
  }

  local function merged(base, extra)
    local o = {}
    for k, v in pairs(base) do o[k] = v end
    if extra then for k, v in pairs(extra) do o[k] = v end end
    return o
  end
  M.merged = merged

  -- ---------------------------------------------------------------- detection
  -- f: core frame (keys, -1 transparent). axis "x": column boundaries, "y": rows.
  -- E[0..L] (L = W or H), E[x] = edge between x-1 and x; E[0] = E[L] = 0
  function M.edge_profile(f, axis)
    local w, h, px = f.w, f.h, f.px
    local L = (axis == "x") and w or h
    local E = {}
    for i = 0, L do E[i] = 0 end
    local function chan(k)
      if k < 0 then return 0, 0, 0, 0 end
      return (k >> 16) & 255, (k >> 8) & 255, k & 255, 255
    end
    -- per-key channel cache is not needed: unpack inline
    for y = 0, h - 1 do
      for x = 0, w - 1 do
        local ny, nx
        if axis == "x" then ny, nx = y, x + 1 else ny, nx = y + 1, x end
        if ny < h and nx < w then
          local a, b = px[y * w + x + 1], px[ny * w + nx + 1]
          if a ~= b then
            local r1, g1, b1, a1 = chan(a)
            local r2, g2, b2, a2 = chan(b)
            local d = abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2) + abs(a1 - a2) - NOISE
            if d > 0 then
              local idx = (axis == "x") and (x + 1) or (y + 1)
              E[idx] = E[idx] + d
            end
          end
        end
      end
    end
    return E, L
  end

  function M.find_peaks(E, L)
    local mx = 0
    for i = 0, L do if E[i] > mx then mx = E[i] end end
    local out = {}
    for x = 1, L - 1 do
      local v = E[x]
      if v > 0 and v >= E[x - 1] and v > E[x + 1] and v * PEAK_DIV >= mx then
        out[#out + 1] = { x, v }
      end
    end
    return out, mx
  end

  -- best 2 px phase window of the peaks folded by p: weight in window, window start
  function M.fold(peaks, p)
    local rs = {}
    for i, pk in ipairs(peaks) do rs[i] = { fmod(pk[1] + 0.0, p), i, pk[2] } end
    table.sort(rs, function(a, b)
      if a[1] ~= b[1] then return a[1] < b[1] end
      return a[2] < b[2]
    end)
    local n = #rs
    local r2, w2 = {}, {}
    for i = 1, n do r2[i] = rs[i][1]; w2[i] = rs[i][3] end
    for i = 1, n do r2[n + i] = rs[i][1] + p; w2[n + i] = rs[i][3] end
    local j, s, best, r0 = 1, 0, -1, 0.0
    for i = 1, n do
      local lim = r2[i] + WIN
      while j < i + n and r2[j] <= lim do
        s = s + w2[j]
        j = j + 1
      end
      if s > best then best, r0 = s, r2[i] end
      s = s - w2[i]
    end
    return best, r0
  end

  local function total_weight(peaks)
    local t = 0
    for _, pk in ipairs(peaks) do t = t + pk[2] end
    return t
  end

  function M.search_period(peaks, length)
    local tot = total_weight(peaks)
    local pmax = math.min(P_MAX, length / 3.0)
    local bs, bp, br = nil, nil, nil
    local i = 0
    while true do
      local p = (300 + i) / 100
      if p > pmax then break end
      local s, r0 = M.fold(peaks, p)
      local score = s / tot - WIN / p
      if bs == nil or score > bs then bs, bp, br = score, p, r0 end
      i = i + 1
    end
    return bs, bp, br
  end

  function M.fit_line(peaks, a, b, fix_size)
    for _ = 1, 2 do
      local Sw, Sk, Sx, Skk, Skx = 0, 0, 0, 0, 0
      for _, pk in ipairs(peaks) do
        local x, w = pk[1], pk[2]
        local k = floor((x - a) / b + 0.5)
        if abs(x - (a + k * b)) <= INLIER then
          Sw = Sw + w; Sk = Sk + w * k; Sx = Sx + w * x; Skk = Skk + w * k * k; Skx = Skx + w * k * x
        end
      end
      if Sw == 0 then break end
      local fSw, fSk, fSx, fSkk, fSkx = Sw + 0.0, Sk + 0.0, Sx + 0.0, Skk + 0.0, Skx + 0.0
      if not fix_size then
        local den = fSw * fSkk - fSk * fSk
        if den ~= 0.0 then
          local nb = (fSw * fSkx - fSk * fSx) / den
          if nb >= P_MIN * 0.5 then b = nb end
        end
      end
      a = (fSx - b * fSk) / fSw
    end
    return a, b
  end

  function M.comb_fit(peaks, bounds)
    local tot = total_weight(peaks)
    if tot == 0 then return 0.0 end
    local s, j = 0, 1
    for _, pk in ipairs(peaks) do
      local x, w = pk[1], pk[2]
      while j + 1 <= #bounds and bounds[j + 1] <= x do j = j + 1 end
      local d = abs(x - bounds[j])
      if j + 1 <= #bounds then d = math.min(d, abs(bounds[j + 1] - x)) end
      if d <= 1 then s = s + w end
    end
    return s / tot
  end

  function M.detect_axis(f, axis, cell, snap)
    local E, L = M.edge_profile(f, axis)
    local peaks, mx = M.find_peaks(E, L)
    if #peaks < 2 then
      local p = cell and (cell + 0.0) or (L + 0.0)
      local step = math.max(1, floor(p))
      local bounds = {}
      for x = 0, L - 1, step do bounds[#bounds + 1] = x end
      bounds[#bounds + 1] = L
      return { size = p, phase = 0.0, bounds = bounds, fit = 0.0, score = 0.0, peaks = {} }
    end
    local score, p, a, b
    if cell then
      p = cell + 0.0
      local s, r0 = M.fold(peaks, p)
      score = s / total_weight(peaks) - WIN / p
      a, b = M.fit_line(peaks, r0 + WIN / 2, p, true)
    else
      local r0
      score, p, r0 = M.search_period(peaks, L)
      a, b = M.fit_line(peaks, r0 + WIN / 2, p, false)
    end
    local kmin = floor(-a / b) - 1
    local kmax = floor((L - a) / b) + 2
    local set = { [0] = true, [L] = true }
    for k = kmin, kmax do
      local B = a + b * k
      local x0 = floor(B + 0.5)
      local pick = x0
      if snap then
        local bestx = nil
        for xx = x0 - 1, x0 + 1 do
          if xx >= 1 and xx <= L - 1 then
            if bestx == nil or E[xx] > E[bestx] or (E[xx] == E[bestx] and abs(xx - B) < abs(bestx - B)) then
              bestx = xx
            end
          end
        end
        if bestx and E[bestx] * PEAK_DIV >= mx and E[bestx] > 0 then pick = bestx end
      end
      if pick > 0 and pick < L then set[pick] = true end
    end
    local bounds = {}
    for v in pairs(set) do bounds[#bounds + 1] = v end
    table.sort(bounds)
    return { size = b, phase = a, bounds = bounds, fit = M.comb_fit(peaks, bounds), score = score, peaks = peaks }
  end

  function M.detect_grid(src, o)
    local cx, cy = nil, nil
    if o.fake == "manual" and o.cell then cx, cy = o.cell, o.cell end
    if o.cell_x then cx, cy = o.cell_x, o.cell_y end
    local snap = o.snap ~= false
    local gx = M.detect_axis(src, "x", cx, snap)
    local gy = M.detect_axis(src, "y", cy, snap)
    return {
      xb = gx.bounds, yb = gy.bounds, size_x = gx.size, size_y = gy.size, phase_x = gx.phase, phase_y = gy.phase,
      fit = (gx.fit + gy.fit) / 2, score_x = gx.score, score_y = gy.score, peaks_x = gx.peaks, peaks_y = gy.peaks,
    }
  end

  -- ---------------------------------------------------------------- resample
  local function bin_of(k)
    return ((k >> 20) << 8) | (((k >> 12) & 15) << 4) | ((k >> 4) & 15)
  end

  function M.cell_colour(src, x0, x1, y0, y1, sampler)
    local w, px = src.w, src.px
    if sampler == "centre" then
      return px[((y0 + y1 - 1) // 2) * w + (x0 + x1 - 1) // 2 + 1]
    end
    local mx = (x1 - x0 >= 3) and 1 or 0
    local my = (y1 - y0 >= 3) and 1 or 0
    local pix, nt = {}, 0
    for y = y0 + my, y1 - my - 1 do
      local row = y * w
      for x = x0 + mx, x1 - mx - 1 do
        local k = px[row + x + 1]
        if k < 0 then nt = nt + 1 else pix[#pix + 1] = k end
      end
    end
    if nt > #pix or #pix == 0 then return -1 end
    local bins, order = {}, {}
    for _, k in ipairs(pix) do
      local bi = bin_of(k)
      if bins[bi] == nil then bins[bi] = 0; order[#order + 1] = bi end
      bins[bi] = bins[bi] + 1
    end
    table.sort(order)
    local best, bd = nil, -1
    for _, bi in ipairs(order) do
      local r, g, b = bi >> 8, (bi >> 4) & 15, bi & 15
      local d = 0
      for dr = -1, 1 do
        for dg = -1, 1 do
          for db = -1, 1 do
            local rr, gg, b2 = r + dr, g + dg, b + db
            if rr >= 0 and rr < 16 and gg >= 0 and gg < 16 and b2 >= 0 and b2 < 16 then
              d = d + (bins[(rr << 8) | (gg << 4) | b2] or 0)
            end
          end
        end
      end
      if d > bd then best, bd = bi, d end
    end
    local sr, sg, sb, n = 0, 0, 0, 0
    for _, k in ipairs(pix) do
      if bin_of(k) == best then
        sr = sr + ((k >> 16) & 255); sg = sg + ((k >> 8) & 255); sb = sb + (k & 255); n = n + 1
      end
    end
    local rr, gg, b2 = (sr + n // 2) // n, (sg + n // 2) // n, (sb + n // 2) // n
    sr, sg, sb, n = 0, 0, 0, 0
    for _, k in ipairs(pix) do
      local r, g, b = (k >> 16) & 255, (k >> 8) & 255, k & 255
      if abs(r - rr) <= COL_TOL and abs(g - gg) <= COL_TOL and abs(b - b2) <= COL_TOL then
        sr = sr + r; sg = sg + g; sb = sb + b; n = n + 1
      end
    end
    return (((sr + n // 2) // n) << 16) | (((sg + n // 2) // n) << 8) | ((sb + n // 2) // n)
  end

  function M.resample(src, xb, yb, sampler)
    local W, H = #xb - 1, #yb - 1
    local f = core.new_frame(W, H, -1)
    for j = 1, H do
      for i = 1, W do
        f.px[(j - 1) * W + i] = M.cell_colour(src, xb[i], xb[i + 1], yb[j], yb[j + 1], sampler)
      end
    end
    return f
  end

  function M.bbox(f)
    local w, h, px = f.w, f.h, f.px
    local x0, y0, x1, y1 = w, h, -1, -1
    for y = 0, h - 1 do
      for x = 0, w - 1 do
        if px[y * w + x + 1] >= 0 then
          if x < x0 then x0 = x end
          if x > x1 then x1 = x end
          if y < y0 then y0 = y end
          if y > y1 then y1 = y end
        end
      end
    end
    if x1 < 0 then return nil end
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1
  end

  -- full C1 pipeline on one image (a sheet is one image). src: core frame (hard alpha).
  -- cache (optional table): reuses detect_grid between runs with the same cell options.
  function M.fake_to_pixels(src, opts, cache)
    local o = merged(M.DEFAULTS, opts)
    local gkey = tostring(o.fake) .. "|" .. tostring(o.cell) .. "|" .. tostring(o.cell_x) .. "|" ..
      tostring(o.cell_y) .. "|" .. tostring(o.snap)
    local grid = cache and cache[gkey]
    if not grid then
      grid = M.detect_grid(src, o)
      if cache then cache[gkey] = grid end
    end
    local low = M.resample(src, grid.xb, grid.yb, o.sampler)
    local bg
    if o.bg == "pick" then bg = o.bgkey
    elseif o.bg == "none" then bg = nil
    else bg = core.border_colour({ low }) end
    low = core.remove_background({ low }, bg, o.bgtol, o.bgcont)[1]
    local x0, y0, w, h = M.bbox(low)
    if not x0 then
      return { frames = {}, grid = grid, lowres = low, crop = { 0, 0 }, pitch = 0, origins = {}, info = "empty", bg = bg }
    end
    low = core.crop(low, x0, y0, w, h)
    local frames, info, pitch, origins
    if o.split then
      frames, info, pitch, origins = core.split_columns(low)
    else
      frames, info, pitch, origins = { low }, "1 frame", w, { 0 }
    end
    local out = core.clean_frames(frames, o)
    return { frames = out, grid = grid, lowres = low, crop = { x0, y0 }, pitch = pitch, origins = origins,
      info = info, bg = bg }
  end

  -- ---------------------------------------------------------------- C2: candidates + score
  local W_FID, W_GRID, W_OUT, W_LON, W_COL, W_FLI = 0.35, 0.20, 0.15, 0.10, 0.10, 0.10
  local COL_TARGET, FID_SCALE = 32, 0.15

  M.VARIANTS = {
    fake = {
      { "base", {} }, { "pal 0.030", { pal_thr = 0.030 } }, { "pal 0.060", { pal_thr = 0.060 } },
      { "outline flip", { outline = "flip" } }, { "smear flip", { smear = "flip" } },
      { "cell -1", { cell_delta = -1 } }, { "cell +1", { cell_delta = 1 } },
      { "centre sample", { sampler = "centre" } },
      { "pal 0.030 + smear flip", { pal_thr = 0.030, smear = "flip" } },
      { "pal 0.030 + outline flip", { pal_thr = 0.030, outline = "flip" } },
      { "pal 0.060 + smear flip", { pal_thr = 0.060, smear = "flip" } },
      { "centre + pal 0.030", { sampler = "centre", pal_thr = 0.030 } },
    },
    down2x = {
      { "base", {} }, { "pal 0.030", { pal_thr = 0.030 } }, { "pal 0.060", { pal_thr = 0.060 } },
      { "outline flip", { outline = "flip" } }, { "2x2 mode", { method = "mode" } },
      { "smear flip", { smear = "flip" } }, { "pal 0.030 + outline flip", { pal_thr = 0.030, outline = "flip" } },
      { "2x2 mode + pal 0.030", { method = "mode", pal_thr = 0.030 } },
      { "pal 0.060 + outline flip", { pal_thr = 0.060, outline = "flip" } },
      { "match flip", { match = "flip" } }, { "2x2 mode + outline flip", { method = "mode", outline = "flip" } },
      { "speck 2", { speck = 2 } },
    },
    clean = {
      { "base", {} }, { "pal 0.030", { pal_thr = 0.030 } }, { "pal 0.060", { pal_thr = 0.060 } },
      { "outline flip", { outline = "flip" } }, { "smear flip", { smear = "flip" } },
      { "pal 0.030 + outline flip", { pal_thr = 0.030, outline = "flip" } },
      { "match flip", { match = "flip" } }, { "speck 2", { speck = 2 } },
      { "pal 0.060 + outline flip", { pal_thr = 0.060, outline = "flip" } },
      { "pal 0.030 + smear flip", { pal_thr = 0.030, smear = "flip" } },
      { "lonely flip", { lonely = "flip" } }, { "match thr 0.040", { match_thr = 0.040 } },
    },
  }

  function M.variant_opts(base, change, grid)
    local o = merged(base)
    for k, v in pairs(change) do
      if v == "flip" then
        o[k] = not base[k]
      elseif k == "cell_delta" then
        o.cell_x = grid.size_x + v
        o.cell_y = grid.size_y + v
      else
        o[k] = v
      end
    end
    return o
  end

  local function err_of(s, r)
    if s < 0 or r < 0 then return 1.0 end
    if s == r then return 0.0 end
    local d = core.lab_dist(s, r)
    return math.min(1.0, d / FID_SCALE)
  end

  local function fid_of(list)
    -- list: flat array s1, r1, s2, r2, ...
    local n = #list // 2
    if n == 0 then return 0.0 end
    local err = 0.0
    for i = 1, #list, 2 do err = err + err_of(list[i], list[i + 1]) end
    return 1.0 - err / n
  end

  function M.frame_parts(frames)
    local lonely, opaque, double, dark_edge = 0, 0, 0, 0
    local cols, ncol = {}, 0
    local flick = {}
    local prev = nil
    for _, f in ipairs(frames) do
      local w, h, px = f.w, f.h, f.px
      local function at(y, x)
        if y >= 0 and y < h and x >= 0 and x < w then return px[y * w + x + 1] end
        return -1
      end
      local edge, dark = {}, {}
      for y = 0, h - 1 do
        for x = 0, w - 1 do
          local i = y * w + x + 1
          local k = px[i]
          edge[i], dark[i] = false, false
          if k >= 0 then
            opaque = opaque + 1
            if not cols[k] then cols[k] = true; ncol = ncol + 1 end
            local n0 = at(y - 1, x - 1)
            if n0 >= 0 and n0 ~= k and at(y - 1, x) == n0 and at(y - 1, x + 1) == n0 and at(y, x - 1) == n0
                and at(y, x + 1) == n0 and at(y + 1, x - 1) == n0 and at(y + 1, x) == n0 and at(y + 1, x + 1) == n0 then
              lonely = lonely + 1
            end
            edge[i] = y == 0 or y == h - 1 or x == 0 or x == w - 1 or px[i - w] < 0 or px[i + w] < 0
              or px[i - 1] < 0 or px[i + 1] < 0
            dark[i] = core.lum(k) <= 0.24
          end
        end
      end
      for y = 0, h - 1 do
        for x = 0, w - 1 do
          local i = y * w + x + 1
          if edge[i] and dark[i] then
            dark_edge = dark_edge + 1
            if (y > 0 and dark[i - w] and not edge[i - w]) or (y < h - 1 and dark[i + w] and not edge[i + w])
                or (x > 0 and dark[i - 1] and not edge[i - 1]) or (x < w - 1 and dark[i + 1] and not edge[i + 1]) then
              double = double + 1
            end
          end
        end
      end
      if prev and prev.w == w and prev.h == h then
        local ch, un = 0, 0
        for i = 1, w * h do
          local a, b = px[i], prev.px[i]
          if a >= 0 or b >= 0 then
            un = un + 1
            if a ~= b then ch = ch + 1 end
          end
        end
        flick[#flick + 1] = ch / math.max(1, un)
      end
      prev = f
    end
    local fl = 0.0
    for _, v in ipairs(flick) do fl = fl + v end
    if #flick > 0 then fl = fl / #flick else fl = 0.0 end
    return lonely, opaque, double, dark_edge, ncol, fl
  end

  function M.total_score(fid, grid_fit, frames)
    local lonely, opaque, double, dark_edge, n, fl = M.frame_parts(frames)
    local O = 1.0 - double / math.max(1, dark_edge)
    local Lo = math.max(0.0, 1.0 - 10.0 * lonely / math.max(1, opaque))
    local Co
    if n <= COL_TARGET then Co = 1.0 else Co = math.max(0.0, 1.0 - (n - COL_TARGET) / (3 * COL_TARGET)) end
    local Fl = 1.0 - fl
    local s = 100.0 * (W_FID * fid + W_GRID * grid_fit + W_OUT * O + W_LON * Lo + W_COL * Co + W_FLI * Fl)
    return s, { fidelity = fid, grid = grid_fit, outline = O, lonely = Lo, colours = Co, flicker = Fl, n_colours = n }
  end

  function M.fidelity_fake(src, res, bgtol)
    local g = res.grid
    local xb, yb = g.xb, g.yb
    local GW, GH = #xb - 1, #yb - 1
    local canvas = {}
    for i = 1, GW * GH do canvas[i] = -1 end
    local cx0, cy0 = res.crop[1], res.crop[2]
    for fi, f in ipairs(res.frames) do
      local ox = res.origins[fi]
      for y = 0, f.h - 1 do
        local gy = cy0 + y
        if gy >= 0 and gy < GH then
          for x = 0, f.w - 1 do
            local gx = cx0 + ox + x
            if gx >= 0 and gx < GW then
              local k = f.px[y * f.w + x + 1]
              if k >= 0 then canvas[gy * GW + gx + 1] = k end
            end
          end
        end
      end
    end
    local bg = res.bg
    local list = {}
    local sw, spx = src.w, src.px
    for j = 1, GH do
      local y0, y1 = yb[j], yb[j + 1]
      local my = (y1 - y0 >= 3) and 1 or 0
      for i = 1, GW do
        local x0, x1 = xb[i], xb[i + 1]
        local mx = (x1 - x0 >= 3) and 1 or 0
        local r = canvas[(j - 1) * GW + i]
        for y = y0 + my, y1 - my - 1, 2 do
          for x = x0 + mx, x1 - mx - 1, 2 do
            local s = spx[y * sw + x + 1]
            if s >= 0 and bg ~= nil and core.close_to(s, bg, bgtol) then s = -1 end
            if s >= 0 or r >= 0 then list[#list + 1] = s; list[#list + 1] = r end
          end
        end
      end
    end
    return fid_of(list)
  end

  -- 1x: each pixel vs the same source pixel. 2x: each output pixel vs the OKLab mean of the
  -- opaque pixels of its 2x2 source cell (opaque when >= 2 of 4)
  function M.fidelity_frames(src, out, scale)
    if scale == 1 then
      local list = {}
      for fi, f in ipairs(src) do
        local g = out[fi]
        for i = 1, f.w * f.h do
          local s, r = f.px[i], g.px[i]
          if s >= 0 or r >= 0 then list[#list + 1] = s; list[#list + 1] = r end
        end
      end
      return fid_of(list)
    end
    local err, n = 0.0, 0
    for fi, f in ipairs(src) do
      local g = out[fi]
      local w = f.w
      for y = 0, g.h - 1 do
        for x = 0, g.w - 1 do
          local i0 = 2 * y * w + 2 * x + 1
          local ks = {}
          for _, k in ipairs{ f.px[i0], f.px[i0 + 1], f.px[i0 + w], f.px[i0 + w + 1] } do
            if k >= 0 then ks[#ks + 1] = k end
          end
          local r = g.px[y * g.w + x + 1]
          if #ks < 2 then
            if r >= 0 then err = err + 1.0; n = n + 1 end
          else
            n = n + 1
            if r < 0 then
              err = err + 1.0
            else
              local mL, ma, mb = 0.0, 0.0, 0.0
              for _, k in ipairs(ks) do
                local L, A, B = core.oklab(k)
                mL = mL + L; ma = ma + A; mb = mb + B
              end
              local c = #ks
              mL = mL / c; ma = ma / c; mb = mb / c
              local L, A, B = core.oklab(r)
              local dL, da, db = L - mL, A - ma, B - mb
              err = err + math.min(1.0, sqrt(dL * dL + da * da + db * db) / FID_SCALE)
            end
          end
        end
      end
    end
    if n == 0 then return 0.0 end
    return 1.0 - err / n
  end

  M.CLEAN_DEFAULTS = {
    bg = "none", bgkey = 0xFFFFFF, bgtol = 16, bgcont = true, pal_thr = 0.045, speck = 4, smear = true,
    lonely = true, outline = true, match = true, match_thr = 0.08, loop = true, scale = 1, method = "tone",
  }

  -- 1x / 2x path: background then cleanup or downscale. Returns bg-removed source, result
  function M.run_frames(frames, o)
    local bg = nil
    if o.bg == "pick" then bg = o.bgkey elseif o.bg == "auto" then bg = core.border_colour(frames) end
    local src = frames
    if bg ~= nil then src = core.remove_background(frames, bg, o.bgtol or 16, o.bgcont ~= false) end
    local out
    if o.scale == 2 then out = core.downscale_frames(src, o) else out = core.clean_frames(src, o) end
    return src, out
  end

  -- source: core frame (mode "fake") or list of core frames ("clean" / "down2x").
  -- progress (optional): function(i, n, name) called before each candidate.
  function M.run_candidates(source, base_opts, mode, n, progress)
    local out = {}
    if mode == "fake" then
      local base = merged(M.DEFAULTS, base_opts)
      local cache = {}
      local grid0 = nil
      local manual = base.fake == "manual" or base.cell_x ~= nil
      -- a manual cell size is the user's choice: no cell +-1 variants then
      local list = {}
      for _, v in ipairs(M.VARIANTS.fake) do
        if not (manual and v[2].cell_delta) then list[#list + 1] = v end
      end
      for i = 1, math.min(n, #list) do
        local name, ch = list[i][1], list[i][2]
        if progress then progress(i, math.min(n, #list), name) end
        local o
        if grid0 == nil then o = base else o = M.variant_opts(base, ch, grid0) end
        local res = M.fake_to_pixels(source, o, cache)
        if grid0 == nil then grid0 = res.grid end
        local fid = (#res.frames > 0) and M.fidelity_fake(source, res, o.bgtol) or 0.0
        local s, parts = M.total_score(fid, res.grid.fit, res.frames)
        out[#out + 1] = { name = name, opts = o, frames = res.frames, score = s, parts = parts, info = res.info,
          size_x = res.grid.size_x, size_y = res.grid.size_y, res = res }
      end
      return out
    end
    local base = merged(M.CLEAN_DEFAULTS, base_opts)
    if mode == "down2x" then base.scale = 2 end
    local list = (base.scale == 2) and M.VARIANTS.down2x or M.VARIANTS.clean
    for i = 1, math.min(n, #list) do
      local name, ch = list[i][1], list[i][2]
      if progress then progress(i, math.min(n, #list), name) end
      local o = M.variant_opts(base, ch)
      local src, res = M.run_frames(source, o)
      local fid = M.fidelity_frames(src, res, o.scale)
      local s, parts = M.total_score(fid, 1.0, res)
      out[#out + 1] = { name = name, opts = o, frames = res, score = s, parts = parts, info = "" }
    end
    return out
  end

  return M
end
