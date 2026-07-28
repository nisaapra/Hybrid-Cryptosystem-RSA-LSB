// ============================================================
// SECURE MESSAGE APPLICATION - SCRIPT
// RSA & LSB Modules Separated
// ============================================================

const API_BASE = '/api';

// State
let currentStegoImage = null;
let currentOriginalImage = null;
let currentRsaCiphertext = '';

// ============================================================
// TOAST NOTIFICATION
// ============================================================
function showToast(message, type = 'info') {
    document.querySelectorAll('.toast').forEach(t => t.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================
// FILE HANDLING
// ============================================================
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// ============================================================
// DOM READY
// ============================================================
document.addEventListener('DOMContentLoaded', function() {

    console.log('🚀 Secure Message Application started');

    // ============================================================
    // SIDEBAR NAVIGATION
    // ============================================================
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabPanels = {
        rsa: document.getElementById('rsa'),
        lsb: document.getElementById('lsb'),
        keys: document.getElementById('keys')
    };
    
    navBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            
            navBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const tabId = this.dataset.tab;
            Object.keys(tabPanels).forEach(key => {
                if (tabPanels[key]) {
                    tabPanels[key].classList.toggle('active', key === tabId);
                }
            });
        });
    });

    // ============================================================
// RSA - INPUT MODE TOGGLE (Manual / Dokumen)
// ============================================================
const modeManualBtn = document.getElementById('mode-manual-btn');
const modeDocumentBtn = document.getElementById('mode-document-btn');
const rsaManualMode = document.getElementById('rsa-manual-mode');
const rsaDocumentMode = document.getElementById('rsa-document-mode');

let rsaInputMode = 'manual'; // 'manual' | 'document'
let rsaDocumentContent = '';

if (modeManualBtn && modeDocumentBtn) {
    modeManualBtn.addEventListener('click', function() {
        this.classList.add('active');
        modeDocumentBtn.classList.remove('active');
        rsaManualMode.classList.add('active');
        rsaDocumentMode.classList.remove('active');
        rsaInputMode = 'manual';
    });
    
    modeDocumentBtn.addEventListener('click', function() {
        this.classList.add('active');
        modeManualBtn.classList.remove('active');
        rsaDocumentMode.classList.add('active');
        rsaManualMode.classList.remove('active');
        rsaInputMode = 'document';
    });
}

// ============================================================
// RSA - UPLOAD DOKUMEN
// ============================================================
const rsaDocInput = document.getElementById('rsa-document-input');
const rsaDocFilename = document.getElementById('rsa-doc-filename');
const rsaDocPreviewContainer = document.getElementById('rsa-doc-preview-container');
const rsaDocRemoveBtn = document.getElementById('rsa-doc-remove');
const rsaDocContentText = document.getElementById('rsa-doc-content-text');
const rsaDocContentPreview = document.getElementById('rsa-doc-content-preview');

// Fungsi untuk membaca isi dokumen
async function readDocumentContent(file) {
    const fileExt = file.name.split('.').pop().toLowerCase();
    
    if (fileExt === 'txt') {
        // Baca sebagai text
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = reject;
            reader.readAsText(file);
        });
    } else if (fileExt === 'pdf') {
        // PDF - kirim ke server untuk ekstraksi
        const base64 = await fileToBase64(file);
        const response = await fetch(`${API_BASE}/extract/document`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                document: base64,
                filename: file.name
            })
        });
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        return data.content;
    } else if (['docx', 'doc'].includes(fileExt)) {
        // DOCX - kirim ke server untuk ekstraksi
        const base64 = await fileToBase64(file);
        const response = await fetch(`${API_BASE}/extract/document`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                document: base64,
                filename: file.name
            })
        });
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        return data.content;
    } else {
        throw new Error(`Format file ${fileExt} tidak didukung`);
    }
}

