# Testing Documentation

## Overview
This document describes the test suite for the P2P Secure Chat application and how to run the tests.

## Test Structure

The test suite is organized into two main categories:

### 1. Cryptographic Tests (`p2p_secure_chat/test_crypto.py`)
Tests the core cryptographic functionality including key generation, handshake, and encryption/decryption.

### 2. Network Tests (`p2p_secure_chat/test_network.py`)
Tests the network connection handling, session management, and message exchange.

## Running Tests

### Run All Tests
```bash
# Run all tests in the package
python3 -m unittest discover p2p_secure_chat -p "test_*.py"
```

### Run Specific Test Suites

**Crypto Tests Only:**
```bash
python3 -m unittest p2p_secure_chat.test_crypto
```

**Network Tests Only:**
```bash
python3 -m unittest p2p_secure_chat.test_network
```

### Run Individual Tests

**Single crypto test:**
```bash
python3 -m unittest p2p_secure_chat.test_crypto.TestCryptoHandler.test_handshake_and_key_derivation
```

**Single network test:**
```bash
python3 -m unittest p2p_secure_chat.test_network.TestNetworkConnection.test_session_key_persistence
```

### Run with Verbose Output
Add `-v` flag for detailed output:
```bash
python3 -m unittest p2p_secure_chat.test_crypto -v
```

## Test Coverage

### Cryptographic Tests (6 tests)

#### 1. `test_key_generation_and_loading`
- **Purpose**: Verify key generation, storage, and loading
- **What it tests**:
  - Keys are generated if they don't exist
  - Keys are saved to PEM files
  - Keys can be loaded from files
  - Fingerprints remain consistent after reload
- **Expected result**: PASS

#### 2. `test_fingerprint_generation`
- **Purpose**: Verify fingerprint calculation
- **What it tests**:
  - Fingerprints are generated correctly
  - Different key pairs produce different fingerprints
- **Expected result**: PASS

#### 3. `test_handshake_and_key_derivation`
- **Purpose**: Verify the complete handshake process
- **What it tests**:
  - Public key bundle creation
  - Signature generation
  - Session key derivation
  - **Critical**: Both peers derive the same session key
- **Expected result**: PASS (was failing before fix)

#### 4. `test_handshake_failure_on_bad_signature`
- **Purpose**: Verify signature verification
- **What it tests**:
  - Invalid signatures are rejected
  - Session is not established with bad signature
- **Expected result**: PASS

#### 5. `test_encryption_decryption`
- **Purpose**: Verify end-to-end encryption
- **What it tests**:
  - Messages can be encrypted
  - Encrypted messages can be decrypted
  - Decrypted content matches original
- **Expected result**: PASS (was failing before fix)

#### 6. `test_decryption_failure_on_tampering`
- **Purpose**: Verify AEAD protection
- **What it tests**:
  - Tampered ciphertext is detected
  - ChaCha20-Poly1305 authentication works
  - Exception is raised on tampering
- **Expected result**: PASS

### Network Tests (3 tests)

#### 1. `test_port_conflict_handling`
- **Purpose**: Verify port conflict management
- **What it tests**:
  - Port conflicts are detected
  - Dynamic port selection works
  - `allow_dynamic_port` parameter functions correctly
- **Expected result**: PASS or SKIP (timing-dependent)

#### 2. `test_session_key_persistence` ⭐ **Critical**
- **Purpose**: Verify session keys remain active
- **What it tests**:
  - Connection is established successfully
  - Handshake completes
  - Both peers have active sessions
  - Session keys are identical
  - **Critical**: Sessions remain active over time
- **Expected result**: PASS
- **Why it's critical**: This test verifies the main bug fix (session key derivation)

#### 3. `test_message_exchange` ⭐ **Critical**
- **Purpose**: Verify bidirectional messaging works
- **What it tests**:
  - Messages can be sent from A to B
  - Messages can be sent from B to A
  - Message content is preserved
  - **Critical**: Connection stays active after sending
  - Sessions remain active after messaging
- **Expected result**: PASS
- **Why it's critical**: This test verifies messages can actually be sent (was failing before fix)

## Test Output Examples

### Successful Test Run
```
test_decryption_failure_on_tampering ... ok
test_encryption_decryption ... ok
test_fingerprint_generation ... ok
test_handshake_and_key_derivation ... ok
test_handshake_failure_on_bad_signature ... ok
test_key_generation_and_loading ... ok
test_session_key_persistence ... ok
test_message_exchange ... ok

----------------------------------------------------------------------
Ran 8 tests in 5.211s

OK
```

### Failed Test (Before Fix)
```
======================================================================
FAIL: test_handshake_and_key_derivation
----------------------------------------------------------------------
Traceback (most recent call last):
  ...
AssertionError: b'Z",|\xa3\x06\x1a\xc3...' != b'\x16l\xceE\x97\x12"...'
```

