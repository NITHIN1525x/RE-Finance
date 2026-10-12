from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from qbo import audit
from qbo.models import Client


class Command(BaseCommand):
    help = "Create a client (one QuickBooks company per client) and grant users access to it."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help='Display name, e.g. "ABC Inc (sandbox)"')
        parser.add_argument("--slug", help="URL-safe id, e.g. abc-inc-sandbox (default: derived from --name)")
        parser.add_argument("--member", action="append", default=[], help="Username allowed to use this client (repeatable)")

    def handle(self, *args, **opts):
        slug = opts["slug"] or slugify(opts["name"])
        if not slug or slug != slugify(slug):
            raise CommandError(f"Invalid slug {slug!r}: use lowercase letters, digits and hyphens")
        users = []
        for username in opts["member"]:
            user = get_user_model().objects.filter(username=username).first()
            if user is None:
                raise CommandError(f"No user {username!r}. Create it first: python manage.py createsuperuser --username {username}")
            users.append(user)
        client, created = Client.objects.get_or_create(slug=slug, defaults={"name": opts["name"]})
        client.members.add(*users)
        audit.record("create_client" if created else "update_client_members", audit.cli_actor(), True, client,
                     f"Members: {', '.join(u.username for u in client.members.all()) or 'none'}")
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} client '{client.slug}' with {client.members.count()} member(s)."))
