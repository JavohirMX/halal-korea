"""
Translation Guidelines and Standards for Halal Korea Project

This module defines comprehensive translation guidelines, standards, and validation
rules to ensure consistent, high-quality multilingual content across the platform.

Author: Halal Korea Development Team
Created: 2025-01-22
Version: 1.0
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from django.conf import settings

logger = logging.getLogger(__name__)


class TranslationSeverity(Enum):
    """Severity levels for translation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TranslationIssue:
    """Represents a translation validation issue."""
    severity: TranslationSeverity
    message: str
    context: str
    suggestion: Optional[str] = None
    line_number: Optional[int] = None
    file_path: Optional[str] = None


class TranslationGuidelines:
    """
    Comprehensive translation guidelines for the Halal Korea project.
    
    This class defines standards, conventions, and validation rules for 
    maintaining high-quality translations across Korean, English, and Uzbek.
    """
    
    # Supported languages with their characteristics
    LANGUAGES = {
        'en': {
            'name': 'English',
            'native_name': 'English',
            'direction': 'ltr',
            'pluralization_rules': 2,  # one, other
            'formal_address': False,
            'honorifics': False,
        },
        'ko': {
            'name': 'Korean',
            'native_name': '한국어',
            'direction': 'ltr',
            'pluralization_rules': 1,  # Korean doesn't have plural forms
            'formal_address': True,
            'honorifics': True,
        },
        'uz': {
            'name': 'Uzbek',
            'native_name': "O'zbek",
            'direction': 'ltr',
            'pluralization_rules': 1,  # Uzbek has limited plural distinction
            'formal_address': True,
            'honorifics': False,
        }
    }
    
    # Critical terms that require specific translations
    HALAL_TERMINOLOGY = {
        'en': {
            'halal': 'halal',
            'haram': 'haram',
            'mosque': 'mosque',
            'prayer_room': 'prayer room',
            'muslim': 'Muslim',
            'islamic': 'Islamic',
            'qibla': 'Qibla',
            'prayer_times': 'prayer times',
            'ramadan': 'Ramadan',
            'iftar': 'Iftar',
            'suhur': 'Suhur',
        },
        'ko': {
            'halal': '할랄',
            'haram': '하람',
            'mosque': '모스크',
            'prayer_room': '기도실',
            'muslim': '무슬림',
            'islamic': '이슬람',
            'qibla': '키블라',
            'prayer_times': '기도 시간',
            'ramadan': '라마단',
            'iftar': '이프타르',
            'suhur': '수후르',
        },
        'uz': {
            'halal': 'halol',
            'haram': 'harom',
            'mosque': 'masjid',
            'prayer_room': 'namoz xonasi',
            'muslim': 'musulmon',
            'islamic': 'islomiy',
            'qibla': 'qibla',
            'prayer_times': 'namoz vaqtlari',
            'ramadan': 'Ramazon',
            'iftar': 'iftorlik',
            'suhur': 'saharlik',
        }
    }
    
    # Location-specific terms for Korea
    KOREA_TERMINOLOGY = {
        'en': {
            'seoul': 'Seoul',
            'busan': 'Busan',
            'incheon': 'Incheon',
            'daegu': 'Daegu',
            'korea': 'Korea',
            'south_korea': 'South Korea',
            'korean': 'Korean',
            'won': 'Won (₩)',
            'subway': 'subway',
            'station': 'station',
            'district': 'district',
            'dong': 'dong',
            'gu': 'gu',
        },
        'ko': {
            'seoul': '서울',
            'busan': '부산',
            'incheon': '인천',
            'daegu': '대구',
            'korea': '한국',
            'south_korea': '대한민국',
            'korean': '한국의',
            'won': '원 (₩)',
            'subway': '지하철',
            'station': '역',
            'district': '구',
            'dong': '동',
            'gu': '구',
        },
        'uz': {
            'seoul': 'Seul',
            'busan': 'Pusan',
            'incheon': 'Incheon',
            'daegu': 'Tegu',
            'korea': 'Koreya',
            'south_korea': 'Janubiy Koreya',
            'korean': 'koreys',
            'won': 'von (₩)',
            'subway': 'metro',
            'station': 'stansiya',
            'district': 'tuman',
            'dong': 'dong',
            'gu': 'gu',
        }
    }
    
    # Context-specific translation patterns
    CONTEXT_PATTERNS = {
        'food_categories': {
            'en': ['restaurant', 'market', 'grocery', 'butcher', 'bakery'],
            'ko': ['음식점', '마켓', '식료품점', '정육점', '베이커리'],
            'uz': ['restoran', 'bozor', 'oziq-ovqat do\'koni', 'qassobxona', 'novvoyxona'],
        },
        'prayer_facilities': {
            'en': ['mosque', 'prayer room', 'Islamic center', 'musalla'],
            'ko': ['모스크', '기도실', '이슬람 센터', '무살라'],
            'uz': ['masjid', 'namoz xonasi', 'islom markazi', 'musallo'],
        },
        'user_actions': {
            'en': ['search', 'find', 'locate', 'navigate', 'review', 'rate'],
            'ko': ['검색', '찾기', '위치 찾기', '안내', '리뷰', '평가'],
            'uz': ['qidirish', 'topish', 'joylashuvini aniqlash', 'yo\'l ko\'rsatish', 'sharh', 'baho'],
        }
    }
    
    # Formality and tone guidelines
    TONE_GUIDELINES = {
        'en': {
            'formality': 'neutral',
            'address_style': 'informal',
            'imperatives': 'direct',
            'questions': 'straightforward',
        },
        'ko': {
            'formality': 'polite',
            'address_style': 'formal_polite',  # -습니다/-세요 endings
            'imperatives': 'polite_request',  # -세요 instead of direct commands
            'questions': 'polite_inquiry',
        },
        'uz': {
            'formality': 'respectful',
            'address_style': 'formal',
            'imperatives': 'polite',
            'questions': 'respectful',
        }
    }
    
    @classmethod
    def get_language_info(cls, language_code: str) -> Dict:
        """Get comprehensive language information."""
        return cls.LANGUAGES.get(language_code, {})
    
    @classmethod
    def get_terminology(cls, language_code: str, category: str = 'halal') -> Dict[str, str]:
        """Get terminology for specific category and language."""
        if category == 'halal':
            return cls.HALAL_TERMINOLOGY.get(language_code, {})
        elif category == 'korea':
            return cls.KOREA_TERMINOLOGY.get(language_code, {})
        return {}
    
    @classmethod
    def get_tone_guidelines(cls, language_code: str) -> Dict:
        """Get tone and formality guidelines for a language."""
        return cls.TONE_GUIDELINES.get(language_code, {})
    
    @classmethod
    def validate_terminology_consistency(cls, text: str, language_code: str) -> List[TranslationIssue]:
        """Validate that specialized terminology is used consistently."""
        issues = []
        
        # Check halal terminology
        halal_terms = cls.HALAL_TERMINOLOGY.get(language_code, {})
        for en_term, local_term in halal_terms.items():
            if language_code == 'en':
                continue

            # Match whole terms only to avoid false positives such as "gu" in "guide".
            term_pattern = re.escape(en_term.replace('_', ' '))
            term_regex = re.compile(rf'\b{term_pattern}\b', re.IGNORECASE)
            matches = list(term_regex.finditer(text))
            if not matches:
                continue

            # Allow project brand name "Halal Korea" without forcing term replacement.
            if en_term in {'halal', 'korea'}:
                brand_regex = re.compile(r'\bHalal Korea\b', re.IGNORECASE)
                brand_count = len(list(brand_regex.finditer(text)))
                if brand_count >= len(matches):
                    continue

            if language_code != 'en' and matches:
                issues.append(TranslationIssue(
                    severity=TranslationSeverity.WARNING,
                    message=f"English term '{en_term}' found in {language_code} text",
                    context=text,
                    suggestion=f"Consider using '{local_term}' instead"
                ))
        
        return issues