## Test Environment

### Requirements
- Python 3.8+
- cryptography library (see requirements.txt)
- Network access (for network tests)

### Test Directories
Tests create temporary directories for key storage:
- `test_keys_a/`, `test_keys_b/` (crypto tests)
- `test_keys_network_a/`, `test_keys_network_b/` (network tests)

These are automatically cleaned up after tests complete.

### Ports Used
Network tests use port 15000 by default. If this port is in use, tests may:
- Skip the port conflict test
- Use alternative ports (15001-15010) with `allow_dynamic_port`

## Continuous Integration

### GitHub Actions (If Implemented)
Example workflow:
```yaml
- name: Run Tests
  run: |
    python3 -m unittest discover p2p_secure_chat -p "test_*.py"
```

## Manual Testing Checklist

Beyond automated tests, perform these manual tests:

### 1. Connection Establishment
- [ ] Start peer A in listening mode
- [ ] Connect peer B to peer A
- [ ] Verify "Session sécurisée établie" message appears
- [ ] Check fingerprints match in logs

### 2. Message Exchange
- [ ] Send text message from A to B
- [ ] Verify message appears on B
- [ ] Send text message from B to A
- [ ] Verify message appears on A
- [ ] Send multiple messages in quick succession
- [ ] Verify all messages arrive in order

### 3. File Transfer
- [ ] Send small file (< 1 MB) from A to B
- [ ] Verify file is received correctly
- [ ] Compare checksums of sent and received files
- [ ] Test with various file types

### 4. Error Handling
- [ ] Disconnect network cable during transfer
- [ ] Verify connection is detected as lost
- [ ] Verify clean reconnection is possible
- [ ] Test with incorrect IP address
- [ ] Test with incorrect port

### 5. Port Conflicts
- [ ] Start peer A on port 5000
- [ ] Start peer B on port 5000 (should fail)
- [ ] Verify error message is clear
- [ ] Close peer A
- [ ] Start peer B on port 5000 (should succeed)

### 6. Long-Running Stability
- [ ] Establish connection
- [ ] Leave idle for 5 minutes
- [ ] Send message (should still work)
- [ ] Send 100+ messages
- [ ] Verify connection remains stable

## Debugging Failed Tests

### Test Fails: "Module not found"
**Problem**: Import errors
**Solution**: 
```bash
# Ensure you're in the project root directory
cd /path/to/P2P-s-curis-e-en-Python
python3 -m unittest p2p_secure_chat.test_crypto
```

### Test Fails: "Address already in use"
**Problem**: Port is occupied
**Solution**:
```bash
# Find and kill process using the port
lsof -ti:15000 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :15000    # Windows

# Or wait a minute for the port to be released
sleep 60
```

### Test Fails: "Permission denied"
**Problem**: Cannot create test directories
**Solution**:
```bash
# Check write permissions in current directory
ls -la
# Or run from a directory where you have write access
cd ~
```

### Test Timeout
**Problem**: Network test hangs
**Solution**:
```bash
# Use timeout command
timeout 60 python3 -m unittest p2p_secure_chat.test_network

# Or check for firewall blocking localhost
# Temporarily disable firewall for testing
```

## Test Maintenance

### Adding New Tests
1. Add test method to appropriate test class
2. Follow naming convention: `test_description_of_what_is_tested`
3. Include docstring explaining purpose
4. Ensure proper setUp/tearDown

### Updating Tests After Code Changes
- Crypto changes: Update `test_crypto.py`
- Network changes: Update `test_network.py`
- Protocol changes: May need to update both

### Test Data Management
- Use temporary directories (auto-cleanup)
- Don't commit test keys to repository
- Use `.gitignore` to exclude test artifacts

## Performance Benchmarks

### Typical Test Execution Times
- Crypto tests: ~0.02s (very fast)
- Network tests: ~2-5s each (network setup overhead)
- Full suite: ~5-10s

### What's Normal
- Occasional port conflict warnings: **Normal**
- Brief "Bad file descriptor" errors during cleanup: **Normal**
- Tests taking 2-3x longer on slow systems: **Normal**

### What's Not Normal
- Tests hanging indefinitely: **Problem**
- Consistent failures: **Problem**
- Crashes without error message: **Problem**

## Troubleshooting Common Issues

### "Session key mismatch"
- This was the original bug (now fixed)
- If you see this, the fix may have been reverted
- Check `crypto_handler.py` line ~193 for sorted keys

### "Connection closed after handshake"
- Check logs for session state
- Verify both peers have `active=True`
- May indicate socket issues

### "Module 'tkinter' not found"
- GUI tests are optional
- Install: `apt-get install python3-tk` (Linux)
- Or skip GUI-related tests

## Contact

For test-related issues:
1. Check this documentation
2. Check CHANGELOG.md for known issues
3. Review test output carefully
4. Check logs with DEBUG level enabled
