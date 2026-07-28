from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
import os
import traceback

class RSACrypto:
    def __init__(self, key_file='rsa_keys.pem'):
        self.key_file = key_file
        self.private_key = None
        self.public_key = None
        self.load_or_generate_keys()
    
    def load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        if os.path.exists(self.key_file):
            print(f"🔐 Loading RSA keys from {self.key_file}...")
            try:
                with open(self.key_file, 'rb') as f:
                    key_data = f.read()
                
                # Load private key
                self.private_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
                self.public_key = self.private_key.public_key()
                print("✅ RSA keys loaded successfully")
                return
            except Exception as e:
                print(f"⚠️ Failed to load keys: {str(e)}")
                print("🔄 Generating new keys...")
        
        self.generate_keys()
        self.save_keys()
    
    def generate_keys(self):
        """Generate RSA key pair (2048 bit)"""
        try:
            print("🔐 Generating RSA keys...")
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
            print("✅ RSA keys generated successfully")
        except Exception as e:
            print(f"❌ RSA key generation error: {str(e)}")
            raise
    
    def save_keys(self):
        """Save private key to file"""
        try:
            pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.key_file, 'wb') as f:
                f.write(pem)
            print(f"✅ RSA keys saved to {self.key_file}")
        except Exception as e:
            print(f"⚠️ Failed to save keys: {str(e)}")
    
    def get_public_key_pem(self):
        """Get public key in PEM format"""
        try:
            return self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
        except Exception as e:
            print(f"❌ Error getting public key: {str(e)}")
            return None
    
    def encrypt(self, plaintext):
        """Encrypt plaintext using RSA public key"""
        try:
            print(f"🔐 Encrypting {len(plaintext)} characters...")
            
            # Check plaintext size
            plaintext_bytes = plaintext.encode('utf-8')
            if len(plaintext_bytes) > 190:
                raise Exception(f"Plaintext too long! Maximum 190 bytes, got {len(plaintext_bytes)} bytes")
            
            ciphertext = self.public_key.encrypt(
                plaintext_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            result = base64.b64encode(ciphertext).decode('utf-8')
            print(f"✅ Encryption successful, ciphertext length: {len(result)}")
            return result
        except Exception as e:
            print(f"❌ Encryption error: {str(e)}")
            print(traceback.format_exc())
            raise Exception(f"Encryption failed: {str(e)}")
    
    def decrypt(self, ciphertext_b64):
        """Decrypt ciphertext using RSA private key"""
        try:
            print(f"🔓 Decrypting ciphertext...")
            
            # Clean input
            ciphertext_b64 = ciphertext_b64.strip()
            # Remove whitespace and newlines
            ciphertext_b64 = ''.join(c for c in ciphertext_b64 if c.isalnum() or c in '+/=')
            
            # Check if valid base64
            try:
                ciphertext = base64.b64decode(ciphertext_b64)
            except Exception as e:
                raise Exception(f"Invalid base64 encoding: {str(e)}")
            
            print(f"📊 Ciphertext bytes: {len(ciphertext)} (expected: 256 for RSA-2048)")
            
            if len(ciphertext) != 256:
                raise Exception(f"Invalid ciphertext length: {len(ciphertext)} bytes. Expected 256 bytes for RSA-2048.")
            
            plaintext = self.private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            result = plaintext.decode('utf-8')
            print(f"✅ Decryption successful, plaintext length: {len(result)}")
            return result
        except Exception as e:
            print(f"❌ Decryption error: {str(e)}")
            print(traceback.format_exc())
            raise Exception(f"Decryption failed: {str(e)}")