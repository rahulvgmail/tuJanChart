from stockpulse.app import create_app

app = create_app()


def create_app_wrapper():
    """Entry point for gunicorn / flask run."""
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
