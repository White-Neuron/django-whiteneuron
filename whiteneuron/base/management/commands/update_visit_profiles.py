from django.core.management.base import BaseCommand
from django.db.models import Min, Max, Q
from whiteneuron.base.models import VisitProfile


class Command(BaseCommand):
    help = 'Cập nhật first_seen và last_seen cho VisitProfile dựa trên hoạt động từ UserActivity và AnonymousActivity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ hiển thị thông tin sẽ cập nhật, không cập nhật thật',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        profiles = VisitProfile.objects.filter(
            Q(useractivities__isnull=False) | Q(anonymousactivities__isnull=False)
        ).distinct()

        total_count = profiles.count()
        updated_count = 0
        skipped_count = 0

        self.stdout.write(f'Tổng số VisitProfile có activity: {total_count}')
        if dry_run:
            self.stdout.write('[DRY RUN] Chế độ xem trước, không cập nhật')
        self.stdout.write('-' * 60)

        for profile in profiles:
            min_ts = profile.useractivities.aggregate(Min('timestamp'))['timestamp__min']
            max_ts = profile.useractivities.aggregate(Max('timestamp'))['timestamp__max']

            anon_min = profile.anonymousactivities.aggregate(Min('timestamp'))['timestamp__min']
            anon_max = profile.anonymousactivities.aggregate(Max('timestamp'))['timestamp__max']

            all_timestamps = [ts for ts in [min_ts, max_ts, anon_min, anon_max] if ts is not None]

            if not all_timestamps:
                skipped_count += 1
                continue

            first_seen_candidate = min(all_timestamps)
            last_seen_candidate = max(all_timestamps)

            updates = {}
            needs_update = False

            if first_seen_candidate < profile.first_seen:
                updates['first_seen'] = first_seen_candidate
                needs_update = True

            if last_seen_candidate > profile.last_seen:
                updates['last_seen'] = last_seen_candidate
                needs_update = True

            if needs_update:
                if dry_run:
                    self.stdout.write(
                        f'P{profile.id} - {profile.ip_address}: '
                        f'first_seen: {profile.first_seen} -> {updates.get("first_seen", profile.first_seen).date()}, '
                        f'last_seen: {profile.last_seen} -> {updates.get("last_seen", profile.last_seen).date()}'
                    )
                else:
                    VisitProfile.objects.filter(pk=profile.pk).update(**updates)
                    updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write('-' * 60)
        if dry_run:
            self.style.SUCCESS(f'[DRY RUN] Sẽ cập nhật {updated_count}/{total_count} profiles')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Đã cập nhật: {updated_count}')
            )
            self.stdout.write(
                self.style.WARNING(f'Bỏ qua (không cần update): {skipped_count}')
            )
