from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Secure Backend running on HTTPS"
    })


@app.route('/login', methods=['POST'])
def login():

    data = request.json

    return jsonify({
        "status": "authenticated",
        "username": data["username"],
        "token": "secret-jwt-token-abcd1234efgh"
    })


if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000,
        ssl_context=(
            '../certificates/cert.pem',
            '../certificates/key.pem'
        )
    )