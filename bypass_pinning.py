import requests

proxy = {
    "http":"http://127.0.0.1:8080",
    "https":"http://127.0.0.1:8080"
}

print(
"Pinning bypass enabled"
)

response = requests.post(

"https://127.0.0.1:5000/login",

json={

"username":"attacker",

"password":"bypass123"

},

verify=False,

proxies=proxy

)

print(response.text)
