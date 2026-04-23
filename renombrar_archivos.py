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
    # 1. Custom pattern
    dt = extract_from_custom_pattern(filepath.name, pattern, date_format)
    if dt:
        ext = filepath.suffix[1:].lower() or "dat"
        return dt, ext, "custom"

    # 2. Nombre
    name_data = extract_from_name(filepath.name)
    if name_data:
        y, mo, d, h, mi, s, ext, src = name_data
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s)), ext, src

    # 3. EXIF
    exif_dt = extract_exif_date(filepath)
    if exif_dt:
        ext = filepath.suffix[1:].lower() or "dat"
        return exif_dt, ext, "exif"

    # 4. mtime
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
                print("El prefijo no puede estar vacío.")
                continue
            return normalize_prefix(prefix)

        print("Opción inválida.")


def ask_include_batch(non_matching_files):
    if not non_matching_files:
        return []

    print(f"\nSe encontraron {len(non_matching_files)} archivo(s) sin patrón:")

    while True:
        print("\nOpciones:")
        print("  [t] Incluir TODOS")
        print("  [n] No incluir ninguno")
        print("  [i] Elegir uno por uno")

        choice = input("Opción (t/n/i): ").strip().lower()

        if choice == 't':
            return non_matching_files
        elif choice == 'n':
            return []
        elif choice == 'i':
            selected = []
            for f in non_matching_files:
                if input(f"¿Incluir '{f.name}'? (y/n): ").lower() == 'y':
                    selected.append(f)
            return selected

        print("Opción inválida.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--use-dirname", action="store_true")
    parser.add_argument("--prefix", type=str)
    parser.add_argument("--directory", type=str, default=".")
    parser.add_argument("--dry-run", action="store_true")

    # NUEVO
    parser.add_argument("--pattern", type=str,
                        help="Regex para extraer fecha personalizada")
    parser.add_argument("--date-format", choices=["DMY", "YMD", "MDY"],
                        help="Formato de fecha del patrón")

    args = parser.parse_args()

    dir_path = Path(args.directory).resolve()

    if not dir_path.is_dir():
        print("Directorio inválido")
        return

    # Prefijo
    if args.interactive:
        prefix = ask_prefix(dir_path)
    elif args.use_dirname:
        prefix = normalize_prefix(dir_path.name)
    elif args.prefix:
        prefix = normalize_prefix(args.prefix)
    else:
        print("Debes definir un prefijo")
        return

    script_name = Path(sys.argv[0]).name

    all_files = [
        f for f in dir_path.iterdir()
        if f.is_file() and f.name != script_name
    ]

    matching = []
    non_matching = []

    for f in all_files:
        if extract_from_name(f.name):
            matching.append(f)
        else:
            non_matching.append(f)

    selected_files = matching + ask_include_batch(non_matching)

    if not selected_files:
        print("Nada que procesar")
        return

    file_data = []
    for f in selected_files:
        dt, ext, source = extract_date(f, args.pattern, args.date_format)
        file_data.append((f, dt, ext, source))

    file_data.sort(key=lambda x: (x[1], x[0].name))

    counter = defaultdict(int)
    changes = []

    for f, dt, ext, source in file_data:
        fecha = format_date(dt)
        key = (prefix, fecha)

        counter[key] += 1
        num = counter[key]

        new_name = f"{prefix}_{fecha}_{num}.{ext}"
        new_path = dir_path / new_name

        while new_path.exists() and new_path != f:
            counter[key] += 1
            num = counter[key]
            new_name = f"{prefix}_{fecha}_{num}.{ext}"
            new_path = dir_path / new_name

        changes.append((f.name, new_name, source))

    print(f"\nPrefijo: {prefix}")
    print(f"Total: {len(changes)} archivos\n")

    for orig, new, src in changes[:5]:
        print(f"{orig} -> {new}   [{src}]")

    if len(changes) > 5:
        print(f"... y {len(changes)-5} más")

    if args.dry_run:
        print("\nModo simulación")
        return

    if input("\n¿Aplicar cambios? (y/n): ").lower() != 'y':
        print("Cancelado")
        return

    print("\nRenombrando...")
    for orig, new, _ in changes:
        try:
            (dir_path / orig).rename(dir_path / new)
            print(f"{orig} -> {new}")
        except Exception as e:
            print(f"Error: {orig}: {e}")

    print("Listo.")


if __name__ == "__main__":
    main()
