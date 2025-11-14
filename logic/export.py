import csv
from pathlib import Path

def export_inventory_to_csv(rows, output_path: Path) -> None:
    if not rows:
      # Pusta lista — można zapisać nagłówki
      fieldnames = ["id", "name", "category", "purchase_date", "serial_number", "description"]
    else:
      fieldnames = list(rows[0].keys())

    # Upewnij się, że katalog istnieje
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def detect_usb_mount() -> Path | None:
    possible_mounts = [Path("/mnt/usb"), Path("/media/pi")]

    for base in possible_mounts:
        if not base.exists():
            continue
      
        if base.is_dir() and any(base.iterdir()):
            return base

        if base.name == "pi":
            for sub in base.iterdir():
                if sub.is_dir():
                    return sub

    return None      