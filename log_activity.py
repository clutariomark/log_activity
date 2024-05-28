import os
import time
from datetime import datetime
from pathlib import Path

from PIL import Image
from Xlib import X, display


def get_active_window(disp_obj: display.Display):
    root = disp_obj.screen().root
    net_active_window: int = disp_obj.intern_atom("_NET_ACTIVE_WINDOW")
    active_window_id: int = root.get_full_property(
        net_active_window, X.AnyPropertyType
    ).value[0]
    active_window = disp_obj.create_resource_object("window", active_window_id)

    return active_window


def get_window_properties(window) -> dict:
    class_name: str = ""
    window_class: tuple[str, str] | None = window.get_wm_class()
    if window_class is not None:
        class_name = window_class[1]

    window_name: str = window.get_full_property(
        window.display.get_atom("WM_NAME"), X.AnyPropertyType
    ).value.decode()
    geometry = window.get_geometry()

    return {
        "window_class": class_name,
        "window_name": window_name,
        "x": geometry.x,
        "y": geometry.y,
        "width": geometry.width,
        "height": geometry.height,
    }


def save_screenshot(
    window, window_props: dict, output_path: Path, datetimestr: str
) -> str:
    root = window.query_tree().root
    raw = root.get_image(
        window_props["x"],
        window_props["y"],
        window_props["width"],
        window_props["height"],
        X.ZPixmap,
        0xFFFFFFFF,
    )
    image = Image.frombytes(
        "RGB",
        (window_props["width"], window_props["height"]),
        raw.data,
        "raw",
        "BGRX",
    )

    file_name = output_path.joinpath(
        f"screenshot_{datetimestr}_{window_props["window_class"]}.png"
    )
    image.save(file_name)

    return str(file_name)


def main() -> None:
    disp_obj: display.Display = display.Display()

    while True:
        active_window = get_active_window(disp_obj)
        active_window_props: dict = get_window_properties(active_window)

        timestamp: datetime = datetime.now()

        main_outpath: Path = Path(".").resolve()
        logs_dir: str | None = os.getenv("PERSONAL_LOGS")
        if logs_dir is not None:
            main_outpath = Path(logs_dir)

        day_outpath: Path = main_outpath.joinpath(timestamp.strftime("%Y%m%d"))
        hour_outpath: Path = day_outpath.joinpath(timestamp.strftime("%H"))

        if not hour_outpath.is_dir():
            hour_outpath.mkdir(parents=True, exist_ok=True)

        datetimestr: str = timestamp.strftime("%Y%m%d-%H%M%S")
        screenshot_file_name: str = save_screenshot(
            active_window, active_window_props, hour_outpath, datetimestr
        )

        print(
            f"{datetimestr}: {active_window_props["window_class"]} -- {screenshot_file_name}"
        )

        time.sleep(10)


if __name__ == "__main__":
    main()
