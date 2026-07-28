from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from rsa_crypto import RSACrypto
from lsb_stego import LSBSteganography
from PIL import Image
import os
import uuid
import base64
import numpy as np
from datetime import datetime
import traceback

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Setup folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ORIGINAL_FOLDER = os.path.join(UPLOAD_FOLDER, 'original')
STEGO_FOLDER = os.path.join(UPLOAD_FOLDER, 'stego')
DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'documents')

os.makedirs(ORIGINAL_FOLDER, exist_ok=True)
os.makedirs(STEGO_FOLDER, exist_ok=True)
os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Initialize crypto and stego
rsa = RSACrypto()
stego = LSBSteganography()

RSA_KEYS = {
    'public_key': rsa.get_public_key_pem(),
    'private_key': 'Private key is stored securely in the backend (not exposed for security)'
}

def calculate_metrics(original_path, stego_path):
    """
    Menghitung MSE dan PSNR antara dua gambar
    
    MSE = (1/(M×N)) × Σ(i=1 to M) Σ(j=1 to N) (X(i,j) - Y(i,j))²
    PSNR = 10 × log10(MAX² / MSE)
    """
    try:
        img1 = Image.open(original_path)
        img2 = Image.open(stego_path)
        
        if img1.mode != 'RGB':
            img1 = img1.convert('RGB')
        if img2.mode != 'RGB':
            img2 = img2.convert('RGB')
        
        arr1 = np.array(img1, dtype=np.float64)
        arr2 = np.array(img2, dtype=np.float64)
        
        if arr1.shape != arr2.shape:
            raise Exception("Image dimensions do not match")
        
        # MSE = (1/(M×N)) × Σ(i=1 to M) Σ(j=1 to N) (X(i,j) - Y(i,j))²
        mse = np.mean((arr1 - arr2) ** 2)
        
        # PSNR = 10 × log10(MAX² / MSE)
        if mse == 0:
            psnr = float('inf')
        else:
            max_pixel = 255.0
            psnr = 10 * np.log10((max_pixel ** 2) / mse)
        
        return {
            'psnr': psnr,
            'mse': mse
        }
        
    except Exception as e:
        raise Exception(f"Error calculating metrics: {str(e)}")


# ============================================================
# FUNGSI BACA DOKUMEN
# ============================================================
def read_document_file(file_path):
    """Read content from document file (TXT, PDF, DOCX)"""
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif file_ext == '.pdf':
            try:
                import PyPDF2
                text = ""
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text.strip() if text.strip() else "[PDF] Tidak ada teks yang bisa diekstrak"
            except ImportError:
                return "[PDF] Library PyPDF2 tidak terinstall. Install: pip install PyPDF2"
            except Exception as e:
                return f"[PDF Error: {str(e)}]"
        
        elif file_ext in ['.docx', '.doc']:
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                return text.strip() if text.strip() else "[DOCX] Tidak ada teks yang bisa diekstrak"
            except ImportError:
                return "[DOCX] Library python-docx tidak terinstall. Install: pip install python-docx"
            except Exception as e:
                return f"[DOCX Error: {str(e)}]"
        
        else:
            return f"[Unsupported file format: {file_ext}]"
            
    except Exception as e:
        return f"[Error reading file: {str(e)}]"


# ============================================================
# ROUTE: HOMEPAGE
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/keys', methods=['GET'])
def get_keys():
    return jsonify({
        'public_key': RSA_KEYS['public_key'],
        'private_key': RSA_KEYS['private_key'],
        'key_size': 2048,
        'algorithm': 'RSA-OAEP',
        'hash_algorithm': 'SHA-256'
    })


@app.route('/api/capacity', methods=['POST'])
def get_capacity():
    try:
        data = request.json
        image_base64 = data.get('image', '')
        
        if not image_base64:
            return jsonify({'error': 'Image is required'}), 400
        
        temp_id = uuid.uuid4().hex[:8]
        temp_path = os.path.join(ORIGINAL_FOLDER, f'temp_{temp_id}.png')
        
        with open(temp_path, 'wb') as f:
            f.write(base64.b64decode(image_base64))
        
        capacity = stego.get_capacity(temp_path)
        
        try:
            os.remove(temp_path)
        except:
            pass
        
        return jsonify({'capacity': capacity})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# 🔐 ENDPOINT: RSA ENCRYPT
