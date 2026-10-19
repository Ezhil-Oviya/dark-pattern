import logging
import os
from typing import Optional, Tuple
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, PyMongoError, ServerSelectionTimeoutError

logger = logging.getLogger("app.config.database")

load_dotenv()

# Read values from environment
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME") or os.getenv("MONGODB_DATABASE") or "dark_pattern_db"
EVIDENCE_DB_NAME = os.getenv("EVIDENCE_DATABASE_NAME", "dark_pattern_evidence")
TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "10000"))


def configure_dns_resolvers():
    """
    Configures dnspython default resolver with reliable public DNS servers (8.8.8.8, 1.1.1.1).
    This prevents 'resolution lifetime expired' and DNS operation timed out errors when
    resolving MongoDB Atlas SRV records (_mongodb._tcp...) on local networks with slow/unreliable DNS.
    """
    try:
        import dns.resolver
        resolver = dns.resolver.get_default_resolver()
        reliable_servers = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
        current = list(resolver.nameservers)
        resolver.nameservers = [ns for ns in reliable_servers if ns not in current] + current
        resolver.lifetime = max(getattr(resolver, "lifetime", 5.0), 10.0)
        resolver.timeout = max(getattr(resolver, "timeout", 3.0), 5.0)
    except Exception as e:
        logger.debug(f"Could not configure fallback DNS resolvers: {e}")


# Configure DNS before connecting
configure_dns_resolvers()


def create_mongo_client(uri: str, timeout_ms: int = TIMEOUT_MS) -> MongoClient:
    """
    Creates and returns a MongoClient configured for MongoDB Atlas with proper TLS/certifi and timeouts.
    Never bypasses TLS validation or uses insecure SSL settings.
    Automatically retries with reliable public DNS servers if local SRV resolution times out.
    """
    if not uri:
        raise ConfigurationError("MONGO_URI is empty or not set in environment.")

    configure_dns_resolvers()

    client_kwargs = {
        "serverSelectionTimeoutMS": timeout_ms,
        "connectTimeoutMS": timeout_ms,
        "socketTimeoutMS": 15000,
    }

    # If URI uses TLS/SSL or Atlas SRV connection, configure certifi CA file
    is_tls = "mongodb+srv" in uri or "ssl=true" in uri.lower() or "tls=true" in uri.lower() or "mongodb.net" in uri.lower()
    if is_tls:
        client_kwargs["tlsCAFile"] = certifi.where()

    try:
        return MongoClient(uri, **client_kwargs)
    except ConfigurationError as ce:
        logger.warning(f"Initial MongoDB Atlas connection attempt failed: {ce}. Retrying with strict public DNS...")
        try:
            import dns.resolver
            resolver = dns.resolver.get_default_resolver()
            resolver.nameservers = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
            resolver.lifetime = 15.0
            resolver.timeout = 8.0
            return MongoClient(uri, **client_kwargs)
        except Exception:
            raise ce


# Track whether the client is a fallback client due to initial network/DNS unavailability
is_fallback_client = False

try:
    client = create_mongo_client(MONGO_URI)
except Exception as init_err:
    logger.error(
        f"Could not initialize primary MongoDB Atlas client at startup: {init_err}.\n"
        "Initializing fallback offline client to allow server to start gracefully."
    )
    is_fallback_client = True
    # Non-SRV local client won't fail with DNS SRV timeout during import
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000)

# Select databases from client
website_db = client[DATABASE_NAME]
evidence_db = client[EVIDENCE_DB_NAME]
db = website_db

# Collections
website_collection = website_db["websites"]


def check_mongo_connection(client_instance: Optional[MongoClient] = None, timeout_ms: int = 5000) -> Tuple[bool, str]:
    """
    Pings MongoDB Atlas to verify connectivity and returns (is_connected, status_message).
    If initial connection failed at startup, attempts reconnection when called.
    """
    global client, website_db, evidence_db, db, website_collection, is_fallback_client

    if is_fallback_client and MONGO_URI:
        try:
            new_client = create_mongo_client(MONGO_URI, timeout_ms=timeout_ms)
            new_client.admin.command("ping")
            client = new_client
            website_db = client[DATABASE_NAME]
            evidence_db = client[EVIDENCE_DB_NAME]
            db = website_db
            website_collection = website_db["websites"]
            is_fallback_client = False
            return True, "Connected successfully"
        except Exception as e:
            return False, f"Reconnection failed: {str(e)[:120]}"

    target = client_instance if client_instance is not None else client

    try:
        # Ping admin database with configured timeout
        target.admin.command("ping")
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


def get_mongo_diagnostics(connection_check: Optional[Tuple[bool, str]] = None) -> dict:
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
