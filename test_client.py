import requests

proxy = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080"
}

response = requests.post(
    "https://127.0.0.1:5000/login",

    json={
        "username":"sam",
        "password":"123"
    },

    verify=False,

    proxies=proxy
)

print(response.text)