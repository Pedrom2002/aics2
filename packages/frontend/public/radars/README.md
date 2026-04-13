# Radar minimaps

Drop 1024×1024 PNGs of each competitive map here, named by the map's
engine slug (lowercase):

- `de_mirage.png`
- `de_inferno.png`
- `de_dust2.png`
- `de_nuke.png`
- `de_anubis.png`
- `de_ancient.png`
- `de_vertigo.png`
- `de_overpass.png`
- `de_train.png`

They are served as `/radars/{map}.png` and drawn as the background of the
replay map canvas. When a file is missing, the canvas falls back to a
plain grid so the replay stays usable.

## License note

The PNGs currently committed were extracted from the official CS2
install (`game/csgo/pak01_dir.vpk` → `panorama/images/overheadmaps/*.vtex_c`)
using the [ValveResourceFormat CLI](https://github.com/ValveResourceFormat/ValveResourceFormat).
These are Valve assets: fine for internal/dev use, follow the Steam
Subscriber Agreement for anything commercial.

For a safer commercial license, swap in [SimpleRadar](https://readtldr.gg/simpleradar)
(CC BY 4.0). Download the CS2 classic pack, extract the `de_*_radar_*.png`
files, rename them to `de_<map>.png`, and replace the files here.
The `MapCanvas` component doesn't care which source as long as the
filename matches.