class TranslationValidator:
    """
    Comprehensive validation system for translation quality.
    
    Validates translations against guidelines, checks for common issues,
    and ensures consistency across the platform.
    """
    
    def __init__(self):
        self.guidelines = TranslationGuidelines()
        self.issues: List[TranslationIssue] = []
    
    def validate_translation(self, 
                           source_text: str, 
                           translated_text: str, 
                           source_lang: str = 'en', 
                           target_lang: str = 'ko',
                           context: str = '') -> List[TranslationIssue]:
        """
        Comprehensive validation of a translation.
        
        Args:
            source_text: Original text
            translated_text: Translated text
            source_lang: Source language code
            target_lang: Target language code
            context: Additional context information
            
        Returns:
            List of translation issues found
        """
        issues = []
        
        # Basic validation checks
        issues.extend(self._check_length_ratio(source_text, translated_text, source_lang, target_lang))
        issues.extend(self._check_placeholders(source_text, translated_text))
        issues.extend(self._check_html_tags(source_text, translated_text))
        issues.extend(self._check_punctuation(translated_text, target_lang))
        issues.extend(self._check_terminology(translated_text, target_lang))
        issues.extend(self._check_formality(translated_text, target_lang))
        issues.extend(self._check_korean_specific(translated_text) if target_lang == 'ko' else [])
        issues.extend(self._check_uzbek_specific(translated_text) if target_lang == 'uz' else [])
        
        # Add context to all issues
        for issue in issues:
            issue.context = context or f"{source_lang}: {source_text} → {target_lang}: {translated_text}"
        
        return issues
    
    def _check_length_ratio(self, source: str, target: str, source_lang: str, target_lang: str) -> List[TranslationIssue]:
        """Check if translation length is reasonable compared to source."""
        issues = []
        
        if not source or not target:
            issues.append(TranslationIssue(
                severity=TranslationSeverity.CRITICAL,
                message="Empty source or target text",
                context=""
            ))
            return issues
        
        source_len = len(source.strip())
        target_len = len(target.strip())
        
        if source_len == 0:
            return issues
        
        ratio = target_len / source_len
        
        # Language-specific expected ratios
        expected_ratios = {
            ('en', 'ko'): (0.5, 2.0),  # Korean can be more concise or verbose
            ('en', 'uz'): (0.8, 1.5),  # Uzbek usually similar length
            ('ko', 'en'): (0.5, 2.0),
            ('uz', 'en'): (0.7, 1.3),
        }
        
        expected_range = expected_ratios.get((source_lang, target_lang), (0.3, 3.0))
        
        if ratio < expected_range[0]:
            issues.append(TranslationIssue(
                severity=TranslationSeverity.WARNING,
                message=f"Translation seems too short (ratio: {ratio:.2f})",
                context="",
                suggestion="Check if all meaning is preserved"
            ))
        elif ratio > expected_range[1]:
            issues.append(TranslationIssue(
                severity=TranslationSeverity.WARNING,
                message=f"Translation seems too long (ratio: {ratio:.2f})",
                context="",
                suggestion="Consider more concise phrasing"
            ))
        
        return issues
    
    def _check_placeholders(self, source: str, target: str) -> List[TranslationIssue]:
        """Check that all placeholders are preserved in translation."""
        issues = []
        
        # Django template variables: {{ variable }}
        source_vars = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', source))
        target_vars = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', target))
        
        missing_vars = source_vars - target_vars
        extra_vars = target_vars - source_vars
        
        for var in missing_vars:
            issues.append(TranslationIssue(
                severity=TranslationSeverity.ERROR,
                message=f"Missing placeholder: {{{{ {var} }}}}",
                context="",
                suggestion=f"Add {{{{ {var} }}}} to translation"
            ))
        
        for var in extra_vars:
            issues.append(TranslationIssue(
                severity=TranslationSeverity.ERROR,
                message=f"Extra placeholder: {{{{ {var} }}}}",
                context="",
                suggestion=f"Remove {{{{ {var} }}}} or check source"
            ))
        
        # Python format strings: {variable} or {0}, {1}
        source_formats = set(re.findall(r'\{([^}]+)\}', source))
        target_formats = set(re.findall(r'\{([^}]+)\}', target))
        
        missing_formats = source_formats - target_formats
        
        for fmt in missing_formats:
            issues.append(TranslationIssue(
                severity=TranslationSeverity.ERROR,
                message=f"Missing format placeholder: {{{fmt}}}",
                context="",
                suggestion=f"Add {{{fmt}}} to translation"
            ))
        
        return issues
    
    def _check_html_tags(self, source: str, target: str) -> List[TranslationIssue]:
        """Check that HTML tags are properly preserved."""
        issues = []
        
        # Find HTML tags
        source_tags = re.findall(r'<[^>]+>', source)
        target_tags = re.findall(r'<[^>]+>', target)
        
        # Simple check for tag count (more sophisticated parsing could be added)
        if len(source_tags) != len(target_tags):
            issues.append(TranslationIssue(
                severity=TranslationSeverity.ERROR,
                message=f"HTML tag count mismatch: source has {len(source_tags)}, target has {len(target_tags)}",
                context="",
                suggestion="Ensure all HTML tags are preserved in translation"
            ))
        
        return issues
    
    def _check_punctuation(self, text: str, language: str) -> List[TranslationIssue]:
        """Check punctuation conventions for specific languages."""
        issues = []
        
        if language == 'ko':
            # Korean-specific punctuation checks
            if '。' in text:
                issues.append(TranslationIssue(
                    severity=TranslationSeverity.WARNING,
                    message="Japanese period found in Korean text",
                    context=text,
                    suggestion="Use Korean period (.) instead of Japanese (。)"
                ))
            
            # Check for proper spacing around Korean punctuation
            if re.search(r'[가-힣][!?]', text):
                issues.append(TranslationIssue(
                    severity=TranslationSeverity.INFO,
                    message="Consider spacing before exclamation/question marks in Korean",
                    context=text
                ))
        
        elif language == 'uz':
            # Uzbek-specific punctuation (uses Latin script punctuation)
            if '，' in text or '。' in text:
                issues.append(TranslationIssue(
                    severity=TranslationSeverity.WARNING,
                    message="Asian punctuation found in Uzbek text",
                    context=text,
                    suggestion="Use Latin punctuation marks"
                ))
        
        return issues
    
    def _check_terminology(self, text: str, language: str) -> List[TranslationIssue]:
        """Check for consistent use of specialized terminology."""
        return self.guidelines.validate_terminology_consistency(text, language)
    
    def _check_formality(self, text: str, language: str) -> List[TranslationIssue]:
        """Check formality level according to language guidelines."""
        issues = []
        tone_guide = self.guidelines.get_tone_guidelines(language)
        
        if language == 'ko' and tone_guide.get('formality') == 'polite':
            # Check for informal endings in Korean
            informal_patterns = [r'야\s*$', r'어\s*$', r'아\s*$']
            for pattern in informal_patterns:
                if re.search(pattern, text):
                    issues.append(TranslationIssue(
                        severity=TranslationSeverity.WARNING,
                        message="Informal Korean detected, consider using polite form",
                        context=text,
                        suggestion="Use -습니다/-세요 endings for formal tone"
                    ))
        
        return issues
    
    def _check_korean_specific(self, text: str) -> List[TranslationIssue]:
        """Korean-specific validation checks."""
        issues = []
        
        # Check for proper Hangeul usage
        if re.search(r'[ㄱ-ㅎㅏ-ㅣ]', text):
            issues.append(TranslationIssue(
                severity=TranslationSeverity.ERROR,
                message="Incomplete Hangeul characters found",
                context=text,
                suggestion="Complete all Hangeul syllables"
            ))
        
        # Check for mixed script issues
        if re.search(r'[가-힣][a-zA-Z][가-힣]', text):
            issues.append(TranslationIssue(
                severity=TranslationSeverity.INFO,
                message="Mixed Korean-English text without spacing",
                context=text,
                suggestion="Consider adding spaces around English words"
            ))
        
        return issues
    
    def _check_uzbek_specific(self, text: str) -> List[TranslationIssue]:
        """Uzbek-specific validation checks."""
        issues = []
        
        # Check for proper apostrophe usage in Uzbek
        if "'" in text and not re.search(r"[gGnN]'", text):
            # Uzbek uses apostrophes primarily for g' and n' combinations
            issues.append(TranslationIssue(
                severity=TranslationSeverity.INFO,
                message="Apostrophe usage in Uzbek text",
                context=text,
                suggestion="Ensure apostrophes are used correctly (g', n', etc.)"
            ))
        
        return issues


