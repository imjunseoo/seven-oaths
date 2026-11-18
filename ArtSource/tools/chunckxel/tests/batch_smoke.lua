-- Headless smoke test of the packaged extension (no UI in batch mode, so Dialog is mocked).
-- aseprite.exe -b --script-param ext=<extracted extension dir> --script-param sheet=<A sheet png>
--   --script-param ref_clean=<parity/lua_A_clean.png> --script-param ref_down=<parity/lua_A_down2x.png>
--   --script batch_smoke.lua
local P = app.params
local fails = 0
local function check(cond, msg)
  if cond then print("  ok   " .. msg) else print("  FAIL " .. msg); fails = fails + 1 end
end

-- 1. load like Aseprite does: run the script, then init(plugin)
local registered = {}
local plugin = { path = P.ext, preferences = {} }
function plugin:newCommand(t) registered[#registered + 1] = t end
dofile(app.fs.joinPath(P.ext, "chunckxel.lua"))
init(plugin)
local api = chunckxel_api
local core = api.core
print("[load]")
check(#registered == 1 and registered[1].id == "Chunckxel" and registered[1].group == "sprite_crop",
  "command registered: " .. tostring(registered[1] and registered[1].title))
check(type(core) == "table" and type(core.clean_frames) == "function", "core loaded from extension dir")

-- helpers
local function snapshot(spr)
  local s = {}
  for _, fr in ipairs(spr.frames) do
    local cel = spr.layers[1]:cel(fr.frameNumber)
    s[#s + 1] = cel and (cel.position.x .. "," .. cel.position.y .. ":" .. cel.image.width .. "x" ..
      cel.image.height .. ":" .. cel.image.bytes) or "nil"
  end
  return spr.width .. "x" .. spr.height .. "|" .. table.concat(s, "|")
end
local function sheet_bytes(spr)
  -- render frames side by side as a full-canvas frame list -> RGBA sheet bytes
  local fs = api.read_targets(spr, spr.layers[1], (function()
    local t = {}; for i = 1, #spr.frames do t[i] = i end; return t end)())
  local W = spr.width * #fs
  local sheet = core.new_frame(W, spr.height, -1)
  for i, f in ipairs(fs) do
    for y = 0, f.h - 1 do
      for x = 0, f.w - 1 do sheet.px[y * W + (i - 1) * f.w + x + 1] = f.px[y * f.w + x + 1] end
    end
  end
  return core.to_rgba(sheet)
end
local function ref_bytes(path)
  local img = Image{ fromFile = path }
  return core.to_rgba(core.from_rgba(img.bytes, img.width, img.height, 128))
end

-- 2. sheet split (empty columns + grid) into new sprites
print("[split]")
local sheet = app.open(P.sheet)
app.sprite = sheet
app.layer = sheet.layers[1]
app.frame = sheet.frames[1]
local o = api.options_from(api.default_data(), sheet)
local s1, info1 = api.split_sheet(sheet, sheet.layers[1], 1, o, "Empty columns", 1, 1)
check(s1 and #s1.frames == 10 and s1.width == 96 and s1.height == 96, "empty-column split: " .. tostring(info1))
local s2, info2 = api.split_sheet(sheet, sheet.layers[1], 1, o, "Grid", 10, 1)
check(s2 and #s2.frames == 10 and s2.width == 96, "grid split: " .. tostring(info2))

-- 3. Apply cleanup (all frames) == parity reference, then one undo restores everything
print("[apply 1x]")
local spr = s2
app.sprite = spr; app.layer = spr.layers[1]; app.frame = spr.frames[1]
local before = snapshot(spr)
local ok, msg = api.apply(spr, spr.layers[1], o)
check(ok, "apply: " .. tostring(msg))
check(sheet_bytes(spr) == ref_bytes(P.ref_clean), "applied frames == Lua parity sheet (== Python)")
app.undo()
check(snapshot(spr) == before, "single undo restores the sprite")

-- 4. Apply 2x -> 1x
print("[apply 2x->1x]")
local o2 = api.options_from(api.default_data(), spr)
o2.scale = 2
ok, msg = api.apply(spr, spr.layers[1], o2)
check(ok and spr.width == 48 and spr.height == 48, "downscale apply -> " .. spr.width .. "x" .. spr.height)
check(sheet_bytes(spr) == ref_bytes(P.ref_down), "downscaled frames == Lua parity sheet (== Python)")
app.undo()
check(snapshot(spr) == before and spr.width == 96, "single undo restores size and pixels")

-- 5. background removal: paint a solid background into a copy, remove it with auto + picked
print("[background]")
local fs = api.read_targets(spr, spr.layers[1], { 1 })
local f = fs[1]
local bgk = 0x00ff00
local g = core.copy_frame(f)
for i = 1, g.w * g.h do if g.px[i] < 0 then g.px[i] = bgk end end
check(core.border_colour({ g }) == bgk, "auto background colour detected")
local r = core.remove_background({ g }, bgk, 8, true)[1]
local same = true
for i = 1, f.w * f.h do if r.px[i] ~= f.px[i] then same = false; break end end
check(same, "background removed back to the original alpha")

-- 6. Indexed sprite round trip (palette mode + encode)
print("[indexed]")
local ix = Sprite(spr) -- duplicate
app.sprite = ix
app.command.ChangePixelFormat{ format = "indexed" }
app.layer = ix.layers[1]; app.frame = ix.frames[1]
ok, msg = api.apply(ix, ix.layers[1], api.options_from(api.default_data(), ix))
check(ok and ix.colorMode == ColorMode.INDEXED, "apply on indexed sprite: " .. tostring(msg))

-- 7. Dialog code path with a mock Dialog (real widgets need the GUI)
print("[dialog mock]")
local mock
Dialog = function(t)
  local d = { w = {}, data = {}, repaints = 0, title = t and t.title }
  local function add(kind)
    return function(self, a)
      a = a or {}
      if a.id then
        self.w[a.id] = { kind = kind, args = a }
        if kind == "combobox" then self.data[a.id] = a.option or a.options[1]
        elseif kind == "slider" then self.data[a.id] = a.value
        elseif kind == "check" then self.data[a.id] = a.selected or false
        elseif kind == "color" then self.data[a.id] = a.color
        elseif kind == "number" then self.data[a.id] = tonumber(a.text) or 0
        elseif kind == "label" then self.data[a.id] = a.text end
      end
      return self
    end
  end
  for _, k in ipairs{ "separator", "combobox", "slider", "check", "color", "number", "button", "canvas",
    "label", "newrow", "entry" } do d[k] = add(k) end
  function d:modify(a)
    local wd = self.w[a.id]
    assert(wd, "modify unknown id " .. tostring(a.id))
    for k, v in pairs(a) do wd.args[k] = v end
    if a.text and wd.kind == "label" then self.data[a.id] = a.text end
    if a.value and wd.kind == "slider" then self.data[a.id] = a.value end
    if a.option and wd.kind == "combobox" then self.data[a.id] = a.option end
    if a.selected ~= nil and wd.kind == "check" then self.data[a.id] = a.selected end
  end
  function d:repaint() self.repaints = self.repaints + 1 end
  function d:show() end
  function d:close() end
  mock = d
  return d
end
app.sprite = spr; app.layer = spr.layers[1]; app.frame = spr.frames[3]
api.open_dialog()
check(mock ~= nil and mock.w.canvas and mock.w.apply, "dialog built")
print("       info: " .. tostring(mock.data.info))
check(mock.data.info and mock.data.info:find("10 frame") ~= nil, "initial preview computed")
local drawn = 0
local gc = { width = 360, height = 200 }
function gc:fillRect() end
function gc:fillText() end
function gc:drawImage(img, src, dst) drawn = drawn + 1 end
function gc:strokeRect() end
mock.w.canvas.args.onpaint({ context = gc })
check(drawn == 2, "onpaint draws before + after (" .. drawn .. ")")
check(mock.data.pframe == 3 and mock.w.pframe.args.max == 10, "preview slider starts at the current frame (3 of 10)")
mock.data.scale = "2x -> 1x (tone)"; mock.w.scale.args.onchange()
check(mock.data.info:find("%-> 48x48") ~= nil, "downscale preview: " .. mock.data.info)
mock.data.bg = "Auto (border colour)"; mock.w.bg.args.onchange()
mock.data.palmode = "Map to sprite palette"; mock.w.palmode.args.onchange()
mock.data.target = "Current frame"; mock.w.target.args.onchange()
check(mock.data.info:find("^1 frame") ~= nil, "current-frame preview: " .. mock.data.info)
mock.w.apply.args.onclick()
check(spr.width == 48, "Apply button ran (sprite " .. spr.width .. "x" .. spr.height .. ")")
app.undo()
check(snapshot(spr) == before, "undo after dialog Apply")
mock.data.target = "All frames"; mock.data.scale = "1x"; mock.data.bg = "None"; mock.data.palmode = "Keep colours"
app.sprite = sheet; app.layer = sheet.layers[1]; app.frame = sheet.frames[1]
mock.w.dosplit.args.onclick()
check(app.sprite ~= spr and #app.sprite.frames == 10, "Split button made a new sprite")

-- 8. option C: fake pixels in the dialog (auto detect -> new sprite, candidates -> pick -> apply)
print("[fake pixels]")
local function sprite_sheet_bytes(s)
  local fs = api.read_targets(s, s.layers[1], (function()
    local t = {}; for i = 1, #s.frames do t[i] = i end; return t end)())
  local W = 0
  for _, f in ipairs(fs) do W = W + f.w end
  local sh = core.new_frame(W, s.height, -1)
  local ox = 0
  for _, f in ipairs(fs) do
    for y = 0, f.h - 1 do
      for x = 0, f.w - 1 do sh.px[y * W + ox + x + 1] = f.px[y * f.w + x + 1] end
    end
    ox = ox + f.w
  end
  return core.to_rgba(sh)
end
local jpg = app.open(app.fs.joinPath(P.c_in, "fake_sd_x7.3.jpg"))
app.sprite = jpg; app.layer = jpg.layers[1]; app.frame = jpg.frames[1]
api.open_dialog()
mock.data.fake = "Auto"; mock.w.fake.args.onchange()
check(mock.data.smear == false, "switching to fake pixels unticks smear removal")
print("       info: " .. tostring(mock.data.info))
check(mock.data.info:find("cell 7.30 x 7.30") ~= nil, "auto cell size detected")
mock.w.apply.args.onclick()
local ns = app.sprite
check(ns ~= jpg and ns.width == 60 and ns.height == 87 and #ns.frames == 1, "Apply -> new sprite " .. ns.width .. "x" .. ns.height)
check(sprite_sheet_bytes(ns) == ref_bytes(app.fs.joinPath(P.c_dir, "lua_sd_c1.png")), "new sprite == parity candidate 1 (base)")
app.sprite = jpg; app.layer = jpg.layers[1]; app.frame = jpg.frames[1]
mock.data.fake = "Auto"; mock.w.fake.args.onchange()
mock.data.ncand = 8
mock.w.gencand.args.onclick()
print("       " .. tostring(mock.data.candinfo))
check(mock.data.candinfo:find("^8 candidates") ~= nil, "8 candidates generated")
local cgc = { width = 360, height = 132 }
local thumbs = 0
function cgc:fillRect() end
function cgc:fillText() end
function cgc:strokeRect() end
function cgc:drawImage() thumbs = thumbs + 1 end
mock.w.cands.args.onpaint({ context = cgc })
check(thumbs == 8, "8 thumbnails drawn")
mock.w.cands.args.onmousedown({ x = 120, y = 30 }) -- candidate #2 (pal 0.030)
check(mock.data.candinfo:find("^#2 pal 0.030") ~= nil and mock.data.palthr == 30, "click picks #2: " .. mock.data.candinfo)
mock.w.apply.args.onclick()
check(app.sprite ~= jpg and sprite_sheet_bytes(app.sprite) == ref_bytes(app.fs.joinPath(P.c_dir, "lua_sd_c2.png")),
  "Apply of the picked candidate == parity candidate 2")
local sh = app.open(app.fs.joinPath(P.c_in, "fake_sdidle_sheet_x6.4.jpg"))
app.sprite = sh; app.layer = sh.layers[1]; app.frame = sh.frames[1]
mock.data.palthr = 45 -- the picked candidate #2 left the slider at 30 (as in the real dialog)
mock.data.fake = "Auto"; mock.w.fake.args.onchange()
mock.w.apply.args.onclick()
check(#app.sprite.frames == 4 and app.sprite.width == 72, "sheet -> " .. #app.sprite.frames .. " frames of " .. app.sprite.width .. "px")
check(sprite_sheet_bytes(app.sprite) == ref_bytes(app.fs.joinPath(P.c_dir, "lua_sheet_c1.png")), "sheet frames == parity candidate 1")

print(fails == 0 and "SMOKE OK" or ("SMOKE FAILED: " .. fails))
