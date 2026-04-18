import pytest
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

# We import from the bridge specifically to verify its integrity
from src.generator import (
    generate_lesson_content,
    text_to_speech,
    generate_visuals,
    compose_video
)

class TestBridgePipelineIntegrity:
    @pytest.fixture
    def mock_env(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        return {
            "output_dir": output_dir,
            "lesson_title": "Integration Test Lesson",
            "content": {
                "short_form_highlight": "This is a test highlight for TCM integration.",
                "hashtags": "#test #integration"
            }
        }

    @patch('src.infrastructure.llm.ollama.chat')
    @patch('src.engine.video_engine.get_relevant_pexels_video')
    @patch('src.infrastructure.tts.subprocess.run')
    def test_mode_to_infra_pipeline(self, mock_subproc, mock_pexels, mock_ollama, mock_env):
        """
        Verifies the full pipeline from Mode logic (via Bridge) to Infrastructure.
        
        Mode calls Bridge -> Bridge calls Engine/Infrastructure -> Infrastructure calls Tools.
        """
        # --- ARRANGE ---
        # Mock LLM to return valid JSON content
        mock_ollama.return_value = {
            'message': {
                'content': json.dumps(mock_env["content"])
            }
        }
        
        # Mock Pexels to return a dummy mp4 path
        dummy_video = mock_env["output_dir"] / "dummy_video.mp4"
        dummy_video.touch()
        mock_pexels.return_value = str(dummy_video)
        
        # Mock subprocess for TTS (avoiding real ffmpeg/say calls)
        mock_subproc.return_value = MagicMock(returncode=0)

        # --- ACT ---
        # 1. Trigger Content Generation (via Bridge)
        content = generate_lesson_content(mock_env["lesson_title"])
        assert content["short_form_highlight"] == mock_env["content"]["short_form_highlight"]
        
        # 2. Trigger TTS (via Bridge)
        audio_file_base = mock_env["output_dir"] / "test_audio"
        # We need to fake the output of text_to_speech
        with patch('src.infrastructure.tts.Path.exists', return_value=True):
             # Ensure wav_path is returned and exists (mocked exists)
             final_audio = text_to_speech(content["short_form_highlight"], audio_file_base)
        
        # 3. Trigger Engine Visuals (via Bridge)
        slide_dir = mock_env["output_dir"] / "slides"
        slide_path = generate_visuals(
            output_dir=slide_dir,
            video_type="short",
            slide_content={
                "title": mock_env["lesson_title"],
                "content": content["short_form_highlight"]
            }
        )
        assert Path(slide_path).exists()
        
        # 4. Trigger Engine Composition (via Bridge)
        video_output = mock_env["output_dir"] / "final_video.mp4"
        
        # Mock heavy MoviePy internals to avoid actual rendering but verify orchestration
        with patch('src.engine.video_engine.VideoFileClip') as mock_vclip, \
             patch('src.engine.video_engine.AudioFileClip') as mock_aclip, \
             patch('src.engine.video_engine.ImageClip') as mock_iclip, \
             patch('src.engine.video_engine.CompositeVideoClip') as mock_composite, \
             patch('src.engine.video_engine.concatenate_videoclips') as mock_concat:
            
            # Setup mock durations and behavior
            mock_aclip.return_value.duration = 5.0
            mock_vclip.return_value.duration = 10.0
            mock_vclip.return_value.size = (1080, 1920)
            mock_vclip.return_value.fx.return_value = mock_vclip.return_value
            mock_vclip.return_value.subclip.return_value = mock_vclip.return_value
            mock_vclip.return_value.resize.return_value = mock_vclip.return_value
            mock_vclip.return_value.set_position.return_value = mock_vclip.return_value
            
            mock_iclip.return_value.set_duration.return_value = mock_iclip.return_value
            mock_iclip.return_value.fadein.return_value = mock_iclip.return_value
            mock_iclip.return_value.fadeout.return_value = mock_iclip.return_value
            mock_iclip.return_value.set_opacity.return_value = mock_iclip.return_value
            mock_iclip.return_value.set_position.return_value = mock_iclip.return_value
            mock_iclip.return_value.set_audio.return_value = mock_iclip.return_value
            
            mock_final = MagicMock()
            mock_concat.return_value = mock_final
            
            mock_composite.return_value.set_audio.return_value = mock_composite.return_value
            mock_composite.return_value.duration = 5.0
            
            compose_video(
                [slide_path], 
                [str(final_audio)], 
                video_output, 
                "short", 
                mock_env["lesson_title"]
            )
            
            # Verify orchestration: concatenate_videoclips should have been called
            assert mock_concat.called
            # And write_videofile called on the final clip
            assert mock_final.write_videofile.called

        # --- FINAL ASSERT ---
        # Verify bridge correctly routed to infrastructure/engine
        assert mock_ollama.called
        assert mock_pexels.called
        assert "final_video.mp4" in str(video_output)
