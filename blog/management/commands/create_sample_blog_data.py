"""
Management command to create sample blog data for testing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from blog.models import Category, Tag, BlogPost
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample blog data for testing'

    def handle(self, *args, **options):
        # Create categories
        categories_data = [
            {'name': 'Halal Lifestyle', 'description': 'Tips and guides for living a halal lifestyle in Korea'},
            {'name': 'Food & Restaurants', 'description': 'Reviews and recommendations for halal food in Korea'},
            {'name': 'Community', 'description': 'Stories and updates from the halal community'},
            {'name': 'Website Updates', 'description': 'Latest updates and announcements about the website'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f"Created category: {category.name}")

        # Create tags
        tags_data = ['halal', 'korea', 'food', 'lifestyle', 'travel', 'community', 'guide', 'tips']
        tags = {}
        for tag_name in tags_data:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            tags[tag_name] = tag
            if created:
                self.stdout.write(f"Created tag: {tag.name}")

        # Get or create admin user for blog posts
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING("No admin user found. Please create a superuser first."))
            return

        # Create sample blog posts
        posts_data = [
            {
                'title': 'Complete Guide to Halal Food in Seoul',
                'excerpt': 'Discover the best halal restaurants, markets, and food options in Seoul with our comprehensive guide.',
                'content': '''
                <p>Seoul offers a growing number of halal food options for Muslim residents and visitors. From traditional Korean dishes prepared with halal ingredients to authentic Middle Eastern cuisine, the capital city has something for everyone.</p>

                <h2>Top Halal Restaurants in Seoul</h2>
                <p>Here are some of the most popular halal restaurants that you should definitely try:</p>
                <ul>
                    <li><strong>Myeongdong Halal Kitchen</strong> - Authentic Korean-Muslim fusion cuisine</li>
                    <li><strong>Istanbul Restaurant</strong> - Traditional Turkish dishes in the heart of Seoul</li>
                    <li><strong>Arab Kitchen</strong> - Middle Eastern specialties with a Korean twist</li>
                </ul>

                <h2>Halal Markets and Grocery Stores</h2>
                <p>Shopping for halal ingredients is easier than ever with these dedicated halal markets:</p>
                <ul>
                    <li><strong>Seoul Central Halal Market</strong> - Wide variety of halal meat and groceries</li>
                    <li><strong>Itaewon Halal Shop</strong> - Convenient location with imported halal products</li>
                    <li><strong>Online halal delivery services</strong> - Available throughout Seoul</li>
                </ul>

                <p><em>Remember to always verify halal certification when dining out or shopping for ingredients.</em></p>
                ''',
                'category': categories['Food & Restaurants'],
                'tags': [tags['halal'], tags['korea'], tags['food'], tags['guide']],
            },
            {
                'title': 'Living as a Muslim in Korea: A Community Perspective',
                'excerpt': 'Personal experiences and insights from Muslims living in Korea, including challenges and opportunities.',
                'content': '''
                <p>Korea has become home to a growing Muslim community, with people from various backgrounds finding ways to maintain their faith while embracing Korean culture.</p>

                <h2>Finding Community</h2>
                <p>Building connections with fellow Muslims in Korea is essential for maintaining spiritual and social well-being. Here are some ways to connect:</p>
                <ul>
                    <li><strong>Join local mosque communities</strong> in Seoul, Busan, and other major cities</li>
                    <li><strong>Participate in cultural exchange events</strong> organized by various organizations</li>
                    <li><strong>Connect through social media groups</strong> and online forums</li>
                </ul>

                <h2>Balancing Culture and Faith</h2>
                <p>Living in Korea while maintaining Islamic practices requires some adaptation, but the experience can be incredibly rewarding. The Korean people are generally very respectful of different cultures and religions.</p>

                <h2>Support Networks</h2>
                <p><em>Don't hesitate to reach out to established community members who can provide guidance and support during your journey in Korea.</em></p>
                ''',
                'category': categories['Community'],
                'tags': [tags['lifestyle'], tags['community'], tags['korea']],
            },
            {
                'title': 'New Features: Enhanced Search and Mobile Experience',
                'excerpt': 'We\'ve updated our platform with improved search functionality and a better mobile experience for finding halal places.',
                'content': '''
                <p>We're excited to announce several major updates to our platform that will make it easier than ever to find halal places in Korea.</p>

                <h2>Enhanced Search Features</h2>
                <p>Our new search functionality includes:</p>
                <ul>
                    <li><strong>Location-based filtering</strong> with GPS integration</li>
                    <li><strong>Advanced category filtering</strong> (restaurants, markets, mosques, prayer rooms)</li>
                    <li><strong>Real-time availability updates</strong> from our community</li>
                    <li><strong>User ratings and reviews integration</strong> for better decision making</li>
                </ul>

                <h2>Improved Mobile Experience</h2>
                <p>The mobile version of our site now features:</p>
                <ul>
                    <li><strong>Faster loading times</strong> - optimized for mobile networks</li>
                    <li><strong>Intuitive navigation</strong> designed for touch interfaces</li>
                    <li><strong>Offline map functionality</strong> for saved places</li>
                    <li><strong>Quick access to prayer times</strong> from anywhere</li>
                </ul>

                <h2>What's Next?</h2>
                <p><em>We're continuously working on improvements based on user feedback. Stay tuned for more updates including multi-language support enhancements and community features.</em></p>
                ''',
                'category': categories['Website Updates'],
                'tags': [tags['tips'], tags['guide']],
            },
        ]

        for post_data in posts_data:
            # Check if post already exists
            if not BlogPost.objects.filter(title=post_data['title']).exists():
                post = BlogPost.objects.create(
                    title=post_data['title'],
                    excerpt=post_data['excerpt'],
                    content=post_data['content'],
                    category=post_data['category'],
                    author=admin_user,
                    status='published',
                    published_at=timezone.now(),
                    language='en'
                )
                
                # Add tags
                post.tags.set(post_data['tags'])
                
                self.stdout.write(f"Created blog post: {post.title}")
            else:
                self.stdout.write(f"Blog post already exists: {post_data['title']}")

        self.stdout.write(self.style.SUCCESS("Sample blog data created successfully!"))
