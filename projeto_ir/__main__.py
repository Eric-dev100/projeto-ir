"""Abre a tela do Projeto IR no navegador: python -m projeto_ir"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    from streamlit.web import cli as stcli

    app = Path(__file__).resolve().parent / "app.py"
    sys.argv = ["streamlit", "run", str(app), "--server.headless", "false",
                "--browser.gatherUsageStats", "false",
                "--client.toolbarMode", "minimal", "--theme.primaryColor", "#0d7560"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
