"""Inventario local de auditoría PAA, de sólo lectura fuera de su carpeta de salida.

Ejecutar: python -m src.audit_paa_project
Las coincidencias son evidencia para revisión contextual, no reemplazos automáticos.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

import pandas as pd
import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/auditoria_integral_2026_10_24"
OLD = re.compile(
    r"\b(?:sin actividad|sin detecci[oó]n|(?:riesgo[ _]|nivel[ _]|actividad[ _])?"
    r"(?:muy[ _])?(?:baj[oa]s?|moderad[oa]s?|alt[oa]s?))\b", re.I
)
TEXT = {'.py', '.md', '.txt', '.json', '.jsonl', '.csv', '.html', '.sha256',
        '.toml', '.yml', '.yaml', '.ini', '.cfg', '.geojson'}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    inventory, hits, errors = [], [], []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or OUTPUT in path.parents or any(
            part in {'.git', '__pycache__', '.pytest_cache', '.ipynb_checkpoints'}
            for part in path.relative_to(ROOT).parts
        ):
            continue
        rel = str(path.relative_to(ROOT))
        item = {'ruta': rel, 'bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        try:
            suffix = path.suffix.lower()
            fragments = []
            if suffix == '.ipynb':
                nb = json.loads(path.read_text())
                codes = []
                embedded = 0
                for i, cell in enumerate(nb['cells']):
                    source = ''.join(cell['source'])
                    fragments.append((f'celda {i} fuente', source))
                    if cell['cell_type'] == 'code':
                        ast.parse(source)
                        codes.append(source.strip())
                    for j, out in enumerate(cell.get('outputs', [])):
                        if out.get('output_type') == 'error':
                            errors.append({'ruta': rel, 'error': f'salida de error en celda {i}'})
                        fragments.append((f'celda {i} salida {j}', ''.join(out.get('text', []))))
                        for mime, data in out.get('data', {}).items():
                            if mime.startswith('text/'):
                                fragments.append((f'celda {i} {mime}', ''.join(data)))
                            elif mime.startswith('image/'):
                                embedded += 1
                item.update(celdas=len(nb['cells']), imagenes_embebidas=embedded,
                            fuentes_duplicadas=[s[:120] for s, n in Counter(codes).items() if s and n > 1],
                            inspeccion='fuentes AST y salidas textuales; imágenes embebidas inventariadas')
            elif suffix == '.parquet':
                parquet = pq.ParquetFile(path)
                columns = [c for c in parquet.schema_arrow.names if any(
                    t in c.lower() for t in ('nivel', 'clase', 'target', 'riesgo'))]
                classes = {}
                if columns:
                    frame = pd.read_parquet(path, columns=columns)
                    classes = {c: {str(k): int(v) for k, v in frame[c].value_counts(dropna=False).items()}
                               for c in columns}
                item.update(filas=parquet.metadata.num_rows, columnas=parquet.schema_arrow.names,
                            etiquetas=classes, inspeccion='esquema, filas y columnas de clases completas')
            elif suffix == '.png':
                with Image.open(path) as im:
                    item.update(ancho=im.width, alto=im.height)
                    im.verify()
                item['inspeccion'] = 'integridad PNG; texto raster no leído por este inventario'
            elif suffix == '.zip':
                with ZipFile(path) as z:
                    item['miembros'] = z.namelist()
                    item['miembro_corrupto'] = z.testzip()
                item['inspeccion'] = 'directorio y CRC; contenido no auditado semánticamente'
            elif suffix in TEXT or path.name in {'.gitignore', 'requirements.txt'}:
                source = path.read_text()
                if suffix == '.py':
                    ast.parse(source)
                if suffix in {'.json', '.geojson'}:
                    json.loads(source)
                fragments.append(('texto', source))
                item['inspeccion'] = 'lectura completa; búsqueda contextual de nomenclatura'
            else:
                item['inspeccion'] = 'hash e inventario; contenido binario no interpretado'
            for location, source in fragments:
                for line, text in enumerate(source.splitlines(), 1):
                    matches = [m.group(0) for m in OLD.finditer(text)]
                    if matches:
                        hits.append({'ruta': rel, 'ubicacion': location, 'linea': line,
                                     'coincidencias': matches, 'texto': text[:1200]})
        except Exception as exc:
            item['inspeccion'] = 'error'
            errors.append({'ruta': rel, 'error': repr(exc)})
        inventory.append(item)
    result = {'archivos': inventory, 'errores': errors,
              'resumen': dict(Counter(p['inspeccion'] for p in inventory))}
    (OUTPUT / 'inventario.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    (OUTPUT / 'referencias_finales.json').write_text(json.dumps(hits, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'archivos': len(inventory), 'referencias_contextuales': len(hits),
                      'errores': errors, 'resumen': result['resumen']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
