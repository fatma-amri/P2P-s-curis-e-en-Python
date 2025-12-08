# Testing Instructions for P2P Secure Chat

This document provides comprehensive testing instructions for the P2P Secure Chat application after the security and robustness improvements.

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation

1. Clone the repository (if not already done):
   ```bash
   git clone https://github.com/fatma-amri/P2P-s-curis-e-en-Python.git
   cd P2P-s-curis-e-en-Python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Unit Tests

Run the cryptographic unit tests to verify core functionality:

```bash
python -m unittest test_crypto.py
```

**Expected output:**
```
......
----------------------------------------------------------------------
Ran 6 tests in 0.016s

OK
```

All 6 tests should pass:
- `test_key_generation_and_loading` - Verifies key generation, saving, and loading
- `test_fingerprint_generation` - Tests fingerprint computation
- `test_handshake_and_key_derivation` - Tests complete handshake and session key derivation
- `test_handshake_failure_on_bad_signature` - Verifies signature validation
- `test_encryption_decryption` - Tests message encryption/decryption
- `test_decryption_failure_on_tampering` - Verifies AEAD authentication

## Manual Testing: Two-Instance Communication

### Test 1: Basic Connection and Handshake

**Instance A (Server):**
1. Start the application:
   ```bash
   python main.py
   ```
2. Note the displayed fingerprint in the UI
3. Click "Démarrer écoute"
4. Enter port: `5000`
5. Wait for connection

**Instance B (Client):**
1. Start the application in a new terminal:
   ```bash
   python main.py
   ```
2. Note the displayed fingerprint in the UI
3. Click "Se connecter"
4. Enter: `127.0.0.1:5000`
5. Wait for connection

**Expected Results:**
- Both instances show "Connecté à [IP:Port]" status
- Both instances display "--- Session sécurisée établie ---"
- Log shows "Handshake réussi. Clé de session établie."
- Send and file buttons become enabled

**Security Note:** In production, users should manually verify each other's fingerprints through a trusted channel before communicating.

### Test 2: Text Messaging

With both instances connected from Test 1:

**Instance A:**
1. Type a message in the input field
2. Click "Envoyer message" or press Enter
3. Verify message appears with timestamp and "Moi:" prefix

**Instance B:**
1. Verify the message appears with timestamp and "Pair:" prefix
2. Reply with another message
3. Verify it appears in Instance A

**Expected Results:**
- All messages are transmitted successfully
- Messages are displayed with correct timestamps
- Sent messages show "Moi:" prefix
- Received messages show "Pair:" prefix

### Test 3: File Transfer

With both instances connected:

**Instance A (Sender):**
1. Create a test file (e.g., `echo "Test content" > test.txt`)
2. Click "Envoyer fichier"
3. Select the test file
4. Wait for transfer to complete

**Instance B (Receiver):**
1. A dialog appears: "Le pair souhaite vous envoyer le fichier..."
2. Click "Yes" to accept
3. Choose a save location
4. Wait for transfer to complete
5. Verify the file is saved correctly
6. Compare content with original file

**Expected Results:**
- File transfer request dialog appears on receiver
- File is transmitted in chunks
- Progress is logged in the UI
- File is saved to chosen location
- File content matches original exactly
- Success message appears: "Fichier reçu avec succès"

### Test 4: File Transfer - Large File

Create a larger test file (within 10MB limit):

```bash
# Create a 5MB test file
dd if=/dev/urandom of=large_test.bin bs=1M count=5
```

Repeat Test 3 with this larger file.

**Expected Results:**
- Transfer completes successfully
- File size matches (verify with `ls -lh` or `stat`)
- No errors in logs

### Test 5: File Transfer - Rejection

**Instance A:** Click "Envoyer fichier" and select a file

**Instance B:** When dialog appears, click "No" to reject

**Expected Results:**
- Transfer is cancelled
- Log shows: "Réception du fichier annulée par l'utilisateur"
- No partial file is created

### Test 6: Connection Validation

Test invalid connection attempts:

**Test 6.1: Invalid IP Format**
1. Click "Se connecter"
2. Enter: `invalid.ip.address:5000`
3. Verify error message: "Adresse IP invalide"

**Test 6.2: Invalid Port**
1. Click "Se connecter"
2. Enter: `127.0.0.1:99999`
3. Verify error message: "Port invalide (doit être entre 1 et 65535)"

**Test 6.3: Missing Port**
1. Click "Se connecter"
2. Enter: `127.0.0.1`
3. Verify error message: "Format IP:Port invalide"

### Test 7: Disconnection and Reconnection

With both instances connected:

**Instance A:**
1. Close the application window
2. Restart the application
3. Note that a new key pair may be generated (different fingerprint)

**Instance B:**
1. Verify connection status changes to "Déconnecté"
2. Try to send a message - should fail with warning
3. Send/file buttons should be disabled

**Reconnection:**
1. Instance A: Click "Démarrer écoute" with port 5000
2. Instance B: Click "Se connecter" with 127.0.0.1:5000
3. Verify handshake completes successfully
4. Verify messaging works again

## Security Testing

### Test 8: Message Authentication

This test verifies that tampering is detected (already covered in unit tests, but can be observed in logs).

The AEAD (ChaCha20-Poly1305) cipher ensures:
- Messages cannot be decrypted without the correct key
- Any tampering is detected and causes decryption to fail
- Replay attacks are mitigated by the nonce counter

### Test 9: Path Traversal Protection

**Instance A:** Send a file named `test.txt`

**Instance B:**
1. When prompted to save, try entering a path like: `../../etc/passwd`
2. The application uses `os.path.basename()` to prevent traversal
3. File should be saved safely in the chosen directory

### Test 10: Nonce Uniqueness

Send multiple messages in quick succession:

**Instance A:**
1. Send 10 messages rapidly
2. Check logs for any encryption errors

**Expected Results:**
- All messages are encrypted successfully
- No nonce reuse errors
- The nonce counter increments for each message

## Performance Testing

### Test 11: Multiple Messages

Send 50+ messages in succession and verify:
- No memory leaks
- UI remains responsive
- All messages are received correctly

### Test 12: Maximum File Size

Test the 10MB file size limit:

```bash
# Create a file just under the limit
dd if=/dev/urandom of=9mb_test.bin bs=1M count=9

