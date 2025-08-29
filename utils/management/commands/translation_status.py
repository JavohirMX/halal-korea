"""
Django management command to show comprehensive translation status and metrics.

Usage:
    python manage.py translation_status [--detailed] [--language LANG]

This command provides an overview of translation completion, quality metrics,
and identifies areas that need attention across all supported languages.

Author: Halal Korea Development Team
Created: 2025-01-22
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from utils.translation_guidelines import TranslationMetrics, TranslationGuidelines


class Command(BaseCommand):
    help = 'Show comprehensive translation status and metrics'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed breakdown by category'
        )
        parser.add_argument(
            '--language',
            type=str,
            help='Show status for specific language only',
            choices=['ko', 'uz', 'en']
        )
        parser.add_argument(
            '--missing',
            action='store_true',
            help='List missing translations'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📊 Translation Status Dashboard'))
        self.stdout.write('=' * 50)
        
        guidelines = TranslationGuidelines()
        languages = [options['language']] if options['language'] else ['ko', 'uz']
        
        overall_stats = {}
        
        for lang in languages:
            stats = self.get_language_stats(lang)
            overall_stats[lang] = stats
            self.show_language_status(lang, stats, options['detailed'])
            
            if options['missing']:
                self.show_missing_translations(lang)
        
        # Show overall summary
        if not options['language']:
            self.show_overall_summary(overall_stats)
        
        # Show recommendations
        self.show_recommendations(overall_stats)
    
    def get_language_stats(self, language_code: str) -> dict:
        """Get comprehensive statistics for a language."""
        locale_path = Path(settings.BASE_DIR) / 'locale' / language_code / 'LC_MESSAGES'
        po_file = locale_path / 'django.po'
        
        if not po_file.exists():
            return {
                'exists': False,
                'completion_rate': 0.0,
                'total_strings': 0,
                'translated_strings': 0,
                'missing_count': 0,
                'file_size': 0,
                'last_modified': None
            }
        
        # Get completion metrics
        metrics = TranslationMetrics.calculate_completion_rate(str(po_file))
        missing = TranslationMetrics.identify_missing_translations(str(po_file))
        
        # File info
        file_stat = po_file.stat()
        
        return {
            'exists': True,
            'completion_rate': metrics['rate'],
            'total_strings': metrics['total'],
            'translated_strings': metrics['completed'],
            'missing_count': len(missing),
            'missing_strings': missing[:10],  # Sample of missing strings
            'file_size': file_stat.st_size,
            'last_modified': file_stat.st_mtime,
            'file_path': str(po_file)
        }
    
    def show_language_status(self, language_code: str, stats: dict, detailed: bool = False):
        """Show status for a specific language."""
        lang_info = TranslationGuidelines.get_language_info(language_code)
        lang_name = lang_info.get('native_name', language_code.upper())
        
        self.stdout.write(f'\n🌐 {lang_name} ({language_code.upper()})')
        self.stdout.write('-' * 30)
        
        if not stats['exists']:
            self.stdout.write(self.style.ERROR('❌ Translation file not found'))
            return
        
        # Completion status
        completion = stats['completion_rate']
        if completion >= 95:
            status_icon = '✅'
            status_style = self.style.SUCCESS
        elif completion >= 80:
            status_icon = '⚠️'
            status_style = self.style.WARNING
        else:
            status_icon = '❌'
            status_style = self.style.ERROR
        
        self.stdout.write(status_style(
            f'{status_icon} Completion: {completion:.1f}% '
            f'({stats["translated_strings"]}/{stats["total_strings"]} strings)'
        ))
        
        # Missing translations
        if stats['missing_count'] > 0:
            self.stdout.write(f'📝 Missing: {stats["missing_count"]} translations')
        
        # File info
        if detailed:
            file_size_kb = stats['file_size'] / 1024
            import datetime
            last_mod = datetime.datetime.fromtimestamp(stats['last_modified'])
            
            self.stdout.write(f'📄 File size: {file_size_kb:.1f} KB')
            self.stdout.write(f'🕒 Last modified: {last_mod.strftime("%Y-%m-%d %H:%M")}')
            
            # Show language-specific info
            self.show_language_specific_info(language_code, detailed)
    
    def show_language_specific_info(self, language_code: str, detailed: bool):
        """Show language-specific information and guidelines."""
        guidelines = TranslationGuidelines()
        lang_info = guidelines.get_language_info(language_code)
        tone_guide = guidelines.get_tone_guidelines(language_code)
        
        if detailed and lang_info:
            self.stdout.write(f'📋 Language info:')
            if lang_info.get('formal_address'):
                self.stdout.write(f'  • Uses formal address forms')
            if lang_info.get('honorifics'):
                self.stdout.write(f'  • Has honorific system')
            
            formality = tone_guide.get('formality', 'neutral')
            self.stdout.write(f'  • Recommended formality: {formality}')
    
    def show_missing_translations(self, language_code: str):
        """Show sample of missing translations."""
        locale_path = Path(settings.BASE_DIR) / 'locale' / language_code / 'LC_MESSAGES'
        po_file = locale_path / 'django.po'
        
        if not po_file.exists():
            return
        
        missing = TranslationMetrics.identify_missing_translations(str(po_file))
        
        if missing:
            self.stdout.write(f'\n📝 Missing translations for {language_code.upper()}:')
            self.stdout.write('-' * 40)
            
            for i, text in enumerate(missing[:10], 1):
                # Truncate long texts
                display_text = text[:60] + '...' if len(text) > 60 else text
                self.stdout.write(f'{i:2d}. "{display_text}"')
            
            if len(missing) > 10:
                self.stdout.write(f'    ... and {len(missing) - 10} more')
    
    def show_overall_summary(self, overall_stats: dict):
        """Show summary across all languages."""
        self.stdout.write(f'\n📈 OVERALL PROJECT STATUS')
        self.stdout.write('=' * 30)
        
        total_strings = 0
        total_translated = 0
        total_missing = 0
        
        for lang, stats in overall_stats.items():
            if stats['exists']:
                total_strings += stats['total_strings']
                total_translated += stats['translated_strings']
                total_missing += stats['missing_count']
        
        if total_strings > 0:
            overall_completion = (total_translated / total_strings) * 100
            self.stdout.write(f'🎯 Overall completion: {overall_completion:.1f}%')
            self.stdout.write(f'📊 Total strings: {total_strings}')
            self.stdout.write(f'✅ Translated: {total_translated}')
            self.stdout.write(f'📝 Missing: {total_missing}')
            
            # Calculate translation workload
            remaining_work = total_missing * len([l for l in overall_stats.keys() if overall_stats[l]['exists']])
            self.stdout.write(f'💼 Estimated work: {remaining_work} translation tasks')
    
    def show_recommendations(self, overall_stats: dict):
        """Show recommendations based on current status."""
        self.stdout.write(f'\n💡 RECOMMENDATIONS')
        self.stdout.write('=' * 20)
        
        recommendations = []
        
        for lang, stats in overall_stats.items():
            if not stats['exists']:
                recommendations.append(f"Create translation file for {lang.upper()}")
            elif stats['completion_rate'] < 50:
                recommendations.append(f"Prioritize {lang.upper()} translations (only {stats['completion_rate']:.0f}% complete)")
            elif stats['missing_count'] > 0:
                recommendations.append(f"Complete {stats['missing_count']} missing {lang.upper()} translations")
        
        # Generic recommendations
        if any(stats.get('missing_count', 0) > 0 for stats in overall_stats.values()):
            recommendations.append("Run translation validation: python manage.py validate_translations")
        
        if all(stats.get('completion_rate', 0) > 90 for stats in overall_stats.values() if stats['exists']):
            recommendations.append("Consider implementing automated translation quality checks")
            recommendations.append("Set up translation memory for consistency")
        
        if not recommendations:
            self.stdout.write(self.style.SUCCESS('🎉 All translations are in good shape!'))
        else:
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(f'{i}. {rec}')
        
        # Show useful commands
        self.stdout.write(f'\n🛠️  USEFUL COMMANDS')
        self.stdout.write('-' * 18)
        self.stdout.write('• python manage.py makemessages -l ko -l uz')
        self.stdout.write('• python manage.py validate_translations --report')
        self.stdout.write('• python manage.py check_translation_consistency')
        self.stdout.write('• python manage.py compilemessages')
