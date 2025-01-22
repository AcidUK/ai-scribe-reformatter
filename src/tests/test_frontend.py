import pytest
from frontend import Gui

def test_gui_initialization():
    """Test GUI initialization with default arguments"""
    initial_state = {
        "history": "Sample History",
        "exam": "Sample Exam",
        "imp": "Sample Impression",
        "plan": "Sample Plan"
    }
    
    gui = Gui(initial_state)
    
    assert gui.state == initial_state

def test_gui_update():
    """Test updating GUI state"""
    gui = Gui({})
    
    gui.update(
        history="New History", 
        exam="New Exam", 
        imp="New Impression", 
        plan="New Plan"
    )
    
    assert gui.state["history"] == "New History"
    assert gui.state["exam"] == "New Exam"
    assert gui.state["imp"] == "New Impression"
    assert gui.state["plan"] == "New Plan"

def test_gui_clear():
    """Test clearing GUI state"""
    initial_state = {
        "history": "Sample History",
        "exam": "Sample Exam",
        "imp": "Sample Impression",
        "plan": "Sample Plan"
    }
    
    gui = Gui(initial_state)
    gui.clear()
    
    assert gui.state == {}

def test_remove_headings():
    """Test removing section headings"""
    initial_state = {
        "history": "History:\nSample History Content",
        "exam": "Examination:\nSample Exam Content",
        "imp": "Impression:\nSample Impression Content",
        "plan": "Plan:\nSample Plan Content"
    }
    
    gui = Gui(initial_state)
    gui.remove_headings()
    
    assert not gui.state["history"].startswith("History:")
    assert not gui.state["exam"].startswith("Examination:")
    assert not gui.state["imp"].startswith("Impression:")
    assert not gui.state["plan"].startswith("Plan:")
    
    assert "Sample History Content" in gui.state["history"]
    assert "Sample Exam Content" in gui.state["exam"]
    assert "Sample Impression Content" in gui.state["imp"]
    assert "Sample Plan Content" in gui.state["plan"]