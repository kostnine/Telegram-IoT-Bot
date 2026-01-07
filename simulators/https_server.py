#!/usr/bin/env python3
"""
Simple HTTPS server for phone sensor app
Allows GPS and other sensors to work on mobile browsers
"""

import http.server
import ssl
import os
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

CERT_FILE = "server.pem"
KEY_FILE = "server.key"

def generate_self_signed_cert():
    """Generate self-signed certificate using Python cryptography"""
    print("🔐 Generating self-signed SSL certificate...")
    
    # Generate key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address("172.20.10.2")),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())
    
    # Write key
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write cert
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print("✅ Certificate generated!")

if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
    import ipaddress
    generate_self_signed_cert()

# Start HTTPS server
PORT = 8443
Handler = http.server.SimpleHTTPRequestHandler

# Change to the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print(f"🔒 Starting HTTPS server on port {PORT}")
print(f"📱 Open on phone: https://172.20.10.2:{PORT}/phone_sensor_app.html")
print("⚠️  Accept the security warning (self-signed certificate)")
print(f"📂 Serving from: {os.getcwd()}")

httpd = http.server.HTTPServer(("0.0.0.0", PORT), Handler)

# Wrap with SSL
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(CERT_FILE, KEY_FILE)
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print("✅ HTTPS server running...")
httpd.serve_forever()
