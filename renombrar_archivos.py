#!/usr/bin/env python3

import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Pillow opcional
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Aviso: Pillow no está instalado. Se omitirá EXIF (pip install pillow).")

# Patrones
PATTERN_IMG = re.compile(
    r'^IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\d*\.(jpg|jpeg|png|JPG|JPEG|PNG)$'
)

PATTERN_SCREEN = re.compile(
    r'^Screenshot_(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})\.(png|PNG)$'
)

PATTERN_WA = re.compile(
    r'^IMG-(\d{4})(\d{2})(\d{2})-WA\d+.*\.(jpg|jpeg|png|JPG|JPEG|PNG)$'
)


def normalize_prefix(prefix):
    prefix = prefix.strip().replace(" ", "_")
    return re.sub(r'[^\w\-]', '_', prefix, flags=re.UNICODE)


def extract_from_name(filename):
    m = PATTERN_IMG.match(filename)
    if m:
        return (*m.groups()[:6], m.group(7).lower(), "name")

    m = PATTERN_SCREEN.match(filename)
    if m:
        return (*m.groups()[:6], m.group(7).lower(), "name")

    m = PATTERN_WA.match(filename)
    if m:
        y, mo, d, ext = m.groups()
        return (y, mo, d, "00", "00", "00", ext.lower(), "wa")

    return None


def extract_from_custom_pattern(filename, pattern, date_format):
    if not pattern:
        return None

    m = re.search(pattern, filename)
    if not m:
        return None

    parts = m.groups()

    try:
        if date_format == "DMY":
            d, mo, y = parts
        elif date_format == "YMD":
            y, mo, d = parts
        elif date_format == "MDY":
            mo, d, y = parts
        else:
            return None

        return datetime(int(y), int(mo), int(d), 0, 0, 0)
    except Exception:
        return None


def extract_exif_date(filepath):
    if not PILLOW_AVAILABLE:
        return None

    try:
        with Image.open(filepath) as img:
            exif = img.getexif()
            if not exif:
                return None

            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "DateTimeOriginal":
                    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None

    return None


def extract_fallback_date(filepath):
    return datetime.fromtimestamp(filepath.stat().st_mtime)


def extract_date(filepath, pattern=None, date_format=None):
    dt = extract_from_custom_pattern(filepath.name, pattern, date_format)
    if dt:
        ext = filepath.suffix[1:].lower() or "dat"
        return dt, ext, "custom"

    name_data = extract_from_name(filepath.name)
    if name_data:
        y, mo, d, h, mi, s, ext, src = name_data
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s)), ext, src

    exif_dt = extract_exif_date(filepath)
    if exif_dt:
        ext = filepath.suffix[1:].lower() or "dat"
        return exif_dt, ext, "exif"

    ext = filepath.suffix[1:].lower() or "dat"
    return extract_fallback_date(filepath), ext, "mtime"


def format_date(dt):
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


def ask_prefix(dir_path):
    while True:
        print("\n¿Cómo quieres nombrar los archivos?\n")
        print("1) Usar nombre de la carpeta")
        print("2) Escribir un nombre personalizado")

        choice = input("Elige una opción (1/2): ").strip()

        if choice == "1":
            return normalize_prefix(dir_path.name)
        elif choice == "2":
            prefix = input("Escribe el prefijo: ").strip()
            if not prefix:
                print("No puede estar vacío")
                continue
            return normalize_prefix(prefix)

        print("Opción inválida")


def build_pattern(prefix, date_format, location):
    if date_format == "DMY":
        date_regex = r"(\d{2})-(\d{2})-(\d{4})"
    elif date_format == "YMD":
        date_regex = r"(\d{4})-(\d{2})-(\d{2})"
    elif date_format == "MDY":
        date_regex = r"(\d{2})-(\d{2})-(\d{4})"
    else:
        return None

    if not prefix:
        return date_regex

    if location == 'after':
        # permite separadores entre medio
        return rf"{re.escape(prefix)}.*?{date_regex}"
    else:
        return rf"{date_regex}"


def ask_custom_pattern():
    use = input("\n¿Los archivos tienen un patrón específico? (y/n): ").lower()
    if use != 'y':
        return None, None

    prefix = input("Prefijo esperado (ej: kelly) o vacío: ").strip()

    print("\nFormato de fecha:")
    print("1) DD-MM-YYYY")
    print("2) YYYY-MM-DD")
    print("3) MM-DD-YYYY")

    fmt = input("Elige: ").strip()
    fmt_map = {"1": "DMY", "2": "YMD", "3": "MDY"}
    date_format = fmt_map.get(fmt)

    if not date_format:
        return None, None

    print("\n¿Dónde está la fecha?")
    print("1) Después del prefijo")
    print("2) En cualquier parte")

    loc = input("Elige: ").strip()
    location = 'after' if loc == '1' else 'anywhere'

    pattern = build_pattern(prefix, date_format, location)

    print(f"\nPatrón generado: {pattern}")
    return pattern, date_format


def ask_include_batch(files):
    if not files:
        return []

    print(f"\n{len(files)} archivos sin patrón detectado")

    choice = input("[t] todos / [n] ninguno / [i] individual: ").lower()

    if choice == 't':
        return files
    if choice == 'n':
        return []

    selected = []
    for f in files:
        if input(f"Incluir {f.name}? (y/n): ").lower() == 'y':
            selected.append(f)
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--prefix")
    parser.add_argument("--use-dirname", action="store_true")
    parser.add_argument("--directory", default=".")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pattern")
    parser.add_argument("--date-format")

    args = parser.parse_args()

    dir_path = Path(args.directory).resolve()

    if not dir_path.is_dir():
        print("Directorio inválido")
        return

    if args.interactive:
        prefix = ask_prefix(dir_path)
    elif args.use_dirname:
        prefix = normalize_prefix(dir_path.name)
    elif args.prefix:
        prefix = normalize_prefix(args.prefix)
    else:
        print("Define prefijo")
        return

    pattern = args.pattern
    date_format = args.date_format

    if args.interactive and not pattern:
        pattern, date_format = ask_custom_pattern()

    script_name = Path(sys.argv[0]).name

    files = [f for f in dir_path.iterdir() if f.is_file() and f.name != script_name]

    matching = [f for f in files if extract_from_name(f.name)]
    non_matching = [f for f in files if not extract_from_name(f.name)]

    selected = matching + ask_include_batch(non_matching)

    data = [(f, *extract_date(f, pattern, date_format)) for f in selected]
    data.sort(key=lambda x: (x[1], x[0].name))

    counter = defaultdict(int)
    changes = []

    for f, dt, ext, src in data:
        key = (prefix, format_date(dt))
        counter[key] += 1
        num = counter[key]

        new_name = f"{prefix}_{key[1]}_{num}.{ext}"
        changes.append((f, new_name, src))

    print("\nPreview:")
    for f, new, src in changes[:5]:
        print(f"{f.name} -> {new} [{src}]")

    if args.dry_run:
        return

    if input("\nAplicar cambios? (y/n): ") != 'y':
        return

    for f, new, _ in changes:
        f.rename(dir_path / new)

    print("Listo")


if __name__ == "__main__":
    main()
