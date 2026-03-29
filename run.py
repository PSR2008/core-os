"""run.py — Application entry point."""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from flask_migrate import upgrade

app = create_app()

try:
    upgrade()
except Exception as e:
    print("Migration skipped or failed:", e)

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug)