# Changelog

All notable changes to the P2P Secure Chat project will be documented in this file.

## [Unreleased] - Security and Robustness Update

### Security Improvements

#### Cryptography
- **Removed deprecated `default_backend`**: Updated all cryptography imports to remove deprecated `default_backend` parameter, ensuring compatibility with cryptography>=3.4
- **HKDF with deterministic salt**: Implemented proper key derivation using HKDF with a deterministic salt derived from both peers' Ed25519 public keys (lexicographically ordered) to prevent KDF vulnerabilities
- **Nonce uniqueness guarantee**: Added nonce counter mechanism for ChaCha20-Poly1305 encryption:
  - Session-unique 4-byte prefix generated on session establishment
  - 8-byte incrementing counter for each message
  - Total 12-byte nonce ensuring uniqueness and preventing nonce reuse attacks
- **Session cleanup on failure**: Ensured `session_key`, `nonce_prefix`, and `send_counter` are properly cleared when key derivation fails

#### Network Security
- **Message size validation**: Added strict validation of incoming message sizes against `MAX_MESSAGE_SIZE` (4096 bytes) before allocating memory, preventing potential DoS attacks
- **Socket timeouts**: Implemented configurable timeouts:
  - `RECV_SOCKET_TIMEOUT`: 30 seconds for individual recv operations
  - `RECV_TOTAL_TIMEOUT`: 60 seconds for complete message reception
- **Zero-size message validation**: Only `FILE_END` messages are allowed to have zero size, preventing protocol confusion attacks

#### File Transfer Security
- **Path traversal protection**: Implemented multiple layers of protection:
  - Convert all paths to absolute paths using `os.path.abspath()`
  - Use `os.path.basename()` on filenames to strip directory components
  - Validate parent directory exists before opening files
- **Input validation**: Enhanced validation for file metadata:
  - JSON decode error handling
  - File size limit checks before and during transfer
  - Bounds checking on received bytes

#### UI Security
- **IP address validation**: Added comprehensive validation before connection attempts:
  - Regex pattern matching for IP format
  - Numeric validation for each octet (0-255)
  - Port range validation (1-65535)
  - Protected against ValueError from non-numeric input
- **Input sanitization**: All user inputs are validated before use

### Robustness Improvements

#### Network Handler
- **Improved error handling**: Enhanced `_recv_all()` with:
  - Global timeout tracking to prevent indefinite hangs
  - Explicit socket.timeout exception handling
  - Better error logging for debugging
  - Graceful handling of connection failures
- **Proper socket cleanup**: Added socket shutdown before close:
  - `socket.shutdown(socket.SHUT_RDWR)` before `close()`
  - Exception handling for shutdown failures
  - Prevents hanging connections and port conflicts

#### File Transfer
- **I/O exception handling**: Comprehensive error handling:
  - `IOError` handling for file open/write operations
  - `JSONDecodeError` handling for metadata parsing
  - Automatic cleanup on transfer failures
- **Progress validation**: Added bounds checking to ensure received bytes don't exceed expected file size
- **Resource cleanup**: Ensured file handles are closed even on errors

#### GUI
- **Fixed file transfer dialog**: Replaced spin-wait loop with proper `threading.Event` synchronization:
  - 30-second timeout for user response
  - No UI freezing during dialog wait
  - Proper event-based signaling between threads
- **UI state management**: Added `_update_ui_state()` method:
  - Automatically enable/disable send/file buttons based on connection state
  - Disable listen/connect buttons when already connected
  - Clear visual feedback of connection status
- **Thread-safe UI updates**: All UI modifications use `after()` to ensure they run in the main thread

#### Logger
- **Backward-compatible callback**: Updated logger callback signature:
  - Attempts to call callback with `(message, level)` for new code
  - Falls back to `(message)` for old code using introspection
  - Maintains full backward compatibility

### Code Quality Improvements

#### Dependencies
- **Updated requirements**: Specified minimum cryptography version: `cryptography>=3.4`
- **Added .gitignore**: Prevent committing:
  - Python bytecode (`__pycache__`, `*.pyc`)
  - Test directories (`test_keys_a/`, `test_keys_b/`)
  - Virtual environments
  - IDE files
  - Generated key files

#### Code Organization
- **Constants added**: Defined explicit constants for better maintainability:
  - `NONCE_PREFIX_SIZE = 4`
  - `NONCE_COUNTER_SIZE = 8`
  - `CHACHA20_NONCE_SIZE = 12`
  - `RECV_SOCKET_TIMEOUT = 30`
  - `RECV_TOTAL_TIMEOUT = 60`
- **Binary mode PEM I/O**: Fixed inconsistent file I/O:
  - Keys are now consistently read/written in binary mode
  - Proper encoding/decoding of PEM data
- **Test cleanup**: Removed problematic `os.chdir()` from test teardown

### Testing

- **All unit tests passing**: 6/6 tests in `test_crypto.py`
- **CodeQL security scan**: 0 alerts found
- **Code review addressed**: Fixed all critical review comments
- **New testing documentation**: Added comprehensive `TESTING.md` with:
  - Unit test instructions
  - Manual two-instance testing procedures
  - Security testing scenarios
  - Performance testing guidelines
  - Troubleshooting guide

### API Compatibility

All changes maintain backward compatibility with existing APIs:
- `CryptoHandler.get_public_keys_bundle()` - unchanged
- `CryptoHandler.derive_session_key()` - unchanged (internal improvements only)
- `CryptoHandler.encrypt_message()` - unchanged signature (nonce handling is internal)
- `CryptoHandler.decrypt_message()` - unchanged signature
- `Logger.log()` - enhanced but backward compatible
- `NetworkHandler` - no public API changes
- `FileTransferHandler` - no public API changes
- `ChatApp` - no breaking changes to public interface

### Breaking Changes

None. All changes are backward compatible.

### Migration Guide

No migration required. Simply:
1. Pull latest changes
2. Run `pip install -r requirements.txt` to update dependencies
3. Run tests to verify: `python -m unittest test_crypto.py`
4. Restart application

Existing key files are compatible and will be loaded correctly.

### Security Notes

**For users:**
1. Always verify peer fingerprints through a trusted channel before exchanging sensitive information
2. Use strong filesystem permissions to protect private key files (0600 on Unix)
3. Be cautious when accepting file transfers from untrusted peers
4. The application does not persist message history - messages are only in memory

**For developers:**
1. The nonce counter provides uniqueness within a session, but sessions should be limited in duration
2. Consider implementing session rekeying after a certain number of messages or time period
3. Key files are stored unencrypted - consider adding passphrase protection for high-security environments
4. The 10MB file size limit is a security measure to prevent DoS

### Known Issues

None at this time.

### Future Improvements

Potential enhancements for future releases:
- Implement automatic session rekeying (currently logged but not implemented)
- Add message history persistence with encryption
- Add support for multiple simultaneous connections
- Implement passphrase-encrypted key storage
- Add support for key revocation and rotation
- Implement forward secrecy with ephemeral keys
- Add support for group messaging

### Contributors

- GitHub Copilot Workspace
- fatma-amri

---

## Previous Versions

### [Initial Release]
- Basic P2P secure chat functionality
- X25519 key exchange
- Ed25519 signature authentication
- ChaCha20-Poly1305 encryption
- File transfer support
- Tkinter GUI