# Create a file over the limit
dd if=/dev/urandom of=11mb_test.bin bs=1M count=11
```

**Expected Results:**
- 9MB file transfers successfully
- 11MB file is rejected with error: "Taille du fichier dépasse la limite"

## Timeout Testing

### Test 13: Connection Timeout

1. Start Instance A listening on port 5000
2. Configure firewall to block connection or disconnect network
3. Instance B attempts to connect
4. Verify connection times out gracefully with error message

### Test 14: Receive Timeout

1. Establish connection between two instances
2. Pause one instance (e.g., with debugger or Ctrl+Z on Linux)
3. Try to send message from other instance
4. Verify timeout is handled gracefully after RECV_SOCKET_TIMEOUT (30 seconds)

## Regression Testing

After making any changes, always run:

1. Unit tests: `python -m unittest test_crypto.py`
2. Basic connection test (Test 1)
3. Message exchange test (Test 2)
4. File transfer test (Test 3)

## Known Limitations

1. Only one P2P connection at a time
2. File size limited to 10MB
3. No message history persistence
4. Keys are stored unencrypted (use strong filesystem permissions)
5. No group chat support (P2P only)

## Troubleshooting

### Issue: "Port already in use"
**Solution:** Wait a few seconds for the port to be released, or use a different port number.

### Issue: Connection refused
**Solution:** 
- Verify the server is listening
- Check firewall settings
- Verify IP address and port are correct

### Issue: Handshake fails
**Solution:**
- Check that both instances are running compatible versions
- Verify network connectivity
- Check logs for specific error messages

### Issue: File transfer doesn't start
**Solution:**
- Ensure both instances are connected with active session
- Check that file size is under 10MB limit
- Verify disk space is available

## Security Scan

The codebase has been scanned with CodeQL and shows 0 security alerts:

```bash
# CodeQL analysis results
Analysis Result for 'python'. Found 0 alerts:
- **python**: No alerts found.
```

## Reporting Issues

When reporting issues, please include:
1. Operating system and Python version
2. Steps to reproduce
3. Expected vs actual behavior
4. Relevant log messages from the UI
5. Screenshots if applicable

## Additional Resources

- [README.md](README.md) - Application overview and features
- [cryptography documentation](https://cryptography.io/) - Details on cryptographic primitives used