if (rsaDocInput) {
    rsaDocInput.addEventListener('change', async function(e) {
        const file = this.files[0];
        if (!file) {
            rsaDocPreviewContainer.classList.add('hidden');
            rsaDocContentPreview.classList.add('hidden');
            rsaDocumentContent = '';
            return;
        }
        
        rsaDocFilename.textContent = file.name;
        rsaDocPreviewContainer.classList.remove('hidden');
        rsaDocContentPreview.classList.add('hidden');
        rsaDocumentContent = '';
        
        try {
            showToast('📖 Membaca isi dokumen...', 'info');
            const content = await readDocumentContent(file);
            rsaDocumentContent = content;
            
            // Tampilkan preview konten
            rsaDocContentText.textContent = content.length > 500 
                ? content.substring(0, 500) + '\n... (klik Encrypt untuk memproses semua)' 
                : content;
            rsaDocContentPreview.classList.remove('hidden');
            
            showToast(`✅ Dokumen berhasil dibaca (${content.length} karakter)`, 'success');
            
            // Update char counter
            document.getElementById('rsa-char-count').textContent = content.length;
            
        } catch (error) {
            console.error('Error reading document:', error);
            showToast('❌ Gagal membaca dokumen: ' + error.message, 'error');
            rsaDocumentContent = '';
        }
    });
}

if (rsaDocRemoveBtn) {
    rsaDocRemoveBtn.addEventListener('click', function() {
        rsaDocInput.value = '';
        rsaDocPreviewContainer.classList.add('hidden');
        rsaDocContentPreview.classList.add('hidden');
        rsaDocumentContent = '';
        document.getElementById('rsa-char-count').textContent = '0';
    });
}

