# VFWatchfaceFactory

<img width="1402" height="932" alt="VFWatchfaceFactory" src="https://github.com/user-attachments/assets/e10128c6-5243-4b3d-8eff-1ffba03284bb" />

A watch face editor for VeryFit smartwatches, inspired by ArnCep's
ATSDialFactory.

VFWatchfaceFactory is intended for creating and editing `.iwf` watch face
projects using the same structure used by IDO/VeryFit watch faces.

## Supported devices

Currently supported:

| Device | Resolution |
|--------|------------|
| IDW13 | 240 × 284 |

Other devices are planned.

## Running

Install the dependencies:

```bash
pip install -r requirements.txt
```

Then start the editor:

```bash
python main.py
```

## Watch face projects

VFWatchfaceFactory works with projects containing an `iwf.json`, `font.json`,
background images, and the asset folders used by the watch face.

Custom widgets use image-based glyphs rather than rendering text directly.
For example, a time such as `10:08` can be assembled from:

```text
1.png
0.png
10.png
0.png
8.png
```

The `font` value in `iwf.json` refers to the asset folder in the project.
The format and bit depth of each font are described in `font.json`.

Both PNG and BMP assets are supported.

## IWF packer

The `iwf_packer` directory contains the `.iwf` packer and its image converter.

It is kept separate from the editor and can be run from the command line:

```bash
python iwf_packer/pack_iwf.py /path/to/project_dir /path/to/output.iwf
```

The packer uses the same project structure produced by VFWatchfaceFactory, so
there is no need to rearrange the project before packing.

## Current scope

Supported widget types are being added incrementally.

Some types from the reference format are not implemented yet, including:

- `multimeter`
- `gradient`
- `shortcut`
- `sleep`
- `bluetooth`

Animation widgets currently use their first frame for the editor preview.

## Status

VFWatchfaceFactory is still in development. More devices and widget types will
be added as the IWF format is documented further.
