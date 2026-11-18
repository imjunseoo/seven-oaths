-- Headless: run the Chunckxel core on a horizontal sprite sheet and save the result.
-- aseprite.exe -b --script-param in=<sheet.png> --script-param n=<frames>
--              --script-param out=<out.png> [--script-param mode=clean|down2x]
--              --script-param core=<path to chunckxel_core.lua> --script run_clean_sheet.lua
local P = app.params
local core = dofile(P.core)
local n = tonumber(P.n)
local mode = P.mode or "clean"

local function load_frames(path, count)
  local img = Image{ fromFile = path }
  assert(img, "cannot load " .. path)
  assert(img.colorMode == ColorMode.RGB, "sheet must be RGBA")
  local W, H = img.width, img.height
  local sheet = core.from_rgba(img.bytes, W, H, 128)
  local fw = W // count
  local frames = {}
  for i = 0, count - 1 do
    local f = core.new_frame(fw, H, -1)
    for y = 0, H - 1 do
      for x = 0, fw - 1 do
        f.px[y * fw + x + 1] = sheet.px[y * W + i * fw + x + 1]
      end
    end
    frames[#frames + 1] = f
  end
  return frames
end

local function save_sheet(frames, path)
  local fw, fh = frames[1].w, frames[1].h
  local sheet = core.new_frame(fw * #frames, fh, -1)
  local W = fw * #frames
  for i, f in ipairs(frames) do
    for y = 0, fh - 1 do
      for x = 0, fw - 1 do
        sheet.px[y * W + (i - 1) * fw + x + 1] = f.px[y * fw + x + 1]
      end
    end
  end
  local img = Image(W, fh, ColorMode.RGB)
  img.bytes = core.to_rgba(sheet)
  img:saveAs(path)
end

local t0 = os.clock()
local frames = load_frames(P["in"], n)
local out
if mode == "down2x" then
  out = core.downscale_frames(frames, {})
else
  out = core.clean_frames(frames, {})
end
save_sheet(out, P.out)
print(string.format("%s: %d frames %dx%d -> %dx%d in %.2fs", mode, #frames, frames[1].w, frames[1].h,
  out[1].w, out[1].h, os.clock() - t0))
