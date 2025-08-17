# Version Para Lrc Palabra por Palabra
import re
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

import pygame
from rich.console import Console
from rich.text import Text

console = Console()

# Configuración de alineación del texto: "left", "center", "right"
TEXT_ALIGN = "center"

# Patrones: tiempos de línea [mm:ss.xx] y de palabra <mm:ss.xx>
LRC_LINE_TS_RE = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\]')     # [mm:ss.xx]
LRC_WORD_TS_RE = re.compile(r'<(\d+):(\d+(?:\.\d+)?)>')       # <mm:ss.xx>

def _to_seconds(m: str, s: str) -> float:
    return int(m) * 60 + float(s)

def parse_lrc(path: Path) -> List[Dict[str, Any]]:
    """
    Devuelve una lista de eventos (líneas) ordenados por tiempo.

    Estructura por elemento:
    - {
        "start": float,                   # timestamp de inicio de la línea
        "text": str,                      # texto de la línea sin marcas
        "inline": Optional[List[Tuple[float, str]]]  # lista de (ts, segmento) si hay marcas <...>
      }

    Comportamiento:
    - Soporta varias marcas [..] al inicio (duplicará la línea para cada marca).
    - Si hay marcas <..> dentro de la línea, se generan segmentos palabra a palabra
      sincronizados a esos tiempos. El primer segmento usa el tiempo de la primera [..].
    """
    lines: List[Dict[str, Any]] = []

    with path.open(encoding='utf-8') as f:
        for raw in f:
            raw = raw.rstrip("\n")
            if not raw.strip():
                continue

            # Todas las marcas de línea [..]
            line_times = LRC_LINE_TS_RE.findall(raw)
            if not line_times:
                # Sin timestamp de línea => ignoramos (metadatos u otros)
                continue

            # Texto tras la última ]
            # Nota: split deja tokens, tomamos la cola posterior
            text_after = LRC_LINE_TS_RE.split(raw)[-1]

            # Detectar marcas de palabra <..>
            word_matches = list(LRC_WORD_TS_RE.finditer(text_after))

            # Texto "plano" sin marcas <..> para el modo letra-a-letra
            plain_text = LRC_WORD_TS_RE.sub("", text_after).strip()

            if word_matches:
                # Hay marcas word-by-word. Construimos segmentos absolutos.
                # Recorremos el texto con un cursor y vamos leyendo los tramos entre marcas.
                segments: List[Tuple[float, str]] = []

                pos = 0
                # Primer tramo (entre inicio de la línea y el primer <..>)
                first_start = _to_seconds(*line_times[0])  # usamos la primera marca [..] como inicio
                first_seg = text_after[pos:word_matches[0].start()].strip()
                if first_seg:
                    segments.append((first_start, first_seg))
                pos = word_matches[0].end()

                # Tramos intermedios: (ts de <..>, texto hasta la próxima marca)
                for i in range(len(word_matches) - 1):
                    ts = _to_seconds(*word_matches[i].groups())
                    seg = text_after[pos:word_matches[i + 1].start()].strip()
                    if seg:
                        segments.append((ts, seg))
                    pos = word_matches[i + 1].end()

                # Tramo final: desde la última marca hasta el final
                last_ts = _to_seconds(*word_matches[-1].groups())
                tail = text_after[pos:].strip()
                if tail:
                    segments.append((last_ts, tail))

                # Ordenamos por tiempo (por seguridad)
                segments.sort(key=lambda t: t[0])

                # Si la línea tenía múltiples [..], duplicamos la línea para cada inicio adicional:
                # Aquí asumimos que los <..> son ABSOLUTOS (lo más común). Por eso no ajustamos segmentos.
                for m, s in line_times:
                    start_ts = _to_seconds(m, s)
                    # Ajuste opcional: si este start_ts es distinto al del primer segmento,
                    # y deseas tratar las marcas <..> como relativas a la línea, descomenta:
                    # delta = start_ts - first_start
                    # segs = [(ts + delta, seg) for ts, seg in segments]
                    # En esta implementación: consideramos <..> como absolutos => no ajustamos.
                    segs = segments
                    lines.append({
                        "start": start_ts,
                        "text": plain_text,  # texto total sin marcas (solo por referencia)
                        "inline": segs
                    })
            else:
                # Sin marcas <..>: cada [..] genera una línea clásica
                for m, s in line_times:
                    start_ts = _to_seconds(m, s)
                    lines.append({
                        "start": start_ts,
                        "text": plain_text,
                        "inline": None
                    })

    # Ordenamos por tiempo de inicio
    lines.sort(key=lambda d: d["start"])
    return lines

