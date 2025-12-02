"""
Management command to populate ProximityLocation model with default locations.
"""
from django.core.management.base import BaseCommand
from places.models import ProximityLocation


# Default proximity locations to seed
DEFAULT_LOCATIONS = [
    # Seoul Major Areas
    {'name': 'itaewon', 'name_korean': '이태원', 'latitude': 37.5345, 'longitude': 126.9946, 'aliases': 'itaewon-dong'},
    {'name': 'hongdae', 'name_korean': '홍대', 'latitude': 37.5563, 'longitude': 126.9237, 'aliases': 'hongik, hongik university, 홍익대'},
    {'name': 'gangnam', 'name_korean': '강남', 'latitude': 37.4979, 'longitude': 127.0276, 'aliases': 'gangnam-gu'},
    {'name': 'myeongdong', 'name_korean': '명동', 'latitude': 37.5636, 'longitude': 126.9869, 'aliases': ''},
    {'name': 'sinchon', 'name_korean': '신촌', 'latitude': 37.5550, 'longitude': 126.9368, 'aliases': ''},
    {'name': 'jongno', 'name_korean': '종로', 'latitude': 37.5704, 'longitude': 126.9922, 'aliases': 'jongno-gu, 종로구'},
    {'name': 'dongdaemun', 'name_korean': '동대문', 'latitude': 37.5711, 'longitude': 127.0095, 'aliases': 'ddm'},
    {'name': 'insadong', 'name_korean': '인사동', 'latitude': 37.5741, 'longitude': 126.9870, 'aliases': ''},
    {'name': 'apgujeong', 'name_korean': '압구정', 'latitude': 37.5270, 'longitude': 127.0286, 'aliases': ''},
    {'name': 'yeouido', 'name_korean': '여의도', 'latitude': 37.5217, 'longitude': 126.9243, 'aliases': ''},
    {'name': 'mapo', 'name_korean': '마포', 'latitude': 37.5537, 'longitude': 126.9536, 'aliases': 'mapo-gu, 마포구'},
    {'name': 'yongsan', 'name_korean': '용산', 'latitude': 37.5299, 'longitude': 126.9648, 'aliases': 'yongsan-gu, 용산구'},
    {'name': 'seoul station', 'name_korean': '서울역', 'latitude': 37.5547, 'longitude': 126.9707, 'aliases': 'seoul'},
    
    # Additional Seoul areas
    {'name': 'gwanghwamun', 'name_korean': '광화문', 'latitude': 37.5760, 'longitude': 126.9769, 'aliases': ''},
    {'name': 'gangbuk', 'name_korean': '강북', 'latitude': 37.6397, 'longitude': 127.0255, 'aliases': 'gangbuk-gu'},
    {'name': 'songpa', 'name_korean': '송파', 'latitude': 37.5048, 'longitude': 127.1127, 'aliases': 'songpa-gu, 송파구'},
    {'name': 'nowon', 'name_korean': '노원', 'latitude': 37.6543, 'longitude': 127.0568, 'aliases': 'nowon-gu'},
    {'name': 'sindorim', 'name_korean': '신도림', 'latitude': 37.5089, 'longitude': 126.8915, 'aliases': ''},
    {'name': 'coex', 'name_korean': '코엑스', 'latitude': 37.5121, 'longitude': 127.0590, 'aliases': 'samseong'},
    
    # Other major Korean cities
    {'name': 'busan', 'name_korean': '부산', 'latitude': 35.1796, 'longitude': 129.0756, 'aliases': ''},
    {'name': 'incheon', 'name_korean': '인천', 'latitude': 37.4563, 'longitude': 126.7052, 'aliases': ''},
    {'name': 'daegu', 'name_korean': '대구', 'latitude': 35.8714, 'longitude': 128.6014, 'aliases': ''},
    {'name': 'daejeon', 'name_korean': '대전', 'latitude': 36.3504, 'longitude': 127.3845, 'aliases': ''},
    {'name': 'gwangju', 'name_korean': '광주', 'latitude': 35.1595, 'longitude': 126.8526, 'aliases': ''},
    {'name': 'ulsan', 'name_korean': '울산', 'latitude': 35.5384, 'longitude': 129.3114, 'aliases': ''},
    {'name': 'suwon', 'name_korean': '수원', 'latitude': 37.2636, 'longitude': 127.0286, 'aliases': ''},
    {'name': 'jeonju', 'name_korean': '전주', 'latitude': 35.8242, 'longitude': 127.1480, 'aliases': ''},
    {'name': 'jeju', 'name_korean': '제주', 'latitude': 33.4996, 'longitude': 126.5312, 'aliases': 'jeju island, 제주도'},
]


class Command(BaseCommand):
    help = 'Populate ProximityLocation model with default Korean locations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing locations before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_count = ProximityLocation.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing locations'))

        created_count = 0
        updated_count = 0

        for loc_data in DEFAULT_LOCATIONS:
            obj, created = ProximityLocation.objects.update_or_create(
                name=loc_data['name'],
                defaults={
                    'name_korean': loc_data['name_korean'],
                    'latitude': loc_data['latitude'],
                    'longitude': loc_data['longitude'],
                    'aliases': loc_data.get('aliases', ''),
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {obj.name} ({obj.name_korean})")
            else:
                updated_count += 1
                self.stdout.write(f"  Updated: {obj.name} ({obj.name_korean})")

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created: {created_count}, Updated: {updated_count}'
        ))