# ============================================================
@app.route('/api/rsa/encrypt', methods=['POST'])
def rsa_encrypt():
    try:
        data = request.json
        plaintext = data.get('plaintext', '')
        
        if not plaintext:
            return jsonify({'error': 'Plaintext is required'}), 400
        
        print(f"🔐 RSA Encrypt - Plaintext length: {len(plaintext)} chars")
        
        ciphertext = rsa.encrypt(plaintext)
        print(f"🔐 Ciphertext length: {len(ciphertext)} chars")
        
        return jsonify({
            'success': True,
            'ciphertext': ciphertext,
            'ciphertext_length': len(ciphertext),
            'plaintext_length': len(plaintext)
        })
        
    except Exception as e:
        print(f"❌ RSA Encrypt error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================================
# 🔐 ENDPOINT: RSA DECRYPT
# ============================================================
@app.route('/api/rsa/decrypt', methods=['POST'])
def rsa_decrypt():
    try:
        data = request.json
        ciphertext = data.get('ciphertext', '')
        
        if not ciphertext:
            return jsonify({'error': 'Ciphertext is required'}), 400
        
        # Debug: tampilkan detail ciphertext
        print("=" * 60)
        print("🔓 RSA DECRYPT REQUEST")
        print("=" * 60)
        print(f"📝 Raw ciphertext length: {len(ciphertext)} chars")
        print(f"📝 Raw ciphertext preview: {ciphertext[:50]}...")
        print(f"📝 Raw ciphertext last 50: ...{ciphertext[-50:]}")
        
        # Bersihkan input: hapus whitespace, newline, dll
        original_ciphertext = ciphertext
        ciphertext = ciphertext.strip()
        ciphertext = ''.join(c for c in ciphertext if c.isalnum() or c in '+/=')
        
        print(f"📝 Cleaned ciphertext length: {len(ciphertext)} chars")
        
        if len(ciphertext) != len(original_ciphertext.strip()):
            print(f"⚠️ Warning: Ciphertext was modified during cleaning!")
            print(f"   Original: {len(original_ciphertext)} chars")
            print(f"   Cleaned: {len(ciphertext)} chars")
        
        # Cek apakah base64 valid
        try:
            decoded = base64.b64decode(ciphertext)
            print(f"📊 Decoded bytes length: {len(decoded)} bytes (expected: 256 for RSA-2048)")
        except Exception as e:
            print(f"❌ Invalid base64: {str(e)}")
            return jsonify({'error': f'Invalid base64 ciphertext: {str(e)}'}), 400
        
        plaintext = rsa.decrypt(ciphertext)
        print(f"✅ Decryption successful!")
        print(f"📝 Plaintext length: {len(plaintext)} chars")
        print(f"📝 Plaintext preview: {plaintext[:100]}...")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'plaintext': plaintext,
            'plaintext_length': len(plaintext)
        })
        
    except Exception as e:
        print(f"❌ RSA Decrypt error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================================
# 📥 ENDPOINT: LSB HIDE (Menyembunyikan pesan ke gambar)
# ============================================================
@app.route('/api/lsb/hide', methods=['POST'])
def lsb_hide():
    try:
        data = request.json
        message = data.get('message', '')
        cover_base64 = data.get('cover_image', '')
        
        print("=" * 60)
        print("📥 LSB HIDE REQUEST")
        print("=" * 60)
        print(f"📝 Message length: {len(message)} chars")
        print(f"📝 Message preview: {message[:100]}...")
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not cover_base64:
            return jsonify({'error': 'Cover image is required'}), 400
        
        embed_id = uuid.uuid4().hex[:8]
        
        # Save cover image
        cover_data = base64.b64decode(cover_base64)
        cover_path = os.path.join(ORIGINAL_FOLDER, f'cover_{embed_id}.png')
        
        with open(cover_path, 'wb') as f:
            f.write(cover_data)
        
        # Validate image
        try:
            img = Image.open(cover_path)
            if img.mode not in ['RGB', 'RGBA']:
                img = img.convert('RGB')
                img.save(cover_path, format='PNG')
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Check capacity
        max_bytes = stego.get_capacity(cover_path)
        message_bytes = len(message.encode('utf-8'))
        print(f"📊 Capacity: {max_bytes} bytes, Message: {message_bytes} bytes")
        
        if message_bytes > max_bytes:
            return jsonify({
                'error': f'Message too long. Maximum {max_bytes} bytes, got {message_bytes} bytes'
            }), 400
        
        # Embed message into image
        stego_filename = f'stego_{embed_id}.png'
        stego_path = os.path.join(STEGO_FOLDER, stego_filename)
        
        print(f"📷 Embedding message into image...")
        stego.embed(cover_path, message, stego_path)
        print(f"✅ Embedding successful!")
        
        # Calculate metrics (hanya MSE dan PSNR)
        try:
            metrics = calculate_metrics(cover_path, stego_path)
        except Exception as e:
            metrics = {
                'psnr': 0,
                'mse': 0
            }
        
        # Read images as base64
        with open(stego_path, 'rb') as f:
            stego_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        with open(cover_path, 'rb') as f:
            original_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Cleanup
        try:
            os.remove(cover_path)
            os.remove(stego_path)
        except:
            pass
        
        print("✅ LSB Hide completed successfully")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'message': 'Pesan berhasil disembunyikan',
            'embed_id': embed_id,
            'stego_image': stego_base64,
            'original_image': original_base64,
            'stego_filename': stego_filename,
            'metrics': {
                'psnr': float(metrics['psnr']) if metrics['psnr'] != float('inf') else 100.0,
                'mse': float(metrics['mse'])
            },
            'capacity': {
                'max_bytes': max_bytes,
                'used_bytes': message_bytes,
                'usage_percent': (message_bytes / max_bytes * 100) if max_bytes > 0 else 0
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ LSB Hide error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================================
# 📤 ENDPOINT: LSB EXTRACT (Mengambil pesan dari gambar)
# ============================================================
@app.route('/api/lsb/extract', methods=['POST'])
def lsb_extract():
    try:
        data = request.json
        stego_base64 = data.get('stego_image', '')
        
        print("=" * 60)
        print("📤 LSB EXTRACT REQUEST")
        print("=" * 60)
        
        if not stego_base64:
            return jsonify({'error': 'Stego image is required'}), 400
        
        extract_id = uuid.uuid4().hex[:8]
        stego_path = os.path.join(STEGO_FOLDER, f'extract_{extract_id}.png')
        
        try:
            print(f"💾 Saving image to: {stego_path}")
            image_data = base64.b64decode(stego_base64)
            print(f"📊 Image data size: {len(image_data)} bytes")
            
            with open(stego_path, 'wb') as f:
                f.write(image_data)
            print("✅ Image saved successfully")
        except Exception as e:
            print(f"❌ Error saving image: {str(e)}")
            return jsonify({'error': f'Failed to save image: {str(e)}'}), 500
        
        try:
            print("🔍 Extracting message from image...")
            extracted_data = stego.extract(stego_path)
            print(f"📊 Extracted data length: {len(extracted_data) if extracted_data else 0}")
            
            if extracted_data:
                print(f"📝 Extracted data preview: {extracted_data[:100]}...")
                
                # ✅ CEK APAKAH DATA ADALAH BASE64 VALID
                try:
                    decoded = base64.b64decode(extracted_data)
                    print(f"📊 Decoded base64 length: {len(decoded)} bytes")
                    
                    # Cek apakah panjang decoded adalah 256 bytes (RSA-2048)
                    if len(decoded) == 256:
                        print("✅ Data appears to be valid RSA ciphertext (256 bytes)")
                    else:
                        print(f"⚠️ Data length is {len(decoded)} bytes, expected 256 for RSA-2048")
                        print("   Data may be corrupted or not RSA-encrypted")
                except Exception as e:
                    print(f"⚠️ Data is not valid base64: {str(e)}")
                    print("   Data may be plaintext or corrupted")
                    
        except Exception as e:
            print(f"❌ Extraction error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': f'Extraction failed: {str(e)}'}), 500
        
        # Cleanup
        try:
            os.remove(stego_path)
            print("🗑️ Temporary file deleted")
        except:
            pass
        
        if not extracted_data or 'No hidden message' in extracted_data or len(extracted_data) < 5:
            print("❌ No valid hidden message found")
            return jsonify({
                'success': False,
                'error': 'No hidden message found in this image',
                'extracted_data': extracted_data if extracted_data else None
            }), 400
        
        # 🔐 COBA DECRYPT JIKA DATA ADALAH CIPHERTEXT RSA
        plaintext = None
        is_encrypted = False
        decryption_error = None
        
        try:
            print("🔐 Attempting RSA decryption...")
            plaintext = rsa.decrypt(extracted_data)
            is_encrypted = True
            print(f"✅ RSA Decryption successful!")
            print(f"📝 Plaintext length: {len(plaintext)} chars")
            print(f"📝 Plaintext preview: {plaintext[:100]}...")
        except Exception as e:
            decryption_error = str(e)
            print(f"❌ RSA Decryption failed: {decryption_error}")
            print(f"ℹ️ Data is not RSA-encrypted (or invalid)")
            # Data mungkin plaintext biasa, bukan ciphertext
            plaintext = extracted_data
            is_encrypted = False
        
        print("✅ LSB Extract completed successfully")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'message': 'Pesan berhasil diekstrak',
            'extract_id': extract_id,
            'extracted_data': extracted_data,
            'extracted_length': len(extracted_data),
            'plaintext': plaintext,
            'plaintext_length': len(plaintext) if plaintext else 0,
            'is_encrypted': is_encrypted,
            'decryption_error': decryption_error,  # Tambahkan ini untuk debugging
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print("❌ LSB Extract error:")
        print(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================
# 📊 ENDPOINT: COMPARE IMAGES
# ============================================================
@app.route('/api/compare', methods=['POST'])
def compare_images():
    try:
        data = request.json
        original_base64 = data.get('original_image', '')
        stego_base64 = data.get('stego_image', '')
        
        if not original_base64 or not stego_base64:
            return jsonify({'error': 'Both images are required'}), 400
        
        compare_id = uuid.uuid4().hex[:8]
        original_path = os.path.join(ORIGINAL_FOLDER, f'compare_original_{compare_id}.png')
        stego_path = os.path.join(STEGO_FOLDER, f'compare_stego_{compare_id}.png')
        
        with open(original_path, 'wb') as f:
            f.write(base64.b64decode(original_base64))
        
        with open(stego_path, 'wb') as f:
            f.write(base64.b64decode(stego_base64))
        
        metrics = calculate_metrics(original_path, stego_path)
        
        try:
            os.remove(original_path)
            os.remove(stego_path)
        except:
            pass
        
        psnr = metrics['psnr']
        if psnr == float('inf'):
            quality = 'Sempurna'
        elif psnr > 50:
            quality = 'Sangat Baik'
        elif psnr > 40:
            quality = 'Baik'
        elif psnr > 30:
            quality = 'Cukup'
        else:
            quality = 'Buruk'
        
        return jsonify({
            'success': True,
            'metrics': {
                'psnr': float(metrics['psnr']) if metrics['psnr'] != float('inf') else 100.0,
                'mse': float(metrics['mse'])
            },
            'quality': {
                'category': quality,
                'description': f'PSNR: {metrics["psnr"]:.2f} dB - {quality}'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Compare error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================================
# 🔗 ENDPOINT: EMBED (Legacy - tetap dipertahankan untuk kompatibilitas)
# ============================================================
@app.route('/api/embed', methods=['POST'])
def embed_message():
    try:
        data = request.json
        plaintext = data.get('message', '')
        cover_base64 = data.get('cover_image', '')
        
        print(f"📝 Received message length: {len(plaintext)} chars")
        
        if not plaintext:
            return jsonify({'error': 'Message is required'}), 400
        
        if not cover_base64:
            return jsonify({'error': 'Cover image is required'}), 400
        
        embed_id = uuid.uuid4().hex[:8]
        
        # CEK: Apakah pesan berupa file reference?
        if plaintext.startswith('[FILE:'):
            print("📄 Processing document file...")
            filename = plaintext.replace('[FILE:', '').replace(']', '')
            
            if data.get('document_file'):
                try:
                    print(f"📄 Decoding document: {data.get('document_name', 'unknown')}")
                    doc_data = base64.b64decode(data.get('document_file'))
                    doc_name = data.get('document_name', 'document.pdf')
                    doc_path = os.path.join(DOCUMENTS_FOLDER, doc_name)
                    with open(doc_path, 'wb') as f:
                        f.write(doc_data)
                    
                    print(f"📄 Reading document: {doc_path}")
                    plaintext = read_document_file(doc_path)
                    print(f"📄 Document content length: {len(plaintext)} chars")
                    
                    try:
                        os.remove(doc_path)
                    except:
                        pass
                except Exception as e:
                    print(f"❌ Document processing error: {str(e)}")
                    return jsonify({'error': f'Failed to process document: {str(e)}'}), 400
            else:
                doc_path = os.path.join(DOCUMENTS_FOLDER, filename)
                if os.path.exists(doc_path):
                    plaintext = read_document_file(doc_path)
                    try:
                        os.remove(doc_path)
                    except:
                        pass
                else:
                    return jsonify({'error': f'Document {filename} not found'}), 400
        
        # Save cover image
        print(f"🖼️ Saving cover image...")
        cover_data = base64.b64decode(cover_base64)
        cover_filename = f'cover_{embed_id}.png'
        cover_path = os.path.join(ORIGINAL_FOLDER, cover_filename)
        
        with open(cover_path, 'wb') as f:
            f.write(cover_data)
        
        try:
            img = Image.open(cover_path)
            if img.mode not in ['RGB', 'RGBA']:
                img = img.convert('RGB')
                img.save(cover_path, format='PNG')
        except Exception as e:
            return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
        
        # Check capacity
        max_chars = stego.get_capacity(cover_path)
        print(f"📊 Image capacity: {max_chars} bytes, message: {len(plaintext)} bytes")

        if len(plaintext.encode('utf-8')) > max_chars:
            return jsonify({
                'error': f'Message too long. Maximum {max_chars} bytes, got {len(plaintext.encode("utf-8"))} bytes'
            }), 400
        
        # Encrypt with RSA
        print(f"🔐 Encrypting message with RSA...")
        try:
            ciphertext = rsa.encrypt(plaintext)
            print(f"🔐 Ciphertext length: {len(ciphertext)} chars")
        except Exception as e:
            print(f"❌ Encryption error: {str(e)}")
            return jsonify({'error': f'Encryption failed: {str(e)}'}), 500
        
        # Embed into image
        stego_filename = f'stego_{embed_id}.png'
        stego_path = os.path.join(STEGO_FOLDER, stego_filename)
        
        print(f"📷 Embedding ciphertext into image...")
        try:
            stego.embed(cover_path, ciphertext, stego_path)
            print(f"✅ Embedding successful!")
        except Exception as e:
            print(f"❌ Embedding error: {str(e)}")
            return jsonify({'error': f'Embedding failed: {str(e)}'}), 500
        
        # Calculate metrics (hanya MSE dan PSNR)
        try:
            metrics = calculate_metrics(cover_path, stego_path)
        except Exception as e:
            metrics = {
                'psnr': 0,
                'mse': 0
            }
        
        with open(stego_path, 'rb') as f:
            stego_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        with open(cover_path, 'rb') as f:
            original_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'message': 'Pesan berhasil disembunyikan',
            'embed_id': embed_id,
            'ciphertext': ciphertext,
            'ciphertext_length': len(ciphertext),
            'plaintext_length': len(plaintext),
            'stego_image': stego_base64,
            'original_image': original_base64,
            'stego_filename': stego_filename,
            'cover_filename': cover_filename,
            'metrics': {
                'psnr': float(metrics['psnr']) if metrics['psnr'] != float('inf') else 100.0,
                'mse': float(metrics['mse'])
            },
            'capacity': {
                'max_chars': max_chars,
                'used_chars': len(plaintext),
                'usage_percent': (len(plaintext) / max_chars * 100) if max_chars > 0 else 0
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ UNHANDLED ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================================
# 🔗 ENDPOINT: EXTRACT (Legacy - tetap dipertahankan untuk kompatibilitas)
# ============================================================
@app.route('/api/extract', methods=['POST'])
def extract_message():
    try:
        data = request.json
        stego_base64 = data.get('stego_image', '')
        
        print("=" * 60)
        print("🔍 EXTRACT REQUEST RECEIVED")
        print("=" * 60)
        
        if not stego_base64:
            print("❌ No stego image provided")
            return jsonify({'error': 'Stego image is required'}), 400
        
        extract_id = uuid.uuid4().hex[:8]
        stego_path = os.path.join(STEGO_FOLDER, f'extract_{extract_id}.png')
        
        try:
            print(f"💾 Saving image to: {stego_path}")
            image_data = base64.b64decode(stego_base64)
            print(f"📊 Image data size: {len(image_data)} bytes")
            
            with open(stego_path, 'wb') as f:
                f.write(image_data)
            print("✅ Image saved successfully")
        except Exception as e:
            print(f"❌ Error saving image: {str(e)}")
            return jsonify({'error': f'Failed to save image: {str(e)}'}), 500
        
        try:
            print("🔍 Extracting ciphertext from image...")
            ciphertext = stego.extract(stego_path)
            print(f"📊 Extracted ciphertext length: {len(ciphertext) if ciphertext else 0}")
            
            if ciphertext:
                print(f"📝 Ciphertext preview: {ciphertext[:50]}...")
        except Exception as e:
            print(f"❌ Extraction error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': f'Extraction failed: {str(e)}'}), 500
        
        if not ciphertext or 'No hidden message' in ciphertext or len(ciphertext) < 5:
            print("❌ No valid hidden message found")
            return jsonify({
                'success': False,
                'error': 'No hidden message found in this image',
                'extracted_data': ciphertext if ciphertext else None
            }), 400
        
        try:
            print("🔐 Decrypting ciphertext with RSA...")
            plaintext = rsa.decrypt(ciphertext)
            print(f"✅ Decryption successful!")
            print(f"📝 Plaintext length: {len(plaintext)} chars")
            print(f"📝 Plaintext preview: {plaintext[:100]}...")
        except Exception as e:
            print(f"❌ Decryption error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Decryption failed: {str(e)}',
                'ciphertext': ciphertext[:100] + '...' if len(ciphertext) > 100 else ciphertext
            }), 500
        
        try:
            os.remove(stego_path)
            print("🗑️ Temporary file deleted")
        except:
            pass
        
        print("✅ Extraction completed successfully")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'message': 'Pesan berhasil diekstrak dan didekripsi',
            'extract_id': extract_id,
            'ciphertext': ciphertext,
            'ciphertext_length': len(ciphertext),
            'plaintext': plaintext,
            'plaintext_length': len(plaintext),
            'stego_image': stego_base64,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print("❌ UNHANDLED ERROR:")
        print(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ============================================================
# 📄 ENDPOINT: EXTRACT DOCUMENT CONTENT
# ============================================================
@app.route('/api/extract/document', methods=['POST'])
def extract_document():
    """Ekstrak konten dari dokumen yang diupload (TXT, PDF, DOCX)"""
    try:
        data = request.json
        document_base64 = data.get('document', '')
        filename = data.get('filename', 'document.txt')
        
        if not document_base64:
            return jsonify({'error': 'Document is required'}), 400
        
        extract_id = uuid.uuid4().hex[:8]
        doc_path = os.path.join(DOCUMENTS_FOLDER, f'extract_{extract_id}_{filename}')
        
        # Save document
        with open(doc_path, 'wb') as f:
            f.write(base64.b64decode(document_base64))
        
        # Extract content
        content = read_document_file(doc_path)
        
        # Cleanup
        try:
            os.remove(doc_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'content': content,
            'length': len(content),
            'filename': filename
        })
        
    except Exception as e:
        print(f"❌ Document extraction error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    

# ============================================================
# 📄 ENDPOINT: DOWNLOAD EXTRACTED CONTENT AS PDF
# ============================================================
@app.route('/api/download/pdf', methods=['POST'])
def download_pdf():
    """Download extracted content as PDF file"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
        from reportlab.lib import colors
        import io
        
        data = request.json
        content = data.get('content', '')
        filename = data.get('filename', 'extracted.pdf')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        # Sanitize filename - pastikan .pdf
        if not filename.endswith('.pdf'):
            filename = filename.rsplit('.', 1)[0] + '.pdf' if '.' in filename else filename + '.pdf'
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom style for content
        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        # Title style
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#1a1a2e')
        )
        
        # Build PDF content
        story = []
        
        # Add header
        story.append(Paragraph("📄 Extracted Document", title_style))
        story.append(Spacer(1, 12))
        
        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%d %B %Y, %H:%M:%S")
        timestamp_style = ParagraphStyle(
            'TimestampStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            alignment=TA_LEFT,
            spaceAfter=12
        )
        story.append(Paragraph(f"<i>Diekstrak pada: {timestamp}</i>", timestamp_style))
        story.append(Spacer(1, 8))
        
        # Add separator line
        story.append(Paragraph("─" * 80, styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Process content - split by lines
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                # Escape special characters for HTML
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(escaped_line, content_style))
            else:
                story.append(Spacer(1, 6))
        
        # Add footer
        story.append(Spacer(1, 20))
        story.append(Paragraph("─" * 80, styles['Normal']))
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#a0aec0'),
            alignment=TA_CENTER,
            spaceAfter=6
        )
        story.append(Paragraph("Dokumen ini dihasilkan dari ekstraksi LSB Steganography", footer_style))
        story.append(Paragraph(f"Total {len(content)} karakter", footer_style))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Return PDF as base64
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'pdf': pdf_base64,
            'filename': filename,
            'content_length': len(content)
        })
        
    except ImportError as e:
        print(f"❌ ReportLab not installed: {str(e)}")
        return jsonify({
            'error': 'Library reportlab tidak terinstall. Install dengan: pip install reportlab'
        }), 500
    except Exception as e:
        print(f"❌ PDF generation error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ============================================================
# 📄 ENDPOINT: DOWNLOAD EXTRACTED CONTENT (Legacy)
# ============================================================
@app.route('/api/download/content', methods=['POST'])
def download_content():
    """Download extracted content as file (legacy - redirect to PDF)"""
    try:
        data = request.json
        content = data.get('content', '')
        filename = data.get('filename', 'extracted.pdf')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        # Always use PDF
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib import colors
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        
        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=6,
            fontName='Helvetica'
        )
        
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#1a1a2e')
        )
        
        story = []
        story.append(Paragraph("📄 Extracted Document", title_style))
        story.append(Spacer(1, 12))
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%d %B %Y, %H:%M:%S")
        timestamp_style = ParagraphStyle(
            'TimestampStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#718096'),
            alignment=TA_LEFT,
            spaceAfter=12
        )
        story.append(Paragraph(f"<i>Diekstrak pada: {timestamp}</i>", timestamp_style))
        story.append(Spacer(1, 8))
        story.append(Paragraph("─" * 80, styles['Normal']))
        story.append(Spacer(1, 12))
        
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(escaped_line, content_style))
            else:
                story.append(Spacer(1, 6))
        
        story.append(Spacer(1, 20))
        story.append(Paragraph("─" * 80, styles['Normal']))
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#a0aec0'),
            alignment=TA_CENTER,
            spaceAfter=6
        )
        story.append(Paragraph("Dokumen ini dihasilkan dari ekstraksi LSB Steganography", footer_style))
        story.append(Paragraph(f"Total {len(content)} karakter", footer_style))
        
        doc.build(story)
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'pdf': pdf_base64,
            'filename': filename if filename.endswith('.pdf') else filename + '.pdf',
            'content_length': len(content)
        })
        
    except ImportError:
        return jsonify({'error': 'Library reportlab tidak terinstall. Install dengan: pip install reportlab'}), 500
    except Exception as e:
        print(f"❌ Download content error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    
# ============================================================
# 🏥 ENDPOINT: HEALTH CHECK
# ============================================================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'OK',
        'service': 'Hybrid Cryptosystem RSA-LSB',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


# ============================================================
# 🚀 MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🔐 HYBRID CRYPTOSYSTEM RSA-LSB")
    print("=" * 60)
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 Original folder: {ORIGINAL_FOLDER}")
    print(f"📁 Stego folder: {STEGO_FOLDER}")
    print(f"📁 Documents folder: {DOCUMENTS_FOLDER}")
    print(f"🔑 RSA Key Size: 2048 bits")
    print(f"🔑 Algorithm: RSA-OAEP with SHA-256")
    print("=" * 60)
    print("🚀 Server running on http://localhost:5000")
    print("📱 Open in browser: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)