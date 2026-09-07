# VFWatchfaceFactory

<img width="1402" height="932" alt="Screenshot 2026-09-06 192944" src="https://github.com/user-attachments/assets/e10128c6-5243-4b3d-8eff-1ffba03284bb" />

A watch face editor for VeryFit smartwatches — a successor /
inspired replacement for ArnCep's ATSDialFactory.

Only the **IDW13** device (240×284) is enabled right now. The device table
(`app/device_config.py`) is a plain dict, so adding another model later is a
matter of adding one more entry — nothing else in the app hard-codes IDW13. More
models will be added later.

## Running

```bash
pip install -r requirements.txt
python3 main.py
```

## iwf.json / font.json compatibility

`Project.to_pretty_iwf_json()` / `to_compact_font_json()` reproduce the
reference format's exact field names, field order, and formatting
conventions (4-space indented iwf.json, compact single-line font.json) so
files this app writes are drop-in compatible with the sample format you
provided, and files you open were produced (or could have been produced) by
this editor.

Font/asset folders follow the same convention as the reference tooling: a
custom widget's `"font"` value is a **folder name only** (e.g. `"g141"`),
created inside the project directory, containing glyph images named by
value (`0.png` … `9.png`, `10.png` for punctuation, `11`/`12` for weather
units, or `en_wed.png` / `en_sept.png` / `en_am.png` for the week/month/apm
"letter" widgets). The `font.json` `"format"` field tells the editor whether
to expect `.png` or `.bmp` — nothing is hard-coded to PNG.

## `iwf_packer/` is intentionally separate

Per the spec, the actual `.iwf` binary packer (`pack_iwf.py` + its
`png2raw.py` RAW image converter) is **not** part of the application and is
**not imported by it**. It's included here unmodified, in its own folder,
as a standalone command-line tool you run against a finished project
directory:

```bash
python3 iwf_packer/pack_iwf.py /path/to/project_dir /path/to/output.iwf
```

It reads the same `iwf.json` / `font.json` / asset-folder layout this editor
produces, so a project built here needs no restructuring before packing.

## Known scope limits (match the reference editor's own scope)

- `multimeter`, `gradient`, `shortcut`, `sleep`, `bluetooth` custom types are not available yet.
