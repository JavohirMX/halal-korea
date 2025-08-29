"""
Django management command to validate translations against quality guidelines.

Usage:
    python manage.py validate_translations [--language LANG] [--fix] [--report]

This command validates all translations in the project against the comprehensive
translation guidelines, checking for:
- Terminology consistency
- Formality and tone
- Placeholder preservation
- HTML tag integrity
- Language-specific conventions
- Translation completeness

Author: Halal Korea Development Team
Created: 2025-01-22
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List
from django.core.management.base import BaseCommand
from django.conf import settings
from utils.translation_guidelines import (
    TranslationValidator, 
    TranslationSeverity,
    TranslationMetrics
)


class Command(BaseCommand):
    help = 'Validate translations against quality guidelines'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--language',
            type=str,
            help='Specific language to validate (ko, uz, en)',
            choices=['ko', 'uz', 'en']
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to auto-fix common issues'
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generate detailed validation report'
        )
        parser.add_argument(
            '--severity',
            type=str,
            choices=['info', 'warning', 'error', 'critical'],
            default='warning',
            help='Minimum severity level to report'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file for report (JSON format)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Translation Validation System'))
        self.stdout.write('=' * 50)
        
        validator = TranslationValidator()
        severity_filter = TranslationSeverity(options['severity'])
        
        # Determine languages to validate
        languages = [options['language']] if options['language'] else ['ko', 'uz']
        
        all_issues = {}
        
        for lang in languages:
            self.stdout.write(f'\n📋 Validating {lang.upper()} translations...')
            issues = self.validate_language(lang, validator, severity_filter)
            all_issues[lang] = issues
            
            self.report_language_summary(lang, issues)
        
        # Generate comprehensive report
        if options['report'] or options['output']:
            self.generate_report(all_issues, options['output'])
        
        # Show overall summary
        self.show_overall_summary(all_issues)
        
        # Auto-fix if requested
        if options['fix']:
            self.auto_fix_issues(all_issues)
    
    def validate_language(self, language_code: str, validator: TranslationValidator, severity_filter: TranslationSeverity) -> List:
        """Validate all translations for a specific language."""
        issues = []
        
        # Find .po files for the language
        locale_path = Path(settings.BASE_DIR) / 'locale' / language_code / 'LC_MESSAGES'
        po_file = locale_path / 'django.po'
        
        if not po_file.exists():
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  No .po file found for {language_code}')
            )
            return issues
        
        # Parse .po file and validate entries
        issues.extend(self.validate_po_file(str(po_file), language_code, validator, severity_filter))
        
        # Validate template usage
        issues.extend(self.validate_template_usage(language_code, validator, severity_filter))
        
        return issues
    
    def validate_po_file(self, po_file_path: str, language_code: str, validator: TranslationValidator, severity_filter: TranslationSeverity) -> List:
        """Validate translations in a .po file."""
        issues = []
        
        try:
            with open(po_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse msgid-msgstr pairs
            entries = self.parse_po_entries(content)
            
            for line_num, (msgid, msgstr) in entries:
                if not msgid.strip() or not msgstr.strip():
                    continue
                
                # Validate each translation
                translation_issues = validator.validate_translation(
                    source_text=msgid,
                    translated_text=msgstr,
                    source_lang='en',
                    target_lang=language_code,
                    context=f"Line {line_num} in {os.path.basename(po_file_path)}"
                )
                
                # Filter by severity
                filtered_issues = [
                    issue for issue in translation_issues 
                    if self.severity_level(issue.severity) >= self.severity_level(severity_filter)
                ]
                
                for issue in filtered_issues:
                    issue.line_number = line_num
                    issue.file_path = po_file_path
                
                issues.extend(filtered_issues)
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Error validating {po_file_path}: {str(e)}')
            )
        
        return issues
    
    def validate_template_usage(self, language_code: str, validator: TranslationValidator, severity_filter: TranslationSeverity) -> List:
        """Validate translation usage in templates."""
        issues = []
        
        # Find template files
        template_dirs = [
            Path(settings.BASE_DIR) / 'places' / 'templates',
            Path(settings.BASE_DIR) / 'users' / 'templates',
            Path(settings.BASE_DIR) / 'blog' / 'templates',
            Path(settings.BASE_DIR) / 'contact' / 'templates',
        ]
        
        for template_dir in template_dirs:
            if template_dir.exists():
                for template_file in template_dir.rglob('*.html'):
                    template_issues = self.validate_template_file(
                        str(template_file), language_code, validator, severity_filter
                    )
                    issues.extend(template_issues)
        
        return issues
    
    def validate_template_file(self, template_path: str, language_code: str, validator: TranslationValidator, severity_filter: TranslationSeverity) -> List:
        """Validate translation tags in a template file."""
        issues = []
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find translate tags
            translate_patterns = [
                r'{% translate ["\']([^"\']+)["\'] %}',
                r'{% trans ["\']([^"\']+)["\'] %}',
                r'{% blocktranslate[^%]*%}(.*?){% endblocktranslate %}',
            ]
            
            line_num = 0
            for line in content.split('\n'):
                line_num += 1
                
                for pattern in translate_patterns:
                    matches = re.finditer(pattern, line, re.DOTALL)
                    for match in matches:
                        text = match.group(1)
                        
                        # Validate the translatable text
                        text_issues = validator.validate_translation(
                            source_text=text,
                            translated_text=text,  # Template validation
                            source_lang='en',
                            target_lang=language_code,
                            context=f"Template {os.path.basename(template_path)}:{line_num}"
                        )
                        
                        # Filter and add context
                        for issue in text_issues:
                            if self.severity_level(issue.severity) >= self.severity_level(severity_filter):
                                issue.line_number = line_num
                                issue.file_path = template_path
                                issues.append(issue)
        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Error validating template {template_path}: {str(e)}')
            )
        
        return issues
    
    def parse_po_entries(self, content: str) -> List[tuple]:
        """Parse msgid-msgstr pairs from .po file content."""
        entries = []
        
        # Split into blocks and find msgid-msgstr pairs
        blocks = re.split(r'\n\s*\n', content)
        
        for block in blocks:
            lines = block.strip().split('\n')
            if not lines:
                continue
            
            msgid = ""
            msgstr = ""
            in_msgid = False
            in_msgstr = False
            line_num = content[:content.find(block)].count('\n') + 1
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('msgid '):
                    msgid = re.match(r'msgid\s+"(.*)"', line)
                    msgid = msgid.group(1) if msgid else ""
                    in_msgid = True
                    in_msgstr = False
                elif line.startswith('msgstr '):
                    msgstr = re.match(r'msgstr\s+"(.*)"', line)
                    msgstr = msgstr.group(1) if msgstr else ""
                    in_msgid = False
                    in_msgstr = True
                elif line.startswith('"') and in_msgid:
                    additional = re.match(r'"(.*)"', line)
                    if additional:
                        msgid += additional.group(1)
                elif line.startswith('"') and in_msgstr:
                    additional = re.match(r'"(.*)"', line)
                    if additional:
                        msgstr += additional.group(1)
            
            if msgid and msgstr:
                entries.append((line_num, (msgid, msgstr)))
        
        return entries
    
    def severity_level(self, severity: TranslationSeverity) -> int:
        """Convert severity to numeric level for comparison."""
        levels = {
            TranslationSeverity.INFO: 1,
            TranslationSeverity.WARNING: 2,
            TranslationSeverity.ERROR: 3,
            TranslationSeverity.CRITICAL: 4,
        }
        return levels.get(severity, 1)
    
    def report_language_summary(self, language_code: str, issues: List) -> None:
        """Report summary for a specific language."""
        if not issues:
            self.stdout.write(f'  ✅ No issues found for {language_code.upper()}')
            return
        
        # Count by severity
        severity_counts = {}
        for issue in issues:
            severity = issue.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        self.stdout.write(f'  📊 Found {len(issues)} issues:')
        for severity, count in severity_counts.items():
            icon = {'info': 'ℹ️', 'warning': '⚠️', 'error': '❌', 'critical': '🚨'}.get(severity, '🔍')
            self.stdout.write(f'    {icon} {severity.title()}: {count}')
        
        # Show a few examples
        if len(issues) > 0:
            self.stdout.write(f'  🔍 Sample issues:')
            for issue in issues[:3]:
                self.stdout.write(f'    • {issue.message}')
                if issue.suggestion:
                    self.stdout.write(f'      💡 {issue.suggestion}')
    
    def generate_report(self, all_issues: Dict, output_file: str = None) -> None:
        """Generate comprehensive validation report."""
        report = {
            'timestamp': str(Path().resolve()),
            'summary': {},
            'languages': {}
        }
        
        total_issues = 0
        for lang, issues in all_issues.items():
            total_issues += len(issues)
            
            # Calculate completion metrics
            locale_path = Path(settings.BASE_DIR) / 'locale' / lang / 'LC_MESSAGES' / 'django.po'
            if locale_path.exists():
                metrics = TranslationMetrics.calculate_completion_rate(str(locale_path))
                missing = TranslationMetrics.identify_missing_translations(str(locale_path))
            else:
                metrics = {'total': 0, 'completed': 0, 'rate': 0.0}
                missing = []
            
            report['languages'][lang] = {
                'completion_rate': metrics['rate'],
                'total_strings': metrics['total'],
                'translated_strings': metrics['completed'],
                'missing_translations': len(missing),
                'validation_issues': len(issues),
                'issues_by_severity': self.group_issues_by_severity(issues),
                'sample_missing': missing[:10] if missing else []
            }
        
        report['summary'] = {
            'total_languages': len(all_issues),
            'total_issues': total_issues,
            'avg_completion_rate': sum(
                lang_data['completion_rate'] for lang_data in report['languages'].values()
            ) / len(report['languages']) if report['languages'] else 0
        }
        
        # Output report
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.stdout.write(f'📄 Report saved to {output_file}')
        else:
            self.stdout.write('\n📊 VALIDATION REPORT')
            self.stdout.write('=' * 30)
            self.stdout.write(f'Total Issues: {total_issues}')
            for lang, data in report['languages'].items():
                self.stdout.write(f'\n{lang.upper()}:')
                self.stdout.write(f'  Completion: {data["completion_rate"]:.1f}%')
                self.stdout.write(f'  Issues: {data["validation_issues"]}')
                if data['missing_translations'] > 0:
                    self.stdout.write(f'  Missing: {data["missing_translations"]} translations')
    
    def group_issues_by_severity(self, issues: List) -> Dict[str, int]:
        """Group issues by severity level."""
        groups = {}
        for issue in issues:
            severity = issue.severity.value
            groups[severity] = groups.get(severity, 0) + 1
        return groups
    
    def show_overall_summary(self, all_issues: Dict) -> None:
        """Show overall validation summary."""
        total_issues = sum(len(issues) for issues in all_issues.values())
        
        self.stdout.write(f'\n🎯 OVERALL SUMMARY')
        self.stdout.write('=' * 20)
        
        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS('🎉 All translations are valid!'))
        else:
            self.stdout.write(f'Found {total_issues} total issues across {len(all_issues)} languages')
            
            # Show top issue types
            all_messages = []
            for issues in all_issues.values():
                all_messages.extend([issue.message for issue in issues])
            
            # Simple frequency count
            message_counts = {}
            for msg in all_messages:
                # Simplify message for grouping
                simplified = re.sub(r'["\'].*?["\']', '<text>', msg)
                simplified = re.sub(r'\d+', '<num>', simplified)
                message_counts[simplified] = message_counts.get(simplified, 0) + 1
            
            self.stdout.write('\n🔝 Most common issues:')
            sorted_issues = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)
            for issue_type, count in sorted_issues[:5]:
                self.stdout.write(f'  • {issue_type}: {count} occurrences')
    
    def auto_fix_issues(self, all_issues: Dict) -> None:
        """Attempt to automatically fix common translation issues."""
        self.stdout.write('\n🔧 AUTO-FIX ATTEMPT')
        self.stdout.write('=' * 20)
        
        fixable_count = 0
        
        for lang, issues in all_issues.items():
            for issue in issues:
                if self.can_auto_fix(issue):
                    if self.apply_auto_fix(issue):
                        fixable_count += 1
        
        if fixable_count > 0:
            self.stdout.write(self.style.SUCCESS(f'✅ Auto-fixed {fixable_count} issues'))
        else:
            self.stdout.write('ℹ️  No auto-fixable issues found')
    
    def can_auto_fix(self, issue) -> bool:
        """Check if an issue can be automatically fixed."""
        auto_fixable_patterns = [
            'Missing placeholder',
            'Extra placeholder',
            'Japanese period found',
            'Asian punctuation found',
        ]
        
        return any(pattern in issue.message for pattern in auto_fixable_patterns)
    
    def apply_auto_fix(self, issue) -> bool:
        """Apply automatic fix for an issue."""
        # This would implement actual fixes to .po files
        # For now, just log what would be fixed
        self.stdout.write(f'  🔧 Would fix: {issue.message}')
        return False  # Don't actually fix yet - needs careful implementation