// ============================================================
// MODIFIKASI: RSA Encrypt - Dukung Manual & Dokumen
// ============================================================
const rsaEncryptBtnOriginal = document.getElementById('rsa-encrypt-btn');
if (rsaEncryptBtnOriginal) {
    // Ganti event listener yang lama
    const newEncryptBtn = rsaEncryptBtnOriginal.cloneNode(true);
    rsaEncryptBtnOriginal.parentNode.replaceChild(newEncryptBtn, rsaEncryptBtnOriginal);
    
    newEncryptBtn.addEventListener('click', async function() {
        let plaintext = '';
        
        if (rsaInputMode === 'manual') {
            plaintext = document.getElementById('rsa-plaintext').value.trim();
        } else {
            plaintext = rsaDocumentContent;
        }
        
        if (!plaintext) {
            if (rsaInputMode === 'manual') {
                showToast('❌ Silakan masukkan teks untuk dienkripsi!', 'error');
            } else {
                showToast('❌ Silakan upload dokumen terlebih dahulu!', 'error');
            }
            return;
        }
        
        const btn = this;
        btn.textContent = '⏳ Encrypting...';
        btn.disabled = true;
        
        try {
            const response = await fetch(`${API_BASE}/rsa/encrypt`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plaintext: plaintext })
            });
            
            const data = await response.json();
            
            if (data.error) {
                showToast('❌ ' + data.error, 'error');
                return;
            }
            
            document.getElementById('rsa-ciphertext-display').textContent = data.ciphertext;
            currentRsaCiphertext = data.ciphertext;
            document.getElementById('rsa-encrypt-result').classList.remove('hidden');
            showToast('✅ Enkripsi berhasil!', 'success');
            
        } catch (error) {
            console.error('Error:', error);
            showToast('❌ Error: ' + error.message, 'error');
        } finally {
            btn.textContent = '🔒 Encrypt';
            btn.disabled = false;
        }
    });
}
    // ============================================================
    // ============================================================
    // MODUL 1: RSA CRYPTOGRAPHY
    // ============================================================
    // ============================================================

    // Generate Keys
    const generateKeysBtn = document.getElementById('generate-keys-btn');
    const keysStatus = document.getElementById('keys-status');
    
    if (generateKeysBtn) {
        generateKeysBtn.addEventListener('click', async function() {
            const btn = this;
            btn.textContent = '⏳ Generating...';
            btn.disabled = true;
            keysStatus.textContent = 'Sedang membuat kunci...';
            
            try {
                const response = await fetch(`${API_BASE}/keys`);
                const data = await response.json();
                
                if (data.public_key) {
                    document.getElementById('public-key-display').textContent = data.public_key;
                    document.getElementById('private-key-display').textContent = data.private_key;
                    keysStatus.textContent = '✅ Kunci berhasil dibuat!';
                    showToast('✅ RSA Keys generated successfully!', 'success');
                } else {
                    keysStatus.textContent = '❌ Gagal membuat kunci';
                    showToast('❌ Failed to generate keys', 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                keysStatus.textContent = '❌ Error: ' + error.message;
                showToast('❌ Error generating keys', 'error');
            } finally {
                btn.textContent = '🔑 Generate Keys';
                btn.disabled = false;
            }
        });
    }

    // RSA Encrypt
    const rsaEncryptBtn = document.getElementById('rsa-encrypt-btn');
    const rsaPlaintext = document.getElementById('rsa-plaintext');
    const rsaCiphertextDisplay = document.getElementById('rsa-ciphertext-display');
    const rsaEncryptResult = document.getElementById('rsa-encrypt-result');

    if (rsaEncryptBtn) {
        rsaEncryptBtn.addEventListener('click', async function() {
            const plaintext = rsaPlaintext.value.trim();
            
            if (!plaintext) {
                showToast('Silakan masukkan teks untuk dienkripsi!', 'error');
                return;
            }
            
            const btn = this;
            btn.textContent = '⏳ Encrypting...';
            btn.disabled = true;
            
            try {
                const response = await fetch(`${API_BASE}/rsa/encrypt`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plaintext: plaintext })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showToast('❌ ' + data.error, 'error');
                    return;
                }
                
                rsaCiphertextDisplay.textContent = data.ciphertext;
                currentRsaCiphertext = data.ciphertext;
                rsaEncryptResult.classList.remove('hidden');
                showToast('✅ Enkripsi berhasil!', 'success');
                
            } catch (error) {
                console.error('Error:', error);
                showToast('❌ Error: ' + error.message, 'error');
            } finally {
                btn.textContent = '🔒 Encrypt';
                btn.disabled = false;
            }
        });
    }

    // RSA Decrypt
    const rsaDecryptBtn = document.getElementById('rsa-decrypt-btn');
    const rsaCiphertextInput = document.getElementById('rsa-ciphertext-input');
    const rsaPlaintextDisplay = document.getElementById('rsa-plaintext-display');
    const rsaDecryptResult = document.getElementById('rsa-decrypt-result');

    if (rsaDecryptBtn) {
        rsaDecryptBtn.addEventListener('click', async function() {
            const ciphertext = rsaCiphertextInput.value.trim() || currentRsaCiphertext;
            
            if (!ciphertext) {
                showToast('Silakan masukkan ciphertext untuk didekripsi!', 'error');
                return;
            }
            
            const btn = this;
            btn.textContent = '⏳ Decrypting...';
            btn.disabled = true;
            
            try {
                const response = await fetch(`${API_BASE}/rsa/decrypt`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ciphertext: ciphertext })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showToast('❌ ' + data.error, 'error');
                    return;
                }
                
                rsaPlaintextDisplay.textContent = data.plaintext;
                rsaDecryptResult.classList.remove('hidden');
                showToast('✅ Dekripsi berhasil!', 'success');
                
            } catch (error) {
                console.error('Error:', error);
                showToast('❌ Error: ' + error.message, 'error');
            } finally {
                btn.textContent = '🔓 Decrypt';
                btn.disabled = false;
            }
        });
    }

    // Copy RSA Ciphertext
    const copyRsaCipherBtn = document.getElementById('copy-rsa-cipher-btn');
    if (copyRsaCipherBtn) {
        copyRsaCipherBtn.addEventListener('click', function() {
            const text = rsaCiphertextDisplay.textContent;
            if (text && text !== '-') {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('✅ Ciphertext copied!', 'success');
                }).catch(() => {
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    showToast('✅ Ciphertext copied!', 'success');
                });
            }
        });
    }

// ============================================================
// MODUL 2: LSB STEGANOGRAPHY
// ============================================================

// --- COVER IMAGE ---
const coverImageInput = document.getElementById('cover-image');
const coverFilename = document.getElementById('cover-filename');
const coverPreviewContainer = document.getElementById('cover-preview-container');
const coverPreview = document.getElementById('cover-preview');
const capacityInfo = document.getElementById('capacity-info');
const coverRemoveBtn = document.getElementById('cover-remove');
const maxCharsSpan = document.getElementById('max-chars');

