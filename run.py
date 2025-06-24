import os
from app import app

# Generate certificate if not present
if not (os.path.exists("cert.pem") and os.path.exists("key.pem")):
    import generate_cert  # This will generate the certs

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=443,
        ssl_context=("cert.pem", "key.pem")
    ) 