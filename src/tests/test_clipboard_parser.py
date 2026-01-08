import pytest
from clipboard_parser import (
    block_parser,
    parse_bullets_to_prose,
    parse_bullets_to_comma_separated_prose,
    get_items,
    get_split_sections,
    main,
    BlockItem,
    ConsultationParseError,
    validate_consultation_content
)

def test_block_parser_basic():
    """Test basic block parsing functionality"""
    block = "History:\n- Patient is a 45-year-old male\n- Presenting with chest pain"
    result = block_parser(block)
    
    assert result is not None
    assert result.heading == "History:"
    assert result.bullets == ["Patient is a 45-year-old male", "Presenting with chest pain"]
    assert result.prose == "Patient is a 45-year-old male. Presenting with chest pain"

def test_block_parser_empty_block():
    """Test parsing an empty block"""
    assert block_parser("") is None

def test_parse_bullets_to_prose():
    """Test conversion of bullets to prose"""
    bullets = ["First item.", "Second item", "Third item."]
    result = parse_bullets_to_prose(bullets)
    assert result == "First item. Second item. Third item"

def test_parse_bullets_to_comma_separated_prose():
    """Test conversion of bullets to comma-separated prose"""
    bullets = ["First Item", "Second Item", "Third Item"]
    result = parse_bullets_to_comma_separated_prose(bullets)
    assert result == "first Item, second Item, third Item"

def test_get_items():
    """Test parsing multiple blocks"""
    consultation = """History:
- Patient is 45
- Male gender

Examination:
- Normal vitals
- No acute distress"""
    
    items = get_items(consultation)
    assert len(items) == 2
    assert items[0].heading == "History:"
    assert items[1].heading == "Examination:"

def test_block_item_parse_history():
    """Test parsing of history section"""
    block_item = BlockItem(
        heading="History:", 
        bullets=["Patient details"], 
        prose="Patient is 45 years old", 
        comma_separated_prose="patient is 45 years old"
    )
    
    result = block_item.parse()
    assert "History:" in result
    assert "Patient is 45 years old" in result

def test_block_item_parse_pmh():
    """Test parsing of past medical history"""
    block_item = BlockItem(
        heading="Past Medical History:", 
        bullets=["Hypertension", "Diabetes"], 
        prose="Hypertension and Diabetes", 
        comma_separated_prose="hypertension and diabetes"
    )
    
    result = block_item.parse()
    assert result.startswith("Hx of ")

def test_block_item_parse_exam():
    """Test parsing of examination section"""
    block_item = BlockItem(
        heading="Examination:", 
        bullets=["Vitals stable", "No acute distress"], 
        prose="Vitals stable, no acute distress", 
        comma_separated_prose="vitals stable, no acute distress"
    )
    
    result = block_item.parse()
    assert "Examination:" in result
    assert "Obs stable" in result
    assert "No acute distress" in result

def test_block_item_parse_exam_na():
    """Test parsing of examination section with N/A"""
    block_item = BlockItem(
        heading="Examination:", 
        bullets=["N/A"], 
        prose="Not applicable", 
        comma_separated_prose="N/A"
    )
    
    result = block_item.parse()
    assert result == ""

def test_get_split_sections():
    """Test splitting a full consultation into sections"""
    consultation = """History:
- Patient is 45 years old
- Male gender

Examination:
- Normal vitals
- No acute distress

Impression:
- Stable condition
- No immediate concerns

Management Plan:
- Follow up in 2 weeks
- Continue current medication"""

    sections = get_split_sections(consultation)
    
    assert "history" in sections
    assert "exam" in sections
    assert "imp" in sections
    assert "plan" in sections
    
    assert "Patient is 45 years old" in sections["history"]
    assert "Normal vitals" in sections["exam"]
    assert "Stable condition" in sections["imp"]
    assert "Follow up in 2 weeks" in sections["plan"]

def test_main_function():
    """Test the main function processing a consultation"""
    consultation = """History:
- Patient details
- Important information

Examination:
- Clinical findings"""

    result = main(consultation)

    assert "History:" in result
    assert "Examination:" in result
    assert "Patient details" in result
    assert "Clinical findings" in result


# Tests for validation and exception handling


def test_validate_consultation_content_valid():
    """Test validation of valid consultation content"""
    valid_content = """History:
- Patient is 45 years old

Plan:
- Follow up in 2 weeks"""
    # Should not raise
    validate_consultation_content(valid_content)


def test_validate_consultation_content_empty():
    """Test validation rejects empty content"""
    with pytest.raises(ConsultationParseError) as exc_info:
        validate_consultation_content("")
    assert "empty" in str(exc_info.value).lower()


def test_validate_consultation_content_whitespace_only():
    """Test validation rejects whitespace-only content"""
    with pytest.raises(ConsultationParseError) as exc_info:
        validate_consultation_content("   \n  \t  ")
    assert "empty" in str(exc_info.value).lower()


def test_validate_consultation_content_missing_history():
    """Test validation rejects content without History section"""
    invalid_content = """Plan:
- Follow up in 2 weeks"""
    with pytest.raises(ConsultationParseError) as exc_info:
        validate_consultation_content(invalid_content)
    assert "history" in str(exc_info.value).lower()


def test_validate_consultation_content_missing_plan():
    """Test validation rejects content without Plan section"""
    invalid_content = """History:
- Patient is 45 years old"""
    with pytest.raises(ConsultationParseError) as exc_info:
        validate_consultation_content(invalid_content)
    assert "plan" in str(exc_info.value).lower()


def test_validate_consultation_content_too_short():
    """Test validation rejects very short content"""
    invalid_content = "History:Plan:"
    with pytest.raises(ConsultationParseError) as exc_info:
        validate_consultation_content(invalid_content)
    assert "too short" in str(exc_info.value).lower()


def test_consultation_parse_error_with_preview():
    """Test ConsultationParseError includes clipboard preview"""
    long_content = "History:" + ("x" * 200) + "\nPlan:\n- Follow up"
    error = ConsultationParseError("Test error", long_content)
    error_str = str(error)
    assert "Test error" in error_str
    assert "..." in error_str  # Indicates truncation
    assert "Clipboard preview:" in error_str


def test_consultation_parse_error_without_preview():
    """Test ConsultationParseError without clipboard preview"""
    error = ConsultationParseError("Test error")
    error_str = str(error)
    assert error_str == "Test error"
    assert "Clipboard preview:" not in error_str


def test_get_split_sections_with_invalid_content():
    """Test get_split_sections raises ConsultationParseError for invalid content"""
    invalid_content = "Random text that is not a consultation"
    with pytest.raises(ConsultationParseError):
        get_split_sections(invalid_content)


def test_get_split_sections_with_empty_content():
    """Test get_split_sections raises ConsultationParseError for empty content"""
    with pytest.raises(ConsultationParseError) as exc_info:
        get_split_sections("")
    assert "empty" in str(exc_info.value).lower()