if (coverImageInput) {
    coverImageInput.addEventListener('change', function(e) {
        const file = this.files[0];
        if (!file) {
            coverPreviewContainer.classList.add('hidden');
            capacityInfo.classList.add('hidden');
            return;
        }
        
        coverFilename.textContent = file.name;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            coverPreview.src = e.target.result;
            coverPreviewContainer.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
        
        capacityInfo.classList.remove('hidden');
        maxCharsSpan.textContent = 'Menghitung...';
        
        (async function() {
            try {
                const base64 = await fileToBase64(file);
                const response = await fetch(`${API_BASE}/capacity`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: base64 })
                });
                const data = await response.json();
                if (data.capacity) {
                    maxCharsSpan.textContent = data.capacity;
                }
            } catch (error) {
                console.error('Capacity error:', error);
                maxCharsSpan.textContent = 'Gagal menghitung';
            }
        })();
    });
}

if (coverRemoveBtn) {
    coverRemoveBtn.addEventListener('click', function() {
        coverImageInput.value = '';
        coverPreviewContainer.classList.add('hidden');
        capacityInfo.classList.add('hidden');
        document.getElementById('lsb-hide-result').classList.add('hidden');
    });
}

// --- LSB Message Input ---
const lsbMessageInput = document.getElementById('lsb-message');
const lsbCharCount = document.getElementById('lsb-char-count');
if (lsbMessageInput && lsbCharCount) {
    lsbMessageInput.addEventListener('input', function() {
        lsbCharCount.textContent = this.value.length;
    });
}

// ============================================================
// 🔄 FUNGSI BARU: Ambil ciphertext dari hasil RSA encrypt
// ============================================================
function getLatestCiphertext() {
    const ciphertextDisplay = document.getElementById('rsa-ciphertext-display');
    if (ciphertextDisplay && ciphertextDisplay.textContent && ciphertextDisplay.textContent !== '-') {
        return ciphertextDisplay.textContent;
    }
    return null;
}

// ============================================================
// 🔄 FUNGSI BARU: Isi otomatis message input dengan ciphertext
// ============================================================
function fillMessageWithCiphertext() {
    const ciphertext = getLatestCiphertext();
    if (ciphertext) {
        lsbMessageInput.value = ciphertext;
        lsbCharCount.textContent = ciphertext.length;
        showToast('✅ Ciphertext dari RSA telah diisi otomatis!', 'success');
    } else {
        showToast('⚠️ Silakan enkripsi pesan terlebih dahulu di tab RSA', 'info');
    }
}

// --- Tombol "Ambil Ciphertext dari RSA" ---
const useRsaCipherBtn = document.getElementById('use-rsa-cipher-btn');
if (useRsaCipherBtn) {
    useRsaCipherBtn.addEventListener('click', fillMessageWithCiphertext);
}

// --- LSB Hide Message ---
const lsbHideBtn = document.getElementById('lsb-hide-btn');
const lsbHideResult = document.getElementById('lsb-hide-result');
const lsbStegoPreview = document.getElementById('lsb-stego-preview');
const lsbDownloadBtn = document.getElementById('lsb-download-btn');
const lsbCompareBtn = document.getElementById('lsb-compare-btn');

if (lsbHideBtn) {
    lsbHideBtn.addEventListener('click', async function() {
        // Ambil ciphertext dari input (bisa dari RSA atau manual)
        let message = lsbMessageInput.value.trim();
        const coverFile = coverImageInput.files[0];
        
        // Jika kosong, coba ambil dari hasil RSA encrypt
        if (!message) {
            const cipherFromRSA = getLatestCiphertext();
            if (cipherFromRSA) {
                message = cipherFromRSA;
                lsbMessageInput.value = message;
                lsbCharCount.textContent = message.length;
                showToast('✅ Menggunakan ciphertext dari RSA', 'info');
            }
        }
        
        if (!message) {
            showToast('❌ Silakan masukkan ciphertext atau enkripsi pesan dulu di tab RSA!', 'error');
            return;
        }
        
        if (!coverFile) {
            showToast('❌ Silakan pilih gambar penampung!', 'error');
            return;
        }
        
        const btn = this;
        btn.textContent = '⏳ Processing...';
        btn.disabled = true;
        
        try {
            const coverBase64 = await fileToBase64(coverFile);
            
            const response = await fetch(`${API_BASE}/lsb/hide`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    cover_image: coverBase64
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                showToast('❌ ' + data.error, 'error');
                return;
            }
            
            // Tampilkan hasil
            lsbStegoPreview.src = `data:image/png;base64,${data.stego_image}`;
            currentStegoImage = data.stego_image;
            currentOriginalImage = data.original_image;
            lsbHideResult.classList.remove('hidden');
            
            // Simpan ciphertext yang diembed untuk referensi
            currentRsaCiphertext = message;
            
            // Metrics
            if (data.metrics) {
                document.getElementById('lsb-mse').textContent = data.metrics.mse.toFixed(4);
                document.getElementById('lsb-psnr').textContent = data.metrics.psnr.toFixed(2);
            }
            
            showToast('✅ Ciphertext berhasil disembunyikan dalam gambar!', 'success');
            
        } catch (error) {
            console.error('Error:', error);
            showToast('❌ Error: ' + error.message, 'error');
        } finally {
            btn.textContent = '📥 Hide Message';
            btn.disabled = false;
        }
    });
}

