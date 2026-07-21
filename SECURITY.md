# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. Email: security@example.com
2. Do not disclose publicly
3. Allow time for a fix

## Authentication

- API keys for service access
- JWT tokens for user sessions
- bcrypt for password hashing

## Data Protection

- Secrets stored in environment variables
- Database connections use parameterized queries
- Input validation on all endpoints

## Rate Limiting

API endpoints are rate-limited to prevent abuse.
