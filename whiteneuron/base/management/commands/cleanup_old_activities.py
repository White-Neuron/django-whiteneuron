from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from whiteneuron.base.models import UserActivity, AnonymousActivity, VisitProfile


class Command(BaseCommand):
    help = 'Xóa các bản ghi activity và notification cũ'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Số ngày giữ lại data (default: 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ hiển thị số lượng bản ghi sẽ xóa, không xóa thật',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(f'{"[DRY RUN] " if dry_run else ""}Cắt data trước: {cutoff_date.date()}')
        self.stdout.write('-' * 60)

        models_to_clean = [
            ('UserActivity', UserActivity),
            ('AnonymousActivity', AnonymousActivity),
        ]

        total_deleted = 0

        for model_name, Model in models_to_clean:
            count = Model.objects.filter(timestamp__lt=cutoff_date).count()
            if count > 0:
                self.stdout.write(
                    f'{model_name}: {count} bản ghi cũ hơn {days} ngày'
                )
                if not dry_run:
                    deleted, _ = Model.objects.filter(timestamp__lt=cutoff_date).delete()
                    total_deleted += deleted
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'{model_name}: không có bản ghi nào cần xóa')
                )

        try:
            from whiteneuron.notification.models import Notification
            count = Notification.objects.filter(created_at__lt=cutoff_date).count()
            if count > 0:
                self.stdout.write(
                    f'Notification: {count} bản ghi cũ hơn {days} ngày'
                )
                if not dry_run:
                    deleted, _ = Notification.objects.filter(created_at__lt=cutoff_date).delete()
                    total_deleted += deleted
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Notification: không có bản ghi nào cần xóa')
                )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Không thể truy cập Notification model: {e}')
            )

        orphan_profiles = VisitProfile.objects.exclude(
            pk__in=VisitProfile.objects.filter(
                Q(useractivities__isnull=False) | Q(anonymousactivities__isnull=False)
            ).values('pk')
        )
        if orphan_profiles.exists():
            count = orphan_profiles.count()
            self.stdout.write(f'Orphan profiles (no activities): {count}')
            if not dry_run:
                deleted, _ = orphan_profiles.delete()
                total_deleted += deleted

        self.stdout.write('-' * 60)
        if dry_run:
            self.stdout.write(
                f'[DRY RUN] Tổng số bản ghi sẽ xóa: {total_deleted}'
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Đã xóa {total_deleted} bản ghi')
            )