def _aligned_print(s: str, style: str):
    width = console.width
    ln = s
    if TEXT_ALIGN == "center":
        padding = max((width - len(ln)) // 2, 0)
        ln = " " * padding + ln
    elif TEXT_ALIGN == "right":
        padding = max(width - len(ln), 0)
        ln = " " * padding + ln
    console.print(Text(ln, style=style), end="\r", soft_wrap=False)

def pretty_print_line_letter_by_letter(line: str, duration: float, style: str):
    """Revelado horizontal letra por letra para líneas sin marcas <..>."""
    line = line or ""
    if len(line.strip()) > 0:
        delay_per_char = max(duration / max(len(line), 1), 0.02)
    else:
        delay_per_char = 0.02

    revealed = ""
    for ch in line:
        revealed += ch
        _aligned_print(revealed, style)
        time.sleep(delay_per_char)

    console.print("")  # salto de línea final

def print_line_word_by_word(segments: List[Tuple[float, str]], style: str, now_fn):
    """
    Muestra una línea que tiene segmentos (ts, palabra/fragmento) con tiempos absolutos.
    Se va construyendo la línea acumulada según el reloj del reproductor (now_fn()).
    """
    buffer = ""
    i = 0
    n = len(segments)

    while i < n:
        seg_ts, seg_text = segments[i]
        now = now_fn()
        wait = seg_ts - now
        if wait > 0:
            # Dormir poco para ser reactivo
            time.sleep(min(wait, 0.05))
            continue

        # Añadir el segmento al buffer, respetando espacios
        if not buffer:
            buffer = seg_text
        else:
            # Heurística: si el segmento empieza con puntuación, no agregar espacio previo
            if seg_text and seg_text[0] in ",.;:!?)]}":
                buffer += seg_text
            else:
                buffer += " " + seg_text

        _aligned_print(buffer, style)
        i += 1

    console.print("")  # salto de línea final

def play_and_show(audio_file: Path, lrc_file: Path):
    # Inicializar pygame mixer
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(str(audio_file))
    except Exception as e:
        console.print(f"[bold red]Error cargando audio:[/bold red] {e}")
        return

    lines = parse_lrc(lrc_file)
    if not lines:
        console.print("[bold yellow]No se encontraron líneas reproducibles en el LRC.[/bold yellow]")
        return

    colors = ["bold red", "bold yellow", "bold green", "bold cyan", "bold magenta"]

    # Reproducir
    pygame.mixer.music.play()
    start = time.perf_counter()

    def now() -> float:
        return time.perf_counter() - start

    for idx, entry in enumerate(lines):
        style = colors[idx % len(colors)]
        ts = entry["start"]
        nxt = lines[idx + 1]["start"] if idx + 1 < len(lines) else ts + 3.0
        base_duration = max(nxt - ts, 0.5)

        # Esperar al comienzo de esta línea
        while True:
            cur = now()
            wait = ts - cur
            if wait <= 0:
                break
            time.sleep(min(wait, 0.05))

        # Mostrar línea según tenga o no segmentos <..>
        if entry["inline"]:
            # Word-by-word sincronizado a tiempos absolutos
            print_line_word_by_word(entry["inline"], style, now_fn=now)
        else:
            # Letra por letra con duración estimada
            pretty_print_line_letter_by_letter(entry["text"], base_duration, style)

    # Esperar a que termine la reproducción
    while pygame.mixer.music.get_busy():
        time.sleep(0.2)

"""
if __name__ == "__main__":
    audio_path = Path("sample.mp3")   # ponga su archivo mp3 aquí
    lrc_path = Path("sample.lrc")     # ponga su archivo lrc aquí

    if not audio_path.exists():
        console.print(f"[bold red]No existe el archivo de audio: {audio_path}[/bold red]")
    elif not lrc_path.exists():
        console.print(f"[bold red]No existe el archivo LRC: {lrc_path}[/bold red]")
    else:
        console.print("[bold green]Reproduciendo y mostrando letra...[/bold green]")
        play_and_show(audio_path, lrc_path)
"""
if __name__ == "__main__":
    # Archivos principales
    audio_path = Path("lib/assets/sample.mp3")    # ponga su archivo mp3 aquí
    lrc_path = Path("lib/assets/sample.lrc")      # ponga su archivo lrc aquí

    # Archivos de respaldo
    backup_audio = Path("lib/assets/default/sample_word_by_word.mp3") # No modificar esto es solo para preview
    backup_lrc = Path("lib/assets/default/sample_wor__by_word_example.lrc") # No modificar esto es solo para preview

    # Bandera para preview
    use_preview = False

    # Verificar archivo de audio
    if not audio_path.exists():
        audio_path = backup_audio
        use_preview = True

    # Verificar archivo LRC
    if not lrc_path.exists():
        lrc_path = backup_lrc
        use_preview = True

    # Mensajes según resultado
    if use_preview:
        console.print("[yellow]⚠️ Usando Version Preview[/yellow]")
    else:
        console.print("[bold green]Reproduciendo y mostrando letra...[/bold green]")

    # Ejecutar siempre play_and_show con los paths correctos
    play_and_show(audio_path, lrc_path)