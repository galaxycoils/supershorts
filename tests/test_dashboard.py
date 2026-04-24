import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dashboard import app, PROJECT_ROOT

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_api_health(client):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": []}
        
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert 'ollama' in data
        assert 'uptime_s' in data

def test_api_assets(client, tmp_path):
    # Mock PROJECT_ROOT to use tmp_path
    with patch('dashboard.PROJECT_ROOT', tmp_path):
        assets_dir = tmp_path / "assets"
        bg_dir = assets_dir / "backgrounds"
        char_dir = assets_dir / "characters"
        music_dir = assets_dir / "music"
        
        bg_dir.mkdir(parents=True)
        char_dir.mkdir(parents=True)
        music_dir.mkdir(parents=True)
        
        (bg_dir / "bg1.jpg").touch()
        (char_dir / "char1.png").touch()
        (music_dir / "music1.mp3").touch()
        
        response = client.get('/api/assets')
        assert response.status_code == 200
        data = response.get_json()
        assert "bg1.jpg" in data["backgrounds"]
        assert "char1.png" in data["characters"]
        assert "music1.mp3" in data["music"]

def test_api_run_with_advanced_and_assets(client):
    # Patch the specific runner to avoid actual execution
    with patch('dashboard.run_brainrot_pipeline') as mock_runner:
        payload = {
            "count": 2,
            "dry_run": "y",
            "voice": "en_US-amy-medium",
            "llm_model": "mistral",
            "hd_mode": "y",
            "author_name": "TestAuthor",
            "background": "bg1.jpg",
            "character": "char1.png",
            "music": "music1.mp3",
            "temperature": "0.9"
        }
        
        response = client.post('/api/run/brainrot', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert 'job_id' in data

def test_api_run_default_values(client):
    with patch('dashboard.run_brainrot_pipeline') as mock_runner:
        response = client.post('/api/run/brainrot', json={})
        assert response.status_code == 200

def test_api_models(client):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [{"name": "model1"}, {"name": "model2"}]
        }
        
        response = client.get('/api/models')
        assert response.status_code == 200
        data = response.get_json()
        assert data["models"] == ["model1", "model2"]

def test_api_models_fallback(client):
    with patch('requests.get', side_effect=Exception("Ollama down")):
        response = client.get('/api/models')
        assert response.status_code == 200
        data = response.get_json()
        assert data["models"] == ["llama3", "mistral"]

def test_api_disk(client):
    with patch('dashboard._dir_mb', return_value=123.4):
        response = client.get('/api/disk')
        assert response.status_code == 200
        data = response.get_json()
        assert data["output_mb"] == 123.4
        assert data["pexels_mb"] == 123.4
        assert data["assets_mb"] == 123.4

def test_api_gallery(client, tmp_path):
    with patch('dashboard.PROJECT_ROOT', tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "video1.mp4").touch()
        (output_dir / "video2.mp4").touch()
        
        response = client.get('/api/gallery')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]["name"] in ["video1.mp4", "video2.mp4"]

def test_api_terminate(client):
    job_id = "test_job"
    with patch('dashboard.JOBS', {job_id: {"status": "running"}}):
        response = client.post(f'/api/terminate/{job_id}')
        assert response.status_code == 200
        assert response.get_json()["status"] == "terminated"

def test_api_terminate_not_found(client):
    response = client.post('/api/terminate/nonexistent')
    assert response.status_code == 404
