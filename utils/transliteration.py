"""
Korean ↔ English Transliteration Utilities

Provides romanization of Korean text and phonetic Korean approximation of English text.
Used for cross-language search functionality.
"""

import re
import unicodedata

# Korean Unicode ranges
HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
JAMO_INITIALS = 0x1100
JAMO_MEDIALS = 0x1161
JAMO_FINALS = 0x11A7

# Jamo consonant/vowel mappings for romanization
INITIALS = [
    'g', 'gg', 'n', 'd', 'dd', 'r', 'm', 'b', 'bb', 's', 'ss',
    '', 'j', 'jj', 'ch', 'k', 't', 'p', 'h'
]

MEDIALS = [
    'a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 'wae',
    'oe', 'yo', 'u', 'wo', 'we', 'wi', 'yu', 'eu', 'ui', 'i'
]

FINALS = [
    '', 'k', 'kk', 'ks', 'n', 'nj', 'nh', 't', 'l', 'lk', 'lm',
    'lp', 'ls', 'lt', 'lp', 'lh', 'm', 'p', 'ps', 's', 'ss',
    'ng', 'j', 'ch', 'k', 't', 'p', 'h'
]

# English to Korean phonetic mappings (approximate)
ENGLISH_TO_KOREAN = {
    # Consonants
    'b': '브', 'c': '크', 'd': '드', 'f': '프', 'g': '그',
    'h': '흐', 'j': '즈', 'k': '크', 'l': '르', 'm': '므',
    'n': '느', 'p': '프', 'q': '크', 'r': '르', 's': '스',
    't': '트', 'v': '브', 'w': '우', 'x': '크스', 'z': '즈',
    # Vowels
    'a': '아', 'e': '에', 'i': '이', 'o': '오', 'u': '우',
    # Common patterns
    'ch': '치', 'sh': '시', 'th': '스', 'ph': '프',
    'ee': '이', 'oo': '우', 'ou': '아우', 'ai': '아이',
    'ea': '이', 'ie': '이', 'ey': '이', 'ay': '에이',
    'ck': '크', 'ng': '응', 'tion': '션', 'sion': '션',
}

# Common word mappings for better transliteration
WORD_MAPPINGS_EN_TO_KR = {
    'restaurant': '레스토랑',
    'halal': '할랄',
    'cafe': '카페',
    'coffee': '커피',
    'chicken': '치킨',
    'pizza': '피자',
    'burger': '버거',
    'kebab': '케밥',
    'shawarma': '샤와르마',
    'biryani': '비리야니',
    'mosque': '모스크',
    'masjid': '마스지드',
    'market': '마켓',
    'store': '스토어',
    'shop': '샵',
    'food': '푸드',
    'seoul': '서울',
    'busan': '부산',
    'incheon': '인천',
    'daegu': '대구',
    'itaewon': '이태원',
    'hongdae': '홍대',
    'gangnam': '강남',
    'myeongdong': '명동',
    'sinchon': '신촌',
}

WORD_MAPPINGS_KR_TO_EN = {v: k for k, v in WORD_MAPPINGS_EN_TO_KR.items()}


def is_hangul(char):
    """Check if a character is Korean Hangul"""
    code = ord(char)
    return HANGUL_START <= code <= HANGUL_END


def decompose_hangul(char):
    """Decompose a Hangul syllable into its jamo components"""
    code = ord(char) - HANGUL_START
    initial = code // 588
    medial = (code % 588) // 28
    final = code % 28
    return initial, medial, final


def romanize_char(char):
    """Convert a single Hangul character to romanized form"""
    if not is_hangul(char):
        return char
    
    initial, medial, final = decompose_hangul(char)
    
    romanized = INITIALS[initial] + MEDIALS[medial]
    if final > 0:
        romanized += FINALS[final]
    
    return romanized


def romanize_korean(text):
    """
    Convert Korean text to romanized form (Revised Romanization).
    
    Args:
        text: String potentially containing Korean characters
        
    Returns:
        Romanized version of the text
    """
    if not text:
        return ''
    
    # Check for known word mappings first
    text_lower = text.lower().strip()
    if text_lower in WORD_MAPPINGS_KR_TO_EN:
        return WORD_MAPPINGS_KR_TO_EN[text_lower]
    
    result = []
    for char in text:
        if is_hangul(char):
            result.append(romanize_char(char))
        else:
            result.append(char)
    
    romanized = ''.join(result)
    
    # Clean up common romanization artifacts
    romanized = re.sub(r'\s+', ' ', romanized)
    
    return romanized.strip()


def koreanize_english(text):
    """
    Convert English text to approximate Korean phonetic form.
    
    Args:
        text: English string to convert
        
    Returns:
        Korean phonetic approximation
    """
    if not text:
        return ''
    
    text = text.lower().strip()
    
    # Check for known word mappings first
    words = text.split()
    result_words = []
    
    for word in words:
        if word in WORD_MAPPINGS_EN_TO_KR:
            result_words.append(WORD_MAPPINGS_EN_TO_KR[word])
        else:
            # Convert character by character with pattern matching
            result = []
            i = 0
            word_len = len(word)
            
            while i < word_len:
                matched = False
                
                # Try multi-character patterns first (longest match)
                for length in range(4, 0, -1):
                    if i + length <= word_len:
                        pattern = word[i:i+length]
                        if pattern in ENGLISH_TO_KOREAN:
                            result.append(ENGLISH_TO_KOREAN[pattern])
                            i += length
                            matched = True
                            break
                
                if not matched:
                    # Keep non-alphabetic characters as-is
                    if not word[i].isalpha():
                        result.append(word[i])
                    i += 1
            
            result_words.append(''.join(result))
    
    return ' '.join(result_words)


def has_korean(text):
    """Check if text contains any Korean characters"""
    if not text:
        return False
    return any(is_hangul(char) for char in text)


def has_english(text):
    """Check if text contains any English alphabetic characters"""
    if not text:
        return False
    return any(char.isalpha() and ord(char) < 128 for char in text)


def generate_transliterations(text):
    """
    Generate all relevant transliterations for a given text.
    
    Args:
        text: Input text (can be Korean, English, or mixed)
        
    Returns:
        Dict with 'romanized' and 'korean' transliterations
    """
    if not text:
        return {'romanized': None, 'korean': None}
    
    result = {
        'romanized': None,
        'korean': None,
    }
    
    # If text has Korean, generate romanized version
    if has_korean(text):
        result['romanized'] = romanize_korean(text)
    
    # If text has English, generate Korean phonetic version
    if has_english(text):
        result['korean'] = koreanize_english(text)
    
    return result


def expand_search_query(query):
    """
    Expand a search query with transliterations for better matching.
    
    Args:
        query: Original search query
        
    Returns:
        List of query variations including transliterations
    """
    if not query:
        return []
    
    variations = [query]
    transliterations = generate_transliterations(query)
    
    if transliterations['romanized']:
        variations.append(transliterations['romanized'])
    
    if transliterations['korean']:
        variations.append(transliterations['korean'])
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for v in variations:
        if v.lower() not in seen:
            seen.add(v.lower())
            unique.append(v)
    
    return unique
