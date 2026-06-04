import os
import sys
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo


PARIS_TZ = ZoneInfo("Europe/Paris")


class TimestampedTee:
    """Duplique stdout/stderr vers la console et un fichier journal horodate."""

    def __init__(self, stream, log_file_path: str):
        self.stream = stream
        self.log_file_path = log_file_path
        self._buffer = ""

    def write(self, message):
        if not isinstance(message, str):
            message = str(message)

        # On garde l'affichage console tel quel pour conserver l'experience actuelle.
        self.stream.write(message)

        # On ajoute un horodatage au debut de chaque ligne pour le fichier log.
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip() == "":
                continue
            ts = datetime.now(PARIS_TZ).strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {line}\n")

    def flush(self):
        self.stream.flush()


def archive_previous_logs(logs_dir: str):
    """
    Archive les .log des jours precedents dans des .zip mensuels.

    Retourne un resume pour affichage console:
    - archived_count: nb de fichiers archives
    - skipped_count: nb de fichiers ignores (dont le log du jour)
    - reclaimed_bytes: taille des sources supprimees
    - archives: liste des chemins zip touches
    - errors: erreurs non bloquantes
    """
    result = {
        "archived_count": 0,
        "skipped_count": 0,
        "reclaimed_bytes": 0,
        "archives": [],
        "errors": [],
    }

    os.makedirs(logs_dir, exist_ok=True)
    archive_dir = os.path.join(logs_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    today = datetime.now(PARIS_TZ).date()
    files_by_month = {}

    # On filtre tous les logs qui ne sont pas du jour pour les archiver.
    for name in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, name)
        if not os.path.isfile(file_path) or not name.lower().endswith(".log"):
            continue

        try:
            file_date = datetime.fromtimestamp(os.path.getmtime(file_path), PARIS_TZ).date()
        except OSError as e:
            result["errors"].append(f"mtime introuvable pour {name}: {e}")
            continue

        if file_date >= today:
            result["skipped_count"] += 1
            continue

        month_key = file_date.strftime("%Y-%m")
        files_by_month.setdefault(month_key, []).append((file_path, file_date))

    for month_key, entries in files_by_month.items():
        zip_path = os.path.join(archive_dir, f"logs_{month_key}.zip")
        existing_names = set()

        if os.path.exists(zip_path):
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    existing_names = set(zf.namelist())
            except Exception as e:
                result["errors"].append(f"lecture archive {zip_path} impossible: {e}")
                continue

        try:
            with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path, file_date in entries:
                    name = os.path.basename(file_path)
                    arcname = f"{file_date.isoformat()}/{name}"

                    if arcname in existing_names:
                        # Deja present dans l'archive: on ne duplique pas.
                        result["skipped_count"] += 1
                        continue

                    zf.write(file_path, arcname=arcname)
                    try:
                        file_size = os.path.getsize(file_path)
                    except OSError:
                        file_size = 0

                    os.remove(file_path)
                    result["reclaimed_bytes"] += file_size
                    result["archived_count"] += 1
        except Exception as e:
            result["errors"].append(f"echec archivage vers {zip_path}: {e}")
            continue

        if zip_path not in result["archives"]:
            result["archives"].append(zip_path)

    return result


def setup_daily_console_log(component_name: str):
    """Active un log journalier tout en conservant l'affichage console."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    logs_dir = os.path.join(base_dir, "data", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Avant d'ouvrir le log du jour, on archive les logs precedents.
    archive_result = archive_previous_logs(logs_dir)
    if archive_result["archived_count"] > 0:
        mb = archive_result["reclaimed_bytes"] / (1024 ** 2)
        archives = ", ".join(archive_result["archives"])
        print(
            "Archive logs: "
            f"{archive_result['archived_count']} fichier(s) archive(s), "
            f"{mb:.2f} MB liberes -> {archives}"
        )
    else:
        print("Archive logs: rien a archiver")

    if archive_result["errors"]:
        for err in archive_result["errors"]:
            print(f"Archive logs warning: {err}")

    date_str = datetime.now(PARIS_TZ).strftime("%Y-%m-%d")
    log_file_path = os.path.join(logs_dir, f"{component_name}_{date_str}.log")

    # On remplace stdout/stderr par un tee pour capturer tous les print existants.
    sys.stdout = TimestampedTee(sys.stdout, log_file_path)
    sys.stderr = TimestampedTee(sys.stderr, log_file_path)

    print(f"Journal actif: {log_file_path}")
    return log_file_path
