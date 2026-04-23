# Rename Media Script

Script en Python para renombrar archivos multimedia (fotos, capturas, etc.) usando la mejor fecha disponible:

1. Fecha en el nombre del archivo (`IMG_`, `Screenshot_`)
2. Metadatos EXIF (si es imagen)
3. Fecha de modificación del sistema (fallback)

## Caracteristicas

- Detecta automaticamente fechas desde multiples fuentes
- Prioridad inteligente: nombre → EXIF → sistema
- Usa el nombre de la carpeta o un prefijo personalizado
- Evita colisiones con numeracion automatica
- Orden cronologico real
- Vista previa antes de aplicar cambios
- Modo interactivo o uso por flags
- Manejo opcional de archivos sin patron
- Funciona incluso sin EXIF (Pillow opcional)

## Requisitos

Python 3.8+

Opcional (para leer metadatos EXIF):

```bash
pip install pillow
```

## Uso

### Modo interactivo (recomendado)

```bash
python3 script.py --interactive
```

Te permitira:

- Elegir prefijo
- Decidir que hacer con archivos sin patron
- Ver preview antes de aplicar cambios

### Usar nombre de carpeta

```bash
python3 script.py --use-dirname
```

### Prefijo personalizado

```bash
python3 script.py --prefix vacaciones
```

### Simulacion (sin cambios reales)

```bash
python3 script.py --interactive --dry-run
```

## Formato de salida

```
<prefijo>_YYYY-MM-DD_HH-MM-SS_<n>.<ext>
```

Ejemplo:

```
viaje_2026-04-21_22-04-40_1.jpg
viaje_2026-04-21_22-04-40_2.jpg
```

## Origen de fechas

Durante el preview se indica de donde se obtuvo la fecha:

- `[name]` → desde el nombre del archivo
- `[exif]` → desde metadatos de la imagen
- `[mtime]` → desde fecha del sistema

## Notas importantes

- Los archivos se procesan en orden cronologico
- Si varios archivos tienen la misma fecha, se numeran automaticamente
- Archivos sin extension reciben `.dat` por defecto
- El script evita renombrarse a si mismo

## Casos de uso ideales

- Organizar fotos de celular (`IMG_*`)
- Ordenar capturas (`Screenshot_*`)
- Limpiar carpetas de descargas
- Unificar nombres antes de archivar o documentar
