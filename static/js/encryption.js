/**
 * Chat encryption utilities using Web Crypto API
 */
class ChatEncryption {
  /**
   * Generates a new AES-GCM encryption key
   * @returns {Promise<string>} Base64-encoded key
   */
  static async generateKey() {
    const key = await window.crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"]
    );
    const exportedKey = await window.crypto.subtle.exportKey("raw", key);
    return btoa(String.fromCharCode(...new Uint8Array(exportedKey)));
  }

  /**
   * Imports a key from a Base64 string
   * @param {string} keyBase64 - Base64-encoded key
   * @returns {Promise<CryptoKey>} Imported key
   */
  static async importKey(keyBase64) {
    const keyData = Uint8Array.from(atob(keyBase64), c => c.charCodeAt(0));
    return window.crypto.subtle.importKey(
      "raw",
      keyData,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"]
    );
  }

  /**
   * Encrypts a message
   * @param {string} message - Plaintext message
   * @param {string} keyBase64 - Base64-encoded key
   * @returns {Promise<string>} Base64-encoded encrypted message (IV + ciphertext)
   */
  static async encryptMessage(message, keyBase64) {
    const key = await this.importKey(keyBase64);
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const encodedMessage = new TextEncoder().encode(message);

    const encrypted = await window.crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      key,
      encodedMessage
    );

    const combined = new Uint8Array(iv.length + encrypted.byteLength);
    combined.set(iv);
    combined.set(new Uint8Array(encrypted), iv.length);

    return btoa(String.fromCharCode(...combined));
  }

  /**
   * Decrypts a message
   * @param {string} encryptedBase64 - Base64-encoded encrypted message
   * @param {string} keyBase64 - Base64-encoded key
   * @returns {Promise<string>} Decrypted message
   */
  static async decryptMessage(encryptedBase64, keyBase64) {
    const key = await this.importKey(keyBase64);
    const encryptedData = Uint8Array.from(atob(encryptedBase64), c => c.charCodeAt(0));
    const iv = encryptedData.slice(0, 12);
    const ciphertext = encryptedData.slice(12);

    const decrypted = await window.crypto.subtle.decrypt(
      { name: "AES-GCM", iv },
      key,
      ciphertext
    );

    return new TextDecoder().decode(decrypted);
  }

  /**
   * Stores a key in localStorage
   * @param {string} roomId - Room identifier
   * @param {string} keyBase64 - Base64-encoded key
   */
  static storeKey(roomId, keyBase64) {
    localStorage.setItem(`chat_key_${roomId}`, keyBase64);
  }

  /**
   * Retrieves a key from localStorage
   * @param {string} roomId - Room identifier
   * @returns {string|null} Base64-encoded key or null
   */
  static getKey(roomId) {
    return localStorage.getItem(`chat_key_${roomId}`);
  }
}

export default ChatEncryption;