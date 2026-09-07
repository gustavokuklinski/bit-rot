import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import pkcs12, BestAvailableEncryption
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

def generate_windows_code_sign_cert(filename="win_bitrot_cert.pfx", password="bitrot&Certificate@Windows912026"):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Rio de Janeiro"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Rio de Janeiro"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Gustavo Kuklinski"),
        x509.NameAttribute(NameOID.COMMON_NAME, "bitrot"), 
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        # MANDATORY FOR EXECUTABLES:
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CODE_SIGNING]), critical=True)
        .sign(private_key, hashes.SHA256())
    )

    pfx_data = pkcs12.serialize_key_and_certificates(
        name=b"BitRot Signing",
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=BestAvailableEncryption(password.encode('utf-8'))
    )

    with open(filename, "wb") as f:
        f.write(pfx_data)
        
    print(f"Success! Certificate saved to {filename}")

if __name__ == "__main__":
    generate_windows_code_sign_cert()
