import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    if getattr(sys, "frozen", False):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

if __name__ == "__main__":
    # Point to the internal app.py
    # When frozen, we'll bundle src/app.py as app.py in the root or similar
    # Let's assume we bundle it alongside.
    
    # We need to set the path to the app script
    if getattr(sys, "frozen", False):
        app_path = resolve_path("app.py")
    else:
        app_path = os.path.join(os.path.dirname(__file__), "src", "app.py")
    
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