// --- LSB Download ---
if (lsbDownloadBtn) {
    lsbDownloadBtn.addEventListener('click', function() {
        if (currentStegoImage) {
            const link = document.createElement('a');
            link.download = `stego_${Date.now()}.png`;
            link.href = `data:image/png;base64,${currentStegoImage}`;
            link.click();
            showToast('✅ Image downloaded!', 'success');
        }
    });
}

// --- LSB Compare ---
if (lsbCompareBtn) {
    lsbCompareBtn.addEventListener('click', async function() {
        if (!currentOriginalImage || !currentStegoImage) {
            showToast('❌ Tidak ada gambar untuk dibandingkan!', 'error');
            return;
        }
        
        const btn = this;
        btn.textContent = '⏳...';
        btn.disabled = true;
        
        try {
            const response = await fetch(`${API_BASE}/compare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_image: currentOriginalImage,
                    stego_image: currentStegoImage
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                showToast('❌ ' + data.error, 'error');
                return;
            }
            
            const metrics = data.metrics;
            const quality = data.quality;
            
            let msg = '📊 HASIL PERBANDINGAN CITRA\n';
            msg += '═'.repeat(40) + '\n';
            msg += `MSE: ${metrics.mse.toFixed(4)}\n`;
            msg += `PSNR: ${metrics.psnr.toFixed(2)} dB\n`;
            msg += `MAE: ${metrics.mae.toFixed(4)}\n`;
            msg += '═'.repeat(40) + '\n';
            msg += `Kualitas: ${quality.category}\n`;
            msg += `Imperceptibility: ${quality.imperceptibility_level}\n`;
            
            alert(msg);
            showToast('✅ Perbandingan selesai!', 'success');
            
        } catch (error) {
            showToast('❌ Error: ' + error.message, 'error');
        } finally {
            btn.textContent = '📊 Bandingkan';
            btn.disabled = false;
        }
    });
}

// ============================================================
// LSB EXTRACT - Dengan Download Dokumen
// ============================================================
const stegoImageInput = document.getElementById('stego-image');
const stegoFilename = document.getElementById('stego-filename');
const stegoPreviewContainer = document.getElementById('stego-preview-container');
const stegoPreviewImg = document.getElementById('extract-preview-img');
const stegoRemoveBtn = document.getElementById('stego-remove');
const lsbExtractBtn = document.getElementById('lsb-extract-btn');
const lsbExtractResult = document.getElementById('lsb-extract-result');
const lsbExtractEmpty = document.getElementById('lsb-extract-empty');
const extractedMessageDisplay = document.getElementById('extracted-message-display');
const extractedMsgLen = document.getElementById('extracted-msg-len');
const extractedDownloadBtn = document.getElementById('extracted-download-btn');
const extractedCopyBtn = document.getElementById('extracted-copy-btn');

let lastExtractedContent = '';
let lastExtractedFilename = 'extracted.txt';

if (stegoImageInput) {
    stegoImageInput.addEventListener('change', function(e) {
        const file = this.files[0];
        if (!file) {
            stegoPreviewContainer.classList.add('hidden');
            return;
        }
        
        stegoFilename.textContent = file.name;
        const reader = new FileReader();
        reader.onload = function(e) {
            stegoPreviewImg.src = e.target.result;
            stegoPreviewContainer.classList.remove('hidden');
            lsbExtractEmpty.classList.add('hidden');
            lsbExtractResult.classList.add('hidden');
            // Reset extracted content
            lastExtractedContent = '';
        };
        reader.readAsDataURL(file);
    });
}

if (stegoRemoveBtn) {
    stegoRemoveBtn.addEventListener('click', function() {
        stegoImageInput.value = '';
        stegoPreviewContainer.classList.add('hidden');
        lsbExtractResult.classList.add('hidden');
        lsbExtractEmpty.classList.remove('hidden');
        extractedMessageDisplay.textContent = '';
        extractedMsgLen.textContent = '0';
        document.getElementById('extracted-cipher-container').classList.add('hidden');
        lastExtractedContent = '';
    });
}

// Fungsi untuk mendownload konten sebagai PDF
async function downloadExtractedContent(content, filename) {
    try {
        // Kirim ke server untuk generate PDF
        const response = await fetch(`${API_BASE}/download/content`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                content: content,
                filename: filename || 'extracted.pdf'
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showToast('❌ ' + data.error, 'error');
            return;
        }
        
        // Download PDF
        const link = document.createElement('a');
        link.download = data.filename;
        link.href = `data:application/pdf;base64,${data.pdf}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast(`✅ PDF "${data.filename}" berhasil didownload!`, 'success');
        
    } catch (error) {
        console.error('Download error:', error);
        showToast('❌ Gagal mendownload PDF: ' + error.message, 'error');
    }
}

// Download extracted content sebagai PDF
if (extractedDownloadBtn) {
    extractedDownloadBtn.addEventListener('click', function() {
        if (!lastExtractedContent) {
            showToast('❌ Tidak ada konten untuk didownload!', 'error');
            return;
        }
        
        // Tanyakan nama file ke user (default .pdf)
        const defaultName = lastExtractedFilename.replace(/\.[^.]+$/, '') + '.pdf';
        const userFilename = prompt('Masukkan nama file PDF:', defaultName);
        if (userFilename === null) return; // User membatalkan
        
        let finalFilename = userFilename.trim();
        if (!finalFilename) finalFilename = defaultName;
        if (!finalFilename.endsWith('.pdf')) finalFilename += '.pdf';
        
        downloadExtractedContent(lastExtractedContent, finalFilename);
    });
}
if (lsbExtractBtn) {
    lsbExtractBtn.addEventListener('click', async function() {
        const stegoFile = stegoImageInput.files[0];
        
        if (!stegoFile) {
            showToast('❌ Silakan pilih gambar stego!', 'error');
            return;
        }
        
        const btn = this;
        btn.textContent = '⏳ Extracting...';
        btn.disabled = true;
        
        try {
            const stegoBase64 = await fileToBase64(stegoFile);
            
            const response = await fetch(`${API_BASE}/lsb/extract`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stego_image: stegoBase64
                })
            });
            
            const data = await response.json();
            console.log('📥 Extract response:', data);
            
            // ✅ CEK STATUS RESPONSE DULU
            if (!response.ok) {
                const errorMsg = data.error || data.message || 'Gagal mengekstrak pesan';
                showToast('❌ ' + errorMsg, 'error');
                console.error('Extract error:', data);
                return;
            }
            
            if (data.error) {
                showToast('❌ ' + data.error, 'error');
                return;
            }
            
            if (!data.success) {
                showToast('❌ ' + (data.error || 'Gagal ekstrak'), 'error');
                return;
            }
            
            // ✅ TAMPILKAN HASIL
            lsbExtractResult.classList.remove('hidden');
            lsbExtractEmpty.classList.add('hidden');
            
            // ✅ Jika ada error decryption, tampilkan peringatan
            if (data.decryption_error) {
                console.warn('⚠️ Decryption error:', data.decryption_error);
                showToast('⚠️ Data tidak bisa didekripsi (kemungkinan RSA key berbeda)', 'info');
            }
            
            // Tampilkan plaintext
            const displayText = data.plaintext || data.message || 'Tidak ada pesan';
            extractedMessageDisplay.textContent = displayText;
            extractedMsgLen.textContent = displayText.length;
            
            // Simpan untuk download
            lastExtractedContent = displayText;
            
            // Tampilkan info apakah terenkripsi
            if (data.is_encrypted) {
                document.getElementById('extracted-encrypted-badge')?.classList.remove('hidden');
                showToast('✅ Pesan berhasil diekstrak dan didekripsi!', 'success');
            } else {
                document.getElementById('extracted-encrypted-badge')?.classList.add('hidden');
                if (data.extracted_data && data.extracted_data.length > 0) {
                    showToast('📝 Pesan diekstrak (tidak terenkripsi)', 'info');
                }
            }
            
            // Tampilkan ciphertext
            const extractedCipherDisplay = document.getElementById('extracted-cipher-display');
            if (extractedCipherDisplay && data.extracted_data) {
                extractedCipherDisplay.textContent = data.extracted_data;
                document.getElementById('extracted-cipher-container').classList.remove('hidden');
            }
            
        } catch (error) {
            console.error('❌ Extract error:', error);
            showToast('❌ Error: ' + error.message, 'error');
        } finally {
            btn.textContent = '🔍 Extract Message';
            btn.disabled = false;
        }
    });
}

