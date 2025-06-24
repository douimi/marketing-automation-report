import os
from subprocess import run

CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"

if not (os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)):
    print("Generating self-signed certificate...")
    run([
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", KEY_FILE, "-out", CERT_FILE,
        "-days", "365", "-nodes",
        "-subj", "/CN=localhost"
    ])
    print("Certificate generated.")
else:
    print("Certificate already exists.") 