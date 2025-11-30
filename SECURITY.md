# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by:

1. **Email**: rajanm001@gmail.com
2. **Subject**: [SECURITY] Brief description
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Based on severity
  - Critical: 24-48 hours
  - High: 3-7 days
  - Medium: 7-14 days
  - Low: 14-30 days

## Security Measures

### Current Protections

✅ **SQL Injection Prevention**
- Parameterized queries using SQLAlchemy
- Input validation with Pydantic
- No raw SQL string concatenation

✅ **Credential Management**
- Environment variables for sensitive data
- No hardcoded passwords or API keys
- `.env` file excluded from version control

✅ **Input Validation**
- Type checking for all API endpoints
- Data sanitization before database operations
- Maximum length constraints

✅ **Error Handling**
- Generic error messages to users
- Detailed logging for debugging
- No sensitive information in error responses

✅ **CORS Configuration**
- Restricted origin list
- Credential handling configured
- Method restrictions

### Recommended Production Settings

1. **HTTPS Only**
   ```bash
   # Use reverse proxy (nginx/traefik) with SSL certificates
   ```

2. **Database Security**
   ```bash
   # Use strong passwords (20+ characters)
   # Restrict database access to application IP
   # Enable SSL for database connections
   ```

3. **API Authentication**
   ```python
   # Implement API key authentication
   # Add rate limiting
   # Use JWT tokens for session management
   ```

4. **Environment Hardening**
   ```bash
   # Run with non-root user
   # Minimize file permissions
   # Disable debug mode in production
   ```

## Security Best Practices

### For Developers

1. **Never commit sensitive data**
   - Check `.gitignore` includes `.env`
   - Review commits before pushing
   - Use environment variables

2. **Keep dependencies updated**
   ```bash
   pip list --outdated
   pip install --upgrade -r requirements.txt
   ```

3. **Validate all inputs**
   - Use Pydantic models
   - Check data types and ranges
   - Sanitize user-provided data

4. **Use parameterized queries**
   ```python
   # Good
   query = "SELECT * FROM inventory WHERE batch_id = :batch_id"
   result = session.execute(text(query), {"batch_id": batch_id})
   
   # Bad - Never do this
   query = f"SELECT * FROM inventory WHERE batch_id = '{batch_id}'"
   ```

### For Users

1. **Secure Database Credentials**
   - Use strong passwords (20+ characters)
   - Change default passwords
   - Restrict database access by IP

2. **Keep Software Updated**
   - Regularly update PostgreSQL
   - Update Python and dependencies
   - Apply OS security patches

3. **Monitor Access Logs**
   - Review application logs regularly
   - Set up alerts for suspicious activity
   - Monitor database connection attempts

4. **Backup Regularly**
   - Automated database backups
   - Secure backup storage
   - Test restoration process

## Known Security Considerations

### Database Access
- Default configuration uses localhost only
- Production should implement network restrictions
- Consider using connection encryption (SSL)

### API Security
- Currently no authentication implemented
- Recommend adding API key or JWT for production
- Rate limiting should be implemented

### Sensitive Data
- Patient enrollment data may contain PII
- Implement data encryption at rest
- Consider HIPAA compliance requirements

## Disclosure Policy

- Security issues are treated with highest priority
- Fixes are developed and tested privately
- Public disclosure after patch is available
- Credit given to reporter (if desired)

## Contact

**Security Contact**: Rajan Mishra  
**Email**: rajanm001@gmail.com  
**Response Time**: Within 48 hours

---

*Last Updated: November 30, 2025*  
*Maintained by Rajan Mishra*
