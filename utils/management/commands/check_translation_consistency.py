"""
Django management command to check translation consistency across languages.

Usage:
    python manage.py check_translation_consistency [--fix-terminology] [--report]

This command ensures that key terminology is consistently translated across
all languages and identifies inconsistencies in translation approaches.

Author: Halal Korea Development Team
Created: 2025-01-22
"""

import re
from pathlib import Path
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.conf import settings
from utils.translation_guidelines import TranslationGuidelines


class Command(BaseCommand):
    help = 'Check translation consistency across languages'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-terminology',
            action='store_true',
            help='Auto-fix known terminology inconsistencies'
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generate detailed consistency report'
        )
        parser.add_argument(
            '--category',
            type=str,
            choices=['halal', 'korea', 'ui'],
            help='Check specific terminology category'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Translation Consistency Checker'))
        self.stdout.write('=' * 45)
        
        guidelines = TranslationGuidelines()
        
        # Check terminology consistency
        inconsistencies = self.check_terminology_consistency(guidelines, options.get('category'))
        
        # Check translation patterns
        pattern_issues = self.check_translation_patterns()
        
        # Check formality consistency
        formality_issues = self.check_formality_consistency()
        
        # Report findings
        self.report_inconsistencies(inconsistencies, pattern_issues, formality_issues)
        
        # Generate detailed report if requested
        if options['report']:
            self.generate_consistency_report(inconsistencies, pattern_issues, formality_issues)
        
        # Auto-fix if requested
        if options['fix_terminology']:
            self.fix_terminology_issues(inconsistencies)
    
    def check_terminology_consistency(self, guidelines: TranslationGuidelines, category: str = None) -> dict:
        """Check consistency of specialized terminology."""
        inconsistencies = defaultdict(list)
        
        categories = [category] if category else ['halal', 'korea']
        
        for cat in categories:
            self.stdout.write(f'\n📚 Checking {cat} terminology...')
            
            # Get terminology for all languages
            en_terms = guidelines.get_terminology('en', cat)
            ko_terms = guidelines.get_terminology('ko', cat)
            uz_terms = guidelines.get_terminology('uz', cat)
            
            # Check each language's .po file
            for lang in ['ko', 'uz']:
                lang_terms = ko_terms if lang == 'ko' else uz_terms
                po_inconsistencies = self.check_po_terminology(lang, en_terms, lang_terms)
                
                if po_inconsistencies:
                    inconsistencies[f'{lang}_{cat}'] = po_inconsistencies
        
        return dict(inconsistencies)
    
    def check_po_terminology(self, language_code: str, en_terms: dict, lang_terms: dict) -> list:
        """Check terminology usage in a specific .po file."""
        inconsistencies = []
        
        locale_path = Path(settings.BASE_DIR) / 'locale' / language_code / 'LC_MESSAGES'
        po_file = locale_path / 'django.po'
        
        if not po_file.exists():
            return inconsistencies
        
        try:
            with open(po_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse msgid-msgstr pairs
            entries = self.parse_po_entries(content)
            
            for line_num, (msgid, msgstr) in entries:
                if not msgid.strip() or not msgstr.strip():
                    continue
                
                # Check if English msgid contains terminology
                for en_term, expected_translation in lang_terms.items():
                    # Use whole-term matching to avoid false positives
                    # (e.g., "gu" matching inside "guide").
                    source_term = en_term.replace('_', ' ')
                    source_regex = re.compile(rf'\b{re.escape(source_term)}\b', re.IGNORECASE)
                    msgid_matches = list(source_regex.finditer(msgid))

                    if msgid_matches:
                        # Check if translation uses expected term
                        accepted_terms = self.get_accepted_terms(language_code, en_term, expected_translation)
                        if not any(term.lower() in msgstr.lower() for term in accepted_terms):
                            # Preserve project brand name without forcing localized terms.
                            if en_term in {'halal', 'korea'} and re.search(r'\bHalal Korea\b', msgstr, re.IGNORECASE):
                                continue
                            inconsistencies.append({
                                'line': line_num,
                                'english_term': en_term,
                                'expected_translation': expected_translation,
                                'msgid': msgid,
                                'msgstr': msgstr,
                                'type': 'missing_expected_term'
                            })
                    
                    # Check if translation incorrectly uses English term
                    elif language_code != 'en' and re.search(rf'\b{re.escape(source_term)}\b', msgstr, re.IGNORECASE):
                        if en_term in {'halal', 'korea'} and re.search(r'\bHalal Korea\b', msgstr, re.IGNORECASE):
                            continue
                        inconsistencies.append({
                            'line': line_num,
                            'english_term': en_term,
                            'expected_translation': expected_translation,
                            'msgid': msgid,
                            'msgstr': msgstr,
                            'type': 'english_term_in_translation'
                        })
        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Warning: Could not check {language_code} terminology: {e}')
            )
        
        return inconsistencies

    def get_accepted_terms(self, language_code: str, en_term: str, expected_translation: str) -> list:
        """Return acceptable localized variants for a terminology term."""
        aliases = {
            'ko': {
                'korea': ['한국', '대한민국', '코리아'],
                'south_korea': ['대한민국', '한국', '남한'],
                'korean': ['한국어', '한국의', '한국'],
                'mosque': ['모스크', '사원'],
            },
            'uz': {
                'korea': ['Koreya', 'Janubiy Koreya'],
                'south_korea': ['Janubiy Koreya', 'Koreya'],
                'korean': ['koreys', 'koreyscha'],
                'busan': ['Pusan', 'Busan'],
                'daegu': ['Tegu', 'Daegu'],
                'halal': ['halol', 'Halal'],
            },
        }
        language_aliases = aliases.get(language_code, {})
        terms = [expected_translation]
        terms.extend(language_aliases.get(en_term, []))
        return list(dict.fromkeys(terms))
    
    def check_translation_patterns(self) -> dict:
        """Check for consistent translation patterns."""
        pattern_issues = defaultdict(list)
        
        self.stdout.write('\n🔍 Checking translation patterns...')
        
        # Common patterns to check
        patterns = {
            'questions': r'\?$',
            'imperatives': r'^(Please|Click|Select|Choose|Enter)',
            'error_messages': r'^(Error|Invalid|Missing|Required)',
            'success_messages': r'^(Success|Complete|Done|Saved)',
        }
        
        for lang in ['ko', 'uz']:
            for pattern_name, pattern in patterns.items():
                issues = self.check_pattern_consistency(lang, pattern_name, pattern)
                if issues:
                    pattern_issues[f'{lang}_{pattern_name}'] = issues
        
        return dict(pattern_issues)
    
    def check_pattern_consistency(self, language_code: str, pattern_name: str, pattern: str) -> list:
        """Check consistency of a specific translation pattern."""
        issues = []
        
        locale_path = Path(settings.BASE_DIR) / 'locale' / language_code / 'LC_MESSAGES'
        po_file = locale_path / 'django.po'
        
        if not po_file.exists():
            return issues
        
        try:
            with open(po_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entries = self.parse_po_entries(content)
            
            # Collect translations for this pattern
            pattern_translations = []
            
            for line_num, (msgid, msgstr) in entries:
                if re.search(pattern, msgid, re.IGNORECASE):
                    pattern_translations.append({
                        'line': line_num,
                        'msgid': msgid,
                        'msgstr': msgstr
                    })
            
            # Analyze consistency within this pattern
            if len(pattern_translations) > 1:
                consistency_analysis = self.analyze_pattern_consistency(
                    pattern_translations, pattern_name, language_code
                )
                issues.extend(consistency_analysis)
        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Warning: Could not check {language_code} patterns: {e}')
            )
        
        return issues
    
    def analyze_pattern_consistency(self, translations: list, pattern_name: str, language_code: str) -> list:
        """Analyze consistency within a group of translations."""
        issues = []
        
        # For questions in Korean, check for consistent question endings
        if pattern_name == 'questions' and language_code == 'ko':
            endings = []
            for trans in translations:
                msgstr = trans['msgstr'].strip()
                if msgstr:
                    # Extract last few characters
                    ending = msgstr[-3:] if len(msgstr) >= 3 else msgstr
                    endings.append(ending)
            
            # Check if multiple different endings are used
            unique_endings = set(endings)
            # Korean questions naturally vary by context; only flag extreme variation.
            if len(unique_endings) > 5:
                issues.append({
                    'type': 'inconsistent_question_endings',
                    'pattern': pattern_name,
                    'details': f'Found {len(unique_endings)} different question endings',
                    'examples': list(unique_endings)[:5]
                })
        
        # For imperatives, check formality consistency
        elif pattern_name == 'imperatives':
            guidelines = TranslationGuidelines()
            expected_formality = guidelines.get_tone_guidelines(language_code).get('imperatives')
            
            if expected_formality == 'polite' and language_code == 'ko':
                # Check if Korean imperatives use polite forms
                non_polite_count = 0
                for trans in translations:
                    msgstr = trans['msgstr'].strip()
                    # Simple check for polite endings (-세요, -습니다)
                    if msgstr and not re.search(r'(세요|습니다)$', msgstr):
                        non_polite_count += 1
                
                if non_polite_count > len(translations) * 0.3:  # More than 30% non-polite
                    issues.append({
                        'type': 'inconsistent_formality',
                        'pattern': pattern_name,
                        'details': f'{non_polite_count}/{len(translations)} imperatives not using polite forms',
                        'language': language_code
                    })
        
        return issues
    
    def check_formality_consistency(self) -> dict:
        """Check overall formality consistency."""
        formality_issues = {}
        
        self.stdout.write('\n🎩 Checking formality consistency...')
        
        guidelines = TranslationGuidelines()
        
        for lang in ['ko', 'uz']:
            expected_formality = guidelines.get_tone_guidelines(lang).get('formality')
            issues = self.analyze_formality_in_language(lang, expected_formality)
            
            if issues:
                formality_issues[lang] = issues
        
        return formality_issues
    
    def analyze_formality_in_language(self, language_code: str, expected_formality: str) -> list:
        """Analyze formality consistency in a specific language."""
        issues = []
        
        if language_code == 'ko' and expected_formality == 'polite':
            # Check Korean translations for consistent politeness
            locale_path = Path(settings.BASE_DIR) / 'locale' / language_code / 'LC_MESSAGES'
            po_file = locale_path / 'django.po'
            
            if not po_file.exists():
                return issues
            
            try:
                with open(po_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                entries = self.parse_po_entries(content)
                
                formal_count = 0
                informal_count = 0
                total_sentences = 0
                
                for line_num, (msgid, msgstr) in entries:
                    if not msgstr.strip():
                        continue
                    
                    # Count sentences (rough approximation)
                    sentences = re.split(r'[.!?]', msgstr)
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) > 5:  # Ignore very short fragments
                            total_sentences += 1
                            
                            # Check for formal endings
                            if re.search(r'(습니다|세요|됩니다|입니다)$', sentence):
                                formal_count += 1
                            elif re.search(r'[가-힣](다|야|어|아)$', sentence):
                                informal_count += 1
                
                if total_sentences > 10:  # Only analyze if sufficient data
                    informal_ratio = informal_count / total_sentences
                    if informal_ratio > 0.2:  # More than 20% informal
                        issues.append({
                            'type': 'mixed_formality',
                            'formal_count': formal_count,
                            'informal_count': informal_count,
                            'total_sentences': total_sentences,
                            'informal_ratio': informal_ratio
                        })
            
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Warning: Could not analyze {language_code} formality: {e}')
                )
        
        return issues
    
    def parse_po_entries(self, content: str) -> list:
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
            
            if msgid:  # Include even if msgstr is empty for analysis
                entries.append((line_num, (msgid, msgstr)))
        
        return entries
    
    def report_inconsistencies(self, inconsistencies: dict, pattern_issues: dict, formality_issues: dict):
        """Report all found inconsistencies."""
        total_issues = (len(inconsistencies) + len(pattern_issues) + len(formality_issues))
        
        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No consistency issues found!'))
            return
        
        self.stdout.write(f'\n📊 CONSISTENCY ANALYSIS RESULTS')
        self.stdout.write('=' * 35)
        self.stdout.write(f'Found {total_issues} consistency issues')
        
        # Report terminology inconsistencies
        if inconsistencies:
            self.stdout.write(f'\n📚 Terminology Issues:')
            for category, issues in inconsistencies.items():
                self.stdout.write(f'  {category}: {len(issues)} issues')
                for issue in issues[:3]:  # Show first 3 examples
                    self.stdout.write(f'    • Line {issue["line"]}: {issue["type"]}')
                    if issue.get('expected_translation'):
                        self.stdout.write(f'      Expected: {issue["expected_translation"]}')
        
        # Report pattern issues
        if pattern_issues:
            self.stdout.write(f'\n🔍 Pattern Issues:')
            for pattern, issues in pattern_issues.items():
                self.stdout.write(f'  {pattern}: {len(issues)} issues')
        
        # Report formality issues
        if formality_issues:
            self.stdout.write(f'\n🎩 Formality Issues:')
            for lang, issues in formality_issues.items():
                for issue in issues:
                    if issue['type'] == 'mixed_formality':
                        self.stdout.write(
                            f'  {lang}: {issue["informal_ratio"]:.1%} informal usage '
                            f'({issue["informal_count"]}/{issue["total_sentences"]} sentences)'
                        )
    
    def generate_consistency_report(self, inconsistencies: dict, pattern_issues: dict, formality_issues: dict):
        """Generate detailed consistency report."""
        self.stdout.write('\n📄 Generating detailed report...')
        # This would generate a detailed report file
        # Implementation would create JSON/CSV report with all findings
        self.stdout.write(f'Report would include {len(inconsistencies)} terminology issues')
    
    def fix_terminology_issues(self, inconsistencies: dict):
        """Auto-fix known terminology inconsistencies."""
        self.stdout.write('\n🔧 Auto-fixing terminology issues...')
        
        fixed_count = 0
        for category, issues in inconsistencies.items():
            for issue in issues:
                if issue['type'] == 'english_term_in_translation':
                    # This would implement actual fixes to .po files
                    self.stdout.write(f'  Would fix: {issue["english_term"]} → {issue["expected_translation"]}')
                    fixed_count += 1
        
        if fixed_count > 0:
            self.stdout.write(f'✅ Would fix {fixed_count} terminology issues')
            self.stdout.write('⚠️  Actual fixing not implemented yet - requires careful validation')
        else:
            self.stdout.write('ℹ️  No auto-fixable issues found')
