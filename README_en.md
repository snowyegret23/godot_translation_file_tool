# Godot Translation file Tool

## Prerequisites

* Install `python` (3.8+ recommended)
* `pip install smaz-py3 dotenv`
* **Important (for PCK mode)**: Download `godotpcktool.exe` from [GodotPckTool](https://github.com/hhyyrylainen/GodotPckTool/releases) and place it in this folder (or add it to your `PATH`).
* You can download `godot_translation_file_tool.exe` from [Release](https://github.com/snowyegret23/godot_translation_file_tool/releases) for easier use.

## Usage

`Godot Translation file Tool` supports two modes (Export, Import) and works both with the original `.pck` file or with just the `.translation` file.

### 1. Export (Extract translation file and convert to CSV)

**A. With PCK file (Automated Extraction)**
Extracts the `.translation` file from the game's `.pck` file and converts it to CSV.
```bash
python godot_translation_file_tool.py --pck "C:\Path\To\UntilThen.pck" --export text.en.translation
```

**B. Single File Mode (File already extracted)**
Converts an existing local `.translation` file to CSV.
```bash
python godot_translation_file_tool.py --export text.en.translation
```
* Running this command generates `text.en.translation.csv`.

### 2. Import (Apply translation CSV)

**A. With PCK file (Extract source, Apply, and Repack)**
Applies the translated CSV to create (patch) the `.translation` file. The source file is automatically extracted from the PCK, patched, and **repacked (added back)** into the PCK.
```bash
python godot_translation_file_tool.py --pck "C:\Path\To\UntilThen.pck" --import text.en.translation.csv --locale ko
```

**B. Single File Mode (Patch local file)**
Overwrites the content of the `.translation` file in the current folder with the CSV content.
```bash
python godot_translation_file_tool.py --import text.en.translation.csv --locale ko
```
* Note: The `text.en.translation` file must exist in the current folder.
* The target filename (`text.en.translation`) is automatically inferred from the CSV filename specified in `--import` (e.g., `text.en.translation.csv`).
