from django.core.management.base import BaseCommand

from visualization.db_utils import run_aggregations


class Command(BaseCommand):
    help = 'Run sensor -> hourly -> daily aggregations (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument('--quiet', action='store_true', help='Minimise output')

    def handle(self, *args, **options):
        quiet = options.get('quiet')
        if not quiet:
            self.stdout.write('Starting aggregations...')

        try:
            status, details, log_id = run_aggregations()
            if not quiet:
                self.stdout.write(self.style.SUCCESS(f'Aggregations finished: {status}'))
                if details:
                    self.stdout.write(details)
                if log_id:
                    self.stdout.write(self.style.SUCCESS(f'Log id: {log_id}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error running aggregations: {e}'))
            raise