// Download extracted content
if (extractedDownloadBtn) {
    extractedDownloadBtn.addEventListener('click', function() {
        if (!lastExtractedContent) {
            showToast('❌ Tidak ada konten untuk didownload!', 'error');
            return;
        }
        
        // Tanyakan nama file ke user
        const userFilename = prompt('Masukkan nama file:', lastExtractedFilename);
        if (userFilename === null) return; // User membatalkan
        
        const finalFilename = userFilename.trim() || lastExtractedFilename;
        downloadExtractedContent(lastExtractedContent, finalFilename);
    });
}

// Copy extracted content
if (extractedCopyBtn) {
    extractedCopyBtn.addEventListener('click', function() {
        const text = extractedMessageDisplay.textContent;
        if (text && text !== 'Tidak ada pesan' && text !== '-') {
            navigator.clipboard.writeText(text).then(() => {
                showToast('✅ Pesan disalin ke clipboard!', 'success');
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showToast('✅ Pesan disalin ke clipboard!', 'success');
            });
        }
    });
}

    // ============================================================
    // DROPZONE SETUP
    // ============================================================
    function setupDropzone(dropzoneId, inputId) {
        const dropzone = document.getElementById(dropzoneId);
        const input = document.getElementById(inputId);
        
        if (!dropzone || !input) return;
        
        dropzone.addEventListener('click', (e) => {
            if (e.target.tagName !== 'INPUT') {
                input.click();
            }
        });
        
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = '#667eea';
            dropzone.style.background = '#f7faff';
        });
        
        dropzone.addEventListener('dragleave', () => {
            dropzone.style.borderColor = '#e2e8f0';
            dropzone.style.background = '#fafbfc';
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = '#e2e8f0';
            dropzone.style.background = '#fafbfc';
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                input.dispatchEvent(new Event('change'));
            }
        });
    }

    setupDropzone('cover-dropzone', 'cover-image');
    setupDropzone('stego-dropzone', 'stego-image');

    // ============================================================
    // KEYS - Load Public Key
    // ============================================================
    async function loadKeys() {
        try {
            const response = await fetch(`${API_BASE}/keys`);
            const data = await response.json();
            
            document.getElementById('public-key-display').textContent = data.public_key || 'Gagal memuat';
            document.getElementById('private-key-display').textContent = data.private_key || 'Private key tersimpan di server';
            
        } catch (error) {
            console.error('Failed to load keys:', error);
        }
    }

    const copyPublicBtn = document.getElementById('copy-public-btn');
    if (copyPublicBtn) {
        copyPublicBtn.addEventListener('click', function() {
            const text = document.getElementById('public-key-display').textContent;
            if (text && text !== 'Loading...' && text !== 'Gagal memuat') {
                navigator.clipboard.writeText(text).then(() => {
                    showToast('✅ Public key copied!', 'success');
                }).catch(() => {
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    document.body.appendChild(textarea);
                    textarea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textarea);
                    showToast('✅ Public key copied!', 'success');
                });
            }
        });
    }

    loadKeys();
    console.log('✅ App ready');

});