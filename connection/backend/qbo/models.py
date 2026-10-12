"""Client -> QBOConnection (one realm per client) -> AuditLog.

Token columns hold Fernet ciphertext only. Plaintext tokens exist briefly in memory during a request
or management command, and nowhere else in this app.
"""
from django.conf import settings
from django.db import models


class Client(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    # Authorization: only these users may see or act on this client (see qbo/access.py).
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="qbo_clients", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.slug


class QBOConnection(models.Model):
    class Status(models.TextChoices):
        CONNECTED = "connected"
        REFRESH_REQUIRED = "refresh_required"   # refresh token rejected or expired: reconnect via OAuth
        ERROR = "error"
        DISCONNECTED = "disconnected"

    class Owner(models.TextChoices):
        # Exactly one component may refresh (and therefore rotate) the refresh token at a time.
        DJANGO = "django"
        MCP = "mcp"      # checked out to the official MCP server via export_mcp_env

    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="connection")
    realm_id = models.CharField(max_length=32)   # unique among active connections: see Meta
    environment = models.CharField(max_length=16, default="sandbox", editable=False)
    encrypted_refresh_token = models.TextField(blank=True, default="")
    encrypted_access_token = models.TextField(blank=True, default="")
    access_token_expires_at = models.DateTimeField(null=True, blank=True)
    refresh_token_expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONNECTED)
    token_owner = models.CharField(max_length=10, choices=Owner.choices, default=Owner.DJANGO)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # A QuickBooks company can be actively connected to at most ONE client (isolation).
            # Disconnected rows keep their realm for history without blocking a later reconnect.
            models.UniqueConstraint(fields=["realm_id"], condition=~models.Q(status="disconnected"),
                                    name="one_active_client_per_realm"),
        ]

    @property
    def realm_hint(self):
        """At most the first four characters; the full realm ID never leaves the backend."""
        return f"{self.realm_id[:4]}…" if self.realm_id else ""

    def __str__(self):
        return f"{self.client.slug} ({self.realm_hint})"


class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    # SET_NULL + slug snapshot: the trail survives a client being deleted.
    client = models.ForeignKey(Client, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    client_slug = models.CharField(max_length=80, blank=True)
    action = models.CharField(max_length=40)
    actor = models.CharField(max_length=150)
    success = models.BooleanField()
    detail = models.CharField(max_length=500, blank=True)   # never secrets: see qbo/audit.py

    class Meta:
        ordering = ["-timestamp", "-id"]
