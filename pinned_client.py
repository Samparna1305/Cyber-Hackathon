import requests
import hashlib
import ssl
import socket

HOST = "127.0.0.1"
PORT = 5000

EXPECTED_PIN = "06cc57cf75abb31b75ded3379001e893a0b6b10be2609258f996fac5dda378e8"


def get_cert_hash():

    context = ssl._create_unverified_context()

    with socket.create_connection((HOST, PORT)) as sock:

        with context.wrap_socket(
            sock,
            server_hostname=HOST
        ) as ssock:

            cert = ssock.getpeercert(binary_form=True)

            return hashlib.sha256(cert).hexdigest()


server_hash = get_cert_hash()

print("Server hash:", server_hash)

if server_hash != EXPECTED_PIN:

    raise Exception(
        "Certificate Pinning Failed"
    )

response = requests.post(

    f"https://{HOST}:{PORT}/login",

    json={
        "username":"sam",
        "password":"123"
    },

    verify=False
)

print(response.text)