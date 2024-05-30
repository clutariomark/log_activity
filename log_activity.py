import os
import math
import time
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from PIL import Image
from Xlib import X, display, error, xobject, protocol


def get_active_window(
    disp_obj: display.Display,
) -> xobject.drawable.Window | None:
    root = disp_obj.screen().root
    net_active_window: int = disp_obj.intern_atom("_NET_ACTIVE_WINDOW")
    active_window_id: int = root.get_full_property(
        net_active_window, X.AnyPropertyType
    ).value[0]
    active_window = disp_obj.create_resource_object("window", active_window_id)

    try:
        active_window.get_wm_class()
    except error.BadWindow:
        active_window = None

    return active_window


def get_window_properties(window: xobject.drawable.Window) -> dict:
    class_name: str = ""
    window_name: str = ""

    window_class: tuple[str, str] | None = window.get_wm_class()
    if window_class is not None:
        class_name = window_class[1]

    temp_window_name: protocol.request.GetProperty | None = (
        window.get_full_property(
            window.display.get_atom("WM_NAME"), X.AnyPropertyType
        )
    )

    if temp_window_name is None:
        temp_window_name = window.get_full_property(
            window.display.get_atom("_NET_WM_NAME"), X.AnyPropertyType
        )

    if temp_window_name is not None:
        window_name = temp_window_name.value.decode()

    geometry: protocol.request.GetGeometry = window.get_geometry()

    window_props: dict = {
        "window_class": class_name,
        "window_name": window_name,
        "x": geometry.x,
        "y": geometry.y,
        "width": geometry.width,
        "height": geometry.height,
    }

    return window_props


def save_screenshot(
    window: xobject.drawable.Window,
    window_props: dict,
    output_path: Path,
    datetimestr: str,
) -> str:
    root: xobject.drawable.Window = window.query_tree().root
    raw: protocol.request.GetImage = root.get_image(
        window_props["x"],
        window_props["y"],
        window_props["width"],
        window_props["height"],
        X.ZPixmap,
        0xFFFFFFFF,
    )
    image: Image.Image = Image.frombytes(
        "RGB",
        (window_props["width"], window_props["height"]),
        raw.data,
        "raw",
        "BGRX",
    )

    file_name: Path = output_path.joinpath(
        f"screenshot_{datetimestr}_{window_props["window_class"]}.png"
    )
    image.save(file_name)

    return str(file_name)


def create_html_report(
    window_props: dict,
    screenshot_file_name: str,
    outpath: Path,
    timestamp: datetime,
) -> str:
    datetimestr: str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    html_log_str: str = (
        f"<tr><td>{datetimestr}</td>"
        + f"<td>{window_props["window_class"]}</td>"
        + f"<td>{window_props["window_name"]}</td>"
        + f'<td><a href="{screenshot_file_name}">screenshot</a></td></tr>'
    )

    table_file: Path = outpath.joinpath("tablecontents.html")
    with table_file.open("a") as fw:
        fw.write(f"{html_log_str}\n")

    env: Environment = Environment(
        loader=FileSystemLoader(["templates/", str(outpath)])
    )

    table: Template = env.get_template("table.html")
    title_str: str = timestamp.strftime("%Y %B %d")
    content: str = table.render(title=title_str)

    datestr: str = timestamp.strftime("%Y%m%d")
    report_file: Path = outpath.joinpath(f"report_{datestr}.html")
    with report_file.open("w") as fw:
        fw.write(content)

    return str(report_file)


def main() -> None:
    disp_obj: display.Display = display.Display()

    while True:
        active_window: xobject.drawable.Window | None = get_active_window(
            disp_obj
        )

        if active_window is not None:
            active_window_props: dict = get_window_properties(active_window)

            timestamp: datetime = datetime.now()
            second_val: int = math.floor(timestamp.second) // 10 * 10
            timestamp: datetime = timestamp.replace(
                second=second_val, microsecond=0
            )

            main_outpath: Path = Path(".").resolve()
            logs_dir: str | None = os.getenv("PERSONAL_LOGS")
            if logs_dir is not None:
                main_outpath = Path(logs_dir)

            datestr: str = timestamp.strftime("%Y%m%d")
            day_outpath: Path = main_outpath.joinpath(datestr)
            hour_outpath: Path = day_outpath.joinpath(timestamp.strftime("%H"))

            if not hour_outpath.is_dir():
                hour_outpath.mkdir(parents=True, exist_ok=True)

            datetimestr: str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            screenshot_file_name: str = save_screenshot(
                active_window, active_window_props, hour_outpath, datetimestr
            )

            create_html_report(
                active_window_props,
                screenshot_file_name,
                day_outpath,
                timestamp,
            )

            log_str: str = (
                f"{datetimestr}: "
                + f"{active_window_props["window_class"]} -- "
                + f"{active_window_props["window_name"]}"
            )

            print(log_str)

            time.sleep(10)


if __name__ == "__main__":
    main()
