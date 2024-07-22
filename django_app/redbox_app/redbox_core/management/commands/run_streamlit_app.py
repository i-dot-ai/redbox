import subprocess

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the Streamlit app'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting Streamlit app...'))
        subprocess.run(['streamlit', 'run', 'notebooks/embeddings/app.py'])