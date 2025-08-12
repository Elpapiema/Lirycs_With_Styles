# stay_gold_player.py
import re
import time
from pathlib import Path
from typing import List, Tuple

import pygame
from rich.console import Console
from rich.text import Text

console = Console()

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

def pretty_print_line(line: str, effect_index: int = 0):
    """
    Imprime la línea con colorines usando rich.
    Cambiamos estilo según effect_index para variación.
    """
    t = Text(line)
    # generar colores simples por caracter (ciclo)
    colors = ["bold red", "bold yellow", "bold green", "bold cyan", "bold magenta"]
    style = colors[effect_index % len(colors)]
    t.stylize(style)
    console.print(t, justify="center")

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

    # Loop principal: esperamos y mostramos líneas en su timestamp
    while current_index < len(lyrics):
        ts, text = lyrics[current_index]
        now = time.perf_counter() - start
        wait = ts - now
        if wait > 0:
            # dormir en trozos pequeños para mantener responsividad
            time.sleep(min(wait, 0.1))
            continue
        # mostrar la línea
        pretty_print_line(text, effect_index)
        effect_index += 1
        current_index += 1

    # esperar a que termine la reproducción antes de cerrar (o cortar)
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
