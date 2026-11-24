# Security

- The initial account is created from a password entered by the operator. Passwords use Argon2 hashing. The temporary bootstrap password does not change existing account credentials.
- The API validates a signed, expiring session cookie against a revocable SQLite session record. Cookies are HttpOnly and SameSite Strict. Logout revokes the server-side session.
- Protected API routes check the session. Administrator-only settings and audit routes additionally check the role.
- Login attempts are bounded per client within the serving process. Event ingestion validates field types, lengths, and limits. Key operator actions are audited.
- Keep runtime data and the JWT signing key private. Load model artifacts generated locally by the training routine, since joblib artifacts are executable deserialization inputs.

The supplied launcher binds both servers to loopback. Local HTTP and the bootstrap workflow are intended for a single machine. See [limitations](KNOWN_LIMITATIONS.md).
