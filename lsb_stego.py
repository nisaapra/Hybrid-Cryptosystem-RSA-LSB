from PIL import Image
import numpy as np
import struct
import traceback

class LSBSteganography:
    def __init__(self):
        pass
    
    def _text_to_bits(self, text):
        """Convert text to binary string"""
        bits = ''.join(format(ord(char), '08b') for char in text)
        return bits
    
    def _bits_to_text(self, bits):
        """Convert binary string to text"""
        try:
            chars = []
            for i in range(0, len(bits), 8):
                if i + 8 <= len(bits):
                    byte = bits[i:i+8]
                    chars.append(chr(int(byte, 2)))
            return ''.join(chars)
        except Exception as e:
            print(f"❌ Error converting bits to text: {str(e)}")
            return ""
    
    def embed(self, image_path, message, output_path):
        """
        Embed message into image using LSB with length header
        """
        try:
            print(f"📷 Opening image: {image_path}")
            img = Image.open(image_path)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img_array = np.array(img)
            original_shape = img_array.shape
            print(f"📊 Image shape: {original_shape}")
            
            # Convert message to bytes then to bits
            message_bytes = message.encode('utf-8')
            message_len = len(message_bytes)
            print(f"📊 Message length: {message_len} bytes")
            
            # Create header: 4 bytes for length (32-bit integer)
            header = struct.pack('>I', message_len)
            header_bits = ''.join(format(byte, '08b') for byte in header)
            
            # Convert message to bits
            message_bits = ''.join(format(byte, '08b') for byte in message_bytes)
            
            # Combine header + message
            all_bits = header_bits + message_bits
            print(f"📊 Total bits to embed: {len(all_bits)}")
            
            # Flatten image array
            flat_pixels = img_array.flatten()
            
            # Check capacity
            if len(all_bits) > len(flat_pixels):
                raise Exception(f"Message too large. Need {len(all_bits)} bits, available {len(flat_pixels)} bits")
            
            # Embed bits into LSB
            for i in range(len(all_bits)):
                bit = int(all_bits[i])
                flat_pixels[i] = (flat_pixels[i] & ~1) | bit
            
            # Reshape and save
            new_img_array = flat_pixels.reshape(original_shape)
            new_img = Image.fromarray(new_img_array.astype('uint8'), 'RGB')
            new_img.save(output_path, format='PNG')
            
            print(f"✅ Image saved to: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Embedding error: {str(e)}")
            print(traceback.format_exc())
            raise Exception(f"Embedding failed: {str(e)}")
    
    def extract(self, image_path):
        """
        Extract message from image using LSB with length header
        """
        try:
            print(f"📷 Opening stego image: {image_path}")
            img = Image.open(image_path)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img_array = np.array(img)
            print(f"📊 Image shape: {img_array.shape}")
            
            # Flatten image array
            flat_pixels = img_array.flatten()
            print(f"📊 Total pixels: {len(flat_pixels)}")
            
            # Extract first 32 bits for header (4 bytes)
            header_bits = ''
            for i in range(32):
                if i < len(flat_pixels):
                    header_bits += str(flat_pixels[i] & 1)
                else:
                    header_bits += '0'
            
            # Convert header bits to integer
            try:
                header_bytes = int(header_bits, 2).to_bytes(4, 'big')
                message_len = struct.unpack('>I', header_bytes)[0]
                print(f"📊 Message length from header: {message_len} bytes")
            except Exception as e:
                print(f"❌ Invalid header: {str(e)}")
                return "No hidden message found (invalid header)"
            
            # Validate message length
            if message_len <= 0 or message_len > 1000000:
                print(f"❌ Invalid message length: {message_len}")
                return "No hidden message found (invalid length)"
            
            # Extract message bits
            total_bits_needed = 32 + (message_len * 8)
            if total_bits_needed > len(flat_pixels):
                print(f"❌ Not enough pixels: need {total_bits_needed}, have {len(flat_pixels)}")
                return "No hidden message found (data truncated)"
            
            message_bits = ''
            for i in range(32, 32 + (message_len * 8)):
                if i < len(flat_pixels):
                    message_bits += str(flat_pixels[i] & 1)
                else:
                    break
            
            print(f"📊 Extracted {len(message_bits)} message bits")
            
            # Convert bits to bytes
            try:
                message_bytes = bytearray()
                for i in range(0, len(message_bits), 8):
                    if i + 8 <= len(message_bits):
                        byte = int(message_bits[i:i+8], 2)
                        message_bytes.append(byte)
                
                message = message_bytes.decode('utf-8')
                print(f"✅ Extracted message length: {len(message)} chars")
                return message
            except Exception as e:
                print(f"❌ Error decoding message: {str(e)}")
                return "No hidden message found (invalid data)"
            
        except Exception as e:
            print(f"❌ Extraction error: {str(e)}")
            print(traceback.format_exc())
            raise Exception(f"Extraction failed: {str(e)}")
    
    def get_capacity(self, image_path):
        """Get maximum message capacity in characters"""
        try:
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_array = np.array(img)
            total_bits = img_array.size
            # 32 bits for header, 8 bits per char
            max_bytes = (total_bits - 32) // 8
            print(f"📊 Image capacity: {max_bytes} bytes")
            return max_bytes
        except Exception as e:
            print(f"❌ Capacity error: {str(e)}")
            return 0