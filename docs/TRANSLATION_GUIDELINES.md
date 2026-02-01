# Translation Guidelines and Validation System

## Overview

This document outlines the comprehensive translation guidelines and validation system for the Halal Korea project. Our system ensures high-quality, consistent translations across Korean (한국어), English, and Uzbek (O'zbek) languages.

## 🌍 Supported Languages

| Language | Code | Native Name | Direction | Formality Level |
|----------|------|-------------|-----------|-----------------|
| English  | `en` | English     | LTR       | Neutral         |
| Korean   | `ko` | 한국어      | LTR       | Polite          |
| Uzbek    | `uz` | O'zbek      | LTR       | Respectful      |

## 📚 Core Translation Principles

### 1. Cultural Sensitivity
- **Islamic Context**: All translations must respect Islamic culture and practices
- **Korean Context**: Consider Korean cultural norms and social expectations
- **Uzbek Context**: Maintain respectful tone appropriate for Uzbek culture

### 2. Terminology Consistency

#### Halal & Islamic Terms
| English | Korean | Uzbek | Notes |
|---------|--------|-------|-------|
| halal | 할랄 | halol | Never translate or transliterate differently |
| haram | 하람 | harom | Maintain consistent spelling |
| mosque | 모스크 | masjid | Korean uses transliteration, Uzbek uses Arabic term |
| prayer room | 기도실 | namoz xonasi | Functional translation |
| Muslim | 무슬림 | musulmon | Proper noun, consistent capitalization |
| Qibla | 키블라 | qibla | Direction of prayer |
| prayer times | 기도 시간 | namoz vaqtlari | |

#### Korean Geographic Terms
| English | Korean | Uzbek | Notes |
|---------|--------|-------|-------|
| Seoul | 서울 | Seul | Capital city |
| Korea | 한국 | Koreya | Country name |
| Korean Won | 원 (₩) | von (₩) | Currency |
| subway | 지하철 | metro | Public transport |
| district (구) | 구 | tuman | Administrative division |

### 3. Formality and Tone Guidelines

#### Korean (한국어)
- **Formality Level**: Polite formal (높임말)
- **Verb Endings**: Use `-습니다/-세요` forms
- **Imperatives**: Use polite requests (`-세요`) instead of direct commands
- **Questions**: End with polite question forms
- **Address Style**: Formal polite addressing

**Examples:**
- ❌ `찾아` (informal) → ✅ `찾으세요` (polite)
- ❌ `클릭해` (casual) → ✅ `클릭하세요` (polite)

#### Uzbek (O'zbek)
- **Formality Level**: Respectful
- **Address Style**: Formal addressing with respectful tone
- **Imperatives**: Use polite forms when addressing users
- **Script**: Modern Latin script (post-1993)

#### English
- **Formality Level**: Professional but approachable
- **Tone**: Clear, concise, and helpful
- **Style**: American English spelling and conventions

## 🔍 Validation System

### Automated Checks

Our validation system automatically checks for:

1. **Placeholder Consistency**
   - Django template variables: `{{ variable }}`
   - Format strings: `{0}`, `{name}`
   - HTML tags preservation

2. **Length Validation**
   - Korean translations: 0.5x - 2.0x English length
   - Uzbek translations: 0.8x - 1.5x English length

3. **Terminology Consistency**
   - Specialized Islamic terms
   - Korean geographic terms
   - Technical UI terms

4. **Language-Specific Checks**
   - **Korean**: Hangeul completeness, formality level
   - **Uzbek**: Proper apostrophe usage (`g'`, `n'`)
   - **English**: Grammar and punctuation

5. **HTML & Markup Integrity**
   - Tag preservation
   - Attribute consistency
   - Link integrity

### Quality Metrics

- **Completion Rate**: Percentage of translated strings
- **Consistency Score**: Terminology adherence
- **Formality Score**: Appropriate tone usage
- **Technical Score**: Placeholder and markup integrity

## 🛠️ Management Commands

### Translation Status
```bash
# View overall translation status
python manage.py translation_status

# Detailed breakdown for specific language
python manage.py translation_status --language ko --detailed

# Show missing translations
python manage.py translation_status --missing
```

### Validation
```bash
# Validate all translations
python manage.py validate_translations

# Validate specific language with detailed report
python manage.py validate_translations --language ko --report

# Save validation report to file
python manage.py validate_translations --output validation_report.json
```

### Consistency Checking
```bash
# Check terminology consistency
python manage.py check_translation_consistency

# Check specific category
python manage.py check_translation_consistency --category halal

# Generate detailed report
python manage.py check_translation_consistency --report
```

## 📝 Translation Workflow

### 1. Preparation
1. Extract translatable strings:
   ```bash
   python manage.py makemessages -l ko -l uz
   ```

2. Check current status:
   ```bash
   python manage.py translation_status
   ```

### 2. Translation Process
1. **Translate strings** in `.po` files located in `locale/[lang]/LC_MESSAGES/django.po`
2. **Follow terminology guidelines** for consistency
3. **Maintain appropriate formality** for each language
4. **Preserve all placeholders** and HTML tags

### 3. Validation
1. Validate translations:
   ```bash
   python manage.py validate_translations --language ko
   ```

2. Check consistency:
   ```bash
   python manage.py check_translation_consistency
   ```

3. Fix any issues reported by the validation system

### 4. Compilation
1. Compile translations:
   ```bash
   python manage.py compilemessages
   ```

2. Test in development environment
3. Verify language switching functionality

## ⚠️ Common Issues and Solutions

### Terminology Issues
**Problem**: Inconsistent translation of Islamic terms
**Solution**: Use the standardized terminology table above

**Problem**: English terms appearing in Korean/Uzbek translations
**Solution**: Always use the localized terms from our guidelines

### Formality Issues
**Problem**: Mixed formal/informal Korean
**Solution**: Consistently use polite formal (`-습니다/-세요`) endings

**Problem**: Too casual tone in Uzbek
**Solution**: Use respectful addressing and formal language structures

### Technical Issues
**Problem**: Missing placeholders in translations
**Solution**: Ensure all `{{ variables }}` and `{format}` strings are preserved

**Problem**: Broken HTML in translations
**Solution**: Maintain all HTML tags and attributes exactly as in source

## 🎯 Quality Standards

### Minimum Requirements
- ✅ **95%+ completion rate** for all languages
- ✅ **Zero critical validation errors** (missing placeholders, broken HTML)
- ✅ **Consistent terminology** across all contexts
- ✅ **Appropriate formality level** for each language

### Excellence Targets
- 🏆 **100% completion rate**
- 🏆 **Zero validation warnings**
- 🏆 **Cultural appropriateness** review by native speakers
- 🏆 **User testing** with target language speakers

## 🔧 Integration with Development

### Pre-commit Hooks
Consider adding translation validation to your pre-commit hooks:
```bash
# Validate translations before commit
python manage.py validate_translations --severity error
```

### CI/CD Integration
Include translation checks in your continuous integration:
```yaml
- name: Validate Translations
  run: |
    python manage.py validate_translations --report
    python manage.py check_translation_consistency
```

### Regular Maintenance
- **Weekly**: Run translation status check
- **Monthly**: Full validation and consistency review
- **Release**: Complete translation audit

## 📞 Support and Resources

### Getting Help
1. **Technical Issues**: Check validation command output
2. **Terminology Questions**: Refer to terminology tables
3. **Cultural Context**: Consult with native speakers
4. **Complex Translations**: Use `{% blocktranslate %}` for longer texts

### Best Practices
1. **Context First**: Understand the UI context before translating
2. **User Perspective**: Consider the end-user experience
3. **Consistency**: Always check existing translations for similar terms
4. **Validation**: Run validation after every translation session

---

*This document is part of the Halal Korea project documentation. For technical implementation details, see the source code in `utils/translation_guidelines.py`.*
