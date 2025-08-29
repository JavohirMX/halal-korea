"""
Django management command - Translation Assistant

A comprehensive assistant for managing translations with interactive guidance.

Usage:
    python manage.py translation_assistant [--auto] [--language LANG]

This command provides an interactive interface for:
- Checking translation status
- Running validation
- Getting improvement suggestions
- Managing translation workflow

Author: Halal Korea Development Team
Created: 2025-01-22
"""

import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from utils.translation_guidelines import TranslationMetrics


class Command(BaseCommand):
    help = 'Interactive translation management assistant'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Run automated checks without interactive prompts'
        )
        parser.add_argument(
            '--language',
            type=str,
            choices=['ko', 'uz', 'en'],
            help='Focus on specific language'
        )
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Quick status check only'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Translation Assistant'))
        self.stdout.write('=' * 40)
        
        if options['quick']:
            self.quick_status()
            return
        
        if options['auto']:
            self.automated_workflow(options.get('language'))
        else:
            self.interactive_workflow(options.get('language'))
    
    def quick_status(self):
        """Quick status overview."""
        self.stdout.write('📊 Quick Status Check')
        self.stdout.write('-' * 25)
        
        languages = ['ko', 'uz']
        for lang in languages:
            completion = self.get_completion_rate(lang)
            if completion >= 95:
                status = self.style.SUCCESS('✅ Complete')
            elif completion >= 70:
                status = self.style.WARNING('⚠️  Needs work')
            else:
                status = self.style.ERROR('❌ Incomplete')
            
            self.stdout.write(f'{lang.upper()}: {completion:.1f}% {status}')
    
    def automated_workflow(self, target_language=None):
        """Run automated checks and provide recommendations."""
        self.stdout.write('🔄 Running automated workflow...\n')
        
        # Step 1: Status check
        self.stdout.write('1️⃣  Checking translation status...')
        if target_language:
            call_command('translation_status', language=target_language)
        else:
            call_command('translation_status')
        
        # Step 2: Validation
        self.stdout.write('\n2️⃣  Validating translations...')
        if target_language:
            call_command('validate_translations', language=target_language, severity='warning')
        else:
            call_command('validate_translations', severity='warning')
        
        # Step 3: Consistency check
        self.stdout.write('\n3️⃣  Checking consistency...')
        call_command('check_translation_consistency')
        
        # Step 4: Recommendations
        self.stdout.write('\n4️⃣  Generating recommendations...')
        self.provide_recommendations(target_language)
    
    def interactive_workflow(self, target_language=None):
        """Interactive translation management workflow."""
        self.stdout.write('🎯 Interactive Translation Assistant')
        self.stdout.write('Choose what you\'d like to do:\n')
        
        options = [
            ('1', 'Check translation status', 'status'),
            ('2', 'Validate translations', 'validate'),
            ('3', 'Check consistency', 'consistency'),
            ('4', 'Get recommendations', 'recommendations'),
            ('5', 'Full analysis', 'full'),
            ('6', 'Quick fix guidance', 'fix'),
            ('q', 'Quit', 'quit')
        ]
        
        for opt, desc, _ in options:
            self.stdout.write(f'{opt}. {desc}')
        
        while True:
            choice = input('\nSelect option (1-6, q): ').strip().lower()
            
            if choice == 'q':
                self.stdout.write('👋 Goodbye!')
                break
            elif choice == '1':
                self.run_status_check(target_language)
            elif choice == '2':
                self.run_validation(target_language)
            elif choice == '3':
                self.run_consistency_check()
            elif choice == '4':
                self.provide_recommendations(target_language)
            elif choice == '5':
                self.run_full_analysis(target_language)
            elif choice == '6':
                self.provide_fix_guidance()
            else:
                self.stdout.write('Invalid option. Please try again.')
    
    def run_status_check(self, target_language=None):
        """Run translation status check."""
        self.stdout.write('\n📊 Translation Status')
        self.stdout.write('-' * 20)
        
        if target_language:
            call_command('translation_status', language=target_language, detailed=True)
        else:
            call_command('translation_status', detailed=True)
        
        self.press_enter_to_continue()
    
    def run_validation(self, target_language=None):
        """Run translation validation."""
        self.stdout.write('\n🔍 Translation Validation')
        self.stdout.write('-' * 25)
        
        if target_language:
            call_command('validate_translations', language=target_language)
        else:
            call_command('validate_translations')
        
        self.press_enter_to_continue()
    
    def run_consistency_check(self):
        """Run consistency check."""
        self.stdout.write('\n🔍 Consistency Check')
        self.stdout.write('-' * 20)
        
        call_command('check_translation_consistency')
        self.press_enter_to_continue()
    
    def run_full_analysis(self, target_language=None):
        """Run comprehensive analysis."""
        self.stdout.write('\n🎯 Full Translation Analysis')
        self.stdout.write('-' * 30)
        
        # Status
        self.stdout.write('\n📊 Current Status:')
        if target_language:
            call_command('translation_status', language=target_language)
        else:
            call_command('translation_status')
        
        # Validation
        self.stdout.write('\n🔍 Validation Results:')
        if target_language:
            call_command('validate_translations', language=target_language, severity='warning')
        else:
            call_command('validate_translations', severity='warning')
        
        # Consistency
        self.stdout.write('\n🔍 Consistency Check:')
        call_command('check_translation_consistency')
        
        # Recommendations
        self.stdout.write('\n💡 Recommendations:')
        self.provide_recommendations(target_language)
        
        self.press_enter_to_continue()
    
    def provide_recommendations(self, target_language=None):
        """Provide actionable recommendations."""
        self.stdout.write('\n💡 Translation Recommendations')
        self.stdout.write('-' * 30)
        
        languages = [target_language] if target_language else ['ko', 'uz']
        
        for lang in languages:
            completion = self.get_completion_rate(lang)
            self.stdout.write(f'\n🌐 {lang.upper()} Language:')
            
            if completion < 50:
                self.stdout.write('🚨 Priority: High - Major translation work needed')
                self.stdout.write('  1. Start with core UI elements')
                self.stdout.write('  2. Focus on user-facing messages')
                self.stdout.write('  3. Use terminology guidelines for consistency')
            elif completion < 80:
                self.stdout.write('⚠️  Priority: Medium - Completion push needed')
                self.stdout.write('  1. Identify missing critical translations')
                self.stdout.write('  2. Run validation to fix quality issues')
                self.stdout.write('  3. Review formality and tone')
            elif completion < 95:
                self.stdout.write('✅ Priority: Low - Quality refinement')
                self.stdout.write('  1. Polish existing translations')
                self.stdout.write('  2. Ensure terminology consistency')
                self.stdout.write('  3. Validate technical accuracy')
            else:
                self.stdout.write('🎉 Status: Excellent - Maintenance mode')
                self.stdout.write('  1. Regular validation checks')
                self.stdout.write('  2. New feature translation as needed')
                self.stdout.write('  3. User feedback integration')
        
        # General recommendations
        self.stdout.write('\n🎯 Next Steps:')
        self.stdout.write('1. python manage.py makemessages -l ko -l uz  # Extract new strings')
        self.stdout.write('2. Edit .po files with translations')
        self.stdout.write('3. python manage.py validate_translations  # Check quality')
        self.stdout.write('4. python manage.py compilemessages  # Apply changes')
        
        if not target_language:
            self.press_enter_to_continue()
    
    def provide_fix_guidance(self):
        """Provide guidance for fixing common issues."""
        self.stdout.write('\n🔧 Quick Fix Guidance')
        self.stdout.write('-' * 22)
        
        fixes = [
            ('Missing placeholders', 'Ensure {{ variables }} are preserved in translations'),
            ('English terms in Korean', 'Use 할랄 for halal, 무슬림 for Muslim, 모스크 for mosque'),
            ('English terms in Uzbek', 'Use halol for halal, musulmon for Muslim, masjid for mosque'),
            ('Informal Korean', 'Use -습니다/-세요 endings for polite form'),
            ('Broken HTML tags', 'Copy all <tags> exactly as they appear in English'),
            ('Wrong punctuation', 'Korean uses . not 。, Uzbek uses Latin punctuation'),
        ]
        
        for issue, solution in fixes:
            self.stdout.write(f'❓ {issue}:')
            self.stdout.write(f'   ✅ {solution}\n')
        
        self.stdout.write('💡 Pro tip: Run validation after each fix to check progress!')
        self.press_enter_to_continue()
    
    def get_completion_rate(self, language_code: str) -> float:
        """Get completion rate for a language."""
        try:
            from pathlib import Path
            locale_path = Path(settings.BASE_DIR) / 'locale' / language_code / 'LC_MESSAGES'
            po_file = locale_path / 'django.po'
            
            if po_file.exists():
                metrics = TranslationMetrics.calculate_completion_rate(str(po_file))
                return metrics['rate']
        except Exception:
            pass
        return 0.0
    
    def press_enter_to_continue(self):
        """Wait for user input to continue."""
        input('\nPress Enter to continue...')
        self.stdout.write('')  # Add blank line
