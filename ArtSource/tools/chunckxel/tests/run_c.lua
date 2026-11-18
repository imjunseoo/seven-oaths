-- Headless option C run (fake pixels / candidates) for the parity test.
-- aseprite.exe -b --script-param in=<image> --script-param mode=fake|clean|down2x
--   [--script-param n=<frames in sheet, clean/down2x>] [--script-param cands=8]
--   [--script-param cell_x=4.47 --script-param cell_y=5.0]   (manual cell size, fake)
--   --script-param out=<dir> --script-param tag=<name> --script-param ext=<chunckxel dir>
--   --script run_c.lua
-- Writes <out>/lua_<tag>_c<i>.png (candidate frames side by side) and <out>/lua_<tag>_scores.txt
local P = app.params
local core = dofile(app.fs.joinPath(P.ext, "chunckxel_core.lua"))
local fake = dofile(app.fs.joinPath(P.ext, "chunckxel_fake.lua"))(core)
local mode = P.mode or "fake"
local ncand = tonumber(P.cands or "8")

local img = Image{ fromFile = P["in"] }
assert(img and img.colorMode == ColorMode.RGB, "need an RGB(A) image: " .. tostring(P["in"]))
local bytes = img.bytes
if img.rowStride ~= img.width * 4 then
  local rows = {}
  for y = 0, img.height - 1 do rows[#rows + 1] = bytes:sub(y * img.rowStride + 1, y * img.rowStride + img.width * 4) end
  bytes = table.concat(rows)
end
local src = core.from_rgba(bytes, img.width, img.height, 128)

local function save_sheet(frames, path)
  if #frames == 0 then
    local e = Image(1, 1, ColorMode.RGB); e:saveAs(path); return
  end
  local fw, fh = frames[1].w, frames[1].h
  local W = 0
  for _, f in ipairs(frames) do W = W + f.w end
  local sheet = core.new_frame(W, fh, -1)
  local ox = 0
  for _, f in ipairs(frames) do
    for y = 0, math.min(fh, f.h) - 1 do
      for x = 0, f.w - 1 do sheet.px[y * W + ox + x + 1] = f.px[y * f.w + x + 1] end
    end
    ox = ox + f.w
  end
  local o = Image(W, fh, ColorMode.RGB)
  o.bytes = core.to_rgba(sheet)
  o:saveAs(path)
end

local t0 = os.clock()
local cands
if mode == "fake" then
  local base = {}
  if P.cell_x then base.cell_x = tonumber(P.cell_x); base.cell_y = tonumber(P.cell_y) end
  cands = fake.run_candidates(src, base, "fake", ncand)
else
  local n = tonumber(P.n)
  local fw = src.w // n
  local frames = {}
  for i = 0, n - 1 do frames[#frames + 1] = core.crop(src, i * fw, 0, fw, src.h) end
  cands = fake.run_candidates(frames, {}, mode, ncand)
end
local lines = {}
for i, c in ipairs(cands) do
  save_sheet(c.frames, app.fs.joinPath(P.out, string.format("lua_%s_c%d.png", P.tag, i)))
  local p = c.parts
  lines[#lines + 1] = string.format("%d|%s|%.9f|%.9f|%.9f|%.9f|%.9f|%.9f|%.9f|%d|%.6f|%.6f|%s", i, c.name, c.score,
    p.fidelity, p.grid, p.outline, p.lonely, p.colours, p.flicker, p.n_colours, c.size_x or 0, c.size_y or 0, c.info or "")
end
local f = io.open(app.fs.joinPath(P.out, string.format("lua_%s_scores.txt", P.tag)), "w")
f:write(table.concat(lines, "\n") .. "\n")
f:close()
print(string.format("%s %s: %d candidates in %.2fs", P.tag, mode, #cands, os.clock() - t0))
