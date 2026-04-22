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


def extract_from_name(filename):
    m = PATTERN_IMG.match(filename)
    if m:
        return (*m.groups()[:6], m.group(7).lower())

    m = PATTERN_SCREEN.match(filename)
    if m:
        return (*m.groups()[:6], m.group(7).lower())

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


def extract_date(filepath):
    name_data = extract_from_name(filepath.name)
    if name_data:
        y, mo, d, h, mi, s, ext = name_data
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s)), ext, "name"

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
            prefix = dir_path.name
        elif choice == "2":
            prefix = input("Escribe el prefijo: ").strip()
            if not prefix:
                print("El prefijo no puede estar vacío.")
                continue
        else:
            print("Opción inválida.")
            continue

        # Normalizar
        prefix = prefix.strip().replace(" ", "_")
        prefix = re.sub(r'[^a-zA-Z0-9_]', '_', prefix)
        return prefix


def ask_include_batch(non_matching_files):
    if not non_matching_files:
        return []

    count = len(non_matching_files)
    print(f"\nSe encontraron {count} archivo(s) sin patrón:")
    for f in non_matching_files[:5]:
        print(f"  - {f.name}")
    if count > 5:
        print(f"  ... y {count - 5} más.")

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

    args = parser.parse_args()

    dir_path = Path(args.directory).resolve()

    if not dir_path.is_dir():
        print("Directorio inválido")
        return

    # Prefijo
    if args.interactive:
        prefix = ask_prefix(dir_path)
    elif args.use_dirname:
        prefix = dir_path.name
    elif args.prefix:
        prefix = args.prefix
    else:
        print("Debes definir un prefijo")
        return

    prefix = prefix.strip().replace(" ", "_")
    prefix = re.sub(r'[^a-zA-Z0-9_]', '_', prefix)

    # Archivos (excluir script actual)
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
        dt, ext, source = extract_date(f)
        file_data.append((f, dt, ext, source))

    # Orden estable
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

        # Colisión consistente
        while new_path.exists() and new_path != f:
            counter[key] += 1
            num = counter[key]
            new_name = f"{prefix}_{fecha}_{num}.{ext}"
            new_path = dir_path / new_name

        changes.append((f.name, new_name, source))

    # Preview
    print(f"\nPrefijo: {prefix}")
    print(f"Total: {len(changes)} archivos\n")

    if len(changes) > 10:
        show_all = input("¿Mostrar todos los cambios? (y/n): ").lower() == "y"
    else:
        show_all = True

    if show_all:
        for orig, new, src in changes:
            print(f"{orig} -> {new}   [{src}]")
    else:
        for orig, new, src in changes[:5]:
            print(f"{orig} -> {new}   [{src}]")
        print(f"... y {len(changes) - 5} más")

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
