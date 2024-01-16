import os
import sys
from importlib.metadata import entry_points

from django.apps import apps
from pyfiglet import Figlet
from rich.console import Console
from rich.text import Text


def get_extension_app_config_name():
    eps = entry_points()
    (app_config_ep,) = eps.select(group="swo.mpt.ext", name="app_config")
    app_config = app_config_ep.load()
    return f"{app_config.__module__}.{app_config.__name__}"


def get_extension_appconfig():
    app_config_name = get_extension_app_config_name()
    return next(
        filter(
            lambda app: app_config_name
            == f"{app.__class__.__module__}.{app.__class__.__name__}",
            apps.app_configs.values(),
        ),
        None,
    )


def get_extension():
    return get_extension_appconfig().extension


def get_events_registry():
    return get_extension().events


def gradient(start_hex, end_hex, num_samples=10):
    start_rgb = tuple(int(start_hex[i : i + 2], 16) for i in range(1, 6, 2))
    end_rgb = tuple(int(end_hex[i : i + 2], 16) for i in range(1, 6, 2))
    gradient_colors = [start_hex]
    for sample in range(1, num_samples):
        red = int(
            start_rgb[0]
            + (float(sample) / (num_samples - 1)) * (end_rgb[0] - start_rgb[0])
        )
        green = int(
            start_rgb[1]
            + (float(sample) / (num_samples - 1)) * (end_rgb[1] - start_rgb[1])
        )
        blue = int(
            start_rgb[2]
            + (float(sample) / (num_samples - 1)) * (end_rgb[2] - start_rgb[2])
        )
        gradient_colors.append(f"#{red:02X}{green:02X}{blue:02X}")

    return gradient_colors


def show_banner():
    program_name = os.path.basename(sys.argv[0])
    program_name = "".join((program_name[0:3].upper(), program_name[3:]))
    figlet = Figlet("georgia11")

    banner = Text(figlet.renderText(program_name))

    colored_banner = Text()

    gradient_colors = gradient("#009900", "#ffffff", len(banner))
    gradient_colors = gradient("#0c3f13", "#00dd6f", len(banner))
    console = Console()

    for i in range(len(banner)):
        char = banner[i : i + 1]
        char.stylize(gradient_colors[i])
        colored_banner = Text.assemble(
            colored_banner,
            char,
        )

    console.print(colored_banner)
