import os
from pathlib import Path

# =============================================================================
# Database Configuration
# =============================================================================
# Uses environment variables with fallback defaults
# Set environment variables for production:
#   export DB_HOST=localhost
#   export DB_USER=root
#   export DB_PASSWORD=your_password

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'oyrq1206'),  # Set via environment variable
    'database': os.getenv('DB_NAME', 'AIplane'),
    'charset': 'utf8mb4',
    'port': int(os.getenv('DB_PORT', 3306))
}

# =============================================================================
# File Paths
# =============================================================================

# Base directory (database/)
BASE_DIR = Path(__file__).parent.parent

# Data directory (database/data/)
DATA_DIR = BASE_DIR / 'data'

# Source files
EXCEL_FILE = DATA_DIR / 'field_mapping.xlsx'
SQL_FILE = DATA_DIR / 'AIplane.sql'

# =============================================================================
# Validation
# =============================================================================

def validate_config():
    """Validate configuration and print status."""
    print("=" * 50)
    print("Database Configuration")
    print("=" * 50)
    print(f"Host:     {DB_CONFIG['host']}")
    print(f"User:     {DB_CONFIG['user']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"Port:     {DB_CONFIG['port']}")
    print(f"Password: {'[SET]' if DB_CONFIG['password'] else '[NOT SET]'}")
    print()
    print(f"Excel:    {EXCEL_FILE}")
    print(f"  Exists: {EXCEL_FILE.exists()}")
    print(f"SQL:      {SQL_FILE}")
    print(f"  Exists: {SQL_FILE.exists()}")
    print("=" * 50)


if __name__ == "__main__":
    validate_config()