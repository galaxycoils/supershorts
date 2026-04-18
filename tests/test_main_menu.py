import pytest
from unittest.mock import MagicMock, patch

def test_imports_and_entry_points():
    """Verify all re-exported entry points in src.generator are callable."""
    from src import generator
    
    # List of functions that should be re-exported and callable
    entry_points = [
        'start_tutorial_generation',
        'generate_youtube_content_package',
        'start_viral_gameplay_mode',
        'run_brainrot_pipeline',
        'run_tcm_mode',
        'run_rotgen_pipeline',
        'start_idea_generator',
        'run_video_clipper',
        'start_learning_mode'
    ]
    
    for ep in entry_points:
        assert hasattr(generator, ep), f"generator missing {ep}"
        assert callable(getattr(generator, ep)), f"generator.{ep} is not callable"

def test_main_routing_logic():
    """Verify that main.py can be imported and has expected function."""
    import main
    assert hasattr(main, 'main')
    assert hasattr(main, 'main_flow')
    assert hasattr(main, 'produce_lesson_videos')

def test_workflow_engine_imports():
    """Verify run_workflow.py can be imported."""
    import run_workflow
    assert hasattr(run_workflow, 'run_brainrot')
    assert hasattr(run_workflow, 'run_tcm_batch')
