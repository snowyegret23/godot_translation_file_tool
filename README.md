# Godot Translation file Tool

For English instructions, see [README_en.md](README_en.md).

## 기초 준비사항

* `python` 설치 (3.8 이상 권장)
* `pip install smaz-py3 dotenv`
* **중요 (PCK 모드 사용 시)**: [GodotPckTool](https://github.com/hhyyrylainen/GodotPckTool/releases)에서 `godotpcktool.exe`를 다운로드하여 이 폴더(또는 `Path` 경로)에 넣어주세요.
* [Release](https://github.com/snowyegret23/godot_translation_file_tool/releases)에서 `godot_translation_file_tool.exe`를 다운로드하여 편하게 사용하실 수 있습니다.

## 사용 방법

`Godot Translation file Tool`은 두 가지 모드(Export, Import)를 지원하며, 원본 `.pck`가 있는 경우와 `.translation` 파일만 있는 경우 모두 동작합니다.

### 1. Export (번역 파일 추출 및 CSV 변환)

**A. PCK 파일이 있는 경우 (자동 추출)**
게임의 `.pck` 파일에서 `.translation` 파일을 추출하고 CSV로 변환합니다.
```bash
python godot_translation_file_tool.py --pck "C:\Path\To\UntilThen.pck" --export text.en.translation
```

**B. 단일 파일 모드 (이미 추출된 파일)**
이미 가지고 있는 `.translation` 파일을 CSV로 변환합니다.
```bash
python godot_translation_file_tool.py --export text.en.translation
```
* 위 명령어 실행 시, `text.en.translation.csv`가 생성됩니다.

### 2. Import (번역 CSV 적용)

**A. PCK 파일이 있는 경우 (원본 추출 후 적용)**
번역된 CSV 파일을 적용하여 `.translation` 파일을 생성(패치)합니다. 원본 파일은 PCK에서 추출하여 사용합니다.
```bash
python godot_translation_file_tool.py --pck "C:\Path\To\UntilThen.pck" --import text.en.translation.csv --locale ko
```

**B. 단일 파일 모드 (로컬 파일 패치)**
현재 폴더에 있는 `.translation` 파일에 CSV 내용을 덮어씌웁니다.
```bash
python godot_translation_file_tool.py --import text.en.translation.csv --locale ko
```
* 주의: `text.en.translation` 파일이 현재 폴더에 존재해야 합니다.
* `--import`에 지정된 CSV 파일명(예: `text.en.translation.csv`)에서 대상 파일명(`text.en.translation`)을 자동으로 유추합니다.