# Translation quality metrics
class TranslationMetrics:
    """Calculate and track translation quality metrics."""
    
    @staticmethod
    def calculate_completion_rate(po_file_path: str) -> Dict[str, float]:
        """Calculate translation completion rate from .po file."""
        try:
            with open(po_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            entries = TranslationMetrics._parse_po_entries(content)
            total = 0
            completed = 0
            for entry in entries:
                msgid = entry['msgid']
                if not msgid.strip():
                    continue
                total += 1

                if entry['is_plural']:
                    plural_values = [v.strip() for v in entry['msgstr_plural'].values()]
                    if plural_values and all(plural_values):
                        completed += 1
                elif entry['msgstr'].strip():
                    completed += 1
            
            return {
                'total': total,
                'completed': completed,
                'rate': (completed / total * 100) if total > 0 else 0.0
            }
        except Exception as e:
            logger.error(f"Error calculating completion rate: {e}")
            return {'total': 0, 'completed': 0, 'rate': 0.0}
    
    @staticmethod
    def identify_missing_translations(po_file_path: str) -> List[str]:
        """Identify strings that need translation."""
        try:
            with open(po_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            entries = TranslationMetrics._parse_po_entries(content)
            missing = []
            for entry in entries:
                msgid = entry['msgid']
                if not msgid.strip():
                    continue

                if entry['is_plural']:
                    plural_values = [v.strip() for v in entry['msgstr_plural'].values()]
                    if not plural_values or any(not v for v in plural_values):
                        missing.append(msgid)
                elif not entry['msgstr'].strip():
                    missing.append(msgid)
            
            return missing
        except Exception as e:
            logger.error(f"Error identifying missing translations: {e}")
            return []

    @staticmethod
    def _parse_po_entries(content: str) -> List[Dict[str, object]]:
        """Parse PO content into structured singular/plural entries."""
        entries: List[Dict[str, object]] = []
        blocks = re.split(r'\n\s*\n', content)

        for block in blocks:
            stripped = block.strip()
            if not stripped:
                continue

            lines = stripped.split('\n')
            if any(line.strip().startswith('#~') for line in lines):
                continue

            msgid = ""
            msgstr = ""
            msgstr_plural: Dict[int, str] = {}
            in_msgid = False
            in_msgstr = False
            current_plural_index: Optional[int] = None
            is_plural = False

            for raw_line in lines:
                line = raw_line.strip()

                if line.startswith('msgid_plural '):
                    is_plural = True
                    in_msgid = False
                    in_msgstr = False
                    current_plural_index = None
                elif line.startswith('msgid '):
                    match = re.match(r'msgid\s+"(.*)"', line)
                    msgid = match.group(1) if match else ""
                    in_msgid = True
                    in_msgstr = False
                    current_plural_index = None
                elif line.startswith('msgstr['):
                    match = re.match(r'msgstr\[(\d+)\]\s+"(.*)"', line)
                    if match:
                        is_plural = True
                        current_plural_index = int(match.group(1))
                        msgstr_plural[current_plural_index] = match.group(2)
                        in_msgid = False
                        in_msgstr = False
                elif line.startswith('msgstr '):
                    match = re.match(r'msgstr\s+"(.*)"', line)
                    msgstr = match.group(1) if match else ""
                    in_msgid = False
                    in_msgstr = True
                    current_plural_index = None
                elif line.startswith('"'):
                    additional = re.match(r'"(.*)"', line)
                    if not additional:
                        continue
                    text = additional.group(1)
                    if in_msgid:
                        msgid += text
                    elif current_plural_index is not None:
                        msgstr_plural[current_plural_index] = msgstr_plural.get(current_plural_index, "") + text
                    elif in_msgstr:
                        msgstr += text

            if msgid.strip():
                entries.append({
                    'msgid': msgid,
                    'msgstr': msgstr,
                    'is_plural': is_plural,
                    'msgstr_plural': msgstr_plural,
                })

        return entries


# Export main classes
__all__ = [
    'TranslationGuidelines',
    'TranslationValidator', 
    'TranslationIssue',
    'TranslationSeverity',
    'TranslationMetrics'
]
