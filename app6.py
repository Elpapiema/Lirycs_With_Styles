# stay_gold_player.py
import re
import time
from pathlib import Path
from typing import List, Tuple

import pygame
from rich.console import Console
from rich.text import Text

console = Console()

# Configuración de alineación del texto: "left", "center", "right"
TEXT_ALIGN = "center"

LRC_TIMING_RE = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\]')  # [mm:ss.xx]

def parse_lrc(path: Path) -> List[Tuple[float, str]]:
    """
    Devuelve lista ordenada de (timestamp_seconds, line_text)
    Soporta varias marcas por línea.
    """
    entries = []
    with path.open(encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            times = LRC_TIMING_RE.findall(raw)
            if not times:
                continue
            # extraer texto tras última marca ]
            text = LRC_TIMING_RE.split(raw)[-1].strip()
            for m in times:
                minutes = int(m[0])
                seconds = float(m[1])
                ts = minutes * 60 + seconds
                entries.append((ts, text))
    entries.sort(key=lambda x: x[0])
    return entries

def pretty_print_line(line: str, duration: float, effect_index: int = 0):
    """
    Imprime la línea revelando letra por letra en horizontal,
    con alineación configurable: left, center, right.
    """
    colors = ["bold red", "bold yellow", "bold green", "bold cyan", "bold magenta"]
    style = colors[effect_index % len(colors)]

    # Tiempo por carácter
    if len(line.strip()) > 0:
        delay_per_char = max(duration / len(line), 0.02)  # mínimo 0.02s
    else:
        delay_per_char = 0.02

    width = console.width
    revealed = ""  # cadena acumulada

    for ch in line:
        revealed += ch
        if TEXT_ALIGN == "center":
            padding = max((width - len(revealed)) // 2, 0)
            text_to_show = " " * padding + revealed
        elif TEXT_ALIGN == "right":
            padding = max(width - len(revealed), 0)
            text_to_show = " " * padding + revealed
        else:  # left
            text_to_show = revealed

        console.print(Text(text_to_show, style=style), end="\r", soft_wrap=False)
        time.sleep(delay_per_char)

    console.print("")  # salto de línea final

def play_and_show(audio_file: Path, lrc_file: Path):
    # Inicializar pygame mixer
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(str(audio_file))
    except Exception as e:
        console.print(f"[bold red]Error cargando audio:[/bold red] {e}")
        return

    lyrics = parse_lrc(lrc_file)
    if not lyrics:
        console.print("[bold yellow]No se encontraron líneas en el archivo LRC.[/bold yellow]")
        return

    # reproducir
    pygame.mixer.music.play()
    start = time.perf_counter()
    current_index = 0
    effect_index = 0

    # Loop principal
    while current_index < len(lyrics):
        ts, text = lyrics[current_index]
        next_ts = lyrics[current_index + 1][0] if current_index + 1 < len(lyrics) else ts + 3
        duration = max(next_ts - ts, 0.5)

        now = time.perf_counter() - start
        wait = ts - now
        if wait > 0:
            time.sleep(min(wait, 0.1))
            continue

        pretty_print_line(text, duration, effect_index)
        effect_index += 1
        current_index += 1

    # esperar a que termine la reproducción
    while pygame.mixer.music.get_busy():
        time.sleep(0.2)

if __name__ == "__main__":
    audio_path = Path("sample.mp3")    # ponga su archivo mp3 aquí
    lrc_path = Path("sample.lrc")      # ponga su archivo lrc aquí

    if not audio_path.exists():
        console.print(f"[bold red]No existe el archivo de audio: {audio_path}[/bold red]")
    elif not lrc_path.exists():
        console.print(f"[bold red]No existe el archivo LRC: {lrc_path}[/bold red]")
    else:
        console.print("[bold green]Reproduciendo y mostrando letra...[/bold green]")
        play_and_show(audio_path, lrc_path)
