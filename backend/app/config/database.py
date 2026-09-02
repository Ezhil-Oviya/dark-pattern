import logging
import os
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

logger = logging.getLogger("app.config.database")

# Load environment variables
load_dotenv()

# Read values from environment
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME") or os.getenv("MONGODB_DATABASE") or "dark_pattern_db"
EVIDENCE_DB_NAME = os.getenv("EVIDENCE_DATABASE_NAME", "dark_pattern_evidence")
TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))


def create_mongo_client(uri: str, timeout_ms: int = TIMEOUT_MS) -> MongoClient:
    """
    Creates and returns a MongoClient configured for MongoDB Atlas with proper TLS/certifi and timeouts.
    Never bypasses TLS validation or uses insecure SSL settings.
    """
    client_kwargs = {
        "serverSelectionTimeoutMS": timeout_ms,
        "connectTimeoutMS": timeout_ms,
        "socketTimeoutMS": 10000,
    }

    # If URI uses TLS/SSL or Atlas SRV connection, configure certifi CA file
    is_tls = "mongodb+srv" in uri or "ssl=true" in uri.lower() or "tls=true" in uri.lower() or "mongodb.net" in uri.lower()
    if is_tls:
        client_kwargs["tlsCAFile"] = certifi.where()

    return MongoClient(uri, **client_kwargs)


# Initialize single primary Atlas MongoClient directly from environment
client = create_mongo_client(MONGO_URI)

# Select databases from single Atlas client
website_db = client[DATABASE_NAME]
evidence_db = client[EVIDENCE_DB_NAME]
db = website_db

# Collections
website_collection = website_db["websites"]


def check_mongo_connection(client_instance: MongoClient = client, timeout_ms: int = 3000) -> tuple[bool, str]:
    """
    Pings MongoDB Atlas to verify connectivity and returns (is_connected, status_message).
    """
    try:
        # Ping admin database with short timeout
        client_instance.admin.command("ping")
        return True, "Connected successfully"
    except ServerSelectionTimeoutError as sse:
        err_msg = str(sse)
        if "SSL" in err_msg or "TLS" in err_msg or "ALERT_INTERNAL_ERROR" in err_msg:
            return False, "SSL/TLS handshake failed. Verify MongoDB Atlas IP Access List (whitelist)."
        return False, f"Server selection timeout: {err_msg[:120]}"
    except PyMongoError as pe:
        return False, f"PyMongo error: {str(pe)[:120]}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)[:120]}"


def get_mongo_diagnostics(connection_check: tuple[bool, str] = None) -> dict:
    """
    Returns detailed diagnostics about the configured MongoDB Atlas connection.
    Safely masks all credentials.
    """
    if connection_check is not None:
        is_connected, message = connection_check
    else:
        is_connected, message = check_mongo_connection()

    masked_uri = MONGO_URI
    host = "cluster0.ub9pvxy.mongodb.net" if "mongodb.net" in MONGO_URI else "unknown"
    if "@" in masked_uri:
        prefix = masked_uri.split("@")[0].split("://")[0]
        host_part = masked_uri.split("@")[1].split("/")[0]
        host = host_part
        masked_uri = f"{prefix}://***:***@{host_part}"

    return {
        "connected": is_connected,
        "status_message": message,
        "server": host,
        "uri": masked_uri,
        "website_database": DATABASE_NAME,
        "evidence_database": EVIDENCE_DB_NAME,
        "timeout_ms": TIMEOUT_MS,
    }