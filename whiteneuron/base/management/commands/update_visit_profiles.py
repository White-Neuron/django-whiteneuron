from django.core.management.base import BaseCommand
from django.db.models import Exists, Max, Min, OuterRef, Subquery
from whiteneuron.base.models import AnonymousActivity, UserActivity, VisitProfile


def _bound(model, func):
    """Correlated subquery: MIN/MAX(timestamp) of ``model`` rows for the outer profile."""
    return Subquery(
        model.objects.filter(profile=OuterRef('pk')).order_by()
        .values('profile').annotate(v=func('timestamp')).values('v')[:1]
    )


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

        # Min/max timestamps computed in the same query (was 4 aggregate queries per profile)
        # EXISTS keeps one row per profile (a JOIN + DISTINCT re-ran the subqueries per activity row)
        profiles = VisitProfile.objects.filter(
            Exists(UserActivity.objects.filter(profile=OuterRef('pk')))
            | Exists(AnonymousActivity.objects.filter(profile=OuterRef('pk')))
        ).annotate(
            user_min=_bound(UserActivity, Min), user_max=_bound(UserActivity, Max),
            anon_min=_bound(AnonymousActivity, Min), anon_max=_bound(AnonymousActivity, Max),
        )

        total_count = profiles.count()
        updated_count = 0
        skipped_count = 0

        self.stdout.write(f'Tổng số VisitProfile có activity: {total_count}')
        if dry_run:
            self.stdout.write('[DRY RUN] Chế độ xem trước, không cập nhật')
        self.stdout.write('-' * 60)

        for profile in profiles.iterator(chunk_size=2000):
            all_timestamps = [ts for ts in [profile.user_min, profile.user_max, profile.anon_min, profile.anon_max]
                              if ts is not None]

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
                    updated_count += 1
                else:
                    VisitProfile.objects.filter(pk=profile.pk).update(**updates)
                    updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write('-' * 60)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'[DRY RUN] Sẽ cập nhật {updated_count}/{total_count} profiles'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Đã cập nhật: {updated_count}')
            )
            self.stdout.write(
                self.style.WARNING(f'Bỏ qua (không cần update): {skipped_count}')
            )
