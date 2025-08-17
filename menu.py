import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog
from rich.console import Console
from rich.panel import Panel
from rich.align import Align

console = Console()

BASE_DIR = os.path.dirname(__file__)
LIB_PATH = os.path.join(BASE_DIR, "lib")
ASSETS_PATH = os.path.join(LIB_PATH, "assets")

os.makedirs(ASSETS_PATH, exist_ok=True)

MENU = {
    "1": ("📂 Modo Estándar Clásico y confiable", "rc1.py"),
    "2": ("🎤 Karaoke Bug ¡Diviértete viendo cómo funciona! 😎", "rc2.py"),
    "3": ("⌛ Compatible con Word by Word Precisión milimétrica 🕰️", "rc4.py"),
    "4": ("⚡ Word by Word Remasterizado Experiencia mejorada 💎", "rc5.py"),
}


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def cargar_archivos():
    console.print("[bold cyan]¿Quieres cargar tu archivo MP3 y LRC? (y/s para sí, n para no)[/bold cyan]")
    respuesta = input("👉 ").strip().lower()

    if respuesta in ("y", "s"):
        root = tk.Tk()
        root.withdraw()  
        console.print("[bold yellow]Selecciona el archivo MP3[/bold yellow]")
        mp3_file = filedialog.askopenfilename(filetypes=[("Archivos MP3", "*.mp3")])

        console.print("[bold yellow]Selecciona el archivo LRC[/bold yellow]")
        lrc_file = filedialog.askopenfilename(filetypes=[("Archivos LRC", "*.lrc")])

        if mp3_file and lrc_file:
            shutil.copy(mp3_file, os.path.join(ASSETS_PATH, "sample.mp3"))
            shutil.copy(lrc_file, os.path.join(ASSETS_PATH, "sample.lrc"))
            console.print("[bold green]Archivos copiados a /lib/assets como sample.mp3 y sample.lrc[/bold green]")
        else:
            console.print("[bold red]No se seleccionaron ambos archivos. Continuando...[/bold red]")

   
    clear_console()


def mostrar_menu():
    console.print(
        Align.center("[bold magenta]Hecho con mucho amor por Emma (Violet's Version) 💜[/bold magenta]\n")
    )

    panel = Panel.fit(
        Align.center("[bold cyan]=== MENÚ PRINCIPAL ===[/bold cyan]", vertical="middle"),
        border_style="bright_magenta",
    )
    console.print(Align.center(panel))

    for key, (texto, _) in MENU.items():
        console.print(Align.center(f"[bold green]{key}[/bold green]. {texto}"))

    console.print(Align.center("[bold red]0[/bold red]. Salir"))


def ejecutar_opcion(opcion):
    if opcion in MENU:
        texto, script_name = MENU[opcion]
        script = os.path.join(LIB_PATH, script_name)
        if os.path.exists(script):
            clear_console() 
            console.print(f"[bold yellow]>>> Ejecutando {texto} Un Momento...[/bold yellow]\n")
            os.system(f"{sys.executable} {script}")
            input("✔ Finalizó la ejecución. Presiona ENTER para volver al menú")
        else:
            console.print(f"[bold red]El archivo {script_name} no existe en /lib.[/bold red]")
    elif opcion == "0":
        console.print("[bold red]Bye Bye... 👋[/bold red]")
        sys.exit(0)
    else:
        console.print("[bold red]Opción inválida. Intenta de nuevo.[/bold red]")


def main():
    cargar_archivos()
    while True:
        clear_console()
        mostrar_menu()
        opcion = input("\n👉 Selecciona una opción: ").strip()
        ejecutar_opcion(opcion)


if __name__ == "__main__":
    main()
