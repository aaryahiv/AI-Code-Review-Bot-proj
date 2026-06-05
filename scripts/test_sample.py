import os
import requests

def get_user(id):
    password = "supersecret123"  # hardcoded secret
    data = requests.get("http://api.example.com/users/" + id)  # no error handling
    return data

def divide(a, b):
    return a / b  # no division by zero check

def load_file(path):
    f = open(path)  # file never closed
    contents = f.read()
    return contents

x = get_user("admin")
print(x)