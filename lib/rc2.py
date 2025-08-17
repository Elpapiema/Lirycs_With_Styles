# stay_gold_karaoke_typewriter.py
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
    entries = []
    with path.open(encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            times = LRC_TIMING_RE.findall(raw)
            if not times:
                continue
            # texto después de las marcas
            text = LRC_TIMING_RE.split(raw)[-1].strip()
            for m in times:
                minutes = int(m[0])
                seconds = float(m[1])
                ts = minutes * 60 + seconds
                entries.append((ts, text))
    entries.sort(key=lambda x: x[0])
    return entries

def hex_to_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(c):
    return "#{:02x}{:02x}{:02x}".format(int(c[0]), int(c[1]), int(c[2]))

def lerp_color(c1, c2, t: float):
    return (c1[0] + (c2[0]-c1[0]) * t,
            c1[1] + (c2[1]-c1[1]) * t,
            c1[2] + (c2[2]-c1[2]) * t)

def build_gradient_colors(line: str, start_hex: str, end_hex: str):
    total = len(line)
    if total == 0:
        return []
    c1 = hex_to_rgb(start_hex)
    c2 = hex_to_rgb(end_hex)
    colors = []
    for i in range(total):
        t = i / max(total - 1, 1)
        rgb = lerp_color(c1, c2, t)
        colors.append(rgb_to_hex(rgb))
    return colors

def typewriter_karaoke(line: str, duration: float, start_color="#ffeb3b", end_color="#ff3d00"):
    """
    Revela la línea carácter por carácter calculando per-char delay a partir
    de duration. Aplica degradado entre start_color y end_color.
    """
    if not line:
        return
    total_chars = len(line)
    per_char = max(duration / total_chars, 0.001)  # evitar 0
    gradient = build_gradient_colors(line, start_color, end_color)

    # mostramos progresivamente más caracteres
    revealed = 0
    start_time = time.perf_counter()
    while revealed < total_chars:
        now = time.perf_counter()
        # sincronizar en caso de que las sleeps acumuladas fallen
        elapsed = now - start_time
        target_revealed = min(int(elapsed / per_char), total_chars)
        if target_revealed <= revealed:
            # al menos dormir un poco
            time.sleep(min(per_char / 4, 0.02))
            continue
        revealed = target_revealed

        t = Text()
        for i, ch in enumerate(line):
            if i < revealed:
                # aplicamos color del degradado para caracteres ya revelados
                t.append(ch, style=gradient[i])
            else:
                # carácter no revelado: tenue
                t.append(ch, style="grey37")
        # imprimimos en la misma línea, centrado
        console.print(t, justify="center", end="\r")
        console.file.flush()

    # Si sobra tiempo (por imprecisiones), esperamos el resto
    total_elapsed = time.perf_counter() - start_time
    if total_elapsed < duration:
        time.sleep(duration - total_elapsed)
    # asegure la línea final totalmente coloreada
    final = Text()
    for i, ch in enumerate(line):
        final.append(ch, style=gradient[i])
    console.print(final, justify="center")

def play_and_show(audio_file: Path, lrc_file: Path):
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

    pygame.mixer.music.play()
    start = time.perf_counter()

    for idx, (ts, text) in enumerate(lyrics):
        now = time.perf_counter() - start
        wait = ts - now
        if wait > 0:
            time.sleep(wait)

        # duración hasta la siguiente línea (estimada)
        if idx + 1 < len(lyrics):
            duration = max(lyrics[idx + 1][0] - ts, 0.1)
        else:
            # tiempo extra razonable para la última línea
            duration = 3.0

        # puedes cambiar los colores aquí:
        typewriter_karaoke(text, duration, start_color="#ffd54f", end_color="#ff6e40")

    # Esperar a que termine la pista
    while pygame.mixer.music.get_busy():
        time.sleep(0.2)

"""
if __name__ == "__main__":
    audio_path = Path("sample.mp3")    # ponga su archivo mp3 aquí
    lrc_path = Path("sample.lrc")      # ponga su archivo lrc aquí

    if not audio_path.exists():
        console.print(f"[bold red]No existe el archivo de audio: {audio_path}[/bold red]")
    elif not lrc_path.exists():
        console.print(f"[bold red]No existe el archivo LRC: {lrc_path}[/bold red]")
    else:
        console.print("[bold green]Reproduciendo y mostrando letra (typewriter + degradado)...[/bold green]")
        play_and_show(audio_path, lrc_path)
"""
if __name__ == "__main__":
    # Archivos principales
    audio_path = Path("lib/assets/sample.mp3")    # ponga su archivo mp3 aquí
    lrc_path = Path("lib/assets/sample.lrc")      # ponga su archivo lrc aquí

    # Archivos de respaldo
    backup_audio = Path("lib/assets/default/sample.mp3") # No modificar esto es solo para preview
    backup_lrc = Path("lib/assets/default/sample.lrc") # No modificar esto es solo para preview

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