"""Client-scoped authorization. Every view resolves its client through these helpers.

A user only sees clients they are a member of. A client that exists but belongs to someone else
returns 404, the same as a missing one, so its existence is not disclosed.
"""
from django.http import Http404

from .models import AuditLog, Client


def clients_for(user):
    return Client.objects.filter(members=user)


def get_client_for(user, slug):
    client = clients_for(user).filter(slug=slug).select_related("connection").first()
    if client is None:
        raise Http404("Client not found")
    return client


def audit_for(user):
    return AuditLog.objects.filter(client__members=user)
