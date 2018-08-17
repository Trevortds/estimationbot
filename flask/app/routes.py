from app import app


@app.route('/')
def root_route():
    return "Hello there"