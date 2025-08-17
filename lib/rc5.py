# Version Para Lrc Palabra por Palabra Remasterizado
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
    lines: List[Dict[str, Any]] = []

    with path.open(encoding='utf-8') as f:
        for raw in f:
            raw = raw.rstrip("\n")
            if not raw.strip():
                continue

            line_times = LRC_LINE_TS_RE.findall(raw)
            if not line_times:
                continue

            text_after = LRC_LINE_TS_RE.split(raw)[-1]
            word_matches = list(LRC_WORD_TS_RE.finditer(text_after))
            plain_text = LRC_WORD_TS_RE.sub("", text_after).strip()

            if word_matches:
                segments: List[Tuple[float, str]] = []
                pos = 0
                first_start = _to_seconds(*line_times[0])
                first_seg = text_after[pos:word_matches[0].start()].strip()
                if first_seg:
                    segments.append((first_start, first_seg))
                pos = word_matches[0].end()

                for i in range(len(word_matches) - 1):
                    ts = _to_seconds(*word_matches[i].groups())
                    seg = text_after[pos:word_matches[i + 1].start()].strip()
                    if seg:
                        segments.append((ts, seg))
                    pos = word_matches[i + 1].end()

                last_ts = _to_seconds(*word_matches[-1].groups())
                tail = text_after[pos:].strip()
                if tail:
                    segments.append((last_ts, tail))

                segments.sort(key=lambda t: t[0])

                for m, s in line_times:
                    start_ts = _to_seconds(m, s)
                    segs = segments
                    lines.append({
                        "start": start_ts,
                        "text": plain_text,
                        "inline": segs
                    })
            else:
                for m, s in line_times:
                    start_ts = _to_seconds(m, s)
                    lines.append({
                        "start": start_ts,
                        "text": plain_text,
                        "inline": None
                    })

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

    console.print("")

def print_line_word_by_word(segments: List[Tuple[float, str]], style: str, now_fn):
    """
    Muestra una línea que tiene segmentos (ts, palabra/fragmento) con tiempos absolutos,
    pero cada fragmento se revela letra por letra de forma gradual.
    """
    buffer = ""
    n = len(segments)

    for i, (seg_ts, seg_text) in enumerate(segments):
        # Esperar al momento exacto del segmento
        while True:
            now = now_fn()
            wait = seg_ts - now
            if wait <= 0:
                break
            time.sleep(min(wait, 0.02))  # precisión alta

        # Calcular cuánto tiempo tenemos antes del próximo segmento
        if i + 1 < n:
            next_ts = segments[i + 1][0]
            duration = max(next_ts - seg_ts, 0.05)
        else:
            duration = 0.5  # último segmento

        # Añadir espacio si no es el primer segmento y no empieza con puntuación
        if buffer and seg_text and seg_text[0] not in ",.;:!?)]}":
            buffer += " "

        # Revelado letra por letra
        partial_word = ""
        delay_per_char = max(duration / max(len(seg_text), 1), 0.02)
        for ch in seg_text:
            partial_word += ch
            _aligned_print(buffer + partial_word, style)
            time.sleep(delay_per_char)

        buffer += seg_text

    console.print("")

def play_and_show(audio_file: Path, lrc_file: Path):
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

    pygame.mixer.music.play()
    start = time.perf_counter()

    def now() -> float:
        return time.perf_counter() - start

    for idx, entry in enumerate(lines):
        style = colors[idx % len(colors)]
        ts = entry["start"]
        nxt = lines[idx + 1]["start"] if idx + 1 < len(lines) else ts + 3.0
        base_duration = max(nxt - ts, 0.5)

        while True:
            cur = now()
            wait = ts - cur
            if wait <= 0:
                break
            time.sleep(min(wait, 0.05))

        if entry["inline"]:
            print_line_word_by_word(entry["inline"], style, now_fn=now)
        else:
            pretty_print_line_letter_by_letter(entry["text"], base_duration, style)

    while pygame.mixer.music.get_busy():
        time.sleep(0.2)
"""
if __name__ == "__main__":
    audio_path = Path("sample.mp3")
    lrc_path = Path("sample.lrc")

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