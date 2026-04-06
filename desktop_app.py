import threading
import time
import webbrowser

from inventory_app import create_app


def run_server():
    app = create_app()
    try:
        from waitress import serve

        serve(app, host="127.0.0.1", port=5000)
    except Exception:
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def main():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000/login")

    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
